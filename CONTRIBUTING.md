# Contributing

Thanks for your interest in web-changelog.

## Issues

Bug reports, questions and ideas are welcome as issues. A minimal example (a
short `CHANGELOG.md` excerpt and the call that misbehaves) helps a lot.

## Support

This is a personal project maintained in spare time. There is no guaranteed
support, response time or roadmap. Pull requests may be declined if they do not
fit the scope of the library.

## Pull requests

- Keep changes focused and include tests. Unit tests run with
  `python -m unittest discover -v tests/`, acceptance tests with `python -m behave`.
- Add a changelog fragment to `changelog.d/` (see `changelog.d/README.md`).

## Developer Certificate of Origin

Every commit must be signed off under the
[Developer Certificate of Origin](https://developercertificate.org). By signing
off you certify that you wrote the change or otherwise have the right to submit
it under the project's license. Use:

```bash
git commit -s
```

This adds a `Signed-off-by: Your Name <you@example.com>` line to the commit
message. Commits without a sign-off cannot be merged.
