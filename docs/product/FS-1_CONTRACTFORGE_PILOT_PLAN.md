# FS-1 — ContractForge pilot integration plan

> **Status:** planning. Normative for FS-1 scope. This file is documentation
> only; it does not change code by itself.
>
> **Baseline:** ForgeShield FS-0.5 — `e6ea117 chore: establish ForgeShield FS-0.5 scratch gate`.

## 1. FS-1 mission

FS-1 is the **first ContractForge pilot integration layer**: the milestone
where ContractForge (`Product.CONTRACT_IQ`) becomes the first product to run
the FS-0.5 stack end-to-end in a real workflow—**activation guard**, **CC-14
review artifact policy**, **PromptBuilder (D7)**, and **wrap_untrusted_content
(D6)**—under controlled pilot rules.

Goals:

1. **Prove integration** — Demonstrate that a single product can classify
   inbound review artifacts, call `activation_guard` as the sole policy gate,
   route external contract bytes only through sanctioned APIs, and emit
   auditable decisions—without widening `LEGACY_UNSIGNED` beyond the
   ContractForge pilot allowance already committed in FS-0.5.
2. **Contain blast radius** — Keep DocketForge and GrantForge on **SIGNED_V1
   only** with no exceptions. Do not add products, tiers, or table rows that
   expand unsigned acceptance.
3. **Do not couple to NativeForge** — `POLICIES[Product.NATIVEFORGE]` may still
   list `LEGACY_UNSIGNED` until FS-12, but **FS-1 design, tests, and CI must
   not rely on that path**. NativeForge tightening remains FS-12’s job.

FS-1 is **not** FS-12 (NativeForge policy tightening), **not** FS-2 (signing /
`SIGNED_V1` producer), and **not** DocketForge or GrantForge work.

## 2. What ContractForge pilot integration means

**Pilot integration** means: at the ContractForge contract-review **activation
boundary**, the product uses ForgeShield as specified in FS-0.5, with
`Product.CONTRACT_IQ` as the only product that may accept `LEGACY_UNSIGNED`
review artifacts during the pilot, per the existing policy table.

Concretely (normative intent for the integration; implementation lands in the
ContractForge repo under its own change train, not in this planning step):

- **Single policy gate** — One well-defined callsite invokes
  `activation_guard(Product.CONTRACT_IQ, tier)` where `tier` is a
  `ReviewArtifactTier` (`LEGACY_UNSIGNED` or `SIGNED_V1`). No parallel
  “shadow” tier checks in product code.
- **Prompt hygiene** — All externally sourced contract text passes through
  `PromptBuilder.add_external_content` (and thus the untrusted-content
  envelope); no contract bytes in trusted layers or raw prompt f-strings in
  violation of the semgrep tripwires.
- **Classification** — Inbound artifacts are classified before the guard so
  only valid tier values reach `activation_guard`. Malformed or untrusted
  inputs are rejected **before** the guard; `REJECTED` is an ingest outcome,
  **not** a third review-artifact tier (CC-14 defines exactly two tiers).
- **Auditability** — Each activation records product, tier, decision, time,
  correlation id, and source metadata sufficient to prove what the guard saw.

## 3. What is allowed under `LEGACY_UNSIGNED` during the pilot

**Scope:** `Product.CONTRACT_IQ` only, and only at artifact positions and
workflows explicitly covered by the pilot—**no widening** of
`POLICIES[Product.CONTRACT_IQ].accepted_tiers` beyond
`frozenset({LEGACY_UNSIGNED, SIGNED_V1})` as committed in FS-0.5.

Allowed:

- **Activation** — `activation_guard(Product.CONTRACT_IQ, LEGACY_UNSIGNED)`
  may return `activated=True` when policy and ingest checks pass.
- **Provenance labeling** — Downstream handling may tag lineage as legacy /
  unsigned for observability and future migration, without treating the
  artifact as `SIGNED_V1`.
- **Telemetry** — Structured logs/metrics on allow vs deny by tier for
  pilot observability (counts, rates, sampling as appropriate).

Not allowed: using `LEGACY_UNSIGNED` as an excuse to skip D6/D7, bypass the
guard, or accept unsigned artifacts for DocketForge or GrantForge.

## 4. What remains forbidden

- **DocketForge** — `SIGNED_V1` only at every artifact position from day one.
  No exceptions. The defensive `is_tier_accepted(DOCKETFORGE, LEGACY_UNSIGNED)
  == False` behavior must remain; do not weaken the table or that check.
- **GrantForge** — `SIGNED_V1` only by default; no `LEGACY_UNSIGNED`.
- **Third tier** — Do not introduce another `ReviewArtifactTier` value or
  “implicit” tier in policy.
- **Policy expansion** — Do not add `LEGACY_UNSIGNED` to any product that
  does not already have it under FS-0.5 rules. Do not add new `Product` rows
  that include `LEGACY_UNSIGNED` except through a deliberate FS-XX plan that
  updates `tests/security/test_review_artifacts_policy.py` and CC-14—**not**
  part of FS-1.
