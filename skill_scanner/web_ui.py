#!/usr/bin/env python3
"""
Skill Security Scanner - Web UI Server
Provides an interactive web interface for scanning skills.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_from_directory

sys.path.insert(0, str(Path(__file__).parent.parent))

from skill_scanner.scanner import SkillScanner


app = Flask(__name__)

SCAN_HISTORY = []
SCAN_RESULTS_DIR = Path(__file__).parent / "reports"
SCAN_RESULTS_DIR.mkdir(exist_ok=True)


INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skill Security Scanner</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --critical: #dc2626;
            --high: #ea580c;
            --medium: #ca8a04;
            --low: #16a34a;
            --safe: #059669;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 24px;
        }
        
        /* Header */
        .header {
            text-align: center;
            margin-bottom: 48px;
            position: relative;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: -100px;
            left: 50%;
            transform: translateX(-50%);
            width: 600px;
            height: 200px;
            background: radial-gradient(ellipse, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
            pointer-events: none;
        }
        
        .header h1 {
            font-size: 48px;
            font-weight: 800;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 16px;
            letter-spacing: -1px;
        }
        
        .header .subtitle {
            color: #64748b;
            font-size: 18px;
            font-weight: 400;
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.6;
        }
        
        .header .badge {
            display: inline-block;
            margin-top: 20px;
            padding: 8px 20px;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            border-radius: 24px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        
        /* Cards */
        .card {
            background: var(--card);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 4px 12px rgba(0,0,0,0.03);
            border: 1px solid var(--border);
        }
        
        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .card-title svg {
            width: 22px;
            height: 22px;
            color: var(--primary);
        }
        
        /* Form Elements */
        .form-group {
            margin-bottom: 24px;
        }
        
        .form-group label {
            display: block;
            font-size: 15px;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 12px;
            letter-spacing: 0.3px;
        }
        
        .path-selector {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .path-selector select {
            flex: 1;
        }
        
        .path-selector input {
            flex: 2;
        }
        
        select, input[type="text"] {
            width: 100%;
            padding: 14px 16px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text);
            font-size: 14px;
            font-family: inherit;
            transition: all 0.2s;
        }
        
        select:focus, input[type="text"]:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
        
        .refresh-btn {
            padding: 14px 20px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
            white-space: nowrap;
        }
        
        .refresh-btn:hover {
            background: var(--border);
            color: var(--text);
        }
        
        /* Checkboxes */
        .checkbox-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
        }
        
        .scan-methods {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }
        
        .scan-methods-summary {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 20px;
            padding: 16px;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 12px;
            border: 1px solid #bae6fd;
        }
        
        .method-summary-card {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 16px;
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            flex: 1;
            min-width: 160px;
        }
        
        .method-summary-icon {
            font-size: 20px;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border-radius: 8px;
            color: white;
        }
        
        .method-summary-text {
            display: flex;
            flex-direction: column;
        }
        
        .method-summary-text strong {
            font-size: 13px;
            color: var(--text);
            font-weight: 600;
        }
        
        .method-summary-text span {
            font-size: 11px;
            color: var(--text-muted);
        }
        
        .method-summary-card .method-toggle {
            margin-right: 4px;
        }
        
        .method-summary-card .method-toggle .toggle-switch {
            width: 36px;
            height: 20px;
        }
        
        .method-summary-card .method-toggle .toggle-switch::after {
            width: 16px;
            height: 16px;
        }
        
        .method-summary-card .method-toggle input:checked + .toggle-switch {
            background: #6366f1;
        }
        
        .method-details {
            margin-top: 16px;
            margin-bottom: 16px;
        }
        
        .detail-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            margin-top: 12px;
        }
        
        .detail-header {
            font-weight: 600;
            font-size: 14px;
            color: var(--text);
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }
        
        .method-card.section-title {
            grid-column: 1 / -1;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            font-weight: 600;
            font-size: 14px;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .method-card.section-title .method-header {
            display: none;
        }
        
        .section-icon {
            font-size: 16px;
        }
        
        .method-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        .method-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #6366f1, #8b5cf6, #ec4899);
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .method-card:hover {
            transform: translateY(-4px);
            border-color: #6366f1;
            box-shadow: 0 12px 24px rgba(99, 102, 241, 0.15);
        }
        
        .method-card:hover::before {
            opacity: 1;
        }
        
        .method-icon {
            font-size: 22px;
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 12px;
        }
        
        .method-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }
        
        .method-toggle {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
            flex-shrink: 0;
        }
        
        .method-toggle input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .toggle-switch {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
            transition: 0.3s;
            border-radius: 24px;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .toggle-switch:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background: white;
            transition: 0.3s;
            border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .method-toggle input:checked + .toggle-switch {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
        }
        
        .method-toggle input:checked + .toggle-switch:before {
            transform: translateX(20px);
        }
        
        .method-info {
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;
        }
        
        .method-icon {
            font-size: 20px;
        }
        
        .method-name {
            font-weight: 600;
            font-size: 15px;
            color: #1e293b;
        }
        
        .method-desc {
            font-size: 13px;
            color: #64748b;
            margin-bottom: 12px;
            padding-left: 56px;
            line-height: 1.5;
        }
        
        .method-config-btn {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 16px;
            padding: 4px 8px;
            border-radius: 6px;
            transition: background 0.2s;
        }
        
        .method-config-btn:hover {
            background: var(--bg);
        }
        
        .method-desc {
            font-size: 13px;
            color: #666;
            margin-bottom: 12px;
            padding-left: 56px;
        }
        
        .method-config {
            display: none;
            padding: 16px;
            background: rgba(0, 0, 0, 0.02);
            border-radius: 8px;
            margin-left: 56px;
            margin-top: 12px;
        }
        
        .method-config.active {
            display: block;
        }
        
        .config-row {
            margin-bottom: 12px;
        }
        
        .config-row:last-child {
            margin-bottom: 0;
        }
        
        .config-row label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            color: #555;
            margin-bottom: 6px;
        }
        
        .config-row select,
        .config-row input[type="text"],
        .config-row input[type="password"],
        .config-row textarea {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 13px;
            background: white;
            color: var(--text);
        }
        
        .config-row textarea {
            min-height: 80px;
            font-family: monospace;
        }
        
        .checkbox-inline {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }
        
        .checkbox-inline label {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            cursor: pointer;
        }
        
        .switch-label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 13px;
        }
        
        .switch-label input {
            width: 16px;
            height: 16px;
            accent-color: var(--primary);
        }
        
        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 16px;
            background: var(--bg);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
        }
        
        .checkbox-item:hover {
            border-color: var(--border);
        }
        
        .checkbox-item input {
            width: 18px;
            height: 18px;
            accent-color: var(--primary);
        }
        
        .checkbox-item span {
            font-size: 14px;
            color: var(--text);
        }
        
        /* Buttons */
        .btn-scan {
            width: 100%;
            padding: 16px 32px;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        
        .btn-scan:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
        }
        
        .btn-scan:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Loading */
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            width: 48px;
            height: 48px;
            border: 3px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .loading p {
            color: var(--text-muted);
            font-size: 15px;
        }
        
        /* Results */
        .results-card {
            display: none;
        }
        
        .results-card.active {
            display: block;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .results-summary {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }
        
        @media (max-width: 768px) {
            .results-summary {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        .result-stat {
            background: var(--bg);
            padding: 24px 16px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid var(--border);
        }
        
        .result-stat .value {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        
        .result-stat .label {
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 500;
        }
        
        .result-stat.total .value { color: var(--text); }
        .result-stat.critical .value { color: var(--critical); }
        .result-stat.high .value { color: var(--high); }
        .result-stat.medium .value { color: var(--medium); }
        .result-stat.low .value { color: var(--low); }
        
        .result-actions {
            display: flex;
            gap: 12px;
            justify-content: center;
        }
        
        .btn-view {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 24px;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            border-radius: 10px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .btn-view:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        
        /* History */
        .history-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .history-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            background: var(--bg);
            border-radius: 12px;
            border: 1px solid var(--border);
            transition: all 0.2s;
        }
        
        .history-item:hover {
            border-color: var(--primary);
        }
        
        .history-info {
            flex: 1;
        }
        
        .history-info h3 {
            font-size: 15px;
            font-weight: 500;
            margin-bottom: 4px;
            color: var(--text);
        }
        
        .history-info .time {
            font-size: 13px;
            color: var(--text-muted);
        }
        
        .history-badges {
            display: flex;
            gap: 8px;
            margin-right: 16px;
        }
        
        .badge-sev {
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .badge-sev.critical { background: #fef2f2; color: var(--critical); }
        .badge-sev.high { background: #fff7ed; color: var(--high); }
        .badge-sev.medium { background: #fefce8; color: var(--medium); }
        .badge-sev.low { background: #f0fdf4; color: var(--low); }
        
        .empty-state {
            text-align: center;
            padding: 48px 24px;
            color: var(--text-muted);
        }
        
        .empty-state svg {
            width: 48px;
            height: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }
        
        .empty-state p {
            font-size: 15px;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 24px;
            color: var(--text-muted);
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🛡️ Skill Security Scanner</h1>
            <p class="subtitle">Skill Security Scanner 是一款面向 AI Agent 智能插件（Skills）的专用安全扫描工具。</p>
        </header>
        
        <div class="card">
            <h2 class="card-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                    <path d="M2 17l10 5 10-5"/>
                    <path d="M2 12l10 5 10-5"/>
                </svg>
                扫描配置
            </h2>
            
            <form id="scanForm">
                <div class="form-group">
                    <label>扫描路径</label>
                    <div class="path-selector">
                        <select id="scanPathSelect">
                            <option value="">选择 Skill 目录...</option>
                        </select>
                        <input type="text" id="scanPath" placeholder="或输入自定义路径">
                        <button type="button" class="refresh-btn" id="refreshPaths">🔄</button>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>扫描方法</label>
                    
                    <div class="scan-methods-summary">
                        <div class="method-summary-card">
                            <label class="method-toggle">
                                <input type="checkbox" id="enableCodeScan" checked onchange="toggleAllDetectors()">
                                <span class="toggle-switch"></span>
                            </label>
                            <span class="method-summary-icon">🔍</span>
                            <div class="method-summary-text">
                                <strong>代码扫描</strong>
                                <span>内置18种风险检测能力</span>
                            </div>
                        </div>
                        <div class="method-summary-card">
                            <label class="method-toggle">
                                <input type="checkbox" id="enableLlm" onchange="toggleMethodDetail('llmDetail')">
                                <span class="toggle-switch"></span>
                            </label>
                            <span class="method-summary-icon">🤖</span>
                            <div class="method-summary-text">
                                <strong>LLM深入分析</strong>
                                <span>大语言模型语义分析</span>
                            </div>
                        </div>
                        <div class="method-summary-card">
                            <label class="method-toggle">
                                <input type="checkbox" id="enablePermission" onchange="toggleMethodDetail('permissionDetail')">
                                <span class="toggle-switch"></span>
                            </label>
                            <span class="method-summary-icon">🔑</span>
                            <div class="method-summary-text">
                                <strong>权限分析</strong>
                                <span>文件权限、提权风险</span>
                            </div>
                        </div>
                        <div class="method-summary-card">
                            <label class="method-toggle">
                                <input type="checkbox" id="enableIoc" onchange="toggleMethodDetail('iocDetail')">
                                <span class="toggle-switch"></span>
                            </label>
                            <span class="method-summary-icon">🎯</span>
                            <div class="method-summary-text">
                                <strong>IOC威胁情报</strong>
                                <span>恶意IP/域名/哈希</span>
                            </div>
                        </div>
                        <div class="method-summary-card">
                            <label class="method-toggle">
                                <input type="checkbox" id="enableYara" onchange="toggleMethodDetail('yaraDetail')">
                                <span class="toggle-switch"></span>
                            </label>
                            <span class="method-summary-icon">📋</span>
                            <div class="method-summary-text">
                                <strong>YARA规则匹配</strong>
                                <span>自定义规则精准检测</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="method-details" id="llmDetail" style="display:none;">
                        <div class="detail-card">
                            <div class="detail-header">🤖 LLM 深度分析配置</div>
                            <div class="config-row">
                                <label>LLM 提供商</label>
                                <select id="llmProvider">
                                    <option value="openai">OpenAI (GPT-4o)</option>
                                    <option value="anthropic">Anthropic (Claude)</option>
                                    <option value="ollama">Ollama (本地)</option>
                                </select>
                            </div>
                            <div class="config-row">
                                <label>API Key</label>
                                <input type="password" id="llmApiKey" placeholder="留空使用环境变量">
                            </div>
                            <div class="config-row">
                                <label>模型名称</label>
                                <input type="text" id="llmModel" placeholder="如: gpt-4o, claude-3-5-sonnet">
                            </div>
                        </div>
                    </div>
                    
                    <div class="method-details" id="permissionDetail" style="display:none;">
                        <div class="detail-card">
                            <div class="detail-header">🔑 权限分析配置</div>
                            <div class="config-row">
                                <label>检测范围</label>
                                <div class="checkbox-inline">
                                    <label><input type="checkbox" id="permFile" checked> 文件权限</label>
                                    <label><input type="checkbox" id="permSudo" checked> Sudo滥用</label>
                                    <label><input type="checkbox" id="permOwner" checked> 所有者变更</label>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="method-details" id="iocDetail" style="display:none;">
                        <div class="detail-card">
                            <div class="detail-header">🎯 IOC 威胁情报配置</div>
                            <div class="config-row">
                                <label>数据源</label>
                                <div class="checkbox-inline">
                                    <label><input type="checkbox" id="iocEmerging" checked> 新兴威胁</label>
                                    <label><input type="checkbox" id="iocMalware" checked> 恶意软件库</label>
                                    <label><input type="checkbox" id="iocC2" checked> C2 服务器</label>
                                </div>
                            </div>
                            <div class="config-row">
                                <label>VirusTotal API</label>
                                <input type="password" id="vtApiKey" placeholder="VirusTotal API Key (可选)">
                            </div>
                        </div>
                    </div>
                    
                    <div class="method-details" id="yaraDetail" style="display:none;">
                        <div class="detail-card">
                            <div class="detail-header">📋 YARA 规则配置</div>
                            <div class="config-row">
                                <label>规则模式</label>
                                <select id="yaraMode">
                                    <option value="default">默认规则集</option>
                                    <option value="strict">严格模式</option>
                                    <option value="permissive">宽松模式</option>
                                </select>
                            </div>
                            <div class="config-row">
                                <label>自定义规则</label>
                                <textarea id="yaraRules" placeholder="在此输入自定义 YARA 规则..."></textarea>
                            </div>
                        </div>
                    </div>
                    
                </div>
                
                <div class="form-group">
                    <label>输出格式</label>
                    <select id="outputFormat">
                        <option value="html">📄 HTML 报告</option>
                        <option value="markdown">📝 Markdown 报告</option>
                        <option value="json">📊 JSON 数据</option>
                        <option value="text">📃 纯文本</option>
                    </select>
                </div>
                
                <button type="submit" class="btn-scan" id="scanBtn">
                    🚀 开始扫描
                </button>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>正在扫描，请稍候...</p>
            </div>
        </div>
        
        <div class="card results-card" id="resultsCard">
            <h2 class="card-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                扫描结果
            </h2>
            <div class="results-summary" id="resultsSummary"></div>
            <div class="result-actions">
                <a href="#" class="btn-view" id="viewReport" target="_blank">
                    📄 查看完整报告
                </a>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                </svg>
                扫描历史
            </h2>
            <div class="history-list" id="historyList">
                {% if history %}
                    {% for item in history %}
                    <div class="history-item">
                        <div class="history-info">
                            <h3>{{ item.path }}</h3>
                            <div class="time">{{ item.time }}</div>
                        </div>
                        <div class="history-badges">
                            {% if item.critical > 0 %}<span class="badge-sev critical">{{ item.critical }} 严重</span>{% endif %}
                            {% if item.high > 0 %}<span class="badge-sev high">{{ item.high }} 高危</span>{% endif %}
                            {% if item.medium > 0 %}<span class="badge-sev medium">{{ item.medium }} 中危</span>{% endif %}
                            {% if item.low > 0 %}<span class="badge-sev low">{{ item.low }} 低危</span>{% endif %}
                        </div>
                        <a href="/reports/{{ item.report_file }}" class="btn-view" target="_blank">查看</a>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="12" y1="18" x2="12" y2="12"/>
                            <line x1="9" y1="15" x2="15" y2="15"/>
                        </svg>
                        <p>暂无扫描记录</p>
                    </div>
                {% endif %}
            </div>
        </div>
        
        <footer class="footer">
            Skill Security Scanner © 2026 | AI Agent 安全扫描工具 
            公司：北京模湖智能科技有限公司
        </footer>
    </div>
    
    <script>
        function toggleMethodConfig(configId) {
            const config = document.getElementById(configId);
            config.classList.toggle('active');
        }
        
        function toggleMethodDetail(detailId) {
            const detail = document.getElementById(detailId);
            detail.style.display = detail.style.display === 'none' ? 'block' : 'none';
        }
        
        function toggleAllDetectors() {
            const enabled = document.getElementById('enableCodeScan').checked;
            const detectors = document.querySelectorAll('.scan-methods-summary .method-toggle input[type="checkbox"]');
            detectors.forEach(cb => {
                cb.checked = enabled;
            });
        }
        
        async function loadPaths() {
            try {
                const response = await fetch('/api/list-paths');
                const data = await response.json();
                const select = document.getElementById('scanPathSelect');
                select.innerHTML = '<option value="">选择 Skill 目录...</option>';
                data.paths.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.path;
                    opt.textContent = '📁 ' + p.name;
                    select.appendChild(opt);
                });
            } catch (err) {
                console.error('Failed to load paths:', err);
            }
        }
        
        document.getElementById('scanPathSelect').addEventListener('change', (e) => {
            if (e.target.value) {
                document.getElementById('scanPath').value = e.target.value;
            }
        });
        
        document.getElementById('refreshPaths').addEventListener('click', loadPaths);
        loadPaths();
        
        document.getElementById('scanForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const path = document.getElementById('scanPath').value;
            const format = document.getElementById('outputFormat').value;
            const useIoc = document.getElementById('enableIoc')?.checked ?? false;
            const useBehavioral = false;
            const useYara = document.getElementById('enableYara')?.checked ?? false;
            const usePermission = document.getElementById('enablePermission')?.checked ?? false;
            const useLlm = document.getElementById('enableLlm')?.checked ?? false;
            
            const llmProvider = document.getElementById('llmProvider')?.value || 'openai';
            const llmApiKey = document.getElementById('llmApiKey')?.value || null;
            const llmModel = document.getElementById('llmModel')?.value || null;
            const llmBaseUrl = document.getElementById('llmBaseUrl')?.value || null;
            
            const btn = document.getElementById('scanBtn');
            const loading = document.getElementById('loading');
            const resultsCard = document.getElementById('resultsCard');
            
            btn.disabled = true;
            btn.textContent = '⏳ 扫描中...';
            loading.classList.add('active');
            resultsCard.classList.remove('active');
            
            try {
                const response = await fetch('/api/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        path,
                        format,
                        use_ioc: useIoc,
                        use_behavioral: useBehavioral,
                        use_yara: useYara,
                        use_permission: usePermission,
                        use_llm: useLlm,
                        llm_provider: llmProvider,
                        llm_api_key: llmApiKey,
                        llm_model: llmModel,
                        llm_base_url: llmBaseUrl
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const summary = document.getElementById('resultsSummary');
                    summary.innerHTML = `
                        <div class="result-stat total">
                            <div class="value">${data.total}</div>
                            <div class="label">总问题数</div>
                        </div>
                        <div class="result-stat critical">
                            <div class="value">${data.critical}</div>
                            <div class="label">🔴 CRITICAL</div>
                        </div>
                        <div class="result-stat high">
                            <div class="value">${data.high}</div>
                            <div class="label">🟠 HIGH</div>
                        </div>
                        <div class="result-stat medium">
                            <div class="value">${data.medium}</div>
                            <div class="label">🟡 MEDIUM</div>
                        </div>
                        <div class="result-stat low">
                            <div class="value">${data.low}</div>
                            <div class="label">🔵 LOW</div>
                        </div>
                    `;
                    
                    document.getElementById('viewReport').href = '/reports/' + data.report_file;
                    resultsCard.classList.add('active');
                    
                    setTimeout(() => location.reload(), 2000);
                } else {
                    alert('扫描失败: ' + data.error);
                }
            } catch (err) {
                alert('请求失败: ' + err.message);
            }
            
            btn.disabled = false;
            btn.textContent = '🚀 开始扫描';
            loading.classList.remove('active');
        });
    </script>
</body>
</html>
"""


