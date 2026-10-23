async def test_server_lifespan_closes_http_and_cache_singletons():
    from sportiq.core import cache as cache_module
    from sportiq.core import http as http_module
    from sportiq.server import _lifespan

    cache_module.get_cache()
    http_module.get_client()
    assert cache_module._cache_singleton is not None
    assert http_module._client is not None

    async with _lifespan(None):
        pass

    assert cache_module._cache_singleton is None
    assert http_module._client is None


async def test_server_lifespan_skips_cleanup_under_http_transport(monkeypatch):
    from sportiq.core import cache as cache_module
    from sportiq.core import http as http_module
    from sportiq.server import _lifespan

    monkeypatch.setenv("SPORTIQ_TRANSPORT", "http")
    cache_module.get_cache()
    http_module.get_client()

    async with _lifespan(None):
        pass

    assert cache_module._cache_singleton is not None
    assert http_module._client is not None
    await http_module.close_client()


async def test_http_app_lifespan_closes_singletons_once_on_shutdown(monkeypatch):
    from sportiq.core import cache as cache_module
    from sportiq.core import http as http_module
    from sportiq.server import build_http_app, mcp

    monkeypatch.setenv("SPORTIQ_TRANSPORT", "http")
    # The SDK session manager runs once per instance; give this app a fresh one.
    monkeypatch.setattr(mcp, "_session_manager", None)
    app = build_http_app()

    async with app.router.lifespan_context(app):
        cache_module.get_cache()
        http_module.get_client()

    assert cache_module._cache_singleton is None
    assert http_module._client is None