- **Bypassing the guard** — Product code must not re-implement activation by
  reading `POLICIES` or calling `is_tier_accepted` / `enforce_tier` instead of
  going through `activation_guard` for the “may I activate?” question.
- **Weakening FS-0.5 controls** — No silencing of semgrep prompt f-string
  rules; no weakening of `.cursor/rules/forgeshield-artifact-policy.mdc`; no
  skipping `wrap_untrusted_content` for untrusted bytes.

## 5. Activation guard responsibilities

**ForgeShield (`activation_guard`):**

- Delegates tier acceptance to `enforce_tier` / CC-14 policy.
- **Never raises**; returns `ActivationDecision` with `activated` and `reason`
  for uniform handling and audit.
- Remains the **only** supported “may I activate?” API for product code (per
  CC-14 / workspace policy).

**Integrator (ContractForge at the activation boundary):**

- Passes the **classified** `ReviewArtifactTier`—not raw blobs—to the guard.
- On `activated=False`: do not activate; log/audit; surface a safe operator /
  user path without treating `reason` as end-user copy.
- On `activated=True`: proceed only with audit fields that pin `tier`,
  `product`, and correlation metadata; do not re-derive tier later from a
  different source of truth.
- Does **not** import or branch on `POLICIES` / `is_tier_accepted` for
  activation decisions (guards against drift; enforceable via review and
  optional ContractForge-side lint rules in a future change).

## 6. Artifact lifecycle from `LEGACY_UNSIGNED` to `SIGNED_V1`

Two **policy tiers** only; lifecycle describes how instances move from
unsigned legacy provenance to signed manifests, without mutating tier on the
same artifact instance.

1. **Ingest** — Bytes and metadata arrive; optional crypto / manifest
   verification runs in the producer or verifier appropriate to the pipeline.
2. **Classify for policy** — If verification yields a valid detached signature
   over a manifest that pins artifact bytes by hash → treat as **`SIGNED_V1`**
   for policy. If the pipeline is pre-FS-12 / unsigned but otherwise accepted
   for the pilot → **`LEGACY_UNSIGNED`**. Malformed or failed verification →
   **reject before the guard** (not a third tier).
3. **Guard** — `activation_guard(Product.CONTRACT_IQ, tier)`; if not
   activated, stop; do not enter review actions that consume the artifact as
   approved.
4. **Use** — Review steps consume the artifact; audit records carry the tier
   and provenance.
5. **Graduate content, not rows** — When a **`SIGNED_V1` producer** exists
   (planned as FS-2, out of FS-1 scope), the **same logical content** may be
   re-emitted as a **new** `SIGNED_V1` artifact with new ids and ledger
   entries. The original `LEGACY_UNSIGNED` instance is **not** silently
   upgraded in place.

**Invariants:** Tier for a given artifact instance is fixed after
classification. Re-signing creates a **new** artifact identity.

## 7. Required tests for FS-1

ForgeShield-side tests (names illustrative; exact modules may vary):

- **Contract IQ pilot policy** — `activation_guard(CONTRACT_IQ, LEGACY_UNSIGNED)`
  allows; `activation_guard(DOCKETFORGE|GRANTFORGE, LEGACY_UNSIGNED)` denies;
  `SIGNED_V1` allows for all products that accept it per table. NativeForge’s
  current `LEGACY_UNSIGNED` acceptance remains pinned by existing FS-0.5 tests
  with an explicit FS-12 follow-up; **FS-1 tests must not assume NativeForge
  behavior for ContractForge paths.**
- **No policy drift** — `POLICIES` matches: Contract IQ
  `{LEGACY_UNSIGNED, SIGNED_V1}`; DocketForge and GrantForge `{SIGNED_V1}`
  only; product set unchanged unless a deliberate policy FS updates tests.
- **Guard semantics** — Guard never raises; rejected pairs return
  `activated=False` with non-empty `reason`.
- **Prompt / untrusted path** — Tests that the contract-review message shape
  uses exactly one external untrusted envelope for external contract bytes
  and does not place those bytes in system/developer/trusted layers (align
  with existing CC-10 / PromptBuilder tests; extend as needed for FS-1
  fixtures).
- **Regression** — Full `pytest` suite stays green; FS-0.5 baseline count
  (e.g. 41 tests at FS-0.5) must not drop without explanation.

Classifier unit tests may live in ForgeShield or ContractForge depending on
where classification is implemented; either way, **behavior above is
required** before declaring FS-1 done.

## 8. Required CI checks

- **`pytest`** — Full suite passes on every relevant PR.
- **Semgrep** — `semgrep/forge_security` (or repo-standard config): zero
  violations for prompt f-string / injection tripwires; fail the build on new
  findings.
- **Policy pins** — Existing tests in `tests/security/test_review_artifacts_policy.py`
  must run in CI; any change to `review_artifacts.POLICIES` requires matching
  test updates in the **same** change (per CC-14).
