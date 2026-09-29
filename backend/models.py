from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Customer(BaseModel):
    id: str
    name: str
    email: str
    company: Optional[str] = "Independent"
    title: Optional[str] = "Software Developer"
    os: str = "Windows 11"
    environment: str = "Python 3.12"
    preference: str = "Standard guidance"
    last_issue: Optional[str] = None
    last_solution: Optional[str] = None
    conversations_count: int = 0
    last_interaction: str = ""
    status: str = "Active"
    seed_memories: List[str] = Field(default_factory=list)

class CustomerCreate(BaseModel):
    name: str
    email: str
    company: Optional[str] = "Independent"
    title: Optional[str] = "Software Developer"
    os: str = "Windows 11"
    environment: str = "Python 3.12"
    preference: str = "Standard guidance"

class MemoryItemDetail(BaseModel):
    id: str
    text: str
    type: str = "fact"  # "world_fact" | "experience" | "observation"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    relevance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class AutoFixScript(BaseModel):
    os: str
    shell: str  # "powershell" | "zsh" | "bash"
    code: str
    explanation: str

class ChatRequest(BaseModel):
    customer_id: str
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    customer_id: str
    conversation_id: str
    memories_used: int
    retrieved_memories: List[MemoryItemDetail] = Field(default_factory=list)
    memory_updated: bool
    new_memory_stored: Optional[str] = None
    hindsight_status: str  # "active" | "connected" | "local_embedded"
    hindsight_message: Optional[str] = None
    llm_provider: str
    auto_fix_script: Optional[AutoFixScript] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class MemorySearchRequest(BaseModel):
    customer_id: str
    query: str
    limit: Optional[int] = 5

class MemoryStoreRequest(BaseModel):
    customer_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class CustomerMemoryResponse(BaseModel):
    customer_id: str
    customer_name: str
    total_memories: int
    memories: List[MemoryItemDetail]
    categorized_memories: Dict[str, List[MemoryItemDetail]] = Field(default_factory=dict)
    timeline: List[Dict[str, Any]]
    structured_profile: Dict[str, Any]
    hindsight_connected: bool

class ReflectionResponse(BaseModel):
    customer_id: str
    customer_name: str
    mental_model: str
    recurring_pattern: str
    disposition_score: float  # 0.0 - 1.0
    proactive_recommendation: str
    facts_analyzed: int
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class IsolationTestRequest(BaseModel):
    query: str = "database connection issue"
    customer_ids: List[str] = Field(default_factory=lambda: ["cust_rahul", "cust_priya", "cust_arjun"])

class IsolationTestResponse(BaseModel):
    query: str
    results_by_customer: Dict[str, Any]
    isolation_confirmed: bool
    security_verdict: str

class ConversationItem(BaseModel):
    id: str
    customer_id: str
    role: str
    message: str
    timestamp: str
    memories_used: Optional[int] = 0

class HealthResponse(BaseModel):
    status: str
    version: str
    hindsight_connected: bool
    hindsight_url: str
    hindsight_version: Optional[str] = None
    llm_provider: str
    llm_configured: bool
    active_customers: int
