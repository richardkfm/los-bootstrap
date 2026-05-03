# Releasing los-bootstrap

This document covers the maintainer-only steps to cut a release.

## One-time setup (first PyPI release)

Before the first release that publishes to PyPI, the maintainer needs to
configure a **Trusted Publisher** on pypi.org. This avoids storing a
long-lived API token in GitHub Secrets — GitHub Actions authenticates to
PyPI via OIDC instead.

1. Sign in (or create an account) at <https://pypi.org>.
2. Go to <https://pypi.org/manage/account/publishing/> and add a
   **pending publisher** with these values:
   - PyPI project name: `los-bootstrap`
   - Owner: `richardkfm`
   - Repository name: `los-bootstrap`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
3. In this GitHub repo, create an environment named `pypi`
   (Settings → Environments → New environment). No secrets needed; the
   environment scopes the OIDC token. Optionally add required reviewers
   so a release can't go out without manual approval.
4. After the first successful publish, the pending publisher becomes
   a permanent one — no further setup required for subsequent releases.

Until step 1–3 are complete, the `publish.yml` workflow will fail at the
`publish-pypi` job. The `release` job (GitHub Release with install
scripts attached) still works, and the `git clone` install path remains
the documented fallback.

## Per-release flow

1. Confirm `__version__` in `src/los_bootstrap/__init__.py` matches the
   tag you're about to push (semver, no `v` prefix in the file).
2. Confirm `CHANGELOG.md` has an entry under `## [Unreleased]` →
   rename it to `## [x.y.z] - YYYY-MM-DD` and add a fresh empty
   `## [Unreleased]` section above it.
3. Confirm the version badge in `README.md` is up to date.
4. Commit those changes on `main`.
5. Tag and push:
   ```bash
   git tag -a v0.9.0 -m "v0.9.0"
   git push origin v0.9.0
   ```
6. The `publish.yml` workflow runs automatically:
   - builds sdist + wheel
   - publishes to PyPI via Trusted Publishing
   - creates a GitHub Release with the wheel, sdist,
     `install.sh` + `install.sh.sha256`, and
     `install.ps1` + `install.ps1.sha256` attached.
7. Smoke test the release:
   ```bash
   pipx install "los-bootstrap[wizard]"
   los-bootstrap version   # should print x.y.z
   ```

## Rollback

Releases on PyPI cannot be re-uploaded with the same version — bump
to a new patch (`0.9.1`) instead of yanking and re-cutting `0.9.0`.

If a release needs to be hidden, use the **Yank** action on
<https://pypi.org/manage/project/los-bootstrap/releases/>. Yanked
releases are still installable by exact version pin but no longer
selected by `pip install los-bootstrap`.
