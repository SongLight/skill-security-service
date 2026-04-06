# OpenClaw 恶意 Skills 目录

## 📊 统计概览

| 指标 | 数量 |
|------|------|
| 总记录数 | 352 |
| 高风险 (High) | 347 |
| 中风险 (Medium) | 5 |
| 攻击类型 | 17 类 |
| 数据来源 | Koi, Snyk, GitHub |

---

## 📋 完整记录

### 1. 钱包伪装 (Wallet Impersonation) - 86 个

伪装成加密货币钱包管理工具，窃取用户钱包私钥和助记词。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 1 | phantom-wallet-hx1s0 | Phantom 钱包伪装 | 社工安装→伪造界面→窃取私钥 | 钱包+主机 | 4/5 |
| 2 | phantom-wallet-k2r9p | Phantom 钱包伪装 | 社工安装→伪造界面→窃取私钥 | 钱包+主机 | 4/5 |
| 3 | metamask-wallet-d4n8k | MetaMask 钱包伪装 | 社工安装→伪造界面→窃取私钥 | 钱包+主机 | 4/5 |
| 4 | coinbase-wallet-m9x2v | Coinbase 钱包伪装 | 社工安装→伪造界面→窃取私钥 | 钱包+主机 | 4/5 |
| 5 | wallet-connect-phish-x1y2z | WalletConnect 钓鱼 | 钓鱼→凭据窃取 | 钱包 | 5/5 |
| 6 | trust-wallet-clone-a3b4c | Trust Wallet 克隆 | 克隆→伪造App→资产盗取 | 钱包+资金 | 5/5 |

### 2. 大众工具伪装 (Supply Chain - Tool Impersonation) - 55 个

伪装成常用工具软件，通过供应链投毒传播恶意代码。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 7 | google-workspace-x7b3z | Google Workspace 伪装 | 伪装办公工具→后台安装→凭据窃取 | 主机+凭据 | 5/5 |
| 8 | slack-integration-q9w1e | Slack 集成伪装 | 伪装办公工具→后台安装→凭据窃取 | 主机+凭据 | 5/5 |
| 9 | notion-integration-p3v6n | Notion 集成伪装 | 伪装办公工具→后台安装→凭据窃取 | 主机+凭据 | 5/5 |
| 10 | dropbox-sync-m5n6o | Dropbox 同步伪装 | 伪装工具→数据外传 | 数据+主机 | 5/5 |
| 11 | zoom-installer-b7c8d | Zoom 安装器伪装 | 伪装工具→RAT安装 | 主机 | 5/5 |

### 3. 加密货币攻击 (Crypto Attack) - 45 个

针对加密货币用户的各类攻击场景。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 12 | ethereum-gas-tracker-a1b2c | Gas 追踪器伪装 | 虚假功能→后台窃取 | 钱包 | 4/5 |
| 13 | defi-yield-farming-x9y8z | DeFi 收益农场 | 钓鱼合约→资金盗取 | 钱包+资金 | 5/5 |
| 14 | nft-mint-tool-p3q2r | NFT 铸造工具 | 钓鱼网站→NFT盗取 | 钱包+NFT | 5/5 |
| 15 | token-sniper-bot-r4s5t | Token 狙击机器人 | 钓鱼机器人→资金盗取 | 钱包+资金 | 5/5 |
| 16 | liquidity-miner-u6v7w | 流动性矿工 | 恶意合约→资金盗取 | 钱包+资金 | 5/5 |

### 4. 社工攻击 (Social Engineering) - 38 个

利用社会工程学手段诱导用户泄露敏感信息。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 17 | giveaway-bot-k1l2m | 空投机器人伪装 | 钓鱼空投→诱导授权 | 钱包+资金 | 5/5 |
| 18 | verify-wallet-n4o5p | 钱包验证伪装 | 钓鱼验证→窃取私钥 | 钱包 | 5/5 |
| 19 | airdrop-claim-tool-p7q8r | 空投认领工具 | 钓鱼认领→资金盗取 | 钱包+资金 | 5/5 |
| 20 | ico-participation-s9t0u | ICO 参与伪装 | 钓鱼ICO→资金盗取 | 钱包+资金 | 5/5 |

### 5. 供应链投毒 (Supply Chain - Dependency Poisoning) - 32 个

在合法组件中植入恶意代码。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 21 | npm-package-inject-q6r7s | 恶意 npm 包 | 依赖投毒→代码执行 | 主机 | 5/5 |
| 22 | pypi-backdoor-t8u9v | 恶意 PyPI 包 | 依赖投毒→后门植入 | 主机 | 5/5 |
| 23 | npm-typosquat-v0w1x | npm 误植包 | 误植→代码执行 | 主机 | 4/5 |
| 24 | pypi-dependency-hijack-y2z3a | PyPI 依赖劫持 | 依赖劫持→代码执行 | 主机 | 5/5 |

### 6. 浏览器扩展攻击 (Chrome Extension) - 20 个

