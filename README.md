# Meeting Memory Agent

A RAG-based AI assistant that indexes Google Meet transcripts and lets you query meeting history using natural language. Automatically extracts action items, tracks completion, and maintains memory across sessions.

![Python](https://img.shields.io/badge/python-3.12+-blue) ![LangChain](https://img.shields.io/badge/LangChain-1.2+-green) ![Streamlit](https://img.shields.io/badge/Streamlit-1.56+-red)

**[Live Demo](#)**

## Features

- **Gmail integration** — automatically fetches Google Meet transcript emails
- **Manual upload** — upload TXT transcripts directly
- **Smart extraction** — parses summary, decisions, and action items from each meeting
- **Action item tracking** — track open/completed tasks across meetings with assignees
- **Natural language Q&A** — ask questions across all indexed meetings
- **Conversation memory** — agent remembers context within a session
- **Multi-provider LLM** — switch between Claude (Anthropic) or Groq (free)

## Demo

> "What was discussed in the last meeting?"
> "What are the open action items for James?"
> "What decisions were made about the product launch?"
> "Who needs to do what by end of week?"

## Tech Stack

- **LangChain** — RAG pipeline, conversation memory, LLM abstraction
- **ChromaDB** — vector store with Google Gemini embeddings
- **Gmail API** — OAuth integration for fetching meeting transcripts
- **Streamlit** — web UI with chat and action items tracker
- **Claude / Groq** — LLM backends

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/meeting-memory-agent
cd meeting-memory-agent
```

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

### 4. Gmail setup (optional)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `credentials.json` to project root
5. Add yourself as a test user in OAuth consent screen

### 5. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). Upload a transcript or connect Gmail to get started.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | `anthropic` or `groq` | `groq` |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `ANTHROPIC_MODEL` | Claude model name | `claude-haiku-4-5-20251001` |
| `GROQ_API_KEY` | Groq API key | — |
| `GROQ_MODEL` | Groq model name | `llama-3.1-8b-instant` |
| `GOOGLE_API_KEY` | Google AI Studio key (for embeddings) | — |

## Project Structure

```
meeting-memory-agent/
├── app.py                   # Streamlit UI
├── agent.py                 # LangChain agent with conversation memory
├── memory_store.py          # ChromaDB storage and action item tracking
├── transcript_processor.py  # Parse Google Meet transcripts
├── gmail_client.py          # Gmail API OAuth integration
├── requirements.txt
├── .env.example
├── sample_transcript.txt    # Sample transcript for testing
└── README.md
```

## How It Works

1. **Ingest** — transcripts fetched from Gmail or uploaded manually
2. **Parse** — extracts meeting title, date, summary, and action items
3. **Store** — summary and each action item stored as separate chunks in ChromaDB
4. **Retrieve** — semantic search across all meetings based on user question
5. **Generate** — LangChain agent answers with conversation history context
6. **Track** — action items marked complete via UI, status persisted in ChromaDB

The key differentiator is **structured extraction**: unlike generic document Q&A, each action item is stored as a separate chunk with assignee metadata — enabling both semantic search and structured queries like "what does Sarah need to do".

## Sample Transcript

A sample e-commerce team transcript (`sample_transcript.txt`) is included for testing. Upload it via the sidebar to try the Q&A and action item tracking without Gmail setup.

## License

MIT

## Contact

Built by [Gaziz Nigmatullin](https://www.upwork.com/freelancers/gazizn)