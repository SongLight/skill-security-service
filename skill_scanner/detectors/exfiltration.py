#!/usr/bin/env python3
"""
Exfiltration detector - Detects data exfiltration patterns.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class ExfiltrationDetector(BaseDetector):
    """Detects data exfiltration patterns."""
    name = "ExfiltrationDetector"
    category = "data_exfiltration"
    
    _sensitive_dir_pattern = re.compile(r'(\.ssh|\.aws|\.gnupg|\.kube|\.config/gcloud|\.npmrc|\.pypirc)')
    _upload_pattern = re.compile(r'(requests\.(post|put)|urllib\.request\.(urlopen|Request)|http\.client|fetch\s*\(|\.upload)', re.IGNORECASE)

    def scan_file(self, content: str, file_path: str) -> List[Finding]:
        findings = []
        lines = content.splitlines()
        has_sensitive_dir = False
        has_upload = False
        sensitive_lines = []

        for i, line in enumerate(lines, 1):
            if self._sensitive_dir_pattern.search(line):
                has_sensitive_dir = True
                sensitive_lines.append((i, line))
            if self._upload_pattern.search(line):
                has_upload = True

        for i, line in enumerate(lines, 1):
            if re.search(r'zipfile|ZipFile|make_archive', line, re.IGNORECASE):
                if has_upload:
                    findings.append(Finding(
                        detector=self.name,
                        severity=Severity.HIGH,
                        category=self.category,
                        file_path=file_path,
                        line_number=i,
                        line_content=line.strip()[:200],
                        description="ZIP archive creation combined with upload capability — possible data exfiltration",
                        confidence=75,
                    ))
            if re.search(r'glob\.(glob|iglob)\s*\(\s*["\'].*(\*\*|/home|~)', line):
                findings.append(Finding(
                    detector=self.name,
                    severity=Severity.HIGH,
                    category=self.category,
                    file_path=file_path,
                    line_number=i,
                    line_content=line.strip()[:200],
                    description="Recursive file enumeration of sensitive directories",
                    confidence=60,
                ))

        if has_sensitive_dir and has_upload and sensitive_lines:
            ln, lc = sensitive_lines[0]
            findings.append(Finding(
                detector=self.name,
                severity=Severity.HIGH,
                category=self.category,
                file_path=file_path,
                line_number=ln,
                line_content=lc.strip()[:200],
                description="Access to sensitive directories combined with network upload capability",
                confidence=70,
            ))

        return findings
