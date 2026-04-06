# Skill Security Scanner 产品介绍

## 一、产品概述

Skill Security Scanner 是一款面向 AI Agent 智能插件（Skills）的专用静态安全扫描工具，专注于深度检测技能代码中的安全漏洞、恶意行为与风险模式，为 AI 智能体插件全生命周期提供安全审计与风险管控能力。

**核心定位：企业级、可独立部署的 Skills 代码安全扫描工具**

---

## 二、行业背景与产品意义

### 行业背景

随着 AI Agent（智能体）技术的快速发展，Skills（技能插件）作为 AI Agent 扩展能力的核心单元，正在被广泛使用。然而，Skills 在带来强大功能的同时，也引入了严重的安全风险。攻击者可以将恶意逻辑伪装成正常 Skills，通过供应链传播、提示注入、数据窃取、远程代码执行等方式攻击终端用户。

安全研究人员已发现大量恶意 Skills 实例：根据公开研究，截止2026年3月20日，LobeHub 平台存在 **不少于38 个**已标注的恶意 Skills（HuggingFace 16个 + AISA Group 22个），OpenClaw 生态中已收录 **352 条**恶意/可疑 Skills 记录。这些恶意 Skills 涵盖云端训练投毒、Web 测试注入、文档处理远程执行、系统信息外传、数据窃取、支付漏洞等多种攻击向量。

详见 [lobehub-malicious-skills.md](docs/04-threat-intel/lobehub-malicious-skills.md) 、[openclaw-malicious-skills-/](docs/04-threat-intel/openclaw-malicious-skills-/openclaw-risky-skills.md)和[agent-skill-malware.md](docs/04-threat-intel/agent-skill-malware/agent-skill-malware.md)，了解更多风险类型：供应链风险、提示注入风险、数据窃取风险、远程执行风险。

---

### 行业痛点

在 AI Agent 爆发初期，Skills 安全处于"裸奔"状态。虽然目前已有部分安全工具开始关注 Skills 安全问题，但存在以下痛点：

1. **评估体系缺失**：Skills 代码缺陷问题本质上偏向传统安全，但目前尚没有一款工具支持 CVSS 评分，导致 Skills 风险的评估缺乏科学性
2. **工具化局限**：目前市面上的 Skills 扫描工具多处于"小工具"阶段，不具备提供系统性能力支持的能力

---

### 技术路线

Skill Security Scanner 采用**多种扫描器（静态规则）+ LLM 语义分析 + CVSS 评分**的技术路线，具备：

- **零依赖**：无外部第三方依赖，支持离线独立部署
- **服务化**：支持 REST API，可融入企业安全体系
- **可私有化**：支持完全本地部署，数据不出网
- **可商业化**：提供完整的产品能力，支持企业级需求

---

## 三、产品核心功能

### 🔍 安全扫描（18 种风险检测能力）

| 特性 | 说明 |
|------|------|
| 多维度检测 | 支持 18 种已知风险类型的专业安全检测 |
| 零依赖运行 | 无外部第三方依赖，支持离线独立部署 |
| 高精度检测 | 支持 IOC 威胁情报匹配、灵活规则配置 |
| CVSS 3.1 评分 | 标准化的风险量化评估体系 |

### 🤖 LLM 深度语义分析（18+N 扩展检测能力）

| 特性 | 说明 |
|------|------|
| 多模型支持 | OpenAI、Anthropic Claude、Ollama 等 |
| 语义级威胁识别 | 通过代码意图深度理解，发现隐蔽威胁 |
| 本地部署 | 支持 Ollama 本地模型，数据安全可控 |
| 推荐模型 | 推荐北京模湖智能科技优先公司自有红队大模型，若无，优先选择 OpenAI 等模型 |

### 🌐 多种使用方式

| 方式 | 说明 |
|------|------|
| 命令行工具 | 快速上手，灵活集成 |
| Web 界面 | 交互式扫描，可视化报告 |
| REST API | 标准化接口，集成企业安全平台 |

---

## 四、与同类产品对比

### 竞品对比

| 特性 | Skill Security Scanner | openclaw-skill-vetter |
|------|------------------------|-----------------------|
| **平台依赖** | 无依赖，可独立部署 | 强绑定 OpenClaw |
| **检测器数量** | 18+ 完整检测器 | 规则简单，数量有限 |
| **风险评级** | CVSS 3.1 专业评分 | 缺乏体系化评级 |
| **产品形态** | 企业级服务化工具 | 小工具 |
| **部署方式** | REST API / 离线 / 私有化 | 依赖特定平台 |
| **报告能力** | 多格式完整报告 | 基础报告 |

### 四大优势

1. **通用性**：不限制 Agent 平台或框架，任何 Skills 都可以扫描
2. **专业性**：18+N 检测能力 + CVSS 3.1 评分，科学量化风险
3. **工程化**：REST API + 离线部署 + 多格式输出，具备企业级产品能力
4. **灵活性**：支持私有化部署，数据不出网，安全可控

---

## 五、许可模式

- **开源版本**：基础功能免费使用
- **LLM 分析**：需要配置 API 密钥（OpenAI/Anthropic/Ollama）
- **本地部署**：支持完全离线部署

---

## 六、获取支持

- 技术文档：参考本项目文档目录
- 部署指南：参考 [DEPLOY.md](../DEPLOY.md)
- 使用手册：参考 [MANUAL.md](../MANUAL.md)
- CVSS 评分：参考 [CVSS.md](../CVSS.md)
- 命令行帮助：`python -m skill_scanner --help`
- Web 界面：访问 http://localhost:9000

---

## 七、联系我们

- 伙伴：partner@aimohu.com
- 销售：sales@aimohu.com
- 市场：marketing@aimohu.com
- 官网：https://www.aimohu.com
