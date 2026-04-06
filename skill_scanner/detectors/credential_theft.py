#!/usr/bin/env python3
"""
Credential theft detector - Detects credential theft patterns.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class CredentialTheftDetector(BaseDetector):
    """Detects credential theft patterns."""
    name = "CredentialTheftDetector"
    category = "credential_theft"
    
    _patterns = [
        (re.compile(r'osascript.*display\s+dialog.*password', re.IGNORECASE), "macOS password dialog via osascript", 95),
        (re.compile(r'osascript.*display\s+dialog.*hidden\s+answer', re.IGNORECASE), "macOS hidden-input dialog", 95),
        (re.compile(r'security\s+find-(generic|internet)-password', re.IGNORECASE), "macOS Keychain password extraction", 90),
        (re.compile(r'security\s+dump-keychain', re.IGNORECASE), "macOS Keychain dump", 95),
        (re.compile(r'cat\s+.*\.ssh/(id_rsa|id_ed25519|id_ecdsa)', re.IGNORECASE), "SSH private key reading", 90),
        (re.compile(r'(open|cat|read).*\.ssh/id_', re.IGNORECASE), "SSH private key access", 85),
        (re.compile(r'cat\s+.*\.(env|npmrc|pypirc|netrc)', re.IGNORECASE), "Credential file reading", 85),
        (re.compile(r'\.aws/credentials', re.IGNORECASE), "AWS credentials file access", 85),
        (re.compile(r'Cookies/Cookies\.binarycookies|Login\s*Data|cookies\.sqlite', re.IGNORECASE), "Browser credential/cookie access", 90),
    ]

    def scan_line(self, line: str, line_num: int, file_path: str) -> List[Finding]:
        findings = []
        for pattern, desc, confidence in self._patterns:
            if pattern.search(line):
                findings.append(Finding(
                    detector=self.name,
                    severity=Severity.CRITICAL,
                    category=self.category,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line.strip()[:200],
                    description=f"Credential theft technique: {desc}",
                    confidence=confidence,
                ))
        return findings
