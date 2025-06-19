"""
Async services for chat and knowledge base operations
"""
import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from openai import AsyncOpenAI
import chromadb

from .db_models import (
    Product, ProductVariation, Category, Site, 
    ShippingZone, ShippingMethod, ShippingClass, ShippingClassRate,
    Conversation, ConversationMessage
)
from .models_modern import (
    ChatResponse, ProductResponse, ProductVariation as ProductVariationModel,
    ShippingOption, MessageRole
)
from .database_async import Database

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    """Async service for product search and retrieval"""
    
    def __init__(self, db: Database):
        self.db = db
        self.openai_client = AsyncOpenAI()
    
    async def search_products(
        self, 
        site_name: str, 
        query: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search products using vector similarity"""
        
        # Get site
        async with self.db.get_session() as session:
            site_stmt = select(Site).where(Site.name == site_name)
            result = await session.execute(site_stmt)
            site = result.scalar_one_or_none()
            
            if not site:
                logger.warning(f"Site not found: {site_name}")
                return []
        
        # Try vector search first
        products = await self._vector_search(site.id, site_name, query, limit)
        
        # Fallback to SQL search if no results
        if not products:
            products = await self._sql_search(site.id, query, limit)
        
        return products
    
    async def _vector_search(
        self, 
        site_id: int,
        site_name: str,
        query: str, 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search using ChromaDB vectors"""
        try:
            # Generate query embedding
            response = await self.openai_client.embeddings.create(
                input=query,
                model="text-embedding-3-small"
            )
            query_embedding = response.data[0].embedding
            
            # Search in ChromaDB
            results = await self.db.search_vectors(
                collection_name=f"{site_name}_products",
                query_embedding=query_embedding,
                filter_dict={"site_id": site_id},
                n_results=limit
            )
            
            if not results["ids"][0]:
                return []
            
            # Get full product details
            product_ids = [int(m["product_id"]) for m in results["metadatas"][0]]
            return await self._get_products_by_ids(site_id, product_ids)
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def _sql_search(
        self, 
        site_id: int,
        query: str, 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback SQL search"""
        async with self.db.get_session() as session:
            # Search in name and description
            stmt = select(Product).where(
                and_(
                    Product.site_id == site_id,
                    or_(
                        Product.name.ilike(f"%{query}%"),
                        Product.description.ilike(f"%{query}%"),
                        Product.short_description.ilike(f"%{query}%")
                    )
                )
            ).limit(limit)
            
            result = await session.execute(stmt)
            products = result.scalars().all()
            
            return [await self._format_product(p) for p in products]
    
    async def _get_products_by_ids(
        self, 
        site_id: int,
        product_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """Get products by IDs with variations"""
        async with self.db.get_session() as session:
            stmt = select(Product).options(
                selectinload(Product.variations)
            ).where(
                and_(
                    Product.site_id == site_id,
                    Product.woo_id.in_(product_ids)
                )
            )
            
            result = await session.execute(stmt)
            products = result.scalars().all()
            
            return [await self._format_product(p) for p in products]
    
    async def _format_product(self, product: Product) -> Dict[str, Any]:
        """Format product for response"""
        # Parse variations
        variations = []
        if product.variations:
            for var in product.variations:
                try:
                    attrs = json.loads(var.attributes) if var.attributes else {}
                    variations.append({
                        "id": var.id,
                        "sku": var.sku,
                        "price": var.price,
                        "regular_price": var.regular_price,
                        "sale_price": var.sale_price,
                        "attributes": attrs,
                        "stock_quantity": var.stock_quantity,
                        "stock_status": var.stock_status
                    })
                except:
                    pass
        
        # Determine display price
        if variations:
            prices = [float(v["price"]) for v in variations if v["price"]]
            min_price = min(prices) if prices else product.price
            price_display = f"from ${min_price:.2f}"
        else:
            price_display = f"${float(product.price):.2f}" if product.price else "Price on request"
        
        return {
            "id": product.id,
            "woo_id": product.woo_id,
            "name": product.name,
            "slug": product.slug,
            "permalink": product.permalink,
            "type": product.type,
            "description": product.description,
            "short_description": product.short_description,
            "sku": product.sku,
            "price": price_display,
            "regular_price": product.regular_price,
            "sale_price": product.sale_price,
            "stock_status": product.stock_status,
            "stock_quantity": product.stock_quantity,
            "variations": variations,
            "shipping_class": product.shipping_class,
            "weight": product.weight
        }
    
    async def get_shipping_options_for_products(
        self,
        site_name: str,
        product_ids: List[int],
        postcode: Optional[str] = None
    ) -> List[ShippingOption]:
        """Calculate shipping for products"""
        async with self.db.get_session() as session:
            # Get site
            site_stmt = select(Site).where(Site.name == site_name)
            site_result = await session.execute(site_stmt)
            site = site_result.scalar_one_or_none()
            
            if not site:
                return []
            
            # Get products with shipping classes
            products_stmt = select(Product).where(
                and_(
                    Product.site_id == site.id,
                    Product.woo_id.in_(product_ids)
                )
            )
            products_result = await session.execute(products_stmt)
            products = products_result.scalars().all()
            
            # Get shipping zones and methods
            zones_stmt = select(ShippingZone).options(
                selectinload(ShippingZone.methods)
            ).where(ShippingZone.site_id == site.id)
            
            zones_result = await session.execute(zones_stmt)
            zones = zones_result.scalars().all()
            
            # Calculate shipping options
            shipping_options = []
            for zone in zones:
                # Check if postcode matches zone
                if postcode and not self._postcode_matches_zone(postcode, zone):
                    continue
                
                for method in zone.methods:
                    cost = await self._calculate_method_cost(
                        session, method, products
                    )
                    
                    if cost is not None:
                        shipping_options.append(ShippingOption(
                            method_id=f"{zone.id}_{method.id}",
                            method_title=method.method_title,
                            cost=cost,
                            description=method.settings.get("description")
                        ))
            
            return shipping_options
    
    def _postcode_matches_zone(self, postcode: str, zone: ShippingZone) -> bool:
        """Check if postcode matches shipping zone"""
        # Simple implementation - enhance based on zone location data
        if not zone.locations:
            return True  # Zone applies to all locations
        
        # Parse zone locations (stored as JSON)
        try:
            locations = json.loads(zone.locations) if zone.locations else []
            # Implement postcode matching logic
            return True  # Simplified for now
        except:
            return True
    
    async def _calculate_method_cost(
        self,
        session,
        method: ShippingMethod,
        products: List[Product]
    ) -> Optional[float]:
        """Calculate shipping cost for method and products"""
        try:
            # Get base cost from method settings
            settings = json.loads(method.settings) if method.settings else {}
            base_cost = float(settings.get("cost", 0))
            
            # Get shipping class rates
            shipping_classes = set(p.shipping_class for p in products if p.shipping_class)
            
            if shipping_classes:
                # Get highest rate for shipping classes
                rates_stmt = select(ShippingClassRate).where(
                    and_(
                        ShippingClassRate.shipping_method_id == method.id,
                        ShippingClassRate.shipping_class_id.in_(
                            select(ShippingClass.id).where(
                                ShippingClass.slug.in_(shipping_classes)
                            )
                        )
                    )
                )
                rates_result = await session.execute(rates_stmt)
                rates = rates_result.scalars().all()
                
                if rates:
                    # Use highest rate
                    class_costs = [self._parse_cost(r.cost) for r in rates]
                    return max(class_costs)
            
            return base_cost
            
        except Exception as e:
            logger.error(f"Error calculating shipping cost: {e}")
            return None
    
    def _parse_cost(self, cost_string: str) -> float:
        """Parse WooCommerce cost string"""
        if not cost_string:
            return 0.0
        
        # Handle percentage fees like [fee percent="16" min_fee="55" max_fee="120"]
        if "[fee" in cost_string:
            # Extract min_fee as the cost
            import re
            min_fee_match = re.search(r'min_fee="(\d+\.?\d*)"', cost_string)
            if min_fee_match:
                return float(min_fee_match.group(1))
        
        # Try to extract numeric value
        try:
            # Remove non-numeric characters except decimal point
            numeric_str = ''.join(c for c in cost_string if c.isdigit() or c == '.')
            return float(numeric_str) if numeric_str else 0.0
        except:
            return 0.0


class ChatService:
    """Async service for chat interactions"""
    
    def __init__(self, db: Database, kb_service: KnowledgeBaseService):
        self.db = db
        self.kb_service = kb_service
        self.openai_client = AsyncOpenAI()
    
    async def get_response(
        self,
        message: str,
        site_name: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ChatResponse:
        """Get AI chat response"""
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"qrm_{uuid.uuid4().hex[:12]}"
        
        # Get conversation history (gracefully handle missing tables)
        try:
            history = await self._get_or_create_conversation(
                conversation_id, site_name, user_id
            )
        except Exception as e:
            logger.warning(f"Conversation history disabled due to missing tables: {e}")
            history = []
        
        # Save user message (gracefully handle missing tables)
        try:
            await self._save_message(
                conversation_id, MessageRole.USER, message
            )
        except Exception as e:
            logger.warning(f"Message saving disabled due to missing tables: {e}")
        
        # Extract search terms and search for products
        search_terms = await self._extract_search_terms(message)
        products = []
        
        if search_terms:
            for term in search_terms[:3]:  # Limit to 3 searches
                found_products = await self.kb_service.search_products(
                    site_name, term, limit=5
                )
                products.extend(found_products)
        
        # Build context
        context = await self._build_context(
            site_name, products, message
        )
        
        # Get AI response
        ai_response = await self._get_ai_response(
            message, history, context
        )
        
        # Save AI response (gracefully handle missing tables)
        try:
            await self._save_message(
                conversation_id, MessageRole.ASSISTANT, ai_response
            )
        except Exception as e:
            logger.warning(f"AI response saving disabled due to missing tables: {e}")
        
        # Get categories and format products for backward compatibility
        categories = await self._get_categories(site_name)
        
        # Format products to match old structure with variations
        formatted_products = await self._format_products_with_variations(products[:3], site_name)
        
        # Get shipping options based on found products
        shipping_options = []
        if products:
            shipping_options = await self._get_shipping_options_for_products(
                site_name, products, message
            )
        else:
            shipping_options = await self._get_default_shipping_options(site_name)
        
        # Format response to match old structure exactly
        return ChatResponse(
            response=ai_response,
            conversation_id=conversation_id,
            products=formatted_products,
            categories=categories,
            shipping_options=shipping_options[:3]  # Limit to 3 options
        )
    
    async def _get_or_create_conversation(
        self,
        conversation_id: str,
        site_name: str,
        user_id: Optional[str]
    ) -> List[Dict[str, str]]:
        """Get or create conversation and return history"""
        async with self.db.get_session() as session:
            # Get site
            site_stmt = select(Site).where(Site.name == site_name)
            site_result = await session.execute(site_stmt)
            site = site_result.scalar_one_or_none()
            
            if not site:
                raise ValueError(f"Site not found: {site_name}")
            
            # Get or create conversation
            conv_stmt = select(Conversation).where(
                Conversation.conversation_id == conversation_id
            )
            conv_result = await session.execute(conv_stmt)
            conversation = conv_result.scalar_one_or_none()
            
            if not conversation:
                conversation = Conversation(
                    conversation_id=conversation_id,
                    site_id=site.id,
                    user_id=user_id,
                    created_at=datetime.utcnow()
                )
                session.add(conversation)
                await session.commit()
                return []
            
            # Get message history
            messages_stmt = select(ConversationMessage).where(
                ConversationMessage.conversation_id == conversation.id
            ).order_by(ConversationMessage.created_at).limit(10)
            
            messages_result = await session.execute(messages_stmt)
            messages = messages_result.scalars().all()
            
            return [
                {"role": m.role, "content": m.content}
                for m in messages
            ]
    
    async def _save_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ):
        """Save message to conversation history"""
        async with self.db.get_session() as session:
            # Get conversation
            conv_stmt = select(Conversation).where(
                Conversation.conversation_id == conversation_id
            )
            conv_result = await session.execute(conv_stmt)
            conversation = conv_result.scalar_one()
            
            # Create message
            message = ConversationMessage(
                conversation_id=conversation.id,
                role=role,
                content=content,
                created_at=datetime.utcnow()
            )
            session.add(message)
            await session.commit()
    
    async def _extract_search_terms(self, message: str) -> List[str]:
        """Extract product search terms from message"""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract product search terms from the user message. Return as JSON array of strings."
                    },
                    {"role": "user", "content": message}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            terms = json.loads(response.choices[0].message.content)
            return terms if isinstance(terms, list) else []
            
        except:
            return []
    
    async def _build_context(
        self,
        site_name: str,
        products: List[Dict],
        message: str
    ) -> str:
        """Build context for AI response"""
        context_parts = []
        
        # Add product context
        if products:
            context_parts.append("Found Products:")
            for p in products[:5]:
                context_parts.append(
                    f"- {p['name']}: {p['price']} "
                    f"({'in stock' if p['stock_status'] == 'instock' else 'out of stock'})"
                )
        
        # Add shipping info if postcode mentioned
        postcode = self._extract_postcode(message)
        if postcode and products:
            product_ids = [p['woo_id'] for p in products[:3]]
            shipping_options = await self.kb_service.get_shipping_options_for_products(
                site_name, product_ids, postcode
            )
            
            if shipping_options:
                context_parts.append(f"\nShipping to {postcode}:")
                for opt in shipping_options[:3]:
                    context_parts.append(f"- {opt.method_title}: ${opt.cost:.2f}")
        
        return "\n".join(context_parts)
    
    async def _get_ai_response(
        self,
        message: str,
        history: List[Dict],
        context: str
    ) -> str:
        """Get AI response from OpenAI"""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful customer service assistant for an online store. "
                    "Provide accurate, friendly responses based on the product information provided. "
                    "Use HTML <a> tags for product links."
                )
            }
        ]
        
        # Add history
        messages.extend(history[-5:])  # Last 5 messages
        
        # Add context and current message
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        
        messages.append({"role": "user", "content": message})
        
        # Get response
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def _extract_postcode(self, message: str) -> Optional[str]:
        """Extract Australian postcode from message"""
        import re
        # Australian postcode pattern
        match = re.search(r'\b\d{4}\b', message)
        return match.group(0) if match else None
    
    def _generate_suggestions(self, products: List[Dict]) -> List[str]:
        """Generate suggested actions based on products"""
        suggestions = []
        
        if products:
            suggestions.append("View product details")
            suggestions.append("Check availability")
            suggestions.append("Calculate shipping")
        else:
            suggestions.append("Browse categories")
            suggestions.append("Search for products")
        
        return suggestions[:3]
    
    async def _format_products_with_variations(self, products: List[Dict], site_name: str) -> List[Dict[str, Any]]:
        """Format products with variations to match old response structure"""
        formatted_products = []
        
        try:
            async with self.db.get_session() as session:
                for product in products:
                    # Get product with variations
                    prod_stmt = select(Product).options(
                        selectinload(Product.variations)
                    ).where(Product.id == product['id'])
                    
                    prod_result = await session.execute(prod_stmt)
                    prod = prod_result.scalar_one_or_none()
                    
                    if not prod:
                        continue
                    
                    # Format variations
                    variations = []
                    has_variations = len(prod.variations) > 0
                    
                    for var in prod.variations:
                        # Parse attributes
                        var_attributes = []
                        if var.attributes:
                            try:
                                attrs = json.loads(var.attributes) if isinstance(var.attributes, str) else var.attributes
                                if isinstance(attrs, list):
                                    var_attributes = attrs
                                elif isinstance(attrs, dict):
                                    var_attributes = [{"name": k, "option": v} for k, v in attrs.items()]
                            except:
                                pass
                        
                        variations.append({
                            "id": var.woo_id,
                            "sku": var.sku or prod.sku,
                            "price": var.price or "0",
                            "regular_price": var.regular_price or "",
                            "sale_price": var.sale_price or "",
                            "stock_quantity": var.stock_quantity,
                            "stock_status": var.stock_status or "instock",
                            "weight": var.weight or "",
                            "dimensions": {
                                "length": var.dimensions_length or "",
                                "width": var.dimensions_width or "",
                                "height": var.dimensions_height or ""
                            },
                            "attributes": var_attributes
                        })
                    
                    # Calculate price display
                    if has_variations and variations:
                        prices = [float(v['price']) for v in variations if v['price'] and v['price'] != "0"]
                        if prices:
                            min_price = min(prices)
                            display_price = f"from {min_price:.2f}"
                        else:
                            display_price = prod.price or "0"
                    else:
                        display_price = prod.price or "0"
                    
                    formatted_products.append({
                        "id": prod.woo_id,
                        "name": prod.name,
                        "price": display_price,
                        "price_range": None,  # Could calculate if needed
                        "regular_price": prod.regular_price or "",
                        "sale_price": prod.sale_price or "",
                        "sku": prod.sku or "",
                        "permalink": prod.permalink or "",
                        "description": prod.description or "",
                        "short_description": prod.short_description or "",
                        "stock_status": prod.stock_status or "instock",
                        "stock_quantity": prod.stock_quantity,
                        "has_variations": has_variations,
                        "variations": variations,
                        "variation_count": len(variations)
                    })
                    
        except Exception as e:
            logger.error(f"Error formatting products: {e}")
            # Return basic format if detailed formatting fails
            return products[:3]
            
        return formatted_products
    
    async def _get_shipping_options_for_products(
        self, 
        site_name: str, 
        products: List[Dict],
        message: str
    ) -> List[Dict[str, Any]]:
        """Get shipping options based on products in cart"""
        import re
        
        # Extract postcode from message if present
        postcode = None
        postcode_match = re.search(r'\b(\d{4})\b', message)
        if postcode_match:
            postcode = postcode_match.group(1)
        
        try:
            async with self.db.get_session() as session:
                # Get site
                site_stmt = select(Site).where(Site.name == site_name)
                site_result = await session.execute(site_stmt)
                site = site_result.scalar_one_or_none()
                
                if not site:
                    return []
                
                # Get product IDs
                product_ids = [p['id'] for p in products]
                
                # Get shipping options using the existing method
                shipping_options = await self.kb_service.get_shipping_options_for_products(
                    site_name, product_ids, postcode
                )
                
                # Format for response
                formatted_options = []
                for option in shipping_options:
                    # Determine cost display
                    cost = option.cost
                    if isinstance(cost, (int, float)):
                        display_cost = f"${cost:.2f}"
                        cost_type = "fixed" if cost > 0 else "free"
                    else:
                        display_cost = str(cost)
                        cost_type = "variable"
                    
                    formatted_options.append({
                        "method_id": option.method_id.split('_')[1] if '_' in option.method_id else option.method_id,
                        "title": option.method_title,
                        "cost": display_cost,
                        "cost_type": cost_type,
                        "raw_cost": str(cost),
                        "description": option.method_title
                    })
                
                return formatted_options
                
        except Exception as e:
            logger.error(f"Error getting shipping options for products: {e}")
            return await self._get_default_shipping_options(site_name)
    
    async def _get_categories(self, site_name: str) -> List[Dict[str, Any]]:
        """Get all categories for a site"""
        try:
            async with self.db.get_session() as session:
                # Get site
                site_stmt = select(Site).where(Site.name == site_name)
                site_result = await session.execute(site_stmt)
                site = site_result.scalar_one_or_none()
                
                if not site:
                    return []
                
                # Get categories
                cat_stmt = select(Category).where(Category.site_id == site.id)
                cat_result = await session.execute(cat_stmt)
                categories = cat_result.scalars().all()
                
                return [
                    {
                        "id": cat.woo_id,
                        "name": cat.name,
                        "slug": cat.slug or "",
                        "description": cat.description or ""
                    }
                    for cat in categories
                ]
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    async def _get_default_shipping_options(self, site_name: str) -> List[Dict[str, Any]]:
        """Get default shipping options for a site"""
        try:
            async with self.db.get_session() as session:
                # Get site
                site_stmt = select(Site).where(Site.name == site_name)
                site_result = await session.execute(site_stmt)
                site = site_result.scalar_one_or_none()
                
                if not site:
                    return []
                
                # Get shipping zones with methods
                zones_stmt = select(ShippingZone).options(
                    selectinload(ShippingZone.methods)
                ).where(ShippingZone.site_id == site.id)
                
                zones_result = await session.execute(zones_stmt)
                zones = zones_result.scalars().all()
                
                shipping_options = []
                for zone in zones[:3]:  # Limit to first 3 zones
                    for method in zone.methods:
                        if not method.enabled:
                            continue
                            
                        # Parse cost from settings
                        settings = json.loads(method.settings) if method.settings else {}
                        cost = settings.get("cost", "0")
                        
                        # Determine cost type and display
                        if "[fee" in str(cost):
                            cost_type = "percentage"
                            display_cost = self._extract_fee_range(cost)
                        elif cost and cost != "0":
                            cost_type = "fixed"
                            display_cost = f"${cost}"
                        else:
                            cost_type = "fixed"
                            display_cost = "$0.00"
                        
                        shipping_options.append({
                            "method_id": method.method_id,
                            "title": method.title or method.method_title,
                            "cost": display_cost,
                            "cost_type": cost_type,
                            "raw_cost": cost,
                            "description": method.title or method.method_title
                        })
                
                return shipping_options
        except Exception as e:
            logger.error(f"Error getting shipping options: {e}")
            return []
    
    def _extract_fee_range(self, fee_string: str) -> str:
        """Extract min and max fee from fee string"""
        import re
        min_match = re.search(r'min_fee="(\d+)"', fee_string)
        max_match = re.search(r'max_fee="(\d+)"', fee_string)
        
        if min_match and max_match:
            return f"${min_match.group(1)}.00 - ${max_match.group(1)}.00"
        elif min_match:
            return f"${min_match.group(1)}.00+"
        else:
            return "Variable"