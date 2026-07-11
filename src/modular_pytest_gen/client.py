import abc
import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class BaseLLMClient(abc.ABC):
    """
    Abstract base class for LLM API interaction.
    Houses common data extraction logic to ensure provider agnosticism.
    """

    @abc.abstractmethod
    def generate_test(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
    ) -> str:
        """Sends the payload to the LLM and returns raw text or valid JSON string."""
        pass

    def _extract_from_tool(self, tool_calls: list) -> str:
        """Extracts the raw JSON arguments payload from a structured tool call."""
        for call in tool_calls:
            if call.get("function", {}).get("name") == "write_pytest_suite":
                args = call["function"].get("arguments", "")
                if isinstance(args, dict):
                    return json.dumps(args)
                return str(args).strip()
        return ""

    def _extract_from_markdown(self, text: str) -> str:
        """Strips conversational fluff and extracts code from markdown backticks."""
        if "```python" in text:
            blocks = text.split("```python")
            if len(blocks) > 1:
                return blocks[1].split("```")[0].strip()
        elif "```" in text:
            blocks = text.split("```")
            if len(blocks) > 1:
                return blocks[1].split("```")[0].strip()
        return text.strip()


class OllamaClient(BaseLLMClient):
    """Manages local communication with Ollama endpoints."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b-instruct-q8_0",
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.api_url = f"{self.host}/api/chat"

    def generate_test(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature, "top_p": 0.9},
        }
        if tool_schema:
            payload["tools"] = [tool_schema]
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60.0) as response:
                result = json.loads(response.read().decode("utf-8"))
        except TimeoutError:
            raise ConnectionError(f"API request timed out after 60 seconds.")
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self.host}. Is it running? Error: {e}"
            )
        message = result.get("message", {})
        if tool_schema and "tool_calls" in message:
            extracted = self._extract_from_tool(message["tool_calls"])
            if extracted:
                return extracted
        return self._extract_from_markdown(message.get("content", ""))


class MistralClient(BaseLLMClient):
    """Manages communication with the remote Mistral API."""

    def __init__(self, model: str = "codestral-latest"):
        self.model = model
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.api_key = os.environ.get("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "MISTRAL_API_KEY environment variable is required to use MistralClient."
            )

    def generate_test(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if tool_schema:
            payload["tools"] = [tool_schema]
            payload["tool_choice"] = "any"
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(self.api_url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60.0) as response:
                result = json.loads(response.read().decode("utf-8"))
        except TimeoutError:
            raise ConnectionError(f"API request timed out after 60 seconds.")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Mistral API request failed: {e}")
        message = result.get("choices", [{}])[0].get("message", {})
        if tool_schema and "tool_calls" in message:
            extracted = self._extract_from_tool(message["tool_calls"])
            if extracted:
                return extracted
        return self._extract_from_markdown(message.get("content", ""))


def unload_ollama_model(model_name: str):
    """Issues a direct background subprocess system command call to unload the active model."""
    print(
        f"\n[CLEANUP] Stopping Ollama model context framework execution for: {model_name}"
    )
    try:
        subprocess.run(["ollama", "stop", model_name], capture_output=True, text=True)
        print("[CLEANUP] Model unloaded successfully.")
    except Exception as e:
        print(f"[WARN] Failed to issue explicit system model cleanup command: {e}")