def get_history():
    history = []
    seen = set()
    for report in sorted(SCAN_RESULTS_DIR.glob("scan_report_*.*"), reverse=True):
        if report.suffix not in ['.html', '.markdown', '.json']:
            continue
        if report.name in seen:
            continue
        seen.add(report.name)
        
        ts = report.stem.replace('scan_report_', '')
        history.append({
            'path': ts,
            'time': datetime.fromtimestamp(report.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'report_file': report.name
        })
        
        if len(history) >= 10:
            break
    
    return history


@app.route('/')
def index():
    return render_template_string(INDEX_HTML, history=get_history())


@app.route('/reports/<path:filename>')
def serve_report(filename):
    return send_from_directory(SCAN_RESULTS_DIR, filename)


@app.route('/api/list-paths', methods=['GET'])
def list_paths():
    base_paths = [
        Path.home() / "skills",
        Path("/home/kali/skills"),
    ]
    
    found_paths = []
    seen = set()
    for base in base_paths:
        if base.exists():
            try:
                for item in base.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        if item.resolve() not in seen:
                            seen.add(item.resolve())
                            found_paths.append({
                                'name': item.name,
                                'path': str(item.resolve())
                            })
            except PermissionError:
                pass
    
    return jsonify({'paths': found_paths[:20]})


@app.route('/api/scan', methods=['POST'])
def scan():
    data = request.json
    
    path = data.get('path')
    format_type = data.get('format', 'html')
    use_ioc = data.get('use_ioc', False)
    use_behavioral = data.get('use_behavioral', False)
    use_yara = data.get('use_yara', False)
    use_permission = data.get('use_permission', False)
    use_llm = data.get('use_llm', False)
    llm_provider = data.get('llm_provider', 'openai')
    llm_api_key = data.get('llm_api_key')
    llm_model = data.get('llm_model')
    llm_base_url = data.get('llm_base_url')
    
    if not path:
        return jsonify({'success': False, 'error': 'Path is required'})
    
    scanner = SkillScanner(
        use_ioc=use_ioc,
        use_behavioral=use_behavioral,
        use_yara=use_yara,
        use_permission_analysis=use_permission,
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        verbose=False,
    )
    
    findings = scanner.scan(path)
    
    severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for f in findings:
        if f.severity.name in severity_counts:
            severity_counts[f.severity.name] += 1
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = format_type
    report_file = f'scan_report_{timestamp}.{ext}'
    report_path = SCAN_RESULTS_DIR / report_file
    
    if format_type == 'html':
        results_data = scanner._build_results_data(findings)
        from skill_scanner.reporters import HTMLReporter
        output = HTMLReporter().generate(results_data)
    elif format_type == 'markdown':
        results_data = scanner._build_results_data(findings)
        from skill_scanner.reporters import MarkdownReporter
        output = MarkdownReporter().generate(results_data)
    elif format_type == 'json':
        import json
        output = json.dumps([f.to_dict() for f in findings], indent=2)
    else:
        output = scanner.format_output(findings, 'text', group_by_skill=True)
    
    report_path.write_text(output, encoding='utf-8')
    
    return jsonify({
        'success': True,
        'total': sum(severity_counts.values()),
        'critical': severity_counts['CRITICAL'],
        'high': severity_counts['HIGH'],
        'medium': severity_counts['MEDIUM'],
        'low': severity_counts['LOW'],
        'report_file': report_file
    })


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Skill Security Scanner Web UI')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    args = parser.parse_args()
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🛡️  Skill Security Scanner Web UI                     ║
║                                                           ║
║   访问地址: http://{args.host}:{args.port}                       ║
║   报告目录: {SCAN_RESULTS_DIR}            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    app.run(host=args.host, port=args.port, debug=True)
