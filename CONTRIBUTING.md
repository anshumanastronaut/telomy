# Contributing

## Workflow
1. Branch from `main`: `feat/<short-name>`, `fix/<short-name>`, `docs/…`, `chore/…`.
2. Small, focused commits in the imperative mood (`Add HBOT delivered-dose check`). Reference the issue (`#42`).
3. Open a pull request using the template; at least **one reviewer**; CI must be green.
4. Squash-merge into `main`. `main` is always runnable.

## Definition of done
- [ ] Tests added/updated (`make test` passes locally) — every bug fix gets a regression test
- [ ] New/changed endpoints appear in `docs/API.md` (`backend/.venv/bin/python scripts/gen_docs.py`)
- [ ] Science changes cite their source in the docstring and in `docs/ENGINE.md`
- [ ] User-facing copy follows the claims firewall (`docs/CLINICAL_SAFETY.md`); simulated values are labelled
- [ ] Screens checked in the iOS Simulator (light/dark, small and large phones); accessibility labels on controls
- [ ] No real personal data, no secrets, no licensed data files committed

## Code style
- **Python**: 3.13, type hints on public functions, module docstring explaining the science/design, 140-char lines, no new heavy dependencies
  without discussion (keep `requirements.txt` pinned).
- **TypeScript**: strict; components in `src/ui`, screens in `src/app`; use design tokens from `src/lib/theme.ts` (no raw colours);
  `npx expo install` for packages (SDK-compatible versions). Read `mobile/AGENTS.md` before touching Expo APIs.
- Keep the honest-output principles: confidence, receipts, "no reliable signal".

## Areas & owners
See `.github/CODEOWNERS`. Ask in the PR when unsure who should review.
