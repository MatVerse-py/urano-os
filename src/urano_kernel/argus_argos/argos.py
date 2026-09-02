"""ARGOS: governed adjudication over ARGUS evidence observations."""

from dataclasses import dataclass, field
from typing import Mapping, Tuple

from .models import Adjudication, AdjudicationState, EvidenceObservation


@dataclass(frozen=True)
class ArgosPolicy:
    """Fail-closed adjudication policy.

    required_authority maps predicate domains to minimum policy weights.
    Missing or sub-threshold authority keeps the observation in HOLD.
    """

    policy_id: str = "argus-argos.default.v0"
    required_authority: Mapping[str, int] = field(default_factory=dict)
    block_on_conflict: bool = False


class Argos:
    """Decide what may be done with a qualified observation.

    ARGOS does not reinterpret the source. It adjudicates the observation
    produced by ARGUS under an explicit policy.
    """

    def adjudicate(self, observation: EvidenceObservation, policy: ArgosPolicy | None = None) -> Adjudication:
        policy = policy or ArgosPolicy()
        authority = observation.authority.as_dict()
        reasons = []

        if not observation.observation_id or not observation.source_ref or not observation.representation:
            return Adjudication(
                observation_id=observation.observation_id,
                state=AdjudicationState.BLOCK,
                reasons=("MALFORMED_OBSERVATION",),
                policy_id=policy.policy_id,
            )

        if observation.conflicts:
            reasons.append("UNRESOLVED_CONFLICT")
            if policy.block_on_conflict:
                return Adjudication(
                    observation_id=observation.observation_id,
                    state=AdjudicationState.BLOCK,
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
            return Adjudication(
                observation_id=observation.observation_id,
                state=AdjudicationState.HOLD,
                reasons=tuple(reasons),
                policy_id=policy.policy_id,
            )

        return Adjudication(
            observation_id=observation.observation_id,
            state=AdjudicationState.PASS,
            reasons=("POLICY_SATISFIED",),
            policy_id=policy.policy_id,
        )
