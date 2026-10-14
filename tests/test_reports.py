"""Reports remain portable, escaped and bound to the selected workspace."""
import html,json,time,tempfile,unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,unquote
from release_workbench.engine import Engine
from release_workbench.server import report_with_context
from test_engine import workflow,command
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=set()
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if 'id' in attrs:self.ids.add(attrs['id'])
  if tag=='a':self.links.append(attrs.get('href',''))
class ReportTests(unittest.TestCase):
 def test_generated_report_escapes_titles_and_links_real_evidence_with_fragment_names(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);step=command('probe','from pathlib import Path;Path("evidence #1.txt").write_text("proof")',reports=['evidence #1.txt']);step['name']='<script>alert("title")</script>'
   engine=Engine(root,workflow([step]));engine.start();deadline=time.monotonic()+5
   while engine.busy() and time.monotonic()<deadline:time.sleep(.02)
   self.assertFalse(engine.busy());self.assertEqual(engine.exit_code(),0)
   text=(engine.directory/'report.html').read_text();self.assertNotIn('<script>',text);self.assertIn('&lt;script&gt;',text)
   parser=Links();parser.feed(text)
   for link in parser.links:
    if link.startswith('#'):self.assertIn(link[1:],parser.ids)
    else:self.assertTrue((engine.directory/unquote(urlsplit(link).path)).is_file(),link)
   self.assertTrue(any('%231.txt' in link for link in parser.links));self.assertIn('SHA256',text)
 def test_served_report_retains_workspace_for_relative_evidence_links(self):
  content=b'<a href="summary.json">JSON</a><a href="../log.txt?filter=one#tail">log</a><a href="#step-probe">step</a><a href="https://example.com/docs">docs</a>'
  parser=Links();parser.feed(report_with_context(content,'selected-project').decode())
  self.assertEqual(parse_qs(urlsplit(parser.links[0]).query)['workflow'],['selected-project'])
  query=parse_qs(urlsplit(parser.links[1]).query);self.assertEqual(query,{'filter':['one'],'workflow':['selected-project']});self.assertEqual(urlsplit(parser.links[1]).fragment,'tail')
  self.assertEqual(parser.links[2],'#step-probe');self.assertEqual(parser.links[3],'https://example.com/docs')
