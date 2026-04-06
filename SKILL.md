---
name: skill-security-scanner
description: AI Agent Skills Security Scanner - Scan skills for malicious code, security vulnerabilities and risk patterns with CVSS 3.1 scoring
metadata:
  version: 1.0.0
  author: Skill Security Scanner Team
  license: MIT
  homepage: https://gitee.com/yzj1/skill-security-scanner
  openclaw:
    emoji: 🛡️
    os: [windows, darwin, linux]
  lobehub:
    category: security
    tags: [security, scanner, malware-detection, code-audit]
---

# 🛡️ Skill Security Scanner

AI Agent Skills 安全扫描工具 - 使用 CVSS 3.1 评分系统检测 Skills 中的恶意代码、安全漏洞和风险模式。

## 功能特性

### 🔍 多维度安全检测

- **18 种风险检测器**：覆盖 CRITICAL、HIGH、MEDIUM、LOW 四个风险等级
- **CVSS 3.1 评分**：专业量化风险等级，科学评估安全威胁
- **IOC 威胁情报**：匹配已知恶意 IP、域名、文件哈希
- **LLM 语义分析**：通过大语言模型深度理解代码意图，发现隐蔽威胁

### 🎯 检测能力

| 风险等级 | 检测器数量 | 典型威胁 |
|----------|-----------|----------|
| 🔴 CRITICAL | 4 | 硬编码凭证、远程代码执行、命令注入 |
| 🟠 HIGH | 7 | 凭证盗取、持久化驻留、数据外传 |
| 🟡 MEDIUM | 3 | Base64 编码隐藏、异常网络连接 |
| 🟢 LOW | 1 | 隐藏字符注入 |

## 使用方法

### 快速扫描

```
Scan the skills in directory /path/to/skills for security issues
```

### 指定格式输出

```
Scan skills at /path/to/skills and output HTML report
```

```
Scan skills at /path/to/skills and output JSON format
```

### 启用高级检测

```
Scan with LLM deep analysis enabled
```

```
Scan with IOC detection and YARA rules enabled
```

### 过滤风险等级

```
Scan and only show high severity issues
```

```
Scan and filter out low severity findings
```

## 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--path` | 扫描路径（必需） | `--path /path/to/skills` |
| `--format` | 输出格式 | `--format html` |
| `--severity` | 最低风险等级 | `--severity high` |
| `--use-llm` | 启用 LLM 分析 | `--use-llm` |
| `--use-ioc` | 启用 IOC 检测 | `--use-ioc` |
| `--use-yara` | 启用 YARA 规则 | `--use-yara` |
| `--output` | 输出文件 | `-o report.html` |

## 输出示例

### 文本输出

```
🛡️ Skill Security Scanner Report
==================================================

📁 Skill: example-skill
├── 🔴 CRITICAL [CVSS 9.8]
│   └── SecretsDetector: 硬编码 API 密钥
│       File: src/api.py:15
├── 🟠 HIGH [CVSS 7.5]
│   └── NetworkDetector: 异常网络连接
│       File: src/client.py:42

Summary: 2 risks found
```

### HTML 报告

生成专业美观的 HTML 报告，包含风险分布图表、详细漏洞说明和修复建议。

### JSON 输出

适用于自动化集成和 CI/CD 流程。

## 技术架构

- **零依赖**：无需外部第三方库，支持离线部署
- **多检测器**：静态规则 + 威胁情报 + LLM 语义分析
- **多格式输出**：Text、JSON、HTML、SARIF、Markdown
- **REST API**：支持服务化部署，集成企业安全平台

## 适用场景

- 🤖 **Agent 平台安全审核**：在 Skills 上架前进行安全检测
- 🔒 **企业内部审计**：扫描内部开发的 Skills 安全性
- 🧪 **安全研究分析**：分析恶意 Skills 的攻击手法
- ⚙️ **CI/CD 集成**：集成到自动化发布流程

## 安全建议

1. **上架前必扫**：所有 Skills 上架前必须通过安全扫描
2. **定期复审**：定期扫描已上架 Skills，发现新威胁
3. **启用 LLM**：对高风险场景启用 LLM 深度分析
4. **关注 CVSS**：重点关注高 CVSS 评分的漏洞

## 注意事项

- 本工具仅用于安全检测目的
- 扫描结果仅供参考，实际安全状况需综合评估
- 建议结合人工代码审查
- LLM 分析需要配置 API 密钥（OpenAI/Anthropic/Ollama）

## 相关资源

- [Gitee 仓库](https://gitee.com/yzj1/skill-security-scanner)
- [CVSS 评分说明](https://gitee.com/yzj1/skill-security-scanner/blob/main/CVSS.md)
- [恶意 Skills 样本库](https://gitee.com/yzj1/skill-security-scanner/blob/main/docs/04-threat-intel/lobehub-malicious_skills.md)

---

**维护者**：Skill Security Scanner Team

**版本**：1.0.0
