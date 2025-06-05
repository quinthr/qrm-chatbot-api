from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


# Request Models
class ChatRequest(BaseModel):
    message: str
    site_name: str = "store1"
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None


class ProductSearchRequest(BaseModel):
    query: str
    site_name: str = "store1"
    limit: int = 10


class ShippingCalculateRequest(BaseModel):
    site_name: str = "store1"
    country: str
    state: Optional[str] = None
    postcode: Optional[str] = None
    city: Optional[str] = None
    items: List[Dict[str, Any]]  # [{"product_id": 123, "quantity": 1}]


# Response Models
class ProductInfo(BaseModel):
    id: int
    name: str
    price: str
    regular_price: Optional[str] = None
    sale_price: Optional[str] = None
    sku: Optional[str] = None
    permalink: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    stock_status: str = "instock"
    stock_quantity: Optional[int] = None


class CategoryInfo(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None


class ShippingOption(BaseModel):
    method_id: str
    title: str
    cost: str
    description: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    products: List[ProductInfo] = []
    categories: List[CategoryInfo] = []
    shipping_options: List[ShippingOption] = []
    conversation_id: str
    timestamp: datetime = datetime.utcnow()


class ProductSearchResponse(BaseModel):
    products: List[ProductInfo]
    total_found: int


class ShippingCalculateResponse(BaseModel):
    shipping_options: List[ShippingOption]
    total_cost: str


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database_connected: bool
    vector_db_connected: bool
    openai_configured: bool