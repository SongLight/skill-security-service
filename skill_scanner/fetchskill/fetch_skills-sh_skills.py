import argparse
import hashlib
import json
import multiprocessing as mp
import os
import queue
import re
import signal
import tempfile
import time
import threading
import traceback
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote, unquote, urljoin, urlparse

import requests
import yaml


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _now_local() -> datetime:
    return datetime.now().astimezone()

def _fmt_time(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

def _maxrss_kb() -> Optional[int]:
    try:
        import resource  # type: ignore

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:
        return None


def _safe_relpath(rel_path: str) -> Optional[str]:
    p = PurePosixPath(rel_path.replace("\\", "/"))
    if p.is_absolute():
        return None
    parts: List[str] = []
    for part in p.parts:
        if part in ("", "."):
            continue
        if part == "..":
            return None
        parts.append(part)
    return "/".join(parts)

def _is_http_404(e: Exception) -> bool:
    resp = getattr(e, "response", None)
    status = getattr(resp, "status_code", None)
    return status == 404


def _is_skill_dir_missing(e: Exception) -> bool:
    if not isinstance(e, RuntimeError):
        return False
    msg = str(e)
    return "skill directory not found in repo archive" in msg


def _artifact_status_for_error(e: Exception) -> str:
    if _is_skill_dir_missing(e):
        return "missing"
    if _is_http_404(e):
        return "not_found"
    return "error"


@dataclass(frozen=True)
class PgConfig:
    dsn: str


class Pg:
    def __init__(self, cfg: PgConfig):
        try:
            import psycopg2  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Missing PostgreSQL driver. Install: pip install psycopg2-binary"
            ) from e

        self._cfg = cfg
        self._psycopg2 = psycopg2
        self._conn = self._connect()

    def _connect(self):
        conn = self._psycopg2.connect(
            self._cfg.dsn,
            connect_timeout=15,
            application_name="skills_sh_crawler",
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=3,
        )
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'Asia/Shanghai'")
            cur.execute("SET statement_timeout = '120s'")
            cur.execute("SET lock_timeout = '15s'")
            cur.execute("SET idle_in_transaction_session_timeout = '300s'")
        return conn

    def _reconnect(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = self._connect()

    def _is_retryable_db_error(self, e: Exception) -> bool:
        return isinstance(
            e,
            (
                self._psycopg2.OperationalError,
                self._psycopg2.InterfaceError,
            ),
        )

    def _with_retry(self, fn, *, op: str):
        last_exc: Optional[Exception] = None
        for attempt in range(2):
            try:
                return fn()
            except Exception as e:
                last_exc = e
                if not self._is_retryable_db_error(e) or attempt >= 1:
                    raise
                print(
                    _json_dumps(
                        {
                            "event": "pg_retry",
                            "op": op,
                            "attempt": attempt + 1,
                            "error": f"{type(e).__name__}: {e}",
                            "at": _fmt_time(_now_local()),
                        }
                    ),
                    flush=True,
                )
                time.sleep(1.0)
                self._reconnect()
        if last_exc:
            raise last_exc

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            return

    def commit(self) -> None:
        self._with_retry(lambda: self._conn.commit(), op="commit")

    def rollback(self) -> None:
        try:
            self._conn.rollback()
        except Exception:
            try:
                self._reconnect()
            except Exception:
                return

    def execute(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, params)

        self._with_retry(_run, op="execute")

    def fetchall(
        self, sql: str, params: Optional[Tuple[Any, ...]] = None
    ) -> List[Tuple[Any, ...]]:
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

        return self._with_retry(_run, op="fetchall")

    def upsert_skill(
        self,
        *,
        skill_uid: str,
        owner: str,
        repo: str,
        skill_id: str,
        skills_sh_url: str,
        github_url: str,
        install_command: str,
        description: Optional[str],
        installs: Optional[int],
        agent_trust_hub_status: Optional[str],
        agent_trust_hub_url: Optional[str],
        socket_status: Optional[str],
        socket_url: Optional[str],
        snyk_status: Optional[str],
        snyk_url: Optional[str],
    ) -> None:
        sql = """
        INSERT INTO skills_sh_skill (
          skill_uid,
          owner,
          repo,
          skill_id,
          skills_sh_url,
          github_url,
          install_command,
          description,
          installs,
          agent_trust_hub_status,
          agent_trust_hub_url,
          socket_status,
          socket_url,
          snyk_status,
          snyk_url,
          fetched_at,
          last_error
        ) VALUES (
          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL
        )
        ON CONFLICT (skill_uid) DO UPDATE SET
          owner = EXCLUDED.owner,
          repo = EXCLUDED.repo,
          skill_id = EXCLUDED.skill_id,
          skills_sh_url = EXCLUDED.skills_sh_url,
          github_url = EXCLUDED.github_url,
          install_command = EXCLUDED.install_command,
          description = EXCLUDED.description,
          installs = EXCLUDED.installs,
          agent_trust_hub_status = EXCLUDED.agent_trust_hub_status,
          agent_trust_hub_url = EXCLUDED.agent_trust_hub_url,
          socket_status = EXCLUDED.socket_status,
          socket_url = EXCLUDED.socket_url,
          snyk_status = EXCLUDED.snyk_status,
          snyk_url = EXCLUDED.snyk_url,
          fetched_at = EXCLUDED.fetched_at,
          last_error = NULL
        """
        self.execute(
            sql,
            (
                skill_uid,
                owner,
                repo,
                skill_id,
                skills_sh_url,
                github_url,
                install_command,
                description,
                installs,
                agent_trust_hub_status,
                agent_trust_hub_url,
                socket_status,
                socket_url,
                snyk_status,
                snyk_url,
                _now_local(),
            ),
        )

    def mark_skill_error(self, *, skill_uid: str, error: str) -> None:
        sql = """
        UPDATE skills_sh_skill
        SET last_error = %s, fetched_at = %s
        WHERE skill_uid = %s
        """
        self.execute(sql, (error, _now_local(), skill_uid))

    def ensure_artifact_row(self, *, skill_uid: str) -> None:
        sql = """
        INSERT INTO skills_sh_skill_artifact (
          skill_uid,
          status,
          created_at,
          updated_at
        ) VALUES (
          %s,'pending',%s,%s
        )
        ON CONFLICT (skill_uid) DO NOTHING
        """
        now = _now_local()
        self.execute(sql, (skill_uid, now, now))

    def mark_artifact_skipped(self, *, skill_uid: str) -> None:
        sql = """
        UPDATE skills_sh_skill_artifact
        SET status='skipped', updated_at=%s, last_error=NULL
        WHERE skill_uid=%s
        """
        self.execute(sql, (_now_local(), skill_uid))

    def update_artifact_uploaded(
        self,
        *,
        skill_uid: str,
        oss_bucket: str,
        oss_prefix: str,
        source_zip_url: str,
        source_zip_sha256: str,
        source_zip_size_bytes: int,
        source_skill_sha256: str,
        downloaded_at: datetime,
        files_count: int,
    ) -> None:
        sql = """
        UPDATE skills_sh_skill_artifact
        SET status='uploaded',
            oss_bucket=%s,
            oss_prefix=%s,
            source_zip_url=%s,
            source_zip_sha256=%s,
            source_zip_size_bytes=%s,
            source_skill_sha256=%s,
            downloaded_at=%s,
            files_count=%s,
            uploaded_at=%s,
            updated_at=%s,
            last_error=NULL
        WHERE skill_uid=%s
        """
        now = _now_local()
        self.execute(
            sql,
            (
                oss_bucket,
                oss_prefix,
                source_zip_url,
                source_zip_sha256,
                source_zip_size_bytes,
                source_skill_sha256,
                downloaded_at,
                files_count,
                now,
                now,
                skill_uid,
            ),
        )

    def mark_artifact_error(self, *, skill_uid: str, error: str) -> None:
        sql = """
        UPDATE skills_sh_skill_artifact
        SET status='error', updated_at=%s, last_error=%s
        WHERE skill_uid=%s
        """
        self.execute(sql, (_now_local(), error, skill_uid))

    def mark_artifact_status(self, *, skill_uid: str, status: str, error: Optional[str]) -> None:
        sql = """
        UPDATE skills_sh_skill_artifact
        SET status=%s, updated_at=%s, last_error=%s
        WHERE skill_uid=%s
        """
        self.execute(sql, (status, _now_local(), error, skill_uid))

    def get_artifact_status_map(self, *, skill_uids: Sequence[str]) -> Dict[str, Optional[str]]:
        if not skill_uids:
            return {}
        sql = """
        SELECT skill_uid, status
        FROM skills_sh_skill_artifact
        WHERE skill_uid = ANY(%s)
        """
        rows = self.fetchall(sql, (list(skill_uids),))
        out: Dict[str, Optional[str]] = {str(r[0]): (str(r[1]) if r[1] is not None else None) for r in rows}
        return out


@dataclass(frozen=True)
class OssConfig:
    region: str
    endpoint: str
    bucket: str


class OssUploader:
    def __init__(self, cfg: OssConfig):
        try:
            import alibabacloud_oss_v2 as oss  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Missing OSS SDK. Install: pip install alibabacloud-oss-v2"
            ) from e

        credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()
        oss_cfg = oss.config.load_default()
        oss_cfg.credentials_provider = credentials_provider
        oss_cfg.region = cfg.region
        oss_cfg.endpoint = cfg.endpoint
        self.bucket = cfg.bucket
        self._oss = oss
        self._client = oss.Client(oss_cfg)
        self._cfg = cfg

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            return

    def object_prefix_for_skill(self, *, owner: str, repo: str, skill_id: str) -> str:
        safe_skill = quote_path_segment(skill_id)
        return f"skills.sh/{owner}/{repo}/{safe_skill}"

    def put_file(self, key: str, file_path: str) -> None:
        with open(file_path, "rb") as body:
            req = self._oss.PutObjectRequest(
                bucket=self.bucket,
                key=key,
                body=body,
            )
            self._client.put_object(req)


