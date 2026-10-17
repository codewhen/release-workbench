"""Application control failures; cancellation remains asyncio.CancelledError."""

from release_workbench.domain.values import ContractError


class ExecutionFailure(ContractError):
    """A failed card with its original attempt retained in evidence."""


class EvidenceRequired(ExecutionFailure):
    """An unattended run reached a manual intervention."""
