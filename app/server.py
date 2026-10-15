"""Persistent, serial, read-only MCP adapter; model progress remains local."""
import asyncio,json,os,sys,time,uuid
from pathlib import Path
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
os.umask(0o077)
from runtime import ROOT, CONFIG
server=MCPServer('codex-cloud-pilot',version='0.5.0',instructions='Use navegar(tarefa,url) only for read/search browser tasks. No editing, publishing, messages, purchases or deletion. One call per user request. Local Codex performs navigation and returns only final JSON after browser cleanup. Do not poll, monitor, retry automatically or use other agents. Never send credentials in task text.')
lock=asyncio.Lock()
@server.tool()
async def navegar(tarefa:str,url:str)->dict:
 """Delegate READ/SEARCH navigation and an initial public HTTP(S) URL to local Codex. May open pages, click links/menus, scroll and fill searches with the saved Cloud profile. No editing data, publishing, messages, purchases or deletion. Returns ONLY final result after browser cleanup. One task at a time, 180s model deadline; no polling/retries. Never include passwords, codes or keys. Returns requires_auth for login blocks, out_of_scope for changes."""
 if not tarefa.strip() or len(tarefa)>6000:return {'status':'failed','error':'Task must contain 1-6000 characters'}
 sys.path.insert(0,str(ROOT/'app'))
 from navigation_guard import check_url
 try:check_url(url)
 except ValueError:return {'status':'failed','error':'Use a public HTTP(S) URL without credentials'}
 return await dispatch({'task':tarefa,'url':url})
async def dispatch(request):
 if lock.locked():return {'status':'busy','error':'Another query is running. Do not poll or retry automatically.'}
 async with lock:
  run_id=time.strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:12];state=ROOT/'runs'/run_id;state.mkdir(mode=0o700)
  started=time.time();proc=None
  env=dict(os.environ);env.update({'BROWSER_EXECUTOR_STATE':str(state),'BROWSER_EXECUTOR_SESSION':run_id})
  try:
   with (state/'executor-stderr.log').open('wb') as err:
    proc=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'app/executor.py'),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=err,env=env)
    output,_=await asyncio.wait_for(proc.communicate(json.dumps(request).encode()),timeout=300)
   lines=[line for line in output.decode().splitlines() if line.strip()]
   if len(lines)!=1:raise ValueError('Expected one final result')
   result=json.loads(lines[0]);result['run_id']=run_id
   (state/'delivery.json').write_text(json.dumps({'finished_epoch':time.time(),'elapsed_seconds':round(time.time()-started,3),'stdout_lines':len(lines),'returncode':proc.returncode,'result':result},ensure_ascii=False,indent=2))
   return result
  except BaseException as exc:
   if proc is not None and proc.returncode is None:
    proc.terminate()
    try:await asyncio.wait_for(proc.wait(),timeout=60)
    except asyncio.TimeoutError:proc.kill();await proc.wait()
   (state/'delivery-error.json').write_text(json.dumps({'finished_epoch':time.time(),'type':type(exc).__name__}))
   if isinstance(exc,asyncio.CancelledError):raise
   return {'status':'failed','run_id':run_id,'error':'Executor or delivery failed ('+type(exc).__name__+'). Do not retry automatically.'}
security=TransportSecuritySettings(enable_dns_rebinding_protection=True,allowed_hosts=['127.0.0.1:*','localhost:*',CONFIG['public_host']],allowed_origins=['https://'+CONFIG['public_host']])
mcp_app=server.streamable_http_app(streamable_http_path=CONFIG['private_path'],json_response=True,stateless_http=True,transport_security=security)
async def app(scope,receive,send):
 if scope['type']=='http' and scope['path']=='/health':
  await send({'type':'http.response.start','status':200,'headers':[(b'content-type',b'application/json')]});await send({'type':'http.response.body','body':b'{"status":"ok","scope":"browser-read-search"}'});return
 await mcp_app(scope,receive,send)
if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host='127.0.0.1',port=CONFIG['port'],access_log=False,log_level='warning',timeout_graceful_shutdown=65)
