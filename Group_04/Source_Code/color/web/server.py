# #!/usr/bin/env python3
# """
# Lightweight HTTP server for iCare web demo.
# Endpoints:
#  - GET /                          → serves test.html
#  - Static files from web/         → .html, .js, .css, .json, .png
#  - POST /append-responses         → { rows: ["numeral,type_idx,answer"], session_id?: str }
#        Appends rows to responses.csv with UTC timestamp and session_id
#  - POST /append-result            → { session_id, label, probs, total }
#        Appends a summary row to results.csv
#  - POST /next-plate               → dynamic plate generation with external fallback
# """

# from __future__ import annotations

# import json
# from datetime import datetime, timezone
# from http.server import HTTPServer, BaseHTTPRequestHandler
# from pathlib import Path
# from PIL import Image, ImageDraw, ImageFont


# # One-time external generator import (avoid per-request import overhead)
# EXT_GEN_FN = None
# try:
#     import sys
#     ext_path = r"c:\\Users\\Rahul\\OneDrive\\Desktop\\ishihara"
#     if ext_path not in sys.path:
#         sys.path.insert(0, ext_path)
#     from ishihara_gen.generator import generate_plate as _ext_gen  # type: ignore
#     EXT_GEN_FN = _ext_gen
# except Exception:
#     EXT_GEN_FN = None


# class ResponseHandler(BaseHTTPRequestHandler):
#     def _send_json(self, code: int, payload: dict) -> None:
#         self.send_response(code)
#         self.send_header('Content-type', 'application/json')
#         self.end_headers()
#         self.wfile.write(json.dumps(payload).encode('utf-8'))

#     def do_POST(self):
#         try:
#             if self.path == '/append-responses':
#                 content_length = int(self.headers.get('Content-Length', '0') or '0')
#                 raw = self.rfile.read(content_length) if content_length else b'{}'
#                 data = json.loads(raw.decode('utf-8')) if raw else {}
#                 rows = data.get('rows', [])
#                 session_id = data.get('session_id') or ''
#                 if not isinstance(rows, list):
#                     self._send_json(400, {'error': 'rows must be a list of CSV strings'})
#                     return

#                 responses_path = Path(__file__).parent.parent / 'responses.csv'
#                 header = 'numeral,type_idx,answer,timestamp,session_id\n'
#                 if not responses_path.exists() or responses_path.stat().st_size == 0:
#                     with responses_path.open('w', encoding='utf-8') as f:
#                         f.write(header)

#                 ts = datetime.now(timezone.utc).isoformat()
#                 added = 0
#                 with responses_path.open('a', encoding='utf-8') as f:
#                     for r in rows:
#                         # r is expected as 'numeral,type_idx,answer' (compat). If client already
#                         # includes timestamp/session_id, we still normalize to 5 columns by ignoring extras.
#                         parts = [p.strip() for p in str(r).split(',')]
#                         numeral = parts[0] if len(parts) > 0 else ''
#                         type_idx = parts[1] if len(parts) > 1 else ''
#                         answer = parts[2] if len(parts) > 2 else ''
#                         f.write(f"{numeral},{type_idx},{answer},{ts},{session_id}\n")
#                         added += 1
#                 self._send_json(200, {'status': 'appended', 'count': added})
#                 return

#             if self.path == '/append-result':
#                 content_length = int(self.headers.get('Content-Length', '0') or '0')
#                 raw = self.rfile.read(content_length) if content_length else b'{}'
#                 data = json.loads(raw.decode('utf-8')) if raw else {}
#                 session_id = str(data.get('session_id') or '')
#                 label = str(data.get('label') or '')
#                 probs = data.get('probs') or []
#                 total = int(data.get('total') or 0)

#                 results_path = Path(__file__).parent.parent / 'results.csv'
#                 header = 'session_id,timestamp,total_questions,label,probs_json\n'
#                 if not results_path.exists() or results_path.stat().st_size == 0:
#                     with results_path.open('w', encoding='utf-8') as f:
#                         f.write(header)
#                 ts = datetime.now(timezone.utc).isoformat()
#                 with results_path.open('a', encoding='utf-8') as f:
#                     f.write(f"{session_id},{ts},{total},{label},{json.dumps(probs)}\n")
#                 self._send_json(200, {'status': 'result_appended'})
#                 return

