-- ============================================================
-- AI Chatbot MVP — Schema SQL
-- Jalankan di database: ai_chatbot
-- Atau upload via pgAdmin Query Tool
-- ============================================================

-- Extension PGVector (wajib ada di PostgreSQL)
CREATE EXTENSION IF NOT EXISTS vector;

-- ── users ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- ── documents ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename   VARCHAR(512) NOT NULL,
    internal_filename   VARCHAR(512) NOT NULL UNIQUE,
    storage_path        TEXT NOT NULL,
    file_size_bytes     INTEGER NOT NULL,
    mime_type           VARCHAR(128) NOT NULL,
    checksum_sha256     VARCHAR(64) NOT NULL,
    ingest_status       VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    page_count          INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_documents_owner_id ON documents(owner_id);
CREATE INDEX IF NOT EXISTS ix_documents_ingest_status ON documents(ingest_status);

-- ── document_chunks ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    page_number     INTEGER,
    text            TEXT NOT NULL,
    token_count     INTEGER,
    extra_metadata  JSONB,
    embedding_model VARCHAR(256)
);
CREATE INDEX IF NOT EXISTS ix_chunks_document_id ON document_chunks(document_id);

-- ── document_embeddings ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS document_embeddings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id            UUID NOT NULL UNIQUE REFERENCES document_chunks(id) ON DELETE CASCADE,
    embedding_model     VARCHAR(256) NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    embedding           vector(1536),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_embeddings_vector
    ON document_embeddings USING hnsw (embedding vector_cosine_ops);

-- ── ingestion_jobs ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status          VARCHAR(50) NOT NULL DEFAULT 'queued',
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    error_code      VARCHAR(128),
    error_summary   VARCHAR(512),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_ingestion_jobs_document_id ON ingestion_jobs(document_id);

-- ── conversations ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(512),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_conversations_owner_id ON conversations(owner_id);

-- ── messages ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,
    content         TEXT NOT NULL,
    usage_metadata  JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages(conversation_id);

-- ── message_sources ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS message_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id      UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    chunk_id        UUID REFERENCES document_chunks(id) ON DELETE SET NULL,
    document_id     UUID NOT NULL,
    document_name   VARCHAR(512) NOT NULL,
    page_number     INTEGER,
    relevance_score FLOAT
);
CREATE INDEX IF NOT EXISTS ix_message_sources_message_id ON message_sources(message_id);

-- ── audit_logs ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type  VARCHAR(128) NOT NULL,
    target_type VARCHAR(128),
    target_id   VARCHAR(255),
    extra       JSONB,
    ip_address  VARCHAR(45),
    user_agent  VARCHAR(512),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);

-- ── alembic_version (agar Alembic tidak konflik) ──────────────────────────
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
INSERT INTO alembic_version (version_num)
VALUES ('001')
ON CONFLICT DO NOTHING;

-- ── Verifikasi ────────────────────────────────────────────────────────────
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
