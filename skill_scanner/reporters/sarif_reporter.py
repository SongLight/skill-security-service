"""
SARIF报告生成器 - 生成SARIF格式报告，兼容GitHub Code Scanning
SARIF版本: 2.1.0
"""
import json
import hashlib
from typing import Dict
from .base import BaseReporter


class SARIFReporter(BaseReporter):
    """生成SARIF格式报告，用于GitHub Code Scanning集成"""
    
    def get_extension(self) -> str:
        return "sarif"
    
    def generate(self, results_data: Dict = None) -> str:
        """生成SARIF报告"""
        if results_data:
            self.results = results_data
        
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [self._generate_run()]
        }
        return json.dumps(sarif, indent=2, ensure_ascii=False)
    
    def _generate_run(self) -> dict:
        """生成单个run对象"""
        return {
            "tool": self._generate_tool(),
            "invocations": [self._generate_invocation()],
            "results": self._generate_results(),
            "artifacts": self._generate_artifacts(),
        }
    
    def _generate_tool(self) -> dict:
        """生成工具信息"""
        return {
            "driver": {
                "name": self.scanner_info["name"],
                "informationUri": self.scanner_info.get("info_uri", ""),
                "version": self.scanner_info.get("version", "1.0.0"),
                "rules": self._generate_rules()
            }
        }
    
    def _generate_rules(self) -> list:
        """生成规则定义"""
        rules = []
        seen_detectors = set()
        
        skills = self.results.get("skills", {})
        for skill_name, findings in skills.items():
            if skill_name.endswith("_summary"):
                continue
            if not isinstance(findings, list):
                continue
            for finding in findings:
                detector = finding.get("detector", "Unknown")
                if detector in seen_detectors:
                    continue
                seen_detectors.add(detector)
                
                severity = finding.get("severity", "LOW")
                rules.append({
                    "id": detector,
                    "name": detector,
                    "shortDescription": {
                        "text": finding.get("description", "Security finding")
                    },
                    "fullDescription": {
                        "text": f"{finding.get('category', 'security')} detection"
                    },
                    "defaultConfiguration": {
                        "level": self._severity_to_level(severity)
                    },
                    "properties": {
                        "category": finding.get("category", "security"),
                        "severity": severity
                    }
                })
        
        return rules
    
    def _generate_invocation(self) -> dict:
        """生成调用信息"""
        return {
            "executionSuccessful": True,
            "startTimeUtc": self._get_current_time(),
            "endTimeUtc": self._get_current_time(),
        }
    
    def _generate_results(self) -> list:
        """生成扫描结果"""
        results = []
        skills = self.results.get("skills", {})
        
        for skill_name, findings in skills.items():
            if skill_name.endswith("_summary"):
                continue
            if not isinstance(findings, list):
                continue
            for finding in findings:
                result = {
                    "ruleId": finding.get("detector", "Unknown"),
                    "ruleIndex": 0,
                    "level": self._severity_to_level(finding.get("severity", "LOW")),
                    "message": {
                        "text": finding.get("description", "Security issue detected")
                    },
                    "locations": [self._generate_location(finding)],
                    "properties": {
                        "confidence": finding.get("confidence", 0),
                        "category": finding.get("category", "security"),
                    }
                }
                results.append(result)
        
        return results
    
    def _generate_location(self, finding: dict) -> dict:
        """生成位置信息"""
        file_path = finding.get("file_path", "")
        line_number = finding.get("line_number", 1)
        
        # 计算文件哈希（用于物理位置）
        file_hash = hashlib.sha256(file_path.encode()).hexdigest()[:16]
        
        return {
            "physicalLocation": {
                "artifactLocation": {
                    "uri": file_path,
                    "uriBaseId": "%SRCROOT%"
                },
                "region": {
                    "startLine": line_number,
                    "snippet": {
                        "text": finding.get("line_content", "")[:200]
                    }
                }
            },
            "logicalLocations": [
                {
                    "fullyQualifiedName": file_path,
                    "kind": "module"
                }
            ]
        }
    
    def _generate_artifacts(self) -> list:
        """生成工件（文件）列表"""
        artifacts = []
        seen_files = set()
        
        skills = self.results.get("skills", {})
        for skill_name, findings in skills.items():
            if skill_name.endswith("_summary"):
                continue
            if not isinstance(findings, list):
                continue
            for finding in findings:
                file_path = finding.get("file_path", "")
                if file_path in seen_files:
                    continue
                seen_files.add(file_path)
                
                artifacts.append({
                    "location": {
                        "uri": file_path,
                        "uriBaseId": "%SRCROOT%"
                    },
                    "sourceLanguage": self._detect_language(file_path)
                })
        
        return artifacts
    
    def _severity_to_level(self, severity: str) -> str:
        """将严重级别转换为SARIF级别"""
        mapping = {
            "CRITICAL": "error",
            "HIGH": "error",
            "MEDIUM": "warning",
            "LOW": "note"
        }
        return mapping.get(severity.upper(), "warning")
    
    def _detect_language(self, file_path: str) -> str:
        """检测文件语言"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".sh": "shell",
            ".bash": "shell",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".rb": "ruby",
            ".php": "php",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
        }
        
        ext = file_path.lower()
        for ext_suffix, lang in ext_map.items():
            if ext.endswith(ext_suffix):
                return lang
        return "unknown"
