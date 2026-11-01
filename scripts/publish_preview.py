"""CI-only: publish the small verified UI preview through GitHub's contents API.

No build binaries or user data are committed. The commit changes only docs/ui-preview.png.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path


def main():
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ["GITHUB_REF_NAME"]
    api = f"https://api.github.com/repos/{repo}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "maa-verified-preview",
               "Content-Type": "application/json"}

    def request(path, data=None, method="GET"):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(api + path, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    content = base64.b64encode(Path("dist/screenshots/dashboard.png").read_bytes()).decode()
    blob = request("/git/blobs", {"content": content, "encoding": "base64"}, "POST")
    ref = request("/git/ref/heads/" + branch)
    parent = ref["object"]["sha"]
    commit = request("/git/commits/" + parent)
    tree = request("/git/trees", {"base_tree": commit["tree"]["sha"], "tree": [
        {"path": "docs/ui-preview.png", "mode": "100644", "type": "blob", "sha": blob["sha"]}
    ]}, "POST")
    updated = request("/git/commits", {"message": "docs: verified Windows UI preview [skip ci]",
                                      "tree": tree["sha"], "parents": [parent]}, "POST")
    request("/git/refs/heads/" + branch, {"sha": updated["sha"], "force": False}, "PATCH")
    print("Verified documentation preview published:", updated["sha"])


if __name__ == "__main__":
    main()