def quote_path_segment(seg: str) -> str:
    from urllib.parse import quote

    return quote(seg, safe="")


class SkillsShClient:
    def __init__(
        self,
        *,
        timeout: int = 15,
        zip_read_timeout_s: int = 40,
        max_attempts: int = 2,
        max_backoff_s: float = 5.0,
        skills_api_key: Optional[str] = None,
    ):
        self._timeout = timeout
        self._zip_read_timeout_s = zip_read_timeout_s
        self._max_attempts = max(1, int(max_attempts))
        self._max_backoff_s = max(0.0, float(max_backoff_s))
        self._skills_api_key = (skills_api_key.strip() if skills_api_key else None) or None
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "skill-security-service/skills.sh-crawler",
                "Accept": "*/*",
            }
        )

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:
            return

    def _request_with_backoff(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[object] = None,
        stream: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        backoff = 1.0
        last_exc: Optional[Exception] = None
        for _ in range(self._max_attempts):
            try:
                r = self._session.request(
                    method,
                    url,
                    params=params,
                    timeout=self._timeout if timeout is None else timeout,
                    stream=stream,
                    headers=headers,
                )
                if r.status_code in (429, 502, 503, 504):
                    try:
                        r.close()
                    except Exception:
                        pass
                    if r.status_code == 429:
                        try:
                            ra = r.headers.get("retry-after")
                            if ra:
                                time.sleep(min(float(ra), self._max_backoff_s))
                                continue
                        except Exception:
                            pass
                    time.sleep(backoff)
                    backoff = min(backoff * 2.0, self._max_backoff_s)
                    continue
                if 400 <= r.status_code < 500 and r.status_code != 429:
                    r.raise_for_status()
                r.raise_for_status()
                return r
            except Exception as e:
                last_exc = e
                resp = getattr(e, "response", None)
                status = getattr(resp, "status_code", None)
                if isinstance(status, int) and 400 <= status < 500 and status != 429:
                    raise
                time.sleep(backoff)
                backoff = min(backoff * 2.0, self._max_backoff_s)
        if last_exc:
            raise last_exc
        raise RuntimeError("request failed")

    def fetch_sitemap_urls(self) -> List[str]:
        import xml.etree.ElementTree as ET

        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        def _parse_urlset(xml_text: str) -> List[str]:
            root = ET.fromstring(xml_text)
            urls: List[str] = []
            for loc in root.findall("sm:url/sm:loc", ns):
                if loc.text:
                    urls.append(loc.text.strip())
            return urls

        def _parse_sitemap_index(xml_text: str) -> List[str]:
            root = ET.fromstring(xml_text)
            locs: List[str] = []
            for loc in root.findall("sm:sitemap/sm:loc", ns):
                if loc.text:
                    locs.append(loc.text.strip())
            return locs

        r = self._request_with_backoff("GET", "https://skills.sh/sitemap.xml")
        xml_text = r.text
        try:
            root = ET.fromstring(xml_text)
        except Exception as e:
            raise RuntimeError(f"failed to parse sitemap.xml: {type(e).__name__}: {e}") from e

        root_tag = (root.tag.split("}")[-1] if "}" in root.tag else root.tag).lower()
        sitemap_urls: List[str] = []
        if root_tag == "sitemapindex":
            for u in _parse_sitemap_index(xml_text):
                if "sitemap-skills" in u:
                    sitemap_urls.append(u)
        elif root_tag == "urlset":
            return _parse_urlset(xml_text)
        else:
            raise RuntimeError(f"unsupported sitemap root tag: {root_tag}")

        all_urls: List[str] = []
        for su in sitemap_urls:
            rr = self._request_with_backoff("GET", su)
            all_urls.extend(_parse_urlset(rr.text))
        return all_urls

    def fetch_leaderboard_page(self, *, view: str, page: int) -> Dict[str, Any]:
        r = self._request_with_backoff("GET", f"https://skills.sh/api/skills/{view}/{page}")
        return r.json()

    def fetch_official_skills_page(
        self, *, view: str, page: int, per_page: int
    ) -> Dict[str, Any]:
        if not self._skills_api_key:
            raise RuntimeError(
                "missing skills.sh API key for /api/v1. Provide --skills-api-key or set SKILLS_SH_API_KEY."
            )
        headers = {"Authorization": f"Bearer {self._skills_api_key}"}
        params: Dict[str, Any] = {"page": int(page), "per_page": int(per_page)}
        if view and str(view) != "all-time":
            params["view"] = view
        r = self._request_with_backoff(
            "GET",
            "https://skills.sh/api/v1/skills",
            params=params,
            headers=headers,
        )
        return r.json()

    def search_skill(self, *, q: str, limit: int = 20) -> Dict[str, Any]:
        r = self._request_with_backoff(
            "GET", "https://skills.sh/api/search", params={"q": q, "limit": limit}
        )
        return r.json()

    def fetch_skill_page_html(self, skills_sh_url: str) -> str:
        r = self._request_with_backoff("GET", skills_sh_url)
        return r.text

    def download_github_raw(
        self, *, owner: str, repo: str, branch: str, path: str
    ) -> Optional[str]:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        try:
            r = self._session.get(url, timeout=self._timeout)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.text
        except Exception:
            return None

    def download_github_repo_zip(
        self, *, owner: str, repo: str, branch: str, dest_path: str
    ) -> Tuple[str, str, int]:
        urls = [
            f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip",
            f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}",
        ]
        last_exc: Optional[Exception] = None
        for url in urls:
            try:
                r = self._request_with_backoff(
                    "GET",
                    url,
                    timeout=(10, self._zip_read_timeout_s),
                    stream=True,
                )
                h = hashlib.sha256()
                size = 0
                try:
                    with open(dest_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if not chunk:
                                continue
                            f.write(chunk)
                            h.update(chunk)
                            size += len(chunk)
                finally:
                    try:
                        r.close()
                    except Exception:
                        pass
                return url, h.hexdigest(), size
            except Exception as e:
                last_exc = e
                continue
        raise last_exc or RuntimeError("failed to download repo zip")


@dataclass(frozen=True)
class SkillRef:
    owner: str
    repo: str
    skill_id: str
    skills_sh_url: str
    installs: Optional[int] = None

    @property
    def source(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def skill_uid(self) -> str:
        return f"{self.owner}/{self.repo}/{self.skill_id}"

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"

    @property
    def install_command(self) -> str:
        return f"npx skills add {self.github_url} --skill {self.skill_id}"


def _parse_skill_refs_from_urls(urls: Sequence[str]) -> List[SkillRef]:
    out: List[SkillRef] = []
    for u in urls:
        try:
            parsed = urlparse(u)
            if parsed.netloc != "skills.sh":
                continue
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) != 3:
                continue
            owner, repo, skill_id = parts
            out.append(
                SkillRef(
                    owner=owner,
                    repo=repo,
                    skill_id=skill_id,
                    skills_sh_url=f"https://skills.sh/{owner}/{repo}/{skill_id}",
                    installs=None,
                )
            )
        except Exception:
            continue
    return out


def _parse_skill_refs_from_leaderboard(
    payload: Dict[str, Any], *, max_add: Optional[int]
) -> Tuple[List[SkillRef], Optional[int], bool, int]:
    out: List[SkillRef] = []
    total = payload.get("total")
    try:
        total = int(total) if total is not None else None
    except Exception:
        total = None

    has_more = bool(payload.get("hasMore"))
    items = payload.get("skills") or []
    skipped_non_github = 0
    for item in items:
        if max_add is not None and len(out) >= max_add:
            break
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        skill_id = item.get("skillId")
        if not source or not skill_id:
            continue
        if not isinstance(source, str) or not isinstance(skill_id, str):
            continue
        parts = [p for p in source.split("/") if p]
        if len(parts) != 2:
            skipped_non_github += 1
            continue
        owner, repo = parts
        installs = item.get("installs")
        try:
            installs = int(installs) if installs is not None else None
        except Exception:
            installs = None
        out.append(
            SkillRef(
                owner=owner,
                repo=repo,
                skill_id=skill_id,
                skills_sh_url=f"https://skills.sh/{owner}/{repo}/{quote(skill_id, safe='')}",
                installs=installs,
            )
        )
    return out, total, has_more, skipped_non_github


def _parse_skill_refs_from_official_api(
    payload: Dict[str, Any], *, max_add: Optional[int]
) -> Tuple[List[SkillRef], Optional[int], bool]:
    out: List[SkillRef] = []
    items = payload.get("skills") or []
    if not isinstance(items, list):
        items = []

    pagination = payload.get("pagination") or {}
    total: Optional[int] = None
    page: Optional[int] = None
    per_page: Optional[int] = None
    try:
        if isinstance(pagination, dict):
            total = pagination.get("total")
            page = pagination.get("page")
            per_page = pagination.get("perPage") or pagination.get("per_page")
        total = int(total) if total is not None else None
    except Exception:
        total = None
    try:
        page = int(page) if page is not None else None
    except Exception:
        page = None
    try:
        per_page = int(per_page) if per_page is not None else None
    except Exception:
        per_page = None

    has_more: bool
    if isinstance(total, int) and isinstance(page, int) and isinstance(per_page, int) and per_page > 0:
        has_more = (page + 1) * per_page < total
    else:
        has_more = False

    for item in items:
        if max_add is not None and len(out) >= max_add:
            break
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        skill_id = item.get("skillId") or item.get("skill_id") or item.get("skill")
        if not source or not skill_id:
            continue
        if not isinstance(source, str) or not isinstance(skill_id, str):
            continue
        parts = [p for p in source.split("/") if p]
        if len(parts) != 2:
            continue
        owner, repo = parts
        installs = item.get("installs")
        try:
            installs = int(installs) if installs is not None else None
        except Exception:
            installs = None
        out.append(
            SkillRef(
                owner=owner,
                repo=repo,
                skill_id=skill_id,
                skills_sh_url=f"https://skills.sh/{owner}/{repo}/{quote(skill_id, safe='')}",
                installs=installs,
            )
        )

    return out, total, has_more


def _merge_skill_refs(*lists: Sequence[SkillRef]) -> List[SkillRef]:
    out: List[SkillRef] = []
    seen: set[str] = set()
    for lst in lists:
        for sr in lst:
            uid = sr.skill_uid
            if uid in seen:
                continue
            seen.add(uid)
            out.append(sr)
    return out


def _parse_front_matter(md_text: str) -> Tuple[Optional[str], Optional[str]]:
    if not md_text.startswith("---"):
        return None, None
    parts = md_text.split("\n", 1)
    if len(parts) != 2:
        return None, None
    rest = parts[1]
    end = rest.find("\n---")
    if end < 0:
        return None, None
    fm_text = rest[:end]
    try:
        obj = yaml.safe_load(fm_text) or {}
        name = obj.get("name")
        desc = obj.get("description")
        return (str(name) if name is not None else None, str(desc) if desc else None)
    except Exception:
        return None, None


def _parse_security_status(
    html: str, *, skill_ref: SkillRef, typ: str
) -> Tuple[Optional[str], Optional[str]]:
    m = re.search(
        rf'<a[^>]+href="([^"]*?/security/{re.escape(typ)})"[^>]*>([\s\S]*?)</a>',
        html,
        flags=re.IGNORECASE,
    )
    if not m:
        return None, None
    href = m.group(1)
    body = m.group(2) or ""
    tokens = re.findall(r"\b(pass|warn|fail)\b", body, flags=re.IGNORECASE)
    if not tokens:
        return None, urljoin(skill_ref.skills_sh_url, href)
    status = tokens[-1].upper()
    return status, urljoin(skill_ref.skills_sh_url, href)


def _select_search_match(payload: Dict[str, Any], *, skill_ref: SkillRef) -> Optional[int]:
    expected_id = f"{skill_ref.source}/{skill_ref.skill_id}"
    skills = payload.get("skills") or []
    for item in skills:
        if not isinstance(item, dict):
            continue
        if item.get("id") == expected_id:
            installs = item.get("installs")
            return int(installs) if installs is not None else None
    return None


def _skill_id_variants(skill_id: str) -> List[str]:
    raw = str(skill_id)
    decoded = unquote(raw)
    out: List[str] = [raw]
    if decoded and decoded != raw:
        out.append(decoded)
    if decoded and "/" in decoded:
        last = decoded.split("/")[-1]
        if last and last not in out:
            out.append(last)
    return out


def _extract_zip_safe(zip_path: str, dest_dir: str) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            safe = _safe_relpath(info.filename)
            if not safe:
                continue
            out_path = os.path.join(dest_dir, safe)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with zf.open(info, "r") as src, open(out_path, "wb") as dst:
                dst.write(src.read())


def _find_skill_dir(repo_root_dir: str, *, skill_id: str) -> Optional[str]:
    candidates: List[str] = []
    for v in _skill_id_variants(skill_id):
        parts = [p for p in v.split("/") if p]
        if not parts:
            continue
        candidates.extend(
            [
                os.path.join(repo_root_dir, "skills", *parts),
                os.path.join(repo_root_dir, *parts),
                os.path.join(repo_root_dir, "skill", *parts),
                os.path.join(repo_root_dir, ".skills", *parts),
            ]
        )
    for c in candidates:
        if os.path.isdir(c):
            return c

    wanted_files = {"SKILL.md", "skill.md", "Skill.md"}
    for root, dirs, files in os.walk(repo_root_dir):
        base = os.path.basename(root)
        if any(f in wanted_files for f in files):
            for v in _skill_id_variants(skill_id):
                if base == v:
                    return root
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".venv", "__pycache__")]
    return None


