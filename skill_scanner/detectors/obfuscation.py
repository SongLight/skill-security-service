#!/usr/bin/env python3
"""
Obfuscation detector - Detects code obfuscation patterns.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class ObfuscationDetector(BaseDetector):
    """Detects code obfuscation patterns."""
    name = "ObfuscationDetector"
    category = "obfuscation"
    
    _patterns = [
        (re.compile(r'\beval\s*\(\s*[^"\'`\d]'), "eval() with non-literal argument", 80),
        (re.compile(r'(?<!\.)exec\s*\(\s*[^"\'`\d]'), "exec() with non-literal argument", 80),
        (re.compile(r'\\x[0-9a-fA-F]{2}(\\x[0-9a-fA-F]{2}){5,}'), "Hex-encoded string sequence", 70),
        (re.compile(r'chr\s*\(\s*\d+\s*\)\s*\+\s*chr\s*\(\s*\d+\s*\)(\s*\+\s*chr\s*\(\s*\d+\s*\)){3,}'), "chr() chain concatenation", 85),
        (re.compile(r'\[::\s*-1\s*\]'), "String reversal (Python slice)", 45),
        (re.compile(r'\.split\s*\(\s*["\'].*["\']\s*\)\.reverse\s*\(\s*\)\.join'), "String split-reverse-join (JS)", 60),
        (re.compile(r'String\.fromCharCode\s*\(.*,.*,.*,.*\)'), "String.fromCharCode with multiple args", 70),
        (re.compile(r'atob\s*\(\s*[^)]{20,}\s*\)'), "atob() with long encoded string", 65),
    ]

    def scan_line(self, line: str, line_num: int, file_path: str) -> List[Finding]:
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
                    description=f"Obfuscation technique: {desc}",
                    confidence=confidence,
                ))
        return findings
