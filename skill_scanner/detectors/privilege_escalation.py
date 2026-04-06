#!/usr/bin/env python3
"""
Privilege escalation detector - Detects privilege escalation patterns.
"""

import os
import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class PrivilegeEscalationDetector(BaseDetector):
    """Detects privilege escalation patterns."""
    name = "PrivilegeEscalationDetector"
    category = "privilege_escalation"
    
    _doc_extensions = {'.md', '.txt', '.rst', '.adoc'}
    _patterns = [
        (re.compile(r'\bsudo\s+'), "sudo invocation", 65),
        (re.compile(r'chmod\s+777\b'), "chmod 777 (world-writable)", 80),
        (re.compile(r'chmod\s+[0-7]*[4-7][0-7]{2}\s'), "chmod with setuid/setgid bit", 70),
        (re.compile(r'chmod\s+\+s\b'), "chmod +s (setuid)", 85),
        (re.compile(r'chown\s+root\b'), "chown to root", 70),
        (re.compile(r'\bos\.setuid\s*\(|os\.setgid\s*\('), "Python setuid/setgid call", 85),
        (re.compile(r'dscl\s+\.\s+-append\s+/Groups/admin'), "macOS admin group modification", 90),
    ]

    def scan_line(self, line: str, line_num: int, file_path: str) -> List[Finding]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self._doc_extensions:
            return []
        findings = []
        for pattern, desc, confidence in self._patterns:
            if pattern.search(line):
                findings.append(Finding(
                    detector=self.name,
                    severity=Severity.HIGH,
                    category=self.category,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line.strip()[:200],
                    description=f"Privilege escalation: {desc}",
                    confidence=confidence,
                ))
        return findings