#             if self.path == '/next-plate':
#                 # Generate new plate via external generator if available, else fallback
#                 content_length = int(self.headers.get('Content-Length', '0') or '0')
#                 raw = self.rfile.read(content_length) if content_length else b'{}'
#                 payload = json.loads(raw.decode('utf-8')) if raw else {}
#                 plate_id = int(payload.get('plate_id', 0))
#                 type_idx = int(payload.get('type_idx', 0))
#                 numeral = int(payload.get('numeral', 12))
#                 seed = int(payload.get('seed', plate_id * 9973 + type_idx * 131 + numeral * 17))

#                 img = None
#                 meta = {}
#                 try:
#                     mode_map = {1: 'protan', 2: 'deutan', 3: 'tritan'}
#                     mode = mode_map.get(type_idx, 'normal')
#                     # Lighter defaults for fast first paint
#                     size = int(payload.get('size', 512))
#                     dot_count = int(payload.get('dot_count', 1000))
#                     min_r = int(payload.get('min_r', 6))
#                     max_r = int(payload.get('max_r', 16))
#                     hue_sep = float(payload.get('hsep', 0.12))
#                     sat = float(payload.get('sat', 0.8))
#                     lum = float(payload.get('lum', 0.65))
#                     outline = int(payload.get('outline', 0))
#                     if EXT_GEN_FN is not None:
#                         img = EXT_GEN_FN(
#                             text=str(numeral),
#                             size=size,
#                             seed=seed,
#                             dot_count=dot_count,
#                             dot_radius_px=(min_r, max_r),
#                             color_luminance=lum,
#                             color_saturation=sat,
#                             hue_separation=hue_sep,
#                             outline_thickness=outline,
#                             palette_mode=mode,
#                         )
#                     else:
#                         raise RuntimeError('external_generator_unavailable')
#                     meta = {
#                         'source': 'external',
#                         'palette_mode': mode,
#                         'size': size,
#                         'dot_count': dot_count,
#                         'radius_px': [min_r, max_r],
#                         'hsep': hue_sep,
#                         'sat': sat,
#                         'lum': lum,
#                         'outline': outline,
#                     }
#                 except Exception:
#                     # Fallback to local minimal generator
#                     try:
#                         from ishihara_gen import PlateSpec, generate_plate  # type: ignore
#                         spec = PlateSpec(width=512, height=512, type_idx=type_idx, numeral=numeral, rng_seed=seed)
#                         img, meta = generate_plate(spec)
#                     except Exception:
#                         img = None
#                         meta = {'error': 'no_generator'}

#                 out_dir = Path(__file__).parent / 'plates' / 'generated'
#                 out_dir.mkdir(parents=True, exist_ok=True)
#                 filename = f"gen_{plate_id}_{type_idx}_{numeral}_{seed}.png"
#                 out_path = out_dir / filename
#                 if img is not None:
#                     try:
#                         img.save(out_path, format='PNG')
#                     except Exception:
#                         img = None
#                 # If generation failed, create a placeholder so the client never 404s
#                 if img is None:
#                     try:
#                         w, h = 512, 512
#                         ph = Image.new('RGB', (w, h), (30, 30, 30))
#                         dr = ImageDraw.Draw(ph)
#                         msg = 'GEN ERROR'
#                         try:
#                             ft = ImageFont.truetype('arial.ttf', 36)
#                         except Exception:
#                             ft = ImageFont.load_default()
#                         tw, th = dr.textbbox((0,0), msg, font=ft)[2:]
#                         dr.text(((w - tw)//2, (h - th)//2), msg, fill=(220,80,80), font=ft)
#                         ph.save(out_path, format='PNG')
#                         meta['placeholder'] = True
#                     except Exception:
#                         # As a last resort, respond with 500
#                         self._send_json(500, {'error': 'generation_failed'})
#                         return
#                 rel_path = f"plates/generated/{filename}"
#                 self._send_json(200, {
#                     'plate_id': plate_id,
#                     'type_idx': type_idx,
#                     'numeral': numeral,
#                     'seed': seed,
#                     'path': rel_path,
#                     'meta': meta,
#                 })
#                 return

