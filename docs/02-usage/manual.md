# Skill Security Scanner 使用手册

本手册提供 Skill Security Scanner 的详细使用指南，包括安装配置、命令行使用、Web 界面、API 接口等内容。

## 目录

- [安装部署](#安装部署)
- [命令行使用](#命令行使用)
- [Web 界面](#web-界面)
- [REST API](#rest-api)
- [配置说明](#配置说明)
- [高级功能](#高级功能)
- [使用示例](#使用示例)
- [故障排除](#故障排除)

---

## 安装部署

### 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux / macOS / Windows |
| Python | 3.9 或更高版本 |
| 内存 | 最少 4GB |
| 磁盘 | 最少 50MB |

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://gitee.com/yzj1/skill-security-scanner.git
cd skill-security-scanner
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 安装为可执行模块

```bash
pip install -e .
```

### 可选依赖

| 依赖 | 用途 | 安装命令 |
|------|------|----------|
| OpenAI | LLM 分析 | `pip install openai` |
| Anthropic | LLM 分析 | `pip install anthropic` |
| Ollama | 本地 LLM | `pip install ollama` |
| YARA | 规则匹配 | `pip install yara-python` |
| Flask | Web 界面 | `pip install flask` |

---

## 命令行使用

### 基本语法

```bash
python -m skill_scanner [选项]
```

### 必选选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `--path PATH` | 要扫描的技能目录路径 | `--path /home/kali/skills/my-skill` |

### 输出选项

| 选项 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--format FORMAT` | 输出格式 | `text` | `--format json` |
| `--output, -o OUTPUT` | 输出文件路径 | stdout | `-o report.html` |

**支持的格式**：
- `text` - 纯文本格式
- `json` - JSON 格式
- `html` - HTML 报告
- `markdown` - Markdown 格式
- `sarif` - SARIF 格式（用于 GitHub）

### 扫描选项

| 选项 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--severity SEVERITY` | 最低严重级别 | `low` | `--severity high` |
| `--group-by-skill` | 按技能分组结果 | True | `--group-by-skill` |
| `--verbose, -v` | 详细输出 | False | `-v` |
| `--timeout TIMEOUT` | 扫描超时（秒） | 300 | `--timeout 600` |

### 检测器选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `--use-ioc` | 启用 IOC 威胁情报检测 | `--use-ioc` |
| `--use-yara` | 启用 YARA 规则匹配 | `--use-yara` |
| `--use-behavioral` | 启用行为分析 | `--use-behavioral` |
| `--use-permission-analysis` | 启用权限分析 | `--use-permission-analysis` |
| `--use-llm` | 启用 LLM 深度分析 | `--use-llm` |

### LLM 配置选项

| 选项 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--llm-provider PROVIDER` | LLM 提供商 | `openai` | `--llm-provider anthropic` |
| `--llm-model MODEL` | 模型名称 | 提供商默认 | `--llm-model gpt-4o` |
| `--llm-api-key KEY` | API 密钥 | 环境变量 | `--llm-api-key sk-...` |
| `--llm-base-url URL` | 自定义 API 地址 | - | `--llm-base-url http://localhost:11434` |

### 帮助信息

查看所有选项：

```bash
python -m skill_scanner --help
```

输出：

```
usage: skill_scanner [-h] --path PATH [--format {text,json,html,sarif,markdown}]
                     [--output OUTPUT] [--severity {critical,high,medium,low}]
                     [--use-ioc] [--use-yara] [--use-behavioral]
                     [--use-permission-analysis] [--use-llm]
                     [--llm-provider {openai,anthropic,ollama}]
                     [--llm-model MODEL] [--llm-api-key KEY]
                     [--llm-base-url URL] [--group-by-skill]
                     [--verbose] [--timeout TIMEOUT]

Skill Security Scanner - AI Agent Skill 安全扫描工具

options:
  -h, --help            显示帮助信息
  --path PATH           要扫描的技能目录 (必填)
  --format FORMAT       输出格式: text, json, html, sarif, markdown
  --output OUTPUT       输出文件路径
  --severity SEVERITY   最低严重级别: critical, high, medium, low
  --use-ioc            启用 IOC 检测
  --use-yara           启用 YARA 规则
  --use-behavioral     启用行为分析
  --use-permission-analysis  启用权限分析
  --use-llm            启用 LLM 分析
  --llm-provider       LLM 提供商: openai, anthropic, ollama
  --llm-model          LLM 模型名称
  --llm-api-key        LLM API 密钥
  --llm-base-url       自定义 API 地址
  --group-by-skill     按技能分组
  --verbose, -v        详细输出
  --timeout TIMEOUT    超时时间(秒)
```

---

## Web 界面

### 启动 Web 界面

```bash
python -m skill_scanner.web_ui --port 9000
```

### 访问地址

- 本地访问：`http://localhost:9000`
- 网络访问：`http://0.0.0.0:9000` 或 `http://<your-ip>:9000`

### Web 界面功能

| 功能 | 说明 |
|------|------|
| 路径选择 | 自动检测并选择要扫描的技能目录 |
| 检测器配置 | 启用/禁用各个检测器，配置参数 |
| LLM 配置 | 选择 LLM 提供商，配置 API 密钥 |
| 实时扫描 | 显示扫描进度和状态 |
| 报告查看 | 在线查看扫描结果和报告 |
| 报告下载 | 下载 HTML/JSON 格式报告 |

### 配置选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--port PORT` | 监听端口 | `9000` |
| `--host HOST` | 监听地址 | `0.0.0.0` |
| `--reports-dir DIR` | 报告保存目录 | `skill_scanner/reports` |
| `--debug` | 调试模式 | False |

---

## REST API

### 启动 API 服务器

```bash
python -m skill_scanner.api_server --port 8080
```

### API 端点

#### POST /scan

扫描技能目录。

**请求**：

```bash
curl -X POST http://localhost:8080/scan \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/skill",
    "format": "json",
    "severity": "high"
  }'
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 要扫描的目录路径 |
| format | string | 否 | 输出格式: text, json, html, sarif, markdown |
| severity | string | 否 | 最低严重级别: critical, high, medium, low |
| use_llm | boolean | 否 | 是否启用 LLM 分析 |
| use_ioc | boolean | 否 | 是否启用 IOC 检测 |
| use_yara | boolean | 否 | 是否启用 YARA 规则 |

**响应**：

```json
{
  "success": true,
  "total": 5,
  "critical": 2,
  "high": 1,
  "medium": 1,
  "low": 1,
  "findings": [
    {
      "severity": "CRITICAL",
      "detector": "InjectionDetector",
      "category": "injection",
      "description": "检测到命令注入漏洞",
      "file_path": "utils/exec.py",
      "line_number": 89,
      "confidence": 95
    }
  ]
}
```

#### GET /health

健康检查。

```bash
curl http://localhost:8080/health
```

**响应**：

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### GET /detectors

获取支持的检测器列表。

```bash
curl http://localhost:8080/detectors
```

---

## 配置说明

### 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | `export OPENAI_API_KEY="sk-..."` |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | `export ANTHROPIC_API_KEY="sk-ant-..."` |
| `VIRUSTOTAL_API_KEY` | VirusTotal API 密钥 | `export VIRUSTOTAL_API_KEY="..."` |

### YARA 规则配置

创建自定义 YARA 规则目录：

```bash
mkdir -p ~/.skill-scanner/rules
```

将 `.yar` 规则文件放入该目录，扫描时会自动加载。

### 配置文件

支持 YAML 配置文件（可选）：

```yaml
# config.yaml
scanner:
  severity: high
  format: html
  timeout: 300

detectors:
  use_ioc: true
  use_yara: true

llm:
  provider: openai
  model: gpt-4o
```

使用配置文件：

```bash
python -m skill_scanner --path /path/to/skill --config config.yaml
```

---

## 高级功能

### LLM 深度分析

LLM 分析可发现传统静态分析难以识别的隐蔽威胁。

#### OpenAI

```bash
python -m skill_scanner \
  --path /path/to/skill \
  --use-llm \
  --llm-provider openai \
  --llm-model gpt-4o
```

#### Anthropic Claude

```bash
python -m skill_scanner \
  --path /path/to/skill \
  --use-llm \
  --llm-provider anthropic \
  --llm-model claude-3-5-sonnet
```

#### Ollama 本地模型

```bash
# 首先启动 Ollama
ollama serve

# 使用 Ollama 进行扫描
python -m skill_scanner \
  --path /path/to/skill \
  --use-llm \
  --llm-provider ollama \
  --llm-model llama3.1
```

### YARA 规则

创建自定义规则：

```yaml
# my_rules.yar
rule malicious_script
{
    meta:
        description = "Detects suspicious script patterns"
    strings:
        $a = /curl.*\|.*bash/
        $b = /wget.*-O-.*\|.*python/
    condition:
        any of them
}
```

使用自定义规则：

```bash
python -m skill_scanner \
  --path /path/to/skill \
  --use-yara \
  --yara-rules-path /path/to/my_rules.yar
```

### IOC 威胁情报

启用 IOC 检测需要配置 VirusTotal API：

```bash
export VIRUSTOTAL_API_KEY="your-api-key"

python -m skill_scanner \
  --path /path/to/skill \
  --use-ioc
```

---

## 使用示例

### 示例 1：基本安全扫描

```bash
python -m skill_scanner --path /home/kali/skills/my-skill
```

输出：
```
🛡️ Skill Security Scanner 报告
================================

📊 摘要: 3 个问题

🔴 严重 (1)
└── injection: 命令注入 in utils/exec.py:89

🟠 高危 (2)
├── secrets: 硬编码密钥 in config/settings.py:23
└── persistence: 持久化机制 in setup.py:45
```

### 示例 2：生成 HTML 报告

```bash
python -m skill_scanner \
  --path /home/kali/skills/my-skill \
  --format html \
  -o security-report.html
```

### 示例 3：过滤高危以上问题

```bash
python -m skill_scanner \
  --path /home/kali/skills/my-skill \
  --severity high
```

### 示例 4：启用所有检测器

```bash
python -m skill_scanner \
  --path /home/kali/skills/my-skill \
  --use-ioc \
  --use-yara \
  --use-llm \
  --format html \
  -o full-report.html
```

### 示例 5：CI/CD 集成

```bash
# 在 CI 脚本中
python -m skill_scanner \
  --path ./skill \
  --format sarif \
  --severity high \
  -o results.sarif

# 如果有严重问题则退出
if [ $? -ne 0 ]; then
  echo "安全扫描发现高危问题！"
  exit 1
fi
```

### 示例 6：批量扫描

```bash
#!/bin/bash

REPORTS_DIR="./reports"
mkdir -p $REPORTS_DIR

for dir in /home/kali/skills/*/; do
  skill_name=$(basename "$dir")
  echo "扫描: $skill_name"
  
  python -m skill_scanner \
    --path "$dir" \
    --format json \
    -o "$REPORTS_DIR/${skill_name}.json"
done

echo "批量扫描完成！"
```

### 示例 7：Python API 调用

```python
import requests
import json

def scan_skill(path, severity="high", use_llm=False):
    response = requests.post(
        "http://localhost:8080/scan",
        json={
            "path": path,
            "format": "json",
            "severity": severity,
            "use_llm": use_llm
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"总问题数: {result['total']}")
        print(f"严重: {result['critical']}")
        print(f"高危: {result['high']}")
        
        return result
    else:
        print(f"扫描失败: {response.text}")
        return None

# 使用
result = scan_skill("/path/to/skill", severity="high", use_llm=True)
```

---

## 故障排除

### 常见问题

#### Q: 扫描很慢怎么办？

A: 
1. 减少扫描范围，使用 `--severity` 过滤低危问题
2. 禁用不需要的检测器
3. 减少 LLM 分析的文件数量
4. 增加超时时间 `--timeout`

#### Q: LLM 调用失败

A:
1. 检查 API 密钥是否正确配置
2. 确认网络连接正常
3. 尝试使用本地 Ollama 模型
4. 查看详细错误信息添加 `-v` 参数

#### Q: IOC 检测失败

A:
1. 确认已配置 VirusTotal API 密钥
2. 检查网络连接
3. API 可能有速率限制

#### Q: Web 界面无法访问

A:
1. 确认端口未被占用：`lsof -i :9000`
2. 检查防火墙设置
3. 尝试使用 `127.0.0.1` 而非 `0.0.0.0`

#### Q: YARA 规则不生效

A:
1. 确认规则文件格式正确
2. 检查规则文件路径
3. 使用 `-v` 查看详细日志

### 获取帮助

| 方式 | 命令/地址 |
|------|-----------|
| 命令行帮助 | `python -m skill_scanner --help` |
| Web 界面 | http://localhost:9000 |
| API 健康检查 | http://localhost:8080/health |
| 问题反馈 | GitHub Issues |

---

## 附录

### 检测器完整列表

| 检测器 | 风险等级 | 说明 |
|--------|----------|------|
| SecretsDetector | CRITICAL | 硬编码密钥、密码、Token |
| DownloadExecDetector | CRITICAL | 下载并执行恶意代码 |
| InjectionDetector | CRITICAL | 代码/命令注入 |
| IOCDetector | CRITICAL | 已知恶意指标 |
| CredentialTheftDetector | HIGH | 凭证盗取 |
| PersistenceDetector | HIGH | 持久化后门 |
| ObfuscationDetector | HIGH | 代码混淆 |
| ExfiltrationDetector | HIGH | 数据外传 |
| SupplyChainDetector | HIGH | 供应链风险 |
| PrivilegeEscalationDetector | HIGH | 权限提升 |
| SocialEngineeringDetector | HIGH | 社会工程学 |
| Base64Detector | MEDIUM | Base64 编码 |
| NetworkDetector | MEDIUM | 异常网络行为 |
| EntropyDetector | MEDIUM | 高熵值字符串 |
| HiddenCharDetector | LOW | 隐藏字符 |

### 输出格式对比

| 格式 | 用途 | 特点 |
|------|------|------|
| text | 终端显示 | 人类可读，彩色输出 |
| json | 程序处理 | 结构化，便于解析 |
| html | 报告展示 | 图表丰富，交互性强 |
| sarif | CI/CD 集成 | 标准化，兼容 GitHub |
| markdown | 文档嵌入 | GitHub 友好 |
