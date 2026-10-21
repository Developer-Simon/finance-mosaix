## Squash-merge commit message

<!--
  `scripts/dev/create-pr.sh` fills every field of this template. Do not edit
  the placeholders by hand. Change the inputs and run the script again, or
  edit the PR description once and let `scripts/dev/merge-pr.sh` check it.

  `master` uses squash merge. The subject of the merge commit is the PR title
  (Conventional Commits: `type(scope): imperative summary`, release-please
  builds CHANGELOG.md from it), so the fenced block below holds only the BODY.
  It never repeats the title and always ends with a
  `Co-authored-by: Claude Sonnet|Opus|Fable x.y <noreply@anthropic.com>`
  trailer. Haiku is never named there.

  `scripts/dev/merge-pr.sh` takes this block as the merge body. GitHub's own
  merge button would use the commit list instead, so merge with the script.
-->

```text
{{MESSAGE}}
```

## Summary

{{SUMMARY}}

## Checks

- [{{CHECK_TITLE}}] The title is a Conventional Commits subject.
- [{{CHECK_FILES}}] No database files (`*.duckdb`) or local `settings.json` are tracked.
- [{{CHECK_AI}}] AI assistance disclosed per [CONTRIBUTING.md](../blob/master/CONTRIBUTING.md#ai-transparency): {{AI_MODEL}}
- [{{CHECK_SUITES}}] Suites run locally: {{SUITES}}
- Linked issue: {{ISSUE}}
