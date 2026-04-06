#!/usr/bin/env python3
"""
Skill discovery - Discovers and collects skill directories for scanning.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Constants
SKIP_DIRS = {
    "venv", "node_modules", ".git", "__pycache__", ".mypy_cache",
    ".tox", "dist", "build", ".egg-info", ".venv", "env"
}
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".zsh",
    ".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg",
    ".rb", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
    ".html", ".css", ".xml", ".svg", ".env", ".plist",
    ".ps1", ".bat", ".cmd", ".mjs", ".cjs", ".lua", ".php",
}
MAX_FILE_SIZE = 1_000_000  # 1 MB
MAX_FILES_PER_SKILL = 1000


class SkillDiscovery:
    """Discovers and collects skill directories for scanning."""

    def __init__(self):
        self.skill_dirs: List[Path] = []

    def discover(self) -> List[Dict[str, Any]]:
        """Discover all skills in standard locations."""
        home = Path.home()
        search_roots = [
            home / ".claude" / "skills",
            home / ".qoder" / "skills",
            home / ".openclaw" / "workspace" / "skills",
        ]

        # Check for extra directories from config
        for cfg_name in [".qoder/config.json", ".openclaw/openclaw.json"]:
            cfg_path = home / cfg_name
            if cfg_path.exists():
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    extra = cfg.get("skills", {}).get("load", {}).get("extraDirs", [])
                    for d in extra:
                        p = Path(os.path.expanduser(d))
                        if p.is_dir():
                            search_roots.append(p)
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass

        skills = []
        seen_paths = set()

        for root in search_roots:
            if not root.is_dir():
                continue
            for child in sorted(root.iterdir()):
                if child.is_dir() and child.resolve() not in seen_paths:
                    seen_paths.add(child.resolve())
                    files = self._collect_files(child)
                    skills.append({
                        "name": child.name,
                        "path": child,
                        "files": files,
                    })

        return skills

    def discover_single(self, path: str) -> List[Dict[str, Any]]:
        """Scan a single path as one skill."""
        p = Path(path).resolve()
        if not p.is_dir():
            print(f"[ERROR] Not a directory: {p}", file=sys.stderr)
            return []
        files = self._collect_files(p)
        return [{"name": p.name, "path": p, "files": files}]
    
    def discover_multiple(self, path: str) -> List[Dict[str, Any]]:
        """Discover multiple skill subdirectories in a given path."""
        p = Path(path).resolve()
        if not p.is_dir():
            print(f"[ERROR] Not a directory: {p}", file=sys.stderr)
            return []
        
        skills = []
        seen_paths = set()
        
        # Check immediate subdirectories
        for child in sorted(p.iterdir()):
            if child.is_dir() and child.name not in SKIP_DIRS:
                # Check if this subdirectory contains scannable files
                files = self._collect_files(child)
                if files:  # Only add if it has files
                    if child.resolve() not in seen_paths:
                        seen_paths.add(child.resolve())
                        skills.append({
                            "name": child.name,
                            "path": child,
                            "files": files,
                        })
        
        # If no subdirectories found, treat the parent as a single skill
        if not skills:
            files = self._collect_files(p)
            if files:
                skills.append({
                    "name": p.name,
                    "path": p,
                    "files": files,
                })
        
        return skills

    def _collect_files(self, root: Path) -> List[Path]:
        """Collect all scannable files in a directory."""
        files = []
        count = 0
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if count >= MAX_FILES_PER_SKILL:
                    return files
                fp = Path(dirpath) / fname
                if fp.suffix.lower() in TEXT_EXTENSIONS and fp.stat().st_size <= MAX_FILE_SIZE:
                    files.append(fp)
                    count += 1
        return files
