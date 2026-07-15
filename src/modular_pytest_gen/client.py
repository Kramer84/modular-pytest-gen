import abc
import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class BaseLLMClient(abc.ABC):
    r"""
    Define the abstract base class for LLM clients.

    This class serves as the foundation for all LLM client implementations,
    providing the core structure and methods required for generating tests
    and processing responses.

    Methods
    -------
    generate_test :
        Generate a test based on the provided prompts and tool schema.
    _extract_from_tool :
        Extract arguments from tool calls.
    _extract_from_markdown :
        Extract code blocks from markdown text.
    """

    @abc.abstractmethod
    def generate_test(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
    ) -> str:
        r"""
        Generate a unit test from prompts and optional tool schema.

        The test is generated using a local or remote LLM. The output is
        validated by executing it in a subprocess. If the test fails, a
        root-cause analysis is performed to determine the cause of the
        failure. The temperature is dynamically scaled to force creative
        code alternatives.

        Parameters
        ----------
        system_prompt : str
            The system prompt to use for the LLM.
        user_prompt : str
            The user prompt to use for the LLM.
        tool_schema : Optional[Dict[str, Any]], optional
            The optional tool schema to use for the LLM.
        temperature : float, optional
            The temperature to use for the LLM.

        Returns
        -------
        str
            The generated test.

        Raises
        ------
        ValueError
            If the system prompt is empty.

            If the user prompt is empty.
        """

        pass

    def _extract_from_tool(self, tool_calls: list) -> str:
        r"""
        Extract arguments from tool calls.

        Iterates through a list of tool calls to extract and return the
        arguments from the first valid call.

        Parameters
        ----------
        tool_calls : list
            A list of tool call objects, each containing function details.

        Returns
        -------
        str
            Returns a JSON string of the arguments if they are a
            dictionary, otherwise returns the string representation of the
            arguments.

            Returns an empty string if the tool_calls list is empty or if
            no valid arguments are found.
        """

        if not tool_calls:
            return ""
        for call in tool_calls:
            args = call["function"].get("arguments", "")
            if isinstance(args, dict):
                return json.dumps(args)
            return str(args).strip()
        return ""

    def _extract_from_markdown(self, text: str) -> str:
        r"""
        Extracts Python code blocks from Markdown text.

        This method processes Markdown-formatted text to extract Python
        code blocks enclosed in triple backticks. It handles both
        explicitly labeled Python blocks and generic code blocks.

        Parameters
        ----------
        text : str
            The Markdown-formatted text containing potential Python code
            blocks.

        Returns
        -------
        str
            The extracted Python code block if found, otherwise the
            stripped input text.

        Raises
        ------
        ValueError
            If the input text contains malformed Markdown code blocks.
        """

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
    r"""
    Initialize an Ollama client for test generation.

    Configures the Ollama API endpoint and model parameters for test
    generation.

    Parameters
    ----------
    host : str, optional
        The base URL of the Ollama server. Default is
        http://localhost:11434.
    model : str, optional
        The model identifier to use for test generation. Default is
        qwen2.5-coder:7b-instruct-q8_0.

    Methods
    -------
    generate_test :
        Generate a test based on the provided prompts and tool schema.

    Raises
    ------
    ConnectionError
        If the API request times out after 60 seconds.

        If the Ollama server is not running or unreachable.

    See Also
    --------
    modular_pytest_gen.BaseLLMClient :
        The abstract base class for LLM clients.
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b-instruct-q8_0",
    ):
        r"""
        Initialize the Ollama client with a specified host and model.

        Creates an instance of the Ollama client configured to interact
        with a specified host and model. The host URL is normalized to
        remove any trailing slashes, and the API endpoint is constructed by
        appending '/api/chat' to the normalized host URL.

        Warnings
        --------
        Ensure the specified host and model are accessible and correctly
        configured to avoid connection errors.

        See Also
        --------
        ollama.generate :
            Generates text using the configured Ollama model.
        ollama.chat :
            Initiates a chat session with the configured Ollama model.

        Notes
        -----
        The host URL is normalized to ensure consistent API endpoint
        construction.
        """

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
        r"""
        Generate a unit test from a system and user prompt.

        The method constructs a JSON payload with the provided prompts and
        optional tool schema, then sends it to the API endpoint. The
        response is parsed to extract either tool call data or markdown
        content.

        Parameters
        ----------
        system_prompt : str
            The system-level instructions for the test generation.
        user_prompt : str
            The user-specific requirements for the test.
        tool_schema : Optional[Dict[str, Any]], optional
            The schema defining the structure of the tool call response.
        temperature : float, optional
            The randomness factor for the model's output. Default is 0.1.

        Returns
        -------
        str
            The generated test code as a string.

        Raises
        ------
        ConnectionError
            If the API request times out after 60 seconds.

            If the connection to the Ollama server fails.
        """

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
    r"""
    Initialize a client for the Mistral API.

    This class provides an interface to interact with the Mistral API,
    allowing users to generate tests and process responses.

    Parameters
    ----------
    model : str, optional
        The model identifier to use for generating tests. Default is
        codestral-latest.

    Attributes
    ----------
    model : str
        The model identifier used for generating tests.
    api_url : str
        The URL of the Mistral API endpoint.
    api_key : str
        The API key for authenticating with the Mistral API.

    Methods
    -------
    generate_test :
        Generate a test based on the provided prompts and tool schema.

    Raises
    ------
    ValueError
        The MISTRAL_API_KEY environment variable is required to use
        MistralClient.

    See Also
    --------
    modular_pytest_gen.BaseLLMClient :
        The abstract base class for LLM clients.
    """

    def __init__(self, model: str = "codestral-latest"):
        r"""
        Initialize a MistralClient instance.

        Creates a client for interacting with the Mistral API, validating
        the presence of the required API key environment variable.

        Warnings
        --------
        Ensure the `MISTRAL_API_KEY` environment variable is set before
        initializing the client.

        See Also
        --------
        MistralClient.generate :
            Method for generating completions using the Mistral API.

        Notes
        -----
        The client requires the `MISTRAL_API_KEY` environment variable to
        be set for authentication.
        """

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
        r"""
        Generate a unit test from prompts and optional tool schema.

        Constructs a test case by combining system and user prompts, then
        executes the request against the configured LLM API. If a tool
        schema is provided, the response is parsed for tool call data;
        otherwise, the raw content is returned.

        Parameters
        ----------
        system_prompt : str
            The system-level instructions for the LLM.
        user_prompt : str
            The user-specific query or context.
        tool_schema : Optional[Dict[str, Any]], optional
            The JSON schema defining the tool interface for structured
            responses.
        temperature : float, optional
            The randomness parameter for the LLM response.

        Returns
        -------
        str
            The generated test content, either extracted from tool calls or
            raw response text.

        Raises
        ------
        ConnectionError
            If the API request times out after 60 seconds.

            If the API request fails due to network or server issues.
        """

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
    r"""
    Unload an Ollama model

    This function stops the specified Ollama model and cleans up its
    resources.

    Parameters
    ----------
    model_name : str
        The name of the Ollama model to unload

    Raises
    ------
    Exception
        An error occurred while unloading the model
    """

    print(
        f"\n[CLEANUP] Stopping Ollama model context framework execution for: {model_name}"
    )
    try:
        subprocess.run(["ollama", "stop", model_name], capture_output=True, text=True)
        print("[CLEANUP] Model unloaded successfully.")
    except Exception as e:
        print(f"[WARN] Failed to issue explicit system model cleanup command: {e}")
