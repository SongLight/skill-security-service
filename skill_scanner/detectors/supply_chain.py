#!/usr/bin/env python3
"""
Supply chain detector - Detects supply chain attack patterns.
"""

import json
import os
import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class SupplyChainDetector(BaseDetector):
    """Detects supply chain attack patterns."""
    name = "SupplyChainDetector"
    category = "supply_chain"

    def scan_file(self, content: str, file_path: str) -> List[Finding]:
        findings = []
        basename = os.path.basename(file_path)
        lines = content.splitlines()

        if basename == "package.json":
            try:
                pkg = json.loads(content)
                scripts = pkg.get("scripts", {})
                for hook in ("postinstall", "preinstall", "install", "prepare"):
                    if hook in scripts:
                        val = scripts[hook]
                        suspicious = any(kw in val.lower() for kw in [
                            "curl", "wget", "bash", "sh ", "python", "node -e", "eval",
                        ])
                        severity = Severity.CRITICAL if suspicious else Severity.HIGH
                        confidence = 90 if suspicious else 60
                        for i, line in enumerate(lines, 1):
                            if hook in line:
                                findings.append(Finding(
                                    detector=self.name,
                                    severity=severity,
                                    category=self.category,
                                    file_path=file_path,
                                    line_number=i,
                                    line_content=line.strip()[:200],
                                    description=f"npm lifecycle hook '{hook}': {val[:100]}",
                                    confidence=confidence,
                                ))
                                break
            except json.JSONDecodeError:
                pass

        if basename == "setup.py":
            for i, line in enumerate(lines, 1):
                if re.search(r'cmdclass\s*=', line):
                    findings.append(Finding(
                        detector=self.name,
                        severity=Severity.HIGH,
                        category=self.category,
                        file_path=file_path,
                        line_number=i,
                        line_content=line.strip()[:200],
                        description="Python setup.py custom command class (potential install hook)",
                        confidence=55,
                    ))

        return findings
