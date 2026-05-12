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
from forge_security.lifecycle.activation_guard import (
    ActivationDecision,
    activation_guard,
)


def _assert_rejected_activation_reason_quality(
    decision: ActivationDecision,
    *,
    expected_product: Product,
    expected_tier: ReviewArtifactTier,
) -> None:
    """FS-1.3: rejected decisions must be auditable (tier and product in reason)."""
    assert decision.product is expected_product
    assert decision.tier is expected_tier
    assert decision.activated is False
    reason = decision.reason
    assert isinstance(reason, str)
    assert reason.strip() != ""
    assert expected_tier.value in reason
    assert expected_product.value in reason


def test_tier_constants_match_spec():
    assert ReviewArtifactTier.LEGACY_UNSIGNED.value == "LEGACY_UNSIGNED"
    assert ReviewArtifactTier.SIGNED_V1.value == "SIGNED_V1"
    assert LEGACY_UNSIGNED is ReviewArtifactTier.LEGACY_UNSIGNED
    assert SIGNED_V1 is ReviewArtifactTier.SIGNED_V1


def test_contract_iq_pilot_accepts_legacy_unsigned():
    assert is_tier_accepted(Product.CONTRACT_IQ, LEGACY_UNSIGNED)
    assert is_tier_accepted(Product.CONTRACT_IQ, SIGNED_V1)


def test_nativeforge_currently_accepts_legacy_unsigned_pending_fs12():
    """FS-12 precursor only — not an FS-1 ContractForge dependency.

    NativeForge may still list LEGACY_UNSIGNED until FS-12; FS-1 design and
    activation_guard matrix tests intentionally do not rely on this path.
    """
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


@pytest.mark.parametrize(
    ("product", "tier", "expect_activated"),
    [
        pytest.param(
            Product.CONTRACT_IQ,
            LEGACY_UNSIGNED,
            True,
            id="contract_iq_legacy_unsigned_allows",
        ),
        pytest.param(
            Product.CONTRACT_IQ,
            SIGNED_V1,
            True,
            id="contract_iq_signed_v1_allows",
        ),
        pytest.param(
            Product.DOCKETFORGE,
            LEGACY_UNSIGNED,
            False,
            id="docketforge_legacy_unsigned_denies",
        ),
        pytest.param(
            Product.DOCKETFORGE,
            SIGNED_V1,
            True,
            id="docketforge_signed_v1_allows",
        ),
        pytest.param(
            Product.GRANTFORGE,
            LEGACY_UNSIGNED,
            False,
            id="grantforge_legacy_unsigned_denies",
        ),
        pytest.param(
            Product.GRANTFORGE,
            SIGNED_V1,
            True,
            id="grantforge_signed_v1_allows",
        ),
    ],
)
def test_activation_guard_fs1_product_tier_matrix(
    product: Product, tier: ReviewArtifactTier, expect_activated: bool
) -> None:
    """Product × tier matrix for FS-1 activation_guard (Contract IQ, DocketForge, GrantForge)."""
    decision = activation_guard(product, tier)
    assert decision.product is product
    assert decision.tier is tier
    assert decision.activated is expect_activated
    assert isinstance(decision.reason, str)
    assert decision.reason.strip() != ""
    if not expect_activated:
        _assert_rejected_activation_reason_quality(
            decision,
            expected_product=product,
            expected_tier=tier,
        )


def test_activation_guard_never_raises_for_fs1_matrix_pairs() -> None:
    """activation_guard must not raise for the FS-1 matrix (six product × tier pairs)."""
    pairs = [
        (Product.CONTRACT_IQ, LEGACY_UNSIGNED),
        (Product.CONTRACT_IQ, SIGNED_V1),
        (Product.DOCKETFORGE, LEGACY_UNSIGNED),
        (Product.DOCKETFORGE, SIGNED_V1),
        (Product.GRANTFORGE, LEGACY_UNSIGNED),
        (Product.GRANTFORGE, SIGNED_V1),
    ]
    for product, tier in pairs:
        decision = activation_guard(product, tier)
        assert isinstance(decision, ActivationDecision)
        assert decision.product is product
        assert decision.tier is tier
        assert isinstance(decision.reason, str) and decision.reason.strip() != ""
