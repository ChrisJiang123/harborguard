"""One SQLite writer, atomic checkpoints and an internal, unbounded event archive.

Only the last 500 events are exposed by the frozen v1 HTTP contract. The archive
is deliberately not a new public history API. Use one backend worker per file.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path


class StorageError(RuntimeError):
    """A durable write/read failed; never report a successful volatile write."""


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


class HistoryStore:
    def __init__(self, path):
        self.path = str(path)
        self.connection = None
        self._lock = None
        self._objects = {}
        self._images = set()
        try:
            if self.path != ":memory:":
                target = Path(path).expanduser().resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                self.path = str(target)
                self._lock = target.with_name(target.name + ".lock").open("a+b")
                self._lock.seek(0)
                if os.name == "nt":
                    import msvcrt
                    if target.with_name(target.name + ".lock").stat().st_size == 0:
                        self._lock.write(b"0")
                        self._lock.flush()
                    self._lock.seek(0)
                    msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.connection = sqlite3.connect(self.path, timeout=1, check_same_thread=False)
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=FULL")
            version = self.connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise StorageError(f"Unsupported history database version: {version}")
            if version == 0:
                sql = (Path(__file__).resolve().parents[1] / "migrations/001_history.sql").read_text(encoding="utf-8")
                self.connection.executescript("BEGIN IMMEDIATE;\n" + sql + "\nCOMMIT;")
            if self.connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise StorageError("History database integrity check failed")
        except (OSError, sqlite3.Error, StorageError) as exc:
            self.close()
            raise StorageError("Cannot open durable history; inspect database path, lock and schema") from exc

    def load(self, fingerprint):
        try:
            row = self.connection.execute("SELECT seq,fingerprint,checkpoint FROM runtime WHERE id=1").fetchone()
            if row is None:
                if any(self.connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                       for table in ("events", "objects", "images")):
                    raise StorageError("History has records but no runtime checkpoint")
                return None
            if row[1] != fingerprint:
                raise StorageError("Checkpoint data/config/version differs; preserve DB and review migration")
            events = [json.loads(r[0]) for r in self.connection.execute(
                "SELECT payload FROM (SELECT seq,payload FROM events ORDER BY seq DESC LIMIT 500) ORDER BY seq")]
            return row[0], json.loads(row[2]), events
        except (sqlite3.Error, ValueError) as exc:
            raise StorageError("Cannot read durable history") from exc

    def commit(self, *, seq, fingerprint, checkpoint, messages, objects, images):
        # Prepare before BEGIN, and only update memoized writes after COMMIT.
        checkpoint_json = json_text(checkpoint)
        serialized = {(kind, identifier): json_text(payload) for kind, identifier, payload in objects}
        changed = {key: value for key, value in serialized.items() if self._objects.get(key) != value}
        new_images = {key: value for key, value in images.items() if key not in self._images}
        try:
            with self.connection:
                self.connection.execute("BEGIN IMMEDIATE")
                self.connection.executemany("INSERT INTO events(seq,payload) VALUES (?,?)",
                    [(m["seq"], json_text(m)) for m in messages if m["type"] == "event"])
                self.connection.executemany(
                    "INSERT INTO objects(kind,id,payload) VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload",
                    [(kind, identifier, payload) for (kind, identifier), payload in changed.items()])
                self.connection.executemany("INSERT INTO images(id,png) VALUES (?,?) ON CONFLICT(id) DO NOTHING",
                                            list(new_images.items()))
                self.connection.execute(
                    "INSERT INTO runtime(id,seq,fingerprint,checkpoint) VALUES (1,?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET seq=excluded.seq,fingerprint=excluded.fingerprint,checkpoint=excluded.checkpoint",
                    (seq, fingerprint, checkpoint_json))
        except sqlite3.Error as exc:
            raise StorageError("Durable write failed; operation was not committed") from exc
        # Memoize only the active working set, not the ever-growing archive.
        self._objects = serialized
        self._images = set(images)

    def get_object(self, kind, identifier):
        try:
            row = self.connection.execute("SELECT payload FROM objects WHERE kind=? AND id=?", (kind, identifier)).fetchone()
            return json.loads(row[0]) if row else None
        except (sqlite3.Error, ValueError) as exc:
            raise StorageError("Cannot read archived detail") from exc

    def commit_sequence(self, *, previous, seq):
        """A state publication changes only the sequence, not the committed world.

        Keep FULL durability and a transaction. Rewriting the same complete
        checkpoint five times per second is unnecessary; never reserve ahead.
        """
        if seq <= previous:
            raise StorageError("State sequence must increase")
        try:
            with self.connection:
                self.connection.execute("BEGIN IMMEDIATE")
                cursor = self.connection.execute("UPDATE runtime SET seq=? WHERE id=1 AND seq=?", (seq, previous))
                if cursor.rowcount != 1:
                    raise StorageError("State sequence differs from committed checkpoint")
        except sqlite3.Error as exc:
            raise StorageError("Durable state sequence write failed; state was not published") from exc

    def get_image(self, identifier):
        try:
            row = self.connection.execute("SELECT png FROM images WHERE id=?", (identifier,)).fetchone()
            return bytes(row[0]) if row else None
        except sqlite3.Error as exc:
            raise StorageError("Cannot read archived sonar") from exc

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self._lock is not None:
            # Closing releases the OS lock, including when acquisition failed.
            self._lock.close()
            self._lock = None
