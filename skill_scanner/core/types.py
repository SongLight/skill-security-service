"""
Core types and models for the skill scanner.
"""

from dataclasses import dataclass, asdict
from enum import IntEnum
from typing import Dict, Any


class Severity(IntEnum):
    """Security finding severity levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def __str__(self):
        return self.name


@dataclass
class Finding:
    """A security finding from a detector."""
    detector: str
    severity: Severity
    category: str
    file_path: str
    line_number: int
    line_content: str
    description: str
    confidence: int
    rule_id: str = ""
    skill_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = str(self.severity)
        return d


@dataclass
class Rule:
    """A security detection rule."""
    id: str
    name: str
    pattern: str
    confidence: int
    description: str
    severity: Severity = Severity.MEDIUM


@dataclass
class ScanResult:
    """Scan result container."""
    path: str
    findings: list
    total_files: int = 0
    scan_time: float = 0.0
