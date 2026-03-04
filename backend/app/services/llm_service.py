import httpx
import requests
import re
import asyncio
from typing import Dict
from ..config import OLLAMA_URL, MODEL_NAME, LLM_TEMPERATURE, LLM_TIMEOUT, OLLAMA_NUM_GPU

# Simple in-memory cache for LLM responses
llm_cache: Dict[str, str] = {}

async def call_llm_async(prompt: str) -> str:
    """Call the Ollama LLM asynchronously with a simple in-memory cache."""
    # Check cache first
    if prompt in llm_cache:
        print(f"[LLM_SERVICE] Cache hit for prompt (length: {len(prompt)})")
        return llm_cache[prompt]

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": LLM_TEMPERATURE,
                        "num_gpu": OLLAMA_NUM_GPU,
                    }
                }
            )

            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")

            result = response.json()["response"]
            # Store in cache
            llm_cache[prompt] = result
            return result
    except Exception as e:
        print(f"[LLM_SERVICE] Async call error: {str(e)}")
        # Fallback to sync call if async fails for some reason
        return call_llm(prompt)

def call_llm(prompt: str) -> str:
    """Call the Ollama LLM with the given prompt (synchronous)."""
    # Check cache first
    if prompt in llm_cache:
        print(f"[LLM_SERVICE] Cache hit for prompt {prompt[:50]}...")
        return llm_cache[prompt]

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": LLM_TEMPERATURE,
                    "num_gpu": OLLAMA_NUM_GPU,
                }
            },
            timeout=LLM_TIMEOUT
        )

        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.status_code}")

        result = response.json()["response"]
        # Store in cache
        llm_cache[prompt] = result
        return result
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ollama connection error: {str(e)}")


def extract_json(text: str) -> str:
    """Extract JSON from LLM response."""
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    
    if json_start != -1 and json_end > json_start:
        return text[json_start:json_end]
    
    # Try to find JSON between markdown code blocks
    pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    
    return '{}'
