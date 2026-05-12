import argparse
import hashlib
import json
import os
import tempfile
import time
import threading
import zipfile
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin
from urllib.request import pathname2url

import requests


def _try_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        return


def _utc_from_ms(ms: Optional[int]) -> Optional[datetime]:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _now_local() -> datetime:
    return datetime.now().astimezone()


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
        slug: str,
        display_name: str,
        summary: Optional[str],
        owner_handle: Optional[str],
        owner_user_id: Optional[str],
        owner_display_name: Optional[str],
        source_url: Optional[str],
        os_value: Optional[str],
        created_at: Optional[datetime],
        updated_at: Optional[datetime],
        comments_count: Optional[int],
        downloads_count: Optional[int],
        installs_all_time: Optional[int],
        installs_current: Optional[int],
        stars_count: Optional[int],
        versions_count: Optional[int],
        latest_version: Optional[str],
        latest_version_created_at: Optional[datetime],
        latest_version_license: Optional[str],
        latest_version_changelog: Optional[str],
    ) -> None:
        sql = """
        INSERT INTO clawhub_skill (
          slug,
          display_name,
          summary,
          owner_handle,
          owner_user_id,
          owner_display_name,
          source_url,
          os,
          created_at,
          updated_at,
          comments_count,
          downloads_count,
          installs_all_time,
          installs_current,
          stars_count,
          versions_count,
          latest_version,
          latest_version_created_at,
          latest_version_license,
          latest_version_changelog,
          fetched_at,
          detail_fetched_at,
          last_error
        ) VALUES (
          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL
        )
        ON CONFLICT (slug) DO UPDATE SET
          display_name = EXCLUDED.display_name,
          summary = EXCLUDED.summary,
          owner_handle = EXCLUDED.owner_handle,
          owner_user_id = EXCLUDED.owner_user_id,
          owner_display_name = EXCLUDED.owner_display_name,
          source_url = EXCLUDED.source_url,
          os = EXCLUDED.os,
          created_at = COALESCE(clawhub_skill.created_at, EXCLUDED.created_at),
          updated_at = GREATEST(COALESCE(clawhub_skill.updated_at, EXCLUDED.updated_at), EXCLUDED.updated_at),
          comments_count = EXCLUDED.comments_count,
          downloads_count = EXCLUDED.downloads_count,
          installs_all_time = EXCLUDED.installs_all_time,
          installs_current = EXCLUDED.installs_current,
          stars_count = EXCLUDED.stars_count,
          versions_count = EXCLUDED.versions_count,
          latest_version = EXCLUDED.latest_version,
          latest_version_created_at = EXCLUDED.latest_version_created_at,
          latest_version_license = EXCLUDED.latest_version_license,
          latest_version_changelog = EXCLUDED.latest_version_changelog,
          fetched_at = EXCLUDED.fetched_at,
          detail_fetched_at = EXCLUDED.detail_fetched_at,
          last_error = NULL
        """
        now = _now_local()
        self.execute(
            sql,
            (
                slug,
                display_name,
                summary,
                owner_handle,
                owner_user_id,
                owner_display_name,
                source_url,
                os_value,
                created_at,
                updated_at,
                comments_count,
                downloads_count,
                installs_all_time,
                installs_current,
                stars_count,
                versions_count,
                latest_version,
                latest_version_created_at,
                latest_version_license,
                latest_version_changelog,
                now,
                now,
            ),
        )

    def update_skill_latest_from_version(
        self,
        *,
        slug: str,
        latest_version: str,
        latest_version_created_at: Optional[datetime],
        latest_version_license: Optional[str],
        latest_version_changelog: Optional[str],
    ) -> None:
        sql = """
        UPDATE clawhub_skill
        SET
          latest_version = %s,
          latest_version_created_at = %s,
          latest_version_license = %s,
          latest_version_changelog = %s
        WHERE slug = %s
        """
        self.execute(
            sql,
            (
                latest_version,
                latest_version_created_at,
                latest_version_license,
                latest_version_changelog,
                slug,
            ),
        )

    def upsert_skill_version(
        self,
        *,
        slug: str,
        version: str,
        created_at: Optional[datetime],
        license_value: Optional[str],
        changelog: Optional[str],
        virustotal_verdict: Optional[str],
        virustotal_summary: Optional[str],
        clawscan_verdict: Optional[str],
        clawscan_summary: Optional[str],
        static_analysis_verdict: Optional[str],
        static_analysis_summary: Optional[str],
    ) -> None:
        sql = """
        INSERT INTO clawhub_skill_version (
          skill_slug,
          version,
          created_at,
          license,
          changelog,
          virustotal_verdict,
          virustotal_summary,
          clawscan_verdict,
          clawscan_summary,
          static_analysis_verdict,
          static_analysis_summary,
          fetched_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (skill_slug, version) DO UPDATE SET
          created_at = COALESCE(clawhub_skill_version.created_at, EXCLUDED.created_at),
          license = COALESCE(EXCLUDED.license, clawhub_skill_version.license),
          changelog = COALESCE(EXCLUDED.changelog, clawhub_skill_version.changelog),
          virustotal_verdict = COALESCE(EXCLUDED.virustotal_verdict, clawhub_skill_version.virustotal_verdict),
          virustotal_summary = COALESCE(EXCLUDED.virustotal_summary, clawhub_skill_version.virustotal_summary),
          clawscan_verdict = COALESCE(EXCLUDED.clawscan_verdict, clawhub_skill_version.clawscan_verdict),
          clawscan_summary = COALESCE(EXCLUDED.clawscan_summary, clawhub_skill_version.clawscan_summary),
          static_analysis_verdict = COALESCE(EXCLUDED.static_analysis_verdict, clawhub_skill_version.static_analysis_verdict),
          static_analysis_summary = COALESCE(EXCLUDED.static_analysis_summary, clawhub_skill_version.static_analysis_summary),
          fetched_at = EXCLUDED.fetched_at
        """
        self.execute(
            sql,
            (
                slug,
                version,
                created_at,
                license_value,
                changelog,
                virustotal_verdict,
                virustotal_summary,
                clawscan_verdict,
                clawscan_summary,
                static_analysis_verdict,
                static_analysis_summary,
                _now_local(),
            ),
        )

    def update_version_sha256(self, *, slug: str, version: str, sha256: str) -> None:
        sql = """
        UPDATE clawhub_skill_version
        SET sha256 = %s
        WHERE skill_slug = %s AND version = %s
        """
        self.execute(sql, (sha256, slug, version))

    def mark_skill_error(self, slug: str, error: str) -> None:
        sql = """
        UPDATE clawhub_skill
        SET last_error = %s
        WHERE slug = %s
        """
        self.execute(sql, (error[:4000], slug))

    def ensure_artifact_row(self, slug: str, version: str, download_url: str) -> None:
        sql = """
        INSERT INTO clawhub_skill_artifact (
          skill_slug, version, download_url, status, created_at
        ) VALUES (%s,%s,%s,'pending',%s)
        ON CONFLICT (skill_slug, version) DO NOTHING
        """
        self.execute(sql, (slug, version, download_url, _now_local()))

    def update_artifact_uploaded(
        self,
        slug: str,
        version: str,
        download_url: str,
        content_type: Optional[str],
        size_bytes: int,
        oss_bucket: str,
        oss_key: str,
        oss_etag: Optional[str],
    ) -> None:
        sql = """
        UPDATE clawhub_skill_artifact
        SET
          download_url = %s,
          content_type = %s,
          size_bytes = %s,
          oss_bucket = %s,
          oss_key = %s,
          oss_etag = %s,
          downloaded_at = %s,
          uploaded_at = %s,
          status = 'uploaded',
          last_error = NULL
        WHERE skill_slug = %s AND version = %s
        """
        now = _now_local()
        self.execute(
            sql,
            (
                download_url,
                content_type,
                size_bytes,
                oss_bucket,
                oss_key,
                oss_etag,
                now,
                now,
                slug,
                version,
            ),
        )

    def mark_artifact_error(self, slug: str, version: str, error: str) -> None:
        sql = """
        UPDATE clawhub_skill_artifact
        SET
          status = 'error',
          last_error = %s,
          updated_at = %s
        WHERE skill_slug = %s AND version = %s
        """
        self.execute(sql, (error[:4000], _now_local(), slug, version))

    def get_pending_artifacts(self, limit: int) -> List[Tuple[str, str, str]]:
        sql = """
        SELECT a.skill_slug, a.version, a.download_url
        FROM clawhub_skill_artifact a
        WHERE a.status IN ('pending', 'error')
        ORDER BY COALESCE(a.updated_at, a.created_at) ASC
        LIMIT %s
        """
        return [(r[0], r[1], r[2]) for r in self.fetchall(sql, (limit,))]

    def get_artifact_status(self, slug: str, version: str) -> Optional[str]:
        sql = """
        SELECT status
        FROM clawhub_skill_artifact
        WHERE skill_slug = %s AND version = %s
        """
        rows = self.fetchall(sql, (slug, version))
        if not rows:
            return None
        return rows[0][0]

    def get_cached_skill_owner(self, slug: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        sql = """
        SELECT owner_handle, owner_user_id, owner_display_name
        FROM clawhub_skill
        WHERE slug = %s
        """
        rows = self.fetchall(sql, (slug,))
        if not rows:
            return (None, None, None)
        return (rows[0][0], rows[0][1], rows[0][2])

    def is_version_detail_complete(self, slug: str, version: str) -> bool:
        sql = """
        SELECT 1
        FROM clawhub_skill_version
        WHERE skill_slug = %s
          AND version = %s
        LIMIT 1
        """
        return bool(self.fetchall(sql, (slug, version)))

    def should_skip_skill(
        self,
        *,
        slug: str,
        latest_version: Optional[str],
        expected_versions_count: Optional[int],
    ) -> Tuple[bool, Dict[str, Any]]:
        diag: Dict[str, Any] = {
            "slug": slug,
            "api_latest_version": latest_version,
            "expected_versions_count": expected_versions_count,
        }
        rows = self.fetchall(
            "SELECT latest_version FROM clawhub_skill WHERE slug = %s",
            (slug,),
        )
        if not rows:
            diag["db_skill_row"] = False
            return (False, diag)
        diag["db_skill_row"] = True
        db_latest = rows[0][0]
        diag["db_latest_version"] = str(db_latest) if db_latest is not None else None

        latest_match = True
        if latest_version:
            latest_match = bool(db_latest) and str(db_latest) == str(latest_version)
        else:
            latest_match = bool(db_latest)
        diag["latest_match"] = latest_match
        if not latest_match:
            return (False, diag)

        rows2 = self.fetchall(
            "SELECT COUNT(*), COALESCE(SUM(CASE WHEN status IS DISTINCT FROM 'uploaded' THEN 1 ELSE 0 END), 0) FROM clawhub_skill_artifact WHERE skill_slug = %s",
            (slug,),
        )
        artifact_total = int(rows2[0][0]) if rows2 else 0
        artifact_bad = int(rows2[0][1]) if rows2 else 0
        diag["artifact_total"] = artifact_total
        diag["artifact_pending_or_error"] = artifact_bad
        if artifact_total <= 0 or artifact_bad > 0:
            return (False, diag)

        rows3 = self.fetchall(
            "SELECT COUNT(*) FROM clawhub_skill_version WHERE skill_slug = %s",
            (slug,),
        )
        version_total = int(rows3[0][0]) if rows3 else 0
        diag["version_total"] = version_total
        if version_total < artifact_total:
            return (False, diag)

        rows4 = self.fetchall(
            """
            SELECT COUNT(*)
            FROM clawhub_skill_artifact a
            LEFT JOIN clawhub_skill_version v
              ON v.skill_slug = a.skill_slug AND v.version = a.version
            WHERE a.skill_slug = %s
              AND v.skill_slug IS NULL
            """,
            (slug,),
        )
        missing_version_rows = int(rows4[0][0]) if rows4 else 0
        diag["missing_version_rows"] = missing_version_rows
        if missing_version_rows > 0:
            return (False, diag)

        if expected_versions_count is not None and int(expected_versions_count) > 0:
            exp = int(expected_versions_count)
            diag["expected_versions_count_int"] = exp
            if artifact_total < exp or version_total < exp:
                return (False, diag)

        return (True, diag)


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

    def object_prefix_for_skill(self, slug: str, version: str) -> str:
        return f"clawhub/{slug}/{version}"

    def put_bytes(self, key: str, data: bytes) -> Optional[str]:
        result = self._client.put_object(
            self._oss.PutObjectRequest(bucket=self._cfg.bucket, key=key, body=data)
        )
        return getattr(result, "etag", None)

    def upload_zip_extracted(self, zip_path: str, slug: str, version: str) -> Tuple[int, Optional[str]]:
        prefix = self.object_prefix_for_skill(slug, version)
        count = 0
        last_etag: Optional[str] = None
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                name = (info.filename or "").replace("\\", "/")
                if not name or name.endswith("/"):
                    continue
                p = PurePosixPath(name)
                if p.is_absolute() or ".." in p.parts:
                    continue
                key = f"{prefix}/{p.as_posix()}"
                data = zf.read(info)
                last_etag = self.put_bytes(key, data) or last_etag
                count += 1
        return count, last_etag


class ClawHubClient:
    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()
        self._base = "https://clawhub.ai"
        self._api_base = urljoin(self._base, "/api/v1/")
        self._session.headers.update(
            {
                "User-Agent": "skill-security-service/1.0 (fetchskill; +https://github.com/)",
                "Accept": "application/json, text/plain, */*",
            }
        )

    def _request_json(
        self, method: str, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = urljoin(self._api_base, path.lstrip("/"))
        resp = self._request_with_backoff(method, url, params=params)
        return resp.json()

    def _request_with_backoff(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        timeout: int = 60,
        max_retries: int = 12,
    ) -> requests.Response:
        attempt = 0
        while True:
            attempt += 1
            resp = self._session.request(
                method,
                url,
                params=params,
                timeout=timeout,
                stream=stream,
            )
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait_s = int(retry_after) if retry_after and retry_after.isdigit() else min(60, 2**attempt)
                resp.close()
                time.sleep(max(1, wait_s))
                if attempt < max_retries:
                    continue
                raise RuntimeError(f"429 rate-limited after retries: {url}")
            if resp.status_code in (502, 503, 504):
                resp.close()
                time.sleep(min(60, 2**attempt))
                if attempt < max_retries:
                    continue
                raise RuntimeError(f"Upstream error {resp.status_code} after retries: {url}")
            if resp.status_code >= 400:
                body = None
                try:
                    body = resp.text
                except Exception:
                    body = None
                raise RuntimeError(f"HTTP {resp.status_code} {url} {body[:500] if body else ''}".strip())
            return resp

    def iter_skills(self, start_cursor: Optional[str] = None, max_pages: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        cursor = start_cursor
        pages = 0
        while True:
            params = {"cursor": cursor} if cursor else None
            data = self._request_json("GET", "skills", params=params)
            items = data.get("items") or []
            for it in items:
                if isinstance(it, dict):
                    yield it
            cursor = data.get("nextCursor")
            pages += 1
            if not cursor:
                break
            if max_pages is not None and pages >= max_pages:
                break

    def get_skill_detail(self, slug: str) -> Dict[str, Any]:
        return self._request_json("GET", f"skills/{pathname2url(slug)}")

    def get_skill_versions(self, slug: str) -> List[Dict[str, Any]]:
        cursor = None
        out: List[Dict[str, Any]] = []
        while True:
            params = {"cursor": cursor} if cursor else None
            data = self._request_json(
                "GET", f"skills/{pathname2url(slug)}/versions", params=params
            )
            items = data.get("items") or []
            out.extend([it for it in items if isinstance(it, dict)])
            cursor = data.get("nextCursor")
            if not cursor:
                break
        return out

    def get_skill_version_detail(self, slug: str, version: str) -> Dict[str, Any]:
        return self._request_json("GET", f"skills/{pathname2url(slug)}/versions/{pathname2url(version)}")

    def download_skill_zip(
        self, slug: str, version: str, target_path: str
    ) -> Tuple[str, int, Optional[str], str]:
        url = urljoin(self._api_base, "download")
        params = {"slug": slug, "version": version}
        sha = hashlib.sha256()
        size = 0
        resp = self._request_with_backoff("GET", url, params=params, stream=True, timeout=120)
        final_url = resp.url
        content_type = resp.headers.get("Content-Type")
        try:
            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    f.write(chunk)
                    sha.update(chunk)
                    size += len(chunk)
        finally:
            resp.close()
        return final_url, size, content_type, sha.hexdigest()


def _pg_config_from_args(args: argparse.Namespace) -> PgConfig:
    if getattr(args, "pg_dsn", None):
        return PgConfig(dsn=str(args.pg_dsn))
    host = str(args.pg_host)
    port = str(args.pg_port)
    user = str(args.pg_user)
    password = str(args.pg_password)
    dbname = str(args.pg_db)
    dsn = f"host={host} port={port} user={user} password={password} dbname={dbname}"
    return PgConfig(dsn=dsn)


def _oss_config_from_args(args: argparse.Namespace) -> OssConfig:
    region = str(args.oss_region)
    endpoint = str(args.oss_endpoint)
    bucket = str(args.oss_bucket)
    return OssConfig(region=region, endpoint=endpoint, bucket=bucket)


def _os_to_text(metadata: Any) -> Optional[str]:
    if not isinstance(metadata, dict):
        return None
    v = metadata.get("os")
    if not v:
        return None
    if isinstance(v, list):
        items = [str(x).strip() for x in v if x is not None and str(x).strip()]
        return ",".join(items) if items else None
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def _extract_security_fields(security: Any) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    if not isinstance(security, dict):
        return (None, None, None, None, None, None)
    scanners = security.get("scanners") or {}
    vt = scanners.get("vt") or {}
    llm = scanners.get("llm") or {}
    st = scanners.get("static") or {}
    vt_verdict = vt.get("verdict") or vt.get("status")
    vt_summary = vt.get("analysis")
    claw_verdict = llm.get("verdict") or llm.get("status")
    claw_summary = llm.get("summary")
    st_verdict = st.get("verdict") or st.get("status")
    st_summary = st.get("summary")
    return (
        str(vt_verdict) if vt_verdict is not None else None,
        str(vt_summary) if vt_summary is not None else None,
        str(claw_verdict) if claw_verdict is not None else None,
        str(claw_summary) if claw_summary is not None else None,
        str(st_verdict) if st_verdict is not None else None,
        str(st_summary) if st_summary is not None else None,
    )


@dataclass
class _WorkerContext:
    pg: Pg
    client: ClawHubClient
    uploader: OssUploader


def _process_one_skill(
    *,
    pg: Pg,
    client: ClawHubClient,
    uploader: OssUploader,
    item: Dict[str, Any],
    latest_version_value_hint: Optional[str],
    log_resume_checks: bool,
) -> Tuple[int, int, bool]:
    slug = item.get("slug")
    if not slug:
        return (0, 0, False)
    slug = str(slug)
    display_name_for_log = str(item.get("displayName") or slug)
    skill_started_at = _now_local()
    t0 = time.perf_counter()
    processed_versions = 0
    uploaded_versions = 0
    try:
        latest = item.get("latestVersion") or {}
        stats = item.get("stats") or {}
        latest_version_value = latest.get("version") or (item.get("tags") or {}).get("latest") or latest_version_value_hint
        skip, diag = pg.should_skip_skill(
            slug=slug,
            latest_version=str(latest_version_value) if latest_version_value is not None else None,
            expected_versions_count=stats.get("versions"),
        )
        if log_resume_checks:
            print(
                _json_dumps(
                    {
                        "event": "skill_resume_check",
                        "slug": slug,
                        "display_name": display_name_for_log,
                        "resume_check": diag,
                        "decision": "skip" if skip else "process",
                    }
                ),
                flush=True,
            )

        if skip:
            elapsed_s = time.perf_counter() - t0
            print(
                _json_dumps(
                    {
                        "event": "skill_skipped",
                        "slug": slug,
                        "display_name": display_name_for_log,
                        "started_at": skill_started_at.isoformat(),
                        "elapsed_seconds": round(elapsed_s, 3),
                        "reason": "already_fetched_and_uploaded",
                        "resume_check": diag,
                    }
                ),
                flush=True,
            )
            return (0, 0, True)

        cached_owner_handle, cached_owner_user_id, cached_owner_display_name = pg.get_cached_skill_owner(slug)
        detail: Dict[str, Any] = {}
        owner_handle = cached_owner_handle
        owner_user_id = cached_owner_user_id
        owner_display_name = cached_owner_display_name
        if not owner_handle:
            detail = client.get_skill_detail(slug)
            owner = detail.get("owner") or {}
            owner_handle = owner.get("handle")
            owner_user_id = owner.get("userId")
            owner_display_name = owner.get("displayName")
        source_url = f"https://clawhub.ai/{owner_handle}/{slug}" if owner_handle else None
        os_value = _os_to_text(item.get("metadata")) or _os_to_text(detail.get("metadata"))

        pg.upsert_skill(
            slug=slug,
            display_name=str(item.get("displayName") or slug),
            summary=item.get("summary"),
            owner_handle=str(owner_handle) if owner_handle is not None else None,
            owner_user_id=str(owner_user_id) if owner_user_id is not None else None,
            owner_display_name=str(owner_display_name) if owner_display_name is not None else None,
            source_url=source_url,
            os_value=os_value,
            created_at=_utc_from_ms(item.get("createdAt")),
            updated_at=_utc_from_ms(item.get("updatedAt")),
            comments_count=stats.get("comments"),
            downloads_count=stats.get("downloads"),
            installs_all_time=stats.get("installsAllTime"),
            installs_current=stats.get("installsCurrent"),
            stars_count=stats.get("stars"),
            versions_count=stats.get("versions"),
            latest_version=str(latest_version_value) if latest_version_value is not None else None,
            latest_version_created_at=_utc_from_ms(latest.get("createdAt")),
            latest_version_license=latest.get("license"),
            latest_version_changelog=latest.get("changelog"),
        )

        versions = client.get_skill_versions(slug)
        for v in versions:
            version_str = v.get("version")
            if not version_str:
                continue
            version_str = str(version_str)
            download_url = (
                f"https://clawhub.ai/api/v1/download?slug={requests.utils.quote(slug)}"
                f"&version={requests.utils.quote(version_str)}"
            )
            pg.ensure_artifact_row(slug, version_str, download_url)
            status = pg.get_artifact_status(slug, version_str)

            version_complete = pg.is_version_detail_complete(slug, version_str)
            if not version_complete:
                vdetail = client.get_skill_version_detail(slug, version_str)
                vobj = vdetail.get("version") or {}
                created_at = _utc_from_ms(vobj.get("createdAt"))
                license_value = vobj.get("license")
                changelog = vobj.get("changelog")
                security = vobj.get("security")
                vt_v, vt_s, oc_v, oc_s, st_v, st_s = _extract_security_fields(security)
                pg.upsert_skill_version(
                    slug=slug,
                    version=version_str,
                    created_at=created_at,
                    license_value=str(license_value) if license_value is not None else None,
                    changelog=str(changelog) if changelog is not None else None,
                    virustotal_verdict=vt_v,
                    virustotal_summary=vt_s,
                    clawscan_verdict=oc_v,
                    clawscan_summary=oc_s,
                    static_analysis_verdict=st_v,
                    static_analysis_summary=st_s,
                )
                if latest_version_value is not None and version_str == str(latest_version_value):
                    pg.update_skill_latest_from_version(
                        slug=slug,
                        latest_version=version_str,
                        latest_version_created_at=created_at,
                        latest_version_license=str(license_value) if license_value is not None else None,
                        latest_version_changelog=str(changelog) if changelog is not None else None,
                    )

            if status == "uploaded":
                processed_versions += 1
                continue

            with tempfile.TemporaryDirectory() as td:
                zip_path = os.path.join(td, f"{slug}-{version_str}.zip")
                url, size, content_type, sha256 = client.download_skill_zip(slug, version_str, zip_path)
                pg.update_version_sha256(slug=slug, version=version_str, sha256=sha256)
                _, last_etag = uploader.upload_zip_extracted(zip_path, slug, version_str)
                prefix = uploader.object_prefix_for_skill(slug, version_str)
                pg.update_artifact_uploaded(
                    slug=slug,
                    version=version_str,
                    download_url=url,
                    content_type=content_type,
                    size_bytes=size,
                    oss_bucket=uploader._cfg.bucket,
                    oss_key=prefix,
                    oss_etag=last_etag,
                )
                uploaded_versions += 1
            processed_versions += 1

        pg.commit()
        elapsed_s = time.perf_counter() - t0
        print(
            _json_dumps(
                {
                    "event": "skill_done",
                    "slug": slug,
                    "display_name": display_name_for_log,
                    "started_at": skill_started_at.isoformat(),
                    "elapsed_seconds": round(elapsed_s, 3),
                    "status": "ok",
                }
            ),
            flush=True,
        )
        return (processed_versions, uploaded_versions, False)
    except Exception as e:
        try:
            pg.rollback()
        except Exception:
            pass
        try:
            pg.mark_skill_error(slug, str(e))
            pg.commit()
        except Exception:
            try:
                pg.rollback()
            except Exception:
                pass
        elapsed_s = time.perf_counter() - t0
        print(
            _json_dumps(
                {
                    "event": "skill_done",
                    "slug": slug,
                    "display_name": display_name_for_log,
                    "started_at": skill_started_at.isoformat(),
                    "elapsed_seconds": round(elapsed_s, 3),
                    "status": "error",
                    "error": str(e)[:500],
                }
            ),
            flush=True,
        )
        return (0, 0, False)


def fetch_skills(
    *,
    pg_cfg: PgConfig,
    oss_cfg: OssConfig,
    skill_count: Union[int, str],
    start_cursor: Optional[str] = None,
    order_by: str = "downloads",
    order_dir: str = "desc",
    concurrency: int = 1,
    log_resume_checks: bool = False,
) -> Dict[str, int]:
    limit: Optional[int]
    if isinstance(skill_count, str):
        if skill_count.strip().lower() == "all":
            limit = None
        else:
            limit = int(skill_count)
    else:
        limit = int(skill_count)

    processed_skills = 0
    skipped_skills = 0
    processed_versions = 0
    uploaded_versions = 0

    cursor = start_cursor
    concurrency = max(1, int(concurrency))
    list_client = ClawHubClient()

    if concurrency <= 1:
        pg = Pg(pg_cfg)
        try:
            client = ClawHubClient()
            uploader = OssUploader(oss_cfg)
            while True:
                if limit is not None and processed_skills >= limit:
                    break
                params: Dict[str, Any] = {}
                if cursor:
                    params["cursor"] = cursor
                if order_by and order_by != "default":
                    params["sort"] = order_by
                    if order_dir:
                        params["dir"] = order_dir
                if not params:
                    params = None  # type: ignore[assignment]
                data = list_client._request_json("GET", "skills", params=params)
                items = data.get("items") or []
                for item in items:
                    if limit is not None and processed_skills >= limit:
                        break
                    if not isinstance(item, dict):
                        continue
                    vcnt, ucnt, skipped = _process_one_skill(
                        pg=pg,
                        client=client,
                        uploader=uploader,
                        item=item,
                        latest_version_value_hint=None,
                        log_resume_checks=bool(log_resume_checks),
                    )
                    if skipped:
                        skipped_skills += 1
                        continue
                    processed_skills += 1
                    processed_versions += vcnt
                    uploaded_versions += ucnt
                cursor = data.get("nextCursor")
                if not cursor:
                    break
        finally:
            pg.close()
    else:
        thread_local = threading.local()
        contexts: List[_WorkerContext] = []
        ctx_lock = threading.Lock()

        def _ctx() -> _WorkerContext:
            existing = getattr(thread_local, "ctx", None)
            if existing is not None:
                return existing
            ctx = _WorkerContext(pg=Pg(pg_cfg), client=ClawHubClient(), uploader=OssUploader(oss_cfg))
            thread_local.ctx = ctx
            with ctx_lock:
                contexts.append(ctx)
            return ctx

        def _run_item(it: Dict[str, Any]) -> Tuple[int, int, bool]:
            ctx = _ctx()
            return _process_one_skill(
                pg=ctx.pg,
                client=ctx.client,
                uploader=ctx.uploader,
                item=it,
                latest_version_value_hint=None,
                log_resume_checks=bool(log_resume_checks),
            )

        executor = ThreadPoolExecutor(max_workers=concurrency)
        inflight: Set[Future[Tuple[int, int, bool]]] = set()
        submitted = 0
        try:
            while True:
                if limit is not None and submitted >= limit:
                    break
                params2: Dict[str, Any] = {}
                if cursor:
                    params2["cursor"] = cursor
                if order_by and order_by != "default":
                    params2["sort"] = order_by
                    if order_dir:
                        params2["dir"] = order_dir
                if not params2:
                    params2 = None  # type: ignore[assignment]
                data2 = list_client._request_json("GET", "skills", params=params2)
                items2 = data2.get("items") or []
                for item in items2:
                    if limit is not None and submitted >= limit:
                        break
                    if not isinstance(item, dict):
                        continue
                    while len(inflight) >= concurrency * 2:
                        done, inflight = wait(inflight, return_when=FIRST_COMPLETED)
                        for f in done:
                            vcnt, ucnt, skipped = f.result()
                            if skipped:
                                skipped_skills += 1
                                continue
                            processed_skills += 1
                            processed_versions += vcnt
                            uploaded_versions += ucnt
                    inflight.add(executor.submit(_run_item, item))
                    submitted += 1

                cursor = data2.get("nextCursor")
                if not cursor:
                    break

            if inflight:
                done2, _ = wait(inflight)
                for f in done2:
                    vcnt, ucnt, skipped = f.result()
                    if skipped:
                        skipped_skills += 1
                        continue
                    processed_skills += 1
                    processed_versions += vcnt
                    uploaded_versions += ucnt
        finally:
            executor.shutdown(wait=True, cancel_futures=False)
            for c in contexts:
                c.pg.close()

    return {
        "skills": processed_skills,
        "skipped_skills": skipped_skills,
        "versions": processed_versions,
        "uploaded_versions": uploaded_versions,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fetch_clawhub_skills")
    p.add_argument("--pg-dsn", default=None)
    p.add_argument("--pg-host", default="47.104.149.68")
    p.add_argument("--pg-port", default="5432")
    p.add_argument("--pg-db", default="postgres")
    p.add_argument("--pg-user", default="postgres")
    p.add_argument("--pg-password", required=True)
    p.add_argument("--oss-region", default="cn-hangzhou")
    p.add_argument("--oss-endpoint", default="oss-cn-hangzhou.aliyuncs.com")
    p.add_argument("--oss-bucket", default="agent-skill-bucket")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch")
    p_fetch.add_argument("--count", default="all")
    p_fetch.add_argument("--start-cursor", default=None)
    p_fetch.add_argument("--order-by", default="downloads", choices=["downloads", "default"])
    p_fetch.add_argument("--order-dir", default="desc", choices=["desc", "asc"])
    p_fetch.add_argument("--concurrency", type=int, default=4, help="并发数（建议 2~6，过大容易被限流）")
    p_fetch.add_argument(
        "--log-resume-checks",
        action="store_true",
        help="输出每个 skill 的断点续跑判定信息（日志会很多）",
    )

    return p


def main(argv: Optional[List[str]] = None) -> int:
    _try_load_dotenv()
    args = build_arg_parser().parse_args(argv)
    try:
        if args.cmd == "fetch":
            result = fetch_skills(
                pg_cfg=_pg_config_from_args(args),
                oss_cfg=_oss_config_from_args(args),
                skill_count=args.count,
                start_cursor=args.start_cursor,
                order_by=args.order_by,
                order_dir=args.order_dir,
                concurrency=int(args.concurrency),
                log_resume_checks=bool(getattr(args, "log_resume_checks", False)),
            )
            print(_json_dumps(result))
            return 0

        raise RuntimeError(f"Unknown cmd: {args.cmd}")
    finally:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