def _build_skill_dir_index(repo_root_dir: str) -> Dict[str, str]:
    wanted_files = {"SKILL.md", "skill.md", "Skill.md"}
    index: Dict[str, str] = {}
    for root, dirs, files in os.walk(repo_root_dir):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".venv", "__pycache__")]
        md_name = None
        for fn in wanted_files:
            if fn in files:
                md_name = fn
                break
        if not md_name:
            continue
        md_path = os.path.join(root, md_name)
        try:
            with open(md_path, "r", encoding="utf-8", errors="replace") as f:
                md_text = f.read()
        except Exception:
            continue
        fm_name, _ = _parse_front_matter(md_text)
        if fm_name:
            for k in _skill_id_variants(fm_name):
                index.setdefault(k, root)
        base = os.path.basename(root)
        if base:
            for k in _skill_id_variants(base):
                index.setdefault(k, root)
        parts = list(PurePosixPath(md_path.replace("\\", "/")).parts)
        try:
            i = len(parts) - 1 - parts[::-1].index("skills")
        except ValueError:
            i = -1
        if i >= 0:
            skill_path_parts = [p for p in parts[i + 1 : -1] if p]
            if skill_path_parts:
                joined = "/".join(skill_path_parts)
                for k in _skill_id_variants(joined):
                    index.setdefault(k, root)
    return index


