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

    def synthesize_and_verify_answer(
        self,
        query: str,
        candidate_passages: list[tuple[str, str, float]],
    ) -> tuple[str, str, str] | None:
        """
        Reranks, verifies, and synthesizes a direct natural answer to the query
        along with the exact grounding excerpt and source URL.
        candidate_passages: list of (url, verbatim_passage_text, score)
        Returns (url, verbatim_excerpt, direct_answer) or None if refusing to guess / error.
        """
        if not self.is_available or not candidate_passages:
            return None

        passages_text = ""
        for i, (u, text, _) in enumerate(candidate_passages[:5]):
            passages_text += f"[{i+1}] (URL: {u})\n{text}\n\n"

        prompt = (
            f"Query: \"{query}\"\n\n"
            f"Candidate Passages extracted from the crawled website:\n{passages_text}\n"
            f"Instructions:\n"
            f"1. Determine if any of the candidate passages genuinely and directly answer the query.\n"
            f"2. If yes, synthesize a clear, direct, and helpful answer (1-3 sentences) answering the question based strictly on the site facts.\n"
            f"3. Select the best verbatim passage number (1-5) that serves as the grounding evidence.\n"
            f"4. If NONE of the passages answer the query, respond with: {{\"match_index\": null, \"answer\": null}}.\n\n"
            f"Response format (valid JSON only):\n"
            f"{{\n"
            f"  \"match_index\": <number 1-5 or null>,\n"
            f"  \"answer\": \"<direct answer to user query>\"\n"
            f"}}\n"
            f"Only respond with the valid JSON object."
        )

        response = self.generate_text(
            prompt,
            system_prompt="You are a strict, grounded Q&A synthesis system. Output valid JSON only.",
        )
        if not response:
            return None

        try:
            m = re.search(r"\{.*?\}", response, re.DOTALL)
            if m:
                obj = json.loads(m.group(0))
                idx = obj.get("match_index")
                direct_ans = obj.get("answer") or ""
                if idx is not None and isinstance(idx, int) and 1 <= idx <= len(candidate_passages[:5]):
                    chosen_url, chosen_text, _ = candidate_passages[idx - 1]
                    if not direct_ans:
                        direct_ans = chosen_text
                    return chosen_url, chosen_text, direct_ans
                elif idx is None:
                    # Refusal confirmed by AI
                    return "", "", ""
        except Exception:
            pass

        return None

    def verify_and_refine_answer(
        self,
        query: str,
        candidate_passages: list[tuple[str, str, float]],
    ) -> tuple[str, str] | None:
        """Backward-compatible helper returning (url, verbatim_excerpt)."""
        res = self.synthesize_and_verify_answer(query, candidate_passages)
        if res is not None:
            return res[0], res[1]
        return None

    def generate_seo_summary(
        self,
        findings: list[dict],
        url: str,
    ) -> dict | None:
        """
        Uses active AI to produce an executive summary and prioritized action plan
        based on the audit findings. Returns None on error to fall back to deterministic summary.
        """
        if not self.is_available or not findings:
            return None

        sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        metric_samples = []
        for f in findings:
            sev = f.get("severity", "low").lower()
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
            if len(metric_samples) < 15:
                metric_samples.append(f"- [{f.get('severity', 'low').upper()}] {f.get('metric')}: {f.get('evidence', '')[:120]}")

        findings_text = "\n".join(metric_samples)
        prompt = (
            f"Website Technical SEO Audit for: {url}\n"
            f"Total issues found: {len(findings)} (Critical: {sev_counts['critical']}, High: {sev_counts['high']}, Medium: {sev_counts['medium']}, Low: {sev_counts['low']})\n\n"
            f"Key finding samples:\n{findings_text}\n\n"
            f"Instructions:\n"
            f"1. Generate a concise executive summary (2-3 sentences max) evaluating the site's technical SEO health.\n"
            f"2. Provide an overall SEO health score between 0 and 100.\n"
            f"3. Provide 3 to 4 prioritized action recommendations that will boost search rankings, crawlability, and CTR most effectively.\n\n"
            f"Output JSON schema:\n"
            f"{{\n"
            f"  \"health_score\": <number 0-100>,\n"
            f"  \"overview\": \"<2 concise sentences summarizing technical health and main growth bottlenecks>\",\n"
            f"  \"priority_actions\": [\n"
            f"    {{\n"
            f"      \"priority\": 1,\n"
            f"      \"impact\": \"High\",\n"
            f"      \"category\": \"<e.g. Crawlability & Indexing>\",\n"
            f"      \"action\": \"<concise title of action>\",\n"
            f"      \"description\": \"<1-2 sentences explaining why this change boosts SEO>\"\n"
            f"    }}\n"
            f"  ]\n"
            f"}}\n"
            f"Only output valid JSON."
        )

        response = self.generate_text(
            prompt,
            system_prompt="You are an elite SEO strategist. Output clean, valid JSON only.",
        )
        if not response:
            return None

        try:
            m = re.search(r"\{.*\}", response, re.DOTALL)
            if m:
                obj = json.loads(m.group(0))
                if "priority_actions" in obj and "overview" in obj:
                    return obj
        except Exception:
            pass
        return None


