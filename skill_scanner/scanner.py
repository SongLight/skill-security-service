"""
Skill Security Scanner - Main scanner module
"""

import sys
from pathlib import Path
from typing import List, Optional

from skill_scanner.core.types import Finding, Severity
from skill_scanner.detectors import (
    SecretsDetector,
    DownloadExecDetector,
    InjectionDetector,
    CredentialTheftDetector,
    PersistenceDetector,
    ObfuscationDetector,
    Base64Detector,
    ExfiltrationDetector,
    NetworkDetector,
    SupplyChainDetector,
    EntropyDetector,
    HiddenCharDetector,
    PrivilegeEscalationDetector,
    SocialEngineeringDetector,
    IOCDetector,
)
from skill_scanner.discovery import SkillDiscovery


class SkillScanner:
    """Main scanner class for AI Agent Skill security scanning."""

    def __init__(
        self,
        use_ioc: bool = False,
        use_behavioral: bool = False,
        use_yara: bool = False,
        use_permission_analysis: bool = False,
        use_llm: bool = False,
        llm_provider: str = "openai",
        llm_model: str = None,
        llm_api_key: str = None,
        llm_base_url: str = None,
        verbose: bool = False,
    ):
        self.verbose = verbose
        self.use_ioc = use_ioc
        self.use_behavioral = use_behavioral
        self.use_yara = use_yara
        self.use_permission_analysis = use_permission_analysis
        self.use_llm = use_llm
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.llm_base_url = llm_base_url

        self.detectors = self._init_detectors()
        self.discovery = SkillDiscovery()
        
        if self.use_llm:
            from skill_scanner.detectors.llm_analyzer import create_llm_analyzer
            self.llm_detector = create_llm_analyzer(
                provider=llm_provider,
                model=llm_model,
                api_key=llm_api_key,
                base_url=llm_base_url,
            )
        else:
            self.llm_detector = None

    def _init_detectors(self):
        """Initialize all security detectors."""
        return [
            SecretsDetector(),
            DownloadExecDetector(),
            InjectionDetector(),
            CredentialTheftDetector(),
            PersistenceDetector(),
            ObfuscationDetector(),
            Base64Detector(),
            ExfiltrationDetector(),
            NetworkDetector(),
            SupplyChainDetector(),
            EntropyDetector(),
            HiddenCharDetector(),
            PrivilegeEscalationDetector(),
            SocialEngineeringDetector(),
        ]

    def scan(self, path: str, verbose: bool = False) -> List[Finding]:
        """Scan a skill directory or file."""
        findings = []

        p = Path(path).resolve()
        if p.is_dir():
            subdirs = [d for d in p.iterdir() if d.is_dir() and d.name not in {"__pycache__", ".git", "venv"}]
            if subdirs:
                skills = self.discovery.discover_multiple(path)
            else:
                skills = self.discovery.discover_single(path)
        else:
            skills = self.discovery.discover_single(path)

        for skill_data in skills:
            skill_path = skill_data.get("path")
            skill_name = skill_data.get("name", "unknown")
            if verbose:
                print(f"  📄 Scanning: {skill_name}...", file=sys.stderr)
            if not skill_path:
                continue
            for detector in self.detectors:
                findings.extend(detector.scan_skill(skill_path))
            
            if self.llm_detector and self.use_llm:
                if self.verbose:
                    print(f"  🤖 Running LLM deep analysis...", file=sys.stderr)
                findings.extend(self.llm_detector.scan_skill(skill_path))

        return findings

    def format_output(
        self,
        findings: List[Finding],
        format_type: str = "text",
        group_by_skill: bool = True,
    ) -> str:
        """Format scan findings for output."""
        if format_type == "json":
            import json
            return json.dumps(
                [{"severity": f.severity.name, "detector": f.detector,
                  "description": f.description, "file": f.file_path,
                  "line": f.line_number} for f in findings],
                indent=2,
            )

        elif format_type == "text":
            return self._format_text(findings, group_by_skill)

        elif format_type == "html":
            from skill_scanner.reporters import HTMLReporter
            results_data = self._build_results_data(findings)
            return HTMLReporter().generate(results_data)

        elif format_type == "markdown":
            from skill_scanner.reporters import MarkdownReporter
            results_data = self._build_results_data(findings)
            return MarkdownReporter().generate(results_data)

        elif format_type == "sarif":
            from skill_scanner.reporters import SARIFReporter
            results_data = self._build_results_data(findings)
            return SARIFReporter().generate(results_data)

        return str(findings)

    def _build_results_data(self, findings: List[Finding]) -> dict:
        """Build results data structure for reporters."""
        from skill_scanner.core.types import Severity

        skills_data = {}
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        by_skill = {}
        for f in findings:
            if f.file_path:
                parts = Path(f.file_path).parts
                skill_name = parts[-2] if len(parts) > 1 else parts[0]
            else:
                skill_name = "unknown"
            by_skill.setdefault(skill_name, []).append(f)

        for skill_name, skill_findings in by_skill.items():
            skills_data[skill_name] = [f.to_dict() for f in skill_findings]

            skill_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for f in skill_findings:
                sev_name = f.severity.name
                if sev_name in skill_counts:
                    skill_counts[sev_name] += 1
                    severity_counts[sev_name] += 1

            skills_data[skill_name + "_summary"] = {
                "findings_count": len(skill_findings),
                "severity_counts": skill_counts
            }

        skills_scanned = len(by_skill)
        files_scanned = len(set(f.file_path for f in findings if f.file_path))

        return {
            "findings": [f.to_dict() for f in findings],
            "summary": {
                "skills_scanned": skills_scanned,
                "files_scanned": files_scanned,
                "severity_counts": severity_counts,
            },
            "skills": skills_data,
        }

    def _calculate_risk_level(self, counts: dict) -> str:
        """Calculate overall risk level based on finding counts."""
        if counts.get(Severity.CRITICAL, 0) > 0:
            return "CRITICAL"
        elif counts.get(Severity.HIGH, 0) > 0:
            return "HIGH"
        elif counts.get(Severity.MEDIUM, 0) > 0:
            return "MEDIUM"
        elif counts.get(Severity.LOW, 0) > 0:
            return "LOW"
        return "SAFE"

    def _format_text(self, findings: List[Finding], group_by_skill: bool = True) -> str:
        """Format findings as text."""
        severity_icons = {
            Severity.CRITICAL: "🔴",
            Severity.HIGH: "🟠",
            Severity.MEDIUM: "🟡",
            Severity.LOW: "�",
        }

        severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]

        if not findings:
            return "\n✅ No security issues found.\n"

        lines = []
        lines.append("\n" + "═" * 50)
        lines.append("     Skill Security Scanner - Scan Results")
        lines.append("═" * 50)
        lines.append(f"     Total findings: {len(findings)}")
        lines.append("═" * 50 + "\n")

        by_severity = {}
        for f in findings:
            by_severity.setdefault(f.severity, []).append(f)

        if group_by_skill:
            by_skill = {}
            for f in findings:
                if f.file_path:
                    parts = Path(f.file_path).parts
                    skill_name = parts[-2] if len(parts) > 1 else parts[0]
                else:
                    skill_name = "unknown"
                by_skill.setdefault(skill_name, []).append(f)

            for skill_name in sorted(by_skill.keys()):
                skill_findings = by_skill[skill_name]

                skill_counts = {s: 0 for s in Severity}
                for f in skill_findings:
                    skill_counts[f.severity] += 1
                risk_level = self._calculate_risk_level(skill_counts)
                risk_icon = "🔴" if risk_level == "CRITICAL" else "🟠" if risk_level == "HIGH" else "🟡" if risk_level == "MEDIUM" else "🟢"

                lines.append(f"\n📁 Skill: {skill_name}  {risk_icon} {risk_level}")
                lines.append("=" * 50)

                skill_by_severity = {}
                for f in skill_findings:
                    skill_by_severity.setdefault(f.severity, []).append(f)

                for severity in severity_order:
                    if severity not in skill_by_severity:
                        continue
                    fs = skill_by_severity[severity]
                    icon = severity_icons.get(severity, "⚪")
                    lines.append(f"\n  {icon} [{severity.name} Risk] {len(fs)} finding(s)")
                    lines.append("  " + "-" * 40)
                    for i, f in enumerate(fs, 1):
                        lines.append(f"    {i}. {f.detector}")
                        lines.append(f"       {f.description[:80]}")
                        lines.append(f"       📍 {Path(f.file_path).name}:{f.line_number}")
                        lines.append("")
        else:
            for severity in severity_order:
                if severity not in by_severity:
                    continue
                fs = by_severity[severity]
                icon = severity_icons.get(severity, "⚪")
                lines.append(f"\n{icon} [{severity.name}] {len(fs)} finding(s)")
                lines.append("-" * 50)
                for i, f in enumerate(fs, 1):
                    lines.append(f"  {i}. {f.detector}")
                    lines.append(f"     {f.description[:80]}")
                    lines.append(f"     � {Path(f.file_path).name}:{f.line_number}")
                    lines.append("")

        return "\n".join(lines)