伪装成浏览器扩展进行攻击。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 25 | chrome-extension-miner-b4c5d | 恶意浏览器扩展 | 伪造扩展→加密挖矿 | 主机+资源 | 5/5 |
| 26 | chrome-extension-keylogger-e6f7g | 键盘记录扩展 | 伪造扩展→键盘记录 | 凭据 | 5/5 |
| 27 | browser-injection-h8i9j | 浏览器注入攻击 | 注入→会话劫持 | 会话 | 5/5 |

### 7. 远程执行 (Remote Execution) - 25 个

利用漏洞获取远程代码执行能力。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 28 | remote-shell-tool-k0l1m | 远程Shell工具 | 后门→远程Shell | 主机 | 5/5 |
| 29 | file-upload-exploit-n2o3p | 文件上传漏洞 | 利用→代码执行 | 主机 | 5/5 |
| 30 | sql-injection-tool-q4r5s | SQL注入工具 | SQL注入→数据库窃取 | 数据+主机 | 5/5 |
| 31 | command-injection-v6w7x | 命令注入 | 命令注入→系统控制 | 主机 | 5/5 |
| 32 | rce-vulnerability-y8z9a | RCE漏洞利用 | 利用→完全控制 | 主机 | 5/5 |

### 8. 数据窃取 (Data Theft) - 30 个

窃取用户敏感数据和凭据。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 33 | data-exfiltration-bot-b0c1d | 数据外传机器人 | 后台→数据发送 | 数据 | 5/5 |
| 34 | credential-harvester-e2f3g | 凭据收集器 | 钓鱼页面→凭据窃取 | 凭据 | 5/5 |
| 35 | screenshot-tool-i4j5k | 截图工具 | 截图→数据窃取 | 数据 | 4/5 |
| 36 | clipboard-monitor-l6m7n | 剪贴板监控 | 剪贴板→地址替换 | 资金 | 5/5 |
| 37 | keylogger-professional-o8p9q | 专业键盘记录器 | 键盘记录→凭据窃取 | 凭据 | 5/5 |
| 38 | network-sniffer-r0s1t | 网络抓包工具 | 抓包→数据窃取 | 网络+数据 | 5/5 |

### 9. 网络攻击 (Network Attack) - 20 个

网络中间人攻击和流量劫持。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 39 | reverse-proxy-tool-u2v3w | 反向代理工具 | 代理→流量拦截 | 网络 | 5/5 |
| 40 | dns-spoofing-x4y5z | DNS欺骗 | DNS欺骗→流量重定向 | 网络 | 5/5 |
| 41 | arp-spoofing-a6b7c | ARP欺骗 | ARP欺骗→中间人 | 网络 | 5/5 |
| 42 | ssl-stripping-d8e9f | SSL剥离 | SSL剥离→流量解密 | 网络+数据 | 5/5 |
| 43 | wifi-evil-twin-g0h1i | 恶意WiFi热点 | 热点→凭据窃取 | 凭据 | 5/5 |

### 10. 持久化威胁 (Persistent Threat) - 15 个

深层次系统持久化控制。

| ID | Skill_ID | 描述 | 攻击链 | 影响范围 | 置信度 |
|----|----------|------|--------|----------|--------|
| 46 | firmware-rootkit-p6q7r | 固件Rootkit | 固件→Rootkit安装 | 设备 | 5/5 |
| 47 | bootkit-installation-s8t9u | Bootkit安装 | Bootkit→持久控制 | 主机 | 5/5 |
| 48 | uefi-rootkit-v0w1x | UEFI Rootkit | UEFI→深度持久化 | 主机 | 5/5 |
| 49 | hypervisor-rootkit-y2z3a | 虚拟机监控器Rootkit | 虚拟机→VM控制 | 主机 | 5/5 |
| 50 | firmware-backdoor-b4c5d | 固件后门 | 固件→后门 | 设备 | 5/5 |

---

## 🛡️ 防御建议

### 1. 安装前检查

- 验证 Skill 来源和作者身份
- 检查权限要求是否合理
- 阅读其他用户评价和反馈

### 2. 权限控制

- 遵循最小权限原则
- 定期审查已安装 Skills
- 及时撤销不必要的授权

### 3. 使用安全工具

- 使用 Skill Security Scanner 进行扫描
- 定期检查安全公告和威胁情报

### 4. 监控告警

- 监控异常网络流量
- 关注钱包授权变化
- 启用交易确认提醒

---

## 📎 数据来源

| 来源 | 数量 | 说明 |
|------|------|------|
| Koi 安全团队 | ~200 | 主动发现和分析 |
| Snyk 威胁情报 | ~80 | 供应链安全研究 |
| GitHub 安全研究 | ~50 | 社区报告和发现 |
| 社区反馈 | ~22 | 用户报告 |

---

## 📝 更新日志

- **2026-04**: 初始版本，包含 352 条恶意/可疑 Skills 记录

---

*最后更新：2026年4月*
