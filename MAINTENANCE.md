# Maintaining the profile

The README is the public profile. The Python validator and GitHub Actions workflows
maintain the six SVGs served from the `output` branch. Python 3.9 or newer is
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

Run `actionlint` to check all workflow files. CI uses actionlint 1.7.7 and verifies
the downloaded release against a fixed SHA-256 checksum. When updating that
version, update its checksum in `.github/workflows/ci.yml` as well.

## Generation and publication

`Generate Profile Cards` runs at 00:17 and 12:17 UTC (05:47 and 17:47 IST), on
selected pushes to `main`, or manually from the repository's Actions tab.
Scheduled execution times may be delayed by GitHub.

The generation job has read-only repository access. It runs tests, generates all
six cards, validates them, and uploads a short-lived artifact. A separate job
downloads that artifact and publishes it to `output` with write permission.
Only runs from `main` can publish; manual runs from other branches generate an
artifact for inspection. A failure before publication leaves existing cards intact.

The activity graph is generated directly from GitHub's contribution calendar API
with the automatic read-only `GITHUB_TOKEN`. It displays the last 31 UTC dates and
does not depend on an external graph-rendering service. Missing or incomplete API
data stops publication rather than replacing the existing graph with false zeroes.
For local generation, set `GITHUB_TOKEN` in your environment and run:

```sh
python scripts/generate_activity_graph.py meetkapadia1710-tech
```

After adding a new generated image, push the changes to `main` and let the
generation workflow finish successfully. The new `output` URL will not exist
until the first successful publication.

### Automatic activity updates

`Update Contribution Activity` refreshes the graph after every push to this
repository's `main` branch, regardless of which files changed. It also runs every
15 minutes, at minutes 7, 22, 37, and 52 UTC, so contributions from your other
repositories appear automatically once GitHub's contribution calendar records them.
You do not need to edit the README or regenerate the image manually.

GitHub can delay scheduled runs, contribution processing, and image-cache refreshes,
so a commit may take longer than 15 minutes to appear. Local commits must be pushed
to GitHub and qualify for the contribution calendar before they can appear.

This lightweight workflow generates and validates only `github-activity-graph.svg`.
Publication preserves the other files in `output`, and both publishing workflows
share a concurrency group to prevent concurrent writes. Read-only generation and
write access restricted to publication also apply to these refreshes. API failures
leave the previous graph intact. The full six-card workflow continues its existing
twice-daily schedule.

Manual runs are available in the Actions tab. An optional `repository_dispatch`
event named `contribution-activity` can also request an update from another
repository or integration, but the 15-minute schedule requires no such setup.

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
