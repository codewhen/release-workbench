"""Version-two visual starters contain no app-specific commands or credentials."""
def make(name,template):
 def c(id,kind,needs=(),scope=None,**control):return dict(id=id,name=id.replace('-',' ').title(),kind=kind,needs=list(needs),control=control,**({'scope':scope,'region':'body'} if scope else {}))
 if template=='visual-while':steps=[c('counter','declare',name='count',value=0),c('repeat','while',['counter'],test={'source':'vars.count','operator':'less_than','value':3},limit=100,timeout=1800,outputs={'count':'${vars.count}'}),c('increment','update',scope='repeat',name='count',value=1)]
 elif template=='visual-foreach':steps=[c('items','foreach',items=['first','second','third'],parallel=1,limit=100,timeout=1800),dict(id='show',name='Process current item',kind='command',scope='items',commands=[{'argv':['${python}','-c','import sys;print(sys.argv[1])','${loop.item}']}])]
 elif template=='visual-poll':steps=[c('ready','poll',test={'compute':{'commands':[{'argv':['${python}','-c','print("true")']}]}},delay=1,limit=100,timeout=1800)]
 elif template=='visual-retry':steps=[dict(id='probe',name='Retry an executable check',kind='command',commands=[{'argv':['${python}','-c','print("Check passed")']}],retry={'attempts':3,'delay':1,'backoff':2})]
 else:steps=[c('recover','try'),dict(id='failure',name='Demonstrate failure',kind='command',scope='recover',commands=[{'argv':['${python}','-c','raise RuntimeError("demonstration")']}]),dict(c('handle','handle_error',scope='recover'),region='catch'),dict(c('cleanup','wait',scope='recover',delay=.1),region='finally')]
 # Absolute positions keep scope ownership independent from canvas geometry.
 columns={};rows={}
 def column(step):
  if step['id'] in columns:return columns[step['id']]
  refs=step.get('needs',[])+([step['scope']] if step.get('scope') else [])
  n=max([-1]+[column(next(s for s in steps if s['id']==id)) for id in refs])+1
  columns[step['id']]=n;return n
 for s in steps:
  x=column(s);row=rows.get(x,0);rows[x]=row+1;s['position']={'x':x*340,'y':row*280}
 return dict(version=2,name=name,concurrency=4,inputs={},steps=steps)
