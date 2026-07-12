# Development Workflow

This fork is maintained as an independent development line. Upstream synchronization remains important, but it is deliberate rather than automatic: each upstream change should be evaluated for compatibility, security, Kodi behavior, authentication, DRM, playback, and architecture before it is brought into this fork.

## Branches

### master

`master` is the stable release branch for this fork. It should remain deployable, should be updated only from validated `develop`, and releases are tagged from this branch.

### develop

`develop` is the primary integration branch for ongoing work. New feature, fix, and refactor branches should normally start here, and `develop` should remain buildable and testable.

### feature/*

Use `feature/*` branches for new functionality.

Create from:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c feature/<topic>
```

Merge back into `develop` after validation.

### refactor/*

Use `refactor/*` branches for behavior-preserving refactoring. These branches should always start from `develop` and merge back into `develop`.

### fix/*

Use `fix/*` branches for bug fixes. Most fixes should start from `develop`.

Critical production fixes may start from `master`, but they must later be brought back into `develop` so the integration branch does not drift.

### upstream/master

`upstream/master` is the read-only reference to `Nigel1992/NLZiet-Kodi-Addon`.

Do not merge upstream automatically. Review upstream changes individually and bring over only changes that make sense for this fork.

### upstream-pr/*

Use `upstream-pr/*` branches only for temporary upstream pull request preparation. These branches should be created directly from upstream, not from this fork's `master` or `develop`.

Example:

```bash
git fetch upstream
git switch -c upstream-pr/<topic> upstream/master
```

Bring over only the minimal required commits. Prefer isolated cherry-picks or small manual implementations. Never submit the complete fork history as an upstream pull request.

## Release Validation Note

The repository migration to `master` continued after a post-merge `kodi-addon-checker 0.0.36` rerun encountered an external checker defect caused by intermittent repository metadata retrieval failures from `mirrors.kodi.tv`. The failure was traced to an internal checker exception and was confirmed not to be related to the addon contents. Unit tests, compile validation, successful Kodi smoke tests, and previous successful checker execution on the identical addon tree were used as release validation.
