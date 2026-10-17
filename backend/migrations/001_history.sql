-- Internal storage schema. This does not change the frozen public v1 contract.
CREATE TABLE IF NOT EXISTS runtime (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    seq INTEGER NOT NULL CHECK (seq >= 0),
    fingerprint TEXT NOT NULL,
    checkpoint TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS objects (
    kind TEXT NOT NULL,
    id TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (kind, id)
);
CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    png BLOB NOT NULL
);
PRAGMA user_version = 1;
