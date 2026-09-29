import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from backend.config import DATA_DIR, SAMPLE_CUSTOMERS_PATH
from backend.models import ChatRequest, ChatResponse, MemoryItemDetail, Customer
from backend.services.hindsight_service import hindsight_service
from backend.services.llm_service import llm_service

logger = logging.getLogger("memorydesk.agent")
logger.setLevel(logging.INFO)

CONVERSATIONS_FILE = DATA_DIR / "conversations.json"

class AgentService:
    def __init__(self):
        self._conversations_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._load_conversations()

    def _load_conversations(self):
        if CONVERSATIONS_FILE.exists():
            try:
                with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
                    self._conversations_cache = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading conversations: {e}")
                self._conversations_cache = {}

    def _save_conversations(self):
        try:
            with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._conversations_cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving conversations: {e}")

    def get_customer_conversations(self, customer_id: str) -> List[Dict[str, Any]]:
        return self._conversations_cache.get(customer_id, [])

    def _extract_new_memory_fact(self, user_message: str, customer: Dict[str, Any]) -> Optional[str]:
        """
        Analyzes the user's message to extract useful persistent facts for Hindsight storage.
        E.g. operating system mentions, software tools, errors encountered, preferences.
        """
        msg = user_message.strip()
        msg_lower = msg.lower()

        # Check for environment disclosure
        if "windows" in msg_lower or "macos" in msg_lower or "ubuntu" in msg_lower or "linux" in msg_lower:
            return f"Customer reported operating environment: {msg}"
        
        # Check for python/node/stack version disclosure
        if any(tool in msg_lower for tool in ["python", "django", "node", "docker", "postgres", "pytorch", "fastapi"]):
            if "i use" in msg_lower or "i am using" in msg_lower or "running" in msg_lower or "version" in msg_lower:
                return f"Customer environment stack specification: {msg}"

        # Check for error disclosure
        if any(term in msg_lower for term in ["error", "exception", "failed", "timeout", "issue", "bug"]):
            return f"Customer troubleshooting incident: {msg}"

        # Check for preferences
        if "prefer" in msg_lower or "like" in msg_lower or "please provide" in msg_lower or "step-by-step" in msg_lower:
            return f"Customer workflow preference: {msg}"

        # Check for identity
        if "my name is" in msg_lower or "i am " in msg_lower:
            return f"Customer identification detail: {msg}"

        return None

    def process_chat(self, chat_request: ChatRequest, customer: Dict[str, Any]) -> ChatResponse:
        """
        Executes the end-to-end cognitive memory agent loop:
        1. Query -> 2. Hindsight Recall -> 3. Context Construction -> 4. LLM Generation -> 5. Hindsight Retain -> 6. Response
        """
        customer_id = chat_request.customer_id
        user_message = chat_request.message
        conv_id = chat_request.conversation_id or f"conv_{uuid.uuid4().hex[:8]}"

        # Step 1 & 2: Hindsight Memory Retrieval (Recall)
        retrieved_memories, memories_prompt = hindsight_service.retrieve_relevant_memories(
            customer_id=customer_id,
            query=user_message,
            limit=5
        )

        # Step 3: Fetch recent conversation history
        cust_history = self._conversations_cache.get(customer_id, [])

        # Step 4: Generate LLM Response with Memory Grounding
        ai_response_text = llm_service.generate_response(
            user_message=user_message,
            retrieved_memories_prompt=memories_prompt,
            customer_info=customer,
            conversation_history=cust_history
        )

        # Step 5: Extract and Store New Fact in Hindsight (Retain)
        new_fact = self._extract_new_memory_fact(user_message, customer)
        memory_updated = False
        stored_text = None

        if new_fact:
            success, mem_item = hindsight_service.store_memory(
                customer_id=customer_id,
                content=new_fact,
                metadata={"source": "conversation", "type": "learned_fact"},
                tags=["learned", "conversation"]
            )
            if success:
                memory_updated = True
                stored_text = new_fact
        else:
            # If the user shared an issue, retain a summary of interaction
            if any(term in user_message.lower() for term in ["database", "error", "problem", "happened"]):
                summary_fact = f"Customer referenced recurring issue: '{user_message}' - agent provided targeted troubleshooting steps."
                success, _ = hindsight_service.store_memory(
                    customer_id=customer_id,
                    content=summary_fact,
                    metadata={"source": "conversation_resolution", "type": "experience"},
                    tags=["experience", "troubleshooting"]
                )
                if success:
                    memory_updated = True
                    stored_text = summary_fact

        # Step 6: Record conversation turn
        now_iso = datetime.utcnow().isoformat()
        if customer_id not in self._conversations_cache:
            self._conversations_cache[customer_id] = []

        self._conversations_cache[customer_id].append({
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": "user",
            "content": user_message,
            "timestamp": now_iso
        })
        self._conversations_cache[customer_id].append({
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": "assistant",
            "content": ai_response_text,
            "timestamp": now_iso,
            "memories_used": len(retrieved_memories)
        })
        self._save_conversations()

        # Determine Hindsight status for UI badge
        hindsight_status = "active_live" if hindsight_service.is_connected else "active_local"
        hindsight_msg = (
            f"Connected to official Hindsight server ({hindsight_service.base_url})"
            if hindsight_service.is_connected
            else f"Hindsight Memory Engine Active (Local persistence bank synchronized)"
        )

        return ChatResponse(
            response=ai_response_text,
            customer_id=customer_id,
            conversation_id=conv_id,
            memories_used=len(retrieved_memories),
            retrieved_memories=retrieved_memories,
            memory_updated=memory_updated,
            new_memory_stored=stored_text,
            hindsight_status=hindsight_status,
            hindsight_message=hindsight_msg,
            llm_provider=llm_service.provider_name
        )

# Global singleton
agent_service = AgentService()
