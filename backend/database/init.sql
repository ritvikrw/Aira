CREATE TABLE IF NOT EXISTS call_logs (
    session_id      VARCHAR(64) PRIMARY KEY,
    caller_id       VARCHAR(128),
    caller_name     VARCHAR(256),
    room_name       VARCHAR(256),
    status          VARCHAR(32) DEFAULT 'active',
    call_start_time TIMESTAMPTZ DEFAULT NOW(),
    call_end_time   TIMESTAMPTZ,
    call_duration_seconds INTEGER
);

CREATE TABLE IF NOT EXISTS transcripts (
    id          SERIAL PRIMARY KEY,
    session_id  VARCHAR(64) NOT NULL REFERENCES call_logs(session_id) ON DELETE CASCADE,
    speaker     VARCHAR(16) NOT NULL,  -- 'user' or 'agent'
    message     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transcripts_session ON transcripts(session_id);

CREATE TABLE IF NOT EXISTS call_summaries (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(64) NOT NULL REFERENCES call_logs(session_id) ON DELETE CASCADE,
    summary_text    TEXT NOT NULL,
    key_topics      TEXT[],
    action_items    TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id          VARCHAR(64) PRIMARY KEY,
    filename    VARCHAR(512) NOT NULL,
    file_type   VARCHAR(16) NOT NULL,  -- 'pdf', 'xlsx', 'xls', 'csv'
    chunk_count INTEGER DEFAULT 0,
    status      VARCHAR(32) DEFAULT 'processing',  -- 'processing', 'ready', 'error'
    error_msg   TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
