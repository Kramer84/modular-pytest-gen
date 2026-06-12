import pytest
import json
import os
import urllib.error
from unittest.mock import patch, MagicMock

from modular_pytest_gen.client import OllamaClient, MistralClient

# --- Data Extraction Tests (No network mocking required) ---

def test_extract_from_markdown_python_block():
    client = OllamaClient()
    raw_response = "Here is your code:\n```python\n def test_foo():\n    assert True\n```\nHope it helps!"
    extracted = client._extract_from_markdown(raw_response)
    assert extracted == "def test_foo():\n    assert True"

def test_extract_from_markdown_generic_block():
    client = OllamaClient()
    raw_response = "```python\ndef test_bar(): pass\n```"
    extracted = client._extract_from_markdown(raw_response)
    assert extracted == "def test_bar(): pass"
    

def test_extract_from_markdown_no_block():
    client = OllamaClient()
    raw_response = "def test_baz(): pass"
    # Should safely fallback to stripping whitespace
    extracted = client._extract_from_markdown(raw_response)
    assert extracted == "def test_baz(): pass"

def test_extract_from_tool_string_args():
    client = OllamaClient()
    tool_calls = [{
        "function": {
            "name": "write_pytest_suite",
            "arguments": '{"pytest_code": "def test_tool(): pass"}'
        }
    }]
    extracted = client._extract_from_tool(tool_calls)
    assert extracted == "def test_tool(): pass"

def test_extract_from_tool_dict_args():
    client = OllamaClient()
    tool_calls = [{
        "function": {
            "name": "write_pytest_suite",
            "arguments": {"pytest_code": "def test_dict(): pass"}
        }
    }]
    extracted = client._extract_from_tool(tool_calls)
    assert extracted == "def test_dict(): pass"

def test_extract_from_tool_invalid_json():
    client = OllamaClient()
    tool_calls = [{
        "function": {
            "name": "write_pytest_suite",
            "arguments": '{"pytest_code": "def test_fail(): pass' # Missing closing brace/quote
        }
    }]
    extracted = client._extract_from_tool(tool_calls)
    assert extracted == "" # Should gracefully catch JSONDecodeError and return empty string

# --- Network & Payload Tests (Using unittest.mock) ---

@patch('urllib.request.urlopen')
def test_ollama_client_payload_formatting(mock_urlopen):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "message": {"content": "```python\npass\n```"}
    }).encode('utf-8')
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    client = OllamaClient(host="http://fakehost:11434", model="test-model")
    client.generate_test("sys prompt", "usr prompt")

    # Verify the request was made
    mock_urlopen.assert_called_once()
    request_obj = mock_urlopen.call_args[0][0]
    
    assert request_obj.full_url == "http://fakehost:11434/api/chat"
    assert request_obj.headers["Content-type"] == "application/json"
    
    # Verify payload content
    payload = json.loads(request_obj.data.decode('utf-8'))
    assert payload["model"] == "test-model"
    assert payload["messages"][0]["content"] == "sys prompt"
    assert payload["stream"] is False

@patch('urllib.request.urlopen')
def test_ollama_client_connection_error(mock_urlopen):
    # Simulate a network failure
    mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
    
    client = OllamaClient()
    with pytest.raises(ConnectionError, match="Failed to connect to Ollama"):
        client.generate_test("sys", "usr")

@patch.dict(os.environ, {"MISTRAL_API_KEY": "fake_key_123"})
@patch('urllib.request.urlopen')
def test_mistral_client_payload_formatting(mock_urlopen):
    # Setup mock response matching Mistral's schema
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "```python\npass\n```"}}]
    }).encode('utf-8')
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    client = MistralClient()
    client.generate_test("sys", "usr")

    mock_urlopen.assert_called_once()
    request_obj = mock_urlopen.call_args[0][0]
    
    assert request_obj.full_url == "https://api.mistral.ai/v1/chat/completions"
    assert request_obj.headers["Authorization"] == "Bearer fake_key_123"
    
    payload = json.loads(request_obj.data.decode('utf-8'))
    assert payload["temperature"] == 0.1

@patch.dict(os.environ, clear=True)
def test_mistral_client_missing_api_key():
    # MistralClient should fail immediately on init if the key is missing
    with pytest.raises(ValueError, match="MISTRAL_API_KEY environment variable is required"):
        MistralClient()