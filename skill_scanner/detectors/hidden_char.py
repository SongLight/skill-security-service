#!/usr/bin/env python3
"""
Hidden character detector - Detects hidden characters and Unicode bidi attacks.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class HiddenCharDetector(BaseDetector):
    """Detects hidden characters and Unicode bidi attacks."""
    name = "HiddenCharDetector"
    category = "obfuscation"
    
    _zwc_pattern = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff]')
    _bidi_pattern = re.compile(r'[\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]')

    def scan_line(self, line: str, line_num: int, file_path: str) -> List[Finding]:
        findings = []
        if self._zwc_pattern.search(line):
            findings.append(Finding(
                detector=self.name,
                severity=Severity.MEDIUM,
                category=self.category,
                file_path=file_path,
                line_number=line_num,
                line_content=repr(line.strip()[:200]),
                description="Zero-width characters detected (potential code hiding)",
                confidence=60,
            ))
        if self._bidi_pattern.search(line):
            findings.append(Finding(
                detector=self.name,
                severity=Severity.MEDIUM,
                category=self.category,
                file_path=file_path,
                line_number=line_num,
                line_content=repr(line.strip()[:200]),
                description="Unicode bidirectional control characters (Trojan Source attack)",
                confidence=80,
            ))
        return findings
