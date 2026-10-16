"""Polymorphic card execution registry; each card has one concrete executor."""

from release_workbench.domain.calculations import calculate as calculate

from ..errors import EvidenceRequired as EvidenceRequired
from ..errors import ExecutionFailure as ExecutionFailure
from ..ports import CardExecutor as CardExecutor
from .bash import BashExecutor as BashExecutor
from .break_card import BreakExecutor as BreakExecutor
from .calculate_card import CalculateExecutor as CalculateExecutor
from .call import CallExecutor as CallExecutor
from .check_path import CheckPathExecutor as CheckPathExecutor
from .continue_card import ContinueExecutor as ContinueExecutor
from .finish import FinishExecutor as FinishExecutor
from .http import HttpExecutor as HttpExecutor
from .if_card import IfExecutor as IfExecutor
from .join import JoinExecutor as JoinExecutor
from .loop import LoopExecutor as LoopExecutor
from .manual import ManualExecutor as ManualExecutor
from .parallel import ParallelExecutor as ParallelExecutor
from .poll import PollExecutor as PollExecutor
from .program import ProgramExecutor as ProgramExecutor
from .python import PythonExecutor as PythonExecutor
from .read_file import ReadFileExecutor as ReadFileExecutor
from .return_card import ReturnExecutor as ReturnExecutor
from .script import ScriptExecutor as ScriptExecutor
from .start import StartExecutor as StartExecutor
from .try_card import TryExecutor as TryExecutor
from .variable import VariableExecutor as VariableExecutor
from .wait import WaitExecutor as WaitExecutor
from .workspace import WorkspaceExecutor as WorkspaceExecutor
from .write_file import WriteFileExecutor as WriteFileExecutor

EXECUTOR_TYPES = (
    StartExecutor,
    FinishExecutor,
    ReturnExecutor,
    IfExecutor,
    LoopExecutor,
    VariableExecutor,
    CalculateExecutor,
    BreakExecutor,
    ContinueExecutor,
    ParallelExecutor,
    JoinExecutor,
    TryExecutor,
    PythonExecutor,
    BashExecutor,
    ScriptExecutor,
    ProgramExecutor,
    CheckPathExecutor,
    ReadFileExecutor,
    WriteFileExecutor,
    HttpExecutor,
    WaitExecutor,
    PollExecutor,
    ManualExecutor,
    CallExecutor,
    WorkspaceExecutor,
)
EXECUTORS: dict[str, CardExecutor] = {executor.kind: executor() for executor in EXECUTOR_TYPES}
