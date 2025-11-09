-- ============================================
-- UNIFIED MEMORY SYSTEM - Schema v2.0
-- MCP-Optimized Context Architecture
-- ============================================

-- Drop old tables if upgrading
DROP VIEW IF EXISTS database_stats CASCADE;
DROP TABLE IF EXISTS observations CASCADE;
DROP TABLE IF EXISTS relations CASCADE;
DROP TABLE IF EXISTS summaries CASCADE;
DROP TABLE IF EXISTS transcriptions CASCADE;
DROP TABLE IF EXISTS entities CASCADE;
DROP TABLE IF EXISTS sources CASCADE;

-- ============================================
-- CORE TABLES
-- ============================================

-- Sources: tutte le fonti di dati
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL,  -- 'audio', 'email', 'chat', 'web'
    source_id VARCHAR(500) NOT NULL,   -- filename, url, message_id
    source_date TIMESTAMP,
    duration_seconds INTEGER,          -- per audio/video
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sources_type ON sources(source_type);
CREATE INDEX idx_sources_date ON sources(source_date DESC);
CREATE INDEX idx_sources_created ON sources(created_at DESC);

-- ============================================
-- TRANSCRIPTIONS: testo completo (non sempre embedato!)
-- ============================================
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    full_text TEXT NOT NULL,
    word_count INTEGER,
    language VARCHAR(10) DEFAULT 'it',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transcriptions_source ON transcriptions(source_id);
CREATE INDEX idx_transcriptions_fts ON transcriptions USING gin(to_tsvector('italian', full_text));

-- ============================================
-- SUMMARIES: riassunti multi-layer (CORE PER MCP!)
-- ============================================
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    summary_type VARCHAR(50) NOT NULL,  -- 'tldr', 'detailed', 'structured'
    content TEXT NOT NULL,

    -- Structured metadata per MCP query veloce
    participants JSONB DEFAULT '[]'::jsonb,     -- ["Marco", "Sara"]
    topics JSONB DEFAULT '[]'::jsonb,           -- ["budget", "cloud"]
    decisions JSONB DEFAULT '[]'::jsonb,        -- [{"decision": "...", "by": "Marco", "date": "..."}]
    action_items JSONB DEFAULT '[]'::jsonb,     -- [{"task": "...", "owner": "...", "deadline": "..."}]
    key_numbers JSONB DEFAULT '[]'::jsonb,      -- [{"amount": "50k", "type": "budget", "context": "..."}]

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_summaries_source ON summaries(source_id);
CREATE INDEX idx_summaries_type ON summaries(summary_type);
CREATE INDEX idx_summaries_participants ON summaries USING gin(participants);
CREATE INDEX idx_summaries_topics ON summaries USING gin(topics);
CREATE INDEX idx_summaries_fts ON summaries USING gin(to_tsvector('italian', content));

-- ============================================
-- ENTITIES: persone, progetti, aziende, concetti
-- ============================================
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- 'person', 'organization', 'project', 'concept'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_name ON entities(name);

-- ============================================
-- OBSERVATIONS: fatti estratti collegati a entities
-- ============================================
CREATE TABLE observations (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    confidence REAL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_observations_entity ON observations(entity_id);
CREATE INDEX idx_observations_source ON observations(source_id);
CREATE INDEX idx_observations_confidence ON observations(confidence DESC);

-- ============================================
-- RELATIONS: collegamenti tra entities
-- ============================================
CREATE TABLE relations (
    id SERIAL PRIMARY KEY,
    entity_from_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type VARCHAR(100) NOT NULL,  -- 'works_for', 'manages', 'collaborates_with'
    entity_to_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    confidence REAL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_relations_from ON relations(entity_from_id);
CREATE INDEX idx_relations_to ON relations(entity_to_id);
CREATE INDEX idx_relations_type ON relations(relation_type);

-- ============================================
-- VIEWS & HELPER FUNCTIONS
-- ============================================

-- Vista: statistiche database
CREATE VIEW database_stats AS
SELECT
    (SELECT COUNT(*) FROM entities) as total_entities,
    (SELECT COUNT(*) FROM observations) as total_observations,
    (SELECT COUNT(*) FROM relations) as total_relations,
    (SELECT COUNT(*) FROM sources) as total_sources,
    (SELECT COUNT(DISTINCT source_type) FROM sources) as unique_source_types,
    (SELECT COUNT(*) FROM transcriptions) as total_transcriptions,
    (SELECT COUNT(*) FROM summaries) as total_summaries,
    (SELECT COUNT(*) FROM summaries WHERE summary_type='tldr') as tldr_summaries,
    (SELECT COUNT(*) FROM summaries WHERE summary_type='detailed') as detailed_summaries;

-- Funzione: cerca entity per nome (fuzzy)
CREATE OR REPLACE FUNCTION search_entity(query_name VARCHAR)
RETURNS TABLE (id INTEGER, name VARCHAR, entity_type VARCHAR, similarity REAL) AS $$
BEGIN
    RETURN QUERY
    SELECT e.id, e.name, e.entity_type,
           similarity(e.name, query_name) as sim
    FROM entities e
    WHERE e.name % query_name
    ORDER BY sim DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Abilita estensione per similarity search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================
-- SAMPLE DATA (opzionale, per testing)
-- ============================================

-- General context entity (per observations senza entity specifica)
INSERT INTO entities (name, entity_type, metadata)
VALUES ('General_Context', 'concept', '{"description": "Default entity for general observations"}'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- GRANTS
-- ============================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO memory_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO memory_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO memory_user;

-- ============================================
-- COMPLETED
-- ============================================
-- Schema v2.0 - MCP-Optimized Context Architecture
-- Nuove tabelle: transcriptions, summaries
-- Enhanced: sources (duration_seconds), summaries (structured JSONB)
-- Ready for: multi-layer context, smart retrieval, MCP integration
