# FS-1.8 — ForgeShield FS-1 definition-of-done checklist

> **Status:** normative close-out checklist for FS-1 ForgeShield engineering.
> **Documentation only** — this file does not change code, tests, policy,
> semgrep rules, D6/D7 primitives, `activation_guard`, or CC-14 by itself.
>
> **Canonical repo:** `/home/josefgray/projects/forgeshield`
>
> **Reads:** `docs/architecture/FS-1_ENGINEERING_EXECUTION_PLAN.md`,
> `docs/architecture/FS-1_CI_CHECK_COMMANDS.md`,
> `docs/product/FS-1_CONTRACTFORGE_PILOT_PLAN.md`,
> `docs/architecture/FS-1.7_ACTIVATION_DECISION_AUDIT_ERGONOMICS_DECISION.md`,
> `tests/security/test_review_artifacts_policy.py`,
> `tests/security/test_prompt_builder.py`

---

## 1. FS-1 scope summary

FS-1 is the **ForgeShield-side** milestone that proves the FS-0.5 stack is
sufficient for the **ContractForge pilot** (`Product.CONTRACT_IQ`): **activation
guard** as the sole “may I activate?” API, **CC-14** review-artifact policy
(exactly two tiers), **PromptBuilder (D7)** with **wrap_untrusted_content (D6)**
for external contract bytes, and **regression discipline** (tests, documented
CI commands, human gates).

FS-1 **does not** implement ContractForge application code, signing producers,
DocketForge/GrantForge product integration, NativeForge FS-12 tightening, or new
`ReviewArtifactTier` values. ForgeShield supplies **libraries and contracts
only**; real ContractForge wiring lives in **its own repository / workstream**.

---

## 2. Completed FS-1 tickets (traceability)

| Ticket | Outcome |
|--------|---------|
| **FS-1.1** — Activation guard matrix coverage | `activation_guard` product × tier matrix for Contract IQ, DocketForge, and GrantForge is explicitly tested (six pairs) in `tests/security/test_review_artifacts_policy.py` (`test_activation_guard_fs1_product_tier_matrix`, `test_activation_guard_never_raises_for_fs1_matrix_pairs`). |
| **FS-1.2** — GrantForge / Contract IQ `SIGNED_V1` paths | **Already satisfied by FS-1.1:** the same parametrized matrix includes `CONTRACT_IQ` + `SIGNED_V1` (allow), `GRANTFORGE` + `LEGACY_UNSIGNED` (deny), and `GRANTFORGE` + `SIGNED_V1` (allow). |
| **FS-1.3** — Rejection reason quality | Denied activations assert non-empty `reason` with tier and product wire values present (`_assert_rejected_activation_reason_quality` and matrix tests). |
| **FS-1.4** — ContractForge / Contract IQ contract-review PromptBuilder fixture | `contract_review_messages` fixture and associated tests in `tests/security/test_prompt_builder.py` model five-layer review prompts with contract bytes only in `add_external_content` / `EXTERNAL_UNTRUSTED_CONTENT`. |
| **FS-1.5** — CI / check command reference | Authoritative copy-pastable commands: `docs/architecture/FS-1_CI_CHECK_COMMANDS.md`. |
| **FS-1.6** — `POLICIES` snapshot / stability test | Canonical serialization of `POLICIES` pinned in `test_policies_canonical_snapshot_fs16` (`tests/security/test_review_artifacts_policy.py`); intentional table edits require deliberate snapshot update after human review (per test comment). |
| **FS-1.7** — Audit ergonomics | **Decision documented only:** defer optional `ActivationDecision` serializer/helper or extra fields until after pilot evidence — see `docs/architecture/FS-1.7_ACTIVATION_DECISION_AUDIT_ERGONOMICS_DECISION.md`. No production change for FS-1.7 in-repo as part of that decision. |
| **FS-1.8** — Definition-of-done checklist | This document. |

---

## 3. Explicit invariants (must remain true)

- **Contract IQ (pilot)** — Accepts **`LEGACY_UNSIGNED`** and **`SIGNED_V1`**
  for the FS-1 pilot only as already pinned in CC-14 / `POLICIES`; no widening
  of `accepted_tiers` beyond `frozenset({LEGACY_UNSIGNED, SIGNED_V1})` without a
  deliberate FS-XX plan and synchronized policy tests.
- **DocketForge** — Remains **`SIGNED_V1` only** at every artifact position; no
  exceptions; defensive denial of `LEGACY_UNSIGNED` must remain.
- **GrantForge** — Remains **`SIGNED_V1` only**; no `LEGACY_UNSIGNED`.
- **NativeForge `LEGACY_UNSIGNED`** — Remains an **FS-12 precursor** only; FS-1
  design, docs, and Contract IQ matrix tests **must not depend** on NativeForge
  accepting legacy unsigned for ContractForge validation paths.
- **No expansion of `LEGACY_UNSIGNED`** — Do not add `LEGACY_UNSIGNED` to
  DocketForge, GrantForge, or any future product except via an explicit,
  reviewed FS-XX change aligned with `.cursor/rules/forgeshield-artifact-policy.mdc`
  and `tests/security/test_review_artifacts_policy.py`.
- **No ContractForge repo changes** — FS-1 ForgeShield delivery does not modify
  the ContractForge application repository from this workstream.
- **No automatic commits** — Agents, hooks, and automation must not commit or
  push in place of a deliberate human decision (see FS-1.5 human gate).

