# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QRM Chatbot API is a FastAPI-based service that provides AI-powered customer support for WooCommerce sites. It uses OpenAI GPT models for conversations and ChromaDB for semantic product search.

## Common Development Commands

```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python main.py

# Run tests
pytest tests/

# Run with production server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Architecture Overview

The codebase follows a clean architecture pattern:

1. **API Layer** (`main.py`): FastAPI application with REST endpoints
   - Chat endpoint (`/chat`) - Main conversational AI interface
   - Product search (`/search/products`) - Semantic search using embeddings
   - Shipping calculations (`/shipping/calculate`)
   - Site management endpoints

2. **Service Layer** (`services.py`): Business logic
   - `ChatService`: Manages OpenAI chat completions with conversation history
   - `KnowledgeBaseService`: Handles ChromaDB queries and product retrieval

3. **Data Layer**:
   - `database.py`: Manages dual database connections (SQLAlchemy + ChromaDB)
   - `models.py`: Pydantic models for request/response validation

4. **Configuration** (`config.py`): Environment-based settings using Pydantic

## Key Technical Details

- **Dual Database System**: 
  - SQLAlchemy for relational data (products, categories, shipping)
  - ChromaDB for vector embeddings and semantic search
  
- **Multi-Site Support**: Each WooCommerce site has separate ChromaDB collections
  
- **Rate Limiting**: Configurable per-minute limits via RATE_LIMIT_PER_MINUTE env var

- **CORS**: Configured to accept all origins by default (adjust for production)

## Environment Variables

Required environment variables (.env file):
- `OPENAI_API_KEY`: OpenAI API key for chat and embeddings
- `DATABASE_URL`: SQLAlchemy connection string
- `CHROMA_HOST`, `CHROMA_PORT`: ChromaDB connection
- `API_HOST`, `API_PORT`: Server binding configuration
- `SECRET_KEY`: For session management
- `DEBUG`: Enable/disable debug mode

## Testing Approach

Tests should be placed in the `tests/` directory. The project uses pytest. When adding new features:
- Test API endpoints with FastAPI's TestClient
- Mock external services (OpenAI, ChromaDB) for unit tests
- Use fixtures for database setup/teardown