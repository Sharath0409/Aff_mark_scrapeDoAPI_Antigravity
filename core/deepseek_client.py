import json
from types import SimpleNamespace
from urllib.parse import urljoin
import requests
import logging


class DeepseekResponse(SimpleNamespace):
    def __init__(self, api_response):
        self.raw = api_response

        if isinstance(api_response, str):
            self.choices = [SimpleNamespace(message=SimpleNamespace(content=api_response))]
            self.data = []
            return

        choices = []
        if isinstance(api_response, dict) and api_response.get("choices"):
            for choice in api_response.get("choices", []):
                message = choice.get("message", {})
                choice_copy = dict(choice)
                choice_copy["message"] = SimpleNamespace(content=message.get("content", ""))
                choices.append(SimpleNamespace(**choice_copy))
        elif isinstance(api_response, dict) and api_response.get("output"):
            # Generic fallback for non-chat responses
            content = api_response.get("output")
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            choices.append(SimpleNamespace(message=SimpleNamespace(content=content)))
        else:
            choices.append(SimpleNamespace(message=SimpleNamespace(content="")))
        self.choices = choices

        data = []
        if isinstance(api_response, dict) and api_response.get("data"):
            for item in api_response.get("data", []):
                data.append(SimpleNamespace(**item))
        self.data = data


class DeepseekHttpClient:
    def __init__(self, api_key, base_url="https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self.chat = SimpleNamespace(completions=DeepseekChatCompletions(self))
        self.images = SimpleNamespace(generate=DeepseekImageGenerator(self).generate)

    def _request(self, path, payload):
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        response = self.session.post(url, json=payload, timeout=60)
        # If the API returned a client/server error, log the body for debugging
        if response.status_code >= 400:
            logging.getLogger(__name__).error(
                "Deepseek API error %s for %s: %s",
                response.status_code,
                url,
                response.text,
            )
        response.raise_for_status()
        return response.json()

    def _to_response(self, api_response):
        if isinstance(api_response, dict):
            return DeepseekResponse(api_response)
        return DeepseekResponse({"choices": [{"message": {"content": str(api_response)}}]})


class DeepseekChatCompletions:
    def __init__(self, client):
        self.client = client

    def create(self, model, messages, temperature=0.7, **kwargs):
        # Accept common OpenAI-style model names and map them to Deepseek equivalents
        if model in {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4o-mini"}:
            model = "deepseek-v4-flash"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        payload.update(kwargs)
        api_response = self.client._request("chat/completions", payload)
        return self.client._to_response(api_response)


class DeepseekImageGenerator:
    def __init__(self, client):
        self.client = client

    def generate(self, model, prompt, size="1024x1024", quality="standard", n=1, **kwargs):
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": n,
        }
        payload.update(kwargs)
        api_response = self.client._request("images/generate", payload)
        return self.client._to_response(api_response)
