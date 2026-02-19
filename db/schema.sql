-- Persona Builder — PostgreSQL Schema
-- Version: 1.0.0
--
-- Tables: personas, persona_artifacts
-- All UUIDs generated server-side via gen_random_uuid (pgcrypto).
-- Version increments are atomic per (name) via advisory lock
-- executed in db/repo.py.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- PERSONAS
-- ============================================================

CREATE TABLE personas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    version         INTEGER NOT NULL,
    role            TEXT,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'draft',
    confidence_score DOUBLE PRECISION,
    confidence_grade TEXT,
    spec_valid      BOOLEAN,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deployed_at     TIMESTAMPTZ,
    failure_reason  TEXT,

    UNIQUE (slug, version)
);

CREATE INDEX idx_personas_slug ON personas (slug);
CREATE INDEX idx_personas_status ON personas (status);
CREATE INDEX idx_personas_name ON personas (name);

-- ============================================================
-- PERSONA ARTIFACTS
-- ============================================================

CREATE TABLE persona_artifacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona_id      UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    artifact_type   TEXT NOT NULL,
    content_json    JSONB,
    content_text    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (persona_id, artifact_type)
);

CREATE INDEX idx_persona_artifacts_persona_id ON persona_artifacts (persona_id);
