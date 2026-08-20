-- Ambrosia 数据库 Schema（业务数据）
-- PostgreSQL 18 语法
-- 无外键约束，在应用层处理关联关系
-- 所有表主键统一为 _id (BIGSERIAL)

-- ==================== 数据库初始化 ====================

SELECT 'CREATE DATABASE ambrosia'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ambrosia')\gexec
\connect ambrosia

-- ==================== 用户偏好相关 ====================

-- 用户偏好表（存储用户选择的偏好选项）
-- 关联 auth.t_user.id（认证模块的用户表）
CREATE TABLE IF NOT EXISTS t_user_preference (
    _id         BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64) NOT NULL,
    tag_value   VARCHAR(50) NOT NULL,
    tag_type    VARCHAR(20) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_user_preference IS '用户偏好（存储用户选择的偏好选项）';
COMMENT ON COLUMN t_user_preference.user_id IS '关联 auth.t_user.id';
COMMENT ON COLUMN t_user_preference.tag_value IS '关联 t_tag.value';
COMMENT ON COLUMN t_user_preference.tag_type IS '关联 t_tag.type（冗余字段，优化查询）';

CREATE UNIQUE INDEX uk_user_tag ON t_user_preference (user_id, tag_value, tag_type);
CREATE INDEX idx_t_user_preference_tag_type ON t_user_preference (tag_type);
CREATE INDEX idx_t_user_preference_user_type ON t_user_preference (user_id, tag_type);

-- ==================== 菜谱相关 ====================

