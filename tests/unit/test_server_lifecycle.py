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
