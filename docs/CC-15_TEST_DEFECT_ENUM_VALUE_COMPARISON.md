# CC-15 — Test defect: enum value comparison after Pydantic `use_enum_values=True`

> **Status:** correction-class record. Test-defect tier. Carried forward from
> FS-0.5 scratch validation; reproducible **only** in test code that wraps
> `ActivationDecision` in a Pydantic model configured with
> `use_enum_values=True`.
>
> **Severity:** TEST_DEFECT (not SPEC_DEFECT, not IMPLEMENTATION_COPY_ERROR,
> not DEPENDENCY_OR_ENVIRONMENT_ERROR).
>
> **Affects:** any test or audit-roundtrip stub that adopts the pattern in
> §2 below. Does **not** affect production `ActivationDecision` semantics or
> the CC-14 review-artifact policy.

---

## 1. Symptom

In an FS-0.5 scratch test that defined a JSON-roundtrip stub for
`ActivationDecision` using Pydantic:

```python
from pydantic import BaseModel, ConfigDict

class ActivationDecisionModel(BaseModel):
    product: Product
    tier: ReviewArtifactTier
    activated: bool
    reason: str

    model_config = ConfigDict(use_enum_values=True)

roundtrip = ActivationDecisionModel.model_validate(payload)
assert roundtrip.product is Product.CONTRACT_IQ   # ← fails
assert roundtrip.tier    is ReviewArtifactTier.SIGNED_V1   # ← fails
```

the `is`-based comparisons fail even when the JSON payload is well-formed
and the policy allows the pairing.

## 2. Root cause

`ConfigDict(use_enum_values=True)` instructs Pydantic to **store the
`Enum.value`** on the validated model rather than the `Enum` member itself.
Because `Product` and `ReviewArtifactTier` are both `str`-subclassing enums:

```python
class ReviewArtifactTier(str, Enum):
    LEGACY_UNSIGNED = "LEGACY_UNSIGNED"
    SIGNED_V1 = "SIGNED_V1"

class Product(str, Enum):
    CONTRACT_IQ = "contract-iq"
    ...
```

the post-validation field is the **plain `str` value** (e.g. `"SIGNED_V1"`),
which is `==` the enum member (because `str`-enum members hash and equal
their string value) but is **not the same Python object** as the enum
member. `is` therefore returns `False`.

## 3. Correction

Tests that validate roundtrip payloads against `Product` / `ReviewArtifactTier`
**must use `==`, not `is`**, when `use_enum_values=True` is in effect:

```python
assert roundtrip.product == Product.CONTRACT_IQ        # correct
assert roundtrip.tier    == ReviewArtifactTier.SIGNED_V1  # correct
```

Equivalently, tests may compare directly against the wire value
(`"contract-iq"`, `"SIGNED_V1"`), which is what `use_enum_values=True` is
designed to emit.

`is` comparisons are still valid in **production** code paths that have
**not** routed an enum through a `use_enum_values=True` Pydantic model —
for example, `is_tier_accepted` and `activation_guard` keep their identity
checks on real enum members (e.g.
`product is Product.DOCKETFORGE and tier is LEGACY_UNSIGNED`). Those paths
operate on enum members supplied directly by callers and never round-trip
through Pydantic.

## 4. Why this is filed against the test, not the policy

- `Product`, `ReviewArtifactTier`, `POLICIES`, and `is_tier_accepted` in
  `src/forge_security/artifact_integrity/review_artifacts.py` are
  unchanged.
- `ActivationDecision` (the production dataclass in
  `src/forge_security/lifecycle/activation_guard.py`) stores **real enum
  members** and is unaffected.
- The defect is entirely in test code that introduces a Pydantic
  reflection of the dataclass for audit-roundtrip purposes and then forgets
  that `use_enum_values=True` collapses members to their values.

Per the FS ForgeShield artifact policy rule
(`.cursor/rules/forgeshield-artifact-policy.mdc`), CC-15 is **not** a
widening of `POLICIES` and **not** a new tier; it is a comparison-operator
fix in test fixtures.

## 5. Scope in the canonical standalone repo

The canonical standalone `forgeshield` repository **does not currently
ship a Pydantic-based roundtrip test**. CC-15 is recorded here so that:

1. The FS-0.5 scratch validation history is reproducible and auditable.
2. If a future ForgeShield change introduces a JSON audit roundtrip
   (e.g. as part of FS-1.7 audit-ergonomics extension or any DocketForge /
   GrantForge consumer that serialises `ActivationDecision`), the author
   does not re-discover this trap.
3. Any consumer reading `ActivationDecision` over JSON treats the enum
   fields as string-equal-to-value, not identity-equal-to-member.

## 6. Classification matrix

| Class | Applies? | Why |
|---|---|---|
| SPEC_DEFECT | No | The CC-14 two-tier spec and the activation-guard contract are unchanged. |
| IMPLEMENTATION_COPY_ERROR | No | Production modules (`review_artifacts.py`, `activation_guard.py`) are correct. |
| **TEST_DEFECT** | **Yes** | Test code used `is` where `==` was required after Pydantic enum-value reflection. |
| DEPENDENCY_OR_ENVIRONMENT_ERROR | No | Pydantic, pytest, and hypothesis versions were correctly installed; the defect is logical, not environmental. |
