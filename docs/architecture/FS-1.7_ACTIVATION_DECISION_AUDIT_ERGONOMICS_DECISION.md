# FS-1.7 — ActivationDecision audit ergonomics: implement now or defer?

> **Status:** planning decision only. This file does not change production code,
> tests, policy, or `activation_guard` behavior.
>
> **Canonical repo:** `/home/josefgray/projects/forgeshield`
>
> **Reads:** `docs/architecture/FS-1_ENGINEERING_EXECUTION_PLAN.md`,
> `docs/architecture/FS-1_CI_CHECK_COMMANDS.md`,
> `docs/product/FS-1_CONTRACTFORGE_PILOT_PLAN.md`,
> `src/forge_security/lifecycle/activation_guard.py`,
> `tests/security/test_review_artifacts_policy.py`

---

## 1. Current ActivationDecision shape

`ActivationDecision` is a **frozen** `@dataclass` in
`src/forge_security/lifecycle/activation_guard.py` with four fields:

| Field | Type | Role |
|-------|------|------|
| `product` | `Product` | Enum passed into the guard (`str` enum; wire values include `contract-iq`, `docketforge`, `grantforge`, `nativeforge`). |
| `tier` | `ReviewArtifactTier` | CC-14 tier passed into the guard (`LEGACY_UNSIGNED` or `SIGNED_V1` on supported paths). |
| `activated` | `bool` | `True` iff `enforce_tier(product, tier)` succeeds; sole policy outcome bit. |
| `reason` | `str` | Human-readable string: on deny, `str(ArtifactPolicyViolation)`; on allow, `f"{product.value} accepts {tier.value}"`. |

There are **no** optional fields, timestamps, correlation identifiers, or
structured sub-objects on the type today.

---

## 2. Current activation_guard behavior

`activation_guard(product, tier)`:

1. Invokes `enforce_tier(product, tier)` inside a `try` block.
2. On `ArtifactPolicyViolation`: returns `ActivationDecision` with
   `activated=False` and `reason=str(exc)` (never re-raises).
3. On success: returns `ActivationDecision` with `activated=True` and
   `reason` describing acceptance as above.

**Invariants** (unchanged by FS-1.7 planning):

- The guard **never raises**; all outcomes are expressed as `ActivationDecision`.
- Tier acceptance truth is **delegated entirely** to `enforce_tier` / CC-14
  policy (`review_artifacts`); the guard does not implement parallel rules.
- Callers that need hard-fail semantics use `enforce_tier` directly (documented
  in the module docstring), not the guard.

Tests in `tests/security/test_review_artifacts_policy.py` pin the FS-1 product
× tier matrix, non-empty `reason` for all outcomes, and reason quality for
denials (tier and product values present in `reason`).

---

## 3. What ContractForge integrators likely need for audit logging

Per `FS-1_CONTRACTFORGE_PILOT_PLAN.md` and `FS-1_ENGINEERING_EXECUTION_PLAN.md`
§6 / §9, at the **activation boundary** integrators should record each guard
invocation with:

- **Product** — enum value / stable wire string (`Product` is `str, Enum`).
- **Tier** — one of the two CC-14 tier string values after classification.
- **Decision** — allow vs deny (`activated`) plus explanatory `reason` (operator
  / forensic copy; not end-user UI copy per pilot).
- **Timestamp** — integrator clock (not defined inside ForgeShield today).
- **Correlation id** — trace or request id from the integrator’s runtime.
- **Source metadata** — enough context to show **what the guard evaluated**
  (e.g. artifact id, ingest job id, pipeline stage); explicitly **integrator**
  attachment, not a third tier or fabricated policy state.

Rollback criteria in the pilot plan treat **missing** tier / product /
correlation metadata on activation records as a stop-ship signal (“broken
audit”). That bar applies to **integrator-emitted** audit events, not to
widening `ActivationDecision` by default.

---

## 4. Whether current fields are sufficient for the FS-1 pilot

**Yes, for the library side of the pilot.**

The four existing fields supply everything that is **policy-derived and
guard-owned** for an activation attempt:

- Identity of product and tier evaluated.
- Binary outcome aligned with `enforce_tier`.
- A stable, non-empty `reason` string for both allow and deny paths (pinned by
  tests).

The execution plan already assigns **timestamp**, **correlation id**, and
**source metadata** to the integrator, to be recorded **around** the returned
`ActivationDecision` — not as fields the guard must populate. That split matches
the current API surface: ForgeShield stays free of logging I/O and clock
coupling; ContractForge (or any pilot host) owns request scope and lineage
fields.

Therefore FS-1 pilot **audit completeness** does not require new
`ActivationDecision` members **if** integrators implement the documented bundle
(§8 below).

---

## 5. Risks of adding fields or helper APIs now

| Risk | Notes |
|------|--------|
| **Semantic creep** | New fields might be misread as new sources of truth (e.g. implied “audit level” or duplicate tier) and tempt bypasses or double policy interpretation. |
| **Logging side effects** | Any “ergonomic” API that touches `logging` or emits I/O from import or guard execution violates FS-1 non-goals and complicates library use in constrained environments. |
| **API churn during FS-1** | Extra public surface needs tests, review gates, and consumer updates while the pilot is still proving the baseline guard + D6/D7 path. |
| **Frozen dataclass compatibility** | Adding positional fields breaks callers that construct `ActivationDecision` positionally (uncommon but possible); mitigations add design overhead. |
| **False completeness** | A helper that serializes only guard fields might be mistaken for a full audit record, causing teams to omit integrator-required correlation and source metadata. |

---

## 6. Risks of deferring FS-1.7

