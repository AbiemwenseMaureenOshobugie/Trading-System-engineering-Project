CREATE TABLE observation_revisions (
    observation_id TEXT NOT NULL,
    instrument TEXT NOT NULL,
    h1_boundary_timestamp TEXT NOT NULL,
    revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    evaluation_timestamp TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    PRIMARY KEY (observation_id, revision_number),
    UNIQUE (instrument, h1_boundary_timestamp, revision_number)
);
CREATE INDEX idx_observation_revisions_identity
ON observation_revisions (instrument, h1_boundary_timestamp, revision_number DESC);
