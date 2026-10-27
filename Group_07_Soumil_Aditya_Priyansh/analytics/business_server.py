"""Local-only live controls; every business calculation stays in Python."""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json
from urllib.parse import urlsplit,parse_qs
import webbrowser

from hospital_business import payload,validate

ASSETS=Path(__file__).resolve().parent
EDITABLE={'daily_rooms','monitoring_fraction','cash_realization_fraction','capex_ratio_per_cell',
          'maintenance_ratio_per_cell_year','pilot_success_probability'}


def serve(parameters,data,measurements,port=8765,open_browser=False):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass

        def reply(self,body,mime='application/json',status=200):
            encoded=body.encode('utf-8')
            self.send_response(status); self.send_header('Content-Type',mime+'; charset=utf-8')
            self.send_header('Content-Length',str(len(encoded))); self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(encoded)

        def do_GET(self):
            parsed=urlsplit(self.path)
            if parsed.path=='/':
                self.reply((ASSETS/'business_dashboard.html').read_text(encoding='utf-8'),'text/html'); return
            if parsed.path!='/api/model': self.reply('{}',status=404); return
            try:
                query=parse_qs(parsed.query)
                if set(query)-EDITABLE: raise ValueError('Unknown model control')
                updates={key:float(values[0]) for key,values in query.items()}
                current=replace(parameters,**updates); validate(current,data)
                response=payload(current,data,measurements)
                response['fmea']=json.loads((ASSETS/'business_fmea.json').read_text(encoding='utf-8'))
                self.reply(json.dumps(response,allow_nan=False))
            except (ValueError,TypeError) as error: self.reply(json.dumps(dict(error=str(error))),status=400)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    url=f'http://127.0.0.1:{port}/'
    print('Live CSBS model:',url,flush=True)
    print('Local computer only. Ctrl+C stops the server. Assumptions remain provisional.',flush=True)
    if open_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__=='__main__':
    from hospital_business import load_inputs,load_measurements
    p,data=load_inputs(); serve(p,data,load_measurements(),open_browser=True)
