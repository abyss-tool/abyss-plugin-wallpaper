#!/usr/bin/env python3
"""插件仓 CI 门禁：plugin.json / CHANGELOG / 补丁通道三处一致性校验。"""
import json
import re
import sys
from pathlib import Path

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
REQUIRED = ("id", "name", "repo", "category", "version", "minApp", "summary")
CATEGORIES = {"terminal", "system", "sandbox", "disguise", "media",
              "automation", "desktop", "network", "data", "tools"}

errors = []


def fail(msg):
    errors.append(msg)


manifest = json.loads(Path("plugin.json").read_text(encoding="utf-8"))
repo_full = Path(".git/config").read_text(encoding="utf-8")
expected_repo = None
for line in repo_full.splitlines():
    if "url = https://github.com/" in line:
        expected_repo = line.split("github.com/")[1].removesuffix(".git").strip()
        break
if expected_repo is None:
    expected_repo = __import__("os").environ.get("GITHUB_REPOSITORY", "")

for field in REQUIRED:
    if not manifest.get(field):
        fail(f"plugin.json 缺少必填字段 {field}")

pid = manifest.get("id", "")
if not re.match(r"^abyss-plugin-[a-z0-9]+(-[a-z0-9]+)*$", pid):
    fail(f"插件 id 形态非法 → {pid!r}")
if expected_repo and manifest.get("repo") != expected_repo:
    fail(f"plugin.json.repo({manifest.get('repo')}) 与仓库({expected_repo})不一致")
if expected_repo and not expected_repo.endswith(pid):
    fail("仓库名末段应等于插件 id")
if manifest.get("category") not in CATEGORIES:
    fail(f"category 非法 → {manifest.get('category')!r}")
for key in ("version", "minApp"):
    if not SEMVER.match(manifest.get(key, "")):
        fail(f"plugin.json.{key} 非法 SemVer → {manifest.get(key)!r}")
if not isinstance(manifest.get("minHost", 1), int) or manifest.get("minHost", 0) < 1:
    fail("plugin.json.minHost 应为正整数")

changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
if f"## v{manifest.get('version')}" not in changelog:
    fail(f"CHANGELOG.md 缺少当前版本条目 ## v{manifest.get('version')}")

channel = json.loads(Path("patches/index.json").read_text(encoding="utf-8"))
if channel.get("schema") != "abyss-plugin-patches-v1":
    fail("patches/index.json schema 应为 abyss-plugin-patches-v1")
if channel.get("plugin") != pid:
    fail(f"patches/index.json.plugin({channel.get('plugin')}) 与 id 不一致")
if channel.get("latest") != manifest.get("version"):
    fail(f"patches/index.json.latest({channel.get('latest')}) 与 version 不一致")
seen = set()
for p in channel.get("patches", []):
    key = (p.get("from"), p.get("to"))
    if key in seen:
        fail(f"补丁段重复 {key}")
    seen.add(key)
    if not p.get("url"):
        fail(f"补丁 {key} 缺 url")

if errors:
    print(f"[plugin-ci] ✗ {len(errors)} 处校验失败：", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)
print(f"[plugin-ci] ✓ {pid} v{manifest.get('version')} 校验通过"
      f"（{len(channel.get('patches', []))} 条补丁记录）")
