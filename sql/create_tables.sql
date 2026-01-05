-- Patch 1: Case Files Tables
-- Execute this SQL in Railway PostgreSQL console

-- Table principale des dossiers
CREATE TABLE IF NOT EXISTS case_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'intake',
    client_name TEXT,
    client_email TEXT,
    customer_ref TEXT,
    complexity_level INTEGER DEFAULT 1,
    workflow_key TEXT DEFAULT 'WF_SIMPLE_QUOTE',
    confidence NUMERIC,
    missing_fields JSONB,
    assumptions JSONB,
    normalized_request JSONB,
    tags JSONB
);

-- Table des inputs (texte, fichiers, etc.)
CREATE TABLE IF NOT EXISTS case_inputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES case_files(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    source_type TEXT NOT NULL,
    filename TEXT,
    mime_type TEXT,
    storage_uri TEXT,
    raw_text TEXT,
    extracted_json JSONB
);

-- Table des événements (audit trail)
CREATE TABLE IF NOT EXISTS case_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES case_files(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    event_type TEXT NOT NULL,
    payload JSONB
);

-- Table des tâches (workflow steps)
CREATE TABLE IF NOT EXISTS case_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES case_files(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    step_key TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    input_json JSONB,
    output_json JSONB,
    error TEXT
);

-- Table des outputs (résultats)
CREATE TABLE IF NOT EXISTS case_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES case_files(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    output_type TEXT NOT NULL,
    content_json JSONB,
    file_uri TEXT
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_case_inputs_case_id ON case_inputs(case_id);
CREATE INDEX IF NOT EXISTS idx_case_events_case_id ON case_events(case_id);
CREATE INDEX IF NOT EXISTS idx_case_tasks_case_id ON case_tasks(case_id);
CREATE INDEX IF NOT EXISTS idx_case_outputs_case_id ON case_outputs(case_id);
CREATE INDEX IF NOT EXISTS idx_case_files_status ON case_files(status);
CREATE INDEX IF NOT EXISTS idx_case_files_created_at ON case_files(created_at DESC);
