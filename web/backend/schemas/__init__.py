# HexaVeil CMS Backend — Pydantic schemas (per-domain, mirrors remnawave's schemas/)
#
# Domains: auth, common, post, category, page, user, menu, widget,
#          log, media, theme, setting, notification, dashboard, finance.
# These describe the CMS request/response payloads. Routes return the
# PHP-compatible envelope {"success": ..., "data": ...} defined in common.py.