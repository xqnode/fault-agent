-- =============================================================================
-- app_user：系统登录用户（轻量角色，非完整 RBAC）
-- 角色：ADMIN（全量）/ ENGINEER（运维读写）
-- =============================================================================

CREATE TABLE IF NOT EXISTS app_user (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    username        VARCHAR(64)  NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    nickname        VARCHAR(64)  NOT NULL,
    role            VARCHAR(32)  NOT NULL DEFAULT 'ENGINEER',
    status          VARCHAR(32)  NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_app_user PRIMARY KEY (id),
    CONSTRAINT uk_app_user_username UNIQUE (username),
    CONSTRAINT ck_app_user_role CHECK (role IN ('ADMIN', 'ENGINEER')),
    CONSTRAINT ck_app_user_status CHECK (status IN ('ACTIVE', 'DISABLED'))
);

CREATE INDEX IF NOT EXISTS idx_app_user_role ON app_user (role);
CREATE INDEX IF NOT EXISTS idx_app_user_status ON app_user (status);

DROP TRIGGER IF EXISTS trg_app_user_set_updated_at ON app_user;
CREATE TRIGGER trg_app_user_set_updated_at
BEFORE UPDATE ON app_user
FOR EACH ROW
EXECUTE FUNCTION trg_set_updated_at();

COMMENT ON TABLE app_user IS '系统用户表：登录账号与轻量角色（ADMIN/ENGINEER）';
COMMENT ON COLUMN app_user.username IS '登录用户名，唯一';
COMMENT ON COLUMN app_user.password_hash IS '口令摘要：pbkdf2_sha256$iter$salt$hex';
COMMENT ON COLUMN app_user.nickname IS '显示昵称';
COMMENT ON COLUMN app_user.role IS '角色：ADMIN 全量权限；ENGINEER 运维读写';
COMMENT ON COLUMN app_user.status IS '状态：ACTIVE / DISABLED';

-- 演示账号（可重复执行）
-- admin / admin123
-- engineer / engineer123
INSERT INTO app_user (username, password_hash, nickname, role, status)
VALUES
    (
        'admin',
        'pbkdf2_sha256$120000$faultagentseed0001$8274af63c342919883cfd395ff7fa41adf77d216062866be7a5cf121970bec5c',
        '系统管理员',
        'ADMIN',
        'ACTIVE'
    ),
    (
        'engineer',
        'pbkdf2_sha256$120000$faultagentseed0002$165d4c1b277446cc1ae9991de015cf9be0b11ebdced9412d81112782e5c2d4c1',
        '运维工程师',
        'ENGINEER',
        'ACTIVE'
    )
ON CONFLICT (username) DO UPDATE
SET
    password_hash = EXCLUDED.password_hash,
    nickname = EXCLUDED.nickname,
    role = EXCLUDED.role,
    status = EXCLUDED.status,
    updated_at = CURRENT_TIMESTAMP;
