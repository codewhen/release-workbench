"""Explicit catalog of one specification class per card module."""

from ..values import ContractError
from .base import CardSpec as CardSpec
from .base import OperationSpec as OperationSpec
from .base import TerminalSpec as TerminalSpec
from .bash import BashSpec as BashSpec
from .break_card import BreakSpec as BreakSpec
from .calculate import CalculateSpec as CalculateSpec
from .call import CallSpec as CallSpec
from .check_path import CheckPathSpec as CheckPathSpec
from .continue_card import ContinueSpec as ContinueSpec
from .finish import FinishSpec as FinishSpec
from .http import HttpSpec as HttpSpec
from .if_card import IfSpec as IfSpec
from .join import JoinSpec as JoinSpec
from .loop import LoopSpec as LoopSpec
from .manual import ManualSpec as ManualSpec
from .parallel import ParallelSpec as ParallelSpec
from .poll import PollSpec as PollSpec
from .program import ProgramSpec as ProgramSpec
from .python import PythonSpec as PythonSpec
from .read_file import ReadFileSpec as ReadFileSpec
from .return_card import ReturnSpec as ReturnSpec
from .script import ScriptSpec as ScriptSpec
from .start import StartSpec as StartSpec
from .try_card import TrySpec as TrySpec
from .variable import VariableSpec as VariableSpec
from .wait import WaitSpec as WaitSpec
from .workspace import WorkspaceSpec as WorkspaceSpec
from .write_file import WriteFileSpec as WriteFileSpec

SPEC_TYPES = (
    StartSpec,
    FinishSpec,
    ReturnSpec,
    IfSpec,
    LoopSpec,
    VariableSpec,
    CalculateSpec,
    BreakSpec,
    ContinueSpec,
    ParallelSpec,
    JoinSpec,
    TrySpec,
    PythonSpec,
    BashSpec,
    ScriptSpec,
    ProgramSpec,
    CheckPathSpec,
    ReadFileSpec,
    WriteFileSpec,
    HttpSpec,
    WaitSpec,
    PollSpec,
    ManualSpec,
    CallSpec,
    WorkspaceSpec,
)
REGISTRY: dict[str, CardSpec] = {spec.kind: spec() for spec in SPEC_TYPES}


def get_spec(kind: str) -> CardSpec:
    try:
        return REGISTRY[kind]
    except KeyError as error:
        raise ContractError(f"Unknown card type: {kind}") from error
