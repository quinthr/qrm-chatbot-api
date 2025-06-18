import json
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .db_models import Product, Category, Site, ShippingZone, ShippingMethod, Conversation, ConversationMessage, ProductVariation, ShippingClass, ShippingClassRate
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
                    
                    # Convert to dict format - SIMPLE VARIATION SUPPORT
                    for product in db_products:
                        try:
                            # Get variations - simple version
                            variations = []
                            has_variations = False
                            price_display = getattr(product, 'price', 'Price on request')
                            
                            try:
                                # Query variations safely
                                variation_records = session.query(ProductVariation).filter_by(
                                    site_id=site.id, 
                                    product_id=getattr(product, 'id', None)
                                ).all()
                                
                                if variation_records:
                                    has_variations = True
                                    # Collect variation prices
                                    var_prices = []
                                    for var in variation_records:
                                        var_price = getattr(var, 'price', None)
                                        if var_price:
                                            var_prices.append(var_price)
                                        
                                        # Parse attributes from JSON string
                                        attributes_str = getattr(var, 'attributes', None)
                                        attributes_dict = {}
                                        if attributes_str:
                                            try:
                                                attributes_dict = json.loads(attributes_str)
                                            except (json.JSONDecodeError, TypeError):
                                                attributes_dict = {}
                                        
                                        # Build comprehensive variation data
                                        variation_data = {
                                            "id": getattr(var, 'woo_id', None),
                                            "sku": getattr(var, 'sku', None),
                                            "price": var_price,
                                            "regular_price": getattr(var, 'regular_price', None),
                                            "sale_price": getattr(var, 'sale_price', None),
                                            "stock_quantity": getattr(var, 'stock_quantity', None),
                                            "stock_status": getattr(var, 'stock_status', 'unknown'),
                                            "weight": getattr(var, 'weight', None),
                                            "dimensions": {
                                                "length": getattr(var, 'dimensions_length', None),
                                                "width": getattr(var, 'dimensions_width', None),
                                                "height": getattr(var, 'dimensions_height', None)
                                            },
                                            "attributes": attributes_dict
                                        }
                                        variations.append(variation_data)
                                    
                                    # If we have variation prices, show "from" pricing
                                    if var_prices and getattr(product, 'price', None):
                                        price_display = f"from {getattr(product, 'price', '')}"
                                        
                            except Exception as e:
                                print(f"Error getting variations: {e}")
                                # Continue without variations
                            
                            products.append({
                                "id": getattr(product, 'woo_id', None),
                                "name": getattr(product, 'name', ''),
                                "price": price_display,
                                "price_range": None,
                                "regular_price": getattr(product, 'regular_price', None),
                                "sale_price": getattr(product, 'sale_price', None),
                                "sku": getattr(product, 'sku', None),
                                "permalink": getattr(product, 'permalink', None),
                                "description": getattr(product, 'description', None),
                                "short_description": getattr(product, 'short_description', None),
                                "stock_status": getattr(product, 'stock_status', 'unknown'),
                                "stock_quantity": getattr(product, 'stock_quantity', None),
                                "has_variations": has_variations,
                                "variations": variations,
                                "variation_count": len(variations)
                            })
                        except Exception as e:
                            print(f"Error processing product: {e}")
                            continue
        
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
            # Simple version with basic variation support
            try:
                variations = []
                has_variations = False
                price_display = getattr(product, 'price', 'Price on request')
                
                try:
                    # Query variations safely
                    variation_records = session.query(ProductVariation).filter_by(
                        site_id=site.id, 
                        product_id=getattr(product, 'id', None)
                    ).all()
                    
                    if variation_records:
                        has_variations = True
                        # Collect variation prices
                        var_prices = []
                        for var in variation_records:
                            var_price = getattr(var, 'price', None)
                            if var_price:
                                var_prices.append(var_price)
                            
                            # Parse attributes from JSON string
                            attributes_str = getattr(var, 'attributes', None)
                            attributes_dict = {}
                            if attributes_str:
                                try:
                                    attributes_dict = json.loads(attributes_str)
                                except (json.JSONDecodeError, TypeError):
                                    attributes_dict = {}
                            
                            # Build comprehensive variation data
                            variation_data = {
                                "id": getattr(var, 'woo_id', None),
                                "sku": getattr(var, 'sku', None),
                                "price": var_price,
                                "regular_price": getattr(var, 'regular_price', None),
                                "sale_price": getattr(var, 'sale_price', None),
                                "stock_quantity": getattr(var, 'stock_quantity', None),
                                "stock_status": getattr(var, 'stock_status', 'unknown'),
                                "weight": getattr(var, 'weight', None),
                                "dimensions": {
                                    "length": getattr(var, 'dimensions_length', None),
                                    "width": getattr(var, 'dimensions_width', None),
                                    "height": getattr(var, 'dimensions_height', None)
                                },
                                "attributes": attributes_dict
                            }
                            variations.append(variation_data)
                        
                        # If we have variation prices, show "from" pricing
                        if var_prices and getattr(product, 'price', None):
                            price_display = f"from {getattr(product, 'price', '')}"
                            
                except Exception as e:
                    print(f"Error getting variations: {e}")
                    # Continue without variations
                
                return {
                    "id": getattr(product, 'woo_id', None),
                    "name": getattr(product, 'name', ''),
                    "price": price_display,
                    "price_range": None,
                    "regular_price": getattr(product, 'regular_price', None),
                    "sale_price": getattr(product, 'sale_price', None),
                    "sku": getattr(product, 'sku', None),
                    "permalink": getattr(product, 'permalink', None),
                    "description": getattr(product, 'description', None),
                    "short_description": getattr(product, 'short_description', None),
                    "stock_status": getattr(product, 'stock_status', 'unknown'),
                    "stock_quantity": getattr(product, 'stock_quantity', None),
                    "has_variations": has_variations,
                    "variations": variations,
                    "variation_count": len(variations)
                }
            except Exception as e:
                print(f"Error processing single product: {e}")
                return None
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
    
    def get_shipping_options_for_products(self, site_name: str, session: Session, products: List[Dict], cart_total: float = None, customer_postcode: str = None) -> List[Dict]:
        """Get shipping options with product-specific shipping class rates"""
        shipping_options = self.get_shipping_options(site_name, session, cart_total, customer_postcode)
        
        # If no products specified, return basic shipping options
        if not products:
            return shipping_options
        
        # Get shipping classes for products
        site = session.query(Site).filter_by(name=site_name).first()
        if not site:
            return shipping_options
        
        # Collect all shipping class IDs from products
        shipping_class_ids = set()
        for product_data in products:
            product_id = product_data.get('id')
            if product_id:
                product = session.query(Product).filter_by(
                    site_id=site.id,
                    woo_id=product_id
                ).first()
                if product and product.shipping_class:
                    # Look up shipping class by name/slug
                    shipping_class = session.query(ShippingClass).filter_by(
                        site_id=site.id,
                        slug=product.shipping_class
                    ).first()
                    if shipping_class:
                        shipping_class_ids.add(shipping_class.id)
        
        # Update shipping costs based on shipping class rates
        for option in shipping_options:
            # Find the shipping method
            method = session.query(ShippingMethod).filter_by(
                method_id=option['method_id'],
                title=option['title']
            ).first()
            
            if method:
                # Look for specific shipping class rates
                if shipping_class_ids:
                    # Get rates for these shipping classes
                    class_rates = session.query(ShippingClassRate).filter(
                        ShippingClassRate.method_id == method.id,
                        ShippingClassRate.shipping_class_id.in_(shipping_class_ids)
                    ).all()
                    
                    if class_rates:
                        # Use the highest rate among all classes
                        max_cost = 0
                        for rate in class_rates:
                            if rate.cost:
                                cost = self._calculate_shipping_cost(rate.cost, cart_total)
                                cost_value = self._extract_numeric_cost(cost)
                                if cost_value > max_cost:
                                    max_cost = cost_value
                        
                        if max_cost > 0:
                            option['cost'] = f"${max_cost:.2f}"
                            option['cost_type'] = 'class_based'
        
        return shipping_options
    
    def get_shipping_options(self, site_name: str, session: Session, cart_total: float = None, customer_postcode: str = None) -> List[Dict]:
        """Get shipping options for a site with calculated costs"""
        site = session.query(Site).filter_by(name=site_name).first()
        if not site:
            print(f"WARNING: Site '{site_name}' not found in database")
            return []
            
        zones = session.query(ShippingZone).filter_by(site_id=site.id).all()
        print(f"DEBUG: Found {len(zones)} shipping zones for site {site_name}")
        shipping_options = []
        
        # Filter zones by customer postcode if provided
        if customer_postcode:
            matching_zones = []
            for zone in zones:
                if self._postcode_matches_zone(customer_postcode, zone):
                    matching_zones.append(zone)
            # If no specific matches, include ALL zones (fallback to show all options)
            if not matching_zones:
                matching_zones = zones  # Show all zones if no location-specific matches
            zones = matching_zones
        
        for zone in zones:
            methods = session.query(ShippingMethod).filter_by(zone_id=zone.id, enabled=True).all()
            print(f"DEBUG: Zone '{zone.name}' has {len(methods)} enabled methods")
            
            for method in methods:
                settings = json.loads(method.settings) if method.settings else {}
                print(f"DEBUG: Method '{method.title}' settings: {settings}")
                
                # Extract cost from WooCommerce settings structure
                cost_value = "0"
                if isinstance(settings.get("cost"), dict):
                    # Handle WooCommerce settings object format
                    cost_value = settings["cost"].get("value", "0")
                elif "cost" in settings:
                    # Handle direct cost value
                    cost_value = str(settings["cost"])
                
                # Check for no-class shipping rate (where shipping_class_id is NULL)
                no_class_rate = session.query(ShippingClassRate).filter_by(
                    method_id=method.id,
                    shipping_class_id=None
                ).first()
                
                if no_class_rate and no_class_rate.cost:
                    cost_value = no_class_rate.cost
                    print(f"DEBUG: Using no-class rate cost: {cost_value}")
                else:
                    print(f"DEBUG: Extracted cost value from settings: {cost_value}")
                
                # Parse and calculate actual cost
                calculated_cost = self._calculate_shipping_cost(cost_value, cart_total)
                
                # Determine cost type
                cost_type = "percentage" if ("%" in cost_value or "percent" in cost_value) else "fixed"
                
                # Use the direct title from the database (contains proper names like "Free Pickup Footscray 3011")
                shipping_label = method.title
                
                # Include all shipping options (including $0.00 for free pickup)
                shipping_options.append({
                    "method_id": method.method_id,
                    "title": shipping_label,
                    "cost": calculated_cost,
                    "cost_type": cost_type,
                    "raw_cost": cost_value,  # Keep original for reference
                    "description": shipping_label
                })
        
        return shipping_options
    
    def _calculate_product_pricing(self, product, variations):
        """Calculate comprehensive pricing information including variations"""
        if not variations:
            # Simple product without variations
            return {
                "display_price": getattr(product, 'price', 'Price on request'),
                "price_range": None
            }
        
        # Extract numeric prices from variations
        variation_prices = []
        for variation in variations:
            variation_price = getattr(variation, 'price', None)
            if variation_price:
                try:
                    # Handle both "$123.45" and "123.45" formats
                    price_str = str(variation_price).replace("$", "").replace(",", "").strip()
                    if price_str:
                        variation_prices.append(float(price_str))
                except (ValueError, TypeError):
                    continue
        
        if not variation_prices:
            # Fallback to base product price if no valid variation prices
            product_price = getattr(product, 'price', None)
            return {
                "display_price": f"from {product_price}" if product_price else "Price on request",
                "price_range": None
            }
        
        # Calculate price range
        min_price = min(variation_prices)
        max_price = max(variation_prices)
        
        if min_price == max_price:
            # All variations have same price
            display_price = f"${min_price:.2f}"
            price_range = None
        else:
            # Variable pricing
            display_price = f"from ${min_price:.2f}"
            price_range = f"${min_price:.2f} - ${max_price:.2f}"
        
        return {
            "display_price": display_price,
            "price_range": price_range
        }
    
    def _postcode_matches_zone(self, customer_postcode: str, zone) -> bool:
        """Check if customer postcode matches the shipping zone's location data"""
        if not zone.locations or zone.locations.strip() == "":
            return False
            
        try:
            locations = json.loads(zone.locations)
            for location in locations:
                if location.get("type") == "postcode" and location.get("code") == customer_postcode:
                    return True
                # Match by state, city, or region
                if location.get("type") in ["state", "city", "region"]:
                    if self._is_postcode_in_location(customer_postcode, location):
                        return True
        except (json.JSONDecodeError, AttributeError):
            return False
            
        return False
    
    def _is_postcode_in_location(self, postcode: str, location: dict) -> bool:
        """Check if postcode belongs to a specific Australian location"""
        code = location.get("code", "").upper()
        location_type = location.get("type", "")
        
        # Australian postcode ranges by state
        postcode_ranges = {
            # Victoria
            "AU:VIC": range(3000, 4000),
            "VIC": range(3000, 4000),
            "VICTORIA": range(3000, 4000),
            
            # New South Wales
            "AU:NSW": list(range(1000, 3000)) + list(range(2000, 3000)),
            "NSW": list(range(1000, 3000)) + list(range(2000, 3000)),
            "NEW SOUTH WALES": list(range(1000, 3000)) + list(range(2000, 3000)),
            
            # Queensland
            "AU:QLD": range(4000, 5000),
            "QLD": range(4000, 5000),
            "QUEENSLAND": range(4000, 5000),
            
            # South Australia
            "AU:SA": range(5000, 6000),
            "SA": range(5000, 6000),
            "SOUTH AUSTRALIA": range(5000, 6000),
            
            # Western Australia
            "AU:WA": range(6000, 7000),
            "WA": range(6000, 7000),
            "WESTERN AUSTRALIA": range(6000, 7000),
            
            # Tasmania
            "AU:TAS": range(7000, 8000),
            "TAS": range(7000, 8000),
            "TASMANIA": range(7000, 8000),
            
            # Northern Territory
            "AU:NT": list(range(800, 900)) + list(range(900, 1000)),
            "NT": list(range(800, 900)) + list(range(900, 1000)),
            "NORTHERN TERRITORY": list(range(800, 900)) + list(range(900, 1000)),
            
            # Australian Capital Territory
            "AU:ACT": list(range(200, 300)) + list(range(2600, 2700)),
            "ACT": list(range(200, 300)) + list(range(2600, 2700)),
            "AUSTRALIAN CAPITAL TERRITORY": list(range(200, 300)) + list(range(2600, 2700)),
        }
        
        # Major city postcode ranges
        city_ranges = {
            # Melbourne Metro
            "MELBOURNE": range(3000, 3200),
            "MELBOURNE METRO": range(3000, 3200),
            "MELBOURNE CBD": range(3000, 3007),
            "FOOTSCRAY": [3011, 3012],
            "VIRGINIA": [4014],
            
            # Sydney Metro  
            "SYDNEY": list(range(1000, 1400)) + list(range(2000, 2300)),
            "SYDNEY METRO": list(range(1000, 1400)) + list(range(2000, 2300)),
            "SYDNEY CBD": range(2000, 2010),
            
            # Brisbane Metro
            "BRISBANE": range(4000, 4200),
            "BRISBANE METRO": range(4000, 4200),
            "BRISBANE CBD": range(4000, 4010),
            "BEENLEIGH": range(4207, 4210),
            
            # Gold Coast
            "GOLD COAST": range(4200, 4230),
            "SUNSHINE COAST": range(4550, 4580),
            
            # Adelaide Metro
            "ADELAIDE": range(5000, 5200),
            "ADELAIDE METRO": range(5000, 5200),
            
            # Perth Metro
            "PERTH": range(6000, 6200),
            "PERTH METRO": range(6000, 6200),
            
            # Hobart Metro
            "HOBART": range(7000, 7100),
            "HOBART METRO": range(7000, 7100),
            
            # Wollongong
            "WOLLONGONG": range(2500, 2530),
            "WOOLLOONGONG": range(2500, 2530),  # Handle typo in your data
        }
        
        try:
            postcode_int = int(postcode)
        except ValueError:
            return False
        
        # Check state/territory ranges
        if code in postcode_ranges:
            postcode_range = postcode_ranges[code]
            if isinstance(postcode_range, range):
                return postcode_int in postcode_range
            elif isinstance(postcode_range, list):
                return postcode_int in postcode_range
        
        # Check city ranges
        if code in city_ranges:
            city_range = city_ranges[code]
            if isinstance(city_range, range):
                return postcode_int in city_range
            elif isinstance(city_range, list):
                return postcode_int in city_range
        
        # Handle radius-based matching (extract from zone name)
        zone_name = getattr(zone, 'name', '').upper()
        if 'RADIUS' in zone_name or 'METRO' in zone_name:
            return self._is_in_metro_radius(postcode_int, zone_name)
        
        return False
    
    def _is_in_metro_radius(self, postcode: int, zone_name: str) -> bool:
        """Check if postcode is within metro radius zones"""
        metro_zones = {
            "MELBOURNE": (3000, 3200),
            "SYDNEY": (2000, 2300),
            "BRISBANE": (4000, 4200),
            "ADELAIDE": (5000, 5200),
            "PERTH": (6000, 6200),
            "HOBART": (7000, 7100),
        }
        
        for city, (start, end) in metro_zones.items():
            if city in zone_name and start <= postcode < end:
                return True
        
        return False
    
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
    
    def _extract_numeric_cost(self, cost_str: str) -> float:
        """Extract numeric value from cost string"""
        if not cost_str or cost_str == "0":
            return 0.0
        
        try:
            # Remove currency symbols and whitespace
            cleaned = cost_str.replace("$", "").replace(",", "").strip()
            
            # If it's just a number, return it
            if cleaned.replace(".", "").isdigit():
                return float(cleaned)
            
            # Extract number from strings like "From $30.00" or "$30.00 - $75.00"
            import re
            numbers = re.findall(r'[\d.]+', cleaned)
            if numbers:
                return float(numbers[0])  # Return first number found
            
            return 0.0
        except (ValueError, TypeError):
            return 0.0


