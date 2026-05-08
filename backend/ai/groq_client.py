from __future__ import annotations

from groq import Groq

from utils.config import settings


class GroqService:
    def __init__(self) -> None:
        self._client: Groq | None = None

    @property
    def client(self) -> Groq:
        if not settings.groq_api_key:
            raise RuntimeError("Missing GROQ_API_KEY. Add it to your environment before using the chatbot.")
        if self._client is None:
            self._client = Groq(api_key=settings.groq_api_key)
        return self._client

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        response = self.client.chat.completions.create(
            model=settings.groq_model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

