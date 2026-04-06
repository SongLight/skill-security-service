"""
Base detector class for all security detectors.
"""

from typing import List, Optional
from pathlib import Path

from skill_scanner.core.types import Finding, Severity
from skill_scanner.core.cvss_calculator import calculate_severity_with_confidence


class BaseDetector:
    """Base class for all security detectors."""
    name: str = "BaseDetector"
    category: str = "generic"

    def scan_line(self, line: str, line_num: int, file_path: str) -> List[Finding]:
        """Scan a single line. Override in subclasses."""
        return []

    def scan_file(self, content: str, file_path: str) -> List[Finding]:
        """Scan entire file. Default: per-line scan."""
        findings = []
        for i, line in enumerate(content.splitlines(), 1):
            findings.extend(self.scan_line(line, i, file_path))
        return findings

    def scan_skill(self, skill_path: Path) -> List[Finding]:
        """Scan an entire skill directory."""
        findings = []
        if not skill_path.exists():
            return findings

        for file_path in skill_path.rglob("*"):
            if file_path.is_file() and not self._should_skip(file_path):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    findings.extend(self.scan_file(content, str(file_path)))
                except Exception:
                    pass
        return findings

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = {".git", "__pycache__", ".venv", "node_modules"}
        return any(part in skip_patterns for part in file_path.parts)

    def _calculate_severity(self, confidence: int) -> Severity:
        """Calculate severity based on category and confidence using CVSS."""
        severity_name, _, _ = calculate_severity_with_confidence(
            self.category, confidence
        )
        return Severity[severity_name] if severity_name in Severity.__members__ else Severity.MEDIUM
