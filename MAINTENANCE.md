# Maintaining the profile

The README is the public profile. The Python validator and GitHub Actions workflows
maintain the five SVGs served from the `output` branch. Python 3.9 or newer is
required; the validator and tests use only the standard library.

## Local checks

From the repository root, run:

```sh
python -m unittest discover -s tests -v
python scripts/validate_profile_assets.py dist
```

The second command requires generated SVGs in `dist/`; it exits with status 1 if
an expected asset is missing, empty, malformed, an error card, or lacks basic
renderable content. The tests create their own temporary assets.

Run `actionlint` to check both workflow files. CI uses actionlint 1.7.7 and verifies
the downloaded release against a fixed SHA-256 checksum. When updating that
version, update its checksum in `.github/workflows/ci.yml` as well.

## Generation and publication

`Generate Profile Cards` runs at 00:17 and 12:17 UTC (05:47 and 17:47 IST), on
selected pushes to `main`, or manually from the repository's Actions tab.
Scheduled execution times may be delayed by GitHub.

The generation job has read-only repository access. It runs tests, generates all
five cards, validates them, and uploads a short-lived artifact. A separate job
downloads that artifact and publishes it to `output` with write permission.
Only runs from `main` can publish; manual runs from other branches generate an
artifact for inspection. A failure before publication leaves existing cards intact.

The stats and language actions explicitly use `core_version: ""`, which selects
the bundled core dependency installed from the pinned action's frozen lockfile.
Do not remove that override: the action's default `v2` downloads a mutable npm tag.
Review the bundled version and lockfile when upgrading the action.

`Validate Profile Repository` runs tests and workflow linting on pull requests,
including Dependabot updates, and pushes to `main`. It has read-only access and
does not generate or publish cards. To enforce these checks before merging, make
its `validate` job a required status check in the repository's branch protection
or ruleset settings.

## Troubleshooting

1. Open the failed Actions run and inspect the first failing step. Generation
   failures can involve API limits, credentials, or upstream dependency changes.
2. For validation failures, inspect the generated SVG and reproduce the issue
   with a regression test before changing the validator. Fix the generator or
   its options if it emitted an error card.
3. For publication failures, check permissions and rules affecting `output`.
   The publishing job uses the repository's automatic `GITHUB_TOKEN`; no personal
   access token is configured.
4. Rerun the workflow from `main` after resolving the issue. Inspect the updated
   images in the profile.

The SVG check is a structural safeguard, not a full browser renderer. It handles
basic geometry, text, inline display/visibility, and local `<use>` references.
It does not evaluate stylesheets, clipping, external images, or animations;
animated cards may intentionally begin transparent. Visually inspect cards when
changing generators or themes. Other badges and images loaded directly from
external services in the README are outside this publication check.
