"""ARGOS: operational evidence-governance kernel."""

from dataclasses import dataclass, field
from typing import Mapping

from .models import GovernanceDecision, GovernanceEnvelope, GovernanceState


@dataclass(frozen=True)
class ArgosPolicy:
    """Fail-closed governance policy.

    required_authority maps predicate domains to minimum policy weights.
    Missing or sub-threshold authority keeps a record in HOLD. ARGOS accepts
    records from ARGUS and from other MatVerse laboratories/tools.
    """

    policy_id: str = "argos.governance.default.v0"
    required_authority: Mapping[str, int] = field(default_factory=dict)
    block_on_conflict: bool = False
    allowed_producers: tuple[str, ...] = ()


class Argos:
    """Govern evidence under explicit policy.

    This class is only the v0 governance kernel of the broader ARGOS system.
    The canonical ARGOS scope also includes admissibility, policy, receipts,
    ledger, replay, review/contest/revocation and external witness integration;
    those capabilities remain downstream or follow-up components.
    """

    def adjudicate(
        self,
        envelope: GovernanceEnvelope,
        policy: ArgosPolicy | None = None,
    ) -> GovernanceDecision:
        policy = policy or ArgosPolicy()
        authority = envelope.authority.as_dict()
        reasons: list[str] = []

        if not envelope.record_id or not envelope.producer.strip() or not envelope.subject_ref.strip():
            return GovernanceDecision(
                record_id=envelope.record_id,
                state=GovernanceState.BLOCK,
                reasons=("MALFORMED_GOVERNANCE_ENVELOPE",),
                policy_id=policy.policy_id,
            )

        if policy.allowed_producers and envelope.producer not in policy.allowed_producers:
            reasons.append(f"PRODUCER_NOT_ALLOWED:{envelope.producer}")

        if envelope.conflicts:
            reasons.append("UNRESOLVED_CONFLICT")
            if policy.block_on_conflict:
                return GovernanceDecision(
                    record_id=envelope.record_id,
                    state=GovernanceState.BLOCK,
                    reasons=tuple(reasons),
                    policy_id=policy.policy_id,
                )

        for domain, minimum in policy.required_authority.items():
            if domain not in authority:
                reasons.append(f"UNKNOWN_AUTHORITY_DOMAIN:{domain}")
                continue
            if minimum < 0 or minimum > 100:
                reasons.append(f"INVALID_THRESHOLD:{domain}")
                continue
            if authority[domain] < minimum:
                reasons.append(f"AUTHORITY_BELOW_THRESHOLD:{domain}")

        if reasons:
            return GovernanceDecision(
                record_id=envelope.record_id,
                state=GovernanceState.HOLD,
                reasons=tuple(reasons),
                policy_id=policy.policy_id,
            )

        return GovernanceDecision(
            record_id=envelope.record_id,
            state=GovernanceState.PASS,
            reasons=("POLICY_SATISFIED",),
            policy_id=policy.policy_id,
        )
