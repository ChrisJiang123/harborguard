"""Durable high-water publication and bounded snapshot invariants."""
import pytest

from backend.app.engine import GameEngine
from backend.app.storage import HistoryStore, StorageError
from backend.tools.make_samples import samples


def test_state_only_publication_keeps_checkpoint_and_durably_advances_seq(tmp_path):
    path = tmp_path / "history.sqlite3"
    store = HistoryStore(path)
    game = GameEngine(debug_truth=False, store=store)
    game.start("a", 10)
    game.step(1)
    game.control("pause")
    row = store.connection.execute("SELECT seq,checkpoint FROM runtime").fetchone()
    # Fail if state publication attempts to rewrite the checkpoint document.
    store.connection.execute("CREATE TRIGGER checkpoint_unchanged BEFORE UPDATE OF checkpoint ON runtime BEGIN SELECT RAISE(ABORT,'unnecessary checkpoint rewrite'); END")
    for _ in range(20):
        game.publish_state()
    assert store.connection.execute("SELECT checkpoint FROM runtime").fetchone()[0] == row[1]
    assert game.bus.seq == row[0]+20
    state = game.state().model_dump()
    store.connection.execute("DROP TRIGGER checkpoint_unchanged")
    store.close()
    store = HistoryStore(path)
    restored = GameEngine(debug_truth=False, store=store)
    assert restored.state().model_dump() == state
    assert restored.publish_state()["seq"] == state["seq"]+1
    store.close()


def test_failed_state_sequence_write_cannot_broadcast_or_advance_cursor(tmp_path):
    store = HistoryStore(tmp_path / "history.sqlite3")
    game = GameEngine(debug_truth=False, store=store)
    queue = game.bus.subscribe()
    before = game.state().model_dump()
    store.connection.execute("CREATE TRIGGER fail_seq BEFORE UPDATE OF seq ON runtime BEGIN SELECT RAISE(ABORT,'sequence write failure'); END")
    with pytest.raises(StorageError, match="sequence write failed"):
        game.publish_state()
    assert queue.empty() and game.bus.pending is None
    assert game.state().model_dump() == before
    assert store.connection.execute("SELECT seq FROM runtime").fetchone()[0] == before["seq"]
    store.connection.execute("DROP TRIGGER fail_seq")
    # Never preallocate a block of sequences that a failed publication could skip.
    assert game.publish_state()["seq"] == before["seq"]+1
    store.close()


def test_sequence_compare_and_swap_rejects_an_inconsistent_writer(tmp_path):
    store = HistoryStore(tmp_path / "history.sqlite3")
    game = GameEngine(debug_truth=False, store=store)
    store.connection.execute("UPDATE runtime SET seq=999")
    store.connection.commit()
    queue = game.bus.subscribe()
    with pytest.raises(StorageError, match="differs"):
        game.publish_state()
    assert game.bus.seq == 0 and queue.empty()
    assert store.connection.execute("SELECT seq FROM runtime").fetchone()[0] == 999
    store.close()


def test_state_trims_history_without_trimming_rest_detail_or_sharing_mutable_state():
    game = GameEngine(debug_truth=False)
    state, _ = samples()
    track = state["tracks"][0]
    point = track["history"][0]
    track["history"] = [[*point[:3], float(t)] for t in range(5000)]
    game._tracks = [track]
    snapshot = game.state()
    assert len(snapshot.tracks[0].history) == 60
    assert snapshot.tracks[0].history[0][3] == 4940
    assert len(game.get_track(track["id"])["history"]) == 5000
    snapshot.tracks[0].history[0] = (0, 0, 0, 0)
    snapshot.tracks[0].err.a_m = 999
    assert game._tracks[0]["history"][4940][3] == 4940
    assert game._tracks[0]["err"]["a_m"] != 999
