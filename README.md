# QRM Chatbot API

FastAPI-based chatbot service for WooCommerce sites with AI-powered customer support. Provides intelligent product recommendations, pricing information, and shipping calculations through natural language conversations.

## 🚀 Features

- **🤖 AI-Powered Chat**: OpenAI GPT integration for natural conversations
- **🔍 Semantic Search**: Vector-based product search with ChromaDB
- **🛒 Product Recommendations**: Context-aware product suggestions
- **💰 Dynamic Pricing**: Real-time price and inventory information
- **🚚 Shipping Calculator**: Automated shipping cost calculations
- **🏪 Multi-Site Support**: Handle multiple WooCommerce stores
- **📊 Analytics & Monitoring**: Health checks and usage statistics
- **🔐 Security**: CORS, rate limiting, and API authentication

## 📋 Prerequisites

- Python 3.12+
- [QRM Knowledge Base](https://github.com/your-username/qrm-chatbot-knowledge-base) (running)
- OpenAI API key
- Access to crawled WooCommerce data

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/your-username/qrm-chatbot-api.git
cd qrm-chatbot-api
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration
```bash
cp .env.example .env
# Edit .env with your settings
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database Configuration (same as knowledge base)
DATABASE_URL=sqlite:///path/to/knowledge-base/data/products.db
CHROMA_PERSIST_DIRECTORY=path/to/knowledge-base/data/chroma

# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=500

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# Security
SECRET_KEY=your-secret-key-change-this-in-production
CORS_ORIGINS=https://massloadedvinyl.com.au,https://soundproofingproducts.com.au

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

## 🚀 Usage

### Start the API Server
```bash
python main.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/

### Production Deployment
```bash
# With Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# With Docker
docker build -t qrm-chatbot-api .
docker run -p 8000:8000 --env-file .env qrm-chatbot-api
```

## 📡 API Endpoints

### Chat Endpoints

#### POST `/chat`
Main chatbot conversation endpoint.

```bash
curl -X POST "http://localhost:8000/chat" \
-H "Content-Type: application/json" \
-d '{
  "message": "I need soundproofing for my home office",
  "site_name": "store1",
  "conversation_id": "optional-uuid"
}'
```

**Response:**
```json
{
  "response": "For a home office, I recommend our Mass Loaded Vinyl barrier...",
  "products": [
    {
      "id": 123,
      "name": "Mass Loaded Vinyl 1lb",
      "price": "$2.50",
      "permalink": "https://site.com/product/mlv-1lb"
    }
  ],
  "conversation_id": "uuid-string",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### POST `/search/products`
Search products by query.

```bash
curl -X POST "http://localhost:8000/search/products" \
-H "Content-Type: application/json" \
-d '{
  "query": "acoustic foam",
  "site_name": "store1",
  "limit": 5
}'
```

### Management Endpoints

#### GET `/`
Health check and system status.

```bash
curl http://localhost:8000/
```

#### GET `/sites`
List all available sites.

```bash
curl http://localhost:8000/sites
```

#### GET `/sites/{site_name}/stats`
Get statistics for a specific site.

```bash
curl http://localhost:8000/sites/store1/stats
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WordPress     │    │   FastAPI        │    │   Knowledge     │
│    Plugin       │───▶│     API          │───▶│     Base        │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          │
┌─────────────────┐           │                          │
│    OpenAI       │◀──────────┘                          │
│     API         │                                      │
└─────────────────┘                                      │
                                                         │
┌─────────────────┐    ┌──────────────────┐             │
│   ChromaDB      │◀───│    Vector        │◀────────────┘
│   Vectors       │    │    Search        │              
└─────────────────┘    └──────────────────┘              
                                                         
┌─────────────────┐    ┌──────────────────┐             │
│   MySQL/SQLite  │◀───│   Product        │◀────────────┘
│   Database      │    │   Data           │
└─────────────────┘    └──────────────────┘
```

## 🤖 AI Features

### Conversation Management
- **Context Awareness**: Maintains conversation history
- **Product Knowledge**: Deep understanding of catalog
- **Intent Recognition**: Identifies customer needs
- **Recommendation Engine**: Suggests relevant products

### Customization
- **Brand Voice**: Configurable personality per site
- **Product Categories**: Specialized knowledge areas
- **Pricing Rules**: Dynamic pricing and promotions
- **Shipping Logic**: Location-based calculations

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Code Structure
```
src/
├── config.py        # Configuration management
├── database.py      # Database connections
├── models.py        # Pydantic models
└── services.py      # Business logic
```

### Adding New Features
1. Define Pydantic models in `models.py`
2. Implement business logic in `services.py`
3. Add endpoints in `main.py`
4. Update documentation

### Debugging
```bash
# Enable debug mode
export API_DEBUG=true

# Verbose logging
python main.py --log-level debug
```

## 📊 Monitoring

### Health Checks
- Database connectivity
- ChromaDB status
- OpenAI API availability
- Memory and performance metrics

### Logging
- Request/response logging
- Error tracking
- Performance monitoring
- Usage analytics

### Metrics
- Chat conversation rates
- Product recommendation accuracy
- Response times
- Error rates

## 🚀 Deployment

### Production Checklist
- [ ] Set `API_DEBUG=false`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up SSL/HTTPS
- [ ] Configure rate limiting
- [ ] Set up monitoring
- [ ] Configure log rotation
- [ ] Set up backup strategy

### Environment Setup
```bash
# Production environment variables
export API_DEBUG=false
export SECRET_KEY="your-production-secret-key"
export CORS_ORIGINS="https://yourdomain.com"
export DATABASE_URL="mysql://user:pass@host/db"
```

### Docker Deployment
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-api-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔌 Integration

### WordPress Plugin Integration
```javascript
// Example chat widget integration
fetch('https://your-api.com/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: userMessage,
    site_name: 'store1'
  })
})
.then(response => response.json())
.then(data => {
  displayChatResponse(data.response);
  showProductRecommendations(data.products);
});
```

### Webhook Integration
```bash
# Set up webhooks for real-time updates
curl -X POST "https://your-api.com/webhooks/product-update" \
-H "Content-Type: application/json" \
-d '{"product_id": 123, "action": "updated"}'
```

## 🔗 Related Projects

- **[QRM Knowledge Base](https://github.com/your-username/qrm-chatbot-knowledge-base)** - WooCommerce data crawler
- **QRM WordPress Plugin** - Frontend chat widget (coming soon)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/qrm-chatbot-api/issues)
- **Documentation**: [API Documentation](http://your-api.com/docs)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/qrm-chatbot-api/discussions)