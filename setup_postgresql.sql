-- PostgreSQL schema for QRM Chatbot
-- Converted from MySQL schema

-- Create database (run separately if needed)
-- CREATE DATABASE qrm_chatbot;

-- Use UTF-8 encoding (default in PostgreSQL)

-- Sites table
CREATE TABLE IF NOT EXISTS sites (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    url TEXT,
    consumer_key VARCHAR(255),
    consumer_secret VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    woo_id INTEGER NOT NULL,
    name TEXT,
    slug VARCHAR(255),
    permalink TEXT,
    date_created TIMESTAMP,
    date_modified TIMESTAMP,
    type VARCHAR(50) DEFAULT 'simple',
    status VARCHAR(50) DEFAULT 'publish',
    featured BOOLEAN DEFAULT false,
    catalog_visibility VARCHAR(50) DEFAULT 'visible',
    description TEXT,
    short_description TEXT,
    sku VARCHAR(255),
    price DECIMAL(10,2),
    regular_price DECIMAL(10,2),
    sale_price DECIMAL(10,2),
    date_on_sale_from TIMESTAMP,
    date_on_sale_to TIMESTAMP,
    on_sale BOOLEAN DEFAULT false,
    purchasable BOOLEAN DEFAULT true,
    total_sales INTEGER DEFAULT 0,
    virtual BOOLEAN DEFAULT false,
    downloadable BOOLEAN DEFAULT false,
    download_limit INTEGER DEFAULT -1,
    download_expiry INTEGER DEFAULT -1,
    external_url TEXT,
    button_text VARCHAR(255),
    tax_status VARCHAR(50) DEFAULT 'taxable',
    tax_class VARCHAR(255),
    manage_stock BOOLEAN DEFAULT false,
    stock_quantity INTEGER,
    stock_status VARCHAR(50) DEFAULT 'instock',
    backorders VARCHAR(50) DEFAULT 'no',
    backorders_allowed BOOLEAN DEFAULT false,
    backordered BOOLEAN DEFAULT false,
    low_stock_amount INTEGER,
    sold_individually BOOLEAN DEFAULT false,
    weight DECIMAL(8,3),
    dimensions_length DECIMAL(8,3),
    dimensions_width DECIMAL(8,3),
    dimensions_height DECIMAL(8,3),
    shipping_required BOOLEAN DEFAULT true,
    shipping_taxable BOOLEAN DEFAULT true,
    shipping_class VARCHAR(255),
    shipping_class_id INTEGER,
    reviews_allowed BOOLEAN DEFAULT true,
    average_rating DECIMAL(3,2) DEFAULT 0.00,
    rating_count INTEGER DEFAULT 0,
    upsell_ids TEXT,
    cross_sell_ids TEXT,
    parent_id INTEGER DEFAULT 0,
    purchase_note TEXT,
    menu_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, woo_id)
);

-- Product variations table
CREATE TABLE IF NOT EXISTS product_variations (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    woo_id INTEGER NOT NULL,
    date_created TIMESTAMP,
    date_modified TIMESTAMP,
    description TEXT,
    sku VARCHAR(255),
    price DECIMAL(10,2),
    regular_price DECIMAL(10,2),
    sale_price DECIMAL(10,2),
    date_on_sale_from TIMESTAMP,
    date_on_sale_to TIMESTAMP,
    on_sale BOOLEAN DEFAULT false,
    status VARCHAR(50) DEFAULT 'publish',
    purchasable BOOLEAN DEFAULT true,
    virtual BOOLEAN DEFAULT false,
    downloadable BOOLEAN DEFAULT false,
    download_limit INTEGER DEFAULT -1,
    download_expiry INTEGER DEFAULT -1,
    tax_status VARCHAR(50) DEFAULT 'taxable',
    tax_class VARCHAR(255),
    manage_stock BOOLEAN DEFAULT false,
    stock_quantity INTEGER,
    stock_status VARCHAR(50) DEFAULT 'instock',
    backorders VARCHAR(50) DEFAULT 'no',
    backorders_allowed BOOLEAN DEFAULT false,
    backordered BOOLEAN DEFAULT false,
    weight DECIMAL(8,3),
    dimensions_length DECIMAL(8,3),
    dimensions_width DECIMAL(8,3),
    dimensions_height DECIMAL(8,3),
    shipping_class VARCHAR(255),
    shipping_class_id INTEGER,
    attributes JSONB, -- Using JSONB for better performance
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, woo_id)
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    woo_id INTEGER NOT NULL,
    name VARCHAR(255),
    slug VARCHAR(255),
    parent INTEGER DEFAULT 0,
    description TEXT,
    display VARCHAR(50) DEFAULT 'default',
    image_id INTEGER,
    menu_order INTEGER DEFAULT 0,
    count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, woo_id)
);

