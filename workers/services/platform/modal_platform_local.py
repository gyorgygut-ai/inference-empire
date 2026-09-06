"""Modal local platform: fresh dict session over its own fake."""

from __future__ import annotations

from workers.mock_server.modal import fake as _fake


class LocalModalPlatform:
    def deploy(self):
        _fake.clear()

    def undeploy(self):
        _fake.clear()
