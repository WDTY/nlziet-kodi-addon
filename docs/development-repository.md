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
3. Run the `Publish Kodi Repository` workflow manually from the Actions tab only from `develop` or `tooling/kodi-development-repository`, or publish with a tag matching `kodi-repo-*`.

The workflow uses the official GitHub Pages actions and does not require personal access tokens or repository secrets. Pull requests and random feature branches must not deploy; unsupported refs fail during the workflow's validation step.

## First Deployment

1. Decide whether the source `addon.xml` version should be bumped, and commit that version bump separately.
2. Run the full test suite:

   ```text
   python -m pytest
   ```

3. Build locally and inspect the output:

   ```text
   python scripts/build_kodi_repository.py
   ```

4. Publish from a controlled tag, for example:

   ```text
   git tag kodi-repo-2026-07-12
   git push origin kodi-repo-2026-07-12
   ```

5. Install the repository ZIP in Kodi and smoke test browsing, login state, and playback before directing anyone else to use it.

## Kodi Installation

1. Download `repository.wdty.nlziet.zip` from:

   ```text
   https://wdty.github.io/nlziet-kodi-addon/repository.wdty.nlziet.zip
   ```

2. In Kodi, use `Add-ons` > `Install from zip file` and select the downloaded ZIP.
3. Use `Install from repository` > `WDTY NLZiet Development Repository` to install or update `plugin.video.nlziet`.

A valid NLZiet subscription is required. The repository hosts only add-on packages and metadata. It does not host credentials, cookies, tokens, or NLZiet account data.

## Update And Version Behavior

The build reads the exact version from the source `addon.xml`. It uses that value in `addons.xml` and in the plugin ZIP filename. It does not rewrite, calculate, or bump the version.

Kodi only offers an update when the version increases. Publishing another `1.0.1` build will not automatically replace an already installed `1.0.1`. Each development release that should update Kodi installations requires an explicit source version bump before publishing.

Installing this repository uses the same `plugin.video.nlziet` add-on id as upstream. Installing or updating from this repository can replace an installed upstream version when the fork version is higher. A higher fork version can also prevent Kodi from offering a lower upstream version later unless the user removes or downgrades manually.

## Rollback

To roll back, publish a new build with an explicitly higher `addon.xml` version that contains the desired source state. Kodi will not automatically downgrade to a lower version.

To return to upstream, remove `WDTY NLZiet Development Repository` from Kodi, uninstall or downgrade `plugin.video.nlziet` as needed, then install the upstream add-on from the upstream source. If switching sources, verify which repository owns `plugin.video.nlziet` before updating.
