"""Lifecycle activation guard.

The activation guard is the single function the rest of ForgeShield
calls right before allowing a product subsystem to "activate" -- i.e.
to start consuming review artifacts and acting on them. The guard
defers all tier-acceptance logic to
:mod:`forge_security.artifact_integrity.review_artifacts`, so FS-12
(NativeForge tightening) and any future product additions are pure
data-table edits.

The guard never raises; activation failure is encoded in the returned
:class:`ActivationDecision` so callers can log/audit the rejection
instead of crashing the calling subsystem. Use ``enforce_tier`` from
the policy module directly if you want hard-fail semantics.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..artifact_integrity.review_artifacts import (
    ArtifactPolicyViolation,
    Product,
    ReviewArtifactTier,
    enforce_tier,
)


@dataclass(frozen=True)
class ActivationDecision:
    product: Product
    tier: ReviewArtifactTier
    activated: bool
    reason: str


def activation_guard(
    product: Product, tier: ReviewArtifactTier
) -> ActivationDecision:
    try:
        enforce_tier(product, tier)
    except ArtifactPolicyViolation as exc:
        return ActivationDecision(
            product=product,
            tier=tier,
            activated=False,
            reason=str(exc),
        )
    return ActivationDecision(
        product=product,
        tier=tier,
        activated=True,
        reason=f"{product.value} accepts {tier.value}",
    )


__all__ = ["ActivationDecision", "activation_guard"]
