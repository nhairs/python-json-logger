# Release checklist

The `release.yml` workflow builds distributions and stages a GitHub draft.
After `pypi` approval, it publishes GitHub first, then uploads those bytes to PyPI.

## Prepare

- [ ] Set `project.version` in `pyproject.toml`.
- [ ] Update the base-version section in `docs/changelog.md`.
  Set `YYYY-MM-DD` for RCs and stable releases; only development releases may
  use `UNRELEASED`. Post releases must match the date at the base release tag.
- [ ] Merge the release commit into `main`.
- [ ] Review and push the tag. Use `vN.N.N` with optional `.devN`, `.rcN`, or `.postN`, without leading zeros.

For example, `v4.3.0.rc1` matches project version `4.3.0rc1` and the `4.3.0`
changelog section. Alpha, beta, undotted suffixes, and combined suffixes are rejected.
The workflow filter excludes `vladamir/test-the-new-thing`.
Exact validation blocks invalid releases; it does not prevent tag creation.

```shell
git tag v4.3.0.rc1
git push origin v4.3.0.rc1
```

## Approve

- [ ] Check lint and the Linux, macOS, and Windows test results.
- [ ] Review the GitHub draft: title, full changelog, and prerelease flag.
- [ ] Check the wheel, sdist, `SHA256SUMS.json`, and `release.json` assets.
- [ ] Approve the `pypi` deployment.
- [ ] Confirm GitHub is published and PyPI has both files.

File selection runs with read-only permissions before approval. The approved job
publishes GitHub and uses OIDC to upload to PyPI. It does not check out or run
repository scripts. If PyPI fails, GitHub remains published with the original files.

## Recover

- [ ] Use **Re-run all jobs** in the original run for any publishing failure.
  This repeats file selection, reuses the original distributions, and requests approval.
  **Re-run failed jobs** alone cannot refresh the upload selection.
- [ ] Check that existing filenames and hashes match. Identical files are reused;
  missing files are uploaded. Conflicts stop the run.
- [ ] Leave tags and existing assets unchanged. Do not overwrite a conflicting release.
- [ ] Check PyPI again after the retry succeeds.

The `release-bundle` artifact retains distributions, checksums, notes, and commit
metadata for 90 days. If it is missing or expired, the workflow retrieves the exact
files from the official GitHub release and verifies their metadata and checksums.
It never rebuilds a partially published release. Published GitHub assets are never
modified; only matching releases can be reused.

If neither retained artifacts nor matching official assets are available:

- [ ] Stop automatic recovery.
- [ ] Recover the original distributions and manifest from the draft or a verified archive.
- [ ] Verify filenames, SHA-256 digests, tag, and commit before an owner-reviewed recovery.
- [ ] If original bytes cannot be recovered, prepare a new version.

## Validate workflow changes

```shell
uv run --python 3.12 --group dev pytest tests/test_release.py
```

- [ ] Run lint, tests, `actionlint`, and a local build/install check.
- [ ] Review API-facing changes separately. Unit tests check policy and local
  files/Git; they do not prove GitHub or PyPI integration.
- [ ] Obtain separate authorization for live releases, TestPyPI trials, or settings changes.
