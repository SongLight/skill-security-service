#!/usr/bin/env python3
"""
Persistence detector - Detects persistence mechanism patterns.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class PersistenceDetector(BaseDetector):
    """Detects persistence mechanism patterns."""
    name = "PersistenceDetector"
    category = "persistence"
    
    _patterns = [
        (re.compile(r'crontab\s+(-[el]|-)', re.IGNORECASE), "crontab modification", 70),
        (re.compile(r'(>>|>)\s*.*crontab|cron\.d/', re.IGNORECASE), "cron job installation", 75),
        (re.compile(r'LaunchAgents|LaunchDaemons|\.plist', re.IGNORECASE), "macOS launchd persistence", 65),
        (re.compile(r'launchctl\s+(load|bootstrap)', re.IGNORECASE), "macOS launchctl loading", 80),
        (re.compile(r'systemctl\s+(enable|start)', re.IGNORECASE), "systemd service enablement", 60),
        (re.compile(r'/etc/systemd/system/.*\.service', re.IGNORECASE), "systemd service file creation", 70),
        (re.compile(r'HKEY_.*\\Run|CurrentVersion\\Run', re.IGNORECASE), "Windows registry run key", 80),
    ]
    _shell_write_pattern = re.compile(r'(>>|>)\s*.*(\.(bashrc|zshrc|profile|bash_profile))')

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
                    description=f"Persistence mechanism: {desc}",
                    confidence=confidence,
                ))
        if self._shell_write_pattern.search(line):
            findings.append(Finding(
                detector=self.name,
                severity=Severity.HIGH,
                category=self.category,
                file_path=file_path,
                line_number=line_num,
                line_content=line.strip()[:200],
                description="Persistence mechanism: writing to shell profile file",
                confidence=75,
            ))
        return findings
