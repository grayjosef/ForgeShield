"""CC-14 review artifact policy.

Two artifact integrity tiers are defined for ForgeShield:

* ``LEGACY_UNSIGNED`` -- review artifacts produced by the pre-FS
  contract pipeline. They have no detached signature and no signed
  manifest. Accepted ONLY during the ContractForge pilot, ONLY at the
  positions explicitly listed in :data:`POLICIES`. Forbidden everywhere
  in DocketForge from day one, with no exceptions.

* ``SIGNED_V1`` -- review artifacts produced after FS-12. They carry a
  detached signature over a manifest that pins the artifact bytes by
  hash. Accepted everywhere.

NativeForge FS-12 must upgrade the activation guard so NativeForge
no longer accepts ``LEGACY_UNSIGNED``. DocketForge requires
``SIGNED_V1`` at every artifact position from day one and there is no
exception to that rule. This is enforced both via the policy table
below AND via a defensive check in :func:`is_tier_accepted` so a future
edit to the table cannot accidentally weaken DocketForge.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet


class ReviewArtifactTier(str, Enum):
    LEGACY_UNSIGNED = "LEGACY_UNSIGNED"
    SIGNED_V1 = "SIGNED_V1"


LEGACY_UNSIGNED = ReviewArtifactTier.LEGACY_UNSIGNED
SIGNED_V1 = ReviewArtifactTier.SIGNED_V1


class Product(str, Enum):
    CONTRACT_IQ = "contract-iq"
    NATIVEFORGE = "nativeforge"
    DOCKETFORGE = "docketforge"
    GRANTFORGE = "grantforge"


@dataclass(frozen=True)
class ArtifactPolicy:
    """Per-product policy for accepted review artifact tiers."""

    product: Product
    accepted_tiers: FrozenSet[ReviewArtifactTier]
    note: str


POLICIES: Dict[Product, ArtifactPolicy] = {
    Product.CONTRACT_IQ: ArtifactPolicy(
        product=Product.CONTRACT_IQ,
        accepted_tiers=frozenset({LEGACY_UNSIGNED, SIGNED_V1}),
        note="ContractForge pilot may accept LEGACY_UNSIGNED until FS-1 lands.",
    ),
    Product.NATIVEFORGE: ArtifactPolicy(
        product=Product.NATIVEFORGE,
        accepted_tiers=frozenset({LEGACY_UNSIGNED, SIGNED_V1}),
        note="NativeForge accepts LEGACY_UNSIGNED only until FS-12 upgrades the activation guard.",
    ),
    Product.DOCKETFORGE: ArtifactPolicy(
        product=Product.DOCKETFORGE,
        accepted_tiers=frozenset({SIGNED_V1}),
        note="DocketForge requires SIGNED_V1 at every artifact position from day one. No exceptions.",
    ),
    Product.GRANTFORGE: ArtifactPolicy(
        product=Product.GRANTFORGE,
        accepted_tiers=frozenset({SIGNED_V1}),
        note="GrantForge has not started; default to SIGNED_V1 only.",
    ),
}


class ArtifactPolicyViolation(ValueError):
    """Raised when a tier is presented to a product that forbids it."""


def is_tier_accepted(product: Product, tier: ReviewArtifactTier) -> bool:
    """Return True iff ``tier`` is accepted for ``product``.

    DocketForge always returns False for LEGACY_UNSIGNED regardless of
    what the policy table says; this is a deliberate belt-and-braces
    check that survives accidental edits to :data:`POLICIES`.
    """
    if product is Product.DOCKETFORGE and tier is LEGACY_UNSIGNED:
        return False
    policy = POLICIES.get(product)
    if policy is None:
        return False
    return tier in policy.accepted_tiers


def enforce_tier(product: Product, tier: ReviewArtifactTier) -> None:
    """Raise :class:`ArtifactPolicyViolation` if ``tier`` is not accepted."""
    if not is_tier_accepted(product, tier):
        raise ArtifactPolicyViolation(
            f"{product.value} does not accept {tier.value} review artifacts"
        )


__all__ = [
    "ReviewArtifactTier",
    "LEGACY_UNSIGNED",
    "SIGNED_V1",
    "Product",
    "ArtifactPolicy",
    "POLICIES",
    "ArtifactPolicyViolation",
    "is_tier_accepted",
    "enforce_tier",
]
