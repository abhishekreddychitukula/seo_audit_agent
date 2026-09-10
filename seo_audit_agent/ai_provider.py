from __future__ import annotations

import json
import os
import re
import sys
from typing import Literal

from dotenv import find_dotenv

# ============================================================================
# LLM ENGINE CONFIGURATION (Powered by LangChain)
# ============================================================================
# Easily switch between Groq and Google Gemini by commenting/uncommenting below.
# ============================================================================

def _clean_key(val: str | None) -> str:
    """Strips whitespace, surrounding quotes, and ignores placeholders."""
    if not val:
        return ""
    v = str(val).strip().strip("'\"")
    if len(v) < 8 or v.lower().startswith("your_") or "placeholder" in v.lower():
        return ""
    return v


def reload_env() -> dict[str, str]:
    """
    Dynamically re-reads .env fresh from disk and synchronizes os.environ.
    If a key is commented out (#) or removed, it is immediately cleared from memory.
    """
    env_file = find_dotenv(usecwd=True)
    if not env_file or not os.path.isfile(env_file):
        for candidate in [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        ]:
            if os.path.isfile(candidate):
                env_file = candidate
                break

    disk_keys: dict[str, str] = {}
    if env_file and os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Ignore comment lines and lines without '='
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        clean_v = _clean_key(v)
                        if clean_v:
                            disk_keys[k] = clean_v
        except Exception:
            pass

    # Synchronize memory so commented-out keys are purged
    for var in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"):
        if var in disk_keys:
            os.environ[var] = disk_keys[var]
        elif var in os.environ:
            del os.environ[var]

    return disk_keys


def get_llm():
    """
    Initializes and returns the active LangChain chat model.
    Returns (llm_instance, provider_name) or (None, None) if no API key is available.
    """
    env = reload_env()

    # -------------------------------------------------------------------------
    # OPTION 1: Groq (via LangChain) - ACTIVE BY DEFAULT
    # -------------------------------------------------------------------------
    groq_key = env.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            # Using ultra-fast qwen3.6-27b on Groq with reasoning disabled for instant JSON
            llm = ChatGroq(
                model_name="qwen/qwen3.6-27b",
                reasoning_format="hidden",
                reasoning_effort="none",
                temperature=0.1,
                groq_api_key=groq_key,
                max_tokens=600,
            )
            return llm, "Groq"
        except Exception as e:
            print(f"[LangChain] Error initializing Groq: {e}", file=sys.stderr)

    # -------------------------------------------------------------------------
    # OPTION 2: Google Gemini (via LangChain) - UNCOMMENT TO USE GEMINI
    # -------------------------------------------------------------------------
    # gemini_key = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    # if gemini_key:
    #     try:
    #         from langchain_google_genai import ChatGoogleGenerativeAI
    #         llm = ChatGoogleGenerativeAI(
    #             model="gemini-2.5-flash",
    #             temperature=0.1,
    #             google_api_key=gemini_key,
    #             max_output_tokens=500,
    #         )
    #         return llm, "Gemini"
    #     except Exception as e:
    #         print(f"[LangChain] Error initializing Gemini: {e}", file=sys.stderr)

    # If no valid API key is found in .env, return None
    return None, None


# ============================================================================
# FEATURE 1: AUDIT EXECUTIVE SUMMARY & ACTION PLAN (Powered by LangChain)
# ============================================================================

def generate_audit_summary(findings: list[dict], url: str) -> dict | None:
    """
    Sends technical audit findings directly to the LangChain LLM to generate
    an executive summary and a prioritized action plan.
    
    CRITICAL: If no API key is configured, this returns None immediately.
    Nothing is hardcoded or faked.
    """
    if not findings:
        return None

    llm, provider_name = get_llm()
    if not llm:
        # No API key available: return None so the UI knows no AI summary exists
        return None

    # Group issues by severity for clean prompt context
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    samples = []
    for f in findings:
        s = f.get("severity", "low").lower()
        sev_counts[s] = sev_counts.get(s, 0) + 1
        if len(samples) < 6:
            issue_title = f.get("issue") or f.get("metric", "Technical SEO Issue")
            samples.append(f"- [{s.upper()}] {issue_title}: {f.get('evidence', '')[:80]}")

    prompt = (
        f"You are a principal technical SEO engineer.\n"
        f"Audit target: {url}\n"
        f"Total issues found: {len(findings)} (Critical: {sev_counts['critical']}, High: {sev_counts['high']}, Medium: {sev_counts['medium']}, Low: {sev_counts['low']})\n"
        f"Sample findings:\n" + "\n".join(samples) + "\n\n"
        "Generate an executive SEO health assessment and prioritized action plan in JSON format:\n"
        "{\n"
        '  "health_score": <integer between 0 and 100>,\n'
        '  "overview": "<2 concise sentences summarizing overall SEO stability and main bottlenecks>",\n'
        '  "priority_actions": [\n'
        '    {"priority": 1, "impact": "High", "category": "Performance", "action": "<action title>", "description": "<concrete action details>"},\n'
        '    {"priority": 2, "impact": "Medium", "category": "Indexing", "action": "<action title>", "description": "<concrete action details>"}\n'
        "  ]\n"
        "}\n"
        "Output valid JSON only. Do not include markdown code blocks or explanations."
    )

    try:
        response = llm.invoke(prompt)
        text = str(response.content if hasattr(response, "content") else response)
        # Strip any <think> tags from reasoning models
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            if "overview" in data and "priority_actions" in data:
                data["is_ai"] = True
                data["provider"] = provider_name
                return data
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[LangChain Summary Error] {e}", file=sys.stderr)

    return None


