import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from backend.config import DATA_DIR, SAMPLE_CUSTOMERS_PATH
from backend.models import ChatRequest, ChatResponse, MemoryItemDetail, Customer, AutoFixScript
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

    def _generate_auto_fix_script(self, user_message: str, customer: Dict[str, Any]) -> Optional[AutoFixScript]:
        """
        Dynamically synthesizes a copy-pasteable script tailored to customer's exact OS.
        """
        msg_l = user_message.lower()
        os_name = customer.get("os", "Windows 11")
        is_windows = "windows" in os_name.lower()
        is_mac = "mac" in os_name.lower()
        is_linux = "ubuntu" in os_name.lower() or "linux" in os_name.lower()

        # Database / Port issue
        if any(w in msg_l for w in ["database", "postgres", "port", "5432", "django"]):
            if is_windows:
                return AutoFixScript(
                    os=os_name,
                    shell="powershell",
                    code="# Verify and restart PostgreSQL on Windows 11\nGet-Service postgresql* | Select-Object Name, Status\nRestart-Service -Name postgresql-x64-16 -Force\nTest-NetConnection -ComputerName 127.0.0.1 -Port 5432\npython manage.py dbshell",
                    explanation="Checks local Windows service status, restarts daemon, and verifies port 5432 connectivity."
                )
            elif is_mac:
                return AutoFixScript(
                    os=os_name,
                    shell="zsh",
                    code="# Restart PostgreSQL via Homebrew on macOS\nbrew services list | grep postgresql\nbrew services restart postgresql@16\nnc -zv 127.0.0.1 5432",
                    explanation="Restarts Homebrew PostgreSQL daemon and tests loopback socket on macOS."
                )
            else:
                return AutoFixScript(
                    os=os_name,
                    shell="bash",
                    code="# Check and restart PostgreSQL systemd service on Ubuntu\nsudo systemctl status postgresql\nsudo systemctl restart postgresql\npg_isready -h 127.0.0.1 -p 5432",
                    explanation="Restarts Linux systemd daemon and queries pg_isready health probe."
                )

        # Docker issue
        if "docker" in msg_l or "socket" in msg_l:
            return AutoFixScript(
                os=os_name,
                shell="bash" if not is_windows else "powershell",
                code="sudo chmod 666 /var/run/docker.sock\ndocker ps" if not is_windows else "Restart-Service docker\ndocker ps",
                explanation="Refreshes socket permissions for the container daemon."
            )

        # GPU / CUDA issue
        if "cuda" in msg_l or "oom" in msg_l or "gpu" in msg_l:
            return AutoFixScript(
                os=os_name,
                shell="bash",
                code="export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True\nnvidia-smi --query-gpu=memory.total,memory.free --format=csv",
                explanation="Sets PyTorch CUDA memory segmentation allocator to eliminate OOM spikes."
            )

        return None

    def _extract_new_memory_fact(self, user_message: str, customer: Dict[str, Any]) -> Optional[str]:
        msg = user_message.strip()
        msg_lower = msg.lower()

        if "windows" in msg_lower or "macos" in msg_lower or "ubuntu" in msg_lower or "linux" in msg_lower:
            return f"Customer reported operating environment: {msg}"
        if any(tool in msg_lower for tool in ["python", "django", "node", "docker", "postgres", "pytorch", "fastapi"]):
            if "i use" in msg_lower or "i am using" in msg_lower or "running" in msg_lower or "version" in msg_lower:
                return f"Customer environment stack specification: {msg}"
        if any(term in msg_lower for term in ["error", "exception", "failed", "timeout", "issue", "bug"]):
            return f"Customer troubleshooting incident: {msg}"
        if "prefer" in msg_lower or "like" in msg_lower or "please provide" in msg_lower or "step-by-step" in msg_lower:
            return f"Customer workflow preference: {msg}"
        if "my name is" in msg_lower or "i am " in msg_lower:
            return f"Customer identification detail: {msg}"

        return None

    def process_chat(self, chat_request: ChatRequest, customer: Dict[str, Any]) -> ChatResponse:
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

        # Step 6: Generate Auto-Fix Script tailored to customer OS
        auto_fix = self._generate_auto_fix_script(user_message, customer)

        # Step 7: Record conversation turn
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
            llm_provider=llm_service.provider_name,
            auto_fix_script=auto_fix
        )


# Global singleton
agent_service = AgentService()
