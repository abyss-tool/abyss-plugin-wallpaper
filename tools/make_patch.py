#!/usr/bin/env python3
"""插件数据补丁打包器（abyss-patch-v1）：把版本升级打成增量包。

产物（patches/data/，不入库 —— 由 .gitignore 排除，仅作为 GitHub Release
资产上传）：
  <from>-to-<to>.zip        补丁包本体（客户端 PatchEngine 直接消费）
  <from>-to-<to>.meta.json  发布元数据（sha256 / size / notes → 发布器消费）

补丁包结构（与宿主 core:update ZipPatchApplier 契约一致）：
  patch-manifest.json   {schema, target, fromVersion, toVersion, files[]}
  plugin.json           升版后的 manifest（action=replace）
  changelog/<to>.md     本版变更记录（action=add）

同时维护仓库侧的版本事实源（否则 plugin-ci 门禁会拒绝）：
  - plugin.json  version → to
  - CHANGELOG.md 追加 `## v<to>` 一版一条
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def die(msg: str) -> None:
    print(f"[make-patch] ✗ {msg}", file=sys.stderr)
    sys.exit(1)


def ver_tuple(v: str) -> tuple[int, int, int]:
    m = SEMVER.match(v)
    if not m:
        die(f"非法 SemVer：{v!r}")
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser(description="abyss-patch-v1 数据补丁打包")
    parser.add_argument("--to", dest="to_version", required=True, help="目标版本（SemVer）")
    parser.add_argument("--notes", action="append", required=True, help="变更要点（可多次）")
    parser.add_argument("--from", dest="from_version", default=None, help="起始版本（缺省读 plugin.json）")
    args = parser.parse_args()

    manifest_path = Path("plugin.json")
    if not manifest_path.exists():
        die("当前目录不是插件仓库根（缺 plugin.json）")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    pid = manifest.get("id", "")
    if not re.match(r"^abyss-plugin-[a-z0-9]+(-[a-z0-9]+)*$", pid):
        die(f"plugin.json.id 形态非法：{pid!r}")

    frm = args.from_version or manifest.get("version", "")
    to = args.to_version
    if SEMVER.match(frm) is None:
        die(f"起始版本非法：{frm!r}")
    if ver_tuple(to) <= ver_tuple(frm):
        die(f"目标版本必须大于起始版本：{frm} → {to}")

    new_manifest = dict(manifest)
    new_manifest["version"] = to

    # ── 打包 ───────────────────────────────────────────────────────────
    data_dir = Path("patches/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{frm}-to-{to}"
    zip_path = data_dir / f"{stem}.zip"

    payload_manifest = json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n"
    changelog_md = f"# v{to}\n\n" + "\n".join(f"- {n}" for n in args.notes) + "\n"
    patch_manifest = {
        "schema": "abyss-patch-v1",
        "target": pid,
        "fromVersion": frm,
        "toVersion": to,
        "files": [
            {"path": "plugin.json", "action": "replace"},
            {"path": f"changelog/{to}.md", "action": "add"},
        ],
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("patch-manifest.json", json.dumps(patch_manifest, ensure_ascii=False, indent=2) + "\n")
        zf.writestr("plugin.json", payload_manifest)
        zf.writestr(f"changelog/{to}.md", changelog_md)

    sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    size = zip_path.stat().st_size

    meta = {
        "plugin": pid,
        "from": frm,
        "to": to,
        "zip": str(zip_path),
        "assetName": f"{pid}-patch-{stem}.zip",
        "sha256": sha,
        "sizeBytes": size,
        "notes": args.notes,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    meta_path = data_dir / f"{stem}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ── 仓库侧版本事实源同步（plugin-ci 门禁依赖）────────────────────────
    manifest_path.write_text(payload_manifest, encoding="utf-8")
    changelog = Path("CHANGELOG.md")
    if changelog.exists():
        text = changelog.read_text(encoding="utf-8").rstrip("\n")
        entry = f"\n\n## v{to}\n\n" + "\n".join(f"- {n}" for n in args.notes) + "\n"
        if f"## v{to}" not in text:
            changelog.write_text(text + entry, encoding="utf-8")

    print(f"[make-patch] ✓ {pid} {frm} → {to}")
    print(f"[make-patch] 包：{zip_path}（{size} bytes）")
    print(f"[make-patch] sha256 = {sha}")
    print(f"[make-patch] meta → {meta_path}")


if __name__ == "__main__":
    main()
