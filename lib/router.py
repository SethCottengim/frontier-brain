"""Minimal HTTP router — stdlib only, ~50 lines."""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs


class Router:
    def __init__(self):
        self._routes = {}

    def route(self, path):
        def decorator(fn):
            self._routes[path] = fn
            return fn
        return decorator

    def match(self, path):
        return self._routes.get(path)


class APIHandler(BaseHTTPRequestHandler):
    router = None
    static_dir = None

    def do_GET(self):
        parsed = urlparse(self.path)
        handler = self.router.match(parsed.path)
        if handler:
            params = parse_qs(parsed.query)
            result = handler(params)
            self._json_response(result)
        elif parsed.path == '/':
            self._serve_file('index.html', 'text/html')
        else:
            self.send_error(404)

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filename, content_type):
        filepath = Path(self.static_dir) / filename
        if filepath.exists():
            body = filepath.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass
