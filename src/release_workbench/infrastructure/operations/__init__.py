"""Explicit external-effect adapter registry; no workflow scheduling here."""

from .base import OperationHandler as OperationHandler
from .base import workspace_path as workspace_path
from .bash import BashHandler as BashHandler
from .check_path import CheckPathHandler as CheckPathHandler
from .http import HttpHandler as HttpHandler
from .program import ProgramHandler as ProgramHandler
from .python import PythonHandler as PythonHandler
from .read_file import ReadFileHandler as ReadFileHandler
from .script import ScriptHandler as ScriptHandler
from .write_file import WriteFileHandler as WriteFileHandler

HANDLER_TYPES = (
    PythonHandler,
    ProgramHandler,
    BashHandler,
    ScriptHandler,
    HttpHandler,
    CheckPathHandler,
    ReadFileHandler,
    WriteFileHandler,
)
HANDLERS: dict[str, OperationHandler] = {handler.kind: handler() for handler in HANDLER_TYPES}
