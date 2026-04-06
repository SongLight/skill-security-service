#!/usr/bin/env python3
"""
Network detector - Detects network access patterns.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class NetworkDetector(BaseDetector):
    """Detects network access patterns."""
    name = "NetworkDetector"
    category = "network_access"
    
    _patterns = [
        (re.compile(r'\bsocket\.(socket|connect|create_connection)\b'), "Python socket usage", 50),
        (re.compile(r'\bhttp\.client\.(HTTPConnection|HTTPSConnection)\b'), "Python http.client usage", 40),
        (re.compile(r'\burllib\.request\.(urlopen|Request)\b'), "Python urllib usage", 40),
        (re.compile(r'\brequests\.(get|post|put|delete|patch|head)\s*\('), "Python requests library", 35),
        (re.compile(r'\bfetch\s*\(\s*["\']https?://'), "JavaScript fetch() call", 35),
        (re.compile(r'\bXMLHttpRequest\b'), "XMLHttpRequest usage", 35),
        (re.compile(r'\baxios\.(get|post|put|delete|patch)\s*\('), "axios HTTP call", 35),
        (re.compile(r'\bcurl\s+-'), "curl command invocation", 45),
        (re.compile(r'\bwget\s+'), "wget command invocation", 45),
        (re.compile(r'\bnet\.createConnection\b|require\s*\(\s*["\']net["\']\s*\)'), "Node.js net module", 50),
    ]

    def scan_line(self, line: str, line_num: int, file_path: str) -> List[Finding]:
        findings = []
        for pattern, desc, confidence in self._patterns:
            if pattern.search(line):
                findings.append(Finding(
                    detector=self.name,
                    severity=Severity.MEDIUM,
                    category=self.category,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line.strip()[:200],
                    description=f"Network call detected: {desc}",
                    confidence=confidence,
                ))
        return findings
