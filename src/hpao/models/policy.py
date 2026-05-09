from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hpao.db import Base, TimestampMixin

if TYPE_CHECKING:
    pass


POLICY_SCOPES: tuple[str, ...] = ("tea", "district", "school")
"""Hierarchical authority levels for the rules a policy carries.

`tea` = Texas Education Agency (statewide); `district` = e.g. PfISD;
`school` = single-school overrides. The agent is single-school for the
hackathon but the schema is multi-tenant from day one.
"""

POLICY_RULE_SEVERITIES: tuple[str, ...] = ("low", "medium", "high", "critical")

EMBEDDING_DIM = 1536
"""text-embedding-3-small dimension. Phase 5b/5c will populate the column."""

_SCOPES_LIST = ", ".join(f"'{s}'" for s in POLICY_SCOPES)
_SEVERITIES_LIST = ", ".join(f"'{s}'" for s in POLICY_RULE_SEVERITIES)


class Policy(Base, TimestampMixin):
    __tablename__ = "policies"
    __table_args__ = (CheckConstraint(f"scope IN ({_SCOPES_LIST})", name="scope_valid"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    chunks: Mapped[list[PolicyChunk]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )
    rules: Mapped[list[PolicyRule]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Policy {self.scope}:{self.name!r}>"


class PolicyChunk(Base, TimestampMixin):
    """Embedded text fragment of a policy doc — the RAG corpus."""

    __tablename__ = "policy_chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    policy_id: Mapped[UUID] = mapped_column(ForeignKey("policies.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    policy: Mapped[Policy] = relationship(back_populates="chunks")

    def __repr__(self) -> str:
        head = self.text[:40].replace("\n", " ")
        return f"<PolicyChunk policy={self.policy_id} {head!r}>"


class PolicyRule(Base, TimestampMixin):
    """Deterministic rule extracted from a policy.

    `rule_key` is the global, dotted identifier other tables (alerts,
    agent_messages) reference as a string. `expression` is the engine-
    interpreted body — kept as JSONB so Phase 5b's evaluator can be
    extended without schema churn.
    """

    __tablename__ = "policy_rules"
    __table_args__ = (
        UniqueConstraint("rule_key", name="uq_policy_rules_rule_key"),
        CheckConstraint(f"severity IN ({_SEVERITIES_LIST})", name="severity_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    policy_id: Mapped[UUID] = mapped_column(ForeignKey("policies.id"), nullable=False)
    rule_key: Mapped[str] = mapped_column(String(120), nullable=False)
    expression: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    threshold: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)

    policy: Mapped[Policy] = relationship(back_populates="rules")

    def __repr__(self) -> str:
        return f"<PolicyRule {self.rule_key} ({self.severity})>"
