from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import Policy, PolicyRule
from hpao.policy.rules import DEFAULT_RULES, RuleSpec


async def seed_default_rules(session: AsyncSession) -> dict[str, PolicyRule]:
    """Idempotently materialize the default rule set into the database.

    Existing rules (matched by `rule_key`) are left untouched so manual
    edits via SQL/admin tooling survive a re-seed. Returns a map keyed by
    `rule_key` so callers can chain rule references after seeding.
    """
    result: dict[str, PolicyRule] = {}
    policy_cache: dict[tuple[str, str], Policy] = {}

    for spec in DEFAULT_RULES:
        existing = (
            await session.execute(select(PolicyRule).where(PolicyRule.rule_key == spec.rule_key))
        ).scalar_one_or_none()
        if existing is not None:
            result[spec.rule_key] = existing
            continue

        policy = await _get_or_create_policy(session, spec, policy_cache)
        rule = PolicyRule(
            policy_id=policy.id,
            rule_key=spec.rule_key,
            expression=spec.expression,
            threshold=spec.threshold,
            severity=spec.severity,
        )
        session.add(rule)
        await session.flush()
        result[spec.rule_key] = rule

    return result


async def _get_or_create_policy(
    session: AsyncSession,
    spec: RuleSpec,
    cache: dict[tuple[str, str], Policy],
) -> Policy:
    cache_key = (spec.scope, spec.policy_name)
    if cache_key in cache:
        return cache[cache_key]

    policy = (
        await session.execute(
            select(Policy).where(Policy.scope == spec.scope, Policy.name == spec.policy_name)
        )
    ).scalar_one_or_none()
    if policy is None:
        policy = Policy(scope=spec.scope, name=spec.policy_name)
        session.add(policy)
        await session.flush()
    cache[cache_key] = policy
    return policy
