# Release checklist

The release workflow uses PyPI package `nopt==0.2.0` to check eligibility, build
and verify a bundle, and publish the GitHub release. GitHub Actions runs the
project test suite, retains artifacts, and gates PyPI Trusted Publishing through
the `pypi` environment.

## Prepare

- [ ] Set `project.version` in `pyproject.toml`.
- [ ] Update the base-version section in `docs/changelog.md`. Development and
  prerelease versions require `UNRELEASED`. Final versions require `YYYY-MM-DD`.
- [ ] Merge the release commit into `main`.
- [ ] Review and push the canonical `v<version>` tag pointing to that commit.

For example, version `4.3.0rc1` uses tag `v4.3.0rc1` and the `4.3.0` changelog
section. Nopt accepts `X.Y.Z`, `X.Y.Z.devN`, `X.Y.ZaN`, `X.Y.ZbN`, and
`X.Y.ZrcN`. It rejects dotted `.rcN` suffixes, post releases, local versions,
epochs, and compound suffixes.

```shell
git tag v4.3.0rc1
git push origin v4.3.0rc1
```

All release types require a clean checkout and a commit reachable from `main`.
Before CI, nopt rejects an existing PyPI version, including partial or yanked
records. Only HTTP 404 means absent. Network and service errors stop the run.
An existing visible draft or published GitHub release also blocks publication.

## Approve

- [ ] Check lint and the Linux, macOS, and Windows test results.
- [ ] Review the build artifact's wheel, sdist, `release-notes.md`, `release.json`,
  `pyproject.toml`, and standard `SHA256SUMS` manifest.
- [ ] Check the installed-wheel smoke test.
- [ ] Approve the `pypi` deployment.
- [ ] Confirm PyPI has both distributions and GitHub has the expected release.

The build uses nopt's isolated PEP 517 build and validates distribution metadata
and bundle integrity. Publishing jobs retrieve the immutable build artifact by
ID and run without a source checkout. After approval, nopt verifies the bundle,
source tag, workflow identity, PyPI absence, and live GitHub state.

The PyPA action uploads distributions using OIDC and generates attestations.
Only this job has `id-token: write`. The separate GitHub release job has
`contents: write`. It waits for exact PyPI filenames and hashes, creates a draft,
uploads the original assets, and publishes it. All release types get GitHub
releases. Development and prerelease versions are marked as prereleases.
Only the highest canonical final Git tag is eligible for GitHub's latest marker.

Keep the Trusted Publisher repository, workflow filename `release.yml`, and
`pypi` environment aligned with the registered PyPI publisher.

## Recover a failed run

Runs for the same tag are serialized without automatic cancellation. Cancel stale
runs waiting for approval before replacing them. Rechecks reject a moved tag or
a version published by another attempt.

Before any PyPI upload, confirm that the version has no accepted files and inspect
the failed step before starting a fresh attempt. Nopt binds a bundle to its
workflow run and attempt. Rerunning a publishing job with an earlier attempt's
bundle fails that identity check.

After any PyPI file is accepted, preserve the original source, distributions,
manifest, and publication evidence. Recovery requires owner review and manual
handling of the original bytes. An existing GitHub draft also requires manual
resolution. If PyPI upload succeeds and GitHub publication fails, inspect the
remote state and retained bundle before proceeding. Nopt 0.2.0 has no automated
partial-upload or failed-finalization recovery. Prepare a new version if the
original bytes cannot be recovered.

## Retained artifacts

| Artifact | Contents |
| --- | --- |
| `release-bundle-RUN-ATTEMPT` | Original distributions, source project configuration, release notes, identity metadata, and checksums. |
| `publication-evidence-RUN-ATTEMPT` | Distributions passed to the PyPA action and available generated attestations, retained even after failure. |

`RUN` and `ATTEMPT` identify the workflow run and attempt. Artifacts have a 90-day
retention setting. Downstream jobs download the exact build artifact ID.
The publishing job uses its own downloaded copy, so generated attestations leave
the stored bundle intact. Attestations are available only if signing started.

## Validate workflow changes

- [ ] Run `actionlint` against `.github/workflows/release.yml`.
- [ ] Run project lint, tests, and a local build/install smoke check.
- [ ] Review the pinned nopt version and action revisions.
- [ ] Validate live publication through a separately authorized release.

See the [nopt documentation](https://pypi.org/project/nopt/0.2.0/) for CLI options
and release policy details.
