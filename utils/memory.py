"""
LangGraph Persistence Configuration
중앙 집중식 Checkpoint와 Store 설정
"""

import os
import logging
from typing import Optional
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

# 전역 인스턴스들
_checkpointer: Optional[InMemorySaver] = None
_store: Optional[InMemoryStore] = None


def _get_openrouter_api_key() -> str:
    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if key:
        return key
    try:
        import streamlit as st
        return str(st.secrets.get("OPENROUTER_API_KEY", "")).strip()
    except Exception:
        return ""


def _get_openrouter_api_base() -> str:
    return "https://openrouter.ai/api/v1"


def _create_openrouter_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="openai/text-embedding-3-small",
        openai_api_base=_get_openrouter_api_base(),
        openai_api_key=_get_openrouter_api_key(),
        default_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "Decepticon",
        },
    )

def get_checkpointer() -> InMemorySaver:
    """
    중앙 집중식 Checkpointer 인스턴스 반환
    
    Returns:
        InMemorySaver: 메모리 기반 체크포인터
    """
    global _checkpointer
    
    if _checkpointer is None:
        _checkpointer = InMemorySaver()
        logger.info("InMemorySaver checkpointer initialized")
    
    return _checkpointer

def get_store() -> InMemoryStore:
    """
    중앙 집중식 Store 인스턴스 반환
    
    Returns:
        InMemoryStore: 메모리 기반 스토어 (벡터 인덱스 포함)
    """
    global _store
    
    if _store is None:
        api_key = _get_openrouter_api_key()
        if api_key:
            _store = InMemoryStore(
                index={
                    "dims": 1536,
                    "embed": _create_openrouter_embeddings(),
                    "fields": ["text"],
                }
            )
            logger.info("InMemoryStore initialized with vector index")
        else:
            _store = InMemoryStore()
            logger.info("InMemoryStore initialized without vector index")
    
    return _store

def reset_persistence():
    """
    개발용: 모든 persistence 인스턴스 재설정
    """
    global _checkpointer, _store
    
    _checkpointer = None
    _store = None
    logger.info("Persistence instances reset")

def get_persistence_status() -> dict:
    """
    현재 persistence 상태 반환 (디버깅용)
    
    Returns:
        dict: 현재 상태 정보
    """
    return {
        "checkpointer_initialized": _checkpointer is not None,
        "store_initialized": _store is not None,
        "checkpointer_type": type(_checkpointer).__name__ if _checkpointer else None,
        "store_type": type(_store).__name__ if _store else None,
    }

def create_thread_config(user_id: str, conversation_id: Optional[str] = None) -> dict:
    """
    스레드별 설정 생성
    
    Args:
        user_id: 사용자 ID
        conversation_id: 대화 ID (옵션)
    
    Returns:
        dict: LangGraph config 딕셔너리
    """
    thread_id = f"user_{user_id}"
    if conversation_id:
        thread_id += f"_conv_{conversation_id}"
    
    recursion_limit = int(os.getenv("RECURSION_LIMIT", "100"))

    config = {
        "recursion_limit": recursion_limit,
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "main"
        }
    }
    
    logger.debug(f"Created thread config: {config}")
    return config

# 개발 편의를 위한 헬퍼 함수들
def create_memory_namespace(user_id: str, namespace_type: str = "memories") -> tuple:
    """
    메모리 네임스페이스 생성
    
    Args:
        user_id: 사용자 ID
        namespace_type: 네임스페이스 타입 (memories, preferences, etc.)
    
    Returns:
        tuple: LangMem 네임스페이스 튜플
    """
    return (namespace_type, user_id)

def get_debug_info() -> dict:
    """
    디버깅용 정보 반환
    
    Returns:
        dict: 현재 persistence 상태와 통계
    """
    status = get_persistence_status()
    
    # 추가 디버그 정보
    debug_info = status.copy()
    
    if _checkpointer:
        # InMemorySaver는 내부 상태 접근이 제한적이므로 기본 정보만
        debug_info["checkpointer_class"] = str(type(_checkpointer))
    
    if _store:
        debug_info["store_class"] = str(type(_store))
        # InMemoryStore 내부 정보 (가능한 범위에서)
        try:
            debug_info["store_has_index"] = hasattr(_store, 'index')
        except:
            debug_info["store_has_index"] = False
    
    return debug_info
