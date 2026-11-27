"""
Local development server for Property 360 VR.
Mirrors Cloudflare Pages static routing (/p/* -> viewer.html) and /api/* endpoints
using only Python 3.10 standard library.

Usage:
  python dev_server.py
  Default admin password: admin123 (override with ADMIN_PASSWORD env var)
"""

import hashlib
import hmac
import json
import mimetypes
import os
import re
import time
from email.parser import BytesParser
from email.policy import default as email_policy
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8080"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "local-dev-secret-key")
COOKIE_NAME = "vr_admin_session"

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")


def sign_token(payload: str) -> str:
    sig = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_cookie(cookie_header: str) -> bool:
    if not cookie_header:
        return False
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    if COOKIE_NAME not in cookie:
        return False
    val = cookie[COOKIE_NAME].value
    parts = val.split(".")
    if len(parts) != 3:
        return False
    role, exp_str, sig = parts
    if role != "admin":
        return False
    if int(exp_str) < int(time.time()):
        return False
    expected = hmac.new(
        SESSION_SECRET.encode(), f"{role}.{exp_str}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig, expected)


class DevHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status: int = 200, headers: dict | None = None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, rel_path: str):
        safe_rel = os.path.normpath(rel_path.lstrip("/")).replace("..", "")
        full_path = os.path.join(BASE_DIR, safe_rel)
        if os.path.isdir(full_path):
            full_path = os.path.join(full_path, "index.html")
        if not os.path.isfile(full_path):
            self.send_error(404, "File not found")
            return

        ctype, _ = mimetypes.guess_type(full_path)
        if not ctype:
            ctype = "application/octet-stream"
        with open(full_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/auth-check":
            ok = verify_cookie(self.headers.get("Cookie", ""))
            self._send_json({"authenticated": ok}, 200 if ok else 401)
            return

        if path == "/" or path == "":
            self._serve_file("index.html")
            return

        if path.startswith("/p/"):
            self._serve_file("viewer.html")
            return

        self._serve_file(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)

        if path == "/api/login":
            try:
                body = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self._send_json({"error": "Invalid JSON"}, 400)
                return
            if body.get("password") != ADMIN_PASSWORD:
                self._send_json({"error": "Password salah."}, 401)
                return
            exp = int(time.time()) + 86400
            token = sign_token(f"admin.{exp}")
            self._send_json(
                {"ok": True},
                200,
                {"Set-Cookie": f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400"},
            )
            return

        if path == "/api/logout":
            self._send_json(
                {"ok": True},
                200,
                {"Set-Cookie": f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"},
            )
            return

        if not verify_cookie(self.headers.get("Cookie", "")):
            self._send_json({"error": "Sesi habis atau belum login."}, 401)
            return

        if path == "/api/projects":
            try:
                data = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self._send_json({"error": "Invalid JSON"}, 400)
                return
            out_path = os.path.join(BASE_DIR, "data", "projects.json")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._send_json({"ok": True, "message": "Projek berhasil disimpan secara lokal!"})
            return

        if path == "/api/upload":
            ctype = self.headers.get("Content-Type", "")
            msg_bytes = f"Content-Type: {ctype}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + raw_body
            msg = BytesParser(policy=email_policy).parsebytes(msg_bytes)

            slug = "general"
            file_bytes = None
            filename = None

            if msg.is_multipart():
                for part in msg.iter_parts():
                    name = part.get_param("name", header="content-disposition")
                    if name == "slug":
                        slug = re.sub(r"[^a-z0-9-_]", "-", part.get_content().strip().lower()) or "general"
                    elif name == "file":
                        filename = part.get_filename() or f"upload-{int(time.time())}.bin"
                        file_bytes = part.get_payload(decode=True)

            if not file_bytes or not filename:
                self._send_json({"error": "File tidak ditemukan."}, 400)
                return

            safe_name = f"{int(time.time())}-{re.sub(r'[^a-zA-Z0-9._-]', '_', filename)}"
            rel_path = f"assets/uploads/{slug}/{safe_name}"
            full_path = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(file_bytes)

            self._send_json({"ok": True, "path": rel_path})
            return

        self.send_error(404, "Endpoint not found")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), DevHandler)
    print(f"Property 360 VR Dev Server running at http://127.0.0.1:{PORT}")
    print(f"Admin Panel: http://127.0.0.1:{PORT}/admin.html (password: {ADMIN_PASSWORD})")
    server.serve_forever()
