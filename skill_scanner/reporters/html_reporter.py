"""
HTML报告生成器 - 生成可视化的安全扫描报告
"""
import json
from typing import Dict
from .base import BaseReporter


class HTMLReporter(BaseReporter):
    """生成交互式HTML报告"""
    
    def get_extension(self) -> str:
        return "html"
    
    def generate(self, results_data: Dict = None) -> str:
        """生成HTML报告"""
        if results_data:
            self.results = results_data
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Scanner - Skills安全扫描报告</title>
    <style>
        :root {{
            --critical: #991b1b;
            --high: #9a3412;
            --medium: #854d0e;
            --low: #166534;
            --safe: #14532d;
            --bg: #1a1a1a;
            --card: #242424;
            --text: #e5e5e5;
            --text-muted: #888888;
            --border: #333333;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: var(--card);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .meta {{
            color: var(--text-muted);
            font-size: 14px;
            margin-bottom: 20px;
        }}
        
        /* Header 图例说明 */
        .header-legend {{
            display: flex;
            align-items: center;
            gap: 24px;
            padding-top: 15px;
            border-top: 1px solid var(--border);
            font-size: 13px;
        }}
        
        .header-legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            color: #888888;
        }}
        
        .header-legend-icon {{
            font-size: 14px;
        }}
        
        .header-legend-code {{
            font-family: 'Consolas', 'Monaco', monospace;
            background: #1a1a1a;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid #333333;
            font-size: 11px;
            color: #d4d4d4;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .stat-card {{
            background: var(--card);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-value.critical {{ color: var(--critical); }}
        .stat-value.high {{ color: var(--high); }}
        .stat-value.medium {{ color: var(--medium); }}
        .stat-value.low {{ color: var(--low); }}
        
        /* 总问题数卡片样式 - 深灰色 */
        .stat-card.total {{
            background: linear-gradient(135deg, #3a3a3a 0%, #2d2d2d 100%);
            color: #e5e5e5;
        }}
        
        .stat-card.total .stat-value {{
            color: #e5e5e5;
        }}
        
        .stat-card.total .stat-label {{
            color: #888888;
        }}
        
        .stat-label {{
            color: var(--text-muted);
            font-size: 14px;
        }}
        
        .findings-section {{
            background: var(--card);
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .findings-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .filter-buttons {{
            display: flex;
            gap: 10px;
        }}
        
        .filter-btn {{
            padding: 6px 16px;
            border: 1px solid var(--border);
            background: #333333;
            color: var(--text);
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .filter-btn:hover {{
            background: #444444;
        }}
        
        .filter-btn.active {{
            background: #555555;
            color: white;
        }}
        
        /* Skill Section Styles */
        .skill-section {{
            margin-bottom: 30px;
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }}
        
        .skill-header {{
            background: linear-gradient(135deg, #333333 0%, #2a2a2a 100%);
            color: #e5e5e5;
            padding: 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s;
            border-bottom: 1px solid var(--border);
        }}
        
        .skill-header:hover {{
            background: linear-gradient(135deg, #3a3a3a 0%, #323232 100%);
        }}
        
        .skill-name {{
            font-size: 18px;
            font-weight: 600;
        }}
        
        .skill-stats {{
            display: flex;
            gap: 15px;
            align-items: center;
        }}
        
        .skill-count {{
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            white-space: nowrap;
        }}
        
        .skill-sev-summary {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            white-space: nowrap;
        }}
        
        .sev-item {{
            display: flex;
            align-items: center;
            gap: 3px;
        }}
        
        .sev-name {{
            opacity: 0.9;
        }}
        
        .sev-num {{
            font-weight: 700;
            opacity: 1;
        }}
        
        .sev-dot {{
            opacity: 0.5;
            margin: 0 4px;
        }}
        
        .skill-toggle {{
            font-size: 20px;
            transition: transform 0.3s;
        }}
        
        .skill-toggle.collapsed {{
            transform: rotate(-90deg);
        }}
        
        .skill-content {{
            padding: 20px;
            background: var(--bg);
        }}
        
        .skill-content.collapsed {{
            display: none;
        }}
        
        .finding-item {{
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.2s;
        }}
        
        .finding-item:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .finding-item.critical {{ border-left: 4px solid var(--critical); }}
        .finding-item.high {{ border-left: 4px solid var(--high); }}
        .finding-item.medium {{ border-left: 4px solid var(--medium); }}
        .finding-item.low {{ border-left: 4px solid var(--low); }}
        
        /* 安全 Skill 消息 - 深色主题 */
        .safe-message {{
            text-align: center;
            padding: 30px;
            color: #22c55e;
        }}
        
        .safe-icon {{
            font-size: 36px;
            margin-bottom: 8px;
        }}
        
        .safe-text {{
            font-size: 14px;
            color: #888888;
        }}
        
        /* 发现项样式 */
        .finding-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }}
        
        .finding-num {{
            color: var(--text-muted);
            font-size: 13px;
            min-width: 30px;
        }}
        
        .finding-title {{
            font-weight: 600;
            font-size: 15px;
            flex: 1;
        }}
        
        .severity-badge {{
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .severity-badge.critical {{ background: #fee2e2; color: var(--critical); }}
        .severity-badge.high {{ background: #ffedd5; color: var(--high); }}
        .severity-badge.medium {{ background: #fef9c3; color: var(--medium); }}
        .severity-badge.low {{ background: #dcfce7; color: var(--low); }}
        
        .finding-location {{
            color: var(--text-muted);
            font-size: 12px;
            margin-bottom: 8px;
            padding-left: 40px;
        }}
        
        .finding-desc {{
            font-size: 14px;
            color: var(--text);
            line-height: 1.5;
            padding-left: 40px;
        }}
        
        .finding-description {{
            margin-bottom: 10px;
        }}
        
        /* 美观的发现项卡片样式 */
        .finding-card {{
            background: var(--card);
            border-radius: 10px;
            border: 1px solid var(--border);
            overflow: hidden;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .finding-card-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: linear-gradient(135deg, #2a2a2a 0%, #323232 100%);
            border-bottom: 1px solid var(--border);
        }}
        
        .finding-badge {{
            width: 26px;
            height: 26px;
            background: #444444;
            color: #e5e5e5;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            flex-shrink: 0;
        }}
        
        .finding-detector {{
            flex: 1;
            font-weight: 600;
            font-size: 15px;
            color: #e5e5e5;
        }}
        
        .finding-level {{
            padding: 3px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            flex-shrink: 0;
        }}
        
        .finding-level.critical {{ background: #3d1f1f; color: #ef4444; }}
        .finding-level.high {{ background: #3d2416; color: #f97316; }}
        .finding-level.medium {{ background: #3d3116; color: #eab308; }}
        .finding-level.low {{ background: #163d25; color: #22c55e; }}
        
        .finding-card-body {{
            padding: 16px;
        }}
        
        .info-row {{
            display: flex;
            align-items: flex-start;
            gap: 10px;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        
        .info-row:last-child {{
            margin-bottom: 0;
        }}
        
        .info-icon {{
            flex-shrink: 0;
            font-size: 14px;
            margin-top: 2px;
        }}
        
        .info-text {{
            color: var(--text);
            word-break: break-all;
            line-height: 1.5;
        }}
        
        .code-box {{
            background: #1a1a1a;
            color: #d4d4d4;
            padding: 12px 16px;
            border-radius: 8px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            overflow-x: auto;
            margin-top: 10px;
            margin-left: 24px;
            border: 1px solid #333333;
        }}
        
        .code-block {{
            background: #1a1a1a;
            color: #d4d4d4;
            padding: 12px;
            border-radius: 6px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            overflow-x: auto;
            flex: 1;
            border: 1px solid #333333;
        }}
        
        .code-snippet {{
            background: #1a1a1a;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            overflow-x: auto;
            margin-top: 10px;
        }}
        
        .confidence-bar {{
            height: 4px;
            background: var(--border);
            border-radius: 2px;
            margin-top: 10px;
            overflow: hidden;
        }}
        
        .confidence-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--low), var(--medium), var(--high));
            border-radius: 2px;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }}
        
        .empty-state-icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔒 Code Scanner 安全扫描报告</h1>
            <p class="meta">
                扫描时间: {self._get_current_time()} | 
                扫描器: {self.scanner_info['name']} v{self.scanner_info['version']} | 
                Skills: {self.results.get('summary', {}).get('skills_scanned', 0)} 个 | 
                文件: {self.results.get('summary', {}).get('files_scanned', 0)} 个
            </p>
        </header>
        
        <div class="stats-grid">
            {self._generate_stats_cards()}
        </div>
        
        <div class="findings-section">
            <div class="findings-header">
                <h2>Skills风险扫描结果</h2>
                <div class="filter-buttons">
                    <button class="filter-btn active" onclick="filterFindings('all')">全部</button>
                    <button class="filter-btn" onclick="filterFindings('CRITICAL')">严重</button>
                    <button class="filter-btn" onclick="filterFindings('HIGH')">高危</button>
                    <button class="filter-btn" onclick="filterFindings('MEDIUM')">中危</button>
                    <button class="filter-btn" onclick="filterFindings('LOW')">低危</button>
                </div>
            </div>
            
            <div id="findings-list">
                {self._generate_findings_list()}
            </div>
        </div>
    </div>
    
    <script>
        function filterFindings(severity) {{
            const items = document.querySelectorAll('.finding-item');
            const buttons = document.querySelectorAll('.filter-btn');
            
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            items.forEach(item => {{
                if (severity === 'all' || item.dataset.severity === severity) {{
                    item.classList.remove('hidden');
                }} else {{
                    item.classList.add('hidden');
                }}
            }});
        }}
        
        function toggleSkill(skillId) {{
            const content = document.getElementById('skill-content-' + skillId);
            const toggle = document.getElementById('skill-toggle-' + skillId);
            
            if (content.classList.contains('collapsed')) {{
                content.classList.remove('collapsed');
                toggle.classList.remove('collapsed');
            }} else {{
                content.classList.add('collapsed');
                toggle.classList.add('collapsed');
            }}
        }}
    </script>
</body>
</html>"""
        return html
    
    def _generate_stats_cards(self) -> str:
        """生成统计卡片 - 只显示严重级别"""
        summary = self.results.get("summary", {})
        counts = summary.get("severity_counts", {})
        
        # 计算总问题数
        total = sum(counts.values())
        
        cards = []
        
        # 总问题数卡片
        cards.append(f"""
        <div class="stat-card total">
            <div class="stat-value">{total}</div>
            <div class="stat-label">总问题数</div>
        </div>
        """)
        
        # 各严重级别卡片
        severity_labels = {
            "CRITICAL": "严重",
            "HIGH": "高危",
            "MEDIUM": "中危",
            "LOW": "低危"
        }
        
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = counts.get(severity, 0)
            label = severity_labels.get(severity, severity)
            cards.append(f"""
            <div class="stat-card">
                <div class="stat-value {severity.lower()}">{count}</div>
                <div class="stat-label">{label}</div>
            </div>
            """)
        
        return "\n".join(cards)
    
    def _generate_findings_list(self) -> str:
        """生成发现列表 - 按 Skill 分组，简洁展示"""
        skills = self.results.get("skills", {})
        
        # 过滤掉 summary 相关的键
        skill_findings = {k: v for k, v in skills.items() if not k.endswith("_summary")}
        skill_summaries = {k.replace("_summary", ""): v for k, v in skills.items() if k.endswith("_summary")}
        
        if not skill_findings:
            return """
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <h3>未发现安全问题</h3>
                <p>本次扫描未发现任何安全威胁</p>
            </div>
            """
        
        # 按 skill 名称排序
        sorted_skills = sorted(skill_findings.items())
        
        # 严重级别中文映射
        severity_cn = {
            "CRITICAL": "严重",
            "HIGH": "高危", 
            "MEDIUM": "中危",
            "LOW": "低危"
        }
        
        # 检测器中文名称映射
        detector_cn = {
            "SecretsDetector": "敏感凭证检测",
            "DownloadExecDetector": "下载执行检测",
            "InjectionDetector": "代码注入检测",
            "CredentialTheftDetector": "凭证窃取检测",
            "PersistenceDetector": "持久化驻留检测",
            "PrivilegeEscalationDetector": "权限提升检测",
            "ExfiltrationDetector": "数据外传检测",
            "NetworkDetector": "网络请求检测",
            "ObfuscationDetector": "代码混淆检测",
            "Base64Detector": "Base64编码检测",
            "EntropyDetector": "熵值异常检测",
            "HiddenCharDetector": "隐藏字符检测",
            "SocialEngineeringDetector": "社会工程学检测",
            "IOCDetector": "威胁情报检测",
            "SupplyChainDetector": "供应链安全检测",
        }
        
        # 风险描述中文翻译
        description_cn = {
            "Hardcoded secret detected:": "检测到硬编码的敏感凭证：",
            "Download-and-execute pattern:": "检测到下载并执行的恶意行为：",
            "Code/command injection risk:": "检测到代码/命令注入风险：",
            "Credential theft technique:": "检测到凭证窃取技术：",
            "Persistence mechanism:": "检测到持久化驻留机制：",
            "Privilege escalation:": "检测到权限提升行为：",
            "Network call detected:": "检测到网络请求：",
            "Obfuscation technique:": "检测到代码混淆技术：",
            "Base64-encoded string": "检测到Base64编码字符串",
            "High entropy line": "检测到高熵值字符串（可能为加密载荷）",
            "Zero-width characters detected": "检测到零宽字符（潜在代码隐藏）",
            "Unicode bidirectional control characters": "检测到Unicode双向控制字符（特洛伊源码攻击）",
            "Social engineering keyword detected": "检测到社会工程学关键词",
            "Suspicious filename associated with social engineering": "检测到与社会工程学相关的可疑文件名",
            "Known malicious IP detected": "检测到已知恶意IP：",
            "Known malicious domain detected": "检测到已知恶意域名：",
            "Suspicious TLD detected in domain": "检测到可疑的顶级域名",
            "Malicious URL pattern detected": "检测到恶意URL模式：",
            "ZIP archive creation combined with upload capability": "检测到ZIP压缩包创建结合上传功能（可能数据外传）",
            "Recursive file enumeration of sensitive directories": "检测到敏感目录的递归文件枚举",
            "Access to sensitive directories combined with network upload capability": "检测到访问敏感目录结合网络上传功能",
            "npm lifecycle hook": "检测到npm生命周期钩子：",
            "Python setup.py custom command class": "检测到Python setup.py自定义命令类",
            "curl pipe to shell": "curl命令管道执行（高风险）",
            "wget pipe to shell": "wget命令管道执行（高风险）",
            "eval() with non-literal argument": "eval()使用非字面量参数",
            "exec() with non-literal argument": "exec()使用非字面量参数",
            "os.system() call": "os.system()调用",
            "subprocess with shell=True": "subprocess使用shell=True",
            "__import__ dynamic import": "__import__动态导入",
            "AWS Access Key ID": "AWS访问密钥ID",
            "GitHub Personal Access Token": "GitHub个人访问令牌",
            "API key/secret": "API密钥/密钥",
            "SSH private key access": "SSH私钥访问",
            "AWS credentials file access": "AWS凭证文件访问",
            "crontab modification": "crontab计划任务修改",
            "systemd service file creation": "systemd服务文件创建",
            "macOS launchd persistence": "macOS launchd持久化",
            "macOS launchctl loading": "macOS launchctl加载",
            "systemd service enablement": "systemd服务启用",
            "writing to shell profile file": "写入shell配置文件",
            "sudo invocation": "sudo调用",
            "Python requests library": "Python requests库",
            "curl command invocation": "curl命令调用",
            "wget command invocation": "wget命令调用",
            "Python socket usage": "Python socket使用",
            "npm postinstall hook": "npm postinstall钩子",
        }
        
        sections = []
        section_idx = 0
        for skill_name, findings in sorted_skills:
            summary = skill_summaries.get(skill_name, {})
            findings_count = summary.get("findings_count", len(findings))
            severity_counts = summary.get("severity_counts", {})
            
            # 跳过没有风险的 skill
            if findings_count == 0:
                continue
            
            skill_id = f"skill-{section_idx}"
            section_idx += 1
            
            # 生成严重性摘要，带间距（如：严重 3 · 高危 19 · 中危 3）
            sev_parts = []
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                count = severity_counts.get(sev, 0)
                if count > 0:
                    sev_parts.append(f"<span class='sev-item'><span class='sev-name'>{severity_cn[sev]}</span><span class='sev-num'>{count}</span></span>")
            
            sev_html = "<span class='sev-dot'>·</span>".join(sev_parts) if sev_parts else ""
            
            # Skill 头部
            header_html = f"""
            <div class="skill-header" onclick="toggleSkill('{skill_id}')">
                <div class="skill-name">📦 {skill_name}</div>
                <div class="skill-stats">
                    <span class="skill-sev-summary">{sev_html}</span>
                    <span class="skill-count">{findings_count}个问题</span>
                    <span class="skill-toggle" id="skill-toggle-{skill_id}">▼</span>
                </div>
            </div>
            """
            
            # 按严重级别排序
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            sorted_findings = sorted(
                findings,
                key=lambda x: severity_order.get(x.get("severity", "LOW"), 4)
            )
            
            finding_items = []
            for i, finding in enumerate(sorted_findings, 1):
                severity = finding.get("severity", "LOW")
                sev_label = severity_cn.get(severity, severity)
                detector = finding.get('detector', 'Unknown')
                file_path = finding.get('file_path', 'Unknown')
                line_num = finding.get('line_number', 0)
                description = finding.get('description', '')
                
                # 翻译描述为中文
                desc_translated = description
                for eng, cn in description_cn.items():
                    desc_translated = desc_translated.replace(eng, cn)
                
                line_content = finding.get('line_content', '')
                
                finding_items.append(f"""
                <div class="finding-item {severity.lower()}" data-severity="{severity}">
                    <div class="finding-card">
                        <div class="finding-card-header">
                            <span class="finding-badge">{i}</span>
                            <span class="finding-detector">{detector}</span>
                            <span class="finding-level {severity.lower()}">{sev_label}</span>
                        </div>
                        <div class="finding-card-body">
                            <!-- 📍 位置图标：表示风险所在的文件路径和行号 -->
                            <div class="info-row">
                                <span class="info-icon" title="风险位置">风险位置</span>
                                <span class="info-text">{file_path}:{line_num}</span>
                            </div>
                            <!-- ⚠️ 警告图标：表示检测到的风险问题描述 -->
                            <div class="info-row">
                                <span class="info-icon" title="风险描述">风险描述</span>
                                <span class="info-text">{desc_translated}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-icon" title="风险代码">风险代码</span>
                                <span class="info-text">{self._escape_html(line_content)}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """)
            
            content_html = f"""
            <div class="skill-content" id="skill-content-{skill_id}">
                {''.join(finding_items)}
            </div>
            """
            
            sections.append(f"""
            <div class="skill-section">
                {header_html}
                {content_html}
            </div>
            """)
        
        return "\n".join(sections)
    
    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))
