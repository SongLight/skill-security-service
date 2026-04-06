"""
报告生成器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime


class BaseReporter(ABC):
    """报告生成器基类"""
    
    def __init__(self, results: Dict[str, Any] = None, scanner_info: Dict[str, str] = None):
        self.results = results or {}
        self.scanner_info = scanner_info or {
            "name": "Code Scanner",
            "version": "1.0.0",
            "info_uri": "https://github.com/your-org/code-scanner"
        }
    
    @abstractmethod
    def generate(self) -> str:
        """生成报告内容"""
        pass
    
    @abstractmethod
    def get_extension(self) -> str:
        """获取文件扩展名"""
        pass
    
    def _get_current_time(self) -> str:
        """获取当前时间"""
        return datetime.now().isoformat()
    
    def _calculate_risk_score(self) -> float:
        """计算风险评分 (0-100)"""
        counts = self.results.get("summary", {}).get("severity_counts", {})
        total = sum(counts.values())
        if total == 0:
            return 0.0
        
        # 加权计算
        weights = {"CRITICAL": 100, "HIGH": 50, "MEDIUM": 20, "LOW": 5}
        score = sum(counts.get(sev, 0) * weight for sev, weight in weights.items())
        return min(100.0, score / max(total, 1) * 10)
    
    def _get_risk_level(self, score: float) -> str:
        """根据风险评分获取风险等级"""
        if score >= 80:
            return "CRITICAL"
        elif score >= 60:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        elif score >= 20:
            return "LOW"
        return "SAFE"
