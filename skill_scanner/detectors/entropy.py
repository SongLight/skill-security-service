#!/usr/bin/env python3
"""
Entropy detector - Detects high entropy content (encrypted/encoded payloads).
"""

import math
import os
from typing import Dict, List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class EntropyDetector(BaseDetector):
    """Detects high entropy content (encrypted/encoded payloads)."""
    name = "EntropyDetector"
    category = "obfuscation"

    @staticmethod
    def _shannon_entropy(data: str) -> float:
        if not data:
            return 0.0
        freq: Dict[str, int] = {}
        for c in data:
            freq[c] = freq.get(c, 0) + 1
        length = len(data)
        return -sum((count / length) * math.log2(count / length) for count in freq.values())

    def scan_line(self, line: str, line_num: int, file_path: str) -> List[Finding]:
        stripped = line.strip()
        if len(stripped) < 100:
            return []
        if stripped.startswith(("data:", "//", "#", "/*", "*")):
            return []
        basename = os.path.basename(file_path)
        if basename in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "Gemfile.lock", "poetry.lock"):
            return []
        ext = os.path.splitext(file_path)[1].lower()
        has_cjk = any('\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff' or '\uac00' <= c <= '\ud7af' for c in stripped[:50])
        threshold = 6.5 if (has_cjk or ext in ('.md', '.txt')) else 5.5
        entropy = self._shannon_entropy(stripped)
        if entropy > threshold:
            return [Finding(
                detector=self.name,
                severity=Severity.MEDIUM,
                category=self.category,
                file_path=file_path,
                line_number=line_num,
                line_content=stripped[:200],
                description=f"High entropy line (Shannon entropy: {entropy:.2f}) — possible encoded/encrypted payload",
                confidence=max(30, min(80, int((entropy - 5.5) * 40 + 30))),
            )]
        return []