-- Shipping zones table
CREATE TABLE IF NOT EXISTS shipping_zones (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    woo_id INTEGER NOT NULL,
    name VARCHAR(255),
    order_zone INTEGER DEFAULT 0,
    locations JSONB, -- Using JSONB for location data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, woo_id)
);

-- Shipping methods table
CREATE TABLE IF NOT EXISTS shipping_methods (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    shipping_zone_id INTEGER NOT NULL REFERENCES shipping_zones(id) ON DELETE CASCADE,
    woo_id INTEGER NOT NULL,
    instance_id INTEGER,
    title VARCHAR(255),
    order_method INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT true,
    method_id VARCHAR(255),
    method_title VARCHAR(255),
    settings JSONB, -- Using JSONB for settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, woo_id)
);

-- Shipping classes table
CREATE TABLE IF NOT EXISTS shipping_classes (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    woo_id INTEGER NOT NULL,
    name VARCHAR(255),
    slug VARCHAR(255),
    description TEXT,
    count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, woo_id)
);

-- Shipping class rates table
CREATE TABLE IF NOT EXISTS shipping_class_rates (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    shipping_method_id INTEGER NOT NULL REFERENCES shipping_methods(id) ON DELETE CASCADE,
    shipping_class_id INTEGER NOT NULL REFERENCES shipping_classes(id) ON DELETE CASCADE,
    rate_id VARCHAR(255),
    cost VARCHAR(255),
    calculation_type VARCHAR(50) DEFAULT 'flat',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crawl logs table
CREATE TABLE IF NOT EXISTS crawl_logs (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    crawl_type VARCHAR(50),
    status VARCHAR(50),
    items_processed INTEGER DEFAULT 0,
    items_added INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table (for API)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) UNIQUE NOT NULL,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation messages table (for API)
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_products_site_id ON products(site_id);
CREATE INDEX IF NOT EXISTS idx_products_woo_id ON products(woo_id);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug);

CREATE INDEX IF NOT EXISTS idx_product_variations_site_id ON product_variations(site_id);
CREATE INDEX IF NOT EXISTS idx_product_variations_product_id ON product_variations(product_id);
CREATE INDEX IF NOT EXISTS idx_product_variations_woo_id ON product_variations(woo_id);

CREATE INDEX IF NOT EXISTS idx_categories_site_id ON categories(site_id);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent);

CREATE INDEX IF NOT EXISTS idx_shipping_zones_site_id ON shipping_zones(site_id);
CREATE INDEX IF NOT EXISTS idx_shipping_methods_site_id ON shipping_methods(site_id);
CREATE INDEX IF NOT EXISTS idx_shipping_methods_zone_id ON shipping_methods(shipping_zone_id);

CREATE INDEX IF NOT EXISTS idx_shipping_class_rates_method_id ON shipping_class_rates(shipping_method_id);
CREATE INDEX IF NOT EXISTS idx_shipping_class_rates_class_id ON shipping_class_rates(shipping_class_id);

CREATE INDEX IF NOT EXISTS idx_conversations_conversation_id ON conversations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for auto-updating updated_at
CREATE TRIGGER update_sites_updated_at BEFORE UPDATE ON sites 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_product_variations_updated_at BEFORE UPDATE ON product_variations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shipping_zones_updated_at BEFORE UPDATE ON shipping_zones 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shipping_methods_updated_at BEFORE UPDATE ON shipping_methods 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shipping_classes_updated_at BEFORE UPDATE ON shipping_classes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default site (optional)
-- INSERT INTO sites (name, url, is_active) 
-- VALUES ('store1', 'https://example.com', true)
-- ON CONFLICT (name) DO NOTHING;