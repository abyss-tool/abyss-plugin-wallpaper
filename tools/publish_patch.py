#!/usr/bin/env python3
"""插件补丁发布器：GitHub Release + 资产上传 + 补丁通道滚动。

职责：
  1. 读取 make_patch.py 的 meta（sha256 / size / notes）；
  2. 在本插件仓库创建 `v<to>` Release（幂等）并上传 zip 资产（同名先删）；
  3. 本地滚动 patches/index.json：新补丁条目置顶、latest → to
     （提交由 patch-release.yml 的 git 步骤完成）。

凭据：GITHUB_TOKEN 环境变量（Actions 默认令牌，contents:write 即可）。
仓库坐标：GITHUB_REPOSITORY 环境变量（Actions 自动注入），缺省回退
plugin.json.repo。纯 stdlib。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"


def die(msg: str) -> None:
    print(f"[publish-patch] ✗ {msg}", file=sys.stderr)
    sys.exit(1)


def api(method: str, url: str, body: dict | None = None, raw: bytes | None = None,
        not_found_ok: bool = False, retries: int = 4) -> dict:
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, method=method, data=data)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if raw is not None:
        req.add_header("Content-Type", "application/octet-stream")
    elif data is not None:
        req.add_header("Content-Type", "application/json")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read()
                return json.loads(payload.decode()) if payload else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code == 404 and not_found_ok:
                return {}
            if e.code in (409, 422) and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            die(f"GitHub API {method} {url} → HTTP {e.code}\n{detail[:500]}")
        except urllib.error.URLError as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            die(f"GitHub API {method} {url} → 网络错误 {e.reason}")
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="abyss 插件补丁发布")
    parser.add_argument("--meta", required=True, help="make_patch.py 生成的 meta.json 路径")
    args = parser.parse_args()

    if not TOKEN:
        die("GITHUB_TOKEN 未设置")

    meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    pid = meta["plugin"]
    to = meta["to"]
    frm = meta["from"]
    zip_path = Path(meta["zip"])
    if not zip_path.exists():
        die(f"补丁包不存在：{zip_path}")

    repo = os.environ.get("GITHUB_REPOSITORY") or json.loads(
        Path("plugin.json").read_text(encoding="utf-8")
    ).get("repo", "")
    if not repo:
        die("无法确定仓库坐标（GITHUB_REPOSITORY / plugin.json.repo）")

    tag = f"v{to}"
    asset_name = meta["assetName"]
    print(f"[publish-patch] {pid} {frm} → {to} · {repo}")

    # ── 1. Release（幂等；tag 未发布时 404 → 走创建分支）───────────────
    release = api("GET", f"{API}/repos/{repo}/releases/tags/{tag}", not_found_ok=True)
    if "id" in release:
        release_id = release["id"]
        print(f"[publish-patch] 复用既有 Release {tag}（id={release_id}）")
    else:
        created = api(
            "POST",
            f"{API}/repos/{repo}/releases",
            {
                "tag_name": tag,
                "target_commitish": "main",
                "name": f"{pid} {tag}",
                "body": "\n".join(f"- {n}" for n in meta.get("notes", [])) or tag,
            },
        )
        release_id = created.get("id")
        if not release_id:
            die("Release 创建失败")
        print(f"[publish-patch] ✓ Release {tag} 已创建（id={release_id}）")

    # ── 2. 资产上传（同名先删）─────────────────────────────────────────
    existing = {
        a["name"]: a for a in api("GET", f"{API}/repos/{repo}/releases/{release_id}/assets")
    }
    if asset_name in existing:
        api("DELETE", existing[asset_name]["url"])
        print(f"[publish-patch] 移除旧资产 {asset_name}，重新上传")
    with open(zip_path, "rb") as f:
        api(
            "POST",
            f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={asset_name}",
            raw=f.read(),
        )
    download_url = f"https://github.com/{repo}/releases/download/{tag}/{asset_name}"
    print(f"[publish-patch] ✓ 资产已上传 → {download_url}")

    # ── 3. 补丁通道滚动（本地文件；提交交给 workflow 的 git 步骤）───────
    channel_path = Path("patches/index.json")
    channel = json.loads(channel_path.read_text(encoding="utf-8"))
    if channel.get("schema") != "abyss-plugin-patches-v1":
        die(f"patches/index.json schema 非法：{channel.get('schema')!r}")
    if channel.get("plugin") != pid:
        die(f"patches/index.json.plugin({channel.get('plugin')}) 与 meta.plugin({pid}) 不一致")

    patches = [p for p in channel.get("patches", []) if not (p.get("from") == frm and p.get("to") == to)]
    patches.insert(
        0,
        {
            "from": frm,
            "to": to,
            "url": download_url,
            "sha256": meta["sha256"],
            "sizeBytes": meta["sizeBytes"],
            "notes": "；".join(meta.get("notes", [])),
        },
    )
    channel["latest"] = to
    channel["patches"] = patches[:20]
    channel["generatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    channel_path.write_text(
        json.dumps(channel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[publish-patch] ✓ 补丁通道已滚动：latest=v{to} · {len(patches)} 条记录")
    print(f"[publish-patch] 元数据：sha256={meta['sha256']} · {meta['sizeBytes']} bytes")


if __name__ == "__main__":
    main()
