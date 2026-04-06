"""
Markdown报告生成器 - 生成适合文档和PR的Markdown格式报告
"""
from typing import Dict
from .base import BaseReporter


class MarkdownReporter(BaseReporter):
    """生成Markdown格式报告"""
    
    def get_extension(self) -> str:
        return "md"
    
    def generate(self, results_data: Dict = None) -> str:
        """生成Markdown报告"""
        if results_data:
            self.results = results_data
        
        risk_score = self._calculate_risk_score()
        risk_level = self._get_risk_level(risk_score)
        
        md = f"""# 🔒 Code Scanner 安全扫描报告

> **扫描时间**: {self._get_current_time()}  
> **扫描器**: {self.scanner_info['name']} v{self.scanner_info['version']}

---

## 📊 风险概览

| 指标 | 值 |
|------|-----|
| **风险评分** | {risk_score:.1f}/100 |
| **风险等级** | {self._get_risk_badge(risk_level)} |
| **扫描Skills** | {self.results.get('summary', {}).get('skills_scanned', 0)} |
| **扫描文件** | {self.results.get('summary', {}).get('files_scanned', 0)} |

---

## 📈 严重级别统计

{self._generate_severity_table()}

---

## 🔍 安全发现

{self._generate_findings_section()}

---

## 📝 修复建议

{self._generate_remediation()}

---

*报告由 {self.scanner_info['name']} 自动生成*
"""
        return md
    
    def _get_risk_badge(self, risk_level: str) -> str:
        """获取风险等级徽章"""
        badges = {
            "CRITICAL": "🔴 CRITICAL",
            "HIGH": "🟠 HIGH",
            "MEDIUM": "🟡 MEDIUM",
            "LOW": "🟢 LOW",
            "SAFE": "✅ SAFE"
        }
        return badges.get(risk_level, risk_level)
    
    def _generate_severity_table(self) -> str:
        """生成严重级别统计表"""
        counts = self.results.get("summary", {}).get("severity_counts", {})
        
        table = "| 严重级别 | 数量 | 状态 |\n"
        table += "|---------|------|------|\n"
        
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = counts.get(severity, 0)
            status = "⚠️ 需处理" if count > 0 else "✅ 正常"
            badge = self._get_risk_badge(severity)
            table += f"| {badge} | {count} | {status} |\n"
        
        return table
    
    def _generate_findings_section(self) -> str:
        """生成发现详情部分"""
        skills = self.results.get("skills", {})
        
        # 过滤掉 summary 相关的键
        skill_findings = {k: v for k, v in skills.items() if not k.endswith("_summary")}
        skill_summaries = {k.replace("_summary", ""): v for k, v in skills.items() if k.endswith("_summary")}
        
        if not skill_findings or all(len(f) == 0 for f in skill_findings.values()):
            return "✅ **未发现安全问题**\n\n本次扫描未发现任何安全威胁。"
        
        sections = []
        
        # 按 skill 分组输出
        sections.append("## 🔹 按 Skill 分组的安全发现\n")
        
        for skill_name, findings in sorted(skill_findings.items()):
            # 获取该 skill 的摘要信息
            skill_summary = skill_summaries.get(skill_name, {})
            findings_count = skill_summary.get("findings_count", len(findings))
            
            if findings_count > 0:
                sections.append(f"### 📦 Skill: {skill_name}\n")
                sections.append(f"**发现问题数**: {findings_count}\n")
                
                # 显示该 skill 的严重性分布
                severity_counts = skill_summary.get("severity_counts", {})
                if severity_counts:
                    sev_parts = []
                    if severity_counts.get("CRITICAL", 0) > 0:
                        sev_parts.append(f"🔴 CRITICAL: {severity_counts['CRITICAL']}")
                    if severity_counts.get("HIGH", 0) > 0:
                        sev_parts.append(f"🟠 HIGH: {severity_counts['HIGH']}")
                    if severity_counts.get("MEDIUM", 0) > 0:
                        sev_parts.append(f"🟡 MEDIUM: {severity_counts['MEDIUM']}")
                    if severity_counts.get("LOW", 0) > 0:
                        sev_parts.append(f"🔵 LOW: {severity_counts['LOW']}")
                    
                    if sev_parts:
                        sections.append(f"**严重级别分布**: {' | '.join(sev_parts)}\n")
                
                sections.append("\n| # | 检测器 | 问题描述 | 位置 |\n")
                sections.append("|---|--------|----------|------|\n")
                
                # 按严重级别排序
                sorted_findings = sorted(
                    findings,
                    key=lambda f: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(f.get("severity", "LOW"), 4)
                )
                
                for i, finding in enumerate(sorted_findings, 1):
                    detector = finding.get("detector", "Unknown")
                    description = finding.get("description", "")[:80]
                    file_path = finding.get("file_path", "")
                    line = finding.get("line_number", 0)
                    
                    # 提取文件名
                    import os
                    filename = os.path.basename(file_path) if file_path else "Unknown"
                    
                    # 严重级别图标
                    severity = finding.get("severity", "LOW")
                    severity_icon = {
                        "CRITICAL": "🔴",
                        "HIGH": "🟠",
                        "MEDIUM": "🟡",
                        "LOW": "🔵"
                    }.get(severity, "⚪")
                    
                    sections.append(f"| {i} | {severity_icon} {detector} | {description} | {filename}:{line} |\n")
                
                sections.append("\n")
            else:
                sections.append(f"### 📦 Skill: {skill_name}\n")
                sections.append("**✅ 未发现安全问题**\n")
            
            sections.append("---\n")
        
        return "".join(sections)
    
    def _generate_finding_detail(self, finding: dict, index: int) -> str:
        """生成单个发现的详情"""
        detector = finding.get("detector", "Unknown")
        file_path = finding.get("file_path", "Unknown")
        line_number = finding.get("line_number", 0)
        description = finding.get("description", "")
        confidence = finding.get("confidence", 0)
        line_content = finding.get("line_content", "")
        
        detail = f"""#### {index}. {detector}

- **位置**: `{file_path}:{line_number}`
- **描述**: {description}
- **置信度**: {confidence}%
"""
        
        if line_content:
            detail += f"""
```
{line_content[:200]}
```
"""
        
        return detail
    
    def _generate_remediation(self) -> str:
        """生成修复建议"""
        counts = self.results.get("summary", {}).get("severity_counts", {})
        
        if counts.get("CRITICAL", 0) > 0:
            return """### 🚨 立即行动

检测到 **CRITICAL** 级别的问题，请立即：

1. **隔离受影响的Skill**
2. **轮换可能泄露的凭证**
3. **审查相关代码的完整性**
4. **检查是否有数据外泄迹象**

### 通用修复建议

- 移除所有硬编码的密钥和凭证
- 使用环境变量或密钥管理服务
- 审查所有外部网络请求
- 避免使用危险的函数（eval, exec等）
"""
        elif counts.get("HIGH", 0) > 0:
            return """### ⚠️ 建议处理

检测到 **HIGH** 级别的问题，建议：

1. **人工审查相关代码**
2. **评估实际风险影响**
3. **实施适当的缓解措施**

### 通用最佳实践

- 定期轮换API密钥
- 使用最小权限原则
- 审查第三方依赖
"""
        else:
            return """### ✅ 安全状态良好

未发现严重安全问题。建议：

- 继续保持安全编码实践
- 定期进行安全扫描
- 关注依赖项的安全更新
"""