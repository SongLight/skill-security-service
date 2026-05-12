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
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import quote, urljoin
from urllib.request import pathname2url

import requests


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


def _parse_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    return None


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

    def fetchall(
        self, sql: str, params: Optional[Tuple[Any, ...]] = None
    ) -> List[Tuple[Any, ...]]:
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
        summary_zh: Optional[str],
        category: Optional[str],
        source: Optional[str],
        homepage_url: Optional[str],
        owner_handle: Optional[str],
        owner_display_name: Optional[str],
        requires_api_key: Optional[bool],
        score: Optional[float],
        created_at: Optional[datetime],
        updated_at: Optional[datetime],
        comments_count: Optional[int],
        downloads_count: Optional[int],
        installs_count: Optional[int],
        stars_count: Optional[int],
        versions_count: Optional[int],
        latest_version: Optional[str],
        latest_version_created_at: Optional[datetime],
        latest_version_changelog: Optional[str],
        keen_status: Optional[str],
        keen_status_text: Optional[str],
        keen_report_url: Optional[str],
        sanbu_status: Optional[str],
        sanbu_status_text: Optional[str],
        sanbu_report_url: Optional[str],
    ) -> None:
        sql = """
        INSERT INTO skillhub_skill (
          slug,
          display_name,
          summary,
          summary_zh,
          category,
          source,
          homepage_url,
          owner_handle,
          owner_display_name,
          requires_api_key,
          score,
          created_at,
          updated_at,
          comments_count,
          downloads_count,
          installs_count,
          stars_count,
          versions_count,
          latest_version,
          latest_version_created_at,
          latest_version_changelog,
          keen_status,
          keen_status_text,
          keen_report_url,
          sanbu_status,
          sanbu_status_text,
          sanbu_report_url,
          fetched_at,
          detail_fetched_at,
          last_error
        ) VALUES (
          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL
        )
        ON CONFLICT (slug) DO UPDATE SET
          display_name = EXCLUDED.display_name,
          summary = EXCLUDED.summary,
          summary_zh = EXCLUDED.summary_zh,
          category = EXCLUDED.category,
          source = EXCLUDED.source,
          homepage_url = EXCLUDED.homepage_url,
          owner_handle = EXCLUDED.owner_handle,
          owner_display_name = EXCLUDED.owner_display_name,
          requires_api_key = EXCLUDED.requires_api_key,
          score = EXCLUDED.score,
          created_at = COALESCE(skillhub_skill.created_at, EXCLUDED.created_at),
          updated_at = GREATEST(COALESCE(skillhub_skill.updated_at, EXCLUDED.updated_at), EXCLUDED.updated_at),
          comments_count = EXCLUDED.comments_count,
          downloads_count = EXCLUDED.downloads_count,
          installs_count = EXCLUDED.installs_count,
          stars_count = EXCLUDED.stars_count,
          versions_count = EXCLUDED.versions_count,
          latest_version = EXCLUDED.latest_version,
          latest_version_created_at = EXCLUDED.latest_version_created_at,
          latest_version_changelog = EXCLUDED.latest_version_changelog,
          keen_status = EXCLUDED.keen_status,
          keen_status_text = EXCLUDED.keen_status_text,
          keen_report_url = EXCLUDED.keen_report_url,
          sanbu_status = EXCLUDED.sanbu_status,
          sanbu_status_text = EXCLUDED.sanbu_status_text,
          sanbu_report_url = EXCLUDED.sanbu_report_url,
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
                summary_zh,
                category,
                source,
                homepage_url,
                owner_handle,
                owner_display_name,
                requires_api_key,
                score,
                created_at,
                updated_at,
                comments_count,
                downloads_count,
                installs_count,
                stars_count,
                versions_count,
                latest_version,
                latest_version_created_at,
                latest_version_changelog,
                keen_status,
                keen_status_text,
                keen_report_url,
                sanbu_status,
                sanbu_status_text,
                sanbu_report_url,
                now,
                now,
            ),
        )

    def upsert_skill_version(
        self,
        *,
        skill_slug: str,
        version: str,
        version_id: Optional[int],
        changelog: Optional[str],
        created_at: Optional[datetime],
        keen_status: Optional[str],
        keen_status_text: Optional[str],
        keen_report_url: Optional[str],
        sanbu_status: Optional[str],
        sanbu_status_text: Optional[str],
        sanbu_report_url: Optional[str],
    ) -> None:
        sql = """
        INSERT INTO skillhub_skill_version (
          skill_slug,
          version,
          version_id,
          changelog,
          created_at,
          keen_status,
          keen_status_text,
          keen_report_url,
          sanbu_status,
          sanbu_status_text,
          sanbu_report_url,
          fetched_at,
          last_error
        ) VALUES (
          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL
        )
        ON CONFLICT (skill_slug, version) DO UPDATE SET
          version_id = EXCLUDED.version_id,
          changelog = EXCLUDED.changelog,
          created_at = COALESCE(skillhub_skill_version.created_at, EXCLUDED.created_at),
          keen_status = EXCLUDED.keen_status,
          keen_status_text = EXCLUDED.keen_status_text,
          keen_report_url = EXCLUDED.keen_report_url,
          sanbu_status = EXCLUDED.sanbu_status,
          sanbu_status_text = EXCLUDED.sanbu_status_text,
          sanbu_report_url = EXCLUDED.sanbu_report_url,
          fetched_at = EXCLUDED.fetched_at,
          last_error = NULL
        """
        now = _now_local()
        self.execute(
            sql,
            (
                skill_slug,
                version,
                version_id,
                changelog,
                created_at,
                keen_status,
                keen_status_text,
                keen_report_url,
                sanbu_status,
                sanbu_status_text,
                sanbu_report_url,
                now,
            ),
        )

    def ensure_artifact_row(self, skill_slug: str, version: str, source_url: Optional[str]) -> None:
        sql = """
        INSERT INTO skillhub_skill_artifact (
          skill_slug, version, source_url, status, created_at
        ) VALUES (%s,%s,%s,'pending',%s)
        ON CONFLICT (skill_slug, version) DO NOTHING
        """
        self.execute(sql, (skill_slug, version, source_url, _now_local()))

    def mark_skill_error(self, slug: str, error: str) -> None:
        sql = """
        UPDATE skillhub_skill
        SET last_error = %s, fetched_at = %s
        WHERE slug = %s
        """
        now = _now_local()
        self.execute(sql, (error[:2000], now, slug))

    def mark_version_error(self, skill_slug: str, version: str, error: str) -> None:
        sql = """
        UPDATE skillhub_skill_version
        SET last_error = %s, fetched_at = %s
        WHERE skill_slug = %s AND version = %s
        """
        now = _now_local()
        self.execute(sql, (error[:2000], now, skill_slug, version))

    def get_artifact_status(self, skill_slug: str, version: str) -> Optional[str]:
        sql = """
        SELECT status
        FROM skillhub_skill_artifact
        WHERE skill_slug = %s AND version = %s
        """
        rows = self.fetchall(sql, (skill_slug, version))
        if not rows:
            return None
        return rows[0][0]

    def update_artifact_uploaded(
        self,
        *,
        skill_slug: str,
        version: str,
        source_url: Optional[str],
        content_type: str,
        size_bytes: int,
        sha256: str,
        files_count: Optional[int],
        oss_bucket: str,
        oss_key: str,
    ) -> None:
        sql = """
        UPDATE skillhub_skill_artifact
        SET
          source_url = %s,
          content_type = %s,
          size_bytes = %s,
          files_count = %s,
          oss_bucket = %s,
          oss_key = %s,
          downloaded_at = %s,
          uploaded_at = %s,
          status = 'uploaded',
          last_error = NULL,
          updated_at = %s
        WHERE skill_slug = %s AND version = %s
        """
        now = _now_local()
        self.execute(
            sql,
            (
                source_url,
                content_type,
                size_bytes,
                files_count,
                oss_bucket,
                oss_key,
                now,
                now,
                now,
                skill_slug,
                version,
            ),
        )
        self.execute(
            "UPDATE skillhub_skill_version SET sha256 = %s WHERE skill_slug = %s AND version = %s",
            (sha256, skill_slug, version),
        )

    def mark_artifact_error(self, skill_slug: str, version: str, error: str) -> None:
        sql = """
        UPDATE skillhub_skill_artifact
        SET
          status = 'error',
          last_error = %s,
          updated_at = %s
        WHERE skill_slug = %s AND version = %s
        """
        self.execute(sql, (error[:2000], _now_local(), skill_slug, version))


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
        self.bucket = cfg.bucket

    def object_prefix_for_skill(self, slug: str, version: str) -> str:
        return f"skillhub/{slug}/{version}"

    def put_bytes(self, key: str, data: bytes) -> Optional[str]:
        result = self._client.put_object(
            self._oss.PutObjectRequest(bucket=self._cfg.bucket, key=key, body=data)
        )
        return getattr(result, "etag", None)

    def put_file(self, key: str, file_path: str) -> Optional[str]:
        with open(file_path, "rb") as f:
            result = self._client.put_object(
                self._oss.PutObjectRequest(bucket=self._cfg.bucket, key=key, body=f)
            )
        return getattr(result, "etag", None)


class SkillHubClient:
    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()
        self._base = "https://api.skillhub.cn"
        self._session.headers.update(
            {
                "User-Agent": "skill-security-service/1.0 (fetchskill; +https://github.com/)",
                "Accept": "application/json, text/plain, */*",
            }
        )

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

    def _request_json(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = urljoin(self._base, path.lstrip("/"))
        resp = self._request_with_backoff(method, url, params=params)
        try:
            return resp.json()
        finally:
            resp.close()

    def iter_skills(
        self, *, page_size: int, sort_by: str, order: str
    ) -> Iterable[Dict[str, Any]]:
        page = 1
        while True:
            data = self._request_json(
                "GET",
                "/api/skills",
                params={"page": page, "pageSize": page_size, "sortBy": sort_by, "order": order},
            )
            if data.get("code") != 0:
                raise RuntimeError(f"Unexpected response: {data!r}")
            payload = data.get("data") or {}
            items = payload.get("skills") or []
            if not items:
                break
            for it in items:
                if isinstance(it, dict):
                    yield it
            total = payload.get("total")
            if isinstance(total, int) and page * page_size >= total:
                break
            page += 1

    def get_skill_detail(self, slug: str) -> Dict[str, Any]:
        return self._request_json("GET", f"/api/v1/skills/{pathname2url(slug)}")

    def get_skill_versions(self, slug: str) -> Dict[str, Any]:
        return self._request_json("GET", f"/api/v1/skills/{pathname2url(slug)}/versions")

    def get_skill_files(self, slug: str, version: str) -> Dict[str, Any]:
        return self._request_json(
            "GET", f"/api/v1/skills/{pathname2url(slug)}/files", params={"version": version}
        )

    def download_file(self, url: str) -> Tuple[bytes, int, Optional[str], str]:
        sha = hashlib.sha256()
        size = 0
        resp = self._request_with_backoff("GET", url, stream=True, timeout=120)
        content_type = resp.headers.get("Content-Type")
        buf = bytearray()
        try:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                buf.extend(chunk)
                sha.update(chunk)
                size += len(chunk)
        finally:
            resp.close()
        return bytes(buf), size, content_type, sha.hexdigest()

    def download_to_file(self, url: str, file_path: str) -> Tuple[int, Optional[str], str]:
        sha = hashlib.sha256()
        size = 0
        resp = self._request_with_backoff("GET", url, stream=True, timeout=300)
        content_type = resp.headers.get("Content-Type")
        try:
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    sha.update(chunk)
                    size += len(chunk)
        finally:
            resp.close()
        return size, content_type, sha.hexdigest()


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


def _safe_relpath(path: str) -> Optional[str]:
    name = (path or "").replace("\\", "/").lstrip("/")
    if not name or name.endswith("/"):
        return None
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        return None
    return p.as_posix()


def _sha256_file(file_path: str) -> Tuple[int, str]:
    sha = hashlib.sha256()
    size = 0
    with open(file_path, "rb") as f:
        while True:
            buf = f.read(1024 * 1024)
            if not buf:
                break
            sha.update(buf)
            size += len(buf)
    return size, sha.hexdigest()


def _skillhub_zip_url(slug: str, version: str) -> str:
    return (
        "https://skillhub-1388575217.cos.accelerate.myqcloud.com"
        + f"/skills/{quote(slug)}/{quote(version)}.zip"
    )


def _extract_zip_to_dir(zip_path: str, out_dir: str) -> List[str]:
    extracted: List[str] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename
            safe = _safe_relpath(name)
            if not safe:
                continue
            extracted_path = os.path.join(out_dir, safe)
            os.makedirs(os.path.dirname(extracted_path), exist_ok=True)
            with zf.open(info, "r") as src, open(extracted_path, "wb") as dst:
                while True:
                    buf = src.read(1024 * 1024)
                    if not buf:
                        break
                    dst.write(buf)
            extracted.append(safe)
    return extracted


def _extract_security_report_fields(obj: Any, key: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not isinstance(obj, dict):
        return (None, None, None)
    x = obj.get(key) or {}
    if not isinstance(x, dict):
        return (None, None, None)
    status = x.get("status")
    status_text = x.get("statusText")
    report_url = x.get("reportUrl")
    return (
        str(status) if status is not None else None,
        str(status_text) if status_text is not None else None,
        str(report_url) if report_url is not None else None,
    )


def _extract_security_report_fields_loose(obj: Any, key: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    status, status_text, report_url = _extract_security_report_fields(obj, key)
    if status or status_text or report_url:
        return status, status_text, report_url
    if not isinstance(obj, dict):
        return (None, None, None)
    status = obj.get(f"{key}Status") or obj.get(f"{key}_status")
    status_text = obj.get(f"{key}StatusText") or obj.get(f"{key}_status_text")
    report_url = obj.get(f"{key}ReportUrl") or obj.get(f"{key}_report_url")
    return (
        str(status) if status is not None else None,
        str(status_text) if status_text is not None else None,
        str(report_url) if report_url is not None else None,
    )


def _extract_version_security_fields(version_obj: Any) -> Tuple[
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
]:
    if not isinstance(version_obj, dict):
        return (None, None, None, None, None, None)
    sec = version_obj.get("securityReports") or version_obj.get("securityReport") or {}
    keen_status, keen_status_text, keen_report_url = _extract_security_report_fields_loose(sec, "keen")
    sanbu_status, sanbu_status_text, sanbu_report_url = _extract_security_report_fields_loose(sec, "sanbu")
    if keen_status or keen_status_text or keen_report_url or sanbu_status or sanbu_status_text or sanbu_report_url:
        return (
            keen_status,
            keen_status_text,
            keen_report_url,
            sanbu_status,
            sanbu_status_text,
            sanbu_report_url,
        )
    keen_status, keen_status_text, keen_report_url = _extract_security_report_fields_loose(version_obj, "keen")
    sanbu_status, sanbu_status_text, sanbu_report_url = _extract_security_report_fields_loose(version_obj, "sanbu")
    return (
        keen_status,
        keen_status_text,
        keen_report_url,
        sanbu_status,
        sanbu_status_text,
        sanbu_report_url,
    )


@dataclass
class _WorkerContext:
    pg: Pg
    oss: OssUploader
    client: SkillHubClient


def _process_one_skill(
    *,
    item: Dict[str, Any],
    pg: Pg,
    oss: OssUploader,
    client: SkillHubClient,
    latest_only: bool,
    download_files: bool,
) -> None:
    slug = str(item.get("slug") or "").strip()
    if not slug:
        return
    display_name = str(item.get("name") or slug)
    started_at = _now_local()
    t0 = time.perf_counter()
    try:
        created_at = _utc_from_ms(item.get("created_at")) if isinstance(item.get("created_at"), int) else None
        updated_at = _utc_from_ms(item.get("updated_at")) if isinstance(item.get("updated_at"), int) else None
        labels = item.get("labels") or {}
        requires_api_key = _parse_bool(labels.get("requires_api_key") if isinstance(labels, dict) else None)

        pg.upsert_skill(
            slug=slug,
            display_name=display_name,
            summary=str(item.get("description")) if item.get("description") is not None else None,
            summary_zh=str(item.get("description_zh")) if item.get("description_zh") is not None else None,
            category=str(item.get("category")) if item.get("category") is not None else None,
            source=str(item.get("source")) if item.get("source") is not None else None,
            homepage_url=str(item.get("homepage")) if item.get("homepage") is not None else None,
            owner_handle=str(item.get("ownerName")) if item.get("ownerName") is not None else None,
            owner_display_name=str(item.get("ownerName")) if item.get("ownerName") is not None else None,
            requires_api_key=requires_api_key,
            score=float(item.get("score")) if isinstance(item.get("score"), (int, float)) else None,
            created_at=created_at,
            updated_at=updated_at,
            comments_count=None,
            downloads_count=int(item.get("downloads")) if isinstance(item.get("downloads"), int) else None,
            installs_count=int(item.get("installs")) if isinstance(item.get("installs"), int) else None,
            stars_count=int(item.get("stars")) if isinstance(item.get("stars"), int) else None,
            versions_count=None,
            latest_version=str(item.get("version")) if item.get("version") is not None else None,
            latest_version_created_at=None,
            latest_version_changelog=None,
            keen_status=None,
            keen_status_text=None,
            keen_report_url=None,
            sanbu_status=None,
            sanbu_status_text=None,
            sanbu_report_url=None,
        )

        detail = client.get_skill_detail(slug)
        owner = detail.get("owner") or {}
        skill = detail.get("skill") or {}
        latest_version_obj = detail.get("latestVersion") or {}
        security_reports = detail.get("securityReports") or {}

        keen_status, keen_status_text, keen_report_url = _extract_security_report_fields(security_reports, "keen")
        sanbu_status, sanbu_status_text, sanbu_report_url = _extract_security_report_fields(security_reports, "sanbu")

        stats = skill.get("stats") or {}
        pg.upsert_skill(
            slug=slug,
            display_name=str(skill.get("displayName") or display_name),
            summary=str(skill.get("summary")) if skill.get("summary") is not None else None,
            summary_zh=str(skill.get("summary_zh")) if skill.get("summary_zh") is not None else None,
            category=str(skill.get("category")) if skill.get("category") is not None else None,
            source=str(skill.get("source")) if skill.get("source") is not None else None,
            homepage_url=str(item.get("homepage")) if item.get("homepage") is not None else None,
            owner_handle=str(owner.get("handle")) if owner.get("handle") is not None else None,
            owner_display_name=str(owner.get("displayName")) if owner.get("displayName") is not None else None,
            requires_api_key=requires_api_key,
            score=float(item.get("score")) if isinstance(item.get("score"), (int, float)) else None,
            created_at=_utc_from_ms(skill.get("createdAt")) if isinstance(skill.get("createdAt"), int) else created_at,
            updated_at=_utc_from_ms(skill.get("updatedAt")) if isinstance(skill.get("updatedAt"), int) else updated_at,
            comments_count=int(stats.get("comments")) if isinstance(stats.get("comments"), int) else None,
            downloads_count=int(stats.get("downloads")) if isinstance(stats.get("downloads"), int) else None,
            installs_count=int(stats.get("installs")) if isinstance(stats.get("installs"), int) else None,
            stars_count=int(stats.get("stars")) if isinstance(stats.get("stars"), int) else None,
            versions_count=int(stats.get("versions")) if isinstance(stats.get("versions"), int) else None,
            latest_version=str(latest_version_obj.get("version")) if latest_version_obj.get("version") is not None else None,
            latest_version_created_at=_utc_from_ms(latest_version_obj.get("createdAt"))
            if isinstance(latest_version_obj.get("createdAt"), int)
            else None,
            latest_version_changelog=str(latest_version_obj.get("changelog"))
            if latest_version_obj.get("changelog") is not None
            else None,
            keen_status=keen_status,
            keen_status_text=keen_status_text,
            keen_report_url=keen_report_url,
            sanbu_status=sanbu_status,
            sanbu_status_text=sanbu_status_text,
            sanbu_report_url=sanbu_report_url,
        )

        versions_payload = client.get_skill_versions(slug)
        versions = versions_payload.get("versions") or []
        if not isinstance(versions, list):
            versions = []
        version_rows = [v for v in versions if isinstance(v, dict)]

        ver_meta: Dict[str, Dict[str, Any]] = {}
        for v in version_rows:
            ver = str(v.get("version") or "").strip()
            if not ver:
                continue
            (
                v_keen_status,
                v_keen_status_text,
                v_keen_report_url,
                v_sanbu_status,
                v_sanbu_status_text,
                v_sanbu_report_url,
            ) = _extract_version_security_fields(v)
            meta = {
                "version_id": int(v.get("versionId")) if isinstance(v.get("versionId"), int) else None,
                "changelog": str(v.get("changelog")) if v.get("changelog") is not None else None,
                "created_at": _utc_from_ms(v.get("createdAt")) if isinstance(v.get("createdAt"), int) else None,
                "keen_status": v_keen_status,
                "keen_status_text": v_keen_status_text,
                "keen_report_url": v_keen_report_url,
                "sanbu_status": v_sanbu_status,
                "sanbu_status_text": v_sanbu_status_text,
                "sanbu_report_url": v_sanbu_report_url,
            }
            ver_meta[ver] = meta
            pg.upsert_skill_version(
                skill_slug=slug,
                version=ver,
                version_id=meta["version_id"],
                changelog=meta["changelog"],
                created_at=meta["created_at"],
                keen_status=meta["keen_status"],
                keen_status_text=meta["keen_status_text"],
                keen_report_url=meta["keen_report_url"],
                sanbu_status=meta["sanbu_status"],
                sanbu_status_text=meta["sanbu_status_text"],
                sanbu_report_url=meta["sanbu_report_url"],
            )

        latest_ver = str(latest_version_obj.get("version") or item.get("version") or "").strip()
        target_versions: List[str]
        if latest_only:
            target_versions = [latest_ver] if latest_ver else []
        else:
            target_versions = list(ver_meta.keys())

        for ver in target_versions:
            if not ver:
                continue

            meta = ver_meta.get(ver) or {
                "version_id": None,
                "changelog": None,
                "created_at": None,
                "keen_status": None,
                "keen_status_text": None,
                "keen_report_url": None,
                "sanbu_status": None,
                "sanbu_status_text": None,
                "sanbu_report_url": None,
            }
            pg.upsert_skill_version(
                skill_slug=slug,
                version=ver,
                version_id=meta["version_id"],
                changelog=meta["changelog"],
                created_at=meta["created_at"],
                keen_status=meta["keen_status"],
                keen_status_text=meta["keen_status_text"],
                keen_report_url=meta["keen_report_url"],
                sanbu_status=meta["sanbu_status"],
                sanbu_status_text=meta["sanbu_status_text"],
                sanbu_report_url=meta["sanbu_report_url"],
            )

            if not download_files:
                continue

            source_url = _skillhub_zip_url(slug, ver)
            pg.ensure_artifact_row(slug, ver, source_url)
            status = pg.get_artifact_status(slug, ver)
            if status == "uploaded":
                continue
            zip_path: Optional[str] = None
            extract_dir: Optional[str] = None
            try:
                tmp_zip = tempfile.NamedTemporaryFile(
                    prefix=f"skillhub_{slug}_{ver}_",
                    suffix=".zip",
                    delete=False,
                )
                zip_path = tmp_zip.name
                tmp_zip.close()
                size_bytes, zip_content_type, sha256 = client.download_to_file(source_url, zip_path)
                extract_dir = tempfile.mkdtemp(prefix=f"skillhub_{slug}_{ver}_unz_")
                extracted_paths = _extract_zip_to_dir(zip_path, extract_dir)

                prefix = oss.object_prefix_for_skill(slug, ver)
                for rel_path in extracted_paths:
                    abs_path = os.path.join(extract_dir, rel_path)
                    oss_key = f"{prefix}/{rel_path}"
                    oss.put_file(oss_key, abs_path)

                pg.update_artifact_uploaded(
                    skill_slug=slug,
                    version=ver,
                    source_url=source_url,
                    content_type=str(zip_content_type or "application/zip"),
                    size_bytes=size_bytes,
                    sha256=sha256,
                    files_count=len(extracted_paths),
                    oss_bucket=oss.bucket,
                    oss_key=f"{prefix}/",
                )
            except Exception as e:
                pg.mark_artifact_error(slug, ver, str(e))
            finally:
                if zip_path:
                    try:
                        os.unlink(zip_path)
                    except Exception:
                        pass
                if extract_dir:
                    try:
                        for root, dirs, files in os.walk(extract_dir, topdown=False):
                            for name in files:
                                try:
                                    os.unlink(os.path.join(root, name))
                                except Exception:
                                    pass
                            for name in dirs:
                                try:
                                    os.rmdir(os.path.join(root, name))
                                except Exception:
                                    pass
                        os.rmdir(extract_dir)
                    except Exception:
                        pass

        pg.commit()
        elapsed = time.perf_counter() - t0
        print(
            _json_dumps(
                {
                    "event": "skillhub_skill_done",
                    "slug": slug,
                    "display_name": display_name,
                    "started_at": started_at.isoformat(),
                    "elapsed_seconds": round(elapsed, 3),
                    "status": "ok",
                }
            )
        )
    except Exception as e:
        pg.rollback()
        try:
            pg.mark_skill_error(slug, str(e))
            pg.commit()
        except Exception:
            pg.rollback()
        elapsed = time.perf_counter() - t0
        print(
            _json_dumps(
                {
                    "event": "skillhub_skill_done",
                    "slug": slug,
                    "display_name": display_name,
                    "started_at": started_at.isoformat(),
                    "elapsed_seconds": round(elapsed, 3),
                    "status": "error",
                    "error": str(e)[:500],
                }
            )
        )


def fetch_skillhub(
    *,
    pg_cfg: PgConfig,
    oss_cfg: OssConfig,
    count: Optional[int],
    sort_by: str,
    order: str,
    page_size: int,
    latest_only: bool,
    download_files: bool,
    concurrency: int,
) -> None:
    concurrency = max(1, int(concurrency))
    if concurrency <= 1:
        pg = Pg(pg_cfg)
        oss = OssUploader(oss_cfg)
        client = SkillHubClient()
        try:
            processed = 0
            for item in client.iter_skills(page_size=page_size, sort_by=sort_by, order=order):
                if count is not None and processed >= count:
                    break
                if not isinstance(item, dict):
                    continue
                _process_one_skill(
                    item=item,
                    pg=pg,
                    oss=oss,
                    client=client,
                    latest_only=latest_only,
                    download_files=download_files,
                )
                processed += 1
        finally:
            pg.close()
        return

    thread_local = threading.local()
    contexts: List[_WorkerContext] = []
    ctx_lock = threading.Lock()

    def _ctx() -> _WorkerContext:
        existing = getattr(thread_local, "ctx", None)
        if existing is not None:
            return existing
        ctx = _WorkerContext(pg=Pg(pg_cfg), oss=OssUploader(oss_cfg), client=SkillHubClient())
        thread_local.ctx = ctx
        with ctx_lock:
            contexts.append(ctx)
        return ctx

    def _run_item(it: Dict[str, Any]) -> None:
        ctx = _ctx()
        _process_one_skill(
            item=it,
            pg=ctx.pg,
            oss=ctx.oss,
            client=ctx.client,
            latest_only=latest_only,
            download_files=download_files,
        )

    executor = ThreadPoolExecutor(max_workers=concurrency)
    inflight: Set[Future[None]] = set()
    client = SkillHubClient()
    submitted = 0
    try:
        for item in client.iter_skills(page_size=page_size, sort_by=sort_by, order=order):
            if count is not None and submitted >= count:
                break
            if not isinstance(item, dict):
                continue
            while len(inflight) >= concurrency * 2:
                done, inflight = wait(inflight, return_when=FIRST_COMPLETED)
                for f in done:
                    f.result()
            inflight.add(executor.submit(_run_item, item))
            submitted += 1
        if inflight:
            done, _ = wait(inflight)
            for f in done:
                f.result()
    finally:
        executor.shutdown(wait=True, cancel_futures=False)
        for c in contexts:
            c.pg.close()


def _parse_count(v: str) -> Optional[int]:
    s = (v or "").strip().lower()
    if s == "all":
        return None
    n = int(s)
    if n <= 0:
        raise ValueError("--count must be a positive integer or 'all'")
    return n


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="fetch_skillhub_skills.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    fetch = sub.add_parser("fetch")
    fetch.add_argument("--count", default="all", help="抓取数量：all 或正整数")
    fetch.add_argument("--page-size", type=int, default=100)
    fetch.add_argument("--order-by", default="downloads", help="排序字段：score/downloads/stars/installs 等")
    fetch.add_argument("--order-dir", default="desc", choices=("asc", "desc"))
    fetch.add_argument("--all-versions", action="store_true", default=False, help="抓取版本历史（会更慢）")
    fetch.add_argument("--skip-files", action="store_true", default=False, help="仅入库，不下载/上传文件（更快）")
    fetch.add_argument("--concurrency", type=int, default=4, help="并发数（建议 2~6，过大容易被限流）")

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
        fetch_skillhub(
            pg_cfg=_pg_config_from_args(args),
            oss_cfg=_oss_config_from_args(args),
            count=_parse_count(str(args.count)),
            sort_by=str(args.order_by),
            order=str(args.order_dir),
            page_size=int(args.page_size),
            latest_only=(not bool(args.all_versions)),
            download_files=(not bool(args.skip_files)),
            concurrency=int(args.concurrency),
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
