"""Local HTTP smoke test; keeps its isolated database under var/."""
import json, os, socket, subprocess, time, urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[2]
backend=root/'backend'
env={**os.environ,'ZB_DATABASE_URL':'sqlite:///'+str(root/'var/s02_http_smoke.db')}
python=str(backend/'.venv/bin/python')
subprocess.run([python,'-m','alembic','upgrade','head'],cwd=backend,env=env,check=True)
with socket.socket() as s:
 s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
base=f'http://127.0.0.1:{port}/api/v1'
def request(path,data=None,method=None,key=None):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,method=method,headers={'Content-Type':'application/json',**({'Idempotency-Key':key} if key else {})})
 with urllib.request.urlopen(req,timeout=3) as response: return response.status,json.load(response)
def start():
 proc=subprocess.Popen([python,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=backend,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 for _ in range(60):
  try:
   request('/health');return proc
  except Exception:
   if proc.poll() is not None: raise RuntimeError('server exited')
   time.sleep(.1)
 proc.terminate();proc.wait();raise RuntimeError('server startup timed out')
body={'name':'S02 HTTP验收','context':{'bidder_name':'模拟主体','project_leader':'测试负责人','deadline':'2026-11-30T09:00:00+08:00','timezone':'Asia/Shanghai'},'scope':{'label':'S02基础接口'}}
proc=start()
try:
 status,project=request('/projects',body,'POST','s02-http-create')
 assert status==201
 assert request('/projects',body,'POST','s02-http-create')[1]==project
 pid=project['project_id']
 status,current=request('/projects/'+pid,{'expected_input_revision':1,'scope':{'label':'S02基础接口更新'}},'PATCH','s02-http-patch')
 assert current['input_revision']==2
finally:
 proc.terminate();proc.wait(timeout=5)
proc=start()
try:
 assert request('/projects/'+pid)[1]==current
 assert request('/projects')[1]['total']==1
 print(json.dumps({'http_create':'201','idempotent_replay':'passed','patch_revision':2,'process_restart_read':'passed','temporary_port':port},ensure_ascii=False))
finally:
 proc.terminate();proc.wait(timeout=5)
