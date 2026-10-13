import subprocess,unittest
from pathlib import Path
from unittest.mock import patch
from release_workbench.file_picker import choose_workflow
class PickerTests(unittest.TestCase):
 def test_mac_selection_cancel_and_failure(self):
  with patch('release_workbench.file_picker.sys.platform','darwin'),patch('release_workbench.file_picker.subprocess.run') as run:
   run.return_value=subprocess.CompletedProcess([],0,'/tmp/project with spaces/checks.yaml\n','');self.assertEqual(choose_workflow(Path('/tmp')),Path('/tmp/project with spaces/checks.yaml'));self.assertEqual(run.call_args.args[0][-1],'/tmp');self.assertNotIn('shell',run.call_args.kwargs)
   run.return_value=subprocess.CompletedProcess([],0,'','');self.assertIsNone(choose_workflow(Path('/tmp')))
   run.return_value=subprocess.CompletedProcess([],1,'','failure');self.assertRaises(ValueError,choose_workflow,Path('/tmp'))
 def test_timeout_is_actionable(self):
  with patch('release_workbench.file_picker.sys.platform','darwin'),patch('release_workbench.file_picker.subprocess.run',side_effect=subprocess.TimeoutExpired('picker',180)):
   with self.assertRaisesRegex(ValueError,'timed out'):choose_workflow(Path('/tmp'))
 def test_windows_uses_sta_and_environment_for_path(self):
  with patch('release_workbench.file_picker.sys.platform','win32'),patch('release_workbench.file_picker.subprocess.run',return_value=subprocess.CompletedProcess([],0,'C:/x.yaml','')) as run:
   choose_workflow(Path('/tmp'));self.assertIn('-STA',run.call_args.args[0]);self.assertEqual(run.call_args.kwargs['env']['WORKBENCH_PICKER_ROOT'],'/tmp')

 def test_headless_linux_is_actionable(self):
  with patch('release_workbench.file_picker.sys.platform','linux'),patch.dict('release_workbench.file_picker.os.environ',{},clear=True):
   with self.assertRaisesRegex(ValueError,'desktop session'):choose_workflow(Path('/tmp'))
