from web.backend.core.settings_registry import REGISTRY_BY_KEY

SITE_KEYS = (
    "browser_title", "title_separator", "site_name", "site_description",
    "site_url", "favicon_url", "timezone", "locale", "maintenance_mode", "og_image",
)

CMS_KEYS = ("admin_title", "admin_email", "posts_per_page", "comments_auto_approve")


def test_site_keys_live_in_theme_tab():
    for key in SITE_KEYS:
        defn = REGISTRY_BY_KEY[key]
        assert defn.tab == "theme", key
        assert defn.category == "Сайт", key


def test_cms_keys_stay_in_basic_tab():
    for key in CMS_KEYS:
        assert REGISTRY_BY_KEY[key].tab == "basic", key
