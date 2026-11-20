# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Probe whether validators can read public GitHub issue JSON."""

import hashlib
import json
from genlayer import *


URLS = (
    "https://api.github.com/repos/octocat/Hello-World/issues/1",
    "https://api.github.com/repos/JWattjr/bounty-bench-fixtures/issues/1",
    "https://github.com/octocat/Hello-World/issues/1",
)


def fetch_summary(url: str) -> dict:
    try:
        response = gl.nondet.web.get(url, headers={"User-Agent": "Mozilla/5.0 BountyBenchProbe/1.0", "Accept": "application/vnd.github+json"})
        body = response.body
        title = ""
        try:
            title = json.loads(body.decode("utf-8")).get("title", "")[:80]
        except Exception:
            title = ""
        return {"status": int(response.status), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "title": title}
    except Exception:
        return {"status": 0, "bytes": 0, "sha256": "", "title": ""}


class AccessProbeV3(gl.Contract):
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
                return fetch_summary(url).get("status") == proposed.calldata.get("status")

            results[url] = gl.vm.run_nondet_unsafe(leader, validate)
        self.observations["all"] = json.dumps(results, sort_keys=True)

    @gl.public.view
    def get_results(self) -> str:
        return self.observations.get("all", "{}")
