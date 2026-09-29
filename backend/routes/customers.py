import json
import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, status

from backend.config import SAMPLE_CUSTOMERS_PATH
from backend.models import Customer, CustomerCreate
from backend.services.hindsight_service import hindsight_service
from backend.services.agent_service import agent_service

router = APIRouter(prefix="/api/customers", tags=["customers"])
logger = logging.getLogger("memorydesk.routes.customers")

def _load_customers_file() -> List[Dict[str, Any]]:
    if not SAMPLE_CUSTOMERS_PATH.exists():
        return []
    with open(SAMPLE_CUSTOMERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_customers_file(customers: List[Dict[str, Any]]):
    with open(SAMPLE_CUSTOMERS_PATH, "w", encoding="utf-8") as f:
        json.dump(customers, f, indent=2)

def init_customers():
    """Initializes customer banks with their seed persistent memories in Hindsight."""
    customers = _load_customers_file()
    for cust in customers:
        if "seed_memories" in cust and cust["seed_memories"]:
            hindsight_service.seed_customer_memories(
                customer_id=cust["id"],
                seed_texts=cust["seed_memories"]
            )
    return customers

# Run on startup
init_customers()

@router.get("", response_model=List[Customer])
def get_all_customers():
    """Retrieve all synthetic & created customer profiles."""
    return _load_customers_file()

@router.get("/{customer_id}", response_model=Customer)
def get_customer_by_id(customer_id: str):
    """Retrieve single customer profile by ID."""
    customers = _load_customers_file()
    for c in customers:
        if c["id"] == customer_id:
            return c
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer '{customer_id}' not found")

@router.post("", response_model=Customer, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate):
    """Register a new customer and initialize their dedicated Hindsight memory bank."""
    customers = _load_customers_file()
    cust_id = f"cust_{uuid.uuid4().hex[:6]}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_cust = {
        "id": cust_id,
        "name": payload.name,
        "email": payload.email,
        "company": payload.company or "Independent",
        "title": payload.title or "Software Developer",
        "os": payload.os,
        "environment": payload.environment,
        "preference": payload.preference,
        "last_issue": None,
        "last_solution": None,
        "conversations_count": 0,
        "last_interaction": now_str,
        "status": "Active",
        "seed_memories": [
            f"Customer is {payload.name}, {payload.title} at {payload.company}.",
            f"Operating system is {payload.os} with development stack {payload.environment}.",
            f"Support preference: {payload.preference}."
        ]
    }

    # Seed the new bank in Hindsight
    hindsight_service.seed_customer_memories(cust_id, new_cust["seed_memories"])

    customers.append(new_cust)
    _save_customers_file(customers)
    return new_cust

@router.get("/{customer_id}/conversations")
def get_customer_conversations(customer_id: str):
    """Fetch conversation history for the given customer."""
    customers = _load_customers_file()
    if not any(c["id"] == customer_id for c in customers):
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "customer_id": customer_id,
        "conversations": agent_service.get_customer_conversations(customer_id)
    }
