import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from release_workbench.infrastructure.folder_picker import FolderPicker


class FolderPickerTests(unittest.TestCase):
    def test_selected_folder_and_cancel(self):
        picker = FolderPicker()
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(picker, "_command", return_value=["picker"]),
                patch("release_workbench.infrastructure.folder_picker.subprocess.run") as run,
            ):
                run.return_value = subprocess.CompletedProcess([], 0, directory + "\n", "")
                self.assertEqual(picker.choose(), str(Path(directory).resolve()))
                run.return_value = subprocess.CompletedProcess([], 0, "", "")
                self.assertIsNone(picker.choose())

    def test_timeout_releases_dialog_lock(self):
        picker = FolderPicker()
        with (
            patch.object(picker, "_command", return_value=["picker"]),
            patch(
                "release_workbench.infrastructure.folder_picker.subprocess.run",
                side_effect=subprocess.TimeoutExpired([], 180),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "Enter the folder path"):
                picker.choose()
        self.assertTrue(picker._lock.acquire(blocking=False))
        picker._lock.release()

    def test_concurrent_dialog_rejected(self):
        picker = FolderPicker()
        picker._lock.acquire()
        try:
            with self.assertRaisesRegex(ValueError, "already open"):
                picker.choose()
        finally:
            picker._lock.release()

    def test_platform_commands_and_linux_cancellation(self):
        picker = FolderPicker()
        with patch("release_workbench.infrastructure.folder_picker.sys.platform", "darwin"):
            self.assertEqual(picker._command()[0], "/usr/bin/osascript")
        with patch("release_workbench.infrastructure.folder_picker.sys.platform", "win32"):
            self.assertIn("-STA", picker._command())
            with patch("release_workbench.infrastructure.folder_picker.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess([], 1, "", "failure")
                with self.assertRaisesRegex(ValueError, "could not open"):
                    picker.choose()
        with (
            patch("release_workbench.infrastructure.folder_picker.sys.platform", "linux"),
            patch(
                "release_workbench.infrastructure.folder_picker.shutil.which",
                return_value="/bin/zenity",
            ),
            patch("release_workbench.infrastructure.folder_picker.subprocess.run") as run,
        ):
            run.return_value = subprocess.CompletedProcess([], 1, "", "")
            self.assertIsNone(picker.choose())
