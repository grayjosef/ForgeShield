# FS-2.0 — ContractForge pilot integration contract (ForgeShield)

> **Status:** normative integrator contract. **Documentation only** — this file
> does not change production code, tests, semgrep rules, D6/D7 primitives,
> `activation_guard`, CC-14 / `POLICIES`, or `.cursor/rules/forgeshield-artifact-policy.mdc`
> by itself.
>
> **Canonical ForgeShield repo:** `/home/josefgray/projects/forgeshield`
>
> **Reads:** `docs/architecture/FS-1.8_DEFINITION_OF_DONE_CHECKLIST.md`,
> `docs/architecture/FS-1_CI_CHECK_COMMANDS.md`,
> `docs/architecture/FS-1.7_ACTIVATION_DECISION_AUDIT_ERGONOMICS_DECISION.md`,
> `docs/product/FS-1_CONTRACTFORGE_PILOT_PLAN.md`,
> `docs/architecture/FS-1_ENGINEERING_EXECUTION_PLAN.md`,
> `src/forge_security/lifecycle/activation_guard.py`,
> `src/forge_security/artifact_integrity/review_artifacts.py`,
> `src/forge_security/ai_security/prompt_builder.py`,
> `src/forge_security/ai_security/untrusted_content.py`

---

## 1. FS-2.0 scope summary

FS-2.0 is a **ForgeShield-side integration contract only**: a written agreement
for how **ContractForge** must consume ForgeShield libraries during the pilot,
so integration stays **safe, auditable, and consistent** with CC-14 and FS-1.

In this sprint, FS-2.0 **does not**:

- Modify the ContractForge application repository or workstream.
- Add or change **production code** in ForgeShield (no adapters shipped from
  this milestone in-repo).
- Replace FS-1 library delivery; it **narrows** integrator behavior to an
  explicit contract operators and reviewers can gate before any ContractForge
  implementation commit.

**Purpose:** prevent unsafe or inconsistent integration (guard bypass, missing
audit, contract bytes in trusted prompt layers, invented tiers, or policy drift)
before ContractForge-side wiring begins under its own change train.

---

## 2. ContractForge pilot integration boundary

**ContractForge** (separate product / repository) **calls** ForgeShield
primitives: `activation_guard`, `Product`, `ReviewArtifactTier`,
`PromptBuilder`, and (indirectly via `PromptBuilder.add_external_content`)
`wrap_untrusted_content` from `untrusted_content`.

**ForgeShield does not own** ContractForge UI, database schema, workflow
orchestration beyond what integrators build, deployment topology, or customer
runtime processes. ForgeShield supplies **libraries and behavioral contracts**
only.

**ContractForge owns** request identifiers, timestamps, user and organization
context, artifact identifiers, persistence, and any orchestration that
invokes ForgeShield. ForgeShield types such as `ActivationDecision` carry
**policy-derived** fields only; correlation, environment, and lineage belong to
the integrator (see FS-1.7 minimal logging contract).

---

## 3. Required activation flow

At every **activation boundary** (before treating a classified review artifact as
approved for downstream consumption):

1. **Classify** the inbound artifact into a `ReviewArtifactTier` **before**
   activation: exactly `LEGACY_UNSIGNED` or `SIGNED_V1` per CC-14. Malformed
   verification, missing manifest/signature when required by pipeline rules, or
   ambiguous classification outcomes are **ingest failures** — not tiers.
2. **Call** `activation_guard(product=Product.CONTRACT_IQ, tier=resolved_tier)`
   (positional `activation_guard(Product.CONTRACT_IQ, resolved_tier)` is
   equivalent). This is the **only** supported “may I activate?” API for
   product activation decisions; do not branch on `POLICIES` or
   `is_tier_accepted` / `enforce_tier` for that question in product code.
3. If `decision.activated` is **false**: **do not activate** the artifact for
   review consumption; record an audit event (§4); do not treat
   `decision.reason` as end-user copy.
4. If `decision.activated` is **true**: proceed **only** under **pilot limits**
   documented in `FS-1_CONTRACTFORGE_PILOT_PLAN.md` (Contract IQ pilot tiers,
   no widening of `LEGACY_UNSIGNED`, DocketForge/GrantForge unchanged).
5. **Pre-guard invalid artifacts** (unclassifiable tier, failed ingest, policy
   mismatch with actual bytes): **reject before** `activation_guard`. These paths
   must **not** call the guard with a fabricated tier and must **not** invent a
   third `ReviewArtifactTier` value or “implicit” tier string for CC-14.

