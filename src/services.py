import json
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .db_models import Product, Category, Site, ShippingZone, ShippingMethod, Conversation, ConversationMessage, ProductVariation
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
                        # Check if product has variations
                        variations = session.query(ProductVariation).filter_by(
                            site_id=site.id, 
                            product_id=product.id
                        ).all()
                        
                        # Format price with "from" if it has variations
                        price_display = product.price
                        if variations and product.price:
                            price_display = f"from {product.price}"
                        
                        products.append({
                            "id": product.woo_id,
                            "name": product.name,
                            "price": price_display,
                            "regular_price": product.regular_price,
                            "sale_price": product.sale_price,
                            "sku": product.sku,
                            "permalink": product.permalink,
                            "description": product.description,
                            "short_description": product.short_description,
                            "stock_status": product.stock_status,
                            "stock_quantity": product.stock_quantity,
                            "has_variations": len(variations) > 0
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
            # Check if product has variations
            variations = session.query(ProductVariation).filter_by(
                site_id=site.id, 
                product_id=product.id
            ).all()
            
            # Format price with "from" if it has variations
            price_display = product.price
            if variations and product.price:
                price_display = f"from {product.price}"
            
            return {
                "id": product.woo_id,
                "name": product.name,
                "price": price_display,
                "regular_price": product.regular_price,
                "sale_price": product.sale_price,
                "sku": product.sku,
                "permalink": product.permalink,
                "description": product.description,
                "short_description": product.short_description,
                "stock_status": product.stock_status,
                "stock_quantity": product.stock_quantity,
                "has_variations": len(variations) > 0
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
                
                # Extract cost from WooCommerce settings structure
                cost_value = "0"
                if isinstance(settings.get("cost"), dict):
                    # Handle WooCommerce settings object format
                    cost_value = settings["cost"].get("value", "0")
                elif "cost" in settings:
                    # Handle direct cost value
                    cost_value = str(settings["cost"])
                
                # Parse and calculate actual cost
                calculated_cost = self._calculate_shipping_cost(cost_value, cart_total)
                
                # Determine cost type
                cost_type = "percentage" if ("%" in cost_value or "percent" in cost_value) else "fixed"
                
                # Use the direct title from the database (contains proper names like "Free Pickup Footscray 3011")
                shipping_label = method.title
                
                shipping_options.append({
                    "method_id": method.method_id,
                    "title": shipping_label,
                    "cost": calculated_cost,
                    "cost_type": cost_type,
                    "raw_cost": cost_value,  # Keep original for reference
                    "description": shipping_label
                })
        
        return shipping_options
    
    def _calculate_shipping_cost(self, cost_str: str, cart_total: float = None) -> str:
        """Calculate actual shipping cost from string that may contain percentage"""
        if not cost_str or cost_str == "0":
            return "$0.00"
        
        # Handle WooCommerce fee format: [fee percent="14" min_fee="30" max_fee="75"]
        if cost_str.startswith("[fee ") and cost_str.endswith("]"):
            # Parse the fee string
            import re
            percent_match = re.search(r'percent="([^"]+)"', cost_str)
            min_fee_match = re.search(r'min_fee="([^"]+)"', cost_str)
            max_fee_match = re.search(r'max_fee="([^"]+)"', cost_str)
            
            if percent_match:
                percentage = float(percent_match.group(1))
                min_fee = float(min_fee_match.group(1)) if min_fee_match else 0
                max_fee = float(max_fee_match.group(1)) if max_fee_match else float('inf')
                
                if cart_total is None:
                    return f"${min_fee:.2f} - ${max_fee:.2f}" if max_fee != float('inf') else f"From ${min_fee:.2f}"
                
                # Calculate percentage-based fee
                calculated = (cart_total * percentage) / 100
                # Apply min/max constraints
                calculated = max(calculated, min_fee)
                if max_fee != float('inf'):
                    calculated = min(calculated, max_fee)
                
                return f"${calculated:.2f}"
        
        # Check if it's a simple percentage
        if "%" in cost_str:
            if cart_total is None:
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
    def generate_response(self, message: str, site_name: str, conversation_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate chatbot response using OpenAI and knowledge base"""
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        with db_manager.get_session() as session:
            # Get site
            site = session.query(Site).filter_by(name=site_name).first()
            if not site:
                raise ValueError(f"Site '{site_name}' not found")
            
            # Get or create conversation
            conversation = session.query(Conversation).filter_by(conversation_id=conversation_id).first()
            if not conversation:
                conversation = Conversation(
                    site_id=site.id,
                    conversation_id=conversation_id,
                    user_id=user_id
                )
                session.add(conversation)
                session.flush()  # Get the ID
            
            # Get conversation history (last 10 messages)
            conversation_history = session.query(ConversationMessage)\
                .filter_by(conversation_id=conversation_id)\
                .order_by(ConversationMessage.created_at)\
                .limit(10)\
                .all()
            
            # Store user message
            user_message = ConversationMessage(
                conversation_id=conversation_id,
                role="user",
                content=message
            )
            session.add(user_message)
            
            # Extract search terms from message for better product matching
            search_query = self._extract_search_terms(message)
            relevant_products = self.knowledge_base.search_products(site_name, search_query, limit=5)
            
            # Get additional context
            categories = self.knowledge_base.get_categories(site_name, session)
            shipping_options = self.knowledge_base.get_shipping_options(site_name, session)
            
            # Build context for OpenAI
            context = self._build_context(message, relevant_products, categories, shipping_options, site_name)
            
            # Build conversation messages for OpenAI
            openai_messages = [{"role": "system", "content": self._get_system_prompt(site_name)}]
            
            # Add conversation history
            for hist_msg in conversation_history:
                openai_messages.append({
                    "role": hist_msg.role,
                    "content": hist_msg.content
                })
            
            # Add current message with context
            openai_messages.append({
                "role": "user",
                "content": f"Context: {context}\n\nCustomer question: {message}"
            })
            
            # Generate response with OpenAI
            try:
                response = self.openai_client.chat.completions.create(
                    model=config.openai.model,
                    messages=openai_messages,
                    temperature=config.openai.temperature,
                    max_tokens=config.openai.max_tokens
                )
                
                ai_response = response.choices[0].message.content
                
                # Store assistant response
                assistant_message = ConversationMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=ai_response
                )
                session.add(assistant_message)
                session.commit()
                
            except Exception as e:
                print(f"OpenAI API error: {e}")
                ai_response = "I'm sorry, I'm having trouble processing your request right now. Please try again later."
                relevant_products = []
                session.rollback()
        
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
- Include pricing information exactly as provided (if price shows "from $X" then use "from $X")
- For variable products, explain that multiple options/sizes are available and pricing starts from the quoted amount
- Always provide the product page link as a clickable hyperlink
- Format links as: <a href="URL">Click here</a> or <a href="URL">product name</a>
- Suggest related or complementary products when appropriate
- Direct them to visit the product page to see all options and add items to their cart"""
    
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