"""Build a Kodi repository tree for publishing with GitHub Pages."""

from __future__ import annotations

import argparse
import hashlib
import html
import os
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


BASE_URL = "https://wdty.github.io/nlziet-kodi-addon/"
REPOSITORY_ADDON_ID = "repository.wdty.nlziet"
REPOSITORY_SOURCE_DIR = REPOSITORY_ADDON_ID
DEFAULT_OUTPUT_DIR = Path("build") / "kodi-repository"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ALLOWED_WORKFLOW_DISPATCH_REFS = {
    "refs/heads/develop",
    "refs/heads/tooling/kodi-development-repository",
}
PUBLISH_TAG_PREFIX = "refs/tags/kodi-repo-"

EXCLUDED_DIRS = {
    ".git",
    ".github",
    ".cache",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".idea",
    ".vscode",
    "__pycache__",
    "docs",
    "env",
    "node_modules",
    "scripts",
    "tests",
    "venv",
    "build",
    "dist",
    "site",
    "package_build",
    "package_clean",
    REPOSITORY_SOURCE_DIR,
}
EXCLUDED_FILES = {
    ".coverage",
    ".DS_Store",
    ".gitignore",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


@dataclass(frozen=True)
class AddonMetadata:
    addon_id: str
    name: str
    version: str


@dataclass(frozen=True)
class BuildResult:
    output_dir: Path
    addon_zip: Path
    repository_zip: Path
    stable_repository_zip: Path
    addons_xml: Path
    addons_xml_md5: Path
    index_html: Path


class BuildError(RuntimeError):
    """Raised when the repository cannot be built safely."""


def validate_publish_ref(event_name: str, ref: str) -> None:
    if event_name == "workflow_dispatch" and ref in ALLOWED_WORKFLOW_DISPATCH_REFS:
        return
    if event_name == "push" and ref.startswith(PUBLISH_TAG_PREFIX):
        return

    allowed_branches = ", ".join(sorted(ALLOWED_WORKFLOW_DISPATCH_REFS))
    raise BuildError(
        "Unsupported publish ref. "
        f"workflow_dispatch is allowed only from {allowed_branches}; "
        f"push deployment is allowed only for tags matching {PUBLISH_TAG_PREFIX}*; "
        f"got event={event_name!r}, ref={ref!r}."
    )


def parse_addon_metadata(addon_xml: Path) -> AddonMetadata:
    if not addon_xml.is_file():
        raise BuildError(f"Required file is missing: {addon_xml}")

    try:
        root = ET.parse(addon_xml).getroot()
    except ET.ParseError as exc:
        raise BuildError(f"Invalid XML in {addon_xml}: {exc}") from exc

    if root.tag != "addon":
        raise BuildError(f"{addon_xml} must contain an <addon> root element")

    missing = [name for name in ("id", "name", "version") if not root.get(name)]
    if missing:
        raise BuildError(f"{addon_xml} is missing required attribute(s): {', '.join(missing)}")

    return AddonMetadata(
        addon_id=root.attrib["id"],
        name=root.attrib["name"],
        version=root.attrib["version"],
    )


def validate_addon_root(root_dir: Path) -> AddonMetadata:
    addon_xml = root_dir / "addon.xml"
    metadata = parse_addon_metadata(addon_xml)

    required_files = [
        addon_xml,
        root_dir / "default.py",
        root_dir / "icon.png",
        root_dir / REPOSITORY_SOURCE_DIR / "addon.xml",
        root_dir / REPOSITORY_SOURCE_DIR / "icon.png",
    ]
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise BuildError("Required file(s) missing:\n" + "\n".join(missing))

    if metadata.addon_id != "plugin.video.nlziet":
        raise BuildError(
            f"Expected add-on source id 'plugin.video.nlziet', found {metadata.addon_id!r}"
        )

    return metadata


def validate_output_dir(root_dir: Path, output_dir: Path) -> None:
    if output_dir == root_dir:
        raise BuildError("Output directory must not be the add-on source root")
    if root_dir.is_relative_to(output_dir):
        raise BuildError("Output directory must not contain the add-on source root")
    if output_dir.parent == output_dir:
        raise BuildError("Output directory must not be a filesystem root")


def should_exclude(path: Path, root_dir: Path) -> bool:
    rel = path.relative_to(root_dir)
    parts = rel.parts

    if any(part in EXCLUDED_DIRS for part in parts[:-1]):
        return True

    name = path.name
    if path.is_dir():
        return name in EXCLUDED_DIRS
    if name in EXCLUDED_FILES:
        return True
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    if name.endswith(".zip"):
        return True
    return False


def iter_addon_files(source_dir: Path) -> list[Path]:
    files: list[Path] = []
    for current_dir, dir_names, file_names in os.walk(source_dir):
        current = Path(current_dir)
        kept_dirs = []
        for name in sorted(dir_names):
            dir_path = current / name
            if dir_path.is_symlink():
                raise BuildError(f"Symlinked directories are not allowed in builds: {dir_path}")
            if not should_exclude(dir_path, source_dir):
                kept_dirs.append(name)
        dir_names[:] = kept_dirs
        for file_name in sorted(file_names):
            file_path = current / file_name
            if not should_exclude(file_path, source_dir):
                if file_path.is_symlink():
                    raise BuildError(f"Symlinked files are not allowed in builds: {file_path}")
                files.append(file_path)
    return sorted(files, key=lambda path: path.relative_to(source_dir).as_posix())


def write_deterministic_zip(
    zip_path: Path,
    source_dir: Path,
    top_level_dir: str,
    files: list[Path] | None = None,
) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    files = files if files is not None else iter_addon_files(source_dir)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            rel = file_path.relative_to(source_dir).as_posix()
            archive_name = f"{top_level_dir}/{rel}"
            info = zipfile.ZipInfo(archive_name, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            archive.writestr(info, file_path.read_bytes())


def repository_urls(base_url: str) -> dict[str, str]:
    normalized = base_url.rstrip("/") + "/"
    return {
        "base": normalized,
        "info": normalized + "addons.xml",
        "checksum": normalized + "addons.xml.md5",
        "datadir": normalized + "zips/",
        "repository_zip": normalized + f"{REPOSITORY_ADDON_ID}.zip",
    }


def _rewrite_repository_urls(addon_element: ET.Element, base_url: str) -> None:
    urls = repository_urls(base_url)
    extension = addon_element.find("extension[@point='xbmc.addon.repository']")
    if extension is None:
        raise BuildError(f"{REPOSITORY_SOURCE_DIR}/addon.xml is missing repository extension")

    info = extension.find("info")
    checksum = extension.find("checksum")
    datadir = extension.find("datadir")
    if info is None or checksum is None or datadir is None:
        raise BuildError("Repository addon.xml must contain info, checksum, and datadir")

    info.text = urls["info"]
    checksum.text = urls["checksum"]
    datadir.text = urls["datadir"]


def _load_addon_element(addon_xml: Path) -> ET.Element:
    try:
        return ET.parse(addon_xml).getroot()
    except ET.ParseError as exc:
        raise BuildError(f"Invalid XML in {addon_xml}: {exc}") from exc


def generate_addons_xml(root_dir: Path, base_url: str) -> bytes:
    addons = ET.Element("addons")

    plugin = _load_addon_element(root_dir / "addon.xml")
    addons.append(plugin)

    repository = _load_addon_element(root_dir / REPOSITORY_SOURCE_DIR / "addon.xml")
    _rewrite_repository_urls(repository, base_url)
    addons.append(repository)

    ET.indent(addons, space="  ")
    xml_body = ET.tostring(addons, encoding="unicode", short_empty_elements=True)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + xml_body + "\n").encode("utf-8")


def write_index_html(path: Path, addon_metadata: AddonMetadata, urls: dict[str, str]) -> None:
    title = "WDTY NLZiet Kodi Development Repository"
    escaped_name = html.escape(addon_metadata.name)
    escaped_zip_url = html.escape(urls["repository_zip"], quote=True)
    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 3rem auto; padding: 0 1rem; line-height: 1.55; }}
    code {{ background: #f1f3f5; padding: 0.1rem 0.25rem; border-radius: 0.25rem; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>This is an unofficial personal development repository for {escaped_name}. It is not the upstream maintainer's official repository.</p>
  <p>Download <a href="{escaped_zip_url}">{REPOSITORY_ADDON_ID}.zip</a>, then install it in Kodi with <strong>Install from zip file</strong>. After that, install or update <code>{addon_metadata.addon_id}</code> from the repository.</p>
  <p>A valid NLZiet subscription is required to use the add-on. This repository hosts only add-on packages and metadata; it does not host credentials, tokens, cookies, or NLZiet account data.</p>
  <p>Development updates are offered by Kodi only when the version in <code>addon.xml</code> is increased before publishing.</p>
</body>
</html>
"""
    path.write_text(content, encoding="utf-8", newline="\n")


def build_repository(root_dir: Path, output_dir: Path, base_url: str = BASE_URL) -> BuildResult:
    root_dir = root_dir.resolve()
    output_dir = output_dir.resolve()
    metadata = validate_addon_root(root_dir)
    repository_metadata = parse_addon_metadata(root_dir / REPOSITORY_SOURCE_DIR / "addon.xml")
    validate_output_dir(root_dir, output_dir)

    if repository_metadata.addon_id != REPOSITORY_ADDON_ID:
        raise BuildError(
            f"Repository add-on id must be {REPOSITORY_ADDON_ID!r}, found {repository_metadata.addon_id!r}"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    addon_zip = (
        output_dir
        / "zips"
        / metadata.addon_id
        / f"{metadata.addon_id}-{metadata.version}.zip"
    )
    repository_zip = (
        output_dir
        / "zips"
        / repository_metadata.addon_id
        / f"{repository_metadata.addon_id}-{repository_metadata.version}.zip"
    )
    stable_repository_zip = output_dir / f"{REPOSITORY_ADDON_ID}.zip"

    write_deterministic_zip(addon_zip, root_dir, metadata.addon_id)
    repository_source = root_dir / REPOSITORY_SOURCE_DIR
    write_deterministic_zip(repository_zip, repository_source, repository_metadata.addon_id)
    shutil.copyfile(repository_zip, stable_repository_zip)

    addons_xml = output_dir / "addons.xml"
    addons_xml.write_bytes(generate_addons_xml(root_dir, base_url))

    addons_xml_md5 = output_dir / "addons.xml.md5"
    addons_xml_md5.write_text(
        hashlib.md5(addons_xml.read_bytes()).hexdigest(), encoding="ascii", newline="\n"
    )

    index_html = output_dir / "index.html"
    write_index_html(index_html, metadata, repository_urls(base_url))

    return BuildResult(
        output_dir=output_dir,
        addon_zip=addon_zip,
        repository_zip=repository_zip,
        stable_repository_zip=stable_repository_zip,
        addons_xml=addons_xml,
        addons_xml_md5=addons_xml_md5,
        index_html=index_html,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Add-on source root containing addon.xml.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Generated GitHub Pages output directory.",
    )
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help="Public base URL for the GitHub Pages repository.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = build_repository(args.root, args.output, args.base_url)
    except BuildError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(f"Pages output: {result.output_dir}")
    print(f"Plugin ZIP: {result.addon_zip}")
    print(f"Repository ZIP: {result.repository_zip}")
    print(f"Stable repository ZIP: {result.stable_repository_zip}")
    print(f"Addons XML: {result.addons_xml}")
    print(f"Addons XML MD5: {result.addons_xml_md5}")
    print(f"Index HTML: {result.index_html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
