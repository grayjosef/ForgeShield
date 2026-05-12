# FS-1.5 — ForgeShield CI and local check commands (authoritative)

> **Status:** normative for copy-pastable checks in this repository. **Single
> authoritative reference** for local and CI-equivalent commands (FS-1.5).
> Tooling versions follow your org or CI image; commands below assume a Unix
> shell on the operator workstation.

This document does not change code by itself. It complements
`docs/architecture/FS-1_ENGINEERING_EXECUTION_PLAN.md` (policy intent and
regression expectations) with **exact invocations**.

---

## 1. Canonical environment

| Item | Value |
|------|--------|
| **Host** | JG operator workstation |
| **Repository path** | `/home/josefgray/projects/forgeshield` |
| **Remote (origin)** | `git@github.com:grayjosef/ForgeShield.git` |

Run all commands from the repository root unless noted otherwise.

---

## 2. Wrong-environment warning

Do **not** treat ad-hoc clones, other hosts, or alternate paths as the canonical
ForgeShield working tree for FS-1 work.

- **Do not** run ForgeShield engineering or pilot checks from **ForgeNode** or
  any path presented as a substitute for this repo on JG.
- **Do not** assume `/Users/home/projects/forgeshield` (or other macOS-style
  paths) is the canonical checkout; on JG the canonical tree is **WSL** at
  `/home/josefgray/projects/forgeshield`.

If your shell is not in that directory, `cd` there before running checks.

---

## 3. Required local setup

From the repo root:

1. **Activate the project virtualenv**

   ```bash
   . .venv/bin/activate
   ```

   First-time setup (once per clone): create the venv and install dev
   dependencies from `pyproject.toml` (for example
   `python -m venv .venv && . .venv/bin/activate` then
   `pip install -e ".[dev]"`).

2. **Export Python path for imports**

   ```bash
   export PYTHONPATH=src
   ```

`tests/conftest.py` also injects `src/` into `sys.path` for collection, but
exporting `PYTHONPATH=src` matches the documented manual invocation and keeps
behavior aligned with `pyproject.toml` / IDE runs.

---

## 4. Full test command

```bash
python -m pytest -v
```

Run after activating `.venv` and exporting `PYTHONPATH=src`.

---

## 5. Focused test commands

Security-focused modules (fast feedback during D6/D7 and CC-14 work):

```bash
python -m pytest -v tests/security/test_prompt_builder.py
python -m pytest -v tests/security/test_review_artifacts_policy.py
python -m pytest -v tests/security/test_untrusted_content.py
```

---

## 6. Semgrep validation (required)

Validate the D7 prompt f-string tripwire rule pack **without** scanning the
tree (catches broken rule YAML):

```bash
semgrep --validate --config semgrep/forge_security/no-direct-prompt-fstring.yml
```

---

## 7. Optional semgrep scan

After validation succeeds, scan Python under `src/` with the same config (as
documented in the rule file header):

```bash
semgrep --config semgrep/forge_security/no-direct-prompt-fstring.yml src
```

This repository currently ships that single rule file under `semgrep/`; there is
no separate aggregate config directory beyond `semgrep/forge_security/`.

---

## 8. Git pre-commit review checklist

Before every commit:

1. `git status --short` — only intended paths are modified or staged.
2. `git diff --stat` — scope matches your intent.
3. `git diff` (and `git diff --cached` if you use staging) — read the full
   patch.
4. **Run tests and semgrep** — full pytest (`python -m pytest -v`), semgrep
   **validate** (§6), and optional semgrep **scan** (§7) as appropriate for the
   change.

---

## 9. Human gate (commits and automation)

- **No commits** without human review of the diff and **explicit approval** to
  record that revision.
- **No automatic commits** from Cursor, agents, hooks, or other automation in
  place of a deliberate human commit decision.

Automation may *propose* edits or run checks; it must not bypass this gate.

---

## 10. Definition of a clean check

Treat the branch as merge-ready only when **all** of the following hold:

1. **Tests pass** — `python -m pytest -v` exits successfully.
2. **Semgrep validates** — `semgrep --validate --config …` exits successfully
   for `semgrep/forge_security/no-direct-prompt-fstring.yml`.
3. **Git status is intentional** — `git status --short` shows only files you
   mean to commit (no stray artifacts, caches, or accidental edits).
4. **After push, `main` is aligned** — local `HEAD` matches `origin/main` so you
   are not sitting on unpublished work by mistake.

---

## 11. Cross-reference

- Engineering context and non-command expectations (policy files, regression
  baseline): `docs/architecture/FS-1_ENGINEERING_EXECUTION_PLAN.md` §5 and
  related sections.
- CC-14 review artifact tiers and agent rules: `.cursor/rules/forgeshield-artifact-policy.mdc`
  and `src/forge_security/artifact_integrity/review_artifacts.py` (code —
  change only via normal PR process).
