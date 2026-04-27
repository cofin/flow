#!/usr/bin/env python3
# /// script
# dependencies = [
#   "rich-click",
#   "rich",
#   "tomli; python_version < '3.11'",
# ]
# ///
"""Bundle Python dependencies into a standalone distribution for PyApp embedding."""

import contextlib
import os
import platform as host_platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import rich_click as click
from rich.console import Console
from rich.rule import Rule

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef,import-not-found]


DEFAULT_PYTHON_VERSION = "3.13"
DEFAULT_INSTALL_ROOT = "~/.local"
DEFAULT_CACHE_DIRNAME = ".cache/bundler"

# Target Standalone Python Distributions
# Update these URLs as new releases become available.
DEFAULT_URLS: dict[str, str] = {
    "x86_64-unknown-linux-gnu": "https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-3.13.9%2B20251014-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz",
    "aarch64-unknown-linux-gnu": "https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-3.13.9%2B20251014-aarch64-unknown-linux-gnu-install_only_stripped.tar.gz",
    "x86_64-apple-darwin": "https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-3.13.9%2B20251014-x86_64-apple-darwin-install_only_stripped.tar.gz",
    "aarch64-apple-darwin": "https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-3.13.9%2B20251014-aarch64-apple-darwin-install_only_stripped.tar.gz",
    "x86_64-pc-windows-msvc": "https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-3.13.9%2B20251014-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
}

# Cross-Installation Target Platforms for uv pip
DEFAULT_PLATFORMS: dict[str, str] = {
    "x86_64-unknown-linux-gnu": "x86_64-manylinux_2_28",
    "aarch64-unknown-linux-gnu": "aarch64-manylinux_2_28",
    "x86_64-apple-darwin": "x86_64-apple-darwin",
    "aarch64-apple-darwin": "aarch64-apple-darwin",
    "x86_64-pc-windows-msvc": "x86_64-pc-windows-msvc",
}

console = Console()


def left_aligned_rule(title: str, style: str = "blue") -> None:
    rule = Rule(title, style=style, align="left")
    console.print(rule)


def resolve_project_dir(project_dir: str | None) -> Path:
    base = Path(project_dir or Path.cwd()).expanduser().resolve()
    if not base.exists():
        msg = f"Project directory not found: {base}"
        raise click.ClickException(msg)
    return base


def load_pyproject(project_dir: Path) -> dict[str, Any]:
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return {}
    try:
        return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        msg = f"Failed to parse {pyproject_path}: {exc}"
        raise click.ClickException(msg) from exc


def detect_project_name(project_dir: Path, override: str | None) -> str:
    if override:
        return override
    pyproject = load_pyproject(project_dir)
    project_name = pyproject.get("project", {}).get("name")
    return project_name or project_dir.name


def download_with_retry(url: str, dest: Path, max_retries: int = 3) -> None:
    for attempt in range(max_retries):
        try:
            console.print(f"[blue]Downloading[/] {url}...")
            urllib.request.urlretrieve(url, dest)
            if dest.exists() and dest.stat().st_size > 0:
                return
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                console.print(f"[yellow]Warning:[/] Retry {attempt+1}: {exc}")
            else:
                raise click.ClickException(f"Download failed: {exc}") from exc


def find_site_packages(python_root: Path, target: str, python_version: str) -> Path:
    if "windows" in target:
        site_packages = python_root / "Lib" / "site-packages"
    else:
        major_minor = ".".join(python_version.split(".")[:2])
        site_packages = python_root / "lib" / f"python{major_minor}" / "site-packages"
    
    if site_packages.exists():
        return site_packages
        
    for root, dirs, _ in os.walk(python_root):
        if "site-packages" in dirs:
            return Path(root) / "site-packages"
            
    raise click.ClickException("Could not locate site-packages")


def install_requirements(requirements_path: Path, site_packages: Path, platform: str, python_version: str) -> None:
    pip_cmd = [
        "uv", "pip", "install", "--color", "never",
        "-r", str(requirements_path),
        "--target", str(site_packages),
        "--python-platform", platform,
        "--python-version", python_version,
        "--upgrade", "--no-deps"
    ]
    try:
        subprocess.check_call(pip_cmd)
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(f"pip install failed: {exc}") from exc


def patch_pyapp_install_dir(pyapp_dir: Path, install_dir: str) -> None:
    """Patch PyApp to use a custom default installation directory."""
    app_rs = pyapp_dir / "src" / "app.rs"
    if not app_rs.exists():
        raise click.ClickException(f"PyApp source not found at {app_rs}")

    content = app_rs.read_text(encoding="utf-8")
    pattern = re.compile(
        r"platform_dirs\(\)\s*\.data_local_dir\(\)\s*"
        r"\.join\(project_name\(\)\)"
    )
    if not pattern.search(content):
        # Fallback or Warning if structure changed in newer PyApp
        console.print("[yellow]Warning:[/] Could not locate app.rs install block to patch.")
        return

    replacement = f"std::path::PathBuf::from(\"{install_dir}\")"
    updated = pattern.sub(replacement, content, count=1)
    app_rs.write_text(updated, encoding="utf-8")
    console.print(f"[green]Patched[/] PyApp install dir -> {install_dir}")


@click.group(help="Bundle dependencies for offline PyApp.")
def cli() -> None: pass


@cli.command("build")
@click.option("--target", required=True, help="Rust target architecture")
@click.option("--requirements", type=click.Path(path_type=Path), required=True)
@click.option("--output", help="Output path (.tar.gz)")
@click.option("--install-dir", help="Custom static installation path (e.g., ~/.myapp)")
@click.option("--pyapp-dir", type=click.Path(path_type=Path), help="Patch PyApp source checkout before build")
def build_bundle(target: str, requirements: Path, output: str | None, install_dir: str | None, pyapp_dir: Path | None) -> None:
    """Bundle dependencies and optionally patch PyApp source."""
    
    if pyapp_dir and install_dir:
        patch_pyapp_install_dir(pyapp_dir, install_dir)

    url = DEFAULT_URLS.get(target)
    platform = DEFAULT_PLATFORMS.get(target)
    
    if not url or not platform:
        raise click.ClickException(f"Unsupported target: {target}")

    work_dir = Path(tempfile.mkdtemp(prefix="pyapp-bundler-"))
    try:
        archive_path = work_dir / "python.tar.gz"
        download_with_retry(url, archive_path)

        extract_dir = work_dir / "extracted"
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_dir)

        python_root = extract_dir / "python"
        site_packages = find_site_packages(python_root, target, DEFAULT_PYTHON_VERSION)

        install_requirements(requirements, site_packages, platform, DEFAULT_PYTHON_VERSION)

        out_path = Path(output or f"python-dist-{target}.tar.gz")
        with tarfile.open(out_path, "w:gz") as tar:
            tar.add(python_root, arcname="python")

        console.print(f"[bold green]Created offline distribution:[/] {out_path}")
    finally:
        shutil.rmtree(work_dir)


if __name__ == "__main__":
    cli()
