#!/usr/bin/env python3
"""把 src/ 打包成 BetterNCM 插件包（.plugin 就是改名的 zip）。

用法：
    python build.py            打包到 dist/
    python build.py --install  打包后顺便复制到 C:\\betterncm\\plugins\\
"""

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
PLUGINS_DIR = Path(r"C:\betterncm\plugins")
PLUGINS_RUNTIME = Path(r"C:\betterncm\plugins_runtime")

# 包名用 manifest 里的 slug（BetterNCM 插件商店的惯例：<slug>-<version>.plugin）
SLUG = json.loads((SRC / "manifest.json").read_text(encoding="utf-8"))["slug"]
# 安装时一并清理的旧包名 / 旧运行时目录（含改名前的遗留，避免两个 slug 抢 channel.call）
LEGACY_PREFIXES = ("WebPlayer-", "GaplessPlayer-", f"{SLUG}-")
LEGACY_RUNTIME = ("webplayer", "GaplessPlayer")

EXCLUDE = {".DS_Store", "Thumbs.db"}


def read_version() -> str:
    manifest = json.loads((SRC / "manifest.json").read_text(encoding="utf-8"))
    return manifest["version"]


def build() -> Path:
    version = read_version()
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{SLUG}-{version}.plugin"

    files = sorted(p for p in SRC.rglob("*") if p.is_file() and p.name not in EXCLUDE)
    if not files:
        sys.exit(f"src/ 里没有文件：{SRC}")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(SRC).as_posix())

    print(f"已生成 {out}  ({out.stat().st_size / 1024:.1f} KB, {len(files)} 个文件)")
    for path in files:
        print(f"  + {path.relative_to(SRC).as_posix()}")
    return out


def install(plugin: Path) -> None:
    if not PLUGINS_DIR.is_dir():
        sys.exit(f"找不到 BetterNCM 插件目录：{PLUGINS_DIR}")

    for prefix in LEGACY_PREFIXES:
        for old in PLUGINS_DIR.glob(f"{prefix}*.plugin"):
            if old.name != plugin.name:
                old.unlink()
                print(f"已删除旧版本 {old.name}")

    target = PLUGINS_DIR / plugin.name
    shutil.copy2(plugin, target)
    print(f"已安装到 {target}")

    for name in (SLUG,) + LEGACY_RUNTIME:
        runtime = PLUGINS_RUNTIME / name
        if runtime.is_dir():
            shutil.rmtree(runtime)
            print(f"已清理旧运行时目录 {runtime}")
    print("请重启网易云音乐使插件生效。")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true", help="打包后安装到 BetterNCM")
    args = ap.parse_args()

    plugin = build()
    if args.install:
        install(plugin)


if __name__ == "__main__":
    main()
