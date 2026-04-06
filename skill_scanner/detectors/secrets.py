#!/usr/bin/env python3
"""
Secrets detector - Detects hardcoded secrets and credentials.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class SecretsDetector(BaseDetector):
    """Detects hardcoded secrets and credentials."""
    name = "SecretsDetector"
    category = "credential_theft"
    
    _patterns = [
        (re.compile(r'AKIA[0-9A-Z]{16}'), "AWS Access Key ID", 95),
        (re.compile(r'(?i)(aws_access_key_id|aws_secret_access_key)\s*=\s*["\']?[a-zA-Z0-9/+=]{20,}'), "AWS credential", 90),
        (re.compile(r'-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----'), "Private key", 95),
        (re.compile(r'(?i)(api_key|apikey|secret_key|secretkey|access_token|auth_token)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{20,}["\']'), "API key/secret", 85),
        (re.compile(r'sk-[a-zA-Z0-9]{20,}'), "OpenAI API key", 90),
        (re.compile(r'ghp_[a-zA-Z0-9]{36}'), "GitHub Personal Access Token", 95),
        (re.compile(r'gho_[a-zA-Z0-9]{36}'), "GitHub OAuth Token", 95),
        (re.compile(r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}'), "GitHub Fine-grained PAT", 95),
        (re.compile(r'xox[baprs]-[a-zA-Z0-9\-]{10,}'), "Slack Token", 90),
        (re.compile(r'(?i)password\s*[=:]\s*["\'][^"\']{8,}["\']'), "Hardcoded password", 80),
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
                    description=f"Hardcoded secret detected: {desc}",
                    confidence=confidence,
                ))
        return findings
