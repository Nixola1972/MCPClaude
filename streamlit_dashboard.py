#!/usr/bin/env python3
"""
Streamlit Dashboard for Meetings Transcriptions
Web UI to visualize, search, and upload audio files
"""

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import subprocess
import tempfile
import shutil

# Page config
st.set_page_config(
    page_title="Meetings Dashboard",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database config
POSTGRES_HOST = "srv778971.hstgr.cloud"
POSTGRES_PORT = 5433
POSTGRES_DB = "unified_memory"
POSTGRES_USER = "memory_user"
POSTGRES_PASS = "MemoryDB2025!Sicura"

QDRANT_HOST = "srv778971.hstgr.cloud"
QDRANT_PORT = 6333

OLLAMA_EMBED_API = "http://localhost:11434/api/embeddings"


# ===== DATABASE FUNCTIONS =====

@st.cache_resource
def get_postgres_connection():
    """Create PostgreSQL connection (cached)."""
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASS,
        cursor_factory=RealDictCursor
    )


@st.cache_resource
def get_qdrant_client():
    """Create Qdrant client (cached)."""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def create_embedding(text: str) -> list:
    """Create embedding for search."""
    try:
        response = requests.post(OLLAMA_EMBED_API, json={
            "model": "nomic-embed-text",
            "prompt": text
        }, timeout=30)

        if response.status_code == 200:
            return response.json()['embedding']
    except Exception as e:
        st.error(f"Errore embedding: {e}")

    return None


# ===== PAGES =====

