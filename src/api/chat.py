"""Chat endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging

from ..models_modern import ChatRequest, ChatResponse
from ..dependencies import get_chat_service
from ..services_async import ChatService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    """
    Process a chat message and return AI response
    
    - Maintains conversation history
    - Searches for relevant products
    - Includes shipping information when applicable
    """
    try:
        logger.info(f"Chat request: site={request.site_name}, user={request.user_id}")
        
        response = await chat_service.get_response(
            message=request.message,
            site_name=request.site_name,
            conversation_id=request.conversation_id,
            user_id=request.user_id
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process chat message")

@router.get("/chat/history/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    limit: int = 50
):
    """Get conversation history"""
    try:
        messages = await chat_service.get_conversation_history(
            conversation_id=conversation_id,
            limit=limit
        )
        return {"conversation_id": conversation_id, "messages": messages}
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation history")