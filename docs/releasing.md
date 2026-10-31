# Release checklist

The `release.yml` workflow checks eligibility, runs CI, builds distributions, and
stages a GitHub draft. After `pypi` approval, it uploads to PyPI and verifies both
files before publishing GitHub.

## Prepare

- [ ] Set `project.version` in `pyproject.toml`.
- [ ] Update the base-version section in `docs/changelog.md`.
  Set `YYYY-MM-DD` for RCs and stable releases; only development releases may
  use `UNRELEASED`. Post releases must match the date at the base release tag.
- [ ] Merge the release commit into `main`.
- [ ] Review and push the tag. Use `vN.N.N` with optional `.devN`, `.rcN`, or `.postN`, without leading zeros.

For example, `v4.3.0.rc1` matches project version `4.3.0rc1` and the `4.3.0`
changelog section. Alpha, beta, undotted suffixes, and combined suffixes are rejected.
Exact validation blocks invalid releases; it does not prevent tag creation.

```shell
git tag v4.3.0.rc1
git push origin v4.3.0.rc1
```

Before lint or tests, eligibility rejects any PyPI record for the target version,
including partial or yanked releases. Only HTTP 404 means absent; service and
network errors stop the run. A public GitHub release also blocks a new attempt
and requires owner cleanup. Existing drafts are allowed.

## Approve

- [ ] Check lint and the Linux, macOS, and Windows test results.
- [ ] Review the GitHub draft: title, full changelog, and prerelease flag.
- [ ] Check the wheel, sdist, `SHA256SUMS.json`, and `release.json` assets.
- [ ] Approve the `pypi` deployment.
- [ ] Confirm PyPI has both files and GitHub is published.

Every build attempt creates fresh distributions. Staging replaces all assets on a
same-commit draft, or deletes and recreates a draft for a different commit. Cleanup
happens after checks and build succeed. Public releases are never replaced.

After approval, publication readiness repeats the same version-eligibility policy:
the live tag must still match, GitHub must remain unpublished, and PyPI must have
no version record. It also verifies the built bundle's identity and checksums and
compares every draft asset against that bundle. The early check allows no draft
or an obsolete draft; readiness requires the exact staged build. PyPI absence is
checked last, after the asset comparison.

The approved job uses OIDC to upload the complete distribution set. It checks out
only `scripts/release.py` at the run's commit without persisting checkout credentials.
The shared Python checks run with isolation enabled and use only the standard
library. A separate finalization job verifies both PyPI filenames and hashes before
publishing the original draft.
Keep the Trusted Publisher repository, workflow filename `release.yml`, and
`pypi` environment unchanged.

## Recover before any PyPI upload

- [ ] Check PyPI to confirm no file for the version was accepted.
- [ ] Cancel an obsolete run waiting for approval before starting its replacement.
- [ ] Fix and merge the workflow or source change, then retarget the unpublished
  tag under the repository's protection rules, or rerun the original run for a
  transient failure with unchanged source.
- [ ] Review the fresh build and draft, then approve the new deployment.

Runs are serialized per tag without automatic cancellation; different tags run
independently. The owner cancels stale waiting runs manually. If approved instead,
a stale run fails its recheck when the tag moved or another run published PyPI.
Avoid moving tags during an active upload. Rechecks cannot lock a tag against an
owner changing it after the check.

## Recover after a PyPI upload

Any accepted file freezes the version's source and distribution bytes. Normal
attempts stop rather than rebuild, select missing files, or use `skip-existing`.
Deleting a PyPI version does not guarantee its filenames can be uploaded again.

If the PyPI step succeeded but GitHub finalization failed:

1. Select **Re-run failed jobs** on the original run. This reruns finalization
   with the original build artifact ID without uploading to PyPI again.
2. Confirm finalization verifies the complete PyPI hashes and original draft assets.
3. Confirm the GitHub release is published.

Do not select **Re-run all jobs** after publication: eligibility rejects the
existing version. If PyPI accepted files but the upload step failed, or an upload
was partial, stop automatic recovery. Recover the original distributions and
manifest from the draft or retained bundle for an owner-reviewed manual recovery.
This workflow does not automate partial uploads. If the original bytes cannot be
recovered, prepare a new version.

## Retained artifacts

| Artifact | Contents |
| --- | --- |
| `release-bundle-N` | Original wheel and sdist, `SHA256SUMS.json`, full notes, and `release.json` with tag, version, commit, build run, and attempt. |
| `finalization-evidence-N` | Original bundle artifact ID and GitHub finalization outcome. |
| `publication-evidence-N` | Available `.publish.attestation` files, manifest, release metadata, bundle artifact ID, publication attempt, and step outcomes. |

`N` is the job's workflow attempt. Artifacts are retained for 90 days and scoped
to the workflow run. Downstream jobs use the exact build artifact ID, including
when a failed job reruns with a newer attempt number. The old `pypi-upload-N`
subset artifact is no longer needed because normal publication uploads both files.

Evidence retention runs even after failure. If signing never started, the evidence
records that no attestations are available. Distributions remain in the referenced
bundle and GitHub draft. No credentials, OIDC tokens, or private keys are archived.

Saved attestations bind the CI identity to exact distribution hashes; they are
not upload credentials. PyPI requires Trusted Publishing authentication to accept
these attestations. Ordinary local API-token uploads cannot replay that identity.
The publishing action generates fresh attestations and rejects pre-existing
attestation files when generation is enabled. Preserve evidence for investigation
and future recovery rather than assuming it can be submitted by a local upload.

## Release helper commands

The workflow uses these `scripts/release.py` commands. Each command performs one
release operation; job names describe the surrounding pipeline stage.

| Command | Operation |
| --- | --- |
| `prepare-release-metadata` | Check tag/version, ancestry, changelog and release date; write metadata and notes. |
| `check-release-version-eligibility` | Require PyPI absence and the current source tag; reject public GitHub releases. |
| `validate-distributions` | Validate wheel/sdist metadata and write distribution checksums. |
| `verify-release-bundle` | Check bundle tag, commit, workflow run, filenames and distribution hashes. |
| `stage-github-draft` | Recheck eligibility and stage the complete draft asset set. |
| `check-pypi-publication-readiness` | Recheck the approved bundle, live tag, draft assets and PyPI absence. |
| `verify-and-publish-github-release` | Verify complete PyPI hashes and original draft assets, then publish GitHub. |
| `record-github-finalization-outcome` | Record the finalization result and original bundle reference. |

## Validate workflow changes

```shell
uv run --python 3.12 --group dev pytest tests/test_release.py
```

- [ ] Run lint, tests, `actionlint`, and a local build/install check.
- [ ] Review API-facing changes separately. Unit tests check release policy;
  they do not prove GitHub or PyPI integration.
- [ ] Obtain separate authorization for live releases, TestPyPI trials, or settings changes.
