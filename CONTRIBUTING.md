# Contributing to Finance mosaix

Thank you for considering a contribution to Finance mosaix. Your work helps improve this personal finance system and makes it easier for others to manage their data.

## How to contribute

1. Open an issue to describe the bug, feature request, or improvement.
2. Fork the repository.
3. Create a branch from `master`.
   - Use a descriptive branch name such as `feature/add-docs` or `fix/import-parser`.
4. Make your changes and test locally.
5. Submit a pull request against the `master` branch.

### Opening and merging a PR

Open PRs with `scripts/dev/create-pr.sh` and merge them with
`scripts/dev/merge-pr.sh`. The script fills the whole PR template, so nothing
is maintained by hand afterwards. The PR title is the squash subject and a
Conventional Commits subject, release-please builds the changelog from it. The
fenced block in the description is the squash body: it never repeats the title
and ends with `Co-authored-by: Claude Sonnet|Opus|Fable x.y <noreply@anthropic.com>`,
never Haiku. Pass the model as `PR_AI_MODEL="Sonnet 5.5"`, the test suites you
ran as `PR_SUITES`, and optionally `PR_SUMMARY`, `PR_ISSUE` or
`PR_MESSAGE_FILE`. `merge-pr.sh --check` validates the message without merging.

## Review process

- Contributions will be reviewed by the maintainer.
- The maintainer may request changes, discuss alternatives, or propose improvements before merging.
- Please keep changes focused and documented.

## Testing

Use Python 3.11 or newer (matches `pyproject.toml`).

Run tests from the project root:

```bash
python -m pytest
```

If you add new functionality, include tests that cover the new behavior.

## Code style

- Keep code clear and readable.
- Prefer descriptive names for functions and variables.
- Document non-obvious behavior in comments or docstrings.

## AI transparency

- This project has been developed with the assistance of CoPilot.
- The primary model used during project realization is Raptor mini.
- When contributing, state whether CoPilot assistance was used for code, documentation, tests, or other deliverables.
- Referencing the specific CoPilot model(s) used is mandatory for all pull requests.

## Notes

- This repository uses `master` as the mainline branch.
- If you are unsure about the best approach, open an issue first.