- **Artifact policy rule** — `.cursor/rules/forgeshield-artifact-policy.mdc`
  remains present and authoritative (optional CI guard: file exists and
  non-empty).
- **Branch protection / review** — Human review for changes touching
  `artifact_integrity`, `lifecycle`, semgrep rules, and CC-14 tests.

Optional hardening (recommended in FS-1 implementation, if not already
present): golden serialization or hash of `POLICIES` to catch accidental
table edits.

## 9. Rollback criteria

Trigger **stop-ship / revert** for the FS-1 integration train if **any** of:

- **Wrong product** — `LEGACY_UNSIGNED` accepted or activation attempted for
  DocketForge or GrantForge in logs, tests, or production traces.
- **Policy regression** — `POLICIES` or `is_tier_accepted` changed to allow
  `LEGACY_UNSIGNED` outside the FS-0.5 Contract IQ (+ pre-FS-12 NativeForge)
  rules, or DocketForge defensive check removed.
- **Guard bypass** — Product code activates based on direct `POLICIES` /
  `is_tier_accepted` usage instead of `activation_guard` for the activation
  decision.
- **Broken audit** — Activations without recordable tier/product/correlation
  metadata, or tier strings outside the two CC-14 enum values on allowed
  paths.
- **Hygiene failure** — Semgrep tripwire fires on merged code; untrusted
  content skips `wrap_untrusted_content` / `add_external_content` paths.
- **Stability** — Pilot SLO breach (e.g. guard or classifier error rate spike)
  as defined by operators before pilot start.

Rollback **does not** relax DocketForge or GrantForge policy; it reverts the
integration change while keeping FS-0.5 primitives and the policy table
intact unless a separate security process dictates otherwise.

## 10. Graduation criteria from pilot to FS-12

**FS-12** means NativeForge drops `LEGACY_UNSIGNED` and tightens the
activation guard per CC-14. **Pilot graduation** for FS-1 is the evidence bar
that makes it safe to execute FS-12 **without** having depended on
NativeForge’s temporary allowance for ContractForge work.

Authorize **start of FS-12 implementation** when **all** of the following
hold:

1. **Stable pilot** — ContractForge integration has run for an agreed
   observation window with no §9 rollback events.
2. **Proven guard + hygiene** — Production or staging traces show exclusive
   use of `activation_guard` for activation, correct tier distribution, and
   D6/D7 paths for external contract bytes.
3. **No cross-product leakage** — No DocketForge or GrantForge path has
   consumed or attempted `LEGACY_UNSIGNED` artifacts.
4. **Policy intact** — `POLICIES` and defensive DocketForge check unchanged in
   spirit; tests green.

**Explicit:** Shipping FS-12 **does not** automatically remove
`LEGACY_UNSIGNED` from Contract IQ; that is a later policy decision (e.g.
after FS-2 `SIGNED_V1` producer maturity). FS-1 only requires that Contract
Forge pilot success **not** block NativeForge tightening.

## 11. Explicit non-goals

- No DocketForge or GrantForge integration in FS-1.
- No signing service, KMS, or `SIGNED_V1` **producer** in FS-1 (FS-2+).
- No NativeForge policy tightening in FS-1 (FS-12).
- No new `ReviewArtifactTier` or third artifact tier.
- No dependency of FS-1 deliverables on NativeForge accepting
  `LEGACY_UNSIGNED`.
- No weakening of semgrep rules, Cursor artifact policy, or CC-14 tests.
- No general-purpose UI, CLI, or storage platform—only integration and
  supporting tests/CI/docs as scoped.

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **Policy table widened** for unsigned artifacts | CI + `test_review_artifacts_policy` pins; two-person review for `review_artifacts.py`; optional golden `POLICIES` snapshot. |
| **DocketForge / GrantForge accidental `LEGACY_UNSIGNED`** | Defensive `is_tier_accepted` for DocketForge; tests; audit queries on `product` + `tier`. |
| **Guard bypass** | Code review; ContractForge lint ban on `POLICIES`/`is_tier_accepted` for activation (future); log only `ActivationDecision` from guard. |
| **Prompt injection via trusted layers** | D7 layering + semgrep + tests on message list shape. |
| **Classifier bugs** | Pre-guard rejection; metrics; rollback on error-rate SLO breach. |
| **Conflating pilot with NativeForge** | FS-1 tests and design avoid NativeForge; FS-12 remains a separate change set with its own test flip for NativeForge. |
| **Ambiguous graduation** | §10 ties pilot evidence to FS-12 authorization; Contract IQ unsigned removal stays a separate follow-on decision. |

---

**References:** `src/forge_security/artifact_integrity/review_artifacts.py`,
`src/forge_security/lifecycle/activation_guard.py`, D6/D7 modules,
`tests/security/test_review_artifacts_policy.py`,
`.cursor/rules/forgeshield-artifact-policy.mdc`, semgrep configs under
`semgrep/forge_security/`.
