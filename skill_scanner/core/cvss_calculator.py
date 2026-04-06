#!/usr/bin/env python3
"""
CVSS 3.1 Score Calculator
Based on First.org CVSS v3.1 Specification
"""

from typing import Dict, Tuple
import math


CVSS_METRICS = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "PR": {
        "U": {"N": 0.85, "L": 0.62, "H": 0.27},
        "C": {"N": 0.85, "L": 0.68, "H": 0.50},
    },
    "UI": {"N": 0.85, "R": 0.62},
    "S":  {"U": 6.42, "C": 7.52},
    "C":  {"N": 0.0, "L": 0.22, "H": 0.56},
    "I":  {"N": 0.0, "L": 0.22, "H": 0.56},
    "A":  {"N": 0.0, "L": 0.22, "H": 0.56},
}


CVSS_VECTOR_TEMPLATES = {
    "download_exec": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "base": 10.0,
        "desc": "下载执行"
    },
    "credential_theft": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "base": 9.1,
        "desc": "凭证盗取"
    },
    "secrets": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "base": 7.5,
        "desc": "硬编码凭证"
    },
    "injection": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "base": 9.8,
        "desc": "代码注入"
    },
    "code_injection": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "base": 9.8,
        "desc": "代码注入"
    },
    "persistence": {
        "vector": "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "base": 7.0,
        "desc": "持久化驻留"
    },
    "obfuscation": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N",
        "base": 5.3,
        "desc": "代码混淆"
    },
    "exfiltration": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "base": 7.5,
        "desc": "数据外传"
    },
    "data_exfiltration": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "base": 7.5,
        "desc": "数据外传"
    },
    "network": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N",
        "base": 4.3,
        "desc": "异常网络行为"
    },
    "network_access": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N",
        "base": 4.3,
        "desc": "网络访问"
    },
    "supply_chain": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "base": 10.0,
        "desc": "供应链风险"
    },
    "entropy": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "base": 3.7,
        "desc": "熵值异常"
    },
    "hidden_char": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N",
        "base": 1.7,
        "desc": "隐藏字符"
    },
    "privilege_escalation": {
        "vector": "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "base": 7.0,
        "desc": "权限提升"
    },
    "social_engineering": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N",
        "base": 4.3,
        "desc": "社会工程学"
    },
    "threat_intelligence": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "base": 10.0,
        "desc": "威胁情报"
    },
    "ioc": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "base": 10.0,
        "desc": "威胁情报"
    },
    "base64": {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "base": 3.7,
        "desc": "Base64 编码"
    },
}


def parse_vector(vector: str) -> Dict[str, str]:
    """Parse CVSS vector string to dictionary."""
    result = {}
    if not vector.startswith("CVSS:3.1/"):
        return result
    for item in vector.split("/")[1:]:
        if ":" in item:
            key, value = item.split(":", 1)
            result[key] = value
    return result


def _roundup(value: float) -> float:
    """Round up to 1 decimal place."""
    return math.ceil(value * 10) / 10


def calculate_cvss_base(metrics: Dict[str, str]) -> float:
    """Calculate CVSS 3.1 Base Score."""
    if not metrics:
        return 0.0
    
    try:
        AV = CVSS_METRICS["AV"][metrics.get("AV", "N")]
        AC = CVSS_METRICS["AC"][metrics.get("AC", "L")]
        UI = CVSS_METRICS["UI"][metrics.get("UI", "N")]
        S = metrics.get("S", "U")
        C = CVSS_METRICS["C"][metrics.get("C", "N")]
        I = CVSS_METRICS["I"][metrics.get("I", "N")]
        A = CVSS_METRICS["A"][metrics.get("A", "N")]
        
        PR_U = CVSS_METRICS["PR"]["U"]
        PR_C = CVSS_METRICS["PR"]["C"]
        
        if S == "C":
            PR = PR_C[metrics.get("PR", "N")]
            scope_change = 1.08
        else:
            PR = PR_U[metrics.get("PR", "N")]
            scope_change = 1.0
        
        impact = scope_change * (1 - (1 - C) * (1 - I) * (1 - A))
        
        if impact <= 0:
            return 0.0
        
        exploitability = 8.22 * AV * AC * UI * PR
        
        if S == "U":
            base_score = _roundup(min(impact + exploitability, 10))
        else:
            base_score = _roundup(min(1.08 * (impact + exploitability), 10))
        
        return base_score
        
    except (KeyError, TypeError):
        return 0.0


def calculate_severity(cvss_score: float) -> Tuple[str, int]:
    """
    Convert CVSS score to severity level.
    
    Returns: (severity_name, severity_value)
    """
    if cvss_score >= 9.0:
        return "CRITICAL", 4
    elif cvss_score >= 7.0:
        return "HIGH", 3
    elif cvss_score >= 4.0:
        return "MEDIUM", 2
    elif cvss_score > 0.0:
        return "LOW", 1
    else:
        return "NONE", 0


def get_cvss_for_category(category: str) -> Dict:
    """Get CVSS vector template for a detection category."""
    return CVSS_VECTOR_TEMPLATES.get(category, {
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N",
        "base": 0.0,
        "desc": "未知类别"
    })


def calculate_severity_with_confidence(category: str, confidence: int) -> Tuple[str, int, float]:
    """
    Calculate final severity based on CVSS and confidence.
    
    Args:
        category: Detection category
        confidence: Detection confidence (0-100)
    
    Returns:
        (severity_name, severity_value, cvss_score)
    """
    cvss_template = get_cvss_for_category(category)
    base_score = cvss_template["base"]
    
    confidence_factor = confidence / 100.0
    
    if confidence >= 90:
        adjusted_score = base_score
    elif confidence >= 70:
        adjusted_score = base_score * 0.9
    elif confidence >= 50:
        adjusted_score = base_score * 0.7
    else:
        adjusted_score = base_score * 0.5
    
    severity_name, severity_value = calculate_severity(adjusted_score)
    
    return severity_name, severity_value, round(adjusted_score, 1)


if __name__ == "__main__":
    print("=== CVSS 3.1 Calculator Test ===\n")
    
    test_cases = [
        ("secrets", 90),
        ("download_exec", 95),
        ("injection", 85),
        ("credential_theft", 80),
        ("persistence", 75),
        ("network", 60),
        ("hidden_char", 50),
    ]
    
    for category, confidence in test_cases:
        severity, value, score = calculate_severity_with_confidence(category, confidence)
        template = CVSS_VECTOR_TEMPLATES.get(category, {})
        print(f"{category:20s} confidence={confidence:3d}% -> CVSS={score:.1f} [{severity}]")
