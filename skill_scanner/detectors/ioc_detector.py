#!/usr/bin/env python3
"""
IOC detector - Detects patterns matching threat intelligence.
"""

import re
from typing import List

from .base import BaseDetector
from skill_scanner.core.types import Finding, Severity


class IOCDetector(BaseDetector):
    """Detects patterns matching threat intelligence (IPs, domains, URLs)."""
    name = "IOCDetector"
    category = "threat_intelligence"
    
    _ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    _domain_pattern = re.compile(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b')
    _url_pattern = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)

    def __init__(self, ioc_database=None):
        super().__init__()
        self.ioc_db = ioc_database

    def scan_file(self, content: str, file_path: str) -> List[Finding]:
        findings = []
        if not self.ioc_db:
            return findings
            
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            # Check IPs
            for ip_match in self._ip_pattern.finditer(line):
                ip = ip_match.group()
                if self.ioc_db.is_malicious_ip(ip):
                    findings.append(Finding(
                        detector=self.name,
                        severity=Severity.CRITICAL,
                        category=self.category,
                        file_path=file_path,
                        line_number=i,
                        line_content=line.strip()[:200],
                        description=f"Known malicious IP detected: {ip} - {self.ioc_db.get_description('ip', ip)}",
                        confidence=self.ioc_db.get_confidence('ip', ip),
                    ))
            
            # Check domains
            for domain_match in self._domain_pattern.finditer(line):
                domain = domain_match.group()
                if self.ioc_db.is_malicious_domain(domain):
                    findings.append(Finding(
                        detector=self.name,
                        severity=Severity.CRITICAL,
                        category=self.category,
                        file_path=file_path,
                        line_number=i,
                        line_content=line.strip()[:200],
                        description=f"Known malicious domain detected: {domain} - {self.ioc_db.get_description('domain', domain)}",
                        confidence=self.ioc_db.get_confidence('domain', domain),
                    ))
                elif self.ioc_db.is_suspicious_tld(domain):
                    findings.append(Finding(
                        detector=self.name,
                        severity=Severity.MEDIUM,
                        category=self.category,
                        file_path=file_path,
                        line_number=i,
                        line_content=line.strip()[:200],
                        description=f"Suspicious TLD detected in domain: {domain}",
                        confidence=40,
                    ))
            
            # Check URLs
            for url_match in self._url_pattern.finditer(line):
                url = url_match.group()
                if self.ioc_db.is_malicious_url(url):
                    findings.append(Finding(
                        detector=self.name,
                        severity=Severity.CRITICAL,
                        category=self.category,
                        file_path=file_path,
                        line_number=i,
                        line_content=line.strip()[:200],
                        description=f"Malicious URL pattern detected: {url[:50]}...",
                        confidence=85,
                    ))
        
        return findings
