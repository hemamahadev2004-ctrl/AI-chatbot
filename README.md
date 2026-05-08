# AI Database Chatbot

A complete full-stack AI-powered database chatbot with a ChatGPT-inspired interface. The app uses MySQL as the source of truth, FAISS and SentenceTransformers for retrieval, and Groq for SQL planning plus answer generation.

## Stack

- Frontend: HTML5, CSS3, Vanilla JavaScript, TailwindCSS, Font Awesome, Marked.js
- Backend: FastAPI
- Database: MySQL
- AI: Groq API, FAISS, SentenceTransformers

## Project Structure

```text
backend/
|-- app.py
|-- requirements.txt
|-- ai/
|   |-- embeddings.py
|   |-- groq_client.py
|   |-- query_service.py
|   \-- vector_store.py
|-- data/
|   \-- chat_history.json
|-- db/
|   |-- connection.py
|   \-- repository.py
|-- routes/
|   \-- chat.py
\-- utils/
    |-- config.py
    |-- formatter.py
    |-- history_store.py
    |-- models.py
    \-- safety.py

frontend/
|-- index.html
|-- css/
|   \-- styles.css
\-- js/
    \-- app.js

sql/
\-- setup.sql
```

## Features

- ChatGPT-like dark UI with sidebar history and responsive mobile layout
- Local chat history plus backend chat session metadata
- Typing animation and streaming-style assistant rendering
- Markdown, code block, and table rendering
- FAISS retrieval over database schema and row context
- Safe read-only SQL planning using Groq
- Professional summaries grounded only in MySQL data
- New chat, export chat, clear chat, auto-scroll, and copy response actions

## How It Works

1. The backend introspects the MySQL schema dynamically.
2. Table schema and row documents are embedded using `sentence-transformers/all-MiniLM-L6-v2`.
3. FAISS retrieves the most relevant database context for the user question.
4. Groq generates a read-only MySQL query using only the retrieved schema context.
5. The backend validates the query and blocks destructive operations.
6. The SQL result is sent back through Groq for a concise, professional markdown answer.
7. The frontend renders the response with a ChatGPT-style experience.

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
GROQ_API_KEY=your_groq_api_key
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=chatbot_analytics
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=*
VECTOR_TOP_K=8
MAX_INDEX_ROWS_PER_TABLE=200
MAX_SQL_ROWS=200
INDEX_REFRESH_MINUTES=15
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
GROQ_MODEL=llama-3.3-70b-versatile
```

## Setup

1. Create a Python virtual environment and install dependencies:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Create the MySQL schema and sample data:

```bash
mysql -u root -p < ..\sql\setup.sql
```

3. Start the FastAPI server:

```bash
cd backend
uvicorn app:app --reload
```

4. Open `http://localhost:8000` in your browser.

## API

- `POST /chat`
- `GET /history`
- `POST /new-chat`
- `GET /health`

### `POST /chat` request

```json
{
  "chat_id": "optional-session-id",
  "message": "Show total sales this month"
}
```

### `POST /chat` response

```json
{
  "chat_id": "session-id",
  "summary": "North region led this month with ...",
  "table_data": [],
  "raw_data": [],
  "markdown": "## Sales Summary\n...",
  "timestamp": "2026-05-07T08:00:00+00:00",
  "sources": ["sales", "products"],
  "sql_used": "SELECT ..."
}
```

## Security Controls

- User input is normalized and length-limited
- SQL generation is restricted to `SELECT` and `WITH`
- Destructive keywords are blocked
- SQL comments are blocked
- Referenced tables are validated against the live schema
- MySQL execution uses parameterized query parameters from the validated SQL plan

## Notes

- The chatbot is intentionally grounded to database context and SQL results.
- The first run will download the embedding model if it is not already cached.
- Groq API access is required for SQL planning and final answer generation.
- For large databases, tune `MAX_INDEX_ROWS_PER_TABLE` and `INDEX_REFRESH_MINUTES`.
