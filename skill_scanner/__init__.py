"""
Skill Security Scanner - AI Agent Skill Security Scanner

Detects malicious patterns, credential leaks, data exfiltration,
supply chain attacks, and other security threats in AI Agent skills.
"""

__version__ = "1.0.0"
__author__ = "Security Team"

from skill_scanner.core.types import Severity, Finding, Rule
from skill_scanner.scanner import SkillScanner

__all__ = [
    "SkillScanner",
    "Severity",
    "Finding",
    "Rule",
]