def page_home():
    """Homepage with statistics."""
    st.title("🎙️ Meetings Dashboard")
    st.markdown("---")

    conn = get_postgres_connection()
    cur = conn.cursor()

    # Statistics
    col1, col2, col3, col4 = st.columns(4)

    # Total meetings
    cur.execute("SELECT COUNT(*) FROM sources WHERE source_type = 'audio'")
    total_meetings = cur.fetchone()['count']
    col1.metric("📊 Totale Riunioni", total_meetings)

    # Total duration
    cur.execute("SELECT SUM(duration_seconds) FROM sources WHERE source_type = 'audio'")
    total_seconds = cur.fetchone()['sum'] or 0
    total_hours = total_seconds / 3600
    col2.metric("⏱️ Durata Totale", f"{total_hours:.1f}h")

    # Total words
    cur.execute("SELECT SUM(word_count) FROM transcriptions")
    total_words = cur.fetchone()['sum'] or 0
    col3.metric("📝 Parole Totali", f"{total_words:,}")

    # This week meetings
    one_week_ago = datetime.now() - timedelta(days=7)
    cur.execute("""
        SELECT COUNT(*) FROM sources
        WHERE source_type = 'audio' AND source_date >= %s
    """, (one_week_ago,))
    week_meetings = cur.fetchone()['count']
    col4.metric("📅 Questa Settimana", week_meetings)

    st.markdown("---")

    # Chart: Meetings per week
    st.subheader("📈 Riunioni per Settimana")

    cur.execute("""
        SELECT
            DATE_TRUNC('week', source_date) as week,
            COUNT(*) as count,
            SUM(duration_seconds)/3600.0 as total_hours
        FROM sources
        WHERE source_type = 'audio'
        GROUP BY week
        ORDER BY week DESC
        LIMIT 12
    """)

    chart_data = cur.fetchall()

    if chart_data:
        df = pd.DataFrame(chart_data)
        df['week'] = pd.to_datetime(df['week'])

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df['week'],
            y=df['count'],
            name='Numero riunioni',
            yaxis='y',
            marker_color='lightblue'
        ))
        fig.add_trace(go.Scatter(
            x=df['week'],
            y=df['total_hours'],
            name='Durata (ore)',
            yaxis='y2',
            marker_color='orange',
            mode='lines+markers'
        ))

        fig.update_layout(
            xaxis=dict(title='Settimana'),
            yaxis=dict(title='Numero Riunioni', side='left'),
            yaxis2=dict(title='Durata Totale (ore)', overlaying='y', side='right'),
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun dato disponibile per il grafico")

    st.markdown("---")

    # Recent meetings
    st.subheader("📋 Ultime 5 Riunioni")

    cur.execute("""
        SELECT
            s.source_id,
            s.source_date,
            s.duration_seconds,
            t.word_count,
            sm.content as tldr,
            sm.participants
        FROM sources s
        LEFT JOIN transcriptions t ON s.id = t.source_id
        LEFT JOIN summaries sm ON s.id = sm.source_id AND sm.summary_type = 'tldr'
        WHERE s.source_type = 'audio'
        ORDER BY s.source_date DESC
        LIMIT 5
    """)

    recent = cur.fetchall()

    for meeting in recent:
        with st.expander(f"🎙️ {meeting['source_id']} - {meeting['source_date'].strftime('%d/%m/%Y %H:%M')}"):
            col1, col2, col3 = st.columns(3)
            col1.write(f"⏱️ **Durata:** {meeting['duration_seconds']//60} minuti")
            col2.write(f"📝 **Parole:** {meeting['word_count']}")

            participants = meeting.get('participants') or []
            if participants:
                col3.write(f"👥 **Partecipanti:** {', '.join(participants)}")

            if meeting.get('tldr'):
                st.write("**TL;DR:**")
                st.info(meeting['tldr'])

    cur.close()


def page_meetings():
    """List all meetings."""
    st.title("📋 Elenco Riunioni")

    conn = get_postgres_connection()
    cur = conn.cursor()

    # Filters
    col1, col2 = st.columns(2)

    with col1:
        search_name = st.text_input("🔍 Cerca per nome file", "")

    with col2:
        date_filter = st.date_input("📅 Filtra per data", value=None)

    # Query
    query = """
        SELECT
            s.id,
            s.source_id,
            s.source_date,
            s.duration_seconds,
            s.metadata,
            t.word_count,
            sm.content as tldr,
            sm.participants
        FROM sources s
        LEFT JOIN transcriptions t ON s.id = t.source_id
        LEFT JOIN summaries sm ON s.id = sm.source_id AND sm.summary_type = 'tldr'
        WHERE s.source_type = 'audio'
    """

    params = []
    if search_name:
        query += " AND s.source_id ILIKE %s"
        params.append(f"%{search_name}%")

    if date_filter:
        query += " AND DATE(s.source_date) = %s"
        params.append(date_filter)

    query += " ORDER BY s.source_date DESC"

    cur.execute(query, params)
    meetings = cur.fetchall()

    st.write(f"**Trovate {len(meetings)} riunioni**")
    st.markdown("---")

    # Display meetings
    for meeting in meetings:
        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.subheader(f"🎙️ {meeting['source_id']}")
                st.caption(f"📅 {meeting['source_date'].strftime('%d/%m/%Y %H:%M')}")

                if meeting.get('tldr'):
                    st.write(meeting['tldr'])

            with col2:
                st.metric("⏱️ Durata", f"{meeting['duration_seconds']//60}m")
                st.metric("📝 Parole", meeting['word_count'])

                quality = meeting.get('metadata', {}).get('quality_metrics', {})
                if quality:
                    st.metric("🎯 Q", f"{quality.get('words_per_minute', 0):.1f} w/m")

            # Details button
            if st.button("Vedi Dettagli", key=f"btn_{meeting['id']}"):
                st.session_state.selected_meeting = meeting['source_id']
                st.rerun()

            st.markdown("---")

    cur.close()


def page_meeting_detail(filename):
    """Detail page for a specific meeting with TABS layout."""
    st.title(f"🎙️ {filename}")

    conn = get_postgres_connection()
    cur = conn.cursor()

    # Get full data (including mentioned_people if exists)
    cur.execute("""
        SELECT
            s.source_id,
            s.source_date,
            s.duration_seconds,
            s.metadata,
            t.full_text,
            t.word_count,
            t.language,
            sm_tldr.content as tldr,
            sm_detailed.content as detailed_summary,
            sm_tldr.participants,
            sm_tldr.topics,
            sm_tldr.decisions,
            sm_tldr.action_items,
            sm_tldr.key_numbers
        FROM sources s
        LEFT JOIN transcriptions t ON s.id = t.source_id
        LEFT JOIN summaries sm_tldr ON s.id = sm_tldr.source_id AND sm_tldr.summary_type = 'tldr'
        LEFT JOIN summaries sm_detailed ON s.id = sm_detailed.source_id AND sm_detailed.summary_type = 'detailed'
        WHERE s.source_id = %s
    """, (filename,))

    meeting = cur.fetchone()

    if not meeting:
        st.error(f"Riunione non trovata: {filename}")
        if st.button("← Torna all'elenco"):
            del st.session_state.selected_meeting
            st.rerun()
        return

    # Back button
    if st.button("← Torna all'elenco"):
        del st.session_state.selected_meeting
        st.rerun()

    st.markdown("---")

    # Top Metadata (always visible)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📅 Data", meeting['source_date'].strftime('%d/%m/%Y'))
    col2.metric("⏱️ Durata", f"{meeting['duration_seconds']//60} min")
    col3.metric("📝 Parole", f"{meeting['word_count']:,}")

    quality = meeting.get('metadata', {}).get('quality_metrics', {})
    if quality:
        wpm = quality.get('words_per_minute', 0)
        conf = quality.get('avg_confidence', 0)
        col4.metric("🎯 Velocità", f"{wpm:.1f} w/m")
        if conf > 0:
            col5.metric("✅ Confidenza", f"{conf:.0%}")

    st.markdown("---")

    # TABS NAVIGATION
    tab1, tab2, tab3 = st.tabs(["📊 Panoramica", "📄 Trascrizione Completa", "🔍 Analisi Dettagliata"])

    # ========== TAB 1: PANORAMICA ==========
    with tab1:
        # TL;DR prominente
        if meeting.get('tldr'):
            st.markdown("### 📊 Riepilogo Veloce (TL;DR)")
            st.info(meeting['tldr'])
            st.markdown("---")

        # PUNTI CHIAVE (highlights)
        st.markdown("### 📌 Punti Chiave")

        col1, col2, col3 = st.columns(3)

        with col1:
            decisions = meeting.get('decisions') or []
            if decisions:
                st.markdown("**🎯 Decisioni Prese**")
                st.metric("", f"{len(decisions)}")
                for d in decisions[:3]:  # Show max 3
                    if isinstance(d, dict):
                        st.markdown(f"🔸 {d.get('decision', 'N/A')[:60]}...")

        with col2:
            action_items = meeting.get('action_items') or []
            if action_items:
                st.markdown("**✅ Azioni da Fare**")
                st.metric("", f"{len(action_items)}")
                for a in action_items[:3]:  # Show max 3
                    if isinstance(a, dict):
                        st.markdown(f"🔸 [{a.get('owner', '?')}] {a.get('task', 'N/A')[:50]}...")

        with col3:
            numbers = meeting.get('key_numbers') or []
            if numbers:
                st.markdown("**💰 Numeri Importanti**")
                st.metric("", f"{len(numbers)}")
                for n in numbers[:3]:  # Show max 3
                    if isinstance(n, dict):
                        st.markdown(f"🔸 {n.get('amount', 'N/A')} ({n.get('type', 'N/A')})")

        st.markdown("---")

        # Participants and Topics
        col1, col2 = st.columns(2)

        with col1:
            participants = meeting.get('participants') or []
            if participants:
                st.markdown("### 👥 Partecipanti alla Riunione")
                # Display as badges
                badges_html = " ".join([f'<span style="background-color:#1f77b4;color:white;padding:5px 10px;border-radius:15px;margin:2px;display:inline-block;">{p}</span>' for p in participants])
                st.markdown(badges_html, unsafe_allow_html=True)
            else:
                st.info("👥 Nessun partecipante identificato")

        with col2:
            topics = meeting.get('topics') or []
            if topics:
                st.markdown("### 🏷️ Argomenti Discussi")
                # Display as badges
                badges_html = " ".join([f'<span style="background-color:#ff7f0e;color:white;padding:5px 10px;border-radius:15px;margin:2px;display:inline-block;">{t}</span>' for t in topics])
                st.markdown(badges_html, unsafe_allow_html=True)
            else:
                st.info("🏷️ Nessun argomento identificato")

        st.markdown("---")

        # Detailed Summary
        if meeting.get('detailed_summary'):
            st.markdown("### 📋 Riassunto Dettagliato")
            st.write(meeting['detailed_summary'])

    # ========== TAB 2: TRASCRIZIONE COMPLETA ==========
    with tab2:
        st.markdown("### 📄 Trascrizione Integrale")

        # Search in transcription
        search_term = st.text_input("🔍 Cerca nella trascrizione", placeholder="es: fotovoltaico, budget, ecc.")

        transcription = meeting.get('full_text', '')

        if transcription:
            # Stats
            col1, col2, col3 = st.columns(3)
            col1.metric("Parole Totali", f"{meeting['word_count']:,}")
            col2.metric("Caratteri", f"{len(transcription):,}")
            col3.metric("Lingua", meeting.get('language', 'N/A').upper())

            st.markdown("---")

            # Display transcription with search highlight
            if search_term:
                # Highlight search term
                highlighted = transcription.replace(
                    search_term,
                    f"**:red[{search_term}]**"
                )
                st.markdown(highlighted)

                # Count occurrences
                count = transcription.lower().count(search_term.lower())
                if count > 0:
                    st.success(f"✅ Trovate {count} occorrenze di '{search_term}'")
                else:
                    st.warning(f"⚠️ Nessuna occorrenza di '{search_term}'")
            else:
                # Display full text
                st.text_area(
                    "Testo Completo",
                    transcription,
                    height=600,
                    disabled=True,
                    label_visibility="collapsed"
                )

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="⬇️ Scarica TXT",
                    data=transcription,
                    file_name=f"{filename}_trascrizione.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            with col2:
                # Create a formatted version
                formatted = f"""
RIUNIONE: {filename}
DATA: {meeting['source_date'].strftime('%d/%m/%Y %H:%M')}
DURATA: {meeting['duration_seconds']//60} minuti
PAROLE: {meeting['word_count']}

TL;DR:
{meeting.get('tldr', 'N/A')}

TRASCRIZIONE COMPLETA:
{transcription}
"""
                st.download_button(
                    label="⬇️ Scarica Completo",
                    data=formatted,
                    file_name=f"{filename}_completo.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        else:
            st.warning("⚠️ Trascrizione non disponibile")

    # ========== TAB 3: ANALISI DETTAGLIATA ==========
    with tab3:
        # Decisions detailed
        decisions = meeting.get('decisions') or []
        if decisions:
            st.markdown("### 🎯 Decisioni Prese")
            for i, d in enumerate(decisions, 1):
                if isinstance(d, dict):
                    with st.container():
                        st.markdown(f"**{i}. {d.get('decision', 'N/A')}**")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption(f"👤 Deciso da: **{d.get('by', 'N/A')}**")
                        with col2:
                            st.caption(f"📅 Quando: **{d.get('date', 'N/A')}**")

                        st.markdown("---")
        else:
            st.info("🎯 Nessuna decisione registrata")

        st.markdown("<br>", unsafe_allow_html=True)

        # Action Items with filtering
        action_items = meeting.get('action_items') or []
        if action_items:
            st.markdown("### ✅ Action Items")

            # Filter by owner
            all_owners = list(set([a.get('owner', 'N/A') for a in action_items if isinstance(a, dict)]))
            selected_owner = st.selectbox("Filtra per responsabile", ["Tutti"] + all_owners)

            filtered_actions = action_items
            if selected_owner != "Tutti":
                filtered_actions = [a for a in action_items if isinstance(a, dict) and a.get('owner') == selected_owner]

            for i, a in enumerate(filtered_actions, 1):
                if isinstance(a, dict):
                    with st.container():
                        # Checkbox for completion (UI only, not saved)
                        done = st.checkbox(
                            f"**[{a.get('owner', 'N/A')}]** {a.get('task', 'N/A')}",
                            key=f"action_{i}",
                            value=False
                        )

                        deadline = a.get('deadline', 'Da definire')
                        if done:
                            st.success(f"✅ Completato! (Scadenza era: {deadline})")
                        else:
                            st.caption(f"⏰ Scadenza: **{deadline}**")

                        st.markdown("---")
        else:
            st.info("✅ Nessuna azione da fare registrata")

        st.markdown("<br>", unsafe_allow_html=True)

        # Key Numbers
        numbers = meeting.get('key_numbers') or []
        if numbers:
            st.markdown("### 💰 Numeri e Cifre Chiave")

            # Display as table
            import pandas as pd

            numbers_data = []
            for n in numbers:
                if isinstance(n, dict):
                    numbers_data.append({
                        'Valore': n.get('amount', 'N/A'),
                        'Tipo': n.get('type', 'N/A'),
                        'Contesto': n.get('context', 'N/A')
                    })

            if numbers_data:
                df = pd.DataFrame(numbers_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("💰 Nessun numero chiave registrato")

    cur.close()


def page_search():
    """Semantic search page."""
    st.title("🔍 Ricerca Semantica")

    st.write("Cerca nelle riunioni utilizzando linguaggio naturale")

    query = st.text_input("Cosa stai cercando?", placeholder="es: riunioni su impianti fotovoltaici")

    limit = st.slider("Numero massimo risultati", 1, 20, 5)

    if st.button("🔍 Cerca", type="primary"):
        if not query:
            st.warning("Inserisci una query di ricerca")
            return

        with st.spinner("Ricerca in corso..."):
            # Create embedding
            query_vector = create_embedding(query)

            if not query_vector:
                st.error("Errore nella creazione dell'embedding")
                return

            # Search in Qdrant
            client = get_qdrant_client()
            results = client.search(
                collection_name="unified_memory_audio",
                query_vector=query_vector,
                limit=limit
            )

            if not results:
                st.info("Nessun risultato trovato")
                return

            # Get details from PostgreSQL
            conn = get_postgres_connection()
            cur = conn.cursor()

            st.success(f"Trovati {len(results)} risultati")
            st.markdown("---")

            for i, result in enumerate(results, 1):
                filename = result.payload['source_file']
                score = result.score

                cur.execute("""
                    SELECT
                        s.source_id,
                        s.source_date,
                        s.duration_seconds,
                        t.word_count,
                        sm.content as tldr,
                        sm.participants,
                        sm.topics
                    FROM sources s
                    LEFT JOIN transcriptions t ON s.id = t.source_id
                    LEFT JOIN summaries sm ON s.id = sm.source_id AND sm.summary_type = 'tldr'
                    WHERE s.source_id = %s
                """, (filename,))

                meeting = cur.fetchone()

                if meeting:
                    with st.container():
                        col1, col2 = st.columns([4, 1])

                        with col1:
                            st.subheader(f"{i}. 🎙️ {meeting['source_id']}")
                            st.caption(f"📅 {meeting['source_date'].strftime('%d/%m/%Y %H:%M')}")

                            if meeting.get('tldr'):
                                st.write(meeting['tldr'])

                            # Topics
                            topics = meeting.get('topics') or []
                            if topics:
                                st.write("**Argomenti:** " + ", ".join(topics))

                        with col2:
                            st.metric("🎯 Rilevanza", f"{score:.2%}")
                            st.metric("⏱️ Durata", f"{meeting['duration_seconds']//60}m")

                            if st.button("Vedi", key=f"view_{i}"):
                                st.session_state.selected_meeting = filename
                                st.rerun()

                        st.markdown("---")

            cur.close()


def page_upload():
    """Upload audio file page."""
    st.title("📤 Carica Audio")

    st.write("Carica un file audio per processing immediato")

    uploaded_file = st.file_uploader(
        "Seleziona file audio",
        type=['wav', 'm4a', 'mp3', 'flac'],
        help="Formati supportati: WAV, M4A, MP3, FLAC"
    )

    if uploaded_file is not None:
        # Display file info
        st.write(f"**File:** {uploaded_file.name}")
        st.write(f"**Dimensione:** {uploaded_file.size / 1024 / 1024:.2f} MB")

        if st.button("🚀 Avvia Processing", type="primary"):
            with st.spinner("Processing in corso... Questo potrebbe richiedere alcuni minuti"):
                try:
                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name

                    # TODO: Here you would call the workflow
                    # For now, just show a placeholder
                    st.info("⚠️ Funzionalità in sviluppo")
                    st.write("Il file verrebbe processato con:")
                    st.code(f"python3 audio_processing_workflow_v2.py --file {tmp_path}")

                    # Clean up
                    Path(tmp_path).unlink()

                    st.success("✅ File caricato! (demo mode)")
                    st.info("Nota: In produzione, il file verrebbe processato automaticamente")

                except Exception as e:
                    st.error(f"Errore: {e}")


def page_settings():
    """Settings page."""
    st.title("⚙️ Impostazioni")

    st.subheader("🕐 Scheduler Automatico")

    st.write("Configura l'esecuzione automatica del workflow")

    schedule_enabled = st.toggle("Abilita esecuzione automatica", value=False)

    if schedule_enabled:
        schedule_time = st.time_input("Orario esecuzione", value=datetime.strptime("00:00", "%H:%M").time())

        st.info(f"Il workflow verrà eseguito automaticamente ogni giorno alle {schedule_time.strftime('%H:%M')}")

        if st.button("Salva Configurazione"):
            # TODO: Save to cron or systemd timer
            st.success("Configurazione salvata! (demo mode)")
            st.code(f"0 {schedule_time.hour} * * * cd ~/MCPClaude && python3 audio_processing_workflow_v2.py")

    st.markdown("---")

    st.subheader("🗄️ Database")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**PostgreSQL**")
        st.write(f"Host: {POSTGRES_HOST}")
        st.write(f"Database: {POSTGRES_DB}")

        # Test connection
        if st.button("Test Connessione PostgreSQL"):
            try:
                conn = get_postgres_connection()
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM sources")
                count = cur.fetchone()['count']
                cur.close()
                st.success(f"✅ Connesso! ({count} sources)")
            except Exception as e:
                st.error(f"❌ Errore: {e}")

    with col2:
        st.write("**Qdrant**")
        st.write(f"Host: {QDRANT_HOST}")
        st.write(f"Collection: unified_memory_audio")

        # Test connection
        if st.button("Test Connessione Qdrant"):
            try:
                client = get_qdrant_client()
                collection = client.get_collection("unified_memory_audio")
                st.success(f"✅ Connesso! ({collection.points_count} vectors)")
            except Exception as e:
                st.error(f"❌ Errore: {e}")


# ===== MAIN =====

def main():
    # Sidebar navigation
    with st.sidebar:
        st.title("🎙️ Meetings")

        page = st.radio(
            "Navigazione",
            ["🏠 Home", "📋 Riunioni", "🔍 Ricerca", "📤 Upload", "⚙️ Impostazioni"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        st.caption("Dashboard v1.0")
        st.caption("MCP-Optimized System")

    # Route to pages
    if 'selected_meeting' in st.session_state and st.session_state.selected_meeting:
        page_meeting_detail(st.session_state.selected_meeting)
    elif page == "🏠 Home":
        page_home()
    elif page == "📋 Riunioni":
        page_meetings()
    elif page == "🔍 Ricerca":
        page_search()
    elif page == "📤 Upload":
        page_upload()
    elif page == "⚙️ Impostazioni":
        page_settings()


if __name__ == "__main__":
    main()
