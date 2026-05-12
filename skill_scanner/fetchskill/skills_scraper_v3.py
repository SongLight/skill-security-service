#!/usr/bin/env python3
"""
skills.sh 爬虫 V3 - 纯标准库 + BeautifulSoup
无需 lxml
"""

import requests
import json
import time
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_URL = "https://skills.sh"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_page(url: str) -> list:
    """解析单个页面"""
    print(f"[GET] {url}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    skills = []
    
    # 查找所有链接
    for link in soup.find_all('a', href=True):
        href = link['href']
        # 匹配 /owner/repo/skill 格式
        if href.startswith('/'):
            parts = href.strip('/').split('/')
            # 过滤掉系统路径
            if len(parts) == 3 and parts[0] not in [
                'topic', 'agent', 'api', 'docs', 'about', 'contact',
                'privacy', 'terms', 'sitemap', 'search', 'official',
                'trending', 'hot', 'audits'
            ]:
                owner, repo, skill_name = parts
                # 提取显示文本
                text = link.get_text(strip=True)
                if text and len(text) < 100:  # 过滤掉长文本
                    skills.append({
                        "id": f"{owner}/{repo}/{skill_name}",
                        "owner": owner,
                        "repo": repo,
                        "skill_name": skill_name,
                        "display_name": text,
                        "url": urljoin(BASE_URL, href)
                    })
    
    return skills


def crawl_all_skills() -> list:
    """爬取所有 skills"""
    all_skills = []
    
    # 要爬取的页面
    pages = [
        "/",
        "/trending",
        "/hot", 
        "/official",
    ]
    
    # 翻页获取
    for page in pages:
        for page_num in range(5):  # 每页最多5页
            url = f"{BASE_URL}{page}" if page_num == 0 else f"{BASE_URL}{page}?page={page_num}"
            try:
                skills = parse_page(url)
                if not skills:
                    break
                all_skills.extend(skills)
                print(f"  获取到 {len(skills)} 个 skills")
                time.sleep(0.5)
            except Exception as e:
                print(f"[ERROR] {url}: {e}")
                break
    
    # 去重
    seen = set()
    unique = []
    for s in all_skills:
        if s['id'] not in seen:
            seen.add(s['id'])
            unique.append(s)
    
    return unique


def main():
    print("=" * 60)
    print("skills.sh 爬虫 V3")
    print("=" * 60)
    
    skills = crawl_all_skills()
    
    print(f"\n[TOTAL] 共 {len(skills)} 个 unique skills")
    
    # 保存
    with open("skills_data.json", "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)
    
    print("[SAVE] 已保存到 skills_data.json")
    
    # 预览
    print("\n[PREVIEW] 前 10 个:")
    for s in skills[:10]:
        print(f"  {s['id']}")


if __name__ == "__main__":
    main()
