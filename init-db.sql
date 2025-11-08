-- ===== UNIFIED MEMORY DATABASE SCHEMA =====
-- PostgreSQL Schema per Knowledge Graph Multi-Source
-- Version: 2.0

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Full-text search

-- ===== ENTITIES TABLE =====
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- person, organization, project, concept, event
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_metadata ON entities USING GIN(metadata);

-- ===== SOURCES TABLE =====
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL,  -- email, audio, chat, web, document
    source_id VARCHAR(500),  -- email ID, file path, URL, etc.
    source_date TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sources_type ON sources(source_type);
CREATE INDEX idx_sources_id ON sources(source_id);
CREATE INDEX idx_sources_date ON sources(source_date DESC);
CREATE INDEX idx_sources_metadata ON sources USING GIN(metadata);

-- ===== OBSERVATIONS TABLE =====
CREATE TABLE IF NOT EXISTS observations (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    confidence REAL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_obs_entity ON observations(entity_id);
CREATE INDEX idx_obs_source ON observations(source_id);
CREATE INDEX idx_obs_confidence ON observations(confidence DESC);
CREATE INDEX idx_obs_created ON observations(created_at DESC);

-- Full-text search su observations
CREATE INDEX idx_obs_content_fts ON observations USING GIN(to_tsvector('italian', content));

-- ===== RELATIONS TABLE =====
CREATE TABLE IF NOT EXISTS relations (
    id SERIAL PRIMARY KEY,
    from_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    to_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type VARCHAR(100) NOT NULL,  -- works_at, knows, part_of, located_in, etc.
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    confidence REAL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(from_entity_id, to_entity_id, relation_type)
);

CREATE INDEX idx_rel_from ON relations(from_entity_id);
CREATE INDEX idx_rel_to ON relations(to_entity_id);
CREATE INDEX idx_rel_type ON relations(relation_type);
CREATE INDEX idx_rel_source ON relations(source_id);

-- ===== CONSENSUS SCORES (Materialized View) =====
-- Vista per calcolare consensus score per entity
CREATE MATERIALIZED VIEW IF NOT EXISTS entity_consensus AS
SELECT
    e.id AS entity_id,
    e.name AS entity_name,
    e.entity_type,
    COUNT(DISTINCT o.source_id) AS source_count,
    COUNT(o.id) AS observation_count,
    AVG(o.confidence) AS avg_confidence,
    COUNT(DISTINCT o.source_id) * AVG(o.confidence) AS consensus_score,
    MAX(o.created_at) AS last_updated
FROM entities e
LEFT JOIN observations o ON e.id = o.entity_id
GROUP BY e.id, e.name, e.entity_type;

CREATE UNIQUE INDEX idx_entity_consensus_id ON entity_consensus(entity_id);
CREATE INDEX idx_entity_consensus_score ON entity_consensus(consensus_score DESC);

-- Refresh function per aggiornare consensus
CREATE OR REPLACE FUNCTION refresh_consensus()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY entity_consensus;
END;
$$ LANGUAGE plpgsql;

-- ===== ENTITY GENERAL CONTEXT =====
-- Entity speciale per observations generali non collegate a entity specifiche
INSERT INTO entities (name, entity_type, metadata)
VALUES ('General_Context', 'system', '{"description": "System entity for general observations"}')
ON CONFLICT (name) DO NOTHING;

-- ===== TRIGGER: Auto-update timestamp =====
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===== FUNCTIONS: Utility =====

-- Function: Search entities full-text
CREATE OR REPLACE FUNCTION search_entities(search_query TEXT)
RETURNS TABLE (
    entity_id INTEGER,
    entity_name VARCHAR,
    entity_type VARCHAR,
    observation_text TEXT,
    relevance REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.name,
        e.entity_type,
        o.content,
        ts_rank(to_tsvector('italian', o.content), plainto_tsquery('italian', search_query)) AS relevance
    FROM entities e
    JOIN observations o ON e.id = o.entity_id
    WHERE to_tsvector('italian', o.content) @@ plainto_tsquery('italian', search_query)
        OR e.name ILIKE '%' || search_query || '%'
    ORDER BY relevance DESC
    LIMIT 50;
END;
$$ LANGUAGE plpgsql;

-- Function: Get entity with all observations and relations
CREATE OR REPLACE FUNCTION get_entity_full(entity_name_param VARCHAR)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'entity', (
            SELECT row_to_json(e.*)
            FROM entities e
            WHERE e.name = entity_name_param
        ),
        'observations', (
            SELECT json_agg(
                json_build_object(
                    'content', o.content,
                    'source_type', s.source_type,
                    'source_date', s.source_date,
                    'confidence', o.confidence
                ) ORDER BY o.created_at DESC
            )
            FROM observations o
            JOIN sources s ON o.source_id = s.id
            JOIN entities e ON o.entity_id = e.id
            WHERE e.name = entity_name_param
        ),
        'relations_outgoing', (
            SELECT json_agg(
                json_build_object(
                    'to', e_to.name,
                    'relation_type', r.relation_type,
                    'confidence', r.confidence
                )
            )
            FROM relations r
            JOIN entities e_from ON r.from_entity_id = e_from.id
            JOIN entities e_to ON r.to_entity_id = e_to.id
            WHERE e_from.name = entity_name_param
        ),
        'relations_incoming', (
            SELECT json_agg(
                json_build_object(
                    'from', e_from.name,
                    'relation_type', r.relation_type,
                    'confidence', r.confidence
                )
            )
            FROM relations r
            JOIN entities e_from ON r.from_entity_id = e_from.id
            JOIN entities e_to ON r.to_entity_id = e_to.id
            WHERE e_to.name = entity_name_param
        ),
        'consensus_score', (
            SELECT consensus_score
            FROM entity_consensus ec
            JOIN entities e ON ec.entity_id = e.id
            WHERE e.name = entity_name_param
        )
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ===== SAMPLE DATA (per testing) =====
-- Inserisci alcuni dati di esempio

-- Source di esempio
INSERT INTO sources (source_type, source_id, source_date, metadata)
VALUES
    ('email', 'email_001', NOW() - INTERVAL '2 days', '{"from": "mario@example.com", "subject": "Meeting notes"}'),
    ('audio', 'audio_riunione_20250101.wav', NOW() - INTERVAL '1 day', '{"duration_seconds": 3600, "participants": 5}')
ON CONFLICT DO NOTHING;

-- Entities di esempio
INSERT INTO entities (name, entity_type, metadata)
VALUES
    ('Mario_Rossi', 'person', '{"email": "mario.rossi@example.com"}'),
    ('Acme_Corp', 'organization', '{"industry": "Technology"}'),
    ('Progetto_Alpha', 'project', '{"status": "active", "priority": "high"}')
ON CONFLICT (name) DO NOTHING;

-- Observations di esempio
INSERT INTO observations (entity_id, content, source_id, confidence)
SELECT
    e.id,
    'Ruolo: Senior Developer',
    s.id,
    0.95
FROM entities e, sources s
WHERE e.name = 'Mario_Rossi' AND s.source_type = 'email'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Relations di esempio
INSERT INTO relations (from_entity_id, to_entity_id, relation_type, source_id, confidence)
SELECT
    e1.id,
    e2.id,
    'works_at',
    s.id,
    0.9
FROM entities e1, entities e2, sources s
WHERE e1.name = 'Mario_Rossi'
    AND e2.name = 'Acme_Corp'
    AND s.source_type = 'email'
LIMIT 1
ON CONFLICT (from_entity_id, to_entity_id, relation_type) DO NOTHING;

-- Refresh consensus
SELECT refresh_consensus();

-- ===== STATISTICS =====
-- Query per vedere statistiche database
CREATE OR REPLACE VIEW database_stats AS
SELECT
    (SELECT COUNT(*) FROM entities) AS total_entities,
    (SELECT COUNT(*) FROM observations) AS total_observations,
    (SELECT COUNT(*) FROM relations) AS total_relations,
    (SELECT COUNT(*) FROM sources) AS total_sources,
    (SELECT COUNT(DISTINCT source_type) FROM sources) AS unique_source_types;

-- ===== GRANT PERMISSIONS =====
-- Assicura che l'utente memory_user abbia i permessi
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO memory_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO memory_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO memory_user;

-- ===== COMPLETION MESSAGE =====
DO $$
BEGIN
    RAISE NOTICE '✅ Database schema initialized successfully!';
    RAISE NOTICE '📊 Statistics:';
    RAISE NOTICE '   - Entities: %', (SELECT COUNT(*) FROM entities);
    RAISE NOTICE '   - Observations: %', (SELECT COUNT(*) FROM observations);
    RAISE NOTICE '   - Relations: %', (SELECT COUNT(*) FROM relations);
    RAISE NOTICE '   - Sources: %', (SELECT COUNT(*) FROM sources);
END $$;
