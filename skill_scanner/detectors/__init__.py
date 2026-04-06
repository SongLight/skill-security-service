"""
Security detectors for AI Agent Skills.
"""

from skill_scanner.detectors.base import BaseDetector
from skill_scanner.detectors.secrets import SecretsDetector
from skill_scanner.detectors.download_exec import DownloadExecDetector
from skill_scanner.detectors.injection import InjectionDetector
from skill_scanner.detectors.credential_theft import CredentialTheftDetector
from skill_scanner.detectors.persistence import PersistenceDetector
from skill_scanner.detectors.obfuscation import ObfuscationDetector
from skill_scanner.detectors.base64_detector import Base64Detector
from skill_scanner.detectors.exfiltration import ExfiltrationDetector
from skill_scanner.detectors.network import NetworkDetector
from skill_scanner.detectors.supply_chain import SupplyChainDetector
from skill_scanner.detectors.entropy import EntropyDetector
from skill_scanner.detectors.hidden_char import HiddenCharDetector
from skill_scanner.detectors.privilege_escalation import PrivilegeEscalationDetector
from skill_scanner.detectors.social_engineering import SocialEngineeringDetector
from skill_scanner.detectors.ioc_detector import IOCDetector

__all__ = [
    "BaseDetector",
    "SecretsDetector",
    "DownloadExecDetector",
    "InjectionDetector",
    "CredentialTheftDetector",
    "PersistenceDetector",
    "ObfuscationDetector",
    "Base64Detector",
    "ExfiltrationDetector",
    "NetworkDetector",
    "SupplyChainDetector",
    "EntropyDetector",
    "HiddenCharDetector",
    "PrivilegeEscalationDetector",
    "SocialEngineeringDetector",
    "IOCDetector",
]
