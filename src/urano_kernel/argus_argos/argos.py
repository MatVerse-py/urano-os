"""ARGOS: operational evidence-governance kernel."""

from dataclasses import dataclass, field
from typing import Mapping

from .models import GovernanceDecision, GovernanceEnvelope, GovernanceState


@dataclass(frozen=True)
class ArgosPolicy:
    """Fail-closed governance policy.

    `required_authority` maps predicate domains to minimum policy weights.
    Missing or sub-threshold authority keeps a record in HOLD. Epistemic state
    is evaluated separately from numeric authority so an unresolved finding
    cannot become admissible merely by carrying high weights.

    By default ARGOS also requires an explicit authority policy. A caller that
    intentionally wants epistemic-state-only governance must opt out with
    `require_authority_policy=False`; an empty map must never silently mean
    "no evidence threshold required".
    """

    policy_id: str = "argos.governance.default.v0"
    required_authority: Mapping[str, int] = field(default_factory=dict)
    require_authority_policy: bool = True
    block_on_conflict: bool = False
    allowed_producers: tuple[str, ...] = ()
    pass_epistemic_states: tuple[str, ...] = ("SUPPORTED", "VERIFIED", "ADMISSIBLE")
    hold_epistemic_states: tuple[str, ...] = (
        "UNVERIFIED",
        "INSUFFICIENT_EVIDENCE",
        "CONTRADICTORY",
        "OUT_OF_CONTEXT",
        "INTEGRITY_CONFLICT",
        "MANIPULATION_SUSPECTED",
        "FABRICATION_SUSPECTED",
        "COORDINATION_SUSPECTED",
    )
    block_epistemic_states: tuple[str, ...] = ()
    hold_unknown_epistemic_state: bool = True
    require_epistemic_state: bool = True


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

        epistemic_state = envelope.epistemic_state.strip().upper()
        pass_states = {state.strip().upper() for state in policy.pass_epistemic_states}
        block_states = {state.strip().upper() for state in policy.block_epistemic_states}
        hold_states = {state.strip().upper() for state in policy.hold_epistemic_states}

        if not epistemic_state and policy.require_epistemic_state:
            reasons.append("MISSING_EPISTEMIC_STATE")
        elif epistemic_state in block_states:
            return GovernanceDecision(
                record_id=envelope.record_id,
                state=GovernanceState.BLOCK,
                reasons=(f"EPISTEMIC_STATE_BLOCK:{epistemic_state}",),
                policy_id=policy.policy_id,
            )
        elif epistemic_state in hold_states:
            reasons.append(f"EPISTEMIC_STATE_HOLD:{epistemic_state}")
        elif epistemic_state and epistemic_state not in pass_states and policy.hold_unknown_epistemic_state:
            reasons.append(f"UNKNOWN_EPISTEMIC_STATE:{epistemic_state}")

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

        if policy.require_authority_policy and not policy.required_authority:
            reasons.append("MISSING_AUTHORITY_POLICY")

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
