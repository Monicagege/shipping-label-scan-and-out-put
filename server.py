from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import json,webbrowser,threading
from urllib.parse import unquote
from engine import process
ROOT=Path(__file__).parent
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'web'),**kw)
    def do_POST(self):
        if self.path!='/api/recognize':self.send_error(404);return
        if self.headers.get('Origin') not in (None,'http://127.0.0.1:8765','http://localhost:8765'):self.send_error(403);return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=30*1024**2:raise ValueError('文件大小需在 0–30 MB 之间')
            rows=process(self.rfile.read(n),unquote(self.headers.get('X-Filename','labels.pdf')))
            payload=json.dumps({'rows':rows},ensure_ascii=False).encode();self.send_response(200)
        except Exception as e:
            payload=json.dumps({'error':str(e)},ensure_ascii=False).encode();self.send_response(400)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8765),Handler)
    print('LabelDesk V3: http://127.0.0.1:8765 · Ctrl+C 停止')
    threading.Timer(1,lambda:webbrowser.open('http://127.0.0.1:8765')).start()
    server.serve_forever()
