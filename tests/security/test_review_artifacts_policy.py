import pytest

from forge_security.artifact_integrity.review_artifacts import (
    ArtifactPolicyViolation,
    LEGACY_UNSIGNED,
    POLICIES,
    Product,
    ReviewArtifactTier,
    SIGNED_V1,
    enforce_tier,
    is_tier_accepted,
)
from forge_security.lifecycle.activation_guard import activation_guard


def test_tier_constants_match_spec():
    assert ReviewArtifactTier.LEGACY_UNSIGNED.value == "LEGACY_UNSIGNED"
    assert ReviewArtifactTier.SIGNED_V1.value == "SIGNED_V1"
    assert LEGACY_UNSIGNED is ReviewArtifactTier.LEGACY_UNSIGNED
    assert SIGNED_V1 is ReviewArtifactTier.SIGNED_V1


def test_contract_iq_pilot_accepts_legacy_unsigned():
    assert is_tier_accepted(Product.CONTRACT_IQ, LEGACY_UNSIGNED)
    assert is_tier_accepted(Product.CONTRACT_IQ, SIGNED_V1)


def test_nativeforge_currently_accepts_legacy_unsigned_pending_fs12():
    # FS-12 will tighten this to SIGNED_V1 only. This test pins TODAY'S
    # behavior so the FS-12 PR shows up as a real, visible change.
    assert is_tier_accepted(Product.NATIVEFORGE, LEGACY_UNSIGNED)
    assert is_tier_accepted(Product.NATIVEFORGE, SIGNED_V1)


def test_docketforge_never_accepts_legacy_unsigned():
    assert not is_tier_accepted(Product.DOCKETFORGE, LEGACY_UNSIGNED)
    assert is_tier_accepted(Product.DOCKETFORGE, SIGNED_V1)
    # Defense in depth: the table itself must not list LEGACY_UNSIGNED
    # for DocketForge, so a future edit to the function alone cannot
    # silently weaken the rule.
    assert LEGACY_UNSIGNED not in POLICIES[Product.DOCKETFORGE].accepted_tiers


def test_docketforge_enforce_raises_on_legacy_unsigned():
    with pytest.raises(ArtifactPolicyViolation):
        enforce_tier(Product.DOCKETFORGE, LEGACY_UNSIGNED)


def test_grantforge_signed_v1_only():
    assert is_tier_accepted(Product.GRANTFORGE, SIGNED_V1)
    assert not is_tier_accepted(Product.GRANTFORGE, LEGACY_UNSIGNED)


def test_activation_guard_blocks_docketforge_legacy_unsigned():
    decision = activation_guard(Product.DOCKETFORGE, LEGACY_UNSIGNED)
    assert decision.activated is False
    assert "LEGACY_UNSIGNED" in decision.reason
    assert decision.product is Product.DOCKETFORGE


def test_activation_guard_allows_docketforge_signed_v1():
    decision = activation_guard(Product.DOCKETFORGE, SIGNED_V1)
    assert decision.activated is True
    assert "SIGNED_V1" in decision.reason


def test_activation_guard_allows_contract_iq_legacy_unsigned():
    decision = activation_guard(Product.CONTRACT_IQ, LEGACY_UNSIGNED)
    assert decision.activated is True


def test_activation_guard_never_raises():
    # Even for a (product, tier) combo that should be rejected, the
    # guard returns a decision instead of raising.
    decision = activation_guard(Product.DOCKETFORGE, LEGACY_UNSIGNED)
    assert isinstance(decision.reason, str) and decision.reason
