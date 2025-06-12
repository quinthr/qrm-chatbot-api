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
    
    def get_shipping_options(self, site_name: str, session: Session, cart_total: float = None) -> List[Dict]:
        """Get shipping options for a site with calculated costs"""
        site = session.query(Site).filter_by(name=site_name).first()
        if not site:
            return []
            
        zones = session.query(ShippingZone).filter_by(site_id=site.id).all()
        shipping_options = []
        
        for zone in zones:
            methods = session.query(ShippingMethod).filter_by(zone_id=zone.id).all()
            for method in methods:
                settings = json.loads(method.settings) if method.settings else {}
                cost_str = str(settings.get("cost", "0"))
                
                # Parse and calculate actual cost
                calculated_cost = self._calculate_shipping_cost(cost_str, cart_total)
                
                shipping_options.append({
                    "method_id": method.method_id,
                    "title": method.title,
                    "cost": calculated_cost,
                    "cost_type": "percentage" if "%" in cost_str else "fixed",
                    "raw_cost": cost_str,  # Keep original for reference
                    "description": settings.get("title", method.method_title)
                })
        
        return shipping_options
    
    def _calculate_shipping_cost(self, cost_str: str, cart_total: float = None) -> str:
        """Calculate actual shipping cost from string that may contain percentage"""
        if not cost_str or cost_str == "0":
            return "$0.00"
        
        # Check if it's a percentage
        if "%" in cost_str:
            if cart_total is None:
                # If no cart total provided, indicate calculation needed
                return "Calculated at checkout"
            
            # Extract percentage value
            percentage = float(cost_str.replace("%", "").strip())
            calculated = (cart_total * percentage) / 100
            return f"${calculated:.2f}"
        else:
            # Fixed cost - ensure proper formatting
            try:
                # Remove any currency symbols and convert to float
                cost_value = float(cost_str.replace("$", "").replace(",", "").strip())
                return f"${cost_value:.2f}"
            except ValueError:
                return cost_str  # Return as-is if can't parse


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
        
        # Extract search terms from message for better product matching
        search_query = self._extract_search_terms(message)
        relevant_products = self.knowledge_base.search_products(site_name, search_query, limit=5)
        
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
    
    def _extract_search_terms(self, message: str) -> str:
        """Extract relevant search terms from user message"""
        message_lower = message.lower()
        
        # Common product-related terms
        product_keywords = [
            'mass loaded vinyl', 'mlv', 'soundproofing', 'acoustic', 'barrier',
            'insulation', 'foam', 'vinyl', 'noise', 'sound', 'pipe', 'lagging',
            'fence', 'wall', 'ceiling', 'underlay', 'carpet', 'foil', '4zero',
            'nuwrap', 'tecsound', 'nuwave'
        ]
        
        # Extract relevant keywords from the message
        found_keywords = []
        for keyword in product_keywords:
            if keyword in message_lower:
                found_keywords.append(keyword)
        
        # If we found specific keywords, use them
        if found_keywords:
            return ' '.join(found_keywords)
        
        # Otherwise, use the original message but remove common question words
        question_words = ['what', 'how', 'much', 'price', 'cost', 'is', 'the', 'of', 'for', 'do', 'you', 'have', 'can', 'i', 'get', 'need', 'want']
        words = message_lower.split()
        filtered_words = [word for word in words if word not in question_words and len(word) > 2]
        
        return ' '.join(filtered_words) if filtered_words else 'soundproofing'
    
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

Important limitations:
- You CANNOT place orders, process payments, or complete transactions
- You CANNOT access customer accounts or order history
- Direct customers to the website to complete their purchase
- Never offer to "place an order" or "help with checkout"

When discussing shipping:
- Always provide specific dollar amounts when available
- If shipping cost shows "Calculated at checkout", explain it will be calculated based on their order total
- Never mention percentages - always translate to dollar amounts or explain the calculation
- Be clear about what affects shipping costs (location, order size, etc.)

When recommending products:
- Explain why the product fits their needs
- Mention key features and benefits
- Include pricing information
- Suggest related or complementary products when appropriate
- Direct them to add items to their cart on the website"""
    
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
                cost_display = option['cost']
                if option.get('cost_type') == 'percentage' and option['cost'] == "Calculated at checkout":
                    cost_display = f"{option['cost']} (percentage-based on cart total)"
                context_parts.append(f"- {option['title']}: {cost_display}")
        
        return "\n".join(context_parts)


# Global service instances
knowledge_base_service = KnowledgeBaseService()
chat_service = ChatService()