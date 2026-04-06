# README - Test Skills

这些是用于测试 code-scanner 的测试技能集合。

## 测试技能列表

### 1. Clean Skill (`clean-skill/`)
- **用途**: 测试误报率
- **风险等级**: ✅ 无风险
- **特点**: 
  - 完全安全的代码
  - 无任何权限需求
  - 仅包含数学计算和字符串处理

**预期扫描结果**: 0 个发现

```bash
python3 scanner.py --path test-skills/clean-skill --use-permission-analysis
```

---

### 2. Vulnerable Dependencies (`vulnerable-deps/`)
- **用途**: 测试依赖链扫描
- **风险等级**: 🔴 CRITICAL
- **特点**:
  - 包含已知漏洞的依赖包
  - 包含恶意 typosquatting 包
  - 包含恶意的 postinstall 脚本

**预期扫描结果**:
- 6 CRITICAL (恶意包、下载执行)
- 1 HIGH (CVE 漏洞)
- 多个 MEDIUM (typosquatting 警告)

```bash
python3 scanner.py --path test-skills/vulnerable-deps --use-dependency --dep-check-license
```

---

### 3. Permission Overreach (`permission-overreach/`)
- **用途**: 测试权限越界检测
- **风险等级**: 🔴 CRITICAL
- **特点**:
  - 声明有限的权限（只读文件、HTTP 请求）
  - 实际使用更多未声明的权限
  - 包含 socket 监听、shell 命令等高危操作
  - 环境变量访问

**预期扫描结果**:
- 1 CRITICAL (下载执行模式)
- 2 HIGH (命令注入)
- 3 MEDIUM (网络调用)
- 5+ 权限越界发现（需启用 `--use-permission-analysis`）

```bash
# 基础扫描
python3 scanner.py --path test-skills/permission-overreach

# 启用权限分析（推荐）
python3 scanner.py --path test-skills/permission-overreach --use-permission-analysis
```

**典型输出**:
```
📋 Permission Analysis Report
============================================================
Declared Permissions: 2
Inferred from Code: 6
Overreach Detected: 5

✅ Declared Permissions:
   • file_system.read
   • network.http_request

💻 Actual Usage:
   ⚠️ file_system.write
   ✓ network.http_request
   ⚠️ network.listen
   ⚠️ network.socket
   ⚠️ system.environment
   ⚠️ system.shell_command
```

---

### 4. High Risk Malicious (`high-risk-malicious/`)
- **用途**: 测试高危恶意代码检测
- **风险等级**: 🔴 CRITICAL
- **特点**:
  - 硬编码密钥（AWS、GitHub、Stripe）
  - 下载执行恶意载荷
  - 命令注入漏洞
  - 数据渗出
  - 持久化机制
  - 零宽字符隐藏后门

**预期扫描结果**:
- 10+ CRITICAL 发现
- 5+ HIGH 发现
- 多个 MEDIUM 发现

```bash
python3 scanner.py --path test-skills/high-risk-malicious
```

---

### 5. Medium Risk (`medium-risk/`)
- **用途**: 测试中等风险检测
- **风险等级**: 🟡 MEDIUM
- **特点**:
  - 部分权限已声明
  - 存在未声明的中等风险操作
  - 文件写入、环境变量访问、数据库连接

**预期扫描结果**:
- 4 权限越界发现
- 严重级别：MEDIUM

```bash
python3 scanner.py --path test-skills/medium-risk --use-permission-analysis
```

---

## 批量测试所有技能

```bash
# 全功能扫描所有测试技能
python3 scanner.py --path test-skills \
    --use-ioc \
    --use-behavioral \
    --use-yara \
    --use-dependency \
    --dep-check-license \
    --use-permission-analysis \
    --format text
```

## 测试场景矩阵

| 技能 | Secrets | DownloadExec | Injection | PermissionOverreach | VulnerableDeps | 总风险 |
|------|---------|--------------|-----------|---------------------|----------------|--------|
| clean-skill | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ 安全 |
| vulnerable-deps | ❌ | ✅ | ❌ | ❌ | ✅ | 🔴 Critical |
| permission-overreach | ❌ | ❌ | ❌ | ✅ | ❌ | 🔴 Critical |
| high-risk-malicious | ✅ | ✅ | ✅ | ✅ | ❌ | 🔴 Critical |
| medium-risk | ❌ | ❌ | ❌ | ✅ | ❌ | 🟡 Medium |

## 性能基准测试

```bash
# 测试扫描速度
time python3 scanner.py --path test-skills --format json --output results.json
```

## 注意事项

⚠️ **重要**: 
- `high-risk-malicious` 包含真实恶意代码模式，**切勿执行**！
- 仅用于测试扫描器检测能力
- 在隔离环境中运行测试
