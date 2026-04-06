#!/usr/bin/env python3
"""
Download and execute detector - Detects download-and-execute patterns.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class DownloadExecDetector(BaseDetector):
    """Detects download-and-execute patterns (curl|bash, wget|sh, etc.)."""
    name = "DownloadExecDetector"
    category = "download_exec"
    
    _patterns = [
        (re.compile(r'curl\s+.*\|\s*(ba)?sh', re.IGNORECASE), "curl pipe to shell", 95),
        (re.compile(r'wget\s+.*\|\s*(ba)?sh', re.IGNORECASE), "wget pipe to shell", 95),
        (re.compile(r'curl\s+.*-o\s+\S+.*&&\s*(ba)?sh', re.IGNORECASE), "curl download then execute", 90),
        (re.compile(r'wget\s+.*-O\s+\S+.*&&\s*(ba)?sh', re.IGNORECASE), "wget download then execute", 90),
        (re.compile(r'curl\s+.*\|\s*python', re.IGNORECASE), "curl pipe to python", 90),
        (re.compile(r'wget\s+.*\|\s*python', re.IGNORECASE), "wget pipe to python", 90),
        (re.compile(r'fetch\s*\(\s*["\'][^"\']+["\']\s*\).*\.then\s*\(\s*.*eval', re.IGNORECASE), "fetch + eval (JS)", 85),
        (re.compile(r'urllib\.request\.urlopen\s*\(\s*[^)]+\s*\).*exec\s*\(', re.IGNORECASE), "urllib + exec", 85),
        (re.compile(r'requests\.get\s*\(\s*[^)]+\s*\).*exec\s*\(', re.IGNORECASE), "requests + exec", 85),
    ]

    def scan_line(self, line: str, line_num: int, file_path: str) -> List[Finding]:
        findings = []
        for pattern, desc, confidence in self._patterns:
            if pattern.search(line):
                findings.append(Finding(
                    detector=self.name,
                    severity=self._calculate_severity(confidence),
                    category=self.category,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line.strip()[:200],
                    description=f"Download-and-execute pattern: {desc}",
                    confidence=confidence,
                ))
        return findings
