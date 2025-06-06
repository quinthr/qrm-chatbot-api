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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship('Site', back_populates='categories')
    products = relationship('Product', secondary=product_categories, back_populates='categories')
    
    # Add unique constraint for site_id + woo_id
    __table_args__ = (UniqueConstraint('site_id', 'woo_id', name='_site_category_woo_id_uc'),)


class ShippingZone(Base):
    __tablename__ = 'shipping_zones'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    woo_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    order = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship('Site', back_populates='shipping_zones')
    methods = relationship('ShippingMethod', back_populates='zone', cascade='all, delete-orphan')
    
    # Add unique constraint for site_id + woo_id
    __table_args__ = (UniqueConstraint('site_id', 'woo_id', name='_site_zone_woo_id_uc'),)


class ShippingMethod(Base):
    __tablename__ = 'shipping_methods'
    
    id = Column(Integer, primary_key=True)
    zone_id = Column(Integer, ForeignKey('shipping_zones.id'), nullable=False)
    instance_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    order = Column(Integer)
    enabled = Column(Boolean, default=True)
    method_id = Column(String(100))
    method_title = Column(String(255))
    method_description = Column(Text)
    settings = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    zone = relationship('ShippingZone', back_populates='methods')


class ShippingClass(Base):
    __tablename__ = 'shipping_classes'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    woo_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255))
    description = Column(Text)
    count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship('Site', back_populates='shipping_classes')
    
    # Add unique constraint for site_id + woo_id
    __table_args__ = (UniqueConstraint('site_id', 'woo_id', name='_site_class_woo_id_uc'),)


class CrawlLog(Base):
    __tablename__ = 'crawl_logs'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    crawl_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    items_crawled = Column(Integer, default=0)
    items_created = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    errors = Column(Text)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    
    # Relationships
    site = relationship('Site', back_populates='crawl_logs')