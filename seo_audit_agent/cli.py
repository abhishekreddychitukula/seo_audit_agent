from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import nap, q1_onpage, q3_grounded_qa


def main():
    parser = argparse.ArgumentParser(
        description="Free, evidence-backed SEO Audit Agents with optional multi-provider AI enhancement (Gemini, Groq, OpenAI)."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Q1: On-Page Auditor
    p1 = sub.add_parser("q1", help="Question 1: On-page SEO auditor (outputs audit.json)")
    p1.add_argument("url", help="Target website URL to crawl and evaluate")
    p1.add_argument("-o", "--output", default="audit.json", help="Path to output JSON deliverable")
    p1.add_argument("--max-pages", type=int, default=150, help="Maximum pages to crawl (default: 150)")
    p1.add_argument("--timeout", type=float, default=12.0, help="HTTP request timeout in seconds")
    p1.add_argument("--concurrency", type=int, default=5, help="Number of concurrent crawler workers (default: 5)")
    p1.add_argument(
        "--ai-provider",
        choices=["auto", "gemini", "groq", "openai", "none"],
        default="auto",
        help="AI provider for tailored fix recommendations (default: auto)",
    )
    p1.add_argument("--ai-model", default=None, help="Custom AI model name override")

    # Q2: NAP Consistency Checker (100% Rule-Based)
    p2 = sub.add_parser("q2", help="Question 2: Business NAP consistency checker (outputs nap_report.json)")
    p2.add_argument("url", help="Target business website URL")
    p2.add_argument("-o", "--output", default="nap_report.json", help="Path to output JSON deliverable")
    p2.add_argument("--max-pages", type=int, default=150, help="Maximum pages to crawl (default: 150)")
    p2.add_argument("--timeout", type=float, default=12.0, help="HTTP request timeout in seconds")
    p2.add_argument("--concurrency", type=int, default=5, help="Number of concurrent crawler workers (default: 5)")

    # Q3: Grounded Q&A Agent
    p3 = sub.add_parser("q3", help="Question 3: Grounded exact-passage Q&A agent (outputs answer.json)")
    p3.add_argument("url", help="Target website URL")
    p3.add_argument("query", help="Natural-language search query")
    p3.add_argument("-o", "--output", default="answer.json", help="Path to output JSON deliverable")
    p3.add_argument("--max-pages", type=int, default=150, help="Maximum pages to crawl (default: 150)")
    p3.add_argument("--timeout", type=float, default=12.0, help="HTTP request timeout in seconds")
    p3.add_argument("--concurrency", type=int, default=5, help="Number of concurrent crawler workers (default: 5)")
    p3.add_argument(
        "--ai-provider",
        choices=["auto", "gemini", "groq", "openai", "none"],
        default="auto",
        help="AI provider for hybrid passage verification (default: auto)",
    )
    p3.add_argument("--ai-model", default=None, help="Custom AI model name override")

    args = parser.parse_args()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    if args.cmd == "q1":
        print(f"[Q1] Crawling and auditing on-page SEO for: {args.url} (AI: {args.ai_provider}) ...", file=sys.stderr)
        result = q1_onpage.run(
            args.url,
            output=args.output,
            max_pages=args.max_pages,
            timeout=args.timeout,
            concurrency=args.concurrency,
            ai_provider=args.ai_provider,
            ai_model=args.ai_model,
        )
        print(f"[Q1] Done. {len(result)} findings written to {args.output}", file=sys.stderr)

    elif args.cmd == "q2":
        print(f"[Q2] Crawling and checking NAP consistency for: {args.url} ...", file=sys.stderr)
        result = nap.run(
            args.url,
            output=args.output,
            max_pages=args.max_pages,
            timeout=args.timeout,
            concurrency=args.concurrency,
        )
        print(f"[Q2] Done. NAP report written to {args.output}", file=sys.stderr)

    elif args.cmd == "q3":
        print(
            f"[Q3] Searching grounded passage for '{args.query}' on: {args.url} (AI: {args.ai_provider}) ...",
            file=sys.stderr,
        )
        result = q3_grounded_qa.run(
            args.url,
            args.query,
            output=args.output,
            max_pages=args.max_pages,
            timeout=args.timeout,
            concurrency=args.concurrency,
            ai_provider=args.ai_provider,
            ai_model=args.ai_model,
        )
        status = "Answer found" if result.get("excerpt") is not None else "Refusal to guess (null)"
        print(f"[Q3] Done ({status}). Result written to {args.output}", file=sys.stderr)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
