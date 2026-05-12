CREATE TABLE IF NOT EXISTS skillsmp_skill (
    skill_id TEXT PRIMARY KEY,
    skill_url TEXT NOT NULL UNIQUE,
    github_url TEXT NULL,
    github_owner TEXT NULL,
    github_repo TEXT NULL,
    github_branch TEXT NULL,
    github_path TEXT NULL,
    stars_count INTEGER NULL,
    forks_count INTEGER NULL,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE skillsmp_skill IS 'SkillsMP 技能基础表：来源于 skillsmp.com 的 /skills/{id} 页面；通过 sitemap lastmod 选择最新批次/作者批次，并解析 GitHub tree 信息';
COMMENT ON COLUMN skillsmp_skill.skill_id IS 'SkillsMP skill 唯一标识（URL 中 /skills/ 后面的 slug）';
COMMENT ON COLUMN skillsmp_skill.skill_url IS 'SkillsMP skill 详情页 URL（https://skillsmp.com/skills/{skill_id}）';
COMMENT ON COLUMN skillsmp_skill.sitemap_lastmod_utc IS '从 sitemap 中读取的 lastmod（UTC），用作“最新发布/更新”近似时间';
COMMENT ON COLUMN skillsmp_skill.github_url IS '从 skill 页面解析出的 GitHub tree URL（包含 owner/repo/branch/path）';
COMMENT ON COLUMN skillsmp_skill.github_owner IS 'GitHub 仓库 owner（由 github_url 解析）';
COMMENT ON COLUMN skillsmp_skill.github_repo IS 'GitHub 仓库 repo（由 github_url 解析）';
COMMENT ON COLUMN skillsmp_skill.github_branch IS 'GitHub 分支名（由 github_url 解析；常见 main/master）';
COMMENT ON COLUMN skillsmp_skill.github_path IS 'GitHub 仓库内 skill 目录路径（由 github_url 解析；用于调用 /api/github-contents）';
COMMENT ON COLUMN skillsmp_skill.stars_count IS 'GitHub Stars 数（从 SkillsMP skill 页面解析；可能为空）';
COMMENT ON COLUMN skillsmp_skill.forks_count IS 'GitHub Forks 数（从 SkillsMP skill 页面解析；可能为空）';
COMMENT ON COLUMN skillsmp_skill.last_error IS '最近一次处理该 skill 的错误信息（抓取/解析/上传失败时写入）';
COMMENT ON COLUMN skillsmp_skill.created_at IS '首次入库时间（本地记录）';
COMMENT ON COLUMN skillsmp_skill.updated_at IS '最近一次 upsert 更新时间（本地记录）';
COMMENT ON COLUMN skillsmp_skill.last_seen_at IS '最近一次在数据源中“看到”该 skill 的时间（本地记录）';

CREATE INDEX IF NOT EXISTS idx_skillsmp_skill_lastmod ON skillsmp_skill (sitemap_lastmod_utc DESC);
CREATE INDEX IF NOT EXISTS idx_skillsmp_skill_owner ON skillsmp_skill (github_owner);

CREATE TABLE IF NOT EXISTS skillsmp_skill_artifact (
    skill_id TEXT PRIMARY KEY REFERENCES skillsmp_skill(skill_id) ON DELETE CASCADE,
    oss_prefix TEXT NOT NULL,
    skillsmp_download_url TEXT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    downloaded_at TIMESTAMPTZ NULL,
    file_count INTEGER NULL,
    artifact_sha256 TEXT NULL,
    uploaded_at TIMESTAMPTZ NULL,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE skillsmp_skill_artifact IS 'SkillsMP 技能文件产物表：记录 OSS 上传前缀、上传状态、文件数与内容 hash，用于断点续跑';
COMMENT ON COLUMN skillsmp_skill_artifact.skill_id IS '对应 skillsmp_skill.skill_id';
COMMENT ON COLUMN skillsmp_skill_artifact.oss_prefix IS 'OSS 对象前缀（skillsmp/{owner}/{repo}/{skill_id}），其下存放该 skill 的全部文件';
COMMENT ON COLUMN skillsmp_skill_artifact.skillsmp_download_url IS 'SkillsMP 官方下载入口 URL（通常为 skillsmp 的 skill 详情页；页面内提供 Download Zip）';
COMMENT ON COLUMN skillsmp_skill_artifact.status IS '产物状态：pending|uploaded|error';
COMMENT ON COLUMN skillsmp_skill_artifact.downloaded_at IS '从 SkillsMP 获取到该 skill 文件内容的时间（成功拉取 /api/github-contents 后写入）';
COMMENT ON COLUMN skillsmp_skill_artifact.file_count IS '本次上传的文件数量（以 /api/github-contents 返回的文件列表为准）';
COMMENT ON COLUMN skillsmp_skill_artifact.artifact_sha256 IS '对“路径+内容hash”计算的整体 sha256，用于判断内容变化/幂等';
COMMENT ON COLUMN skillsmp_skill_artifact.uploaded_at IS '成功上传时间';
COMMENT ON COLUMN skillsmp_skill_artifact.last_error IS '最近一次上传/处理错误信息';
COMMENT ON COLUMN skillsmp_skill_artifact.created_at IS '产物记录首次创建时间';
COMMENT ON COLUMN skillsmp_skill_artifact.updated_at IS '产物记录最近更新时间';

CREATE INDEX IF NOT EXISTS idx_skillsmp_skill_artifact_status ON skillsmp_skill_artifact (status);
CREATE INDEX IF NOT EXISTS idx_skillsmp_skill_artifact_uploaded_at ON skillsmp_skill_artifact (uploaded_at DESC);