def _find_only_skill_dir(repo_root_dir: str) -> Optional[str]:
    wanted_files = {"SKILL.md", "skill.md", "Skill.md"}
    found: List[str] = []
    for root, dirs, files in os.walk(repo_root_dir):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".venv", "__pycache__")]
        if any(f in wanted_files for f in files):
            found.append(root)
    uniq = sorted(set(found))
    if len(uniq) == 1:
        return uniq[0]
    skills_dir = os.path.join(repo_root_dir, "skills")
    if os.path.isdir(skills_dir):
        subdirs = [
            os.path.join(skills_dir, d)
            for d in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, d))
        ]
        if len(subdirs) == 1:
            return subdirs[0]
    return None


def _iter_files_recursive(base_dir: str) -> Iterable[Tuple[str, str]]:
    for root, _, files in os.walk(base_dir):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, base_dir).replace("\\", "/")
            safe = _safe_relpath(rel)
            if not safe:
                continue
            yield safe, full


def _calc_skill_sha256(files: List[Tuple[str, str]]) -> str:
    h = hashlib.sha256()
    for rel, full in sorted(files, key=lambda x: x[0]):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        with open(full, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        h.update(b"\0")
    return h.hexdigest()


def _read_skill_md_from_repo(repo_root_dir: str, *, skill_id: str) -> Optional[str]:
    skill_dir = _find_skill_dir(repo_root_dir, skill_id=skill_id)
    if not skill_dir:
        return None
    for fn in ("SKILL.md", "skill.md", "Skill.md"):
        p = os.path.join(skill_dir, fn)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
    return None


def _process_one_skill(
    *,
    pg: Pg,
    oss: Optional[OssUploader],
    client: SkillsShClient,
    skill_ref: SkillRef,
    skill_dir_index: Optional[Dict[str, str]],
    repo_zip_url: str,
    repo_zip_sha256: str,
    repo_zip_size_bytes: int,
    repo_downloaded_at: Optional[datetime],
    repo_root_dir: Optional[str],
    repo_total_skills: int,
    download_files: bool,
    fetch_security: bool,
    skip_if_done: bool,
    log_resume_checks: bool,
    allow_raw_md_fetch: bool,
) -> bool:
    started_at = _now_local()
    t0 = time.time()

    try:
        if skip_if_done:
            st_map = pg.get_artifact_status_map(skill_uids=[skill_ref.skill_uid])
            st = st_map.get(skill_ref.skill_uid)
            skip = False
            reason = None
            if download_files:
                if st in ("uploaded", "missing", "not_found"):
                    skip = True
                    reason = f"already_{st}"
            else:
                if st in ("uploaded", "skipped"):
                    skip = True
                    reason = "already_processed"
            if log_resume_checks:
                print(
                    _json_dumps(
                        {
                            "event": "skill_resume_check",
                            "skill_uid": skill_ref.skill_uid,
                            "artifact_status": st,
                            "download_files": download_files,
                            "decision": "skip" if skip else "process",
                        }
                    ),
                    flush=True,
                )
            if skip:
                print(
                    _json_dumps(
                        {
                            "event": "skill_skipped",
                            "skill_uid": skill_ref.skill_uid,
                            "reason": reason,
                            "artifact_status": st,
                            "elapsed_s": round(time.time() - t0, 3),
                            "started_at": _fmt_time(started_at),
                            "finished_at": _fmt_time(_now_local()),
                        }
                    ),
                    flush=True,
                )
                return True

        print(
            _json_dumps(
                {
                    "event": "skill_start",
                    "skill_uid": skill_ref.skill_uid,
                    "download_files": download_files,
                    "fetch_security": fetch_security,
                    "started_at": _fmt_time(started_at),
                }
            ),
            flush=True,
        )

        md_text: Optional[str] = None
        skill_dir: Optional[str] = None
        if repo_root_dir and skill_dir_index:
            for k in _skill_id_variants(skill_ref.skill_id):
                if k in skill_dir_index:
                    skill_dir = skill_dir_index[k]
                    break
        if repo_root_dir and skill_dir is None:
            skill_dir = _find_skill_dir(repo_root_dir, skill_id=skill_ref.skill_id)
        if skill_dir:
            for fn in ("SKILL.md", "skill.md", "Skill.md"):
                p = os.path.join(skill_dir, fn)
                if os.path.isfile(p):
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        md_text = f.read()
                    break
        if allow_raw_md_fetch and md_text is None:
            for branch in ("main", "master"):
                for path in (
                    f"skills/{skill_ref.skill_id}/SKILL.md",
                    f"skills/{skill_ref.skill_id}/skill.md",
                    f"{skill_ref.skill_id}/SKILL.md",
                    f"{skill_ref.skill_id}/skill.md",
                    "SKILL.md",
                    "skill.md",
                ):
                    md_text = client.download_github_raw(
                        owner=skill_ref.owner,
                        repo=skill_ref.repo,
                        branch=branch,
                        path=path,
                    )
                    if md_text is not None:
                        break
                if md_text is not None:
                    break

        name, desc = (None, None)
        if md_text:
            name, desc = _parse_front_matter(md_text)

        installs: Optional[int] = skill_ref.installs
        if installs is None:
            try:
                payload = client.search_skill(
                    q=f"{skill_ref.skill_id} {skill_ref.source}", limit=20
                )
                installs = _select_search_match(payload, skill_ref=skill_ref)
            except Exception as e:
                print(
                    _json_dumps(
                        {
                            "event": "skill_search_error",
                            "skill_uid": skill_ref.skill_uid,
                            "error": f"{type(e).__name__}: {e}",
                            "elapsed_s": round(time.time() - t0, 3),
                        }
                    ),
                    flush=True,
                )
                installs = None

        agent_trust_hub_status = None
        agent_trust_hub_url = None
        socket_status = None
        socket_url = None
        snyk_status = None
        snyk_url = None
        if fetch_security:
            try:
                html = client.fetch_skill_page_html(skill_ref.skills_sh_url)
                agent_trust_hub_status, agent_trust_hub_url = _parse_security_status(
                    html, skill_ref=skill_ref, typ="agent-trust-hub"
                )
                socket_status, socket_url = _parse_security_status(
                    html, skill_ref=skill_ref, typ="socket"
                )
                snyk_status, snyk_url = _parse_security_status(
                    html, skill_ref=skill_ref, typ="snyk"
                )
            except Exception as e:
                print(
                    _json_dumps(
                        {
                            "event": "skill_security_fetch_error",
                            "skill_uid": skill_ref.skill_uid,
                            "error": f"{type(e).__name__}: {e}",
                            "elapsed_s": round(time.time() - t0, 3),
                        }
                    ),
                    flush=True,
                )

        pg.upsert_skill(
            skill_uid=skill_ref.skill_uid,
            owner=skill_ref.owner,
            repo=skill_ref.repo,
            skill_id=skill_ref.skill_id,
            skills_sh_url=skill_ref.skills_sh_url,
            github_url=skill_ref.github_url,
            install_command=skill_ref.install_command,
            description=desc,
            installs=installs,
            agent_trust_hub_status=agent_trust_hub_status,
            agent_trust_hub_url=agent_trust_hub_url,
            socket_status=socket_status,
            socket_url=socket_url,
            snyk_status=snyk_status,
            snyk_url=snyk_url,
        )
        pg.ensure_artifact_row(skill_uid=skill_ref.skill_uid)
        pg.commit()

        if not download_files:
            pg.mark_artifact_skipped(skill_uid=skill_ref.skill_uid)
            pg.commit()
            print(
                _json_dumps(
                    {
                        "event": "skill_processed",
                        "skill_uid": skill_ref.skill_uid,
                        "download_files": False,
                        "elapsed_s": round(time.time() - t0, 3),
                    }
                )
            )
            return True

        if not oss:
            raise RuntimeError("missing OSS uploader")
        if repo_downloaded_at is None:
            repo_downloaded_at = _now_local()
        if not repo_root_dir:
            raise RuntimeError("missing extracted repo directory")
        if not skill_dir and repo_root_dir and repo_total_skills == 1:
            skill_dir = _find_only_skill_dir(repo_root_dir)

        if not skill_dir:
            raise RuntimeError(
                f"skill directory not found in repo archive (skill_id={skill_ref.skill_id}, variants={_skill_id_variants(skill_ref.skill_id)})"
            )

        prefix = oss.object_prefix_for_skill(
            owner=skill_ref.owner, repo=skill_ref.repo, skill_id=skill_ref.skill_id
        )
        files = list(_iter_files_recursive(skill_dir))
        total_files = len(files)
        source_skill_sha256 = _calc_skill_sha256(files)
        print(
            _json_dumps(
                {
                    "event": "skill_upload_start",
                    "skill_uid": skill_ref.skill_uid,
                    "files_total": total_files,
                    "oss_prefix": f"{prefix}/",
                    "elapsed_s": round(time.time() - t0, 3),
                }
            ),
            flush=True,
        )
        uploaded = 0
        for rel, full in files:
            key = f"{prefix}/{rel}"
            oss.put_file(key, full)
            uploaded += 1
            if uploaded in (1, 10) or uploaded % 200 == 0:
                print(
                    _json_dumps(
                        {
                            "event": "skill_upload_progress",
                            "skill_uid": skill_ref.skill_uid,
                            "uploaded": uploaded,
                            "files_total": total_files,
                            "elapsed_s": round(time.time() - t0, 3),
                        }
                    ),
                    flush=True,
                )

        pg.update_artifact_uploaded(
            skill_uid=skill_ref.skill_uid,
            oss_bucket=oss.bucket,
            oss_prefix=f"{prefix}/",
            source_zip_url=repo_zip_url,
            source_zip_sha256=repo_zip_sha256,
            source_zip_size_bytes=repo_zip_size_bytes,
            source_skill_sha256=source_skill_sha256,
            downloaded_at=repo_downloaded_at,
            files_count=total_files,
        )
        pg.commit()
        print(
            _json_dumps(
                {
                    "event": "skill_processed",
                    "skill_uid": skill_ref.skill_uid,
                    "files_uploaded": uploaded,
                    "elapsed_s": round(time.time() - t0, 3),
                    "started_at": _fmt_time(started_at),
                    "finished_at": _fmt_time(_now_local()),
                }
            ),
            flush=True,
        )
        return True
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        status = _artifact_status_for_error(e)
        try:
            pg.rollback()
        except Exception:
            pass
        try:
            pg.mark_skill_error(skill_uid=skill_ref.skill_uid, error=err)
            if status == "error":
                pg.mark_artifact_error(skill_uid=skill_ref.skill_uid, error=err)
            else:
                pg.mark_artifact_status(skill_uid=skill_ref.skill_uid, status=status, error=err)
            pg.commit()
        except Exception:
            pass
        print(
            _json_dumps(
                {
                    "event": "skill_error",
                    "skill_uid": skill_ref.skill_uid,
                    "error": err,
                    "artifact_status": status,
                    "elapsed_s": round(time.time() - t0, 3),
                    "started_at": _fmt_time(started_at),
                    "finished_at": _fmt_time(_now_local()),
                }
            ),
            flush=True,
        )
        return False


def _process_repo_group(
    *,
    pg_cfg: PgConfig,
    oss_cfg: OssConfig,
    skill_refs: List[SkillRef],
    download_files: bool,
    fetch_security: bool,
    skip_if_done: bool,
    log_resume_checks: bool,
    http_timeout_s: int,
    zip_read_timeout_s: int,
    http_max_attempts: int,
) -> Dict[str, Any]:
    client = SkillsShClient(
        timeout=http_timeout_s,
        zip_read_timeout_s=zip_read_timeout_s,
        max_attempts=http_max_attempts,
    )
    pg = Pg(pg_cfg)
    oss = OssUploader(oss_cfg)
    source = skill_refs[0].source if skill_refs else ""
    started = _now_utc().isoformat()
    started_local = _now_local()
    result: Dict[str, Any] = {
        "source": source,
        "skills": len(skill_refs),
        "started_at": _fmt_time(started_local),
        "ok": 0,
        "error": 0,
        "skipped": 0,
    }

    if skip_if_done:
        st_map = pg.get_artifact_status_map(skill_uids=[sr.skill_uid for sr in skill_refs])
        filtered: List[SkillRef] = []
        for sr in skill_refs:
            st = st_map.get(sr.skill_uid)
            if download_files:
                if st in ("uploaded", "missing", "not_found"):
                    result["skipped"] += 1
                    continue
            else:
                if st in ("uploaded", "skipped"):
                    result["skipped"] += 1
                    continue
            filtered.append(sr)
        skill_refs = filtered
        if not skill_refs:
            result["finished_at"] = _fmt_time(_now_local())
            return result

    print(
        _json_dumps(
            {
                "event": "repo_start",
                "source": source,
                "skills_total": result["skills"],
                "skills_to_process": len(skill_refs),
                "download_files": download_files,
                "fetch_security": fetch_security,
                "skip_if_done": skip_if_done,
                "started_at": _fmt_time(_now_local()),
            }
        ),
        flush=True,
    )

    branch: Optional[str] = None
    for b in ("main", "master"):
        text = client.download_github_raw(
            owner=skill_refs[0].owner,
            repo=skill_refs[0].repo,
            branch=b,
            path=f"skills/{skill_refs[0].skill_id}/SKILL.md",
        )
        if text is not None:
            branch = b
            break
    if branch is None:
        branch = "main"

    repo_zip_sha256: Optional[str] = None
    repo_zip_size_bytes: Optional[int] = None
    repo_zip_url = f"https://github.com/{skill_refs[0].owner}/{skill_refs[0].repo}/archive/refs/heads/{branch}.zip"
    try:
        if download_files:
            try:
                with tempfile.TemporaryDirectory(prefix="skills_sh_repo_") as td:
                    zip_path = os.path.join(td, "repo.zip")
                    last_zip_err: Optional[Exception] = None
                    branch_used: Optional[str] = None
                    for b in [branch, "master" if branch != "master" else "main"]:
                        try:
                            print(
                                _json_dumps(
                                    {
                                        "event": "repo_zip_downloading",
                                        "source": source,
                                        "branch": b,
                                        "started_at": _fmt_time(_now_local()),
                                    }
                                ),
                                flush=True,
                            )
                            repo_zip_url, repo_zip_sha256, repo_zip_size_bytes = client.download_github_repo_zip(
                                owner=skill_refs[0].owner,
                                repo=skill_refs[0].repo,
                                branch=b,
                                dest_path=zip_path,
                            )
                            branch_used = b
                            break
                        except Exception as e:
                            last_zip_err = e
                            print(
                                _json_dumps(
                                    {
                                        "event": "repo_zip_download_failed",
                                        "source": source,
                                        "branch": b,
                                        "error": f"{type(e).__name__}: {e}",
                                        "finished_at": _fmt_time(_now_local()),
                                    }
                                ),
                                flush=True,
                            )
                            continue
                    if branch_used is None:
                        raise last_zip_err or RuntimeError("failed to download repo zip")
                    repo_downloaded_at = _now_local()
                    print(
                        _json_dumps(
                            {
                                "event": "repo_zip_downloaded",
                                "source": source,
                                "branch": branch_used,
                                "zip_url": repo_zip_url,
                                "sha256": repo_zip_sha256,
                                "size_bytes": int(repo_zip_size_bytes or 0),
                                "downloaded_at": _fmt_time(repo_downloaded_at),
                            }
                        ),
                        flush=True,
                    )
                    extract_dir = os.path.join(td, "extract")
                    os.makedirs(extract_dir, exist_ok=True)
                    _extract_zip_safe(zip_path, extract_dir)
                    children = [
                        os.path.join(extract_dir, p) for p in os.listdir(extract_dir)
                    ]
                    roots = [p for p in children if os.path.isdir(p)]
                    repo_root_dir = roots[0] if roots else extract_dir
                    skill_dir_index = _build_skill_dir_index(repo_root_dir)

                    for sr in skill_refs:
                        ok = _process_one_skill(
                            pg=pg,
                            oss=oss,
                            client=client,
                            skill_ref=sr,
                            skill_dir_index=skill_dir_index,
                            repo_zip_url=repo_zip_url,
                            repo_zip_sha256=repo_zip_sha256 or "",
                            repo_zip_size_bytes=int(repo_zip_size_bytes or 0),
                            repo_downloaded_at=repo_downloaded_at,
                            repo_root_dir=repo_root_dir,
                            repo_total_skills=result["skills"],
                            download_files=True,
                            fetch_security=fetch_security,
                            skip_if_done=skip_if_done,
                            log_resume_checks=log_resume_checks,
                        allow_raw_md_fetch=False,
                        )
                        if ok:
                            result["ok"] += 1
                        else:
                            result["error"] += 1
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                status = _artifact_status_for_error(e)
                try:
                    pg.rollback()
                except Exception:
                    pass
                for sr in skill_refs:
                    try:
                        pg.ensure_artifact_row(skill_uid=sr.skill_uid)
                        try:
                            pg.mark_skill_error(skill_uid=sr.skill_uid, error=err)
                        except Exception:
                            pass
                        if status == "error":
                            pg.mark_artifact_error(skill_uid=sr.skill_uid, error=err)
                        else:
                            pg.mark_artifact_status(skill_uid=sr.skill_uid, status=status, error=err)
                    except Exception:
                        continue
                try:
                    pg.commit()
                except Exception:
                    pass
                raise
    finally:
        try:
            oss.close()
        finally:
            try:
                pg.close()
            finally:
                client.close()

    if not download_files:
        client2 = SkillsShClient(
            timeout=http_timeout_s,
            zip_read_timeout_s=zip_read_timeout_s,
            max_attempts=http_max_attempts,
        )
        pg2 = Pg(pg_cfg)
        try:
            for sr in skill_refs:
                ok = _process_one_skill(
                    pg=pg2,
                    oss=None,
                    client=client2,
                    skill_ref=sr,
                    skill_dir_index=None,
                    repo_zip_url=repo_zip_url,
                    repo_zip_sha256="",
                    repo_zip_size_bytes=0,
                    repo_downloaded_at=None,
                    repo_root_dir=None,
                    repo_total_skills=result["skills"],
                    download_files=False,
                    fetch_security=fetch_security,
                    skip_if_done=skip_if_done,
                    log_resume_checks=log_resume_checks,
                    allow_raw_md_fetch=False,
                )
                if ok:
                    result["ok"] += 1
                else:
                    result["error"] += 1
        finally:
            try:
                pg2.close()
            finally:
                client2.close()

    result["finished_at"] = _fmt_time(_now_local())
    return result


def _repo_worker_entry(
    result_queue: Any,
    *,
    pg_cfg: PgConfig,
    oss_cfg: OssConfig,
    skill_refs: List[SkillRef],
    download_files: bool,
    fetch_security: bool,
    skip_if_done: bool,
    log_resume_checks: bool,
    http_timeout_s: int,
    zip_read_timeout_s: int,
    http_max_attempts: int,
) -> None:
    try:
        res = _process_repo_group(
            pg_cfg=pg_cfg,
            oss_cfg=oss_cfg,
            skill_refs=skill_refs,
            download_files=download_files,
            fetch_security=fetch_security,
            skip_if_done=skip_if_done,
            log_resume_checks=log_resume_checks,
            http_timeout_s=http_timeout_s,
            zip_read_timeout_s=zip_read_timeout_s,
            http_max_attempts=http_max_attempts,
        )
        result_queue.put({"ok": True, "result": res})
    except Exception as e:
        result_queue.put(
            {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(limit=20),
            }
        )
        raise
    finally:
        try:
            result_queue.close()
        except Exception:
            pass


def fetch_skills_sh(
    *,
    pg_cfg: PgConfig,
    oss_cfg: OssConfig,
    count: Optional[int],
    concurrency: int,
    download_files: bool,
    fetch_security: bool,
    skip_if_done: bool,
    log_resume_checks: bool,
    repo_timeout_s: int,
    http_timeout_s: int,
    zip_read_timeout_s: int,
    http_max_attempts: int,
    skill_source: str,
    leaderboard_view: str,
    skills_api_key: Optional[str],
) -> None:
    started_at = _now_local()
    client = SkillsShClient(
        timeout=http_timeout_s,
        zip_read_timeout_s=zip_read_timeout_s,
        max_attempts=http_max_attempts,
        skills_api_key=skills_api_key,
    )
    skill_refs: List[SkillRef] = []
    if skill_source == "api_v1" and not skills_api_key:
        print(
            _json_dumps(
                {
                    "event": "official_missing_key_fallback",
                    "fallback_to": "public",
                    "hint": "provide --skills-api-key or SKILLS_SH_API_KEY to use /api/v1",
                }
            ),
            flush=True,
        )
        skill_source = "public"

    if skill_source == "api_v1":
        page = 0
        per_page = 500
        remaining = int(count) if count is not None else None
        total_skills: Optional[int] = None
        while True:
            payload = client.fetch_official_skills_page(
                view=leaderboard_view, page=page, per_page=per_page
            )
            add_n = remaining
            refs, total, has_more = _parse_skill_refs_from_official_api(
                payload, max_add=add_n
            )
            if total_skills is None and total is not None:
                total_skills = total
                print(
                    _json_dumps(
                        {
                            "event": "official_total",
                            "view": leaderboard_view,
                            "total": int(total_skills),
                            "per_page": int(per_page),
                        }
                    ),
                    flush=True,
                )
            skill_refs.extend(refs)
            if remaining is not None:
                remaining -= len(refs)
                if remaining <= 0:
                    break
            if not has_more:
                break
            page += 1
        client.close()
    elif skill_source == "api":
        page = 0
        remaining = int(count) if count is not None else None
        total_skills: Optional[int] = None
        skipped_non_github_total = 0
        while True:
            payload = client.fetch_leaderboard_page(view=leaderboard_view, page=page)
            add_n = remaining
            refs, total, has_more, skipped_non_github = _parse_skill_refs_from_leaderboard(
                payload, max_add=add_n
            )
            skipped_non_github_total += int(skipped_non_github)
            if total_skills is None and total is not None:
                total_skills = total
                print(
                    _json_dumps(
                        {
                            "event": "leaderboard_total",
                            "view": leaderboard_view,
                            "total": int(total_skills),
                            "page_size": len(payload.get("skills") or []),
                        }
                    ),
                    flush=True,
                )
            skill_refs.extend(refs)
            if remaining is not None:
                remaining -= len(refs)
                if remaining <= 0:
                    break
            if not has_more:
                break
            page += 1
        if skipped_non_github_total > 0:
            print(
                _json_dumps(
                    {
                        "event": "leaderboard_skipped_non_github",
                        "view": leaderboard_view,
                        "skipped": int(skipped_non_github_total),
                    }
                ),
                flush=True,
            )
        client.close()
    elif skill_source == "public":
        lb_page = 0
        remaining = int(count) if count is not None else None
        total_seen: Optional[int] = None
        skill_refs_lb: List[SkillRef] = []
        while True:
            payload = client.fetch_leaderboard_page(view=leaderboard_view, page=lb_page)
            refs, total, has_more, _skipped_non_github = _parse_skill_refs_from_leaderboard(
                payload, max_add=remaining
            )
            if total_seen is None and total is not None:
                total_seen = total
                print(
                    _json_dumps(
                        {
                            "event": "public_leaderboard_total",
                            "view": leaderboard_view,
                            "declared_total": int(total_seen),
                            "page_size": len(payload.get("skills") or []),
                        }
                    ),
                    flush=True,
                )
            skill_refs_lb.extend(refs)
            if remaining is not None:
                remaining -= len(refs)
                if remaining <= 0:
                    break
            if not has_more or not refs:
                break
            lb_page += 1
            if lb_page > 500:
                break

        skill_refs_sm: List[SkillRef] = []
        try:
            urls = client.fetch_sitemap_urls()
            skill_refs_sm = _parse_skill_refs_from_urls(urls)
            print(
                _json_dumps(
                    {
                        "event": "public_sitemap_loaded",
                        "urls": int(len(urls)),
                        "skills": int(len(skill_refs_sm)),
                    }
                ),
                flush=True,
            )
        except Exception as e:
            print(
                _json_dumps(
                    {
                        "event": "public_sitemap_error",
                        "error": f"{type(e).__name__}: {e}",
                    }
                ),
                flush=True,
            )

        skill_refs = _merge_skill_refs(skill_refs_lb, skill_refs_sm)
        if count is not None:
            skill_refs = skill_refs[: int(count)]
        print(
            _json_dumps(
                {
                    "event": "public_sources_merged",
                    "leaderboard_skills": int(len(skill_refs_lb)),
                    "sitemap_skills": int(len(skill_refs_sm)),
                    "unique_skills": int(len(skill_refs)),
                }
            ),
            flush=True,
        )
        client.close()
    else:
        urls = client.fetch_sitemap_urls()
        skill_refs = _parse_skill_refs_from_urls(urls)
        client.close()

    if not download_files and not fetch_security:
        pg = Pg(pg_cfg)
        try:
            processed = 0
            skipped = 0
            batch_size = 1000
            commit_every = 200
            for i in range(0, len(skill_refs), batch_size):
                batch = skill_refs[i : i + batch_size]
                st_map: Dict[str, Optional[str]] = {}
                if skip_if_done:
                    st_map = pg.get_artifact_status_map(
                        skill_uids=[sr.skill_uid for sr in batch]
                    )
                for sr in batch:
                    st = st_map.get(sr.skill_uid)
                    if skip_if_done and st in (
                        "uploaded",
                        "skipped",
                        "missing",
                        "not_found",
                        "not_supported",
                    ):
                        skipped += 1
                        continue
                    pg.upsert_skill(
                        skill_uid=sr.skill_uid,
                        owner=sr.owner,
                        repo=sr.repo,
                        skill_id=sr.skill_id,
                        skills_sh_url=sr.skills_sh_url,
                        github_url=sr.github_url,
                        install_command=sr.install_command,
                        description=None,
                        installs=sr.installs,
                        agent_trust_hub_status=None,
                        agent_trust_hub_url=None,
                        socket_status=None,
                        socket_url=None,
                        snyk_status=None,
                        snyk_url=None,
                    )
                    pg.ensure_artifact_row(skill_uid=sr.skill_uid)
                    pg.mark_artifact_skipped(skill_uid=sr.skill_uid)
                    processed += 1
                    if processed % commit_every == 0:
                        pg.commit()
                pg.commit()
                if (processed + skipped) % 2000 == 0:
                    print(
                        _json_dumps(
                            {
                                "event": "ingest_progress",
                                "processed": int(processed),
                                "skipped": int(skipped),
                                "total": int(len(skill_refs)),
                                "started_at": _fmt_time(started_at),
                                "now": _fmt_time(_now_local()),
                            }
                        ),
                        flush=True,
                    )
            print(
                _json_dumps(
                    {
                        "event": "ingest_done",
                        "processed": int(processed),
                        "skipped": int(skipped),
                        "total": int(len(skill_refs)),
                        "started_at": _fmt_time(started_at),
                        "finished_at": _fmt_time(_now_local()),
                    }
                ),
                flush=True,
            )
        finally:
            pg.close()
        return

    groups: Dict[str, List[SkillRef]] = {}
    for sr in skill_refs:
        groups.setdefault(sr.source, []).append(sr)

    repo_groups = list(groups.values())
    total_repos = len(repo_groups)
    progress_lock = threading.Lock()
    progress = {"repo_ok": 0, "repo_error": 0, "repo_finished": 0}
    hb_stop = threading.Event()

    def _heartbeat() -> None:
        while not hb_stop.wait(60.0):
            with progress_lock:
                ok = int(progress["repo_ok"])
                err = int(progress["repo_error"])
                finished = int(progress["repo_finished"])
            print(
                _json_dumps(
                    {
                        "event": "heartbeat",
                        "started_at": _fmt_time(started_at),
                        "now": _fmt_time(_now_local()),
                        "repos_total": total_repos,
                        "repos_ok": ok,
                        "repos_error": err,
                        "repos_finished": finished,
                        "repos_remaining": max(0, total_repos - finished),
                        "active_repos": len(active),
                        "repo_timeout_s": int(repo_timeout_s),
                        "http_timeout_s": int(http_timeout_s),
                        "zip_read_timeout_s": int(zip_read_timeout_s),
                        "http_max_attempts": int(http_max_attempts),
                        "maxrss_kb": _maxrss_kb(),
                    }
                ),
                flush=True,
            )

    hb_thread = threading.Thread(target=_heartbeat, name="skills_sh_heartbeat", daemon=True)
    hb_thread.start()

    ctx = mp.get_context("spawn")
    active: List[Dict[str, Any]] = []
    try:
        next_index = 0
        while next_index < total_repos or active:
            while next_index < total_repos and len(active) < max(1, concurrency):
                g = repo_groups[next_index]
                next_index += 1
                source = g[0].source if g else ""
                q: Any = ctx.Queue(maxsize=1)
                proc = ctx.Process(
                    target=_repo_worker_entry,
                    kwargs={
                        "result_queue": q,
                        "pg_cfg": pg_cfg,
                        "oss_cfg": oss_cfg,
                        "skill_refs": g,
                        "download_files": download_files,
                        "fetch_security": fetch_security,
                        "skip_if_done": skip_if_done,
                        "log_resume_checks": log_resume_checks,
                        "http_timeout_s": http_timeout_s,
                        "zip_read_timeout_s": zip_read_timeout_s,
                        "http_max_attempts": http_max_attempts,
                    },
                    name=f"skills_sh_repo_{next_index}",
                )
                proc.start()
                active.append(
                    {
                        "process": proc,
                        "queue": q,
                        "source": source,
                        "started_monotonic": time.monotonic(),
                        "started_at": _fmt_time(_now_local()),
                    }
                )
                print(
                    _json_dumps(
                        {
                            "event": "repo_worker_started",
                            "source": source,
                            "pid": proc.pid,
                            "repo_timeout_s": int(repo_timeout_s),
                            "http_timeout_s": int(http_timeout_s),
                            "zip_read_timeout_s": int(zip_read_timeout_s),
                            "http_max_attempts": int(http_max_attempts),
                            "started_at": _fmt_time(_now_local()),
                        }
                    ),
                    flush=True,
                )

            if not active:
                continue

            finished_any = False
            now_mono = time.monotonic()
            next_active: List[Dict[str, Any]] = []
            for item in active:
                proc = item["process"]
                q = item["queue"]
                source = item["source"]
                elapsed = now_mono - float(item["started_monotonic"])

                if download_files and proc.is_alive() and elapsed > float(repo_timeout_s):
                    try:
                        proc.terminate()
                        proc.join(timeout=5)
                    except Exception:
                        pass
                    if proc.is_alive():
                        try:
                            proc.kill()
                            proc.join(timeout=5)
                        except Exception:
                            pass
                    with progress_lock:
                        progress["repo_error"] += 1
                        progress["repo_finished"] += 1
                    print(
                        _json_dumps(
                            {
                                "event": "repo_timeout",
                                "source": source,
                                "pid": proc.pid,
                                "elapsed_s": round(elapsed, 3),
                                "repo_timeout_s": int(repo_timeout_s),
                                "maxrss_kb": _maxrss_kb(),
                                "finished_at": _fmt_time(_now_local()),
                            }
                        ),
                        flush=True,
                    )
                    try:
                        q.close()
                    except Exception:
                        pass
                    finished_any = True
                    continue

                if proc.is_alive():
                    next_active.append(item)
                    continue

                proc.join(timeout=0)
                payload: Optional[Dict[str, Any]] = None
                try:
                    payload = q.get_nowait()
                except queue.Empty:
                    payload = None
                except Exception:
                    payload = None
                try:
                    q.close()
                except Exception:
                    pass

                if payload and payload.get("ok"):
                    res = payload.get("result") or {}
                    with progress_lock:
                        progress["repo_ok"] += 1
                        progress["repo_finished"] += 1
                    print(
                        _json_dumps({"event": "repo_done", "maxrss_kb": _maxrss_kb(), **res}),
                        flush=True,
                    )
                else:
                    err = "worker exited without result"
                    tb = None
                    if payload:
                        err = str(payload.get("error") or err)
                        tb = payload.get("traceback")
                    elif proc.exitcode not in (0, None):
                        err = f"worker exited with code {proc.exitcode}"
                    with progress_lock:
                        progress["repo_error"] += 1
                        progress["repo_finished"] += 1
                    body: Dict[str, Any] = {
                        "event": "repo_error",
                        "source": source,
                        "error": err,
                        "exit_code": proc.exitcode,
                        "maxrss_kb": _maxrss_kb(),
                    }
                    if tb:
                        body["traceback"] = tb
                    print(_json_dumps(body), flush=True)
                finished_any = True

            active = next_active
            if not finished_any:
                time.sleep(1.0)
    finally:
        for item in active:
            proc = item.get("process")
            q = item.get("queue")
            try:
                if proc is not None and proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=3)
            except Exception:
                pass
            try:
                if q is not None:
                    q.close()
            except Exception:
                pass
        hb_stop.set()
        with progress_lock:
            ok = int(progress["repo_ok"])
            err = int(progress["repo_error"])
            finished = int(progress["repo_finished"])
        print(
            _json_dumps(
                {
                    "event": "fetch_done",
                    "started_at": _fmt_time(started_at),
                    "finished_at": _fmt_time(_now_local()),
                    "repos_total": total_repos,
                    "repos_ok": ok,
                    "repos_error": err,
                    "repos_finished": finished,
                    "repos_remaining": max(0, total_repos - finished),
                    "active_repos": len(active),
                    "repo_timeout_s": int(repo_timeout_s),
                    "http_timeout_s": int(http_timeout_s),
                    "zip_read_timeout_s": int(zip_read_timeout_s),
                    "http_max_attempts": int(http_max_attempts),
                    "maxrss_kb": _maxrss_kb(),
                }
            ),
            flush=True,
        )


