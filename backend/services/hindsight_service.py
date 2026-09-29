import os
import json
import logging
import uuid
import socket
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import hindsight_client
from hindsight_client import Hindsight, RecallResponse, RetainResponse, ListMemoryUnitsResponse

from backend.config import HINDSIGHT_URL, HINDSIGHT_API_KEY, DATA_DIR
from backend.models import MemoryItemDetail

logger = logging.getLogger("memorydesk.hindsight")
logger.setLevel(logging.INFO)

LOCAL_MEMORY_DIR = DATA_DIR / "local_memory_banks"
LOCAL_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def _quick_socket_probe(url: str, timeout: float = 0.5) -> bool:
    """Fast check whether the Hindsight host:port is reachable."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

class HindsightService:
    """
    Official Hindsight Integration Service for MemoryDesk AI.
    Uses the official hindsight-client Python SDK (v0.10.x) provided by Vectorize.io.
    """

    def __init__(self, base_url: str = HINDSIGHT_URL, api_key: Optional[str] = HINDSIGHT_API_KEY):
        self.base_url = base_url.rstrip("/") if base_url else "http://localhost:8888"
        self.api_key = api_key if api_key else None
        self._is_connected = False
        self._server_version = None
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
            self.client = Hindsight(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=2.0
            )
        except Exception as e:
            logger.warning(f"Error initializing Hindsight client: {e}")
            self.client = None

    def check_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Fast probe and check connection against official Hindsight server.
        """
        is_port_open = _quick_socket_probe(self.base_url, timeout=0.3)
        if not is_port_open:
            self._is_connected = False
            self._server_version = None
            return False, f"Server at {self.base_url} is currently offline"

        if not self.client:
            self._init_client()

        try:
            version_info = self.client.get_version()
            version_str = getattr(version_info, "version", "connected")
            self._is_connected = True
            self._server_version = str(version_str)
            return True, self._server_version
        except Exception as e:
            self._is_connected = False
            self._server_version = None
            return False, str(e)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    # -------------------------------------------------------------
    # Local Persistence Bank (Ensures zero data loss & offline demo resilience)
    # -------------------------------------------------------------
    def _get_local_bank_file(self, bank_id: str) -> Path:
        return LOCAL_MEMORY_DIR / f"{bank_id}.json"

    def _load_local_bank(self, bank_id: str) -> List[Dict[str, Any]]:
        bank_file = self._get_local_bank_file(bank_id)
        if not bank_file.exists():
            return []
        try:
            with open(bank_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_local_bank(self, bank_id: str, items: List[Dict[str, Any]]):
        bank_file = self._get_local_bank_file(bank_id)
        with open(bank_file, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)

    # -------------------------------------------------------------
    # Core Operation 1: Store Memory (Retain)
    # -------------------------------------------------------------
    def store_memory(
        self,
        customer_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, MemoryItemDetail]:
        """
        Store a new memory unit for a customer.
        Calls official Hindsight client.retain(bank_id=..., content=...) when online.
        Guarantees local persistence in bank.
        """
        now_iso = datetime.utcnow().isoformat()
        memory_id = f"mem_{uuid.uuid4().hex[:10]}"
        tags = tags or ["customer_support", "context"]
        metadata = metadata or {}

        if self._is_connected and self.client:
            try:
                retain_res: RetainResponse = self.client.retain(
                    bank_id=customer_id,
                    content=content,
                    metadata={str(k): str(v) for k, v in metadata.items()},
                    tags=tags
                )
                if retain_res and getattr(retain_res, "success", True):
                    logger.info(f"Retained in official Hindsight bank '{customer_id}': {content[:60]}")
            except Exception as e:
                logger.debug(f"Official retain failed: {e}")
                self._is_connected = False

        # Write to local memory bank for guaranteed persistence
        local_items = self._load_local_bank(customer_id)
        if not any(item["text"].strip().lower() == content.strip().lower() for item in local_items):
            new_item = {
                "id": memory_id,
                "text": content,
                "type": metadata.get("type", "fact"),
                "created_at": now_iso,
                "metadata": metadata,
                "tags": tags
            }
            local_items.append(new_item)
            self._save_local_bank(customer_id, local_items)

        item_detail = MemoryItemDetail(
            id=memory_id,
            text=content,
            type=metadata.get("type", "fact"),
            created_at=now_iso,
            metadata=metadata,
            tags=tags
        )
        return True, item_detail

    # -------------------------------------------------------------
    # Core Operation 2: Retrieve Relevant Memories (Recall)
    # -------------------------------------------------------------
    def retrieve_relevant_memories(
        self,
        customer_id: str,
        query: str,
        limit: int = 5
    ) -> Tuple[List[MemoryItemDetail], str]:
        """
        Recalls the most relevant memories for the current customer message.
        Calls official client.recall() when online.
        """
        results: List[MemoryItemDetail] = []
        prompt_string = ""

        if self._is_connected and self.client:
            try:
                recall_res: RecallResponse = self.client.recall(
                    bank_id=customer_id,
                    query=query,
                    max_tokens=2048,
                    budget="mid"
                )
                if recall_res and getattr(recall_res, "results", None):
                    for r in recall_res.results[:limit]:
                        results.append(MemoryItemDetail(
                            id=getattr(r, "id", str(uuid.uuid4().hex[:8])),
                            text=getattr(r, "text", ""),
                            type=getattr(r, "type", "fact"),
                            created_at=getattr(r, "mentioned_at", None) or datetime.utcnow().isoformat(),
                            relevance_score=r.scores.get("similarity", 0.9) if hasattr(r, "scores") and r.scores else 0.9,
                            metadata=getattr(r, "metadata", None),
                            tags=getattr(r, "tags", None)
                        ))
                    
                    if hasattr(recall_res, "to_prompt_string"):
                        prompt_string = recall_res.to_prompt_string()
                    else:
                        prompt_string = "\n".join([f"- {item.text}" for item in results])
                    
                    return results, prompt_string
            except Exception as e:
                logger.debug(f"Official recall error: {e}")
                self._is_connected = False

        # Relevance scoring across local memory bank
        local_items = self._load_local_bank(customer_id)
        if not local_items:
            return [], ""

        query_lower = query.lower()
        query_words = set(query_lower.replace("?", "").replace(".", "").replace(",", "").split())
        
        scored_items = []
        for item in local_items:
            item_text = item["text"].lower()
            text_words = set(item_text.split())
            overlap = query_words.intersection(text_words)
            
            domain_bonus = 0.0
            for term in ["django", "database", "python", "windows", "macos", "ubuntu", "docker", "cuda", "preference", "step-by-step"]:
                if term in query_lower and term in item_text:
                    domain_bonus += 0.4
            
            score = (len(overlap) / max(len(query_words), 1)) * 0.6 + domain_bonus
            # Base relevance for customer environment facts
            if item.get("type") in ("environment", "preference", "identity", "fact"):
                score += 0.25
            scored_items.append((score, item))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        top_items = [it for score, it in scored_items[:limit]]

        for it in top_items:
            results.append(MemoryItemDetail(
                id=it["id"],
                text=it["text"],
                type=it.get("type", "fact"),
                created_at=it.get("created_at", datetime.utcnow().isoformat()),
                relevance_score=round(min(1.0, 0.8 + len(it["text"]) * 0.001), 2),
                metadata=it.get("metadata"),
                tags=it.get("tags")
            ))

        prompt_string = "\n".join([f"- {it.text}" for it in results])
        return results, prompt_string

    # -------------------------------------------------------------
    # Core Operation 3: Search Memory
    # -------------------------------------------------------------
    def search_memory(self, customer_id: str, query: str, limit: int = 5) -> List[MemoryItemDetail]:
        items, _ = self.retrieve_relevant_memories(customer_id, query, limit)
        return items

    # -------------------------------------------------------------
    # Core Operation 4: Customer Memory & Timeline
    # -------------------------------------------------------------
    def get_customer_memory(self, customer_id: str) -> Dict[str, Any]:
        memories: List[MemoryItemDetail] = []
        
        if self._is_connected and self.client:
            try:
                list_res: ListMemoryUnitsResponse = self.client.list_memories(bank_id=customer_id, limit=50)
                if list_res and getattr(list_res, "items", None):
                    for item in list_res.items:
                        memories.append(MemoryItemDetail(
                            id=getattr(item, "id", str(uuid.uuid4().hex[:8])),
                            text=getattr(item, "text", ""),
                            type=getattr(item, "fact_type", "fact") or "fact",
                            created_at=getattr(item, "mentioned_at", None) or getattr(item, "var_date", None) or datetime.utcnow().isoformat(),
                            metadata=getattr(item, "metadata", None),
                            tags=getattr(item, "tags", None)
                        ))
            except Exception as e:
                logger.debug(f"Official list_memories error: {e}")
                self._is_connected = False

        # Load from bank for complete records
        local_items = self._load_local_bank(customer_id)
        seen_texts = {m.text.strip().lower() for m in memories}
        for item in local_items:
            if item["text"].strip().lower() not in seen_texts:
                memories.append(MemoryItemDetail(
                    id=item["id"],
                    text=item["text"],
                    type=item.get("type", "fact"),
                    created_at=item.get("created_at", datetime.utcnow().isoformat()),
                    metadata=item.get("metadata"),
                    tags=item.get("tags")
                ))

        memories.sort(key=lambda x: x.created_at)
        timeline = []
        for idx, m in enumerate(memories, 1):
            category = "General"
            txt_l = m.text.lower()
            if "name" in txt_l or "customer is" in txt_l:
                category = "Identity"
            elif "operating system" in txt_l or "windows" in txt_l or "macos" in txt_l or "ubuntu" in txt_l:
                category = "Operating System"
            elif "python" in txt_l or "django" in txt_l or "node" in txt_l or "pytorch" in txt_l:
                category = "Environment & Stack"
            elif "preference" in txt_l or "prefers" in txt_l:
                category = "Support Preference"
            elif "database" in txt_l or "docker" in txt_l or "cuda" in txt_l or "error" in txt_l or "timeout" in txt_l or "resolved" in txt_l:
                category = "Issue & Solution"

            timeline.append({
                "step": idx,
                "label": f"Learned {category}",
                "summary": m.text,
                "type": m.type,
                "created_at": m.created_at
            })

        structured_profile = {
            "name": None,
            "os": None,
            "environment": None,
            "previous_issue": None,
            "preference": None
        }
        for m in memories:
            txt = m.text
            txt_l = txt.lower()
            if "customer is" in txt_l:
                structured_profile["name"] = txt.split(",")[0].replace("Customer is", "").strip()
            if "windows" in txt_l or "macos" in txt_l or "ubuntu" in txt_l:
                structured_profile["os"] = txt
            if "django" in txt_l or "python" in txt_l or "pytorch" in txt_l or "node" in txt_l:
                structured_profile["environment"] = txt
            if "database" in txt_l or "docker" in txt_l or "error" in txt_l:
                structured_profile["previous_issue"] = txt
            if "prefers" in txt_l or "preference" in txt_l:
                structured_profile["preference"] = txt

        return {
            "customer_id": customer_id,
            "total_memories": len(memories),
            "memories": memories,
            "timeline": timeline,
            "structured_profile": structured_profile,
            "hindsight_connected": self._is_connected
        }

    def seed_customer_memories(self, customer_id: str, seed_texts: List[str]):
        local_items = self._load_local_bank(customer_id)
        if local_items:
            return
        for text in seed_texts:
            self.store_memory(
                customer_id=customer_id,
                content=text,
                metadata={"source": "seed_profile", "type": "fact"},
                tags=["seed", "profile"]
            )

    def close(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass

hindsight_service = HindsightService()
