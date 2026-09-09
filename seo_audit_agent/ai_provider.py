from __future__ import annotations

import json
import os
import re
import sys
from typing import Literal

import requests

ProviderType = Literal["auto", "gemini", "groq", "openai", "none"]

DEFAULT_MODELS = {
    "gemini": "gemini-1.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
}


class AIProvider:
    """
    Lightweight, framework-free multi-provider AI REST client.
    Supports Google Gemini, Groq, and OpenAI with instant automatic fallback
    to deterministic manual logic on any failure.
    """

    def __init__(
        self,
        provider: ProviderType = "auto",
        model: str | None = None,
        timeout: float = 8.0,
        api_key: str | None = None,
    ):
        self.timeout = timeout
        env_provider = os.getenv("SEO_AI_PROVIDER", "").strip().lower()
        effective_provider = (provider or "auto").lower()
        if effective_provider == "auto" and env_provider:
            effective_provider = env_provider

        self.api_key = api_key
        self.provider: str = self._resolve_provider(effective_provider)
        self.model: str = model or DEFAULT_MODELS.get(self.provider, "")

    def _resolve_provider(self, requested: str) -> str:
        if requested in ("none", "off", "disabled"):
            return "none"

        # Check explicit requested provider
        if requested == "gemini":
            self.api_key = self.api_key or os.getenv("GEMINI_API_KEY", "")
            return "gemini" if self.api_key else "none"
        if requested == "groq":
            self.api_key = self.api_key or os.getenv("GROQ_API_KEY", "")
            return "groq" if self.api_key else "none"
        if requested == "openai":
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY", "")
            return "openai" if self.api_key else "none"

        # "auto" resolution based on available environment variables
        if os.getenv("GEMINI_API_KEY"):
            self.api_key = os.getenv("GEMINI_API_KEY")
            return "gemini"
        if os.getenv("GROQ_API_KEY"):
            self.api_key = os.getenv("GROQ_API_KEY")
            return "groq"
        if os.getenv("OPENAI_API_KEY"):
            self.api_key = os.getenv("OPENAI_API_KEY")
            return "openai"

        return "none"

    @property
    def is_available(self) -> bool:
        return self.provider != "none" and bool(self.api_key)

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str | None:
        """
        Sends prompt to the active provider.
        Returns text on success, or None on failure (triggering automatic fallback).
        """
        if not self.is_available:
            return None

        try:
            if self.provider == "gemini":
                return self._call_gemini(prompt, system_prompt)
            elif self.provider == "groq":
                return self._call_groq(prompt, system_prompt)
            elif self.provider == "openai":
                return self._call_openai(prompt, system_prompt)
        except Exception as e:
            print(
                f"[AIProvider] Notice: AI generation failed ({self.provider}: {e}). "
                "Falling back to manual process.",
                file=sys.stderr,
            )
            return None
        return None

    def _call_gemini(self, prompt: str, system_prompt: str | None = None) -> str | None:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 800},
        }
        res = requests.post(url, json=payload, timeout=self.timeout)
        if not res.ok:
            if res.status_code in (400, 401, 403):
                self.provider = "none"
            print(f"[AIProvider] Gemini HTTP {res.status_code}: {res.text[:120]}", file=sys.stderr)
            return None
        data = res.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        return None

    def _call_groq(self, prompt: str, system_prompt: str | None = None) -> str | None:
        url = "https://api.groq.com/openai/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 800,
        }
        res = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        if not res.ok:
            if res.status_code in (400, 401, 403):
                self.provider = "none"
            print(f"[AIProvider] Groq HTTP {res.status_code}: {res.text[:120]}", file=sys.stderr)
            return None
        data = res.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
        return None

    def _call_openai(self, prompt: str, system_prompt: str | None = None) -> str | None:
        url = "https://api.openai.com/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 800,
        }
        res = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        if not res.ok:
            if res.status_code in (400, 401, 403):
                self.provider = "none"
            print(f"[AIProvider] OpenAI HTTP {res.status_code}: {res.text[:120]}", file=sys.stderr)
            return None
        data = res.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
        return None

    def enhance_suggested_fix(
        self,
        metric: str,
        evidence: str,
        page_title: str,
        page_snippet: str,
        default_fix: str,
    ) -> str:
        """
        Uses active AI to produce an actionable, customized code fix.
        Falls back to default_fix if AI is unavailable or encounters an issue.
        """
        if not self.is_available:
            return default_fix

        prompt = (
            f"You are an expert SEO technical engineer. A website audit found this issue:\n"
            f"- Metric: {metric}\n"
            f"- Evidence: {evidence}\n"
            f"- Page Title: {page_title}\n"
            f"- Page Content Snippet: {page_snippet[:350]}\n\n"
            f"Provide a concise, production-ready fix. If applicable, include the exact HTML markup snippet to insert. "
            f"Keep your entire answer under 3 sentences."
        )
        ai_response = self.generate_text(
            prompt,
            system_prompt="You are a concise, accurate SEO engineering assistant.",
        )
        if ai_response and len(ai_response.strip()) >= 15:
            return ai_response.strip()
        return default_fix

    def verify_and_refine_answer(
        self,
        query: str,
        candidate_passages: list[tuple[str, str, float]],
    ) -> tuple[str, str] | None:
        """
        Reranks and verifies whether any candidate passage answers the query.
        candidate_passages: list of (url, verbatim_passage_text, score)
        Returns (url, verbatim_passage_text) if an answer is verified, or None if refusing to guess.
        """
        if not self.is_available or not candidate_passages:
            return None

        # Build candidate prompt
        passages_text = ""
        for i, (u, text, _) in enumerate(candidate_passages[:5]):
            passages_text += f"[{i+1}] (URL: {u})\n{text}\n\n"

        prompt = (
            f"Query: \"{query}\"\n\n"
            f"Candidate Passages extracted from the website:\n{passages_text}\n"
            f"Instructions:\n"
            f"1. Determine if any of the candidate passages genuinely and directly answers the query.\n"
            f"2. If yes, respond with a JSON object: {{\"match_index\": <1-5>}}.\n"
            f"3. If NONE of the passages answer the query, respond with: {{\"match_index\": null}}.\n"
            f"Do not guess. Only respond with the JSON object."
        )

        response = self.generate_text(
            prompt,
            system_prompt="You are a strict, hallucination-free passage verification system. Output valid JSON only.",
        )
        if not response:
            return None

        try:
            m = re.search(r"\{.*?\}", response, re.DOTALL)
            if m:
                obj = json.loads(m.group(0))
                idx = obj.get("match_index")
                if idx is not None and isinstance(idx, int) and 1 <= idx <= len(candidate_passages[:5]):
                    chosen_url, chosen_text, _ = candidate_passages[idx - 1]
                    return chosen_url, chosen_text
                elif idx is None:
                    # AI confirmed refusal to guess
                    return "", ""
        except Exception:
            pass

        return None
