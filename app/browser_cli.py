import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from executor import browser
args=sys.argv[1:]
def deny():print('Comando fora do escopo de leitura e pesquisa',file=sys.stderr);sys.exit(2)
from navigation_guard import check_url
if not args or args[0] not in {'open','snapshot','click','fill','press','scroll','scrollintoview','wait','back','forward','reload','get','is'}:deny()
cmd=args[0]
if cmd=='open':
 if len(args)!=2:deny()
 try:check_url(args[1])
 except ValueError:deny()
if cmd=='get' and (len(args)<2 or args[1] not in {'url','title','text'}):deny()
if cmd=='press' and args[1:]!=['Enter']:deny()
if any(a.startswith('-') and not (cmd=='snapshot' and a in {'-i','-c'}) for a in args[1:]):deny()
# Check click/fill/press against the live page before running them (extra layer, not a sandbox).
from action_guard import guard
from runtime import ROOT
guard(cmd,args,browser,ROOT/'execution')
try:print(browser(args))
except Exception as exc:print('Falha na navegação: '+type(exc).__name__,file=sys.stderr);sys.exit(1)
