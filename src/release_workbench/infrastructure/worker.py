"""Child-process entry point for isolated Python return values and HTTP requests."""

from __future__ import annotations

import json
import sys
import textwrap
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

MAX_BYTES = 1024 * 1024


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        if urllib.parse.urlsplit(req.full_url)[:2] != urllib.parse.urlsplit(newurl)[:2]:
            raise ValueError("Cross-origin redirects require an explicit request to the new URL.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main() -> None:
    request = json.load(sys.stdin)
    destination = Path(sys.argv[1])
    try:
        if request["mode"] == "python":
            namespace: dict[str, Any] = {}
            code = "def run(inputs):\n" + textwrap.indent(request["code"] or "pass", "    ")
            exec(compile(code, "<workflow-python>", "exec"), namespace)
            value = namespace["run"](request["inputs"])
        else:
            config = request["config"]
            url = config["url"]
            if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
                raise ValueError("HTTP requests require an http:// or https:// URL.")
            body = (
                None
                if config.get("body") is None
                else json.dumps(config["body"], allow_nan=False).encode()
            )
            if body and len(body) > MAX_BYTES:
                raise ValueError("HTTP request exceeds 1 MiB.")
            headers = {str(k): str(v) for k, v in config.get("headers", {}).items()}
            if body:
                headers.setdefault("Content-Type", "application/json")
            req = urllib.request.Request(
                url, data=body, headers=headers, method=config.get("method", "GET")
            )
            opener = urllib.request.build_opener(SameOriginRedirect())
            try:
                response = opener.open(req, timeout=request.get("timeout", 30))
            except urllib.error.HTTPError as error:
                response = error
            with response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("HTTP response exceeds 1 MiB.")
                text = data.decode("utf-8", "replace")
                try:
                    parsed = json.loads(text)
                except ValueError:
                    parsed = None
                value = {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "text": text,
                    "json": parsed,
                }
                if not 200 <= response.status < 300:
                    raise ValueError(f"HTTP status {response.status}: {text[:500]}")
        destination.write_text(json.dumps({"value": value}, allow_nan=False))
    except BaseException as error:
        traceback.print_exc()
        destination.write_text(json.dumps({"error": str(error)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
