"""Cancellation must stay responsive while parents exit and pipes remain open."""
import os,sys,time,tempfile,unittest
from pathlib import Path
import psutil
from release_workbench.engine import Engine
from test_engine import command,workflow

@unittest.skipIf(os.name=='nt','POSIX orphan process-group behavior; Windows taskkill is separately covered')
class StopTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.engines=[];self.children=[]
 def tearDown(self):
  for engine in self.engines:engine.stop(force=True)
  for child in self.children:
   try:child.kill()
   except psutil.NoSuchProcess:pass
  end=time.monotonic()+5
  while any(e.busy() for e in self.engines) and time.monotonic()<end:time.sleep(.02)
  self.temp.cleanup()
 def wait(self,predicate,seconds=5):
  end=time.monotonic()+seconds
  while not predicate():
   if time.monotonic()>end:self.fail('Condition did not finish within '+str(seconds)+' seconds')
   time.sleep(.02)
 def start_pipe_job(self,ignore=False,**options):
  child='import os,signal,time,pathlib;'+('signal.signal(signal.SIGINT,signal.SIG_IGN);' if ignore else '')+'pathlib.Path("pipe-child.pid").write_text(str(os.getpid()));time.sleep(60)'
  parent='import os,subprocess,sys,pathlib;pathlib.Path("parent.pid").write_text(str(os.getpid()));subprocess.Popen([sys.executable,"-c",'+repr(child)+'])'
  engine=Engine(self.root,workflow([command('job',parent,**options),command('other','import time;time.sleep(.6)'),command('dependent',needs=['job'])]));self.engines.append(engine);engine.start()
  self.wait(lambda:(self.root/'pipe-child.pid').exists());pid=int((self.root/'pipe-child.pid').read_text());self.children.append(psutil.Process(pid))
  self.wait(lambda:not psutil.pid_exists(int((self.root/'parent.pid').read_text())))
  return engine,pid
 def dead(self,pid):return not psutil.pid_exists(pid) or psutil.Process(pid).status()==psutil.STATUS_ZOMBIE
 def test_stop_after_parent_exit_closes_child_pipe_and_preserves_other_branch(self):
  engine,pid=self.start_pipe_job();engine.stop('job');self.wait(lambda:not engine.busy())
  self.assertEqual(engine.state['steps']['job']['status'],'cancelled');self.assertEqual(engine.state['steps']['other']['status'],'passed');self.assertEqual(engine.state['steps']['dependent']['status'],'blocked');self.assertTrue(self.dead(pid))
  log=engine.directory/engine.state['steps']['job']['attempts'][0]['log'];self.assertIn('STOP:',log.read_text())
 def test_timeout_applies_after_parent_exit_during_output_drain(self):
  engine,pid=self.start_pipe_job(timeout=.5);self.wait(lambda:not engine.busy())
  self.assertEqual(engine.state['steps']['job']['status'],'failed');self.assertIn('timeout',engine.state['steps']['job']['error']);self.assertTrue(self.dead(pid))
 def test_force_stop_interrupts_grace_period_for_uncooperative_child(self):
  engine,pid=self.start_pipe_job(ignore=True);engine.stop('job')
  self.wait(lambda:'allowing cleanup' in engine.state['steps']['job'].get('stage',''))
  self.assertTrue(engine.busy());start=time.monotonic();engine.stop('job',force=True);self.wait(lambda:not engine.busy())
  self.assertLess(time.monotonic()-start,3);self.assertTrue(self.dead(pid));self.assertEqual(engine.exit_code(),130);self.assertEqual(engine.state['steps']['other']['status'],'passed')
 def test_stop_all_cancels_pipe_owner_and_does_not_start_dependencies(self):
  engine,pid=self.start_pipe_job();engine.stop();self.wait(lambda:not engine.busy())
  self.assertEqual(engine.state['steps']['job']['status'],'cancelled');self.assertNotEqual(engine.state['steps']['dependent']['status'],'passed');self.assertTrue(self.dead(pid))

 def test_grace_deadline_force_terminates_a_process_that_ignores_interrupt(self):
  import subprocess
  from release_workbench.engine import cancel_tree
  code='import signal,time,pathlib;signal.signal(signal.SIGINT,signal.SIG_IGN);pathlib.Path("ready").touch();time.sleep(60)'
  process=subprocess.Popen([sys.executable,'-c',code],cwd=self.root,start_new_session=True)
  try:
   self.wait(lambda:(self.root/'ready').exists());start=time.monotonic();cancel_tree(process,grace=.1)
   self.assertLess(time.monotonic()-start,2);self.assertIsNotNone(process.returncode)
  finally:
   if process.poll() is None:process.kill()
   process.wait()
