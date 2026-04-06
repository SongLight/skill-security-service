#!/usr/bin/env python3
"""
Skill Security Scanner - AI Agent Skill Security Scanner
Detects malicious patterns in AI Agent skills with zero external dependencies.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from skill_scanner.scanner import SkillScanner


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="skill-scanner",
        description="AI Agent Skill Security Scanner - Detects malicious patterns in AI Agent skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to skill directory or file to scan",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "html", "sarif", "markdown"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: stdout)",
    )

    parser.add_argument(
        "--severity",
        type=str,
        choices=["critical", "high", "medium", "low"],
        help="Filter by minimum severity level",
    )

    parser.add_argument(
        "--use-ioc",
        action="store_true",
        help="Enable IOC (Indicator of Compromise) detection",
    )

    parser.add_argument(
        "--use-behavioral",
        action="store_true",
        help="Enable behavioral analysis",
    )

    parser.add_argument(
        "--use-yara",
        action="store_true",
        help="Enable YARA rule matching",
    )

    parser.add_argument(
        "--use-permission-analysis",
        action="store_true",
        help="Enable permission analysis",
    )

    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Enable LLM-based deep analysis",
    )

    parser.add_argument(
        "--llm-provider",
        type=str,
        default="openai",
        choices=["openai", "anthropic", "ollama"],
        help="LLM provider (default: openai)",
    )

    parser.add_argument(
        "--llm-model",
        type=str,
        help="LLM model (default: provider-specific)",
    )

    parser.add_argument(
        "--llm-api-key",
        type=str,
        help="LLM API key (or set OPENAI_API_KEY/ANTHROPIC_API_KEY)",
    )

    parser.add_argument(
        "--llm-base-url",
        type=str,
        help="Custom API base URL (for proxy/ollama)",
    )

    parser.add_argument(
        "--group-by-skill",
        action="store_true",
        default=True,
        help="Group findings by skill (default: True)",
    )

    parser.add_argument(
        "--no-group-by-skill",
        action="store_true",
        help="Disable grouping by skill",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser


def main():
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()

    scanner = SkillScanner(
        use_ioc=args.use_ioc,
        use_behavioral=args.use_behavioral,
        use_yara=args.use_yara,
        use_permission_analysis=args.use_permission_analysis,
        use_llm=args.use_llm,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_api_key=args.llm_api_key,
        llm_base_url=args.llm_base_url,
        verbose=args.verbose,
    )

    print(f"🔍 Scanning: {args.path}", file=sys.stderr)

    findings = scanner.scan(args.path, verbose=args.verbose)

    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        if f.severity.name in severity_counts:
            severity_counts[f.severity.name] += 1

    total = sum(severity_counts.values())
    print(f"✅ Scan complete: {total} findings", file=sys.stderr)
    if severity_counts["CRITICAL"] > 0:
        print(f"   🔴 CRITICAL: {severity_counts['CRITICAL']}", file=sys.stderr)
    if severity_counts["HIGH"] > 0:
        print(f"   🟠 HIGH: {severity_counts['HIGH']}", file=sys.stderr)
    if severity_counts["MEDIUM"] > 0:
        print(f"   🟡 MEDIUM: {severity_counts['MEDIUM']}", file=sys.stderr)
    if severity_counts["LOW"] > 0:
        print(f"   🔵 LOW: {severity_counts['LOW']}", file=sys.stderr)

    if args.severity:
        severity_order = ["critical", "high", "medium", "low"]
        min_level = severity_order.index(args.severity)
        findings = [
            f for f in findings
            if severity_order.index(f.severity.name.lower()) <= min_level
        ]

    if args.no_group_by_skill:
        args.group_by_skill = False

    output = scanner.format_output(
        findings,
        args.format,
        group_by_skill=args.group_by_skill,
    )

    if args.output:
        output_path = Path(args.output)
    else:
        if args.format != "text":
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = args.format
            output_path = reports_dir / f"scan_report_{timestamp}.{ext}"
        else:
            print(output)
            sys.exit(0 if not findings else 1)
            return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
    print(f"📄 Report saved to: {output_path}", file=sys.stderr)

    sys.exit(0 if not findings else 1)


if __name__ == "__main__":
    main()
