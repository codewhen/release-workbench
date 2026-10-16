"""Native directory selection on the local Workbench host."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path


class FolderPicker:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def choose(self) -> str | None:
        if not self._lock.acquire(blocking=False):
            raise ValueError("A folder picker is already open. Choose a folder or cancel it.")
        try:
            command = self._command()
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, encoding="utf-8", timeout=180
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ValueError(
                    "The folder picker could not finish. Enter the folder path instead."
                ) from error
            if result.returncode == 1 and sys.platform not in ("darwin", "win32"):
                return None
            if result.returncode != 0:
                raise ValueError("The folder picker could not open. Enter the folder path instead.")
            selected = result.stdout.rstrip("\r\n")
            if not selected:
                return None
            path = Path(selected)
            if not path.is_absolute() or not path.is_dir():
                raise ValueError("The selected folder is no longer available.")
            return str(path.resolve())
        finally:
            self._lock.release()

    @staticmethod
    def _command() -> list[str]:
        if sys.platform == "darwin":
            return [
                "/usr/bin/osascript",
                "-e",
                "activate\ntry\n"
                'return POSIX path of (choose folder with prompt "Choose a Workbench project folder")\n'
                'on error number -128\nreturn ""\nend try',
            ]
        if sys.platform == "win32":
            return [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-Command",
                "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$picker = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$picker.Description = 'Choose a Workbench project folder'; "
                "try { if ($picker.ShowDialog() -eq 'OK') { "
                "[Console]::WriteLine($picker.SelectedPath) } } finally { $picker.Dispose() }",
            ]
        if shutil.which("zenity"):
            return ["zenity", "--file-selection", "--directory", "--title=Choose a project folder"]
        if shutil.which("kdialog"):
            return ["kdialog", "--getexistingdirectory", str(Path.home())]
        raise ValueError("No native folder picker is available. Enter the folder path instead.")
