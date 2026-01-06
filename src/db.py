from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_engine = None
_SessionLocal = None

# SQL pour créer les tables (exécuté une seule fois au démarrage)
CREATE_TABLES_SQL = """
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
"""

def init_db(database_url: str):
    """
    Initialise la connexion à la base de données et crée les tables si nécessaire.
    """
    global _engine, _SessionLocal
    if not database_url:
        print("⚠️ WARNING: DATABASE_URL not set, Case Files features disabled")
        return
    
    try:
        _engine = create_engine(database_url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
        
        # Créer les tables automatiquement
        with _engine.connect() as conn:
            conn.execute(text(CREATE_TABLES_SQL))
            conn.commit()
            print("✅ Database tables created/verified successfully")
        
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        _engine = None
        _SessionLocal = None
        raise

def get_session():
    if _SessionLocal is None:
        raise RuntimeError("DB not initialized - DATABASE_URL may be missing")
    return _SessionLocal()

def is_db_available():
    return _SessionLocal is not None
