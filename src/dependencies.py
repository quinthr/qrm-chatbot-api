"""FastAPI dependency injection"""
from fastapi import Request
from typing import Dict, Any

from .database import Database
from .services import ChatService, KnowledgeBaseService

def get_db(request: Request) -> Database:
    """Get database instance from app state"""
    return request.app.state.db

def get_kb_service(request: Request) -> KnowledgeBaseService:
    """Get knowledge base service from app state"""
    return request.app.state.kb_service

def get_chat_service(request: Request) -> ChatService:
    """Get chat service from app state"""
    return request.app.state.chat_service

def get_services(request: Request) -> Dict[str, Any]:
    """Get all services as a dict"""
    return {
        "db": request.app.state.db,
        "kb_service": request.app.state.kb_service,
        "chat_service": request.app.state.chat_service
    }