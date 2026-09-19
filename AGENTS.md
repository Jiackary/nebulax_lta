# Repository workflow

Make frequent, atomic commits while working in this repository. Each commit must
contain one coherent change that can be reviewed and, where applicable, tested on
its own.

Use Conventional Commits for every message:

```text
type(scope): imperative summary
```

Use an appropriate type such as `feat`, `fix`, `docs`, `test`, `refactor`, `style`,
`build`, or `chore`. Keep the summary specific and avoid mixing unrelated changes in
one commit. Run relevant checks before committing and include the files that belong
to that one change only.
