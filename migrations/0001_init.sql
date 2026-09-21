CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE coin_inbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INT NOT NULL DEFAULT 0,
    last_error TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_coin_inbox_status ON coin_inbox (status);

CREATE TABLE coin_awards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id TEXT NOT NULL,
    referrer_email TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('archived', 'hired')),
    coins INT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    api_status TEXT,
    api_response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (candidate_id, outcome)
);
