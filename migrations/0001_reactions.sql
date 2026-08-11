CREATE TABLE IF NOT EXISTS reactions (
    reaction_id TEXT NOT NULL,
    visitor_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (reaction_id, visitor_id)
) WITHOUT ROWID;
