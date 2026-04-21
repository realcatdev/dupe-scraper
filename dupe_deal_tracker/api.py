from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


class DupeApiError(RuntimeError):
    """Raised when Dupe returns an error response or an invalid payload."""


@dataclass(frozen=True)
class DupeClient:
    base_url: str
    api_key: str
    timeout_seconds: int = 30

    def get(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        url = self._url(path, params)
        request = urllib.request.Request(
            url,
            headers={
                "authorization": f"Bearer {self.api_key}",
                "accept": "application/json",
                "user-agent": "dupe-deal-tracker/0.1",
            },
            method="GET",
        )
        return self._send(request)

    def _url(self, path: str, params: Optional[Mapping[str, Any]]) -> str:
        base = self.base_url.rstrip("/")
        clean_path = "/" + path.lstrip("/")
        query = ""
        if params:
            filtered = {
                key: value
                for key, value in params.items()
                if value is not None and value != ""
            }
            if filtered:
                query = "?" + urllib.parse.urlencode(filtered, doseq=True)
        return f"{base}{clean_path}{query}"

    def _send(self, request: urllib.request.Request) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise DupeApiError(f"http {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise DupeApiError(f"request failed: {exc.reason}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DupeApiError("dupe returned non-json response") from exc

        if isinstance(payload, dict) and payload.get("success") is False:
            message = payload.get("error") or payload.get("message") or "unknown api error"
            raise DupeApiError(str(message))
        if not isinstance(payload, dict):
            raise DupeApiError("dupe returned an unexpected response shape")
        return payload