def _pg_config_from_args(args: argparse.Namespace) -> PgConfig:
    dsn = (
        f"host={args.pg_host} port={args.pg_port} dbname={args.pg_db} "
        f"user={args.pg_user} password={args.pg_password}"
    )
    return PgConfig(dsn=dsn)


def _oss_config_from_args(args: argparse.Namespace) -> OssConfig:
    return OssConfig(
        region=args.oss_region, endpoint=args.oss_endpoint, bucket=args.oss_bucket
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fetch skills.sh skills into PG and OSS")
    p.add_argument("--pg-host", required=True)
    p.add_argument("--pg-port", type=int, default=5432)
    p.add_argument("--pg-db", required=True)
    p.add_argument("--pg-user", required=True)
    p.add_argument("--pg-password", required=True)
    p.add_argument("--oss-region", required=True)
    p.add_argument("--oss-endpoint", required=True)
    p.add_argument("--oss-bucket", required=True)

    sub = p.add_subparsers(dest="cmd", required=True)
    fetch = sub.add_parser("fetch", help="Fetch from skills.sh")
    fetch.add_argument("--count", default="all", help="all 或数字")
    fetch.add_argument("--concurrency", type=int, default=4, help="并发数（建议 2~6）")
    fetch.add_argument("--skip-files", action="store_true", help="只入库，不下载/上传 OSS")
    fetch.add_argument("--skip-security", action="store_true", help="不抓取安全审计状态（更快）")
    fetch.add_argument(
        "--repo-timeout-s",
        type=int,
        default=60,
        help="单个 repo 允许的最长处理时长，超时后强制终止该 repo 子进程",
    )
    fetch.add_argument(
        "--http-timeout-s",
        type=int,
        default=15,
        help="普通 HTTP 请求超时秒数（skills.sh 页面、raw 文件等）",
    )
    fetch.add_argument(
        "--zip-read-timeout-s",
        type=int,
        default=40,
        help="GitHub repo zip 下载读取超时秒数",
    )
    fetch.add_argument(
        "--http-max-attempts",
        type=int,
        default=2,
        help="HTTP 最大尝试次数，默认 2 代表首次 + 1 次重试",
    )
    fetch.add_argument(
        "--skill-source",
        choices=["api_v1", "public", "api", "sitemap"],
        default="public",
        help="技能列表来源：api_v1 使用官方 /api/v1/skills（需要 API key）；public 无 key（合并公开 /api/skills + sitemap，覆盖有限）；api 仅公开 /api/skills；sitemap 仅 sitemap",
    )
    fetch.add_argument(
        "--leaderboard-view",
        choices=["all-time", "trending", "hot"],
        default="all-time",
        help="当 --skill-source=api 时使用的榜单视图",
    )
    fetch.add_argument(
        "--skills-api-key",
        default=None,
        help="skills.sh 官方 API key（Bearer）。也可通过环境变量 SKILLS_SH_API_KEY 传入",
    )
    fetch.add_argument(
        "--no-skip-if-done",
        action="store_true",
        help="不启用断点跳过（默认会跳过已处理的 skill）",
    )
    fetch.add_argument("--log-resume-checks", action="store_true", help="输出断点续跑判定信息（日志会很多）")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = build_arg_parser()
    args = p.parse_args(argv)

    if args.cmd != "fetch":
        raise RuntimeError("unsupported cmd")

    if str(args.count).lower() == "all":
        count = None
    else:
        count = int(args.count)

    skills_api_key = (
        str(args.skills_api_key).strip()
        if getattr(args, "skills_api_key", None)
        else (os.environ.get("SKILLS_SH_API_KEY") or os.environ.get("SKILLS_API_KEY"))
    )
    skills_api_key = (skills_api_key.strip() if skills_api_key else None) or None

    def _on_term(signum: int, _frame: object) -> None:
        print(
            _json_dumps(
                {
                    "event": "signal",
                    "signal": int(signum),
                    "finished_at": _fmt_time(_now_local()),
                }
            ),
            flush=True,
        )
        os._exit(128 + int(signum))

    for s in (signal.SIGTERM, signal.SIGQUIT):
        try:
            signal.signal(s, _on_term)
        except Exception:
            pass

    try:
        current_hup = signal.getsignal(signal.SIGHUP)
        if current_hup is not signal.SIG_IGN:
            signal.signal(signal.SIGHUP, _on_term)
    except Exception:
        pass

    try:
        fetch_skills_sh(
            pg_cfg=_pg_config_from_args(args),
            oss_cfg=_oss_config_from_args(args),
            count=count,
            concurrency=int(args.concurrency),
            download_files=not bool(args.skip_files),
            fetch_security=not bool(args.skip_security),
            skip_if_done=not bool(args.no_skip_if_done),
            log_resume_checks=bool(args.log_resume_checks),
            repo_timeout_s=int(args.repo_timeout_s),
            http_timeout_s=int(args.http_timeout_s),
            zip_read_timeout_s=int(args.zip_read_timeout_s),
            http_max_attempts=int(args.http_max_attempts),
            skill_source=str(args.skill_source),
            leaderboard_view=str(args.leaderboard_view),
            skills_api_key=skills_api_key,
        )
        return 0
    except KeyboardInterrupt:
        print(
            _json_dumps(
                {
                    "event": "fatal",
                    "error": "KeyboardInterrupt",
                    "finished_at": _fmt_time(_now_local()),
                }
            ),
            flush=True,
        )
        raise
    except Exception as e:
        print(
            _json_dumps(
                {
                    "event": "fatal",
                    "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc(limit=20),
                    "finished_at": _fmt_time(_now_local()),
                }
            ),
            flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
