"""
Modern Pydantic models for API
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum

# Enums
class StockStatus(str, Enum):
    IN_STOCK = "instock"
    OUT_OF_STOCK = "outofstock"
    ON_BACKORDER = "onbackorder"

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

# Base Models
class BaseRequest(BaseModel):
    """Base request model with common fields"""
    model_config = ConfigDict(from_attributes=True)

class BaseResponse(BaseModel):
    """Base response model with common fields"""
    model_config = ConfigDict(from_attributes=True)

# Product Models
class ProductVariation(BaseModel):
    """Product variation details"""
    id: int
    sku: Optional[str] = None
    price: str
    regular_price: Optional[str] = None
    sale_price: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)
    stock_quantity: Optional[int] = None
    stock_status: StockStatus = StockStatus.IN_STOCK
    weight: Optional[str] = None
    dimensions: Optional[Dict[str, str]] = None

class ProductResponse(BaseResponse):
    """Product response with all details"""
    id: int
    woo_id: int
    name: str
    slug: str
    permalink: str
    type: Literal["simple", "variable", "grouped", "external"]
    status: str = "publish"
    featured: bool = False
    description: Optional[str] = None
    short_description: Optional[str] = None
    sku: Optional[str] = None
    price: str
    regular_price: Optional[str] = None
    sale_price: Optional[str] = None
    stock_status: StockStatus = StockStatus.IN_STOCK
    stock_quantity: Optional[int] = None
    categories: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    variations: List[ProductVariation] = Field(default_factory=list)
    attributes: List[Dict[str, Any]] = Field(default_factory=list)
    shipping_class: Optional[str] = None
    weight: Optional[str] = None
    dimensions: Optional[Dict[str, str]] = None
    images: List[Dict[str, str]] = Field(default_factory=list)

# Chat Models
class ChatRequest(BaseRequest):
    """Chat request model"""
    message: str = Field(min_length=1, max_length=2000)
    site_name: str = Field(default="store1")
    conversation_id: Optional[str] = Field(default=None, max_length=100)
    user_id: Optional[str] = Field(default=None, max_length=100)

class ChatMessage(BaseModel):
    """Individual chat message"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatResponse(BaseResponse):
    """Chat response with products and conversation ID"""
    response: str
    conversation_id: str
    products: List[Dict[str, Any]] = Field(default_factory=list)  # Changed to Dict to match old format
    categories: List[Dict[str, Any]] = Field(default_factory=list)
    shipping_options: List[Dict[str, Any]] = Field(default_factory=list)

# Search Models
class ProductSearchRequest(BaseRequest):
    """Product search request"""
    query: str = Field(min_length=1, max_length=500)
    site_name: str = Field(default="store1")
    limit: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None

class ProductSearchResponse(BaseResponse):
    """Product search response"""
    products: List[ProductResponse]
    count: int
    query: str
    search_time_ms: Optional[float] = None

# Shipping Models
class ShippingItem(BaseModel):
    """Item for shipping calculation"""
    product_id: int
    quantity: int = Field(ge=1)
    variation_id: Optional[int] = None

class ShippingCalculateRequest(BaseRequest):
    """Shipping calculation request"""
    site_name: str = Field(default="store1")
    product_ids: List[int]
    postcode: Optional[str] = Field(default=None, max_length=20)
    country: str = Field(default="AU", max_length=2)
    state: Optional[str] = Field(default=None, max_length=50)

class ShippingOption(BaseModel):
    """Shipping method option"""
    method_id: str
    method_title: str
    cost: float
    estimated_days: Optional[int] = None
    description: Optional[str] = None

class ShippingCalculateResponse(BaseResponse):
    """Shipping calculation response"""
    postcode: Optional[str]
    shipping_options: List[ShippingOption]
    product_ids: List[int]
    total_weight: Optional[float] = None

# Error Models
class ErrorResponse(BaseResponse):
    """Standard error response"""
    error: str
    details: Optional[Dict[str, Any]] = None
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)