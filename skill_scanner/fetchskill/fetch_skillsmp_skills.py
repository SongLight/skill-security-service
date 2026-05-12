import argparse
import hashlib
import heapq
import json
import os
import re
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse
from urllib.request import pathname2url

import requests


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_lastmod_iso(v: Optional[str]) -> Optional[datetime]:
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(v.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _safe_posix_path(p: str) -> Optional[str]:
    s = (p or "").replace("\\", "/").lstrip("/")
    if not s:
        return None
    parts = [x for x in s.split("/") if x not in ("", ".")]
    if any(x == ".." for x in parts):
        return None
    return "/".join(parts)


def _skill_id_from_skill_url(skill_url: str) -> str:
    u = urlparse(skill_url)
    path = (u.path or "").rstrip("/")
    if path.startswith("/skills/"):
        return path[len("/skills/") :]
    return path.strip("/").split("/")[-1] or skill_url


def _extract_github_tree_url_from_skill_page(html_text: str) -> Optional[str]:
    m = re.search(r"import-skills\\?githuburl=([^&\"'<>\\s]+)", html_text, flags=re.IGNORECASE)
    if m:
        return unquote(m.group(1))
    m = re.search(r"githuburl=([^&\"'<>\\s]+)", html_text, flags=re.IGNORECASE)
    if m and "github.com" in m.group(1):
        return unquote(m.group(1))
    m = re.search(r"(https://github\\.com/[^\"'<>\\s]+/(?:tree|blob)/[^\"'<>\\s]+)", html_text)
    if m:
        return m.group(1)
    return None


def _looks_like_cloudflare_challenge(html_text: str) -> bool:
    s = (html_text or "").lower()
    if "cdn-cgi/challenge-platform" in s:
        return True
    if "cf-turnstile" in s:
        return True
    if "just a moment" in s:
        return True
    if "checking your browser" in s:
        return True
    return False


def _parse_count_with_commas(v: str) -> Optional[int]:
    s = (v or "").strip()
    if not s:
        return None
    s = s.replace(",", "")
    if not s.isdigit():
        return None
    try:
        return int(s)
    except Exception:
        return None


def _extract_stars_forks_from_skill_page(html_text: str) -> Tuple[Optional[int], Optional[int]]:
    stars: Optional[int] = None
    forks: Optional[int] = None
    m = re.search(r"stars:\\s*([0-9][0-9,]*)", html_text, flags=re.IGNORECASE)
    if m:
        stars = _parse_count_with_commas(m.group(1))
    m = re.search(r"forks:\\s*([0-9][0-9,]*)", html_text, flags=re.IGNORECASE)
    if m:
        forks = _parse_count_with_commas(m.group(1))
    return stars, forks


def _parse_github_tree_url(github_url: str) -> Optional[Tuple[str, str, str, str]]:
    u = urlparse(github_url)
    if u.netloc not in ("github.com", "www.github.com"):
        return None
    parts = [p for p in (u.path or "").split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    branch = "main"
    path = ""
    if len(parts) >= 4 and parts[2] in ("tree", "blob"):
        branch = parts[3]
        path = "/".join(parts[4:])
        if parts[2] == "blob":
            if "/" in path:
                path = path.rsplit("/", 1)[0]
            else:
                path = ""
    return owner, repo, branch, path


def _artifact_hash_for_files(files: Sequence[Dict[str, Any]]) -> str:
    h = hashlib.sha256()
    items: List[Tuple[str, bytes]] = []
    for f in files:
        p = _safe_posix_path(str(f.get("path") or "")) or ""
        if not p:
            continue
        raw = f.get("content")
        if raw is None:
            continue
        if isinstance(raw, str):
            b = raw.encode("utf-8")
        elif isinstance(raw, (bytes, bytearray)):
            b = bytes(raw)
        elif isinstance(raw, dict) and isinstance(raw.get("base64"), str):
            import base64

            b = base64.b64decode(raw.get("base64") or "")
        else:
            b = str(raw).encode("utf-8")
        items.append((p, b))
    items.sort(key=lambda x: x[0])
    for p, b in items:
        h.update(p.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(b).digest())
        h.update(b"\n")
    return h.hexdigest()


@dataclass(frozen=True)
class PgConfig:
    dsn: str


class Pg:
    def __init__(self, cfg: PgConfig):
        try:
            import psycopg2  # type: ignore
        except Exception as e:
            raise RuntimeError("Missing PostgreSQL driver. Install: pip install psycopg2-binary") from e

        self._psycopg2 = psycopg2
        self._conn = psycopg2.connect(cfg.dsn)
        self._conn.autocommit = False
        with self._conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'Asia/Shanghai'")

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            return

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def execute(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)

    def fetchall(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> List[Tuple[Any, ...]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return rows

    def upsert_skill(
        self,
        *,
        skill_id: str,
        skill_url: str,
        lastmod_utc: Optional[datetime],
        github_url: Optional[str],
        github_owner: Optional[str],
        github_repo: Optional[str],
        github_branch: Optional[str],
        github_path: Optional[str],
        stars_count: Optional[int],
        forks_count: Optional[int],
        last_error: Optional[str],
    ) -> None:
        sql = """
        INSERT INTO skillsmp_skill(
            skill_id, skill_url, sitemap_lastmod_utc,
            github_url, github_owner, github_repo, github_branch, github_path,
            stars_count, forks_count,
            last_error, created_at, updated_at, last_seen_at
        )
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (skill_id) DO UPDATE SET
            skill_url=EXCLUDED.skill_url,
            sitemap_lastmod_utc=COALESCE(EXCLUDED.sitemap_lastmod_utc, skillsmp_skill.sitemap_lastmod_utc),
            github_url=COALESCE(EXCLUDED.github_url, skillsmp_skill.github_url),
            github_owner=COALESCE(EXCLUDED.github_owner, skillsmp_skill.github_owner),
            github_repo=COALESCE(EXCLUDED.github_repo, skillsmp_skill.github_repo),
            github_branch=COALESCE(EXCLUDED.github_branch, skillsmp_skill.github_branch),
            github_path=COALESCE(EXCLUDED.github_path, skillsmp_skill.github_path),
            stars_count=COALESCE(EXCLUDED.stars_count, skillsmp_skill.stars_count),
            forks_count=COALESCE(EXCLUDED.forks_count, skillsmp_skill.forks_count),
            last_error=EXCLUDED.last_error,
            updated_at=EXCLUDED.updated_at,
            last_seen_at=EXCLUDED.last_seen_at
        """
        now = _now_local()
        self.execute(
            sql,
            (
                skill_id,
                skill_url,
                lastmod_utc,
                github_url,
                github_owner,
                github_repo,
                github_branch,
                github_path,
                (int(stars_count) if stars_count is not None else None),
                (int(forks_count) if forks_count is not None else None),
                last_error,
                now,
                now,
                now,
            ),
        )

    def ensure_artifact_row(self, *, skill_id: str, oss_prefix: str, skillsmp_download_url: Optional[str]) -> None:
        sql = """
        INSERT INTO skillsmp_skill_artifact(skill_id, oss_prefix, skillsmp_download_url, status, created_at, updated_at)
        VALUES(%s,%s,%s,'pending',%s,%s)
        ON CONFLICT (skill_id) DO UPDATE SET
            oss_prefix=EXCLUDED.oss_prefix,
            skillsmp_download_url=COALESCE(EXCLUDED.skillsmp_download_url, skillsmp_skill_artifact.skillsmp_download_url),
            updated_at=EXCLUDED.updated_at
        """
        now = _now_local()
        self.execute(sql, (skill_id, oss_prefix, skillsmp_download_url, now, now))

    def mark_artifact_downloaded(self, *, skill_id: str, skillsmp_download_url: Optional[str]) -> None:
        sql = """
        UPDATE skillsmp_skill_artifact
        SET downloaded_at=%s,
            skillsmp_download_url=COALESCE(%s, skillsmp_download_url),
            updated_at=%s
        WHERE skill_id=%s
        """
        now = _now_local()
        self.execute(sql, (now, skillsmp_download_url, now, skill_id))

    def mark_artifact_uploaded(
        self,
        *,
        skill_id: str,
        file_count: int,
        artifact_sha256: str,
    ) -> None:
        sql = """
        UPDATE skillsmp_skill_artifact
        SET status='uploaded',
            file_count=%s,
            artifact_sha256=%s,
            uploaded_at=%s,
            updated_at=%s,
            last_error=NULL
        WHERE skill_id=%s
        """
        now = _now_local()
        self.execute(sql, (int(file_count), artifact_sha256, now, now, skill_id))

    def mark_artifact_error(self, *, skill_id: str, error: str) -> None:
        sql = """
        UPDATE skillsmp_skill_artifact
        SET status='error', updated_at=%s, last_error=%s
        WHERE skill_id=%s
        """
        self.execute(sql, (_now_local(), error, skill_id))

    def get_uploaded_skill_ids(self) -> List[str]:
        sql = "SELECT skill_id FROM skillsmp_skill_artifact WHERE status='uploaded'"
        rows = self.fetchall(sql)
        return [str(r[0]) for r in rows]


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
            raise RuntimeError("Missing OSS SDK. Install: pip install alibabacloud-oss-v2") from e

        credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()
        oss_cfg = oss.config.load_default()
        oss_cfg.credentials_provider = credentials_provider
        oss_cfg.region = cfg.region
        oss_cfg.endpoint = cfg.endpoint
        self._oss = oss
        self._client = oss.Client(oss_cfg)
        self._cfg = cfg

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            return

    def put_bytes(self, key: str, data: bytes) -> Optional[str]:
        result = self._client.put_object(self._oss.PutObjectRequest(bucket=self._cfg.bucket, key=key, body=data))
        return getattr(result, "etag", None)

    def object_prefix_for_skill(self, *, skill_id: str, github_owner: str, github_repo: str) -> str:
        safe_skill = pathname2url(skill_id)
        return f"skillsmp/{github_owner}/{github_repo}/{safe_skill}"


class SkillsMpClient:
    def __init__(
        self,
        *,
        base_url: str = "https://skillsmp.com",
        timeout_s: int = 20,
        max_attempts: int = 3,
        max_backoff_s: float = 8.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout_s = max(1, int(timeout_s))
        self._max_attempts = max(1, int(max_attempts))
        self._max_backoff_s = max(0.0, float(max_backoff_s))
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "skill-security-service/skillsmp-crawler",
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
    ) -> requests.Response:
        backoff = 1.0
        last_exc: Optional[Exception] = None
        for _ in range(self._max_attempts):
            try:
                r = self._session.request(
                    method,
                    url,
                    params=params,
                    timeout=self._timeout_s if timeout is None else timeout,
                    stream=stream,
                )
                if r.status_code in (429, 502, 503, 504):
                    try:
                        r.close()
                    except Exception:
                        pass
                    time.sleep(min(backoff, self._max_backoff_s))
                    backoff = min(backoff * 2.0, self._max_backoff_s)
                    continue
                r.raise_for_status()
                return r
            except Exception as e:
                last_exc = e if isinstance(e, Exception) else Exception(str(e))
                time.sleep(min(backoff, self._max_backoff_s))
                backoff = min(backoff * 2.0, self._max_backoff_s)
        raise RuntimeError(f"request failed: {method} {url}: {last_exc}")

    def fetch_sitemap_index(self, sitemap_index_url: str) -> List[str]:
        r = self._request_with_backoff("GET", sitemap_index_url)
        xml = r.text
        root = ET.fromstring(xml)
        locs: List[str] = []
        for el in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            if el.text:
                locs.append(el.text.strip())
        return locs

    def download_to_tempfile(self, url: str) -> str:
        r = self._request_with_backoff("GET", url, stream=True, timeout=(10, 120))
        tmp = tempfile.NamedTemporaryFile(prefix="skillsmp_sitemap_", suffix=".xml", delete=False)
        try:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                tmp.write(chunk)
        finally:
            try:
                tmp.close()
            except Exception:
                pass
            try:
                r.close()
            except Exception:
                pass
        return tmp.name

    def iter_sitemap_urls(self, xml_path: str) -> Iterable[Tuple[str, Optional[datetime]]]:
        url_tag = "{http://www.sitemaps.org/schemas/sitemap/0.9}url"
        loc_tag = "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
        lastmod_tag = "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod"
        for _, elem in ET.iterparse(xml_path, events=("end",)):
            if elem.tag != url_tag:
                continue
            loc_el = elem.find(loc_tag)
            lastmod_el = elem.find(lastmod_tag)
            loc = (loc_el.text or "").strip() if loc_el is not None else ""
            lastmod = _parse_lastmod_iso((lastmod_el.text or "").strip() if lastmod_el is not None else None)
            if loc:
                yield loc, lastmod
            elem.clear()

    def fetch_skill_page_info(
        self, skill_url: str, *, max_bytes: int = 1024 * 1024
    ) -> Tuple[str, Optional[int], Optional[int]]:
        max_bytes = max(64 * 1024, int(max_bytes))
        max_bytes = min(max_bytes, 2 * 1024 * 1024)

        last_diag: Optional[str] = None
        for attempt in range(self._max_attempts):
            should_retry = False
            r = self._request_with_backoff("GET", skill_url, stream=True, timeout=(10, 60))
            try:
                if "/skills/" not in (r.url or ""):
                    last_diag = f"unexpected redirect: {r.url}"
                    should_retry = True
                    continue

                buf = bytearray()
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    buf.extend(chunk)
                    if len(buf) >= max_bytes:
                        break

                    html_so_far = buf.decode("utf-8", errors="ignore")
                    github_tree = _extract_github_tree_url_from_skill_page(html_so_far)
                    if github_tree:
                        stars, forks = _extract_stars_forks_from_skill_page(html_so_far)
                        return github_tree, stars, forks

                html = bytes(buf).decode("utf-8", errors="ignore")
                if _looks_like_cloudflare_challenge(html):
                    last_diag = "cloudflare_challenge"
                    should_retry = True
                    continue

                github_tree = _extract_github_tree_url_from_skill_page(html)
                if not github_tree:
                    last_diag = "githubUrl not found in skill page"
                    should_retry = True
                    continue
                stars, forks = _extract_stars_forks_from_skill_page(html)
                return github_tree, stars, forks
            finally:
                try:
                    r.close()
                except Exception:
                    pass
            if should_retry and (attempt + 1) < self._max_attempts:
                time.sleep(min(2.0 ** (attempt + 1), 20.0))
        raise RuntimeError(last_diag or "githubUrl not found in skill page")

    def fetch_github_contents(self, *, owner: str, repo: str, path: str, branch: str) -> List[Dict[str, Any]]:
        url = f"{self._base_url}/api/github-contents"
        r = self._request_with_backoff(
            "GET",
            url,
            params={"owner": owner, "repo": repo, "path": path, "branch": branch},
            timeout=(10, 120),
        )
        payload = r.json()
        files = payload.get("files")
        if not isinstance(files, list):
            raise RuntimeError(f"invalid github-contents response: {str(payload)[:200]}")
        return [x for x in files if isinstance(x, dict)]


def _pg_config_from_args(args: argparse.Namespace) -> PgConfig:
    if args.pg_dsn:
        return PgConfig(dsn=str(args.pg_dsn))
    host = str(args.pg_host)
    port = int(args.pg_port)
    db = str(args.pg_db)
    user = str(args.pg_user)
    pwd = str(args.pg_password)
    dsn = f"host={host} port={port} dbname={db} user={user} password={pwd}"
    return PgConfig(dsn=dsn)


def _oss_config_from_args(args: argparse.Namespace) -> OssConfig:
    return OssConfig(region=str(args.oss_region), endpoint=str(args.oss_endpoint), bucket=str(args.oss_bucket))


def _select_targets_from_sitemaps(
    client: SkillsMpClient,
    *,
    sitemap_index_url: str,
    latest_limit: int,
    author_openclaw: Optional[str],
    sitemap_max: int,
) -> Tuple[List[Tuple[str, Optional[datetime]]], List[Tuple[str, Optional[datetime]]]]:
    sitemap_urls = client.fetch_sitemap_index(sitemap_index_url)
    if int(sitemap_max) > 0:
        sitemap_urls = sitemap_urls[: int(sitemap_max)]
    latest_k = max(0, int(latest_limit))
    heap: List[Tuple[float, str, Optional[datetime]]] = []
    openclaw: List[Tuple[str, Optional[datetime]]] = []
    prefix = None
    if author_openclaw:
        prefix = f"{client._base_url}/skills/{author_openclaw.strip()}-"
    for sm_url in sitemap_urls:
        if not sm_url or "/sitemaps/" not in sm_url:
            continue
        xml_path = client.download_to_tempfile(sm_url)
        try:
            for loc, lastmod in client.iter_sitemap_urls(xml_path):
                if not loc.startswith(f"{client._base_url}/skills/"):
                    continue
                if prefix and loc.startswith(prefix):
                    openclaw.append((loc, lastmod))
                if latest_k <= 0:
                    continue
                ts = (lastmod.timestamp() if lastmod else 0.0) if lastmod else 0.0
                if len(heap) < latest_k:
                    heapq.heappush(heap, (ts, loc, lastmod))
                else:
                    if ts > heap[0][0]:
                        heapq.heapreplace(heap, (ts, loc, lastmod))
        finally:
            try:
                os.unlink(xml_path)
            except Exception:
                pass
    latest = [(loc, lastmod) for _, loc, lastmod in heap]
    latest.sort(key=lambda x: (x[1].timestamp() if x[1] else 0.0), reverse=True)
    openclaw.sort(key=lambda x: (x[1].timestamp() if x[1] else 0.0), reverse=True)
    return latest, openclaw


def fetch_skillsmp(
    *,
    pg_cfg: PgConfig,
    oss_cfg: OssConfig,
    sitemap_index_url: str,
    latest_limit: int,
    author_openclaw: Optional[str],
    sitemap_max: int,
    concurrency: int,
    skip_if_uploaded: bool,
    list_only: bool,
    skillsmp_rate_limit_qps: float,
    target_offset: int,
    target_count: int,
) -> None:
    concurrency = max(1, int(concurrency))
    rate_qps = max(0.0, float(skillsmp_rate_limit_qps))
    client = SkillsMpClient()
    pg_main = Pg(pg_cfg)
    try:
        latest, openclaw = _select_targets_from_sitemaps(
            client,
            sitemap_index_url=sitemap_index_url,
            latest_limit=latest_limit,
            author_openclaw=author_openclaw,
            sitemap_max=sitemap_max,
        )

        latest_ids = {_skill_id_from_skill_url(u) for u, _ in latest}
        targets: List[Tuple[str, Optional[datetime], bool, bool]] = []
        for u, lm in latest:
            targets.append((u, lm, True, False))
        for u, lm in openclaw:
            sid = _skill_id_from_skill_url(u)
            targets.append((u, lm, sid in latest_ids, True))

        dedup: Dict[str, Tuple[str, Optional[datetime], bool, bool]] = {}
        for u, lm, sel_latest, sel_openclaw in targets:
            sid = _skill_id_from_skill_url(u)
            old = dedup.get(sid)
            if old is None:
                dedup[sid] = (u, lm, sel_latest, sel_openclaw)
            else:
                uu, llm, a, b = old
                best_lm = llm
                if lm and (not llm or lm > llm):
                    best_lm = lm
                dedup[sid] = (uu or u, best_lm, a or sel_latest, b or sel_openclaw)

        items = [(sid, *dedup[sid]) for sid in dedup.keys()]
        items.sort(key=lambda x: (x[2].timestamp() if x[2] else 0.0), reverse=True)
        offset = max(0, int(target_offset))
        if int(target_count) > 0:
            items = items[offset : offset + int(target_count)]
        else:
            items = items[offset:]

        print(
            _json_dumps(
                {
                    "event": "skillsmp_selected",
                    "latest_limit": int(latest_limit),
                    "latest_count": len(latest),
                    "openclaw_count": len(openclaw),
                    "total_unique": len(items),
                    "target_offset": offset,
                    "target_count": int(target_count),
                }
            )
        )

        if list_only:
            return

        uploaded: Optional[set] = None
        if skip_if_uploaded:
            uploaded = set(pg_main.get_uploaded_skill_ids())

        local = threading.local()
        rate_lock = threading.Lock()
        last_req_at = {"t": 0.0}

        def _sleep_rate_limit() -> None:
            if rate_qps <= 0:
                return
            min_gap = 1.0 / rate_qps
            with rate_lock:
                now = time.time()
                gap = now - float(last_req_at["t"])
                if gap < min_gap:
                    time.sleep(min_gap - gap)
                last_req_at["t"] = time.time()

        def _get_pg() -> Pg:
            p = getattr(local, "pg", None)
            if p is None:
                p = Pg(pg_cfg)
                setattr(local, "pg", p)
            return p

        def _get_oss() -> OssUploader:
            o = getattr(local, "oss", None)
            if o is None:
                o = OssUploader(oss_cfg)
                setattr(local, "oss", o)
            return o

        def _get_client() -> SkillsMpClient:
            c = getattr(local, "client", None)
            if c is None:
                c = SkillsMpClient()
                setattr(local, "client", c)
            return c

        def _process_one(sid: str, skill_url: str, lastmod: Optional[datetime], sel_latest: bool, sel_openclaw: bool) -> Dict[str, Any]:
            if uploaded is not None and sid in uploaded:
                return {"skill_id": sid, "status": "skipped_uploaded"}
            pg = _get_pg()
            oss = _get_oss()
            c = _get_client()
            try:
                _sleep_rate_limit()
                github_tree, stars_count, forks_count = c.fetch_skill_page_info(skill_url)
                parsed = _parse_github_tree_url(github_tree)
                if not parsed:
                    raise RuntimeError(f"invalid github tree url: {github_tree}")
                owner, repo, branch, path = parsed
                prefix = oss.object_prefix_for_skill(skill_id=sid, github_owner=owner, github_repo=repo)
                pg.upsert_skill(
                    skill_id=sid,
                    skill_url=skill_url,
                    lastmod_utc=lastmod,
                    github_url=github_tree,
                    github_owner=owner,
                    github_repo=repo,
                    github_branch=branch,
                    github_path=path,
                    stars_count=stars_count,
                    forks_count=forks_count,
                    last_error=None,
                )
                pg.ensure_artifact_row(skill_id=sid, oss_prefix=prefix, skillsmp_download_url=skill_url)
                pg.commit()

                _sleep_rate_limit()
                files = c.fetch_github_contents(owner=owner, repo=repo, path=path, branch=branch)
                pg.mark_artifact_downloaded(skill_id=sid, skillsmp_download_url=skill_url)
                pg.commit()
                artifact_sha = _artifact_hash_for_files(files)

                count = 0
                for f in files:
                    rel = _safe_posix_path(str(f.get("path") or ""))
                    if not rel:
                        continue
                    raw = f.get("content")
                    if raw is None:
                        continue
                    if isinstance(raw, str):
                        data = raw.encode("utf-8")
                    elif isinstance(raw, (bytes, bytearray)):
                        data = bytes(raw)
                    elif isinstance(raw, dict) and isinstance(raw.get("base64"), str):
                        import base64

                        data = base64.b64decode(raw.get("base64") or "")
                    else:
                        data = str(raw).encode("utf-8")
                    key = f"{prefix}/{rel}"
                    oss.put_bytes(key, data)
                    count += 1

                pg.mark_artifact_uploaded(skill_id=sid, file_count=count, artifact_sha256=artifact_sha)
                pg.commit()
                if uploaded is not None:
                    uploaded.add(sid)
                return {"skill_id": sid, "status": "uploaded", "file_count": count, "artifact_sha256": artifact_sha}
            except Exception as e:
                err = str(e)
                try:
                    pg.upsert_skill(
                        skill_id=sid,
                        skill_url=skill_url,
                        lastmod_utc=lastmod,
                        github_url=None,
                        github_owner=None,
                        github_repo=None,
                        github_branch=None,
                        github_path=None,
                        stars_count=None,
                        forks_count=None,
                        last_error=err[:2000],
                    )
                    pg.ensure_artifact_row(
                        skill_id=sid,
                        oss_prefix=f"skillsmp/_unknown/{pathname2url(sid)}",
                        skillsmp_download_url=skill_url,
                    )
                    pg.mark_artifact_error(skill_id=sid, error=err[:2000])
                    pg.commit()
                except Exception:
                    try:
                        pg.rollback()
                    except Exception:
                        pass
                return {"skill_id": sid, "status": "error", "error": err}

        total = len(items)
        done = 0
        errors = 0
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futs: List[Future] = []
            for sid, u, lm, sel_latest, sel_openclaw in items:
                futs.append(ex.submit(_process_one, sid, u, lm, bool(sel_latest), bool(sel_openclaw)))
            for fut in as_completed(futs):
                res = fut.result()
                done += 1
                if res.get("status") == "error":
                    errors += 1
                if done % 100 == 0 or res.get("status") in ("error",):
                    print(
                        _json_dumps(
                            {
                                "event": "skillsmp_progress",
                                "done": done,
                                "total": total,
                                "errors": errors,
                                "last": res,
                            }
                        )
                    )
    finally:
        try:
            client.close()
        except Exception:
            pass
        try:
            pg_main.close()
        except Exception:
            pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="fetch_skillsmp_skills.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    fetch = sub.add_parser("fetch")
    fetch.add_argument("--sitemap-index-url", default="https://skillsmp.com/sitemap.xml")
    fetch.add_argument("--sitemap-max", type=int, default=0)
    fetch.add_argument("--latest-limit", type=int, default=100000)
    fetch.add_argument("--author-openclaw", default="openclaw")
    fetch.add_argument("--concurrency", type=int, default=4)
    fetch.add_argument("--skip-if-uploaded", action="store_true", default=False)
    fetch.add_argument("--list-only", action="store_true", default=False)
    fetch.add_argument("--skillsmp-qps", type=float, default=1.0)
    fetch.add_argument("--target-offset", type=int, default=0)
    fetch.add_argument("--target-count", type=int, default=0)

    fetch.add_argument("--pg-dsn", default=None)
    fetch.add_argument("--pg-host", default="47.104.149.68")
    fetch.add_argument("--pg-port", default=5432, type=int)
    fetch.add_argument("--pg-db", default="postgres")
    fetch.add_argument("--pg-user", default="postgres")
    fetch.add_argument("--pg-password", required=True)

    fetch.add_argument("--oss-region", required=True)
    fetch.add_argument("--oss-endpoint", required=True)
    fetch.add_argument("--oss-bucket", default="agent-skill-bucket")

    args = parser.parse_args(argv)
    if args.cmd == "fetch":
        fetch_skillsmp(
            pg_cfg=_pg_config_from_args(args),
            oss_cfg=_oss_config_from_args(args),
            sitemap_index_url=str(args.sitemap_index_url),
            latest_limit=int(args.latest_limit),
            author_openclaw=(str(args.author_openclaw).strip() if args.author_openclaw is not None else None) or None,
            sitemap_max=int(args.sitemap_max),
            concurrency=int(args.concurrency),
            skip_if_uploaded=bool(args.skip_if_uploaded),
            list_only=bool(args.list_only),
            skillsmp_rate_limit_qps=float(args.skillsmp_qps),
            target_offset=int(args.target_offset),
            target_count=int(args.target_count),
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
