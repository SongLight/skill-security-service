#!/usr/bin/env python3
"""
Social engineering detector - Detects social engineering patterns.
"""

import os
import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class SocialEngineeringDetector(BaseDetector):
    """Detects social engineering patterns."""
    name = "SocialEngineeringDetector"
    category = "social_engineering"
    
    _suspicious_names = re.compile(
        r'(crypto[_-]?wallet|airdrop|free[_-]?token|security[_-]?update|urgent[_-]?fix|'
        r'claim[_-]?reward|bonus[_-]?token|wallet[_-]?connect|seed[_-]?phrase|'
        r'private[_-]?key[_-]?recovery|metamask[_-]?fix)',
        re.IGNORECASE,
    )
    _filename_suspicious = re.compile(
        r'(wallet|airdrop|claim|reward|metamask|seed|recovery|token[_-]?gen)',
        re.IGNORECASE,
    )

    def scan_file(self, content: str, file_path: str) -> List[Finding]:
        findings = []
        basename = os.path.basename(file_path)
        if self._filename_suspicious.search(basename):
            findings.append(Finding(
                detector=self.name,
                severity=Severity.MEDIUM,
                category=self.category,
                file_path=file_path,
                line_number=0,
                line_content=basename,
                description=f"Suspicious filename associated with social engineering: {basename}",
                confidence=50,
            ))
        for i, line in enumerate(content.splitlines(), 1):
            if self._suspicious_names.search(line):
                findings.append(Finding(
                    detector=self.name,
                    severity=Severity.LOW,
                    category=self.category,
                    file_path=file_path,
                    line_number=i,
                    line_content=line.strip()[:200],
                    description="Social engineering keyword detected (crypto/wallet/airdrop related)",
                    confidence=35,
                ))
                break
        return findings
