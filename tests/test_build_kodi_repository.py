import hashlib
import importlib.util
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_kodi_repository.py"
SPEC = importlib.util.spec_from_file_location("build_kodi_repository", SCRIPT_PATH)
build_kodi_repository = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_kodi_repository
SPEC.loader.exec_module(build_kodi_repository)


def _write_minimal_addon(root):
    (root / "resources" / "media").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "tests").mkdir()
    (root / "docs").mkdir()
    (root / "build" / "kodi-repository").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "__pycache__").mkdir()
    (root / "repository.wdty.nlziet").mkdir()

    (root / "addon.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<addon id="plugin.video.nlziet" name="NLZiet" version="1.2.3" provider-name="WDTY">
  <requires>
    <import addon="xbmc.python" version="3.0.0" />
  </requires>
  <extension point="xbmc.python.pluginsource" library="default.py">
    <provides>video</provides>
  </extension>
  <extension point="xbmc.addon.metadata">
    <summary lang="en">NLZiet</summary>
    <assets>
      <icon>icon.png</icon>
      <fanart>resources/media/background.jpg</fanart>
    </assets>
  </extension>
</addon>
""",
        encoding="utf-8",
    )
    (root / "default.py").write_text("print('addon')\n", encoding="utf-8")
    (root / "icon.png").write_bytes(b"icon")
    (root / "fanart.jpg").write_bytes(b"fanart")
    (root / "resources" / "media" / "background.jpg").write_bytes(b"background")

    (root / "tests" / "test_ignored.py").write_text("ignored = True\n", encoding="utf-8")
    (root / "docs" / "ignored.md").write_text("ignored\n", encoding="utf-8")
    (root / "build" / "kodi-repository" / "addons.xml").write_text(
        "<addons />\n", encoding="utf-8"
    )
    (root / "build" / "kodi-repository" / "ignored.zip").write_bytes(b"zip")
    (root / ".coverage").write_text("coverage\n", encoding="utf-8")
    (root / "__pycache__" / "ignored.pyc").write_bytes(b"bytecode")
    (root / "ignored.pyc").write_bytes(b"bytecode")

    (root / "repository.wdty.nlziet" / "addon.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<addon id="repository.wdty.nlziet" name="Repo" version="0.1.0" provider-name="WDTY">
  <extension point="xbmc.addon.repository" name="Repo">
    <dir>
      <info compressed="false">placeholder</info>
      <checksum>placeholder</checksum>
      <datadir zip="true">placeholder</datadir>
    </dir>
  </extension>
  <extension point="xbmc.addon.metadata">
    <summary lang="en">Repo</summary>
    <assets>
      <icon>icon.png</icon>
    </assets>
  </extension>
</addon>
""",
        encoding="utf-8",
    )
    (root / "repository.wdty.nlziet" / "icon.png").write_bytes(b"repo-icon")


def test_parse_addon_metadata(tmp_path):
    _write_minimal_addon(tmp_path)

    metadata = build_kodi_repository.parse_addon_metadata(tmp_path / "addon.xml")

    assert metadata.addon_id == "plugin.video.nlziet"
    assert metadata.name == "NLZiet"
    assert metadata.version == "1.2.3"


def test_build_writes_zip_with_addon_id_top_level_and_excludes_development_files(tmp_path):
    _write_minimal_addon(tmp_path)

    result = build_kodi_repository.build_repository(tmp_path, tmp_path / "pages")

    with zipfile.ZipFile(result.addon_zip) as archive:
        names = archive.namelist()

    assert names == sorted(names)
    assert all(name.startswith("plugin.video.nlziet/") for name in names)
    assert "plugin.video.nlziet/addon.xml" in names
    assert "plugin.video.nlziet/default.py" in names
    assert "plugin.video.nlziet/icon.png" in names
    assert "plugin.video.nlziet/fanart.jpg" in names
    assert not any("/tests/" in name for name in names)
    assert not any("/docs/" in name for name in names)
    assert not any("/build/" in name for name in names)
    assert not any("__pycache__" in name for name in names)
    assert not any(name.endswith(".pyc") for name in names)
    assert not any("repository.wdty.nlziet/" in name for name in names)


def test_build_generates_addons_xml_with_repository_urls(tmp_path):
    _write_minimal_addon(tmp_path)
    base_url = "https://example.test/kodi/"

    result = build_kodi_repository.build_repository(tmp_path, tmp_path / "pages", base_url)
    root = ET.parse(result.addons_xml).getroot()

    addon_ids = [addon.attrib["id"] for addon in root.findall("addon")]
    assert addon_ids == ["plugin.video.nlziet", "repository.wdty.nlziet"]
    assert root.find("addon[@id='plugin.video.nlziet']").attrib["version"] == "1.2.3"

    repository = root.find("addon[@id='repository.wdty.nlziet']")
    extension = repository.find("extension[@point='xbmc.addon.repository']")
    directory = extension.find("dir")
    assert directory is not None
    assert extension.find("info") is None
    assert extension.find("checksum") is None
    assert extension.find("datadir") is None
    assert directory.findtext("info") == "https://example.test/kodi/addons.xml"
    assert directory.findtext("checksum") == "https://example.test/kodi/addons.xml.md5"
    assert directory.findtext("datadir") == "https://example.test/kodi/zips/"