-- 菜谱主表
CREATE TABLE IF NOT EXISTS t_recipe (
    _id                 BIGSERIAL PRIMARY KEY,
    recipe_id           VARCHAR(32) NOT NULL,
    name                VARCHAR(128) NOT NULL,
    description         TEXT,
    images              JSONB,
    category            VARCHAR(32),
    difficulty          INTEGER DEFAULT 1,
    servings            INTEGER DEFAULT 1,
    prep_time_minutes   INTEGER,
    cook_time_minutes   INTEGER,
    total_time_minutes  INTEGER,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_recipe IS '菜谱主表';
COMMENT ON COLUMN t_recipe.recipe_id IS '由源文件路径生成的稳定 32 位 ID';
COMMENT ON COLUMN t_recipe.images IS '图片列表 (JSON 数组)，第一张为主图';
COMMENT ON COLUMN t_recipe.difficulty IS '难度 1-5';
COMMENT ON COLUMN t_recipe.servings IS '份数';

CREATE UNIQUE INDEX uk_t_recipe_recipe_id ON t_recipe (recipe_id);
CREATE UNIQUE INDEX uk_t_recipe_name ON t_recipe (name);
CREATE INDEX idx_t_recipe_category ON t_recipe (category);

-- 食材表
CREATE TABLE IF NOT EXISTS t_ingredient (
    _id             BIGSERIAL PRIMARY KEY,
    recipe_id       VARCHAR(32) NOT NULL,
    name            VARCHAR(64) NOT NULL,
    category        VARCHAR(32),
    quantity        DOUBLE PRECISION,
    unit            VARCHAR(64),
    text_quantity   VARCHAR(128) NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_ingredient IS '食材表';
COMMENT ON COLUMN t_ingredient.recipe_id IS '关联 t_recipe.recipe_id';
COMMENT ON COLUMN t_ingredient.category IS '关联 ingredient_category.key';
COMMENT ON COLUMN t_ingredient.text_quantity IS '原始文本用量';

CREATE UNIQUE INDEX uk_recipe_name ON t_ingredient (recipe_id, name);
CREATE INDEX idx_t_ingredient_category ON t_ingredient (category);

-- 步骤表
CREATE TABLE IF NOT EXISTS t_step (
    _id             BIGSERIAL PRIMARY KEY,
    recipe_id       VARCHAR(32) NOT NULL,
    step            INTEGER NOT NULL,
    description     TEXT NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_step IS '步骤表';
COMMENT ON COLUMN t_step.step IS '步骤序号';

CREATE UNIQUE INDEX uk_recipe_step ON t_step (recipe_id, step);

-- 小贴士表
CREATE TABLE IF NOT EXISTS t_additional_note (
    _id             BIGSERIAL PRIMARY KEY,
    recipe_id       VARCHAR(32) NOT NULL,
    note            TEXT NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_additional_note IS '小贴士表';

CREATE INDEX idx_t_additional_note_recipe_id ON t_additional_note (recipe_id);

-- ==================== 标签相关 ====================

-- 标签表（独立存储，不关联菜谱）
-- 存储所有标签定义，包括菜谱标签（cuisine/flavor/scene）和用户偏好选项（taboo/allergy）
CREATE TABLE IF NOT EXISTS t_tag (
    _id         BIGSERIAL PRIMARY KEY,
    value       VARCHAR(50) NOT NULL,
    label       VARCHAR(50) NOT NULL,
    type        VARCHAR(20) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_tag IS '标签表（独立存储，不关联菜谱）';
COMMENT ON COLUMN t_tag.value IS '标签值 (如 sichuan, spicy, no_pork)';
COMMENT ON COLUMN t_tag.label IS '显示名称 (如 川菜, 香辣, 不吃猪肉)';
COMMENT ON COLUMN t_tag.type IS '类型: cuisine/flavor/scene/taboo/allergy';

CREATE UNIQUE INDEX uk_type_value ON t_tag (type, value);
CREATE INDEX idx_t_tag_value ON t_tag (value);
CREATE INDEX idx_t_tag_type ON t_tag (type);

-- 菜谱标签关联表（存储菜谱和标签的多对多关系）
CREATE TABLE IF NOT EXISTS t_recipe_tag (
    _id         BIGSERIAL PRIMARY KEY,
    recipe_id   VARCHAR(32) NOT NULL,
    tag_value   VARCHAR(50) NOT NULL,
    tag_type    VARCHAR(20) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_recipe_tag IS '菜谱标签关联表';
COMMENT ON COLUMN t_recipe_tag.recipe_id IS '关联 t_recipe.recipe_id';
COMMENT ON COLUMN t_recipe_tag.tag_value IS '关联 t_tag.value';
COMMENT ON COLUMN t_recipe_tag.tag_type IS '关联 tag.type（冗余字段，优化查询）';

CREATE UNIQUE INDEX uk_recipe_tag ON t_recipe_tag (recipe_id, tag_value, tag_type);
CREATE INDEX idx_t_recipe_tag_tag_value ON t_recipe_tag (tag_value);
CREATE INDEX idx_t_recipe_tag_tag_type ON t_recipe_tag (tag_type);
CREATE INDEX idx_t_recipe_tag_recipe_type ON t_recipe_tag (recipe_id, tag_type);

-- ==================== 食材分类相关 ====================

-- 食材分类表
CREATE TABLE IF NOT EXISTS t_ingredient_category (
    _id         BIGSERIAL PRIMARY KEY,
    "key"       VARCHAR(32) NOT NULL,
    label       VARCHAR(32) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_ingredient_category IS '食材分类表';
COMMENT ON COLUMN t_ingredient_category."key" IS '分类标识符 (meat/seafood/vegetable...)';
COMMENT ON COLUMN t_ingredient_category.label IS '中文名称';

CREATE UNIQUE INDEX uk_t_ingredient_category_key ON t_ingredient_category ("key");

-- ==================== 收藏相关 ====================

-- 收藏表
-- 关联 auth.t_user.id（认证模块的用户表）
CREATE TABLE IF NOT EXISTS t_favorite (
    _id         BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64) NOT NULL,
    recipe_id   VARCHAR(32) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_favorite IS '收藏表';
COMMENT ON COLUMN t_favorite.user_id IS '关联 auth.t_user.id';
COMMENT ON COLUMN t_favorite.recipe_id IS '关联 t_recipe.recipe_id';

CREATE UNIQUE INDEX uk_user_recipe ON t_favorite (user_id, recipe_id);
CREATE INDEX idx_t_favorite_recipe_id ON t_favorite (recipe_id);

-- ==================== 浏览历史相关 ====================

-- 浏览历史表
-- 关联 auth.t_user.id（认证模块的用户表）
CREATE TABLE IF NOT EXISTS t_view_history (
    _id         BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64) NOT NULL,
    recipe_id   VARCHAR(64) NOT NULL,
    viewed_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE t_view_history IS '浏览历史表';
COMMENT ON COLUMN t_view_history.recipe_id IS '关联 t_recipe.recipe_id';

CREATE INDEX idx_t_view_history_recipe_id ON t_view_history (recipe_id);
CREATE INDEX idx_t_view_history_user_viewed ON t_view_history (user_id, viewed_at);
CREATE INDEX idx_t_view_history_user_recipe ON t_view_history (user_id, recipe_id);