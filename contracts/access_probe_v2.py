# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Probe reachability and response-size classes for pinned compare URLs."""

import hashlib
import json
from genlayer import *


URLS = (
    "https://github.com/octocat/Hello-World/compare/553c2077f0edc3d5dc5d17262f6aa498e69d6f8e...7fd1a60b01f91b314f59955a4e4d4e80d8edf11d.diff",
    "https://github.com/octocat/Hello-World/compare/553c2077f0edc3d5dc5d17262f6aa498e69d6f8e...7fd1a60b01f91b314f59955a4e4d4e80d8edf11d.patch",
    "https://github.com/torvalds/linux/compare/0c3836482481200ead7b416ca80c68a29cfdaabd...98f7e32f20d28ec452afb208f9cffc08448a2652.diff",
    "https://github.com/torvalds/linux/compare/0c3836482481200ead7b416ca80c68a29cfdaabd...98f7e32f20d28ec452afb208f9cffc08448a2652.patch",
)
CAP_BYTES = 30_000
LARGE_BYTES = 2_000_000


def fetch_summary(url: str) -> dict:
    try:
        response = gl.nondet.web.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 BountyBenchProbe/1.0"},
        )
        body = response.body
        size = len(body)
        return {
            "status": int(response.status),
            "bytes": size,
            "sha256": hashlib.sha256(body).hexdigest(),
            "over_2mb": size > LARGE_BYTES,
            "over_cap": size > CAP_BYTES,
        }
    except Exception:
        return {"status": 0, "bytes": 0, "sha256": "", "over_2mb": False, "over_cap": False}


def coarse(result: dict) -> tuple:
    size = result.get("bytes", 0)
    bucket = "OVER_2MB" if size > LARGE_BYTES else "OVER_30KB" if size > CAP_BYTES else "AT_OR_UNDER_30KB"
    return result.get("status"), bucket


class AccessProbeV2(gl.Contract):
    observations: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def run(self) -> None:
        results = {}
        for url in URLS:
            def leader(url=url):
                return fetch_summary(url)

            def validate(proposed, url=url):
                if not isinstance(proposed, gl.vm.Return):
                    return False
                own = fetch_summary(url)
                return coarse(own) == coarse(proposed.calldata)

            results[url] = gl.vm.run_nondet_unsafe(leader, validate)
        self.observations["all"] = json.dumps(results, sort_keys=True)

    @gl.public.view
    def get_results(self) -> str:
        return self.observations.get("all", "{}")

