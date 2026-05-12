import argparse
import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
import zipfile
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse
from urllib.request import pathname2url

import requests


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _log(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    print(_json_dumps(payload), flush=True)


def _safe_posix_path(p: str) -> Optional[str]:
    s = (p or "").replace("\\", "/").lstrip("/")
    if not s:
        return None
    parts = [x for x in s.split("/") if x not in ("", ".")]
    if any(x == ".." for x in parts):
        return None
    return "/".join(parts)


def _utc_from_epoch(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    try:
        s = str(v).strip()
        if not s:
            return None
        ts = int(float(s))
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        return None


def _artifact_hash_for_files(file_entries: Sequence[Tuple[str, str]]) -> str:
    h = hashlib.sha256()
    items: List[Tuple[str, bytes]] = []
    for rel, abs_path in file_entries:
        rp = _safe_posix_path(rel)
        if not rp:
            continue
        try:
            with open(abs_path, "rb") as f:
                data = f.read()
        except Exception:
            continue
        items.append((rp, data))
    items.sort(key=lambda x: x[0])
    for rel, data in items:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(data).digest())
        h.update(b"\n")
    return h.hexdigest()


def _parse_github_tree_url(tree_url: str) -> Optional[Tuple[str, str, str, str]]:
    u = urlparse(tree_url)
    if u.netloc not in ("github.com", "www.github.com"):
        return None
    parts = [p for p in (u.path or "").split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    ref = "main"
    path = ""
    if len(parts) >= 4 and parts[2] in ("tree", "blob"):
        ref = parts[3]
        path = "/".join(parts[4:])
        if parts[2] == "blob":
            if "/" in path:
                path = path.rsplit("/", 1)[0]
            else:
                path = ""
    return owner, repo, ref, path


def _looks_like_hex_sha(s: str) -> bool:
    if len(s) not in (7, 8, 40):
        return False
    for ch in s:
        if ch not in "0123456789abcdefABCDEF":
            return False
    return True


def _candidate_repo_zip_urls(owner: str, repo: str, ref: str) -> List[str]:
    ref = (ref or "").strip()
    if not ref:
        ref = "main"
    if _looks_like_hex_sha(ref):
        return [
            f"https://codeload.github.com/{owner}/{repo}/zip/{ref}",
            f"https://github.com/{owner}/{repo}/archive/{ref}.zip",
        ]
    return [
        f"https://github.com/{owner}/{repo}/archive/refs/heads/{ref}.zip",
        f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{ref}",
        f"https://github.com/{owner}/{repo}/archive/refs/tags/{ref}.zip",
        f"https://codeload.github.com/{owner}/{repo}/zip/refs/tags/{ref}",
    ]


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
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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

    def mark_artifact_uploaded(self, *, skill_id: str, file_count: int, artifact_sha256: str) -> None:
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
        self.execute(sql, (_now_local(), error[:2000], skill_id))

    def get_artifact_status_map(self, *, skill_ids: Sequence[str]) -> Dict[str, Optional[str]]:
        if not skill_ids:
            return {}
        sql = """
        SELECT skill_id, status
        FROM skillsmp_skill_artifact
        WHERE skill_id = ANY(%s)
        """
        rows = self.fetchall(sql, (list(skill_ids),))
        return {str(r[0]): (str(r[1]) if r[1] is not None else None) for r in rows}


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

    def put_file(self, key: str, file_path: str) -> None:
        with open(file_path, "rb") as body:
            req = self._oss.PutObjectRequest(bucket=self._cfg.bucket, key=key, body=body)
            self._client.put_object(req)

    def object_prefix_for_skill(self, *, owner: str, repo: str, skill_id: str) -> str:
        safe_skill = pathname2url(skill_id)
        return f"skillsmp/{owner}/{repo}/{safe_skill}"


class HttpClient:
    def __init__(
        self,
        *,
        timeout_s: int = 20,
        max_attempts: int = 3,
        max_backoff_s: float = 10.0,
        use_proxy_env: bool = False,
    ):
        self._timeout_s = max(1, int(timeout_s))
        self._max_attempts = max(1, int(max_attempts))
        self._max_backoff_s = max(0.0, float(max_backoff_s))
        self._session = requests.Session()
        self._session.trust_env = bool(use_proxy_env)
        self._session.headers.update({"User-Agent": "skill-security-service/skillsmp-json-loader", "Accept": "*/*"})

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:
            return

    def request(self, method: str, url: str, *, stream: bool = False, timeout: Optional[object] = None) -> requests.Response:
        backoff = 1.0
        last_exc: Optional[Exception] = None
        for _ in range(self._max_attempts):
            try:
                r = self._session.request(
                    method,
                    url,
                    timeout=(self._timeout_s if timeout is None else timeout),
                    stream=stream,
                    allow_redirects=True,
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

    def download_to_file(self, url: str, out_path: str) -> None:
        r = self.request("GET", url, stream=True, timeout=(10, 120))
        try:
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    f.write(chunk)
        finally:
            try:
                r.close()
            except Exception:
                pass


def _safe_extract_zip(zip_path: str, out_dir: str) -> str:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            name = (info.filename or "").replace("\\", "/")
            if not name:
                continue
            if name.endswith("/"):
                continue
            rel = _safe_posix_path(name)
            if not rel:
                continue
            target = out.joinpath(*rel.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
    dirs = [p for p in out.iterdir() if p.is_dir()]
    if len(dirs) == 1:
        return str(dirs[0])
    return str(out)


def _iter_files_under(root_dir: str) -> List[Tuple[str, str]]:
    root = Path(root_dir)
    out: List[Tuple[str, str]] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        rp = _safe_posix_path(rel)
        if not rp:
            continue
        out.append((rp, str(p)))
    out.sort(key=lambda x: x[0])
    return out


def _load_skills_from_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items: List[Dict[str, Any]] = []
    if isinstance(data, list):
        items = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        for k in ("openclaw_skills", "non_openclaw_top_stars", "non_openclaw_top_recent"):
            v = data.get(k)
            if isinstance(v, list):
                items.extend([x for x in v if isinstance(x, dict)])
    dedup: Dict[str, Dict[str, Any]] = {}
    for it in items:
        sid = str(it.get("id") or "").strip()
        if not sid:
            continue
        old = dedup.get(sid)
        if old is None:
            dedup[sid] = dict(it)
        else:
            merged = dict(old)
            for kk, vv in it.items():
                if merged.get(kk) in (None, "", []) and vv not in (None, "", []):
                    merged[kk] = vv
            dedup[sid] = merged
    out = list(dedup.values())
    out.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return out


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


def handle_skillsmp(
    *,
    input_json: str,
    pg_cfg: PgConfig,
    oss_cfg: OssConfig,
    concurrency: int,
    repo_timeout_s: int,
    skip_if_uploaded: bool,
    list_only: bool,
    use_proxy_env: bool,
    target_offset: int,
    target_count: int,
) -> None:
    items = _load_skills_from_json(input_json)
    offset = max(0, int(target_offset))
    if int(target_count) > 0:
        items = items[offset : offset + int(target_count)]
    else:
        items = items[offset:]

    _log("skillsmp_json_loaded", count=len(items), offset=offset, target_count=int(target_count))

    if list_only:
        return

    pg_main = Pg(pg_cfg)
    http = HttpClient(use_proxy_env=use_proxy_env)
    try:
        status_map: Dict[str, Optional[str]] = {}
        if skip_if_uploaded:
            status_map = pg_main.get_artifact_status_map(skill_ids=[str(x.get("id") or "") for x in items])

        repos: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
        parse_failed = 0
        for it in items:
            sid = str(it.get("id") or "").strip()
            if not sid:
                continue
            if skip_if_uploaded and status_map.get(sid) == "uploaded":
                continue
            tree_url = str(it.get("download_url") or "").strip()
            parsed = _parse_github_tree_url(tree_url)
            if not parsed:
                parse_failed += 1
                continue
            owner, repo, ref, path = parsed
            k = (owner, repo, ref)
            repos.setdefault(k, []).append(it)

        _log("skillsmp_grouped", repo_groups=len(repos), parse_failed=parse_failed)

        local = threading.local()  # type: ignore[name-defined]

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

        def _download_and_extract_repo(owner: str, repo: str, ref: str, work_dir: str) -> str:
            zip_path = os.path.join(work_dir, "repo.zip")
            last_err: Optional[str] = None
            for url in _candidate_repo_zip_urls(owner, repo, ref):
                try:
                    http.download_to_file(url, zip_path)
                    return _safe_extract_zip(zip_path, os.path.join(work_dir, "repo"))
                except Exception as e:
                    last_err = str(e)
                    try:
                        if os.path.exists(zip_path):
                            os.unlink(zip_path)
                    except Exception:
                        pass
                    continue
            raise RuntimeError(last_err or "repo zip download failed")

        def _process_repo(owner: str, repo: str, ref: str, skills: List[Dict[str, Any]]) -> Dict[str, Any]:
            started = time.time()
            work_dir = tempfile.mkdtemp(prefix=f"skillsmp_repo_{owner}_{repo}_")
            pg = _get_pg()
            oss = _get_oss()
            try:
                _log("repo_start", repo=f"{owner}/{repo}", ref=ref, skills=len(skills))
                root = _download_and_extract_repo(owner, repo, ref, work_dir)
                _log("repo_ready", repo=f"{owner}/{repo}", ref=ref, root=root, elapsed_s=round(time.time() - started, 3))
                processed = 0
                uploaded = 0
                errors = 0
                for it in skills:
                    sid = str(it.get("id") or "").strip()
                    if not sid:
                        continue
                    if skip_if_uploaded and status_map.get(sid) == "uploaded":
                        _log("skill_skip_uploaded", skill_id=sid, repo=f"{owner}/{repo}", ref=ref)
                        continue
                    skill_started = time.time()
                    skill_url = str(it.get("official_url") or "").strip()
                    stars = it.get("stars")
                    updated = _utc_from_epoch(it.get("updated_at"))
                    tree_url = str(it.get("download_url") or "").strip()
                    parsed = _parse_github_tree_url(tree_url)
                    if not parsed:
                        err = "invalid download_url"
                        _log("skill_error", skill_id=sid, repo=f"{owner}/{repo}", ref=ref, stage="parse_download_url", error=err, download_url=tree_url)
                        pg.upsert_skill(
                            skill_id=sid,
                            skill_url=skill_url or f"https://skillsmp.com/skills/{sid}",
                            lastmod_utc=updated,
                            github_url=tree_url or None,
                            github_owner=None,
                            github_repo=None,
                            github_branch=None,
                            github_path=None,
                            stars_count=(int(stars) if str(stars).isdigit() else None),
                            forks_count=None,
                            last_error=err,
                        )
                        pg.ensure_artifact_row(
                            skill_id=sid,
                            oss_prefix=f"skillsmp/_unknown/{pathname2url(sid)}",
                            skillsmp_download_url=skill_url or None,
                        )
                        pg.mark_artifact_error(skill_id=sid, error=err)
                        pg.commit()
                        processed += 1
                        errors += 1
                        continue
                    _, _, _, sub_path = parsed

                    prefix = oss.object_prefix_for_skill(owner=owner, repo=repo, skill_id=sid)
                    _log(
                        "skill_start",
                        skill_id=sid,
                        repo=f"{owner}/{repo}",
                        ref=ref,
                        github_path=sub_path,
                        oss_prefix=prefix,
                        official_url=(skill_url or None),
                    )
                    pg.upsert_skill(
                        skill_id=sid,
                        skill_url=skill_url or f"https://skillsmp.com/skills/{sid}",
                        lastmod_utc=updated,
                        github_url=tree_url or None,
                        github_owner=owner,
                        github_repo=repo,
                        github_branch=ref,
                        github_path=sub_path or None,
                        stars_count=(int(stars) if str(stars).isdigit() else None),
                        forks_count=None,
                        last_error=None,
                    )
                    pg.ensure_artifact_row(skill_id=sid, oss_prefix=prefix, skillsmp_download_url=(skill_url or None))
                    pg.commit()

                    skill_root = os.path.join(root, *[p for p in sub_path.split("/") if p])
                    if not os.path.isdir(skill_root):
                        err = f"skill path not found in repo: {sub_path}"
                        _log("skill_error", skill_id=sid, repo=f"{owner}/{repo}", ref=ref, stage="locate_skill_dir", error=err)
                        pg.mark_artifact_error(skill_id=sid, error=err)
                        pg.commit()
                        processed += 1
                        errors += 1
                        continue

                    pg.mark_artifact_downloaded(skill_id=sid, skillsmp_download_url=(skill_url or None))
                    pg.commit()

                    file_entries = _iter_files_under(skill_root)
                    artifact_sha = _artifact_hash_for_files(file_entries)
                    _log(
                        "skill_files_ready",
                        skill_id=sid,
                        repo=f"{owner}/{repo}",
                        ref=ref,
                        file_count=len(file_entries),
                        artifact_sha256=artifact_sha,
                    )
                    count = 0
                    for rel, abs_path in file_entries:
                        key = f"{prefix}/{rel}"
                        oss.put_file(key, abs_path)
                        count += 1

                    pg.mark_artifact_uploaded(skill_id=sid, file_count=count, artifact_sha256=artifact_sha)
                    pg.commit()
                    processed += 1
                    uploaded += 1
                    _log(
                        "skill_done",
                        skill_id=sid,
                        repo=f"{owner}/{repo}",
                        ref=ref,
                        status="uploaded",
                        file_count=count,
                        artifact_sha256=artifact_sha,
                        elapsed_s=round(time.time() - skill_started, 3),
                    )
                return {
                    "repo": f"{owner}/{repo}",
                    "ref": ref,
                    "processed": processed,
                    "uploaded": uploaded,
                    "errors": errors,
                    "elapsed_s": round(time.time() - started, 3),
                }
            finally:
                try:
                    shutil.rmtree(work_dir, ignore_errors=True)
                except Exception:
                    pass

        total_groups = len(repos)
        done_groups = 0
        repo_errors = 0
        with ThreadPoolExecutor(max_workers=max(1, int(concurrency))) as ex:
            futs: List[Future] = []
            for (owner, repo, ref), skills in repos.items():
                futs.append(ex.submit(_process_repo, owner, repo, ref, skills))
            for fut in as_completed(futs, timeout=None):
                done_groups += 1
                try:
                    res = fut.result(timeout=int(repo_timeout_s) if int(repo_timeout_s) > 0 else None)
                    if int(res.get("errors") or 0) > 0:
                        repo_errors += 1
                    _log(
                        "skillsmp_repo_progress",
                        done_groups=done_groups,
                        total_groups=total_groups,
                        repo_errors=repo_errors,
                        last=res,
                    )
                except Exception as e:
                    repo_errors += 1
                    _log("skillsmp_repo_failed", done_groups=done_groups, total_groups=total_groups, error=str(e))
    finally:
        try:
            http.close()
        except Exception:
            pass
        try:
            pg_main.close()
        except Exception:
            pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="handle_skillsmp_skills.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    fetch = sub.add_parser("fetch")
    fetch.add_argument("--input-json", required=True)
    fetch.add_argument("--concurrency", type=int, default=2)
    fetch.add_argument("--repo-timeout-s", type=int, default=1800)
    fetch.add_argument("--skip-if-uploaded", action="store_true", default=False)
    fetch.add_argument("--list-only", action="store_true", default=False)
    fetch.add_argument("--use-proxy-env", action="store_true", default=False)
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
        handle_skillsmp(
            input_json=str(args.input_json),
            pg_cfg=_pg_config_from_args(args),
            oss_cfg=_oss_config_from_args(args),
            concurrency=int(args.concurrency),
            repo_timeout_s=int(args.repo_timeout_s),
            skip_if_uploaded=bool(args.skip_if_uploaded),
            list_only=bool(args.list_only),
            use_proxy_env=bool(args.use_proxy_env),
            target_offset=int(args.target_offset),
            target_count=int(args.target_count),
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
