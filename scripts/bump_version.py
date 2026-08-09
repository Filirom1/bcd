#!/usr/bin/env python3
"""
Unified version bumping script for BCD API and Kids client.

Creates one tag:
  - v*.*.*  (triggers all releases: API Windows/Linux + Kids Windows/Linux)

Usage:
    python scripts/bump_version.py patch   # 1.0.0 -> 1.0.1
    python scripts/bump_version.py minor   # 1.0.0 -> 1.1.0
    python scripts/bump_version.py major   # 1.0.0 -> 2.0.0
    python scripts/bump_version.py --current  # Show current version
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def read_current_version() -> str:
    """Read current version from pyproject.toml (single source of truth)."""
    pyproject_path = get_project_root() / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"❌ Error: {pyproject_path} not found")
        sys.exit(1)

    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)

    if not match:
        print("❌ Error: Could not find version in pyproject.toml")
        sys.exit(1)

    return match.group(1)


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse version string into (major, minor, patch)."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version)
    if not match:
        print(f"❌ Error: Invalid version format: {version}")
        sys.exit(1)

    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(current: str, bump_type: str) -> str:
    """Bump version according to type (major, minor, patch)."""
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"❌ Error: Invalid bump type: {bump_type}")
        print("   Valid types: major, minor, patch")
        sys.exit(1)


def update_pyproject_toml(new_version: str) -> None:
    """Update version in pyproject.toml."""
    pyproject_path = get_project_root() / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")

    # Replace version line
    new_content = re.sub(
        r'^version\s*=\s*["\'][^"\']+["\']',
        f'version = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE
    )

    pyproject_path.write_text(new_content, encoding="utf-8")
    print(f"✅ Updated pyproject.toml: version = \"{new_version}\"")


def update_godot_project(new_version: str) -> None:
    """Update version in Kids client project.godot."""
    project_path = get_project_root() / "bcd_kids" / "project.godot"

    if not project_path.exists():
        print(f"⚠️  Warning: {project_path} not found, skipping project.godot version update")
        return

    content = project_path.read_text(encoding="utf-8")

    new_content = re.sub(
        r'config/version="[^"]+"',
        f'config/version="{new_version}"',
        content
    )

    project_path.write_text(new_content, encoding="utf-8")
    print(f"✅ Updated bcd_kids/project.godot: config/version = \"{new_version}\"")


def update_godot_export_presets(new_version: str) -> None:
    """Update version in Kids client export_presets.cfg."""
    presets_path = get_project_root() / "bcd_kids" / "export_presets.cfg"

    if not presets_path.exists():
        print(f"⚠️  Warning: {presets_path} not found, skipping Godot version update")
        return

    content = presets_path.read_text(encoding="utf-8")

    # Windows version format: "1.0.0.0"
    windows_version = f"{new_version}.0"

    # Replace file_version
    new_content = re.sub(
        r'application/file_version="[^"]+"',
        f'application/file_version="{windows_version}"',
        content
    )

    # Replace product_version
    new_content = re.sub(
        r'application/product_version="[^"]+"',
        f'application/product_version="{windows_version}"',
        new_content
    )

    presets_path.write_text(new_content, encoding="utf-8")
    print(f"✅ Updated bcd_kids/export_presets.cfg")
    print(f"   - file_version = \"{windows_version}\"")
    print(f"   - product_version = \"{windows_version}\"")


def run_git_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=get_project_root(),
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: git {' '.join(args)}")
        print(f"   Error: {e.stderr.strip()}")
        sys.exit(1)


def check_git_status() -> bool:
    """Check if there are uncommitted changes."""
    result = run_git_command(["status", "--porcelain"])
    return len(result.stdout.strip()) > 0


def create_version_commit(version: str) -> None:
    """Create a git commit for the version bump."""
    # Stage both files
    run_git_command(["add", "pyproject.toml"])

    godot_project = get_project_root() / "bcd_kids" / "project.godot"
    if godot_project.exists():
        run_git_command(["add", "bcd_kids/project.godot"])

    godot_presets = get_project_root() / "bcd_kids" / "export_presets.cfg"
    if godot_presets.exists():
        run_git_command(["add", "bcd_kids/export_presets.cfg"])

    # Create commit
    commit_message = f"chore: bump version to {version}"
    run_git_command(["commit", "-m", commit_message])

    print(f"✅ Created commit: {commit_message}")


def create_git_tags(version: str, push: bool = False) -> None:
    """Create git tag for unified release (API + Kids client)."""
    tag = f"v{version}"

    # Create unified tag
    run_git_command(["tag", "-a", tag, "-m", f"Release version {version} (API + Kids client)"])
    print(f"✅ Created tag: {tag} (triggers all releases)")

    if push:
        # Push commit and tag
        print("📤 Pushing commit and tag to remote...")
        run_git_command(["push"])
        run_git_command(["push", "--tags"])
        print(f"✅ Pushed {tag} to remote")


def verify_changelog_has_version(version: str) -> None:
    """Check if CHANGELOG.md describes the version being bumped."""
    changelog_path = get_project_root() / "CHANGELOG.md"
    if not changelog_path.exists():
        print("⚠️  Warning: CHANGELOG.md not found")
        return

    content = changelog_path.read_text(encoding="utf-8")
    # Matches markdown headers like: ## [1.1.0] or ## 1.1.0
    pattern = rf"##\s*\[?{re.escape(version)}\]?"
    if not re.search(pattern, content):
        print(f"❌ Error: {version} is not documented in CHANGELOG.md")
        print("   Please add release notes to CHANGELOG.md before bumping the version.")
        sys.exit(1)
    print(f"✅ Verified {version} is documented in CHANGELOG.md")


def main():
    parser = argparse.ArgumentParser(
        description="Bump version for BCD API and Kids client (unified)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/bump_version.py patch         # 1.0.0 -> 1.0.1
  python scripts/bump_version.py minor         # 1.0.0 -> 1.1.0
  python scripts/bump_version.py major         # 1.0.0 -> 2.0.0
  python scripts/bump_version.py --current     # Show current version
  python scripts/bump_version.py patch --push  # Bump and push to remote

This script updates BOTH:
  - pyproject.toml (API version)
  - bcd_kids/export_presets.cfg (Godot client version)

And creates TWO tags:
  - v*.*.*       (triggers .github/workflows/release-*.yml)
  - godot-v*.*.* (triggers .github/workflows/release-godot.yml)
        """
    )

    parser.add_argument(
        "bump_type",
        nargs="?",
        choices=["major", "minor", "patch"],
        help="Type of version bump"
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="Show current version and exit"
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push commit and tags to remote after creating"
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Only update files, don't create commit or tags"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompts (auto-confirm)"
    )

    args = parser.parse_args()

    current_version = read_current_version()

    if args.current:
        print(f"Current version: {current_version}")
        return

    if not args.bump_type:
        parser.print_help()
        print(f"\nℹ️  Current version: {current_version}")
        sys.exit(1)

    # Calculate new version
    new_version = bump_version(current_version, args.bump_type)

    # Verify changelog describes the new version
    verify_changelog_has_version(new_version)

    print(f"\n📦 Unified Version Bump: {current_version} → {new_version}")
    print(f"   Type: {args.bump_type}")
    print(f"   Tag: v{new_version}")

    # Check for uncommitted changes
    if check_git_status():
        status_output = run_git_command(["status", "--porcelain"]).stdout
        lines = [line for line in status_output.strip().split("\n") if line]

        # Allow if only version files are modified
        allowed_files = ["pyproject.toml", "export_presets.cfg"]
        if any(not any(f in line for f in allowed_files) for line in lines):
            print("\n⚠️  Warning: You have uncommitted changes")
            print("   Commit or stash them before bumping version")
            if not args.yes and sys.stdin.isatty():
                response = input("\n   Continue anyway? [y/N]: ")
                if response.lower() != "y":
                    print("❌ Aborted")
                    sys.exit(1)
            else:
                print("   ⚠️  Auto-continuing (non-interactive mode)")

    # Ask for confirmation
    if not args.yes and sys.stdin.isatty():
        print()
        response = input("Continue? [Y/n]: ")
        if response.lower() == "n":
            print("❌ Aborted")
            sys.exit(1)
    else:
        print("   ✅ Auto-confirmed (non-interactive mode)")

    # Update all files
    update_pyproject_toml(new_version)
    update_godot_project(new_version)
    update_godot_export_presets(new_version)

    if args.no_commit:
        print("\n✅ Version updated in both files")
        print("   (No commit or tags created)")
        return

    # Create commit and tags
    create_version_commit(new_version)
    create_git_tags(new_version, push=args.push)

    print(f"\n✅ Version bump complete!")
    print(f"   New version: {new_version}")
    print(f"   Tag: v{new_version}")

    if not args.push:
        print("\nℹ️  To push to remote, run:")
        print(f"   git push && git push --tags")


if __name__ == "__main__":
    main()
