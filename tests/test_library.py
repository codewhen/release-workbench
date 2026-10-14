"""Multi-project selection, registration, history and execution ownership."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from release_workbench.library import Library
from release_workbench.config import render_yaml
from test_engine import workflow,command

class LibraryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.a=self.root/'project-a';self.b=self.root/'project-b';self.a.mkdir();self.b.mkdir();self.file=self.a/'release-workbench.yaml';self.file.write_text(render_yaml(dict(version=1,name='First',steps=[command('a')])));self.lib=Library(self.file)
 def tearDown(self):self.lib.shutdown();self.temp.cleanup()
 def test_discovery_does_not_create_runs_and_project_registration_survives_restart(self):
  self.assertEqual(len(self.lib.catalog()['workflows']),1);self.assertFalse((self.a/'.workbench').exists())
  (self.b/'release-workbench-tests.yaml').write_text(render_yaml(workflow([command('b')])));self.lib.register(project=str(self.b))
  restarted=Library(self.file);self.assertEqual(len(restarted.catalog()['workflows']),2);self.assertFalse(restarted.apps)
 def test_custom_yaml_requires_explicit_registration(self):
  file=self.b/'checks.yaml';file.write_text(render_yaml(workflow([command('b')])));self.lib.register(config=str(file))
  self.assertIn(self.lib.identity(file),self.lib.paths())
  with self.assertRaises(ValueError):self.lib.get('not-registered')
 def test_new_workflow_is_separate_and_does_not_overwrite_or_execute(self):
  old=self.file.read_bytes()
  self.lib.register(project=str(self.b));created=self.lib.create(self.lib.identity(self.b),'Second','release-workbench-second.yaml')
  self.assertEqual(self.file.read_bytes(),old);self.assertFalse(self.lib.apps)
  with self.assertRaises(ValueError):self.lib.create(self.lib.identity(self.b),'Second','release-workbench-second.yaml')
  self.assertEqual(self.lib.get(created['id']).store.root,self.b)
 def test_invalid_paths_and_templates_never_create_files(self):
  for name in ('../outside.yaml','/tmp/outside.yaml','not-yaml.txt'):
   with self.assertRaises(ValueError):self.lib.create(self.lib.identity(self.a),'Name',name)
  with self.assertRaises(ValueError):self.lib.create(self.lib.identity(self.a),'Name','new.yaml','unsupported')
  with self.assertRaises(ValueError):self.lib.register(project='relative')
 def test_execution_continues_when_another_workflow_is_opened_but_cannot_overlap(self):
  self.file.write_text(render_yaml(workflow([command('a','import time;time.sleep(.4)')])));first=self.lib.get()
  first.engine.start();other=self.lib.create(self.lib.identity(self.a),'Other','release-workbench-other.yaml');second=self.lib.get(other['id'])
  self.assertTrue(first.engine.busy());self.assertIs(first,self.lib.get())
  with self.assertRaises(ValueError):self.lib.ensure_can_run(second)
  while first.engine.busy():time.sleep(.02)
  self.lib.ensure_can_run(second)
 def test_runs_and_reports_are_owned_by_selected_project(self):
  self.lib.register(project=str(self.b));created=self.lib.create(self.lib.identity(self.b),'Second','release-workbench-second.yaml','tests');a=self.lib.get();b=self.lib.get(created['id'])
  self.assertNotEqual(a.engine.directory,b.engine.directory)
  self.assertTrue(b.engine.directory.is_relative_to(self.b));self.assertTrue(a.engine.directory.is_relative_to(self.a))
 def test_missing_and_invalid_workflows_have_recoverable_catalog_errors(self):
  self.file.write_text('version: unsupported');row=self.lib.catalog()['workflows'][0];self.assertTrue(row['error']);self.assertEqual(row['id'],self.lib.identity(self.file))
 def test_empty_project_can_create_first_workflow(self):
  lib=Library(self.b/'release-workbench.yaml');self.assertFalse(lib.catalog()['workflows']);created=lib.create(lib.identity(self.b),'First','release-workbench.yaml');self.assertEqual(lib.get(created['id']).config()['workflow']['name'],'First');lib.shutdown()
 def test_symlink_discovery_does_not_grant_access_to_other_project(self):
  outside=self.b/'secret.yaml';outside.write_text(render_yaml(workflow([command('x')])));link=self.a/'release-workbench-linked.yaml'
  try:link.symlink_to(outside)
  except OSError:self.skipTest('Symlink creation unavailable')
  self.assertNotIn(self.lib.identity(outside),self.lib.paths())

 def test_nested_folders_move_and_rename_persist_without_changing_yaml(self):
  old=self.file.read_bytes();key=self.lib.identity(self.file)
  self.lib.organize('create','Builds/Android');self.lib.organize('move','Builds/Android',workflow=key)
  self.lib.organize('rename','Builds',new_folder='Release')
  restarted=Library(self.file);catalog=restarted.catalog()
  self.assertEqual(catalog['folders'],['Release','Release/Android'])
  self.assertEqual(catalog['workflows'][0]['folder'],'Release/Android')
  self.assertEqual(old,self.file.read_bytes());self.assertFalse(restarted.apps)
 def test_removing_folder_rehomes_entries_without_removing_workflows_or_runs(self):
  key=self.lib.identity(self.file);self.lib.organize('create','Builds/Android');self.lib.organize('move','Builds/Android',workflow=key)
  self.lib.organize('remove','Builds');self.assertEqual(self.lib.catalog()['folders'],[])
  self.assertEqual(self.lib.catalog()['workflows'][0]['folder'],'');self.assertTrue(self.file.is_file())
 def test_invalid_folder_mutations_leave_registry_unchanged(self):
  self.lib.organize('create','Tests');old=self.lib.registry.read_bytes()
  for name in ('../outside','Tests//Bad','', 'Bad\\Name','a/' , 'x/'*9+'y'):
   with self.assertRaises(ValueError):self.lib.organize('create',name)
  with self.assertRaises(ValueError):self.lib.organize('rename','Tests',new_folder='Tests/Child')
  with self.assertRaises(ValueError):self.lib.organize('move','Missing',workflow=self.lib.identity(self.file))
  with self.assertRaises(ValueError):self.lib.organize('move','Tests',workflow='unknown')
  self.assertEqual(old,self.lib.registry.read_bytes())
 def test_folder_rename_collision_does_not_merge_entries(self):
  self.lib.organize('create','First');self.lib.organize('create','Second')
  with self.assertRaises(ValueError):self.lib.organize('rename','First',new_folder='Second')
  self.assertEqual(self.lib.catalog()['folders'],['First','Second'])
