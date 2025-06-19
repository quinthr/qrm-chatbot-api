"""Product search and retrieval endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging

from ..models import ProductSearchRequest, ProductSearchResponse, ProductResponse
from ..dependencies import get_kb_service
from ..services import KnowledgeBaseService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/products/search", response_model=ProductSearchResponse)
async def search_products(
    request: ProductSearchRequest,
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
) -> ProductSearchResponse:
    """
    Search for products using semantic search
    
    - Uses vector embeddings for intelligent matching
    - Returns relevant products with variations
    """
    try:
        products = await kb_service.search_products(
            site_name=request.site_name,
            query=request.query,
            limit=request.limit or 10
        )
        
        return ProductSearchResponse(
            products=products,
            count=len(products),
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"Product search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search products")

@router.get("/products/{site_name}/{product_id}", response_model=ProductResponse)
async def get_product(
    site_name: str,
    product_id: int,
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
) -> ProductResponse:
    """Get a specific product by ID"""
    try:
        product = await kb_service.get_product_by_id(
            site_name=site_name,
            product_id=product_id
        )
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
            
        return ProductResponse(**product)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Product retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve product")

@router.get("/products/{site_name}/categories")
async def get_categories(
    site_name: str,
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Get all product categories for a site"""
    try:
        categories = await kb_service.get_categories(site_name)
        return {"site_name": site_name, "categories": categories}
    except Exception as e:
        logger.error(f"Category retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")