| Risk | Notes |
|------|--------|
| **Inconsistent log schemas** | Different services might name or nest `product` / `tier` / `activated` differently unless a written integrator contract is followed. |
| **Boilerplate duplication** | Each product repeats the same small mapping from `ActivationDecision` to a log payload until a shared helper exists (could live in integrator code first). |
| **Late standardization cost** | If many consumers appear later, aligning on one optional ForgeShield helper may require a coordinated version bump — still manageable if additions are optional and non-breaking (§9). |

None of these risks block FS-1 **library** completion; they are operational and
documentation discipline issues mitigated by an explicit minimal logging
contract (§8).

---

## 7. Recommendation

**Defer FS-1.7 (optional ForgeShield-side audit ergonomics) for the FS-1 pilot.**

Rationale:

- Pilot and engineering plans already require integrators to emit the full audit
  bundle using **current** `ActivationDecision` fields plus integrator-owned
  fields.
- No gap was identified in **policy-relevant** data carried on
  `ActivationDecision` for allow/deny auditing.
- Keeping the library surface minimal through FS-1 reduces blast radius and
  avoids conflating “guard return value” with “complete audit row.”

Revisit FS-1.7 **after** pilot integration if multiple products need an
identical serialization shape and duplication becomes a measurable maintenance
burden — still subject to §10 and non-goals.

---

## 8. Minimal integrator logging contract (current fields only)

When emitting a structured audit event **immediately after**
`decision = activation_guard(product, tier)`, integrators **SHOULD** include at
minimum:

**From `ActivationDecision` (verbatim semantics, stable wire strings):**

- `activation.product` → log field `product` = `decision.product.value`
  (e.g. `"contract-iq"` for ContractForge pilot).
- `activation.tier` → log field `tier` = `decision.tier.value` (must be
  `"LEGACY_UNSIGNED"` or `"SIGNED_V1"` on paths that reached the guard).
- `activation.activated` → log field `activated` = `decision.activated`
  (boolean).
- `activation.reason` → log field `reason` = `decision.reason` (non-empty
  string; do not treat as user-facing).

**From integrator context (not on `ActivationDecision`):**

- `occurred_at` — ISO-8601 or operator-standard timestamp from integrator clock.
- `correlation_id` — trace, request, or job id from the active execution
  context.
- `source` — object or flat fields sufficient to tie the event to the classified
  artifact / ingest attempt the guard evaluated (e.g. internal artifact id,
  content hash reference, pipeline stage); must **not** invent a third tier or
  substitute for `tier`.

**Optional but recommended:**

- `event_type` constant, e.g. `forgeshield.activation_guard`, for log routing.
- Explicit **absence** of activation for pre-guard rejections: log at classify /
  ingest with a distinct `outcome` (not a `ReviewArtifactTier`), per pilot
  “reject before guard” rule.

This contract satisfies pilot rollback language on broken audit **when**
integrators implement it at every guard callsite for Contract IQ activation.

---

## 9. Safest non-breaking option if implemented later

If ForgeShield later adds ergonomics, prefer approaches that **do not change**
`activated` or `reason` derivation and **do not** add default logging:

1. **Pure function or static method** — e.g. `activation_decision_audit_core(decision) -> dict[str, bool | str]` returning only the four canonical keys with `.value` expansion. No I/O, no clock, no imports of `logging` from lifecycle code paths used by default.

2. **Optional frozen fields with defaults** — Add only **optional** dataclass
   fields with defaults (e.g. reserved for future integrator-passed annotations)
   if truly needed; keep `activation_guard` return shape backward compatible and
   document that new fields are never populated by the guard unless an explicit,
   reviewed API extension says otherwise. Prefer (1) over growing the dataclass
   if the only need is serialization.

3. **Versioned serializer** — If multiple wire formats are needed, put them in
   documented helpers with explicit version constants rather than implicit
   `str(decision)` behavior.

Any production change remains behind the human review gate in §10 and must
preserve: guard never raises; single delegation to `enforce_tier`; no new tiers;
no policy weakening.

---

## 10. Human review gate before any future production code change

Per `FS-1_ENGINEERING_EXECUTION_PLAN.md` §13 and pilot §8: **no merge** of
production changes to `activation_guard.py`, `review_artifacts.py`, related
semgrep rules, or `tests/security/test_review_artifacts_policy.py` without
**security-aware / two-person review** (or org-equivalent) and explicit
alignment with CC-14 and `.cursor/rules/forgeshield-artifact-policy.mdc`.

If FS-1.7 is executed as code later, treat it as touching the lifecycle API:
same gate, plus explicit confirmation that the change adds **no** logging side
effects by default and **no** activation semantic change.

---

## 11. Explicit non-goals (FS-1.7 decision scope)

- **No logging side effects** in ForgeShield library code paths for this ticket
  (no implicit `logging` calls from `activation_guard` or `ActivationDecision`).
- **No policy change** — `POLICIES`, `enforce_tier`, `is_tier_accepted`, and
  DocketForge defensive rules stay unchanged by FS-1.7 documentation.
- **No ContractForge code** in this repository as part of FS-1.7; integrator
  contract is specified here for out-of-repo consumers only.
- **No activation semantics change** — `activated` must remain the pure result
  of `enforce_tier` for the given `(product, tier)`; `reason` rules stay
  policy-aligned.

---

## References

- `docs/architecture/FS-1_ENGINEERING_EXECUTION_PLAN.md` §8–§9, §12 (FS-1.7
  ticket), §13
- `docs/product/FS-1_CONTRACTFORGE_PILOT_PLAN.md` §2, §5, §9
- `src/forge_security/lifecycle/activation_guard.py`
- `tests/security/test_review_artifacts_policy.py`
