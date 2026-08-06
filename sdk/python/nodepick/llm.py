import json
import httpx
from typing import Optional, List, Dict, Any

class BaseLLMProvider:
    def __init__(self, model: str):
        self.model = model
        self.system_instruction: Optional[str] = None

    def clear_history(self):
        raise NotImplementedError()

    def set_system_instruction(self, instruction: str):
        self.system_instruction = instruction

    def add_user_message(self, message: str):
        raise NotImplementedError()

    async def generate(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError()

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError()

    def extract_text_response(self, response: Dict[str, Any]) -> str:
        raise NotImplementedError()

    def add_tool_results(self, response: Dict[str, Any], results: List[Dict[str, Any]]):
        raise NotImplementedError()


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str = "https://api.openai.com/v1"):
        super().__init__(model)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.messages: List[Dict[str, Any]] = []

    def clear_history(self):
        self.messages = []

    def add_user_message(self, message: str):
        self.messages.append({"role": "user", "content": message})

    async def generate(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Format tools
        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"]
                }
            })

        payload = {
            "model": self.model,
            "messages": self.messages,
        }
        if self.system_instruction:
            # For OpenAI, system instruction can be placed as a developer/system message at start
            if not self.messages or self.messages[0]["role"] != "system":
                self.messages.insert(0, {"role": "system", "content": self.system_instruction})
        
        if openai_tools:
            payload["tools"] = openai_tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        message = response["choices"][0]["message"]
        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            return []
            
        calls = []
        for tc in tool_calls:
            calls.append({
                "id": tc["id"],
                "name": tc["function"]["name"],
                "args": json.loads(tc["function"]["arguments"])
            })
        return calls

    def extract_text_response(self, response: Dict[str, Any]) -> str:
        return response["choices"][0]["message"].get("content") or ""

    def add_tool_results(self, response: Dict[str, Any], results: List[Dict[str, Any]]):
        message = response["choices"][0]["message"]
        self.messages.append(message)
        for r in results:
            self.messages.append({
                "role": "tool",
                "tool_call_id": r["id"],
                "name": r["name"],
                "content": r["content"]
            })


class OllamaProvider(OpenAIProvider):
    """Ollama uses the exact same Chat Completion schema as OpenAI."""
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        # Ollama has an OpenAI-compatible endpoint at /v1
        super().__init__(api_key="ollama", model=model, base_url=f"{base_url.rstrip('/')}/v1")


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-latest"):
        super().__init__(model)
        self.api_key = api_key
        self.messages: List[Dict[str, Any]] = []

    def clear_history(self):
        self.messages = []

    def add_user_message(self, message: str):
        self.messages.append({"role": "user", "content": message})

    async def generate(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        anthropic_tools = []
        for t in tools:
            anthropic_tools.append({
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"]
            })

        payload = {
            "model": self.model,
            "messages": self.messages,
            "max_tokens": 4096
        }
        
        if self.system_instruction:
            payload["system"] = self.system_instruction

        if anthropic_tools:
            payload["tools"] = anthropic_tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        calls = []
        for block in response.get("content", []):
            if block["type"] == "tool_use":
                calls.append({
                    "id": block["id"],
                    "name": block["name"],
                    "args": block["input"]
                })
        return calls

    def extract_text_response(self, response: Dict[str, Any]) -> str:
        text_parts = []
        for block in response.get("content", []):
            if block["type"] == "text":
                text_parts.append(block["text"])
        return "\n".join(text_parts)

    def add_tool_results(self, response: Dict[str, Any], results: List[Dict[str, Any]]):
        self.messages.append({
            "role": "assistant",
            "content": response["content"]
        })
        
        tool_results_content = []
        for r in results:
            tool_results_content.append({
                "type": "tool_result",
                "tool_use_id": r["id"],
                "content": r["content"]
            })
            
        self.messages.append({
            "role": "user",
            "content": tool_results_content
        })


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        super().__init__(model)
        self.api_key = api_key
        self.contents: List[Dict[str, Any]] = []

    def clear_history(self):
        self.contents = []

    def add_user_message(self, message: str):
        self.contents.append({
            "role": "user",
            "parts": [{"text": message}]
        })

    async def generate(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        gemini_tools = []
        for t in tools:
            # Gemini expects parameter types and structures
            gemini_tools.append({
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"]
            })

        payload = {
            "contents": self.contents
        }
        
        if self.system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": self.system_instruction}]
            }

        if gemini_tools:
            payload["tools"] = [{"functionDeclarations": gemini_tools}]

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        calls = []
        parts = response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        for i, part in enumerate(parts):
            fc = part.get("functionCall")
            if fc:
                calls.append({
                    "id": f"call_{i}",  # Gemini doesn't have call IDs, generate dummy one
                    "name": fc["name"],
                    "args": fc.get("args", {})
                })
        return calls

    def extract_text_response(self, response: Dict[str, Any]) -> str:
        parts = response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text_parts = []
        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
        return "\n".join(text_parts)

    def add_tool_results(self, response: Dict[str, Any], results: List[Dict[str, Any]]):
        content = response["candidates"][0]["content"]
        self.contents.append(content)
        
        parts = []
        for r in results:
            parts.append({
                "functionResponse": {
                    "name": r["name"],
                    "response": {"output": r["content"]}
                }
            })
            
        self.contents.append({
            "role": "user",
            "parts": parts
        })


class AgentLoop:
    def __init__(self, provider: BaseLLMProvider, mcp_client: Any):
        self.provider = provider
        self.mcp_client = mcp_client

    async def run(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Run the agent loop to fetch tools and complete user requests recursively."""
        tools = await self.mcp_client.list_tools()
        
        self.provider.clear_history()
        if system_instruction:
            self.provider.set_system_instruction(system_instruction)
            
        self.provider.add_user_message(prompt)
        
        max_steps = 15
        for _ in range(max_steps):
            response = await self.provider.generate(tools)
            tool_calls = self.provider.extract_tool_calls(response)
            
            if not tool_calls:
                return self.provider.extract_text_response(response)
                
            tool_results = []
            for tool_call in tool_calls:
                name = tool_call["name"]
                args = tool_call["args"]
                call_id = tool_call["id"]
                
                try:
                    result = await self.mcp_client.call_tool(name, args)
                    text_parts = []
                    for c in result.get("content", []):
                        if c["type"] == "text":
                            text_parts.append(c["text"])
                    result_str = "\n".join(text_parts) if text_parts else "Success"
                    if result.get("is_error"):
                        result_str = f"Error: {result_str}"
                except Exception as e:
                    result_str = f"Error executing tool: {str(e)}"
                    
                tool_results.append({
                    "id": call_id,
                    "name": name,
                    "content": result_str
                })
                
            self.provider.add_tool_results(response, tool_results)
            
        raise RuntimeError("Agent loop exceeded maximum execution steps (15)")
