"""
LLM 모델 로더 - 3개 provider 지원 (OpenAI, Anthropic, Ollama)
"""

import json
import os
import requests
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


class ModelProvider(str, Enum):
    """지원하는 LLM Provider (3개 + OpenRouter 주석처리)"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class ModelInfo:
    """모델 정보 (3개 필드만)"""
    display_name: str
    model_name: str
    provider: ModelProvider
    api_key_available: bool = False


def load_cloud_models() -> List[ModelInfo]:
    """cloud_config.json에서 OpenAI/Anthropic 모델 로드"""
    config_path = Path(__file__).parent / "cloud_config.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            models_data = json.load(f)
        
        models = []
        for model_data in models_data:
            try:
                provider = ModelProvider(model_data["provider"])
                api_key_available = validate_api_key(provider)
                
                models.append(ModelInfo(
                    display_name=model_data["display_name"],
                    model_name=model_data["model_name"], 
                    provider=provider,
                    api_key_available=api_key_available
                ))
            except (ValueError, KeyError):
                # 지원하지 않는 provider이거나 잘못된 형식은 스킵
                continue
        
        return models
        
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_local_model_mappings() -> Dict[str, str]:
    """local_config.json에서 model_name -> display_name 매핑 로드"""
    config_path = Path(__file__).parent / "local_config.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            models_data = json.load(f)
        
        # model_name -> display_name 매핑 딕셔너리 생성
        mappings = {}
        for model_data in models_data:
            try:
                if model_data.get("provider") == "ollama":
                    mappings[model_data["model_name"]] = model_data["display_name"]
            except KeyError:
                continue
        
        return mappings
        
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_ollama_models_with_mappings() -> List[ModelInfo]:
    """실제 설치된 Ollama 모델을 가져와서 설정 파일의 display name 매핑 적용"""
    # 설정 파일에서 매핑 로드
    display_name_mappings = load_local_model_mappings()
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            models = []
            
            for model in models_data:
                model_name = model["name"]
                
                # 설정 파일에 매핑이 있으면 사용, 없으면 기본 형태
                if model_name in display_name_mappings:
                    display_name = display_name_mappings[model_name]
                else:
                    display_name = f"{model_name} (Installed)"
                
                models.append(ModelInfo(
                    display_name=display_name,
                    model_name=model_name,
                    provider=ModelProvider.OLLAMA,
                    api_key_available=True
                ))
            
            return models
    except requests.RequestException:
        pass
    
    return []


def get_openrouter_models() -> List[ModelInfo]:
    """OpenRouter 모델 (설정된 기본 모델들)"""
    if not os.getenv("OPENROUTER_API_KEY"):
        return []
    
    # 인기 있는 OpenRouter 모델들만 제공
    openrouter_models = [
        {
            "display_name": "DeepSeek Chat (Free)",
            "model_name": "deepseek/deepseek-chat-v3-0324:free",
            "provider": "openrouter"
        }
    ]
    
    return [
        ModelInfo(
            display_name=model["display_name"],
            model_name=model["model_name"],
            provider=ModelProvider.OPENROUTER,
            api_key_available=True
        )
        for model in openrouter_models
    ]


def validate_api_key(provider: ModelProvider) -> bool:
    """API 키 검증"""
    key_map = {
        ModelProvider.OPENAI: "OPENAI_API_KEY",
        ModelProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
        ModelProvider.GEMINI: "GOOGLE_API_KEY",
        ModelProvider.OPENROUTER: "OPENROUTER_API_KEY"
    }
    
    if provider == ModelProvider.OLLAMA:
        # Ollama 연결 확인
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=3)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    required_key = key_map.get(provider)
    if not required_key:
        return False

    raw_val = os.getenv(required_key)
    if not raw_val:
        return False

    val = raw_val.strip()
    if not val:
        return False

    # common placeholder values
    if val.lower() in {"your-api-key", "changeme", "replace_me"}:
        return False

    return True


def check_ollama_connection() -> Dict[str, Any]:
    """Ollama 연결 상태 확인 (기존 코드와 호환성 유지)"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return {
                "connected": True,
                "url": "http://localhost:11434",
                "models": [model.get("name", "") for model in models],
                "count": len(models)
            }
        else:
            return {
                "connected": False,
                "url": "http://localhost:11434",
                "error": f"HTTP {response.status_code}",
                "models": [],
                "count": 0
            }
    except requests.RequestException as e:
        return {
            "connected": False,
            "url": "http://localhost:11434",
            "error": str(e),
            "models": [],
            "count": 0
        }


def list_available_models() -> List[Dict[str, Any]]:
    """사용 가능한 모든 모델 목록 (CLI에서 사용) - 중복 제거 간소화"""
    all_models = []
    
    # 클라우드 모델들 (OpenAI/Anthropic)
    all_models.extend(load_cloud_models())
    
    # Ollama 모델들 (실제 설치된 것 + 설정 파일 매핑)
    all_models.extend(get_ollama_models_with_mappings())
    
    # OpenRouter 모델들
    all_models.extend(get_openrouter_models())
    
    return [
        {
            "display_name": model.display_name,
            "model_name": model.model_name,
            "provider": model.provider.value,
            "api_key_available": model.api_key_available
        }
        for model in all_models
    ]


def load_llm_model(model_name: str, provider: str, temperature: float = 0.0):
    """실제 LLM 모델 로드 - 각 provider별로 직접 Chat 클래스 사용"""
    try:
        provider_enum = ModelProvider(provider)
    except ValueError:
        raise ValueError(f"Unsupported provider: {provider}")
    
    # 각 provider별로 직접 Chat 클래스 사용 (temperature=0 고정)
    if provider_enum == ModelProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name,
            temperature=0
        )
    
    elif provider_enum == ModelProvider.OPENAI:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            # temperature=0
        )

    elif provider_enum == ModelProvider.GEMINI:
        import google.generativeai as genai
        print("\n--- AVAILABLE GEMINI MODELS ---")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
        print("-----------------------------\n")

        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
        )
    
    elif provider_enum == ModelProvider.OLLAMA:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model_name,
            temperature=0
        )
    
    elif provider_enum == ModelProvider.OPENROUTER:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers={
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "Decepticon"
            }
        )
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# Export main functions
__all__ = [
    "load_llm_model", 
    "list_available_models",
    "validate_api_key",
    "check_ollama_connection",
    "ModelProvider",
    "ModelInfo",
    # 핵심 함수들
    "load_cloud_models",
    "load_local_model_mappings",
    "get_ollama_models_with_mappings"
]