#             if self.path == '/save-responses':
#                 # Legacy endpoint used by older UI
#                 content_length = int(self.headers.get('Content-Length', '0') or '0')
#                 raw = self.rfile.read(content_length) if content_length else b'{}'
#                 data = json.loads(raw.decode('utf-8')) if raw else {}
#                 responses_path = Path(__file__).parent.parent / 'responses.csv'
#                 with responses_path.open('w', encoding='utf-8') as f:
#                     f.write(data.get('data', ''))
#                 self._send_json(200, {'status': 'success'})
#                 return

#             self.send_response(404)
#             self.end_headers()
#         except Exception:
#             self.send_response(500)
#             self.end_headers()

#     def do_GET(self):
#         # Serve static files from web/
#         if self.path == '/':
#             self.path = '/test.html'

#         try:
#             file_path = Path(__file__).parent / self.path.lstrip('/')
#             if file_path.exists() and file_path.is_file():
#                 with file_path.open('rb') as f:
#                     content = f.read()
#                 self.send_response(200)
#                 if file_path.suffix == '.html':
#                     self.send_header('Content-type', 'text/html')
#                 elif file_path.suffix == '.js':
#                     self.send_header('Content-type', 'application/javascript')
#                 elif file_path.suffix == '.css':
#                     self.send_header('Content-type', 'text/css')
#                 elif file_path.suffix == '.json':
#                     self.send_header('Content-type', 'application/json')
#                 elif file_path.suffix == '.png':
#                     self.send_header('Content-type', 'image/png')
#                 else:
#                     self.send_header('Content-type', 'application/octet-stream')
#                 self.end_headers()
#                 self.wfile.write(content)
#             else:
#                 self.send_response(404)
#                 self.end_headers()
#         except Exception:
#             self.send_response(500)
#             self.end_headers()


# def main() -> None:
#     port = 8000
#     server = HTTPServer(('localhost', port), ResponseHandler)
#     print(f"Server running at http://localhost:{port}")
#     print("Open http://localhost:8000/test.html to run the test")
#     try:
#         server.serve_forever()
#     except KeyboardInterrupt:
#         print("\nServer stopped")
#         server.shutdown()


# if __name__ == '__main__':
#     main()



