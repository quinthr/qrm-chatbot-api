# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QRM Chatbot API is a FastAPI-based service that provides AI-powered customer support for WooCommerce sites. It uses OpenAI GPT models for conversations and enhanced SQL search for product retrieval.

**Production URL**: https://qrm-chatbot-api-qzgf.onrender.com (Render deployment)
**Legacy URL**: https://qrm-chatbot-api.com.soundproofingproducts.com.au (VentraIP - deprecated)

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
   - Chat endpoint (`/api/v1/chat`) - Main conversational AI interface with conversation history
   - Product search (`/api/v1/products/search`) - Enhanced SQL search with relevance scoring
   - Shipping calculations (`/api/v1/shipping/calculate`)
   - Health and debug endpoints (`/health/detailed`, `/db-schema`, `/sqlalchemy-models`)

2. **Service Layer** (`services_async.py`): Async business logic
   - `ChatService`: Manages OpenAI chat completions with persistent conversation history
   - `KnowledgeBaseService`: Handles enhanced SQL search and product retrieval

3. **Data Layer**:
   - `database_async.py`: Manages PostgreSQL connections with async SQLAlchemy
   - `models_modern.py`: Pydantic models for request/response validation
   - `db_models.py`: SQLAlchemy models including Conversation and ConversationMessage

4. **Configuration** (`config_modern.py`): Environment-based settings using Pydantic

## Key Technical Details

- **PostgreSQL Database**: 
  - Async SQLAlchemy with asyncpg driver for all relational data
  - Products, categories, shipping, conversations, and variations
  - Enhanced SQL search with relevance scoring (ChromaDB disabled)
  
- **Multi-Site Support**: Each WooCommerce site isolated by site_id
  
- **Rate Limiting**: Configurable per-minute limits via RATE_LIMIT_PER_MINUTE env var

- **CORS**: Configured to accept all origins by default (adjust for production)

- **Conversation History**: Server-side storage with user_id support for multi-user conversations

- **Shipping Integration**: Parses WooCommerce shipping methods including percentage-based fees

## Environment Variables

Required environment variables (.env file):
- `DATABASE_URL`: PostgreSQL connection string (postgresql://...)
- `OPENAI_API_KEY`: OpenAI API key for chat completions
- `OPENAI_MODEL`: Model to use (default: gpt-4o-mini)
- `OPENAI_TEMPERATURE`: Temperature setting (default: 0.7)
- `OPENAI_MAX_TOKENS`: Max tokens per response (default: 500)
- `CHROMA_PERSIST_DIRECTORY`: ChromaDB directory (currently /tmp/chroma, disabled)
- `API_PORT`: Server port (default: 8000)
- `DEBUG`: Enable/disable debug mode
- `SECRET_KEY`: For session management
- `CORS_ORIGINS`: Comma-separated allowed origins

## Testing Approach

Tests should be placed in the `tests/` directory. The project uses pytest. When adding new features:
- Test API endpoints with FastAPI's TestClient
- Mock external services (OpenAI) for unit tests
- Use fixtures for database setup/teardown

## Test Example

```bash
# Test chat endpoint
curl -X POST https://qrm-chatbot-api-qzgf.onrender.com/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "4kg Mass Loaded Vinyl price? Postcode 3000", "site_name": "store1", "conversation_id": "test123"}'
```

Expected response should include:
- Products array with "Mass Loaded Vinyl (MLV) Acoustic Barrier"
- Price of $209.21 for 4kg Full Roll
- Shipping options: $55.00 Courier or Free Pickup Footscray 3011

## Recent Updates (January 2025)

### **Major Migration & Fixes** (Jan 21, 2025):

1. **Database Migration to Render PostgreSQL**:
   - **Problem**: VentraIP MySQL blocked external connections from Render
   - **Solution**: Migrated entire database to PostgreSQL on Render platform
   - **Changes**: 
     - Updated schema with SERIAL instead of AUTO_INCREMENT
     - Used JSONB for JSON fields
     - All 10 tables migrated with 56 shipping rates, 25 variations
   - **Status**: ✅ Completed, fully operational

2. **Fixed Broken Vector Search**:
   - **Problem**: Chat endpoint returning empty products array
   - **Root Cause**: ChromaDB not working, attempting PostgreSQL instead of MySQL approach
   - **Solution**: Implemented enhanced SQL search matching working sync version
   - **Features**:
     - Multi-field search: name, description, short_description, sku, shipping_class
     - Relevance scoring: name matches = 3x weight, short_description = 2x
     - Word splitting for better query matching
     - Same algorithm as proven working sync version
   - **Status**: ✅ Fixed, products now found correctly

3. **Restored WordPress Plugin Compatibility**:
   - **Problem**: Response format changed, breaking WordPress plugin integration
   - **Solution**: Restored exact response format from old working version
   - **Changes**:
     - Maintained products array with has_variations, variation_count
     - Kept categories and shipping_options arrays
     - Removed new fields that broke compatibility
     - Fixed product variation formatting
   - **Status**: ✅ Backward compatibility restored

4. **Fixed OpenAI Configuration**:
   - **Problem**: Hardcoded OpenAI model instead of using environment config
   - **Solution**: Use settings.openai_model from .env (gpt-4o-mini)
   - **Status**: ✅ Fixed

## Enhanced SQL Search Implementation

The current search system uses **enhanced SQL search** instead of vector embeddings:

```python
# Search algorithm
def _vector_search(site_id, site_name, query, limit):
    # Split query into words
    words = query.lower().split()
    
    # Search multiple fields with relevance scoring:
    # - name: 3x weight
    # - short_description: 2x weight  
    # - description, sku, shipping_class: 1x weight
    
    # Returns results ranked by relevance score
```

**Why SQL instead of ChromaDB?**
- ChromaDB was causing deployment issues on Render
- SQL search proven to work well in production
- Faster response times for this hosting environment
- Easier to debug and maintain

## Database Schema

**Current PostgreSQL Tables** (10 total):
- `sites` (1 row) - Store configurations
- `products` (8 rows) - WooCommerce products
- `product_variations` (25 rows) - Product variants with attributes
- `categories` (2 rows) - Product categories  
- `shipping_zones` (15 rows) - Shipping regions
- `shipping_methods` (17 rows) - Shipping options
- `shipping_classes` (3 rows) - Shipping categories
- `shipping_class_rates` (56 rows) - Class-specific pricing
- `crawl_logs` (2 rows) - Import history
- `product_categories` (0 rows) - Category associations

**Missing Tables** (graceful fallback implemented):
- `conversations` - Chat history storage
- `conversation_messages` - Individual messages

## Conversation Tables Migration

To enable conversation history, run:

```sql
-- Execute add_conversation_tables.sql on PostgreSQL
psql $DATABASE_URL -f add_conversation_tables.sql
```

Or use the Python script:
```bash
python3 create_conversation_tables.py
```

## Deployment (Render Platform)

**Current Setup**:
- Platform: Render (render.com)
- Service Type: Web Service
- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`
- Environment: Python 3.11
- Database: PostgreSQL 15

**Auto-deployment**:
- Deploys automatically on git push to main branch
- Build time: ~2-3 minutes
- Health check: `/health/detailed`

**Manual deployment steps**:
1. Push changes to GitHub main branch
2. Render automatically builds and deploys
3. Monitor deployment logs in Render dashboard
4. Test `/api/v1/chat` endpoint for functionality