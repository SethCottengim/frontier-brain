#!/usr/bin/env python3
"""frontier-brain installer — install, upgrade, or uninstall."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MINIMUM_PYTHON = (3, 11)
CLAUDE_HOME = Path.home() / ".claude"
MANIFEST_PATH = CLAUDE_HOME / "frontier-brain" / ".manifest"
SETTINGS_PATH = CLAUDE_HOME / "settings.json"
SETTINGS_BACKUP_PATH = CLAUDE_HOME / "settings.json.bak-frontier-brain"
HOOK_DETECT_SUBSTRING = "decision-detect"


def check_prereqs() -> None:
    if sys.version_info < MINIMUM_PYTHON:
        maj, min_ = MINIMUM_PYTHON
        cur = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"Error: Python {maj}.{min_}+ required (found {cur}).", file=sys.stderr)
        print("Install a newer Python: https://www.python.org/downloads/", file=sys.stderr)
        sys.exit(1)


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_git_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return "unknown"


FILE_MAP: dict[str, str] = {
    "bin/decision-engine.py": "frontier-brain/bin/decision-engine.py",
    "bin/visualize.py": "frontier-brain/bin/visualize.py",
    "bin/static/d3.v7.min.js": "frontier-brain/bin/static/d3.v7.min.js",
    "bin/static/index.html": "frontier-brain/bin/static/index.html",
    "lib/graphdb.py": "frontier-brain/lib/graphdb.py",
    "lib/router.py": "frontier-brain/lib/router.py",
    "lib/frontmatter.py": "frontier-brain/lib/frontmatter.py",
    "hooks/decision-detect.py": "hooks/frontier-brain/decision-detect.py",
    ".claude/skills/decision-recall/SKILL.md": "skills/decision-recall/SKILL.md",
    ".claude/skills/decision-record/SKILL.md": "skills/decision-record/SKILL.md",
    ".claude/skills/decision-harvest/SKILL.md": "skills/decision-harvest/SKILL.md",
    ".claude/skills/open-brain/SKILL.md": "skills/open-brain/SKILL.md",
}


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"commit": None, "installed_at": None, "files": []}


def build_manifest(repo_root: Path, commit: str) -> dict:
    sources: dict[Path, Path] = {}
    files: list[str] = []

    for repo_rel, install_rel in FILE_MAP.items():
        src = repo_root / repo_rel
        if src.exists():
            dst = CLAUDE_HOME / install_rel
            sources[src] = dst
            files.append(str(dst))

    return {
        "commit": commit,
        "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": sorted(files),
        "_sources": sources,
    }


def diff_manifests(old: dict, new: dict) -> dict:
    old_set = set(old.get("files", []))
    new_set = set(new.get("files", []))

    added = sorted(new_set - old_set)
    removed = sorted(old_set - new_set)
    unchanged_or_updated = sorted(new_set & old_set)

    return {
        "added": added,
        "removed": removed,
        "updated": unchanged_or_updated,
        "same_commit": old.get("commit") == new.get("commit"),
    }


def install_files(sources: dict[Path, Path]) -> dict[str, int]:
    copied, skipped = 0, 0
    for src, dst in sources.items():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    return {"copied": copied, "skipped": skipped}


def cleanup_stale(removed_files: list[str]) -> int:
    deleted = 0
    for f in removed_files:
        p = Path(f)
        if p.exists():
            p.unlink()
            deleted += 1
        # remove empty parent dirs up to ~/.claude/
        parent = p.parent
        while parent != CLAUDE_HOME and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return deleted


def reindex_db() -> bool:
    engine = CLAUDE_HOME / "frontier-brain" / "bin" / "decision-engine.py"
    if not engine.exists():
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(engine), "index"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def save_manifest(manifest: dict) -> None:
    clean = {k: v for k, v in manifest.items() if not k.startswith("_")}
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(clean, indent=2) + "\n")


def backup_settings() -> bool:
    if not SETTINGS_PATH.exists():
        return False
    shutil.copy2(SETTINGS_PATH, SETTINGS_BACKUP_PATH)
    return True


def _build_hook_entry(hook_command: str) -> dict:
    return {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": hook_command,
                "timeout": 5,
            }
        ],
    }


def merge_hook(hook_command: str) -> bool:
    if not SETTINGS_PATH.exists():
        settings: dict = {}
    else:
        try:
            settings = json.loads(SETTINGS_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            print("Error: could not parse settings.json. Backup at:", SETTINGS_BACKUP_PATH, file=sys.stderr)
            return False

    hooks = settings.setdefault("hooks", {})
    ups_list: list = hooks.setdefault("UserPromptSubmit", [])

    entry = _build_hook_entry(hook_command)

    for i, existing in enumerate(ups_list):
        for h in existing.get("hooks", []):
            if HOOK_DETECT_SUBSTRING in h.get("command", ""):
                ups_list[i] = entry
                SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n")
                return True

    ups_list.append(entry)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n")
    return True


def remove_hook() -> bool:
    if not SETTINGS_PATH.exists():
        return False
    try:
        settings = json.loads(SETTINGS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return False

    hooks = settings.get("hooks", {})
    ups_list: list = hooks.get("UserPromptSubmit", [])

    filtered = []
    removed = False
    for group in ups_list:
        has_ours = any(
            HOOK_DETECT_SUBSTRING in h.get("command", "")
            for h in group.get("hooks", [])
        )
        if has_ours:
            removed = True
        else:
            filtered.append(group)

    if not removed:
        return False

    if filtered:
        hooks["UserPromptSubmit"] = filtered
    else:
        hooks.pop("UserPromptSubmit", None)
    if not hooks:
        settings.pop("hooks", None)

    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="frontier-brain installer",
        description="Install, upgrade, or uninstall frontier-brain.",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="install",
        choices=["install", "uninstall"],
        help="Action to perform (default: install)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reinstall even if already at current commit",
    )
    return parser.parse_args(argv)


def uninstall() -> None:
    manifest = load_manifest()

    if manifest["commit"] is None and not MANIFEST_PATH.exists():
        print("frontier-brain is not installed (no manifest found).")
        return

    deleted = 0
    for f in manifest.get("files", []):
        p = Path(f)
        if p.exists():
            p.unlink()
            deleted += 1
        parent = p.parent
        while parent != CLAUDE_HOME and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    backup_settings()
    remove_hook()

    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()

    fb_dir = CLAUDE_HOME / "frontier-brain"
    if fb_dir.exists():
        try:
            fb_dir.rmdir()
        except OSError:
            pass

    print(f"Uninstalled frontier-brain ({deleted} files removed).")
    print("Your decisions in ~/.claude/decisions/ were preserved.")


def main(argv: list[str] | None = None) -> None:
    check_prereqs()
    args = parse_args(argv)
    repo_root = get_repo_root()
    commit = get_git_commit(repo_root)

    if args.action == "install":
        old_manifest = load_manifest()
        new_manifest = build_manifest(repo_root, commit)
        diff = diff_manifests(old_manifest, new_manifest)

        if diff["same_commit"] and not args.force:
            print(f"Already up to date ({commit[:8]}). Use --force to reinstall.")
            return

        counts = install_files(new_manifest["_sources"])
        removed = cleanup_stale(diff["removed"])
        save_manifest(new_manifest)

        reindexed = reindex_db()
        db_status = "reindexed" if reindexed else "skipped (no records yet)"

        hook_script = CLAUDE_HOME / "hooks" / "frontier-brain" / "decision-detect.py"
        hook_cmd = f'python3 "{hook_script}"'
        backup_settings()
        hook_ok = merge_hook(hook_cmd)
        hook_status = "registered" if hook_ok else "FAILED (check settings.json)"

        if old_manifest["commit"] is None:
            print(f"Installed frontier-brain ({commit[:8]})")
        else:
            print(f"Upgraded frontier-brain ({old_manifest['commit'][:8]} → {commit[:8]})")

        print(f"  {counts['copied']} files copied, {removed} stale files removed")
        print(f"  brain.db: {db_status}")
        print(f"  hook: {hook_status}")

    elif args.action == "uninstall":
        uninstall()


if __name__ == "__main__":
    main()
