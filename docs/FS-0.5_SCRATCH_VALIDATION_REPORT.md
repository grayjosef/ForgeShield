# FS-0.5 — Scratch validation report (operator workstation)

> **Status:** normative validation record for the FS-0.5 scratch gate.
> **Documentation only** — this file does not change code, tests, policy,
> semgrep rules, D6/D7 primitives, `activation_guard`, or CC-14 by itself.
>
> **Canonical repo:** `/home/josefgray/projects/forgeshield`
>
> **Reads:** `docs/CC-15_TEST_DEFECT_ENUM_VALUE_COMPARISON.md`,
> `src/forge_security/artifact_integrity/review_artifacts.py`,
> `src/forge_security/lifecycle/activation_guard.py`,
> `src/forge_security/ai_security/untrusted_content.py`,
> `src/forge_security/ai_security/prompt_builder.py`

---

## 1. Operator workstation

| Field | Value |
|---|---|
| Host | `JG` |
| User | `josefgray` |
| OS   | Linux 6.6.87.2-microsoft-standard-WSL2 |
| Python | 3.12 (scratch `.venv`) |

## 2. Scratch repository

- **Path:** `/home/josefgray/projects/forgeshield-scratch`
- **Layout:** isolated, no link to any production repo.
- **Dependencies installed in scratch:** `pytest`, `hypothesis`, `pydantic`.

## 3. Exact pytest invocation

```bash
PYTHONPATH=src uv run pytest tests/ -v --tb=short
```

## 4. Result

- **Collected:** 16
- **Passed:** 16
- **Failed:** 0
- **Errors:** 0

Test files run in scratch:

- `tests/security/test_prompt_injection_payloads.py`
- `tests/security/test_artifact_integrity_roundtrip.py`

## 5. Correction recorded — CC-15

A test-defect was discovered and corrected during FS-0.5 validation:

- **CC-15 / TEST_DEFECT — enum value comparison.** `ActivationDecisionModel`
  in the scratch roundtrip test uses Pydantic `ConfigDict(use_enum_values=True)`,
  so post-validation enum fields are *string values*, not enum members. Tests
  must compare roundtrip product / tier values with **`==`**, not **`is`**.
  See `docs/CC-15_TEST_DEFECT_ENUM_VALUE_COMPARISON.md` for the full note.

CC-15 is a **scratch-test concern**. The canonical standalone repo's tests
(`test_review_artifacts_policy.py`) do not currently use Pydantic; the note is
preserved here so that any future audit-roundtrip code introduced into
ForgeShield (or any consumer that audits `ActivationDecision` payloads) avoids
the same trap.

## 6. Production boundary (preserved)

The following production repositories were **not** modified, written to,
staged, committed, or pushed during FS-0.5 scratch validation:

- ContractForge
- ContractIQ (`/Users/home/code/contract-iq`)
- NativeForge (`/Users/home/code/NativeForge`)
- GrantForge
- DocketForge
- ForgeNode

The scratch validation was performed entirely inside
`/home/josefgray/projects/forgeshield-scratch`, which is not linked to any
production repository.

## 7. Readiness

- ForgeShield **v1.2 scratch validation passed**: 16 / 16 tests green under
  the exact pytest invocation in §3.
- ContractForge **FS-1 may proceed only after human approval**.
- **Automatic integration is not authorized.** No agent or automation may
  copy, import, or otherwise wire ForgeShield primitives into a production
  repo on the basis of this report.

## 8. FS-0.6 promotion note (module-name rename)

For full audit history: when scratch v1.2 was promoted into the standalone
`/home/josefgray/projects/forgeshield` repo (FS-0.6), the standalone repo was
already past v1.2 (at FS-2.0, `main` clean, 51 tests passing). Module
*contents* were equivalent to scratch v1.2, but two modules had been **renamed**
in the canonical repo prior to FS-0.6:

| Scratch v1.2 path | Canonical standalone repo path |
|---|---|
| `src/forge_security/artifact_integrity/core.py` | `src/forge_security/artifact_integrity/review_artifacts.py` |
| `src/forge_security/lifecycle/source_transitions.py` | `src/forge_security/lifecycle/activation_guard.py` |

The `Product`, `ReviewArtifactTier`, `POLICIES`, `is_tier_accepted`,
`enforce_tier`, `ActivationDecision`, and `activation_guard` symbols are
**byte-equivalent** across the rename (only module docstrings and the
absolute-vs-relative import path in the lifecycle module differ). The pinned
workspace rule at `.cursor/rules/forgeshield-artifact-policy.mdc` references
the canonical (renamed) paths. FS-0.6 therefore did **not** copy scratch
`.py` files into the standalone repo; instead it preserved the canonical
v1.2-equivalent modules already in `main` and added only this report plus
the CC-15 note.