class ChatService:
    def __init__(self):
        self.knowledge_base = KnowledgeBaseService()
        self.openai_client = OpenAI(api_key=config.openai.api_key)
        
    # @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    def generate_response(self, message: str, site_name: str, conversation_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate chatbot response using OpenAI and knowledge base"""
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Initialize variables with defaults
        ai_response = "I'm sorry, I'm having trouble processing your request right now. Please try again later."
        relevant_products = []
        categories = []
        shipping_options = []
        
        try:
            with db_manager.get_session() as session:
                # Get site
                try:
                    site = session.query(Site).filter_by(name=site_name).first()
                    if not site:
                        raise ValueError(f"Site '{site_name}' not found")
                except Exception as db_error:
                    print(f"ERROR: Database query failed for site lookup: {str(db_error)}")
                    raise Exception(f"Database connection error: {str(db_error)}")
                
                # Get or create conversation
                try:
                    conversation = session.query(Conversation).filter_by(conversation_id=conversation_id).first()
                    if not conversation:
                        conversation = Conversation(
                            site_id=site.id,
                            conversation_id=conversation_id,
                            user_id=user_id
                        )
                        session.add(conversation)
                        session.flush()  # Get the ID
                except Exception as db_error:
                    print(f"ERROR: Database query failed for conversation: {str(db_error)}")
                    raise Exception(f"Database connection error during conversation creation: {str(db_error)}")
                
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
                
                # Get additional context (skip categories if table is empty)
                try:
                    categories = self.knowledge_base.get_categories(site_name, session)
                except Exception as e:
                    print(f"DEBUG: Skipping categories due to error: {e}")
                    categories = []
                
                # Extract postcode from message for location-based shipping
                customer_postcode = self._extract_postcode(message)
                
                # Use product-aware shipping calculation if products found
                if relevant_products:
                    shipping_options = self.knowledge_base.get_shipping_options_for_products(
                        site_name, session, relevant_products, customer_postcode=customer_postcode
                    )
                else:
                    shipping_options = self.knowledge_base.get_shipping_options(
                        site_name, session, customer_postcode=customer_postcode
                    )
                
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
        
        except Exception as e:
            print(f"ERROR: Chat service error: {str(e)}")
            print(f"ERROR: Exception type: {type(e).__name__}")
            import traceback
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            ai_response = f"DEBUG ERROR: {type(e).__name__}: {str(e)}"
            relevant_products = []
            categories = []
            shipping_options = []
        
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
    
    def _extract_postcode(self, message: str) -> str:
        """Extract Australian postcode from customer message"""
        import re
        
        # Look for 4-digit Australian postcodes
        postcode_pattern = r'\b([0-9]{4})\b'
        matches = re.findall(postcode_pattern, message)
        
        for match in matches:
            postcode = int(match)
            # Validate it's a valid Australian postcode range
            if ((1000 <= postcode <= 2999) or  # NSW/ACT
                (3000 <= postcode <= 3999) or  # VIC
                (4000 <= postcode <= 4999) or  # QLD
                (5000 <= postcode <= 5999) or  # SA
                (6000 <= postcode <= 6999) or  # WA
                (7000 <= postcode <= 7999) or  # TAS
                (800 <= postcode <= 999)):     # NT
                return match
        
        return None
    
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
- For variable products with variations, explain the different options available (sizes, weights, attributes)
- If a price range is provided, mention both the starting price and range (e.g., "from $122.59, with options ranging $122.59 - $450.00")
- Mention specific variation details when relevant (e.g., "Available in 2kg, 4kg, 6kg, and 8kg/m² variants")
- ALWAYS provide product page links as clickable HTML hyperlinks
- MUST format links as HTML anchor tags: <a href="URL">Click here</a> or <a href="URL">product name</a>
- NEVER use markdown format [text](url) - always use HTML <a href="url">text</a>
- Suggest related or complementary products when appropriate
- Direct them to visit the product page to see all variation options and add items to their cart"""
    
    def _build_context(self, message: str, products: List[Dict], categories: List[Dict], 
                      shipping_options: List[Dict], site_name: str) -> str:
        """Build context string for OpenAI"""
        context_parts = []
        
        if products:
            context_parts.append("RELEVANT PRODUCTS:")
            for product in products:
                price_info = f"Price: {product['price']}"
                if product.get('price_range'):
                    price_info = f"Price: {product['price']} (Range: {product['price_range']})"
                elif product.get('sale_price'):
                    price_info = f"Regular: {product['regular_price']}, Sale: {product['sale_price']}"
                
                # Add variation information
                variation_info = ""
                if product.get('has_variations') and product.get('variations'):
                    variation_count = product.get('variation_count', 0)
                    variation_info = f"\n  Variations: {variation_count} options available"
                    
                    # Include sample variation attributes
                    sample_variations = product['variations'][:3]  # Show first 3 variations
                    for var in sample_variations:
                        if var.get('attributes'):
                            try:
                                # Attributes can be a list of dicts or a dict
                                attributes = var['attributes']
                                attr_str = ""
                                
                                if isinstance(attributes, list):
                                    # WooCommerce format: list of {name, option} objects
                                    attr_parts = []
                                    for attr in attributes:
                                        if isinstance(attr, dict) and attr.get('option'):
                                            attr_parts.append(f"{attr.get('name', 'Unknown')}: {attr['option']}")
                                    attr_str = ", ".join(attr_parts)
                                elif isinstance(attributes, dict):
                                    # Alternative format: direct key-value pairs
                                    attr_parts = []
                                    for key, value in attributes.items():
                                        if value:
                                            attr_parts.append(f"{key}: {value}")
                                    attr_str = ", ".join(attr_parts)
                                if attr_str:
                                    variation_info += f"\n    - {var.get('sku', 'N/A')}: {var.get('price', 'N/A')} ({attr_str})"
                                else:
                                    variation_info += f"\n    - {var.get('sku', 'N/A')}: {var.get('price', 'N/A')}"
                            except (json.JSONDecodeError, TypeError, KeyError):
                                variation_info += f"\n    - {var.get('sku', 'N/A')}: {var.get('price', 'N/A')}"
                
                context_parts.append(
                    f"- {product['name']} (SKU: {product.get('sku', 'N/A')}) - {price_info}\n"
                    f"  Description: {product.get('short_description', 'No description')}\n"
                    f"  Stock: {product.get('stock_status', 'unknown')}{variation_info}\n"
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