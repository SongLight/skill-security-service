"""
LLM-based analyzer for deep security analysis.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from skill_scanner.core.types import Finding, Severity


class LLMAnalyzer:
    """LLM-based analyzer for semantic security analysis."""
    
    name = "LLMAnalyzer"
    category = "llm_analysis"
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url
        
    def scan_skill(self, skill_path: Path) -> List[Finding]:
        """Scan a skill using LLM analysis."""
        findings = []
        
        if not skill_path.exists():
            return findings
            
        if not self.api_key:
            return findings
            
        code_content = self._extract_code(skill_path)
        if not code_content:
            return findings
            
        analysis = self._analyze_with_llm(code_content, skill_path.name)
        
        for issue in analysis.get("issues", []):
            findings.append(Finding(
                severity=Severity[issue.get("severity", "MEDIUM")],
                detector=self.name,
                category=issue.get("category", "llm_analysis"),
                description=issue.get("description", ""),
                file_path=issue.get("file", ""),
                line_number=issue.get("line", 1),
                confidence=issue.get("confidence", 80),
                remediation=issue.get("remediation", ""),
            ))
            
        return findings
    
    def _extract_code(self, skill_path: Path) -> str:
        """Extract code content from skill directory."""
        content_parts = []
        
        for file_path in skill_path.rglob("*"):
            if file_path.is_file() and self._should_include(file_path):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    rel_path = file_path.relative_to(skill_path)
                    content_parts.append(f"\n# File: {rel_path}\n{content}\n")
                except Exception:
                    pass
                    
        return "\n".join(content_parts[:50])
    
    def _should_include(self, file_path: Path) -> bool:
        """Check if file should be included in analysis."""
        skip_patterns = {".git", "__pycache__", ".venv", "node_modules", "dist", "build"}
        if any(part in skip_patterns for part in file_path.parts):
            return False
            
        ext = file_path.suffix.lower()
        return ext in {".py", ".js", ".ts", ".sh", ".bash", ".zsh"}
    
    def _analyze_with_llm(self, code: str, skill_name: str) -> Dict[str, Any]:
        """Analyze code using LLM."""
        prompt = self._build_prompt(code, skill_name)
        
        try:
            if self.provider == "openai":
                return self._call_openai(prompt)
            elif self.provider == "anthropic":
                return self._call_anthropic(prompt)
            elif self.provider == "ollama":
                return self._call_ollama(prompt)
            else:
                return {"issues": []}
        except Exception as e:
            return {"issues": [], "error": str(e)}
    
    def _build_prompt(self, code: str, skill_name: str) -> str:
        """Build analysis prompt for LLM."""
        return f"""You are a security expert analyzing AI Agent skills for malicious patterns.

Analyze the following skill code for security vulnerabilities. Focus on:
1. Credential theft or secret exfiltration
2. Command injection vulnerabilities
3. Data exfiltration patterns
4. Persistence mechanisms
5. Privilege escalation attempts
6. Network suspicious connections
7. Obfuscated or encoded payloads
8. Supply chain vulnerabilities
9. Social engineering patterns

Skill name: {skill_name}

Code to analyze:
```
{code[:15000]}
```

Respond with a JSON array of issues found. Each issue should have:
- "severity": CRITICAL, HIGH, MEDIUM, or LOW
- "category": one of: credential_theft, command_injection, exfiltration, persistence, privilege_escalation, network, obfuscation, supply_chain, social_engineering, other
- "description": brief description of the issue
- "file": relative file path (if known)
- "line": line number (if known)
- "confidence": 0-100 confidence score
- "remediation": suggested fix

If no issues found, return an empty array: []

JSON Response:"""

    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 4000,
        }
        
        url = self.base_url or "https://api.openai.com/v1/chat/completions"
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        content = response.json()["choices"][0]["message"]["content"]
        return self._parse_response(content)
    
    def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API."""
        import requests
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        
        data = {
            "model": self.model,
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        url = "https://api.anthropic.com/v1/messages"
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        content = response.json()["content"][0]["text"]
        return self._parse_response(content)
    
    def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama local API."""
        import requests
        
        url = (self.base_url or "http://localhost:11434") + "/api/generate"
        
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        
        response = requests.post(url, json=data, timeout=120)
        response.raise_for_status()
        
        content = response.json()["response"]
        return self._parse_response(content)
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response to extract issues."""
        try:
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                issues = json.loads(json_match.group())
                return {"issues": issues}
        except json.JSONDecodeError:
            pass
            
        return {"issues": []}


def create_llm_analyzer(
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMAnalyzer:
    """Factory function to create LLM analyzer."""
    
    default_models = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "ollama": "llama3.1",
    }
    
    model = model or default_models.get(provider, "gpt-4o")
    
    return LLMAnalyzer(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
