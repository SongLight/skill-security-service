#!/usr/bin/env python3
"""
Base64 detector - Detects suspicious Base64 encoded content.
"""

import base64
import os
import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class Base64Detector(BaseDetector):
    """Detects suspicious Base64 encoded content."""
    name = "Base64Detector"
    category = "obfuscation"
    
    _pattern = re.compile(r'[A-Za-z0-9+/]{50,}={0,2}')
    _image_prefix = re.compile(r'data:image/')
    _skip_patterns = re.compile(r'"integrity"\s*:|"sha256"\s*:|"sha512-|"sha384-')

    def scan_line(self, line: str, line_num: int, file_path: str) -> List[Finding]:
        findings = []
        if self._image_prefix.search(line):
            return findings
        basename = os.path.basename(file_path)
        if basename in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock"):
            return findings
        if self._skip_patterns.search(line):
            return findings
            
        for m in self._pattern.finditer(line):
            blob = m.group()
            try:
                decoded = base64.b64decode(blob)
                try:
                    text = decoded.decode("utf-8", errors="strict")
                    suspicious_kw = any(kw in text.lower() for kw in [
                        "exec", "eval", "import", "subprocess", "os.system",
                        "curl", "wget", "bash", "/bin/sh", "socket",
                    ])
                    severity = Severity.HIGH if suspicious_kw else Severity.MEDIUM
                    confidence = 85 if suspicious_kw else 50
                except UnicodeDecodeError:
                    severity = Severity.MEDIUM
                    confidence = 40
            except Exception:
                continue

            findings.append(Finding(
                detector=self.name,
                severity=severity,
                category=self.category,
                file_path=file_path,
                line_number=line_num,
                line_content=line.strip()[:200],
                description=f"Base64-encoded string ({len(blob)} chars) detected",
                confidence=confidence,
            ))
        return findings
