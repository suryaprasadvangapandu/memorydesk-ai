import logging
from fastapi import APIRouter, HTTPException, status

from backend.models import ChatRequest, ChatResponse
from backend.services.agent_service import agent_service
from backend.routes.customers import _load_customers_file, _save_customers_file

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger("memorydesk.routes.chat")

@router.post("", response_model=ChatResponse)
def handle_chat_message(payload: ChatRequest):
    """
    Core Chat Endpoint:
    Processes user message through Hindsight memory retrieval,
    LLM reasoning context, and memory persistence.
    """
    # 1. Validation
    if not payload.message or not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User message cannot be empty."
        )

    customer_id = payload.customer_id.strip()
    customers = _load_customers_file()
    customer = next((c for c in customers if c["id"] == customer_id), None)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' was not found. Please select a valid customer."
        )

    try:
        # 2. Process chat through cognitive agent loop
        chat_response = agent_service.process_chat(payload, customer)

        # 3. Update customer conversation metrics
        customer["conversations_count"] = customer.get("conversations_count", 0) + 1
        _save_customers_file(customers)

        return chat_response

    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating support response: {str(e)}"
        )
