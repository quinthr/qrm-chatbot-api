"""
Database models for the QRM Chatbot API
These models match the schema from the crawler project
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Table, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Association tables
product_categories = Table(
    'product_categories', Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)


class Site(Base):
    __tablename__ = 'sites'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(String(500), nullable=False)
    consumer_key = Column(String(255), nullable=False)
    consumer_secret = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = relationship('Product', back_populates='site', cascade='all, delete-orphan')
    categories = relationship('Category', back_populates='site', cascade='all, delete-orphan')
    shipping_zones = relationship('ShippingZone', back_populates='site', cascade='all, delete-orphan')
    shipping_classes = relationship('ShippingClass', back_populates='site', cascade='all, delete-orphan')
    crawl_logs = relationship('CrawlLog', back_populates='site', cascade='all, delete-orphan')


class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    woo_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255))
    permalink = Column(String(500))
    sku = Column(String(100))
    price = Column(String(50))
    regular_price = Column(String(50))
    sale_price = Column(String(50))
    description = Column(Text)
    short_description = Column(Text)
    weight = Column(String(50))
    dimensions_length = Column(String(50))
    dimensions_width = Column(String(50))
    dimensions_height = Column(String(50))
    shipping_class = Column(String(100))
    stock_quantity = Column(Integer)
    stock_status = Column(String(50))
    manage_stock = Column(Boolean, default=False)
    featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship('Site', back_populates='products')
    categories = relationship('Category', secondary=product_categories, back_populates='products')
    variations = relationship('ProductVariation', back_populates='product', cascade='all, delete-orphan')
    
    # Add unique constraint for site_id + woo_id
    __table_args__ = (UniqueConstraint('site_id', 'woo_id', name='_site_woo_id_uc'),)


class ProductVariation(Base):
    __tablename__ = 'product_variations'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'))
    woo_id = Column(Integer, nullable=False)
    sku = Column(String(100))
    price = Column(String(50))
    regular_price = Column(String(50))
    sale_price = Column(String(50))
    stock_quantity = Column(Integer)
    stock_status = Column(String(50))
    weight = Column(String(50))
    dimensions_length = Column(String(50))
    dimensions_width = Column(String(50))
    dimensions_height = Column(String(50))
    attributes = Column(Text)  # JSON string
    # Note: No created_at, updated_at in actual database
    
    # Relationships
    site = relationship('Site')
    product = relationship('Product', back_populates='variations')
    
    # Add unique constraint for site_id + woo_id
    __table_args__ = (UniqueConstraint('site_id', 'woo_id', name='_site_variation_woo_id_uc'),)


class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    woo_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255))
    description = Column(Text)
    parent_id = Column(Integer, nullable=True)
    # Note: No count, created_at, updated_at columns in actual database
    
    # Relationships
    site = relationship('Site', back_populates='categories')
    products = relationship('Product', secondary=product_categories, back_populates='categories')
    
    # Add unique constraint for site_id + woo_id
    __table_args__ = (UniqueConstraint('site_id', 'woo_id', name='unique_site_category'),)


class ShippingZone(Base):
    __tablename__ = 'shipping_zones'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    woo_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    order = Column(Integer)
    locations = Column(Text)  # JSON string containing location data
    # Note: No created_at, updated_at in actual database
    
    # Relationships
    site = relationship('Site', back_populates='shipping_zones')
    methods = relationship('ShippingMethod', back_populates='zone', cascade='all, delete-orphan')
    
    # Add unique constraint for site_id + woo_id
    __table_args__ = (UniqueConstraint('site_id', 'woo_id', name='unique_site_zone'),)


class ShippingMethod(Base):
    __tablename__ = 'shipping_methods'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    zone_id = Column(Integer, ForeignKey('shipping_zones.id'), nullable=False)
    instance_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    method_id = Column(String(100))
    method_title = Column(String(255))
    enabled = Column(Boolean, default=True)
    settings = Column(Text)  # JSON string
    # Note: No order_method, method_description, created_at, updated_at in actual database
    
    # Relationships
    site = relationship('Site')
    zone = relationship('ShippingZone', back_populates='methods')


class ShippingClass(Base):
    __tablename__ = 'shipping_classes'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    woo_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255))
    description = Column(Text)
    # Note: No count, created_at, updated_at in actual database
    
    # Relationships
    site = relationship('Site', back_populates='shipping_classes')
    
    # Add unique constraint for site_id + woo_id
    __table_args__ = (UniqueConstraint('site_id', 'woo_id', name='_site_class_woo_id_uc'),)


class ShippingClassRate(Base):
    __tablename__ = 'shipping_class_rates'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    method_id = Column(Integer, ForeignKey('shipping_methods.id'), nullable=False)
    shipping_class_id = Column(Integer, ForeignKey('shipping_classes.id'), nullable=True)
    cost = Column(String(50))
    calculation_type = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship('Site')
    method = relationship('ShippingMethod')
    shipping_class = relationship('ShippingClass')


class CrawlLog(Base):
    __tablename__ = 'crawl_logs'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(50))
    products_crawled = Column(Integer, default=0)
    categories_crawled = Column(Integer, default=0)
    errors = Column(Text)
    # Note: No crawl_type, items_created, items_updated in actual database
    
    # Relationships
    site = relationship('Site', back_populates='crawl_logs')


class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    conversation_id = Column(String(255), nullable=False, unique=True)
    user_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship('Site')
    messages = relationship('ConversationMessage', back_populates='conversation', cascade='all, delete-orphan')


class ConversationMessage(Base):
    __tablename__ = 'conversation_messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(255), ForeignKey('conversations.conversation_id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship('Conversation', back_populates='messages')