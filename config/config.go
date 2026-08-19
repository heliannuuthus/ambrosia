package config

import (
	"encoding/base64"
	"errors"
	"fmt"
	"strings"

	"gorm.io/gorm"

	baseconfig "github.com/heliantheon/common/config"
	pkgdb "github.com/heliantheon/common/database"
	"github.com/heliantheon/common/logger"
)

// Cfg 返回 Ambrosia 配置单例
func Cfg() *baseconfig.Cfg {
	return baseconfig.Ambrosia()
}

// Validate 校验 Ambrosia 启动所需的全部配置。
func Validate() error {
	var errs []error
	for _, key := range []string{
		"db.url", "aegis.audience", "aegis.issuer", "aegis.secret-key",
		"openrouter.api-key", "openrouter.model", "amap.api-key",
	} {
		if strings.TrimSpace(Cfg().GetString(key)) == "" {
			errs = append(errs, fmt.Errorf("必需配置 %s 未设置", key))
		}
	}
	if _, err := GetAegisSecretKeyBytes(); err != nil {
		errs = append(errs, err)
	}
	return errors.Join(errs...)
}

// GetAegisAudience 获取 Ambrosia 服务 audience（用于 token 验证）
func GetAegisAudience() string {
	audience := Cfg().GetString("aegis.audience")
	if audience == "" {
		return "ambrosia"
	}
	return audience
}

// GetAegisIssuer 获取 Aegis API/issuer 端点。
func GetAegisIssuer() string {
	issuer := strings.TrimRight(Cfg().GetString("aegis.issuer"), "/")
	if issuer == "" {
		return "https://aegis.heliannuuthus.com/api"
	}
	return issuer
}

// GetAegisSecretKeyBytes 获取 Ambrosia 服务的 48 字节 token seed。
func GetAegisSecretKeyBytes() ([]byte, error) {
	secret := Cfg().GetString("aegis.secret-key")
	if secret == "" {
		return nil, fmt.Errorf("ambrosia aegis.secret-key 未配置")
	}
	seed, err := base64.RawURLEncoding.DecodeString(secret)
	if err != nil {
		return nil, fmt.Errorf("解码 ambrosia aegis.secret-key 失败: %w", err)
	}
	if len(seed) != 48 {
		return nil, fmt.Errorf("ambrosia aegis.secret-key 长度错误: 期望 48 字节 seed, 实际 %d 字节", len(seed))
	}
	return seed, nil
}

// InitDB 初始化 Ambrosia 数据库连接
func InitDB() *gorm.DB {
	cfg := Cfg()
	dsn := cfg.GetString("db.url")

	db, err := pkgdb.Connect(dsn)
	if err != nil {
		logger.Fatalf("连接 Ambrosia 数据库失败: %v", err)
	}
	logger.Infof("数据库连接成功 (ambrosia)")
	return db
}
