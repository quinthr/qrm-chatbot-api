"""
Database models for the QRM Chatbot API
These models match the schema from the crawler project
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Site(Base):
    __tablename__ = 'sites'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = relationship("Product", back_populates="site")
    categories = relationship("Category", back_populates="site")
    shipping_zones = relationship("ShippingZone", back_populates="site")


class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    woo_id = Column(Integer, nullable=False)
    name = Column(String(500), nullable=False)
    slug = Column(String(500))
    sku = Column(String(255))
    price = Column(String(50))
    regular_price = Column(String(50))
    sale_price = Column(String(50))
    description = Column(Text)
    short_description = Column(Text)
    status = Column(String(50))
    stock_status = Column(String(50))
    stock_quantity = Column(Integer)
    categories = Column(JSON)
    tags = Column(JSON)
    images = Column(JSON)
    attributes = Column(JSON)
    variations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship("Site", back_populates="products")


class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    woo_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255))
    description = Column(Text)
    parent_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship("Site", back_populates="categories")


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
    site = relationship("Site", back_populates="shipping_zones")
    methods = relationship("ShippingMethod", back_populates="zone")


class ShippingMethod(Base):
    __tablename__ = 'shipping_methods'
    
    id = Column(Integer, primary_key=True)
    zone_id = Column(Integer, ForeignKey('shipping_zones.id'), nullable=False)
    woo_id = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    method_id = Column(String(100))
    method_title = Column(String(255))
    cost = Column(String(50))
    settings = Column(JSON)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    zone = relationship("ShippingZone", back_populates="methods")