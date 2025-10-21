from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mockup Chatbot API",
    description="Mockup server for testing chatbot integration",
    version="1.0.0"
)

# Request/Response Models
class ChatRequest(BaseModel):
    user_id: int
    query: str
    file: str = ""

class ChatResponse(BaseModel):
    user_id: int
    query: str
    response: str

# Mockup responses based on query type
MOCKUP_RESPONSES = {
    "greeting": [
        "Chào bạn! Rất vui được trò chuyện với bạn. Bạn có khỏe không? Bạn muốn nói về điều gì hôm nay?",
        "Xin chào! Tôi có thể giúp gì cho bạn?",
        "Hello! Tôi là chatbot hỗ trợ quản lý dự án. Bạn cần hỗ trợ gì?"
    ],
    "file_wbs": """✅ Đã phân tích WBS thành công!

📊 **Tổng quan dự án:**
- Tổng số tasks: {task_count}
- Tổng thời gian dự kiến: {total_days} ngày
- Số thành viên cần: {member_count} người

📝 **Danh sách tasks đã tạo:**
{tasks_list}

Tôi đã tạo các tasks trong hệ thống. Bạn có thể:
- Gõ "xem tasks" để xem chi tiết
- Gõ "phân công" để bắt đầu phân công công việc
- Gõ "timeline" để xem timeline dự án""",
    
    "default": "Tôi hiểu bạn muốn biết về '{query}'. Tuy nhiên, tôi cần thêm thông tin để có thể hỗ trợ tốt hơn. Bạn có thể nói rõ hơn được không?"
}

def detect_query_type(query: str, file: str) -> str:
    """Detect type of query to return appropriate response"""
    query_lower = query.lower().strip()
    
    # Check if file content (WBS processing)
    if file and len(file) > 0:
        return "file_wbs"
    
    # Check for greetings
    greeting_keywords = ["xin chào", "chào", "hello", "hi", "hey"]
    if any(keyword in query_lower for keyword in greeting_keywords):
        return "greeting"
    
    return "default"

def parse_wbs_file(file_content: str) -> dict:
    """Parse WBS file content and extract tasks"""
    tasks = []
    total_days = 0
    
    lines = file_content.strip().split('\n')
    for i, line in enumerate(lines[:10], 1):  # Limit to first 10 tasks for mockup
        parts = line.split(',')
        if len(parts) >= 3:
            task_name = parts[0].strip()
            assignee = parts[1].strip() if parts[1] else "Chưa phân công"
            days_str = parts[2].strip()
            
            # Extract days from string (e.g., "5 days" -> 5)
            try:
                days = int(''.join(filter(str.isdigit, days_str)))
                total_days += days
            except:
                days = 1
            
            tasks.append(f"{i}. {task_name} - {assignee} ({days} ngày)")
    
    return {
        "task_count": len(tasks),
        "total_days": total_days,
        "member_count": min(len(tasks) // 2 + 1, 5),  # Mockup calculation
        "tasks_list": "\n".join(tasks) if tasks else "Không tìm thấy tasks"
    }

def generate_response(query: str, file: str, user_id: int) -> str:
    """Generate mockup response based on query type"""
    query_type = detect_query_type(query, file)
    
    logger.info(f"User {user_id} | Query type: {query_type} | Query: {query[:50]}... | File: {len(file)} chars")
    
    if query_type == "file_wbs":
        # Parse WBS file and generate response
        wbs_data = parse_wbs_file(file)
        response = MOCKUP_RESPONSES["file_wbs"].format(**wbs_data)
        return response
    
    elif query_type == "greeting":
        import random
        return random.choice(MOCKUP_RESPONSES["greeting"])
    
    else:
        return MOCKUP_RESPONSES["default"].format(query=query)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that mimics chatbot behavior
    
    - **user_id**: User ID (integer)
    - **query**: User's message/query
    - **file**: File content as string (optional, for WBS processing)
    """
    try:
        logger.info(f"📥 Request from user {request.user_id}")
        logger.info(f"   Query: {request.query[:100]}...")
        logger.info(f"   File: {len(request.file)} chars")
        
        # Generate response
        response_text = generate_response(
            query=request.query,
            file=request.file,
            user_id=request.user_id
        )
        
        logger.info(f"✅ Response generated: {response_text[:100]}...")
        
        return ChatResponse(
            user_id=request.user_id,
            query=request.query,
            response=response_text + "---" + request.file
        )
    
    except Exception as e:
        logger.error(f"❌ Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "message": "Mockup Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "chat": "/chat (POST)"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mockup-chatbot"}

# Test examples endpoint
@app.get("/examples")
async def examples():
    """Get example requests"""
    return {
        "text_only": {
            "user_id": 123,
            "query": "Xin chào",
            "file": ""
        },
        "wbs_file": {
            "user_id": 456,
            "query": "",
            "file": "Task 1,Frontend,5 days\nTask 2,Backend,7 days\nTask 3,Testing,3 days"
        },
        "with_query_and_file": {
            "user_id": 789,
            "query": "Phân tích WBS này",
            "file": "Setup Environment,DevOps,2 days\nDatabase Design,Backend,4 days"
        }
    }

if __name__ == "__main__":
    # Run server
    print("🚀 Starting Mockup Chatbot Server...")
    print("📖 Docs: http://localhost:3030/docs")
    print("🏥 Health: http://localhost:3030/health")
    print("📝 Examples: http://localhost:3030/examples")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3030,
        log_level="info"
    )