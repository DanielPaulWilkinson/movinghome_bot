"""Offline stand-in for services.net.Net: answers from a dict of URL prefixes."""


class FakeNet:
    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls = []

    def get_json(self, url, params=None, min_interval=0.0, cache=True):
        self.calls.append((url, params))
        key = url
        if params and "q" in params:
            key = f"{url}?q={params['q']}"
        for prefix in sorted(self.routes, key=len, reverse=True):
            if key.startswith(prefix):
                value = self.routes[prefix]
                return value(url, params) if callable(value) else value
        return None

    def download(self, *a, **k):
        return False
