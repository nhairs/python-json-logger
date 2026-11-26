# Release checklist

## Prepare the release

1. Set `project.version` in `pyproject.toml`.
2. Update the base-version section in `docs/changelog.md`. Use `UNRELEASED` for
   development and prerelease versions, or `YYYY-MM-DD` for a final release.
3. Merge the release commit into `main`.
4. Tag that commit with `v` followed by the exact project version, then push the tag.

For example, version `4.3.0rc1` uses the `4.3.0` changelog section and this tag.

```shell
git tag v4.3.0rc1
git push origin v4.3.0rc1
```

## Approve publication

When the Release workflow requests approval, review the release notes and
built distributions in its `release-bundle` artifact, then approve the `pypi`
deployment.

## Handle a failed release

Cancel stale runs waiting for approval before starting a replacement.

If any file reached PyPI, preserve the original bundle and publication evidence
from the workflow artifacts. Inspect PyPI and GitHub to establish what was
published before recovering manually. A failed publishing job cannot reuse an
earlier attempt's bundle through **Re-run failed jobs**. Prepare a new version
if the original distribution bytes are unavailable.

See the [nopt documentation](https://pypi.org/project/nopt/0.2.0/) for supported
versions, release policy, and recovery limits.
