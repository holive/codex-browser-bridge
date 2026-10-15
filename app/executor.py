"""One local request -> real Codex/browser -> one final JSON. Diagnostics stay local."""
import json,os,signal,subprocess,sys,threading,time
from pathlib import Path
from runtime import ROOT, CONFIG
from browser import api, browsers, call
STATE=Path(os.environ.get('BROWSER_EXECUTOR_STATE',str(ROOT/'runs/manual')))
SESSION=os.environ.get('BROWSER_EXECUTOR_SESSION','browser-task')
os.umask(0o077)
def browser(args):return call(args,session=SESSION)
def cancel(signum,frame):raise TimeoutError('Executor cancelled')
def execute(request):
 start=time.monotonic();tracked=None;child=None;events=[];audit={'session':SESSION,'started_epoch':time.time(),'codex_invocations':0};result={'status':'failed','result':'','final_url':'','error':'','metrics':{},'browser_closed':False}
 try:
  if set(request)!={'task','url'} or not isinstance(request['task'],str) or not 1<=len(request['task'])<=6000:raise ValueError('Expected task and initial URL')
  from navigation_guard import check_url
  check_url(request['url'])
  (STATE/'received-request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2))
  known={b['id'] for b in browsers()};setup=time.monotonic();browser(['open','about:blank'])
  new=[b for b in browsers() if b['id'] not in known and b['status']=='active'];assert len(new)==1,'Owned browser not uniquely identified'
  tracked=new[0]['id'];audit['browser_id']=tracked;result['metrics']['setup_seconds']=round(time.monotonic()-setup,3)
  prompt=(Path(__file__).with_name('executor-policy.txt')).read_text()+'\nURL inicial: '+json.dumps(request['url'])+'\nTarefa: '+json.dumps(request['task'],ensure_ascii=False)+'\nComece abrindo a URL inicial. Execute somente leitura/pesquisa e termine com o JSON solicitado.'
  (STATE/'codex-prompt.txt').write_text(prompt);env=dict(os.environ);env['PATH']=str(ROOT/'commands')+os.pathsep+env.get('PATH','')
  args=[CONFIG['codex_bin'],'exec','--ignore-user-config','--ephemeral','--skip-git-repo-check','--approve-for-me','--json','-c','sandbox_workspace_write.network_access=true','-c','model="gpt-6.1-sol"','-c','model_reasoning_effort="high"','--output-schema',str(Path(__file__).with_name('schema.json')),'-o',str(STATE/'codex-final.json'),'-']
  began=time.monotonic();audit['codex_invocations']=1
  with (STATE/'codex-events.jsonl').open('w') as raw,(STATE/'codex-stderr.log').open('w') as err:
   child=subprocess.Popen(args,cwd=ROOT/'execution',env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,start_new_session=True)
   def consume():
    for line in child.stdout:
     raw.write(line);raw.flush()
     try:events.append(json.loads(line))
     except ValueError:pass
   reader=threading.Thread(target=consume,daemon=True);reader.start();child.stdin.write(prompt);child.stdin.close()
   try:rc=child.wait(timeout=180)
   except subprocess.TimeoutExpired:raise TimeoutError('Codex deadline reached')
   reader.join(timeout=5)
  result['metrics']['codex_seconds']=round(time.monotonic()-began,3)
  usages=[e['usage'] for e in events if e.get('type')=='turn.completed'];usage=usages[-1] if usages else {}
  result['metrics'].update({'input_tokens':usage.get('input_tokens',0),'cached_input_tokens':usage.get('cached_input_tokens',0),'uncached_input_tokens':usage.get('input_tokens',0)-usage.get('cached_input_tokens',0),'output_tokens':usage.get('output_tokens',0)})
  audit['shell_calls']=sum(e.get('type')=='item.completed' and e.get('item',{}).get('type')=='command_execution' for e in events)
  answer=json.loads((STATE/'codex-final.json').read_text()) if (STATE/'codex-final.json').exists() else {}
  final_url=browser(['get','url']).strip();verified=bool(rc==0 and usage and answer.get('final_url')==final_url and answer.get('status') in {'succeeded','failed','requires_auth','out_of_scope'})
  (STATE/'verification.json').write_text(json.dumps({'process_and_final_url_checked':verified,'answer':answer,'observed_final_url':final_url},ensure_ascii=False,indent=2));audit['process_and_final_url_checked']=verified
  if verified:result.update({'status':answer['status'],'result':answer['result'],'final_url':final_url,'error':answer['error']})
  else:result['error']='Execução ou URL final não confirmada.'

 except TimeoutError:result.update({'status':'timed_out','error':'Prazo de execução atingido.'})
 except Exception as exc:result.update({'status':'failed','error':'Falha de execução ou verificação ('+type(exc).__name__+').'})
 finally:
  if child is not None and child.poll() is None:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
  try:browser(['close'])
  except Exception:audit['close_command_failed']=True
  if tracked:
   try:
    b=api('/browsers/'+tracked)
    if b['status']!='stopped':api('/browsers/'+tracked,'PATCH',{'action':'stop'});b=api('/browsers/'+tracked)
    result['browser_closed']=b['status']=='stopped';audit.update({'browser_status':b['status'],'browser_stop_confirmed_epoch':time.time(),'provider_finished_at':b.get('finishedAt'),'browser_cost_usd':b.get('browserCost'),'proxy_cost_usd':b.get('proxyCost')})
   except Exception:audit['cleanup_error']='Owned browser stop not confirmed'
  if not result['browser_closed'] and result['status']=='succeeded':result.update({'status':'failed','error':'Encerramento do navegador não confirmado.','result':''})
  result['metrics']['total_seconds']=round(time.monotonic()-start,3);audit['finished_epoch']=time.time()
  (STATE/'executor-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2));(STATE/'executor-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 return result
if __name__=='__main__':
 signal.signal(signal.SIGTERM,cancel)
 request=json.load(sys.stdin)
 print(json.dumps(execute(request),ensure_ascii=False),flush=True)
