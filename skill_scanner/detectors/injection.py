#!/usr/bin/env python3
"""
Injection detector - Detects code/command injection patterns.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class InjectionDetector(BaseDetector):
    """Detects code/command injection patterns."""
    name = "InjectionDetector"
    category = "code_injection"
    
    _patterns = [
        (re.compile(r'\beval\s*\(\s*[^"\'`\d]'), "eval() with non-literal argument", 85),
        (re.compile(r'(?<!\.)exec\s*\(\s*[^"\'`\d]'), "exec() with non-literal argument", 85),
        (re.compile(r'__import__\s*\('), "__import__ dynamic import", 75),
        (re.compile(r'\bcompile\s*\('), "compile() function call", 70),
        (re.compile(r'\bos\.system\s*\('), "os.system() call", 80),
        (re.compile(r'\bos\.popen\s*\('), "os.popen() call", 80),
        (re.compile(r'\bsubprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True'), "subprocess with shell=True", 75),
        (re.compile(r'\bexecfile\s*\('), "execfile() call (Python 2)", 80),
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
                    description=f"Code/command injection risk: {desc}",
                    confidence=confidence,
                ))
        return findings
