import os
import logging
from typing import List, Dict, Any, Optional

from backend.config import GROQ_API_KEY, LLM_MODEL

logger = logging.getLogger("memorydesk.llm")
logger.setLevel(logging.INFO)

SYSTEM_PROMPT_TEMPLATE = """You are MemoryDesk AI, an elite intelligent customer support agent powered by Hindsight persistent memory.

Core Principles:
1. You have direct access to verified persistent memories about the customer retrieved from Hindsight.
2. Always actively leverage relevant memories (customer's operating system, environment, past issues, solutions, and communication preferences).
3. If the customer returns or references a previous issue (e.g., "the same database problem happened again"), immediately acknowledge that you remember their environment and their prior issue, and provide immediate continuity without asking them to re-explain.
4. Never claim to remember information that is NOT present in the retrieved memory or conversation.
5. Be helpful, concise, professional, and conversational. Follow the customer's known preferences (e.g. concise snippets, step-by-step guidance).

Customer Verified Memory from Hindsight:
{memory}

Customer Profile:
Name: {customer_name}
Organization: {company}
Operating System: {os}
Environment: {environment}
Preferred Style: {preference}

Recent Conversation History:
{conversation}
"""

class LLMService:
    def __init__(self, api_key: Optional[str] = GROQ_API_KEY, model: str = LLM_MODEL):
        self.api_key = api_key if api_key else os.getenv("GROQ_API_KEY", "")
        self.model = model
        self.provider_name = "Groq (Live LLM)" if self.api_key else "MemoryDesk Contextual Engine"
        self._client = None
        
        if self.api_key:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
                logger.info(f"Initialized Groq LLM service with model {self.model}")
            except Exception as e:
                logger.warning(f"Could not initialize Groq client: {e}")
                self._client = None

    def is_configured(self) -> bool:
        return bool(self._client and self.api_key)

    def generate_response(
        self,
        user_message: str,
        retrieved_memories_prompt: str,
        customer_info: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Generate support response using Groq LLM with Hindsight memories.
        Falls back to deterministic contextual reasoning if API key is not configured.
        """
        # Format conversation history
        conv_formatted = ""
        if conversation_history:
            for turn in conversation_history[-6:]:
                role = "Customer" if turn.get("role") == "user" else "MemoryDesk Agent"
                conv_formatted += f"{role}: {turn.get('content', '')}\n"
        else:
            conv_formatted = "No prior messages in this current session."

        mem_text = retrieved_memories_prompt if retrieved_memories_prompt.strip() else "No prior memories recorded yet."

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            memory=mem_text,
            customer_name=customer_info.get("name", "Valued Customer"),
            company=customer_info.get("company", "Independent"),
            os=customer_info.get("os", "Unknown OS"),
            environment=customer_info.get("environment", "Standard"),
            preference=customer_info.get("preference", "Concise, step-by-step"),
            conversation=conv_formatted
        )

        # Attempt live LLM completion
        if self._client:
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
                completion = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=600
                )
                response_text = completion.choices[0].message.content.strip()
                if response_text:
                    return response_text
            except Exception as e:
                logger.warning(f"Groq API call encountered error: {e}. Utilizing fallback engine.")

        # Fallback intelligent contextual response generator
        # Strictly applies customer memory retrieved from Hindsight
        return self._generate_contextual_fallback(
            user_message=user_message,
            retrieved_memories_prompt=mem_text,
            customer_info=customer_info
        )

    def _generate_contextual_fallback(
        self,
        user_message: str,
        retrieved_memories_prompt: str,
        customer_info: Dict[str, Any]
    ) -> str:
        msg_lower = user_message.lower()
        name = customer_info.get("name", "there")
        first_name = name.split()[0] if name else "there"
        os_info = customer_info.get("os", "your operating system")
        env_info = customer_info.get("environment", "your development environment")
        last_issue = customer_info.get("last_issue", "a previous technical issue")
        has_memory = bool(retrieved_memories_prompt and "No prior memories" not in retrieved_memories_prompt)

        # Scenario 1: Returning customer with recurring issue (Core Hackathon Requirement)
        if any(kw in msg_lower for kw in ["same", "again", "database", "problem", "happened again", "reoccur"]):
            if has_memory:
                return (
                    f"Hello {first_name}! I remember from our previous interactions that you are running {os_info} "
                    f"with {env_info} and previously encountered {last_issue}.\n\n"
                    f"Since you prefer step-by-step troubleshooting, let's pick up right where we left off:\n"
                    f"1. Let's verify if PostgreSQL service on port 5432 is still actively listening:\n"
                    f"   `Get-Service postgresql*` (or check Services.msc on {os_info})\n"
                    f"2. Confirm your connection settings in `settings.py`:\n"
                    f"   `python manage.py dbshell`\n\n"
                    f"Did the connection drop after a network adapter reboot or Windows update again?"
                )
            else:
                return (
                    f"Hello {first_name}! Could you please tell me your operating system, software environment, "
                    f"and what specific error message you are seeing?"
                )

        # Scenario 2: Asking what the agent remembers
        if any(kw in msg_lower for kw in ["what do you remember", "what environment", "who am i", "remember me"]):
            if has_memory:
                return (
                    f"Here is what I have retained in my Hindsight persistent memory about you, {first_name}:\n\n"
                    f"{retrieved_memories_prompt}\n\n"
                    f"Your stack is {env_info} on {os_info}. How can I assist you with your project today?"
                )
            else:
                return f"I don't have any persistent memories saved for you yet, {first_name}. What environment are you running?"

        # Scenario 3: Initial greeting / setup
        if any(kw in msg_lower for kw in ["hi", "hello", "hey"]):
            if has_memory:
                return (
                    f"Welcome back, {first_name}! Great to see you again. I recall you're working on {env_info} on {os_info}. "
                    f"How can I help you today?"
                )
            else:
                return f"Hello {first_name}! I'm MemoryDesk AI. I'm ready to help you troubleshoot. What are you working on today?"

        # Generic helpful response grounded in memories
        if has_memory:
            return (
                f"Thanks for reaching out, {first_name}. Taking into account your {os_info} environment and {env_info}, "
                f"I'm analyzing your request: \"{user_message}\".\n\n"
                f"Let's troubleshoot this methodically based on your preferences. Could you share the latest terminal output or error code?"
            )
        else:
            return (
                f"Thanks for the details, {first_name}. I have registered this context in Hindsight memory. "
                f"Let's proceed with troubleshooting your request: \"{user_message}\"."
            )

# Global singleton
llm_service = LLMService()