#!/usr/bin/env python3
"""
Lightweight HTTP server for iCare web demo.
Endpoints:
 - GET /                          → serves index.html
 - Static files from web/         → .html, .js, .css, .json, .png
 - POST /append-responses         → { rows: ["numeral,type_idx,answer"], session_id?: str }
       Appends rows to responses.csv with UTC timestamp and session_id
 - POST /append-result            → { session_id, label, probs, total }
       Appends a summary row to results.csv
 - POST /next-plate               → dynamic plate generation with external fallback
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# One-time external generator import (avoid per-request import overhead)
EXT_GEN_FN = None
try:
    import sys
    ext_path = r"c:\\Users\\Rahul\\OneDrive\\Desktop\\ishihara"
    if ext_path not in sys.path:
        sys.path.insert(0, ext_path)
    from ishihara_gen.generator import generate_plate as _ext_gen  # type: ignore
    EXT_GEN_FN = _ext_gen
except Exception:
    EXT_GEN_FN = None


class ResponseHandler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict) -> None:
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def do_POST(self):
        try:
            if self.path == '/append-responses':
                content_length = int(self.headers.get('Content-Length', '0') or '0')
                raw = self.rfile.read(content_length) if content_length else b'{}'
                data = json.loads(raw.decode('utf-8')) if raw else {}
                rows = data.get('rows', [])
                session_id = data.get('session_id') or ''
                if not isinstance(rows, list):
                    self._send_json(400, {'error': 'rows must be a list of CSV strings'})
                    return

                responses_path = Path(__file__).parent.parent / 'responses.csv'
                header = 'numeral,type_idx,answer,timestamp,session_id\n'
                if not responses_path.exists() or responses_path.stat().st_size == 0:
                    with responses_path.open('w', encoding='utf-8') as f:
                        f.write(header)

                ts = datetime.now(timezone.utc).isoformat()
                added = 0
                with responses_path.open('a', encoding='utf-8') as f:
                    for r in rows:
                        parts = [p.strip() for p in str(r).split(',')]
                        numeral = parts[0] if len(parts) > 0 else ''
                        type_idx = parts[1] if len(parts) > 1 else ''
                        answer = parts[2] if len(parts) > 2 else ''
                        f.write(f"{numeral},{type_idx},{answer},{ts},{session_id}\n")
                        added += 1
                self._send_json(200, {'status': 'appended', 'count': added})
                return

            if self.path == '/train-model':
                # Train the improved model
                import subprocess
                import sys
                try:
                    # Run the training script
                    result = subprocess.run([
                        sys.executable, 
                        str(Path(__file__).parent.parent / 'scripts' / 'train_response_model.py'),
                        str(Path(__file__).parent / 'plates_manifest.json'),
                        str(Path(__file__).parent / 'weights.json')
                    ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
                    
                    if result.returncode == 0:
                        self._send_json(200, {
                            'status': 'success', 
                            'message': 'Model trained successfully',
                            'output': result.stdout
                        })
                    else:
                        self._send_json(500, {
                            'status': 'error', 
                            'message': 'Training failed',
                            'error': result.stderr
                        })
                except Exception as e:
                    self._send_json(500, {'status': 'error', 'message': str(e)})
                return

            if self.path == '/append-result':
                content_length = int(self.headers.get('Content-Length', '0') or '0')
                raw = self.rfile.read(content_length) if content_length else b'{}'
                data = json.loads(raw.decode('utf-8')) if raw else {}
                session_id = str(data.get('session_id') or '')
                label = str(data.get('label') or '')
                probs = data.get('probs') or []
                total = int(data.get('total') or 0)

                results_path = Path(__file__).parent.parent / 'results.csv'
                header = 'session_id,timestamp,total_questions,label,probs_json\n'
                if not results_path.exists() or results_path.stat().st_size == 0:
                    with results_path.open('w', encoding='utf-8') as f:
                        f.write(header)
                ts = datetime.now(timezone.utc).isoformat()
                with results_path.open('a', encoding='utf-8') as f:
                    f.write(f"{session_id},{ts},{total},{label},{json.dumps(probs)}\n")
                self._send_json(200, {'status': 'result_appended'})
                return

            if self.path == '/next-plate':
                content_length = int(self.headers.get('Content-Length', '0') or '0')
                raw = self.rfile.read(content_length) if content_length else b'{}'
                payload = json.loads(raw.decode('utf-8')) if raw else {}
                plate_id = int(payload.get('plate_id', 0))
                type_idx = int(payload.get('type_idx', 0))
                numeral = int(payload.get('numeral', 12))
                seed = int(payload.get('seed', plate_id * 9973 + type_idx * 131 + numeral * 17))

                img = None
                meta = {}
                try:
                    mode_map = {1: 'protan', 2: 'deutan', 3: 'tritan'}
                    mode = mode_map.get(type_idx, 'normal')
                    size = int(payload.get('size', 512))
                    dot_count = int(payload.get('dot_count', 1500))
                    min_r = int(payload.get('min_r', 6))
                    max_r = int(payload.get('max_r', 16))
                    hue_sep = float(payload.get('hsep', 0.12))
                    sat = float(payload.get('sat', 0.8))
                    lum = float(payload.get('lum', 0.65))
                    outline = int(payload.get('outline', 0))
                    if EXT_GEN_FN is not None:
                        img = EXT_GEN_FN(
                            text=str(numeral),
                            size=size,
                            seed=seed,
                            dot_count=dot_count,
                            dot_radius_px=(min_r, max_r),
                            color_luminance=lum,
                            color_saturation=sat,
                            hue_separation=hue_sep,
                            outline_thickness=outline,
                            palette_mode=mode,
                        )
                    else:
                        raise RuntimeError('external_generator_unavailable')
                    meta = {
                        'source': 'external',
                        'palette_mode': mode,
                        'size': size,
                        'dot_count': dot_count,
                        'radius_px': [min_r, max_r],
                        'hsep': hue_sep,
                        'sat': sat,
                        'lum': lum,
                        'outline': outline,
                    }
                except Exception:
                    try:
                        from ishihara_gen import PlateSpec, generate_plate  # type: ignore
                        spec = PlateSpec(width=512, height=512, type_idx=type_idx, numeral=numeral, rng_seed=seed)
                        img, meta = generate_plate(spec)
                    except Exception:
                        img = None
                        meta = {'error': 'no_generator'}

                out_dir = Path(__file__).parent / 'plates' / 'generated'
                out_dir.mkdir(parents=True, exist_ok=True)
                filename = f"gen_{plate_id}_{type_idx}_{numeral}_{seed}.png"
                out_path = out_dir / filename
                if img is not None:
                    try:
                        img.save(out_path, format='PNG')
                    except Exception:
                        img = None
                if img is None:
                    try:
                        w, h = 512, 512
                        ph = Image.new('RGB', (w, h), (30, 30, 30))
                        dr = ImageDraw.Draw(ph)
                        msg = 'GEN ERROR'
                        try:
                            ft = ImageFont.truetype('arial.ttf', 36)
                        except Exception:
                            ft = ImageFont.load_default()
                        tw, th = dr.textbbox((0, 0), msg, font=ft)[2:]
                        dr.text(((w - tw)//2, (h - th)//2), msg, fill=(220, 80, 80), font=ft)
                        ph.save(out_path, format='PNG')
                        meta['placeholder'] = True
                    except Exception:
                        self._send_json(500, {'error': 'generation_failed'})
                        return
                rel_path = f"plates/generated/{filename}"
                self._send_json(200, {
                    'plate_id': plate_id,
                    'type_idx': type_idx,
                    'numeral': numeral,
                    'seed': seed,
                    'path': rel_path,
                    'meta': meta,
                })
                return

            if self.path == '/save-responses':
                content_length = int(self.headers.get('Content-Length', '0') or '0')
                raw = self.rfile.read(content_length) if content_length else b'{}'
                data = json.loads(raw.decode('utf-8')) if raw else {}
                responses_path = Path(__file__).parent.parent / 'responses.csv'
                with responses_path.open('w', encoding='utf-8') as f:
                    f.write(data.get('data', ''))
                self._send_json(200, {'status': 'success'})
                return

            self.send_response(404)
            self.end_headers()
        except Exception:
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        # Serve static files from web/
        if self.path == '/':
            self.path = '/index.html'   # ✅ now serves index.html

        try:
            file_path = Path(__file__).parent / self.path.lstrip('/')
            if file_path.exists() and file_path.is_file():
                with file_path.open('rb') as f:
                    content = f.read()
                self.send_response(200)
                if file_path.suffix == '.html':
                    self.send_header('Content-type', 'text/html')
                elif file_path.suffix == '.js':
                    self.send_header('Content-type', 'application/javascript')
                elif file_path.suffix == '.css':
                    self.send_header('Content-type', 'text/css')
                elif file_path.suffix == '.json':
                    self.send_header('Content-type', 'application/json')
                elif file_path.suffix == '.png':
                    self.send_header('Content-type', 'image/png')
                else:
                    self.send_header('Content-type', 'application/octet-stream')
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
        except Exception:
            self.send_response(500)
            self.end_headers()


def main() -> None:
    port = 8000
    server = HTTPServer(('localhost', port), ResponseHandler)
    print(f"Server running at http://localhost:{port}")
    print("Open http://localhost:8000/index.html to run the app")  # ✅ changed to index.html
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.shutdown()


if __name__ == '__main__':
    main()