`activation_guard` **never raises**; denial is always expressed via
`ActivationDecision` (`src/forge_security/lifecycle/activation_guard.py`).

---

## 4. Required audit event schema

Emit a **structured audit event at every `activation_guard` invocation**
immediately after the call, combining `ActivationDecision` fields with
integrator-owned context (FS-1.7 §8).

**Pilot readiness:** missing required integrator fields (including correlation
and source binding) is **stop-ship** per `FS-1_CONTRACTFORGE_PILOT_PLAN.md` §9
and FS-1.7 — treat as broken audit, not as a library gap.

**Minimal JSON-shaped example** (field names illustrative; wire format may be
Protobuf, log schema, or DB columns if isomorphic):

```json
{
  "event_type": "forgeshield.activation_guard",
  "occurred_at": "2026-05-12T18:04:02.123456Z",
  "correlation_id": "req_01jxyz789abcdef",
  "product": "contract-iq",
  "tier": "SIGNED_V1",
  "activated": true,
  "reason": "contract-iq accepts SIGNED_V1",
  "source": {
    "artifact_id": "art_01jabc123contractforge",
    "pipeline_stage": "post_verify_classify",
    "content_hash": "sha256:0f1e2d3c4b5a69788796a5b4c3d2e1f0..."
  },
  "actor": {
    "principal_id": "svc:contractforge-review-worker",
    "principal_type": "system"
  },
  "environment": "staging",
  "forgeshield_commit": "abc123def456"
}
```

**Field notes:**

| Field | Required | Source |
|-------|----------|--------|
| `event_type` | Recommended | Constant for routing (e.g. `forgeshield.activation_guard`). |
| `occurred_at` | Yes | Integrator clock; ISO-8601 or operator standard. |
| `correlation_id` | Yes | Trace, request, or job id from ContractForge runtime. |
| `product` | Yes | `decision.product.value` (e.g. `"contract-iq"`). |
| `tier` | Yes | `decision.tier.value` (`"LEGACY_UNSIGNED"` or `"SIGNED_V1"` on paths that reached the guard). |
| `activated` | Yes | `decision.activated`. |
| `reason` | Yes | `decision.reason` (non-empty; operator/forensic, not end-user UI). |
| `source.artifact_id` | Yes | Integrator artifact identity the guard decision applies to. |
| `source.pipeline_stage` | Yes | Stage name sufficient for replay (e.g. ingest, verify, classify). |
| `source.content_hash` **or** `source.content_reference` | Yes (one or both) | Stable reference to bytes evaluated (hash preferred when available). |
| `actor` | If available | User or system principal; omit only if truly unknown, with operator approval. |
| `environment` | Yes | Deployment/stage identifier (e.g. `prod`, `staging`). |
| `forgeshield_commit` **or** package version | If available | Git SHA or released package version of ForgeShield consumed. |

**Pre-guard rejections:** use a **distinct** `event_type` or `outcome` (not a
`tier`) so logs never fabricate `ReviewArtifactTier` values for failed classify
paths (FS-1.7 §8).

---

## 5. Required PromptBuilder integration flow

Use **D7** `PromptBuilder` (`src/forge_security/ai_security/prompt_builder.py`)
so externally sourced contract material flows through **exactly one** external
choke point: `add_external_content`, which internally calls **D6**
`wrap_untrusted_content`.

Layers are always emitted in this **fixed order** when populated:

1. **System layer** — `add_system_instruction`: stable policy and role
   instructions only (no contract body, no vendor/user artifact prose).
2. **Developer layer** — `add_developer_constraint`: deterministic task
   constraints only (schemas, output shape, tool rules). No raw contract bytes.
3. **Trusted internal layer** — `add_trusted_context`: trusted metadata and
   **classifier output that is treated as internal** only when it is genuinely
   non-user-controlled; never paste full contract text here. If classifier
   output could contain echoed external bytes, treat that echo as **external**
   (see §6).
4. **External untrusted layer** — contract bytes **only** through
   `add_external_content(content, source)`, which wraps via
   `wrap_untrusted_content` and emits `<EXTERNAL_UNTRUSTED_CONTENT …>`.
5. **User task layer** — `add_user_task`: the actual review task instructions
   for the model (still must not embed raw contract bytes; reference the
   external envelope only).

