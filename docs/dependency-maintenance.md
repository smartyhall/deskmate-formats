# Dependency maintenance

The repository is privately hosted. The owner reports that its initial four CI
jobs passed on Windows/Ubuntu with Python 3.13/3.14. No public visibility change,
release automation, automatic merge or deployment is configured by this change.

`.github/dependabot.yml` uses version 2, weekly `pip` and `github-actions` updates
at `/`. Pip monitors supported declarations in `pyproject.toml`, including the
development extra; inspect update logs for build-system requirements rather than
assuming every PEP 517 build requirement is discovered. There are no runtime
dependencies. Limits are two pip and one Actions open version-update PRs, three
combined; security-update PRs have a separate limit managed by GitHub.

Configuration on a development branch does not activate version updates. The
owner must review and merge it into the default branch, then inspect the first
scheduled run (or request a manual check in GitHub). Verify discovered manifests,
requirements and update logs, especially setuptools/wheel build requirements.

For each PR: inspect upstream changes and dependency provenance, retain full
40-character commit-SHA pins for Actions, and confirm all four portable CI jobs
pass before manually merging. The existing `push`/`pull_request` workflow has
read-only contents permission, needs no secrets, and runs without proprietary
fixtures. Its triggers include Dependabot PRs. No Actions pins or permissions were
changed. Failed checks require investigation; do not bypass them or enable auto-merge.

Dependabot alerts, dependency graph and Dependabot security updates are separate
repository settings. The owner should review their current availability/state in
Settings > Advanced Security (or the repository's security settings) and enable
desired features for this private repository. This configuration neither asserts
they are enabled nor changes account, plan, permissions or security settings.

GitHub references:

* [Configuration options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
* [Supported ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)
* [Configuration and the default branch](https://docs.github.com/en/code-security/concepts/supply-chain-security/about-the-dependabot-yml-file)
* [Security updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates)
