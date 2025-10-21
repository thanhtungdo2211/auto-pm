from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from services.chatbot_agent_service import ChatbotAgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])

class ChatRequest(BaseModel):
    user_id: str
    query: str
    file: str

class ChatResponse(BaseModel):
    user_id: str
    query: str
    response: str
    success: bool

chatbot_service = ChatbotAgentService()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest):
    """
    Test chatbot integration directly
    """
    
    try:
        result = await chatbot_service.get_conversation_response(
            user_id=request.user_id,
            message=request.query
        )
        
        return ChatResponse(
            user_id=result["user_id"],
            query=result["query"],
            response=result.get("response", "No response"),
            success=result["success"]
        )
    
    except Exception as e:
        logger.error(f"Error in chatbot endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))