---

## 4. Required validation commands

From repository root, with project venv activated and `PYTHONPATH=src` set per
[`FS-1_CI_CHECK_COMMANDS.md`](FS-1_CI_CHECK_COMMANDS.md):

```bash
python -m pytest -v
```

```bash
semgrep --validate --config semgrep/forge_security/no-direct-prompt-fstring.yml
```

(Full environment setup, focused pytest modules, and optional semgrep **scan**
of `src/` are documented in that same file.)

---

## 5. Current expected validation baseline

Operators should treat the following as the **expected green baseline** when
closing FS-1 (update this section only when the suite or rule pack intentionally
changes):

- **`python -m pytest -v`** — **51 tests passed** (full suite green; zero
  unexpected skips or failures).
- **`semgrep --validate --config semgrep/forge_security/no-direct-prompt-fstring.yml`**
  — **Valid** rule pack with **2 rules** loaded from that YAML file.

If counts diverge, confirm whether tests or rules were added/removed on purpose
and refresh this baseline in a follow-on documentation change after review.

---

## 6. Required git clean-state conditions

Before treating the branch as **merge- or pilot-ready**:

- **Local `main` clean** — `git status` shows no unintended modifications;
  only files you mean to ship are present (see FS-1.5 §10 “clean check”).
- **Local `HEAD` matches `origin/main` after push** — After pushing intended
  work, `main` at the operator workstation should align with `origin/main` so
  unpublished drift is not mistaken for the released baseline.

---

## 7. Release readiness decision

**FS-1 is ready for ContractForge pilot integration** (ForgeShield library side)
when **all** of the following hold:

- Every item in **§3 Explicit invariants** remains satisfied in the tree under
  review.
- **§4 Required validation commands** complete successfully at the **§5**
  baseline (or updated documented baseline with cause).
- **§6 Git clean-state conditions** hold for the revision you intend integrators
  to consume.
- Completed tickets in **§2** are reflected in the current `main` (or agreed
  release branch) you are handing off.

ContractForge “pilot live” in production remains **outside** this repository and
depends on integrator work, audits, and operator playbooks in addition to the
above.

---

## 8. Known deferred items

- **FS-12** — Artifact signing maturity, NativeForge **`LEGACY_UNSIGNED`**
  removal, and activation-guard tightening for NativeForge per CC-14 / pilot
  graduation criteria — **not** FS-1 scope.
- **Optional FS-1.7 follow-up** — `ActivationDecision` serializer/helper or
  optional fields **only after human review** and pilot evidence; must not
  change activation semantics, add logging side effects by default, or add
  tiers (see FS-1.7 decision doc).
- **Real ContractForge integration** — Implementation, deployment, and UI in the
  **ContractForge repository / separate workstream**, not in ForgeShield FS-1
  library delivery.

---

## 9. Human gate

- **No production policy changes** (including `review_artifacts.POLICIES`,
  defensive DocketForge behavior, or CC-14 interpretation) **without**
  security-aware review and explicit alignment with
  `.cursor/rules/forgeshield-artifact-policy.mdc` and pinned tests.
- **No commit** until an assistant/human has reviewed the diff and the **user
  explicitly approves** recording that revision (no silent or automated commits).

---

## 10. Operator signoff (checkboxes)

Use this section as the final gate before declaring FS-1 ForgeShield engineering
complete or before pointing integrators at a specific revision.

- [ ] Read and understood FS-1 scope (**§1**) and completed ticket mapping (**§2**).
- [ ] Confirmed **§3 Explicit invariants** (Contract IQ pilot tiers, DocketForge /
      GrantForge `SIGNED_V1` only, NativeForge legacy as FS-12 precursor only,
      no `LEGACY_UNSIGNED` expansion, no ContractForge repo edits from this
      train, no automatic commits).
- [ ] Ran `python -m pytest -v` — green; **51** tests passed (or documented new
      baseline with justification).
- [ ] Ran `semgrep --validate --config semgrep/forge_security/no-direct-prompt-fstring.yml`
      — success; **2** rules in config (or documented change).
- [ ] Git: working tree clean for intended release; **`main`** aligned with
      **`origin/main`** after push (**§6**).
- [ ] Acknowledged **§7** release readiness decision for ContractForge pilot
      integration (library side).
- [ ] Acknowledged **§8** deferred items (FS-12, optional FS-1.7 code, real
      ContractForge integration elsewhere).
- [ ] **§9 Human gate** satisfied: policy-sensitive paths reviewed; **no commit**
      without explicit approval after review.

**Signed:** _________________________ **Date:** _________________________

**Role (e.g. operator / security reviewer):** _________________________

---

**References:** `docs/architecture/FS-1_ENGINEERING_EXECUTION_PLAN.md` §15,
`docs/product/FS-1_CONTRACTFORGE_PILOT_PLAN.md` §7–§9,
`docs/architecture/FS-1_CI_CHECK_COMMANDS.md`,
`docs/architecture/FS-1.7_ACTIVATION_DECISION_AUDIT_ERGONOMICS_DECISION.md`,
`src/forge_security/artifact_integrity/review_artifacts.py`,
`src/forge_security/lifecycle/activation_guard.py`,
`semgrep/forge_security/no-direct-prompt-fstring.yml`,
`.cursor/rules/forgeshield-artifact-policy.mdc`.