**Invariant:** **No raw contract bytes** in system, developer, or trusted
internal layers. Role-switch markers in those layers raise
`PromptInjectionError`; neutralization of hostile patterns happens in the
external envelope path.

---

## 6. Contract body safety rules

Treat **all** of the following as **external untrusted content** (same
security class as user uploads):

- Contract text and clauses from any channel.
- Attachments, scraped pages, pasted excerpts.
- Uploaded files, OCR output, email bodies.
- Vendor- or user-provided artifact payloads and previews.

**Routing:** such content must reach the model only after
`wrap_untrusted_content` via **`PromptBuilder.add_external_content`** — the
only sanctioned public ingress for external bytes on the builder.

**Injection-like markers** (e.g. ChatML tokens, “ignore previous instructions”,
`\nHuman:`) must **never** be interpreted as trusted instructions when they
originate from external sources; the external path **neutralizes** known
patterns rather than elevating them into system/developer/trusted layers.

**Preprocessing:** do **not** summarize, compress, or transform external content
into system/developer/trusted layers **unless** the preprocessing output is
**still** treated as external untrusted content (i.e., passed through
`add_external_content` / `wrap_untrusted_content`). Otherwise, smuggled
instructions could land in a “trusted” summary.

---

## 7. Pilot allowed artifact policy

Aligned with CC-14 and pinned tests (`tests/security/test_review_artifacts_policy.py`):

| Product | Pilot / policy | FS-2.0 note |
|---------|----------------|-------------|
| **Contract IQ** (`Product.CONTRACT_IQ`) | May accept **`LEGACY_UNSIGNED`** and **`SIGNED_V1`** during the FS-1 / FS-2 pilot | No widening of `accepted_tiers` beyond `frozenset({LEGACY_UNSIGNED, SIGNED_V1})` without a deliberate FS-XX change and synchronized tests. |
| **DocketForge** | **`SIGNED_V1` only** | No exceptions; defensive denial of `LEGACY_UNSIGNED` must remain. |
| **GrantForge** | **`SIGNED_V1` only** | No `LEGACY_UNSIGNED`. |
| **NativeForge** | `LEGACY_UNSIGNED` acceptance is an **FS-12 precursor** in the policy table | **Not part** of ContractForge pilot validation paths; FS-2.0 does not require or describe NativeForge integration. |

**No new** `ReviewArtifactTier` values and no implicit third tier strings in
audit or policy paths.

---

## 8. Rejection and failure handling

| Condition | Required behavior |
|-----------|-------------------|
| `activation_guard` returns `activated=False` | **No activation** for that artifact instance; emit audit; safe operator handling. |
| Invalid or missing **tier** before guard | **Reject before** `activation_guard`; distinct audit outcome; **do not** invent a tier. |
| Missing **audit** fields (correlation, source binding, timestamp, product/tier/decision) | **Stop-ship** for pilot readiness (`FS-1_CONTRACTFORGE_PILOT_PLAN.md` §9). |
| **Semgrep** validation/scan failure or new tripwire findings on integrated code | **Stop integration**; do not silence rules to proceed. |
| **`pytest` / CI failure** on ForgeShield or ContractForge train | **Stop integration** until green. |
| **Policy mismatch** (e.g. logs show wrong product accepting `LEGACY_UNSIGNED`, or DocketForge/GrantForge paths touching legacy unsigned) | **Stop integration**; revert per pilot rollback criteria. |

ForgeShield validation commands remain authoritative in
`docs/architecture/FS-1_CI_CHECK_COMMANDS.md` (full `pytest`, semgrep validate,
optional semgrep scan on `src/`).

---

## 9. Minimal ContractForge adapter pseudocode

Illustrative only — **not** production code, **not** copied into this repository
as an adapter. Names mirror ForgeShield public APIs.