def deterministic_seo_summary(findings: list[dict], url: str) -> dict:
    """
    100% deterministic, rule-based executive summary generator.
    Always succeeds even when offline or AI is disabled.
    """
    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    high_count = sum(1 for f in findings if f.get("severity") == "high")
    medium_count = sum(1 for f in findings if f.get("severity") == "medium")
    low_count = sum(1 for f in findings if f.get("severity") == "low")
    total = len(findings)

    deductions = (critical_count * 16) + (high_count * 8) + (medium_count * 4) + (low_count * 1)
    health_score = max(35, min(98, 100 - deductions))

    seen_metrics = set()
    unique_findings = []
    for f in findings:
        m = f.get("metric")
        if m not in seen_metrics:
            seen_metrics.add(m)
            unique_findings.append(f)

    priority_actions = []
    priority_order = ["critical", "high", "medium", "low"]
    current_p = 1

    metric_category_map = {
        "http_error": ("Crawlability", "Fix broken status codes and server connection errors"),
        "canonical_missing": ("Indexing", "Implement self-referencing canonical tags to consolidate link signals"),
        "meta_description_empty": ("CTR & Metadata", "Write concise meta descriptions to improve SERP click-through rates"),
        "meta_description_missing": ("CTR & Metadata", "Add descriptive meta tags to all indexable pages"),
        "duplicate_title": ("Content Quality", "Provide unique titles per page to eliminate internal keyword cannibalization"),
        "heading_hierarchy_skip": ("On-Page Structure", "Maintain logical H1-H2-H3 heading hierarchy for semantic clarity"),
        "image_dimensions_missing": ("Core Web Vitals", "Set explicit width/height on images to eliminate layout shifts (CLS)"),
        "image_alt_missing": ("Accessibility & Image SEO", "Add descriptive alt text to all informative images"),
        "llms_txt_missing": ("AEO / AI Search", "Publish an /llms.txt file for AI search engines like Perplexity and SearchGPT"),
        "render_blocking_script": ("Performance", "Add defer or async to head scripts to improve First Contentful Paint"),
    }

    for target_sev in priority_order:
        for f in unique_findings:
            if f.get("severity") == target_sev and len(priority_actions) < 4:
                m = f.get("metric")
                cat, default_act = metric_category_map.get(m, ("Technical SEO", f.get("suggested_fix", "")[:60]))
                impact = "High" if target_sev in ("critical", "high") else "Medium"
                priority_actions.append({
                    "priority": current_p,
                    "impact": impact,
                    "category": cat,
                    "action": default_act,
                    "description": f.get("suggested_fix", "Resolve this issue to prevent search performance degradation.")
                })
                current_p += 1

    if not priority_actions:
        priority_actions.append({
            "priority": 1,
            "impact": "Low",
            "category": "Maintenance",
            "action": "Maintain current technical optimization",
            "description": "No critical or high severity issues were detected during this crawl session."
        })

    overview = (
        f"Technical audit completed for {url}. Evaluated across {total} total finding(s) "
        f"({critical_count} critical, {high_count} high, {medium_count} medium). "
        f"Focusing on the top priority actions will immediately improve crawl budget, search indexing, and user experience."
    )

    return {
        "health_score": health_score,
        "overview": overview,
        "priority_actions": priority_actions,
    }
