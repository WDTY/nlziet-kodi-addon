# Kodi Development Repository

This fork can publish a private-development Kodi repository to GitHub Pages at:

```text
https://wdty.github.io/nlziet-kodi-addon/
```

The repository is unofficial and personal to this fork. It is not the upstream maintainer's official repository.

## Local Build

Run from the add-on source root:

```text
python scripts/build_kodi_repository.py
```

By default the generated Pages tree is written to:

```text
build/kodi-repository/
```

Expected output:

```text
build/kodi-repository/
  addons.xml
  addons.xml.md5
  index.html
  repository.wdty.nlziet.zip
  zips/
    plugin.video.nlziet/
      plugin.video.nlziet-<addon-version>.zip
    repository.wdty.nlziet/
      repository.wdty.nlziet-<repository-version>.zip
```

## Local Tests

Run the full Python test suite:

```text
python -m pytest
```

Run only the repository build tests:

```text
python -m pytest tests/test_build_kodi_repository.py
```

## GitHub Pages Setup

1. In the GitHub repository, open `Settings` > `Pages`.
2. Set the Pages source to `GitHub Actions`.
3. Run the `Publish Kodi Repository` workflow manually from the Actions tab.
4. Select an allowed branch or tag. The workflow is deliberately not published from every feature branch.

The workflow uses the official GitHub Pages actions and does not require personal access tokens or repository secrets.

## Kodi Installation

1. Download `repository.wdty.nlziet.zip` from:

   ```text
   https://wdty.github.io/nlziet-kodi-addon/repository.wdty.nlziet.zip
   ```

2. In Kodi, use `Add-ons` > `Install from zip file` and select the downloaded ZIP.
3. Use `Install from repository` > `WDTY NLZiet Development Repository` to install or update `plugin.video.nlziet`.

A valid NLZiet subscription is required. The repository hosts only add-on packages and metadata. It does not host credentials, cookies, tokens, or NLZiet account data.

## Update And Version Behavior

The build does not rewrite `addon.xml`. Kodi only offers an update when the version in the source `addon.xml` increases, so each development release requires an explicit version bump before publishing.

Installing this repository uses the same `plugin.video.nlziet` add-on id as upstream. Installing or updating from this repository can replace an installed upstream version.

## Rollback

To roll back, publish a new build with an explicitly higher `addon.xml` version that contains the desired source state. Kodi will not automatically downgrade to a lower version.

Users can also uninstall this repository add-on and reinstall the upstream add-on manually. If they switch sources, they should verify which repository owns `plugin.video.nlziet` before updating.
