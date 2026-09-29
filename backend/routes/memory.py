import logging
from fastapi import APIRouter, HTTPException, status

from backend.models import (
    CustomerMemoryResponse,
    MemorySearchRequest,
    MemoryStoreRequest,
    MemoryItemDetail
)
from backend.services.hindsight_service import hindsight_service
from backend.routes.customers import _load_customers_file

router = APIRouter(prefix="/api", tags=["memory"])
logger = logging.getLogger("memorydesk.routes.memory")

@router.get("/customers/{customer_id}/memory", response_model=CustomerMemoryResponse)
def get_customer_memory(customer_id: str):
    """
    Fetch comprehensive Hindsight memory overview for a customer:
    - Structured profile (OS, Stack, Issues, Preferences)
    - Full list of memory units
    - Chronological learning timeline
    """
    customers = _load_customers_file()
    customer = next((c for c in customers if c["id"] == customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    memory_data = hindsight_service.get_customer_memory(customer_id)
    
    return CustomerMemoryResponse(
        customer_id=customer_id,
        customer_name=customer["name"],
        total_memories=memory_data["total_memories"],
        memories=memory_data["memories"],
        timeline=memory_data["timeline"],
        structured_profile=memory_data["structured_profile"],
        hindsight_connected=memory_data["hindsight_connected"]
    )

@router.post("/memory/search")
def search_memories(payload: MemorySearchRequest):
    """
    Execute semantic search over customer memories in Hindsight.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
    results = hindsight_service.search_memory(
        customer_id=payload.customer_id,
        query=payload.query,
        limit=payload.limit or 5
    )
    return {
        "customer_id": payload.customer_id,
        "query": payload.query,
        "results_count": len(results),
        "results": results
    }

@router.post("/customers/{customer_id}/memory", status_code=status.HTTP_201_CREATED)
def add_customer_memory(customer_id: str, payload: MemoryStoreRequest):
    """
    Explicitly retain a new memory unit into the customer's Hindsight bank.
    """
    if not payload.content or not payload.content.strip():
        raise HTTPException(status_code=400, detail="Memory content cannot be empty")

    success, mem_item = hindsight_service.store_memory(
        customer_id=customer_id,
        content=payload.content,
        metadata=payload.metadata or {"source": "manual_entry", "type": "fact"},
        tags=payload.tags or ["manual"]
    )
    return {
        "success": success,
        "memory": mem_item
    }