def test_build_generates_correct_md5_checksum(tmp_path):
    _write_minimal_addon(tmp_path)

    result = build_kodi_repository.build_repository(tmp_path, tmp_path / "pages")

    expected = hashlib.md5(result.addons_xml.read_bytes()).hexdigest()
    assert result.addons_xml_md5.read_text(encoding="ascii") == expected


def test_repository_url_generation_normalizes_base_url():
    urls = build_kodi_repository.repository_urls("https://example.test/kodi")

    assert urls["info"] == "https://example.test/kodi/addons.xml"
    assert urls["checksum"] == "https://example.test/kodi/addons.xml.md5"
    assert urls["datadir"] == "https://example.test/kodi/zips/"
    assert urls["repository_zip"] == "https://example.test/kodi/repository.wdty.nlziet.zip"


def test_build_writes_repository_zip_to_stable_pages_url(tmp_path):
    _write_minimal_addon(tmp_path)

    result = build_kodi_repository.build_repository(tmp_path, tmp_path / "pages")

    assert result.repository_zip.is_file()
    assert result.stable_repository_zip.is_file()
    assert result.stable_repository_zip.name == "repository.wdty.nlziet.zip"
    assert result.stable_repository_zip.read_bytes() == result.repository_zip.read_bytes()
    with zipfile.ZipFile(result.stable_repository_zip) as archive:
        assert archive.namelist() == [
            "repository.wdty.nlziet/addon.xml",
            "repository.wdty.nlziet/icon.png",
        ]


def test_both_zips_have_exactly_one_expected_top_level_directory(tmp_path):
    _write_minimal_addon(tmp_path)

    result = build_kodi_repository.build_repository(tmp_path, tmp_path / "pages")

    for zip_path, expected in [
        (result.addon_zip, "plugin.video.nlziet"),
        (result.repository_zip, "repository.wdty.nlziet"),
    ]:
        with zipfile.ZipFile(zip_path) as archive:
            top_levels = {name.split("/")[0] for name in archive.namelist()}
        assert top_levels == {expected}


def test_build_preserves_source_addon_xml_and_uses_exact_version(tmp_path):
    _write_minimal_addon(tmp_path)
    source_addon_xml = tmp_path / "addon.xml"
    original_xml = source_addon_xml.read_text(encoding="utf-8")

    result = build_kodi_repository.build_repository(tmp_path, tmp_path / "pages")

    assert source_addon_xml.read_text(encoding="utf-8") == original_xml
    assert result.addon_zip.name == "plugin.video.nlziet-1.2.3.zip"
    generated = ET.parse(result.addons_xml).getroot()
    plugin = generated.find("addon[@id='plugin.video.nlziet']")
    assert plugin.attrib["version"] == "1.2.3"


def test_generated_files_do_not_contain_local_absolute_paths(tmp_path):
    _write_minimal_addon(tmp_path)

    result = build_kodi_repository.build_repository(tmp_path, tmp_path / "pages")
    generated_text = (
        result.addons_xml.read_text(encoding="utf-8")
        + result.index_html.read_text(encoding="utf-8")
    )

    assert str(tmp_path) not in generated_text
    assert "https://wdty.github.io/nlziet-kodi-addon/" in generated_text


def test_build_rejects_output_directory_that_would_delete_source_root(tmp_path):
    _write_minimal_addon(tmp_path)

    with pytest.raises(build_kodi_repository.BuildError, match="source root"):
        build_kodi_repository.build_repository(tmp_path, tmp_path)


def test_publish_ref_validation_accepts_only_controlled_refs():
    build_kodi_repository.validate_publish_ref(
        "workflow_dispatch", "refs/heads/develop"
    )
    build_kodi_repository.validate_publish_ref(
        "workflow_dispatch", "refs/heads/tooling/kodi-development-repository"
    )
    build_kodi_repository.validate_publish_ref(
        "push", "refs/tags/kodi-repo-2026-07-12"
    )

    with pytest.raises(build_kodi_repository.BuildError, match="Unsupported publish ref"):
        build_kodi_repository.validate_publish_ref(
            "workflow_dispatch", "refs/heads/refactor/extract-controller-adapters"
        )
    with pytest.raises(build_kodi_repository.BuildError, match="Unsupported publish ref"):
        build_kodi_repository.validate_publish_ref("pull_request", "refs/pull/1/merge")
