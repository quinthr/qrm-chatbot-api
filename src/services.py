import json
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .db_models import Product, Category, Site, ShippingZone, ShippingMethod
from .database import db_manager
from .config import config


class KnowledgeBaseService:
    def __init__(self):
        self.db = db_manager
        
    def search_products(self, site_name: str, query: str, limit: int = 10) -> List[Dict]:
        """Search products using vector similarity"""
        vector_results = self.db.search_products(site_name, query, limit)
        
        products = []
        if vector_results["ids"] and vector_results["ids"][0]:
            with self.db.get_session() as session:
                # Get site
                site = session.query(Site).filter_by(name=site_name).first()
                if not site:
                    return []
                
                # Extract product IDs from vector search
                product_ids = []
                for metadata in vector_results["metadatas"][0]:
                    if "product_id" in metadata:
                        product_ids.append(int(metadata["product_id"]))
                
                # Get product details from database
                if product_ids:
                    db_products = session.query(Product).filter(
                        Product.site_id == site.id,
                        Product.woo_id.in_(product_ids)
                    ).all()
                    
                    # Convert to dict format
                    for product in db_products:
                        products.append({
                            "id": product.woo_id,
                            "name": product.name,
                            "price": product.price,
                            "regular_price": product.regular_price,
                            "sale_price": product.sale_price,
                            "sku": product.sku,
                            "permalink": product.permalink,
                            "description": product.description,
                            "short_description": product.short_description,
                            "stock_status": product.stock_status,
                            "stock_quantity": product.stock_quantity
                        })
        
        return products
    
    def get_product_by_id(self, site_name: str, product_id: int, session: Session) -> Optional[Dict]:
        """Get specific product by ID"""
        site = session.query(Site).filter_by(name=site_name).first()
        if not site:
            return None
            
        product = session.query(Product).filter(
            Product.site_id == site.id,
            Product.woo_id == product_id
        ).first()
        
        if product:
            return {
                "id": product.woo_id,
                "name": product.name,
                "price": product.price,
                "regular_price": product.regular_price,
                "sale_price": product.sale_price,
                "sku": product.sku,
                "permalink": product.permalink,
                "description": product.description,
                "short_description": product.short_description,
                "stock_status": product.stock_status,
                "stock_quantity": product.stock_quantity
            }
        return None
    
    def get_categories(self, site_name: str, session: Session) -> List[Dict]:
        """Get all categories for a site"""
        site = session.query(Site).filter_by(name=site_name).first()
        if not site:
            return []
            
        categories = session.query(Category).filter_by(site_id=site.id).all()
        return [
            {
                "id": cat.woo_id,
                "name": cat.name,
                "slug": cat.slug,
                "description": cat.description
            }
            for cat in categories
        ]
    
    def get_shipping_options(self, site_name: str, session: Session) -> List[Dict]:
        """Get shipping options for a site"""
        site = session.query(Site).filter_by(name=site_name).first()
        if not site:
            return []
            
        zones = session.query(ShippingZone).filter_by(site_id=site.id).all()
        shipping_options = []
        
        for zone in zones:
            methods = session.query(ShippingMethod).filter_by(zone_id=zone.id).all()
            for method in methods:
                settings = json.loads(method.settings) if method.settings else {}
                shipping_options.append({
                    "method_id": method.method_id,
                    "title": method.title,
                    "cost": settings.get("cost", "0"),
                    "description": settings.get("title", method.method_title)
                })
        
        return shipping_options


class ChatService:
    def __init__(self):
        self.knowledge_base = KnowledgeBaseService()
        self.openai_client = OpenAI(api_key=config.openai.api_key)
        
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    def generate_response(self, message: str, site_name: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate chatbot response using OpenAI and knowledge base"""
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Search for relevant products
        relevant_products = self.knowledge_base.search_products(site_name, message, limit=5)
        
        # Get additional context
        with db_manager.get_session() as session:
            categories = self.knowledge_base.get_categories(site_name, session)
            shipping_options = self.knowledge_base.get_shipping_options(site_name, session)
        
        # Build context for OpenAI
        context = self._build_context(message, relevant_products, categories, shipping_options, site_name)
        
        # Generate response with OpenAI
        try:
            response = self.openai_client.chat.completions.create(
                model=config.openai.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(site_name)},
                    {"role": "user", "content": f"Context: {context}\n\nCustomer question: {message}"}
                ],
                temperature=config.openai.temperature,
                max_tokens=config.openai.max_tokens
            )
            
            ai_response = response.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            ai_response = "I'm sorry, I'm having trouble processing your request right now. Please try again later."
            relevant_products = []
        
        return {
            "response": ai_response,
            "products": relevant_products[:3],  # Return top 3 products
            "categories": categories[:5],  # Return top 5 categories
            "shipping_options": shipping_options[:3],  # Return top 3 shipping options
            "conversation_id": conversation_id
        }
    
    def _get_system_prompt(self, site_name: str) -> str:
        """Get system prompt for the chatbot"""
        if site_name == "store1":
            site_info = "Mass Loaded Vinyl - specializing in soundproofing materials and acoustic solutions"
        else:
            site_info = f"Online store ({site_name})"
            
        return f"""You are a helpful customer service assistant for {site_info}.

Your role:
- Help customers find the right products for their needs
- Provide accurate pricing and product information  
- Explain shipping options and costs
- Answer questions about soundproofing and acoustic materials
- Be friendly, professional, and knowledgeable

Guidelines:
- Always use the provided product context when available
- Include specific product names, SKUs, and prices when relevant
- If you don't have specific information, say so and offer to help find it
- Keep responses concise but helpful
- Focus on solving the customer's problem

When recommending products:
- Explain why the product fits their needs
- Mention key features and benefits
- Include pricing information
- Suggest related or complementary products when appropriate"""
    
    def _build_context(self, message: str, products: List[Dict], categories: List[Dict], 
                      shipping_options: List[Dict], site_name: str) -> str:
        """Build context string for OpenAI"""
        context_parts = []
        
        if products:
            context_parts.append("RELEVANT PRODUCTS:")
            for product in products:
                price_info = f"Price: {product['price']}"
                if product.get('sale_price'):
                    price_info = f"Regular: {product['regular_price']}, Sale: {product['sale_price']}"
                
                context_parts.append(
                    f"- {product['name']} (SKU: {product.get('sku', 'N/A')}) - {price_info}\n"
                    f"  Description: {product.get('short_description', 'No description')}\n"
                    f"  Stock: {product.get('stock_status', 'unknown')}\n"
                    f"  Link: {product.get('permalink', 'N/A')}"
                )
        
        if categories:
            context_parts.append("\nAVAILABLE CATEGORIES:")
            for cat in categories[:5]:
                context_parts.append(f"- {cat['name']}: {cat.get('description', 'No description')}")
        
        if shipping_options:
            context_parts.append("\nSHIPPING OPTIONS:")
            for option in shipping_options[:3]:
                context_parts.append(f"- {option['title']}: {option['cost']}")
        
        return "\n".join(context_parts)


# Global service instances
knowledge_base_service = KnowledgeBaseService()
chat_service = ChatService()