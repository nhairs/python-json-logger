# Publish a release

The `release.yml` workflow validates a version tag, reruns lint and the Linux,
macOS, and Windows test suites, and builds one wheel and one source distribution.
It stages a draft GitHub release before requesting approval to publish to PyPI.
Publishing the GitHub draft remains a manual step.

## Configure owner settings

Complete this setup before pushing a release tag. The workflow does not apply
repository or PyPI settings.

1. In the repository settings, create the `pypi` environment. Add `nhairs` as a
   required reviewer, allow self-approval, and disable administrator bypass.
   Select deployment protection for selected tags with the pattern `v*`; do not
   allow branches. Required reviewers are available for public repositories on
   GitHub Free. See [GitHub deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
2. Inspect the project's existing PyPI publisher configuration. Register a
   [trusted publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
   for owner `nhairs`, repository `python-json-logger`, workflow `release.yml`,
   and environment `pypi`. Do not add a PyPI API token to the workflow.
3. Preserve the existing `v*` tag rulesets: `1773763` protects creation and update,
   and `1773764` protects update and deletion. Verify their bypass permissions
   with owner access. This guide does not require changing those rulesets.
4. Verify that GitHub Actions can create draft releases and use the pinned
   actions. Review action upgrades before changing their commit pins.

## Prepare a version

1. Set `project.version` in `pyproject.toml` and update the corresponding
   base-version section in `docs/changelog.md`. Stable versions need an ISO date
   such as `2026-10-28`. Release candidates can use `UNRELEASED`. The section must
   occur exactly once and contain release notes.
2. Merge the release commit into `main`. The tagged commit must be reachable
   from `main`; a release branch alone is insufficient.
3. Create and push the version tag after reviewing the commit. Accepted formats
   are `vN.N.N` and `vN.N.N.rcN`, with no leading zeros. For example,
   `v4.3.0.rc1` matches the normalized project version `4.3.0rc1` and uses the
   `4.3.0` changelog section. Development, alpha, beta, and postrelease tags fail.
4. Wait for the workflow to create the draft release. Inspect its full changelog,
   version title, prerelease flag, wheel, source distribution, and
   `SHA256SUMS.json`. The `release-bundle` workflow artifact also contains the
   release commit and version metadata. Artifacts are retained for 90 days.
5. Approve the `pypi` deployment after checking the draft and CI results. The
   publisher downloads the validated bytes without checking out repository code.
   Only this job receives an OpenID Connect token. The
   [PyPI publishing action](https://github.com/pypa/gh-action-pypi-publish)
   generates attestations by default.
6. Verify the files on PyPI, then publish the GitHub draft manually. A successful
   PyPI upload does not publish the GitHub release.

## Recover a failed run

Use **Re-run failed jobs** on the original workflow run. Runs are serialized per
version tag and do not cancel an active release. Avoid queuing another run for
the same tag: a fresh run of a previously attempted tag stops for recovery in
the original run. A read-only build token cannot reliably inspect drafts.

- If validation or CI fails, fix the release preparation before attempting a
  release. Do not move a tag that already has published files.
- If the build job reruns after retaining its bundle, it downloads that bundle
  from the same run and verifies its commit, tag, filenames, and checksums.
  It does not rebuild it. If no bundle exists but a previous run, published GitHub
  release, or PyPI version exists, it stops for manual recovery.
- If draft staging fails partway through asset upload, rerun the failed job. A
  matching draft and byte-identical assets are reused; missing assets are added.
  Conflicting metadata, conflicting assets, unexpected assets, and published
  GitHub releases stop the run. Existing assets are never overwritten.
- If PyPI accepts only one distribution, rerun the failed publish job. It checks
  the PyPI JSON API against the retained manifest, skips identical files, and
  uploads only missing files. A mismatched or unexpected filename stops the
  run. Network and API errors also stop the run; they are not treated as missing
  releases. The workflow does not use `skip-existing`.
- If both files already match PyPI, the publishing step is skipped successfully.
  A concurrent upload after the comparison can still fail; rerun to compare the
  published checksums again.

If retained artifacts expire or are unavailable, stop automatic recovery.
Download the original distributions and manifest from the matching GitHub draft
or another verified archive. Compare every filename and SHA-256 digest, including
any files already accepted by PyPI. Confirm the original tag and commit. Recover
using those exact bytes through an owner-reviewed process; do not rebuild a
partially published version. If the original bytes cannot be recovered, prepare
a new version. This workflow deliberately provides no dispatch path that bypasses
these checks or the approval gate.

## Validate workflow changes

Run the offline release tests with Python 3.12:

```shell
uv run --python 3.12 --group dev pytest tests/test_release.py
```

The tests use synthetic distributions and mocked GitHub and PyPI responses.
They do not create tags, draft releases, or uploads. Also run the repository lint
and test suites and validate the workflow with `actionlint`. Production uploads,
TestPyPI trials, and owner setting changes require separate authorization.