# ============================================================================
# FEATURE 2: HYBRID AEO Q&A (BM25 + LangChain Normalization)
# ============================================================================

def answer_query(
    query: str,
    candidate_passages: list[tuple[str, str]],  # [(url, passage_text)]
) -> tuple[str, str, str] | None:
    """
    Hybrid Q&A combining BM25 retrieval with LangChain LLM semantic normalization:
    Given the top passages pre-ranked by BM25, the LLM selects the most accurate
    passage, retrieves the exact verbatim excerpt, and synthesizes a direct answer.
    
    Returns (url, verbatim_excerpt, direct_answer) or None if no match.
    """
    if not candidate_passages:
        return None

    llm, _ = get_llm()
    if not llm:
        return None

    sections = []
    for i, (u, text) in enumerate(candidate_passages[:8]):
        clean_text = re.sub(r"\s+", " ", text).strip()[:350]
        sections.append(f"[{i+1}] (Page: {u})\n{clean_text}")

    prompt = (
        f"User Query: \"{query}\"\n\n"
        "Candidate Passages from Website:\n"
        + "\n\n".join(sections)
        + "\n\n"
        "Instructions:\n"
        "1. Identify the passage that best answers the query.\n"
        "2. If no passage provides a factual answer, return null.\n"
        "3. If answered, provide:\n"
        "   - passage_index (integer)\n"
        "   - verbatim_excerpt (exact text copied from the chosen passage)\n"
        "   - direct_answer (a clear, direct 1-2 sentence natural answer)\n\n"
        "Output JSON format:\n"
        "{\n"
        '  "passage_index": 1,\n'
        '  "verbatim_excerpt": "<exact text>",\n'
        '  "direct_answer": "<direct answer>"\n'
        "}\n"
        "Output valid JSON only."
    )

    try:
        response = llm.invoke(prompt)
        text = str(response.content if hasattr(response, "content") else response)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            idx = data.get("passage_index")
            if isinstance(idx, int) and 1 <= idx <= len(candidate_passages):
                chosen_url = candidate_passages[idx - 1][0]
                excerpt = data.get("verbatim_excerpt") or candidate_passages[idx - 1][1]
                answer = data.get("direct_answer") or excerpt
                return chosen_url, excerpt, answer
    except Exception as e:
        print(f"[LangChain Q&A Error] {e}", file=sys.stderr)

    return None


# ============================================================================
# COMPATIBILITY WRAPPER FOR BACKWARD INTERFACES AND TESTS
# ============================================================================

ProviderType = Literal["auto", "groq", "gemini", "none"]


def _is_valid_key(val: str | None) -> bool:
    return bool(_clean_key(val))


class AIProvider:
    """Wrapper class providing backward compatibility for existing modules and tests."""

    def __init__(self, provider: str = "auto", model: str | None = None, api_key: str | None = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    @property
    def is_available(self) -> bool:
        llm, _ = get_llm()
        return llm is not None

    def generate_seo_summary(self, findings: list[dict], url: str) -> dict | None:
        """Generates audit summary using LangChain. Returns None if no API key is present."""
        return generate_audit_summary(findings, url)

    def find_relevant_answer(self, query: str, passages: list[tuple[str, str]]) -> tuple[str, str, str] | None:
        return answer_query(query, passages)

    def synthesize_and_verify_answer(self, query: str, candidates: list) -> tuple[str, str, str] | None:
        if not candidates:
            return None
        passages = [(c[0], c[1]) for c in candidates]
        return answer_query(query, passages)

    def verify_and_refine_answer(self, query: str, candidates: list) -> tuple[str, str] | None:
        res = self.synthesize_and_verify_answer(query, candidates)
        if res:
            return res[0], res[1]
        return None

    def enhance_suggested_fix(self, issue: str = "", evidence: str = "", page_title: str = "", page_snippet: str = "", default_fix: str = "", metric: str = "") -> str:
        return default_fix

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str | None:
        llm, _ = get_llm()
        if not llm:
            return None
        try:
            res = llm.invoke(prompt)
            txt = str(res.content if hasattr(res, "content") else res)
            return re.sub(r"<think>.*?</think>", "", txt, flags=re.DOTALL).strip()
        except Exception:
            return None


def deterministic_seo_summary(findings: list[dict], url: str) -> dict:
    """Provided purely for test suites and offline static utilities."""
    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    high_count = sum(1 for f in findings if f.get("severity") == "high")
    total = len(findings)
    score = max(40, 100 - (critical_count * 15 + high_count * 8))
    return {
        "health_score": score,
        "overview": f"Site technical evaluation observed {total} findings with score {score}/100.",
        "priority_actions": [
            {"priority": 1, "impact": "High", "category": "SEO", "action": "Remediate Priority Findings", "description": "Resolve high severity issues."}
        ],
        "is_ai": False,
        "provider": "Deterministic Rule-Based",
    }
