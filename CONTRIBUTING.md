# Contributing to Collectarr Sync

Thanks for helping people synchronize and selectively share their collections.

## Before you start

- Check existing issues and pull requests; discuss protocol or persistence
  changes before implementation.
- Read [AGENTS.md](AGENTS.md) and the deployment and protocol docs.
- Preserve user data across migrations and test against isolated databases.
- Never commit credentials, user snapshots, or unlicensed third-party assets.

## Development and review

Use Python 3.14 and the declared dependencies. Follow the repository's
documented testing and migration procedures. Pull requests should describe
behavior, security and privacy implications, tests, and any protocol changes.

## Licensing contributions

Collectarr Sync is licensed under **GNU Affero GPLv3 only**
(`AGPL-3.0-only`). By contributing, you confirm that you have the right
to submit the work under that license and that it may be redistributed
under those terms. You retain copyright to your original contribution;
no copyright assignment is required.

Flag third-party code and its license in your pull request. Earlier versions
were released under MIT; their rights remain intact and the old notice is
preserved in [LICENSES/MIT-legacy.txt](LICENSES/MIT-legacy.txt).
See [LICENSE](LICENSE) for the AGPLv3 terms, including network-use source
access obligations for modified versions.

## Community

Be respectful and open to review, especially for changes affecting privacy,
authentication, or user data.
