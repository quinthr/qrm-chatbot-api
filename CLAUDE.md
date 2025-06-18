# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QRM Chatbot API is a FastAPI-based service that provides AI-powered customer support for WooCommerce sites. It uses OpenAI GPT models for conversations and ChromaDB for semantic product search.

**Production URL**: https://qrm-chatbot-api.com.soundproofingproducts.com.au

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
   - Chat endpoint (`/chat`) - Main conversational AI interface with conversation history
   - Product search (`/search/products`) - Semantic search using embeddings
   - Shipping calculations (`/shipping/calculate`)
   - Site management endpoints

2. **Service Layer** (`services.py`): Business logic
   - `ChatService`: Manages OpenAI chat completions with persistent conversation history
   - `KnowledgeBaseService`: Handles ChromaDB queries and product retrieval

3. **Data Layer**:
   - `database.py`: Manages dual database connections (SQLAlchemy + ChromaDB)
   - `models.py`: Pydantic models for request/response validation
   - `db_models.py`: SQLAlchemy models including Conversation and ConversationMessage

4. **Configuration** (`config.py`): Environment-based settings using Pydantic

## Key Technical Details

- **Dual Database System**: 
  - SQLAlchemy for relational data (products, categories, shipping, conversations)
  - ChromaDB for vector embeddings and semantic search
  
- **Multi-Site Support**: Each WooCommerce site has separate ChromaDB collections
  
- **Rate Limiting**: Configurable per-minute limits via RATE_LIMIT_PER_MINUTE env var

- **CORS**: Configured to accept all origins by default (adjust for production)

- **Conversation History**: Server-side storage with user_id support for multi-user conversations

- **Shipping Integration**: Parses WooCommerce shipping methods including percentage-based fees

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

## Recent Updates (January 2025)

0. **Shipping Cost & Database Fixes** (Latest - Jan 18, 2025):
   - Fixed shipping cost extraction from ShippingClassRate table for no-class rates
   - Added database connection pooling to prevent OperationalError issues
   - Improved error handling to extract underlying errors from RetryError
   - Added debug logging for shipping zone and method discovery
   - Now correctly handles fee format: [fee percent="16" min_fee="55" max_fee="120"]

1. **Product Variations Fix** (Jan 18, 2025):
   - Fixed API to properly parse variation attributes from JSON string stored in database
   - Added comprehensive variation data including SKU, prices, stock, dimensions
   - Handles both list format (WooCommerce standard) and dict format for attributes
   - Variations now display correctly in chat context with all attribute details

## Previous Updates

1. **Shipping Class Rates Integration** (Latest - Jan 17, 2025):
   - Added `ShippingClassRate` model for product-specific shipping costs
   - Implemented `get_shipping_options_for_products()` method
   - ChatService now automatically uses product-aware shipping when products are found
   - Uses highest applicable rate when multiple shipping classes apply
   - Added `_extract_numeric_cost()` helper for robust cost parsing

2. **Product Display Enhancements**:
   - Product URLs now clickable using HTML anchor tags (`<a href="URL">text</a>`)
   - Variable products show "from" pricing (e.g., "from $122.59")
   - Fixed shipping method titles to show proper names like "Free Pickup Footscray 3011"
   - Simple variation support with price and attributes only

3. **Error Handling Improvements**:
   - Fixed AttributeError issues with safe attribute access using `getattr()`
   - Comprehensive error handling for NULL/empty database values
   - Robust variation processing to prevent API crashes

4. **Conversation History**: Added server-side storage of chat history
   - Run migration: `python create_conversation_tables.py`
   - Stores last 10 messages per conversation_id
   - Supports user_id for multi-user tracking

5. **Shipping Cost Parsing**: Fixed WooCommerce format handling
   - Handles `[fee percent="X" min_fee="Y" max_fee="Z"]` format
   - Uses shipping method title from settings
   - Properly displays labels like "Free Pickup Footscray 3011"

6. **Known Issues**:
   - VentraIP hosting may return 503 errors under load
   - Monitor resource usage in cPanel
   - Consider caching for performance optimization

## Deployment

1. Pull latest changes on production server
2. Run database migrations if needed
3. Restart application via cPanel Python app interface
4. Monitor logs for any errors