```text
# Pseudocode: ContractForge activation + audit + prompt assembly
# ForgeShield names only (no extra third-party imports shown).

from forge_security.artifact_integrity.review_artifacts import (
    Product,
    ReviewArtifactTier,
)
from forge_security.lifecycle.activation_guard import activation_guard
from forge_security.ai_security.prompt_builder import PromptBuilder

function handle_review_request(request, artifact_bytes, classified_tier, correlation_id):
    # 1) Pre-guard: tier must be a real ReviewArtifactTier from classify step
    if classified_tier is INVALID or classified_tier not in (ReviewArtifactTier.LEGACY_UNSIGNED, ReviewArtifactTier.SIGNED_V1):
        emit_audit_pre_guard_reject(correlation_id, reason="invalid_or_missing_tier")
        return DENY

    # 2) Sole activation gate
    decision = activation_guard(product=Product.CONTRACT_IQ, tier=classified_tier)

    audit = {
        "event_type": "forgeshield.activation_guard",
        "occurred_at": now_iso(),
        "correlation_id": correlation_id,
        "product": decision.product.value,
        "tier": decision.tier.value,
        "activated": decision.activated,
        "reason": decision.reason,
        "source": {
            "artifact_id": request.artifact_id,
            "pipeline_stage": "activation_boundary",
            "content_hash": hash_of(artifact_bytes),
        },
        "actor": request.actor_if_available,
        "environment": request.environment,
        "forgeshield_commit": read_forgeshield_version_or_commit(),
    }
    emit_structured_audit(audit)

    if not decision.activated:
        return DENY  # no downstream model calls on this artifact

    # 3) Pilot allow path: build prompts — contract bytes ONLY via add_external_content
    pb = PromptBuilder()
    pb.add_system_instruction(STABLE_REVIEW_POLICY_TEXT)
    pb.add_developer_constraint(DETERMINISTIC_OUTPUT_CONSTRAINTS)
    pb.add_trusted_context(TRUSTED_INTERNAL_METADATA_ONLY_NO_CONTRACT_BODY)
    pb.add_external_content(artifact_bytes_as_str, source=request.artifact_filename_or_uri)
    pb.add_user_task(USER_REVIEW_TASK_WITHOUT_RAW_CONTRACT_BYTES)
    messages = pb.build()
    return CALL_MODEL(messages)
```

---

## 10. ContractForge pilot acceptance checklist

Use before declaring ContractForge integration ready to merge in the
ContractForge repository:

- [ ] **Activation guard** called at **every** activation boundary for Contract IQ review artifacts.
- [ ] **Denied** activation (`activated=False`) **blocks** all downstream use of the artifact as approved.
- [ ] **Audit event** emitted for **every** `activation_guard` call with full field bundle (§4).
- [ ] **Missing or invalid tier** rejected **before** the guard with a non-tier audit outcome.
- [ ] **Contract body** appears only inside the **external untrusted** envelope in built prompts.
- [ ] **No raw contract bytes** in system, developer, or trusted internal layers.
- [ ] **DocketForge / GrantForge** policy **unchanged** (`SIGNED_V1` only); no `LEGACY_UNSIGNED` leakage in their paths.
- [ ] **`python -m pytest -v`** passes on the integrated revision (ForgeShield + ContractForge CI as applicable).
- [ ] **Semgrep** validates and integrated code stays clean per `FS-1_CI_CHECK_COMMANDS.md`.
- [ ] **Human integration review** completed **before** any ContractForge commit that wires activation or prompts.

---

## 11. Out of scope

FS-2.0 explicitly **does not** cover:

- ContractForge repository edits, feature branches, or application implementation.
- UI implementation, UX copy, or customer-facing error strings.
- Database migrations or new tables (beyond integrator responsibility to meet §4).
- Deployment, infrastructure-as-code, or runtime scaling decisions.
- FS-12 signing producers, KMS design, or **`SIGNED_V1` emission** work described
  elsewhere as future milestones.
- NativeForge cleanup, NativeForge policy tightening, or NativeForge pilot flows.
- `ActivationDecision` **production** shape changes or new ForgeShield logging
  side effects (FS-1.7 deferred ergonomics remain out of band unless a later
  ticket explicitly changes the library under full review gates).
- New **`ReviewArtifactTier`** values or CC-14 policy widening.

---

## 12. Handoff decision

**FS-2.0 (ForgeShield) is complete** when this contract document is **reviewed**,
**committed**, **pushed**, and repository **validation remains green** (pytest,
semgrep, and policy pins per FS-1.5 / FS-1.8 baselines or their documented
successor counts).

The **next lane** after FS-2.0 is **ContractForge-side implementation planning**
and engineering in the **ContractForge repository / workstream**, using this
document as the normative integration checklist — without weakening ForgeShield
policy, D6/D7 behavior, or activation semantics in either repo.

---

**References:** `.cursor/rules/forgeshield-artifact-policy.mdc`,
`semgrep/forge_security/no-direct-prompt-fstring.yml`,
`tests/security/test_review_artifacts_policy.py`,
`tests/security/test_prompt_builder.py`.
