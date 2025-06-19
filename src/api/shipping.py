"""Shipping calculation endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from ..models_modern import ShippingCalculateRequest, ShippingCalculateResponse
from ..dependencies import get_kb_service
from ..services_async import KnowledgeBaseService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/shipping/calculate", response_model=ShippingCalculateResponse)
async def calculate_shipping(
    request: ShippingCalculateRequest,
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
) -> ShippingCalculateResponse:
    """
    Calculate shipping costs for given products
    
    - Considers product shipping classes
    - Applies zone-based rates
    - Handles percentage and fixed fees
    """
    try:
        shipping_options = await kb_service.get_shipping_options_for_products(
            site_name=request.site_name,
            product_ids=request.product_ids,
            postcode=request.postcode
        )
        
        return ShippingCalculateResponse(
            postcode=request.postcode,
            shipping_options=shipping_options,
            product_ids=request.product_ids
        )
        
    except Exception as e:
        logger.error(f"Shipping calculation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate shipping")

@router.get("/shipping/{site_name}/zones")
async def get_shipping_zones(
    site_name: str,
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Get all shipping zones for a site"""
    try:
        zones = await kb_service.get_shipping_zones(site_name)
        return {"site_name": site_name, "zones": zones}
    except Exception as e:
        logger.error(f"Shipping zone retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve shipping zones")