package ambrosia

import (
	"fmt"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"github.com/heliannuuthus/aegis-go/guard"
	reqr "github.com/heliannuuthus/aegis-go/guard/requirement"
	"github.com/heliannuuthus/aegis-go/utilities/relation"
	ambrosiaconfig "github.com/heliannuuthus/ambrosia/config"
	"github.com/heliannuuthus/ambrosia/internal/favorite"
	"github.com/heliannuuthus/ambrosia/internal/history"
	"github.com/heliannuuthus/ambrosia/internal/home"
	"github.com/heliannuuthus/ambrosia/internal/preference"
	"github.com/heliannuuthus/ambrosia/internal/recipe"
	"github.com/heliannuuthus/ambrosia/internal/recommend"
	"github.com/heliannuuthus/ambrosia/internal/tag"
)

type Ambrosia struct {
	guard             *guard.Gin
	recipeHandler     *recipe.Handler
	favoriteHandler   *favorite.Handler
	historyHandler    *history.Handler
	homeHandler       *home.Handler
	tagHandler        *tag.Handler
	recommendHandler  *recommend.Handler
	preferenceHandler *preference.Handler
}

func New(db *gorm.DB) (*Ambrosia, error) {
	if db == nil {
		return nil, fmt.Errorf("数据库连接未初始化")
	}
	g, err := guard.NewGin(ambrosiaconfig.GetAegisAudience())
	if err != nil {
		return nil, fmt.Errorf("创建鉴权中间件失败: %w", err)
	}
	if err := tag.InitializeCache(); err != nil {
		return nil, fmt.Errorf("初始化标签缓存失败: %w", err)
	}
	recipeHandler, err := recipe.NewHandler(db)
	if err != nil {
		return nil, fmt.Errorf("创建菜谱服务失败: %w", err)
	}
	homeHandler, err := home.NewHandler(db)
	if err != nil {
		return nil, fmt.Errorf("创建首页服务失败: %w", err)
	}
	recommendHandler, err := recommend.NewHandler(db)
	if err != nil {
		return nil, fmt.Errorf("创建推荐服务失败: %w", err)
	}

	return &Ambrosia{
		guard:             g,
		recipeHandler:     recipeHandler,
		favoriteHandler:   favorite.NewHandler(db),
		historyHandler:    history.NewHandler(db),
		homeHandler:       homeHandler,
		tagHandler:        tag.NewHandler(db),
		recommendHandler:  recommendHandler,
		preferenceHandler: preference.NewHandler(db),
	}, nil
}

func (a *Ambrosia) RegisterRoutes(r gin.IRouter) {
	aud := ambrosiaconfig.GetAegisAudience()
	adminReqr := a.guard.Require(reqr.Relation(relation.Qualify("admin", "service:"+aud)))

	api := r.Group("/api")

	recipes := api.Group("/recipes")
	{
		recipes.GET("", a.recipeHandler.GetRecipes)
		recipes.GET("/categories/list", a.recipeHandler.GetCategories)
		recipes.GET("/:recipe_id", a.recipeHandler.GetRecipe)
		recipes.POST("", adminReqr, a.recipeHandler.CreateRecipe)
		recipes.POST("/batch", adminReqr, a.recipeHandler.CreateRecipesBatch)
		recipes.PATCH("/:recipe_id", adminReqr, a.recipeHandler.UpdateRecipe)
		recipes.DELETE("/:recipe_id", adminReqr, a.recipeHandler.DeleteRecipe)
	}

	user := api.Group("/user")
	user.Use(a.guard.Require(reqr.User()))
	{
		favorites := user.Group("/favorites")
		{
			favorites.GET("", a.favoriteHandler.GetFavorites)
			favorites.POST("", a.favoriteHandler.AddFavorite)
			favorites.POST("/batch-check", a.favoriteHandler.BatchCheckFavorites)
			favorites.GET("/:recipe_id/check", a.favoriteHandler.CheckFavorite)
			favorites.DELETE("/:recipe_id", a.favoriteHandler.RemoveFavorite)
		}

		historyGroup := user.Group("/history")
		{
			historyGroup.GET("", a.historyHandler.GetViewHistory)
			historyGroup.POST("", a.historyHandler.AddViewHistory)
			historyGroup.DELETE("", a.historyHandler.ClearViewHistory)
			historyGroup.DELETE("/:recipe_id", a.historyHandler.RemoveViewHistory)
		}

		preferenceGroup := user.Group("/preference")
		{
			preferenceGroup.GET("", a.preferenceHandler.GetUserPreferences)
			preferenceGroup.PUT("", a.preferenceHandler.UpdateUserPreferences)
		}
	}

	homeGroup := api.Group("/home")
	{
		homeGroup.GET("/banners", a.homeHandler.GetBanners)
		homeGroup.GET("/recommend", a.homeHandler.GetRecommendRecipes)
		homeGroup.GET("/hot", a.homeHandler.GetHotRecipes)
	}

	api.GET("/preferences", a.preferenceHandler.GetOptions)

	tags := api.Group("/tags")
	{
		tags.GET("", a.tagHandler.ListTags)
		tags.GET("/:type", a.tagHandler.GetTagsByType)
		tags.POST("", adminReqr, a.tagHandler.CreateTag)
		tags.PUT("/:type/:value", adminReqr, a.tagHandler.UpdateTag)
		tags.DELETE("/:type/:value", adminReqr, a.tagHandler.DeleteTag)
	}

	recommendGroup := api.Group("/recommend")
	{
		recommendGroup.POST("", a.recommendHandler.GetRecommendations)
		recommendGroup.POST("/context", a.guard.Require(reqr.User()), a.recommendHandler.GetContext)
	}
}
