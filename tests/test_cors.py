import importlib

from fastapi.middleware.cors import CORSMiddleware

from collectarr_sync import main as main_module
from collectarr_sync.config import get_settings


def _cors_options() -> dict:
    for middleware in main_module.app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return middleware.kwargs
    raise AssertionError("CORSMiddleware is not configured")


def test_cors_enables_localhost_regex_in_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SYNC_API_KEY", "test-sync-key")
    get_settings.cache_clear()
    try:
        importlib.reload(main_module)
        options = _cors_options()

        assert options.get("allow_origin_regex") == r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
    finally:
        monkeypatch.setenv("ENVIRONMENT", "test")
        get_settings.cache_clear()
        importlib.reload(main_module)


def test_cors_disables_localhost_regex_outside_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SYNC_API_KEY", "test-sync-key")
    get_settings.cache_clear()

    importlib.reload(main_module)
    options = _cors_options()

    assert options.get("allow_origin_regex") is None
