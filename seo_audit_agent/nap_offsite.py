from __future__ import annotations

import json
import os
import re
import sys
from typing import Any
from urllib.parse import urlparse

from ddgs import DDGS
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

try:
    from .ai_provider import get_llm
except (ImportError, ValueError):
    _pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from ai_provider import get_llm


@tool
def search_web(query: str) -> str:
    """
    Search the internet for business listings, directories, citations, and contact details (Name, Address, Phone).
    """
    try:
        results = list(DDGS().text(query, max_results=5))
        if not results:
            return "No external web citations or directory listings found."

        output = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Listing")
            href = r.get("href", "")
            body = r.get("body", "")
            output.append(f"[{i}] {title}\nURL: {href}\nSnippet: {body}")
        return "\n\n".join(output)
    except Exception as e:
        return f"Web search error: {e}"


def extract_in_site_canonical(in_site_report: list[dict]) -> dict[str, str]:
    """Derives canonical Name, Address, and Phone from in-site crawl report."""
    canonical = {"name": "", "address": "", "phone": ""}
    if not in_site_report:
        return canonical

    for item in in_site_report:
        fld = item.get("field")
        if fld in canonical and item.get("values"):
            vals = item["values"]
            if vals and "value" in vals[0]:
                canonical[fld] = str(vals[0]["value"]).strip()
    return canonical


def audit_offsite_nap(url: str, in_site_report: list[dict]) -> dict[str, Any]:
    """
    Agentic Off-Site NAP Consistency Auditor:
    Equips the LangChain LLM with the search_web tool so the model autonomously
    searches the web for external citations, extracts external NAP,
    and compares them against in-site canonical data.
    """
    llm, provider_name = get_llm()
    canonical = extract_in_site_canonical(in_site_report)

    if not llm:
        return {
            "status": "no_llm",
            "citation_health_score": None,
            "summary": "Active LLM API key required in .env to perform autonomous web citation searches.",
            "citations": [],
            "recommendations": [
                "Add GROQ_API_KEY or GEMINI_API_KEY in .env to enable autonomous off-site web citation checking."
            ],
            "in_site_canonical": canonical,
        }

    p = urlparse(url)
    domain = p.hostname or url.replace("https://", "").replace("http://", "").split("/")[0]
    brand_hint = domain.split(".")[0].capitalize()

    known_name = canonical["name"] or brand_hint
    known_addr = canonical["address"] or "Not stated on website"
    known_phone = canonical["phone"] or "Not stated on website"

    prompt = (
        f"Target Business: {known_name}\n"
        f"Official Domain: {domain}\n"
        f"In-Site Canonical Name: {known_name}\n"
        f"In-Site Canonical Address: {known_addr}\n"
        f"In-Site Canonical Phone: {known_phone}\n\n"
        "Instructions:\n"
        "1. Use your `search_web` tool to search for external citations and directory listings for this business "
        f"across the web (e.g. search for `{known_name} business directory address phone` or `{domain} contact address`).\n"
        "2. Examine the search results to find external listings (e.g. Google Business, Yelp, LinkedIn, directories, Crunchbase).\n"
        "3. Compare any external Name, Address, and Phone against the in-site canonical data.\n"
        "4. Respond with valid JSON ONLY in the following format:\n"
        "{\n"
        '  "citation_health_score": <number 0-100>,\n'
        '  "summary": "<2 concise sentences summarizing off-site citation presence and consistency>",\n'
        '  "citations": [\n'
        '    {\n'
        '      "source": "<Platform Name, e.g. Yelp, Google Maps, LinkedIn>",\n'
        '      "url": "<External URL>",\n'
        '      "name": "<External name or null>",\n'
        '      "address": "<External address or null>",\n'
        '      "phone": "<External phone or null>",\n'
        '      "match_status": "<consistent | partial | mismatch | not_listed>",\n'
        '      "discrepancy_details": "<Brief note on matching or mismatching details>"\n'
        '    }\n'
        '  ],\n'
        '  "recommendations": [\n'
        '    "<Actionable recommendation for claiming or fixing local citations>"\n'
        '  ]\n'
        "}\n"
        "Output valid JSON only. No markdown formatting."
    )

    try:
        llm_with_tools = llm.bind_tools([search_web])
        messages = [
            SystemMessage(content="You are an expert Local SEO & Citation Auditor agent. Use search_web to search for external business directory listings, then output valid JSON."),
            HumanMessage(content=prompt),
        ]

        # Step 1: Model issues search_web tool call
        ai_response = llm_with_tools.invoke(messages)
        messages.append(ai_response)

        # Step 2: If model requested search, execute tools
        if getattr(ai_response, "tool_calls", None):
            for tool_call in ai_response.tool_calls:
                query_arg = tool_call.get("args", {}).get("query", f"{known_name} business directory address phone")
                tool_output = search_web.invoke(query_arg)
                messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))

            # Step 3: Call LLM to synthesize final JSON from the search results
            messages.append(HumanMessage(content="Analyze all the external search results above. Compare external Name, Address, and Phone against in-site canonical data and output the final JSON report now. Output valid JSON only."))
            final_response = llm.invoke(messages)
            raw_text = str(final_response.content if hasattr(final_response, "content") else final_response)
        else:
            raw_text = str(ai_response.content if hasattr(ai_response, "content") else ai_response)

        clean_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
        m = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if m:
            raw_json_str = m.group(0)
            # Clean up common model JSON syntax quirks (trailing commas, missing comma between array objects)
            fixed_json_str = re.sub(r",\s*([\]\}])", r"\1", raw_json_str)
            fixed_json_str = re.sub(r"\}\s*\{", r"}, {", fixed_json_str)
            fixed_json_str = re.sub(r"\]\s*\[", r"], [", fixed_json_str)
            data = None
            for candidate in [fixed_json_str, raw_json_str]:
                try:
                    data = json.loads(candidate)
                    break
                except Exception:
                    continue

            if data and ("citations" in data or "summary" in data):
                # Ensure structure matches UI expectations
                if isinstance(data.get("summary"), dict):
                    sum_dict = data["summary"]
                    data["summary"] = f"Identified external citations for {known_name}. Listed address: {sum_dict.get('address', 'N/A')}, phone: {sum_dict.get('phone', 'N/A')}."
                data["status"] = "success"
                data["provider"] = provider_name
                data["in_site_canonical"] = canonical
                data["citations"] = data.get("citations", [])
                if "citation_health_score" not in data:
                    data["citation_health_score"] = 85 if data["citations"] else 50
                if "recommendations" not in data:
                    data["recommendations"] = [
                        "Ensure external directory listings match in-site canonical address exactly.",
                        "Verify phone numbers across local citation aggregators."
                    ]
                return data

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[Off-Site NAP Audit Error] {e}", file=sys.stderr)

    # Fallback for sites with 0 external public directory citations
    return {
        "status": "no_citations_found",
        "citation_health_score": 55,
        "summary": f"No high-confidence external business citations or directory listings were discovered on the public web for {known_name} ({domain}).",
        "citations": [],
        "recommendations": [
            f"Claim and verify a Google Business Profile listing for {known_name}.",
            "Register consistent business citations on major local directories (Bing Places, Apple Maps, Yelp).",
            "Ensure the Name, Address, and Phone on external listings match the website markup exactly."
        ],
        "in_site_canonical": canonical,
    }
