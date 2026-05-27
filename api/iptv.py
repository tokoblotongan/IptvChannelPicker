"""
api/iptv.py — Vercel Python Serverless Function
Handles all IPTV requests server-side (no CORS issues)

Endpoints (POST /api/iptv):
  action=xtream_auth    → authenticate + return account info
  action=xtream_cats    → fetch live/vod categories
  action=xtream_live    → fetch all live channels
  action=xtream_vod     → fetch all VOD
  action=mac_auth       → MAC portal handshake + token
  action=mac_channels   → fetch all MAC portal channels
  action=m3u_fetch      → download + parse M3U/M3U8 URL
"""

import json, re, time
from http.server import BaseHTTPRequestHandler
import urllib.request, urllib.parse, urllib.error

MAG_UA = (
    "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 "
    "(KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
)
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# ─── HTTP helpers ───────────────────────────────────────────
def fetch(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def fetch_json(url, headers=None, timeout=20):
    raw = fetch(url, headers, timeout)
    return json.loads(raw)

def ok_url(u):
    try:
        r = urllib.parse.urlparse(u.strip())
        return r.scheme in ("http", "https") and bool(r.netloc)
    except Exception:
        return False

def ok_mac(m):
    return bool(m and re.match(
        r'^([0-9A-Fa-f]{2}[:\-]){5}([0-9A-Fa-f]{2})$', m.strip()))

def sort_key(name):
    n = (name or "").strip()
    if not n: return (2, "")
    c = n[0]
    if c.isdigit(): return (0, n.lower())
    if c.isalpha(): return (1, n.lower())
    return (2, n.lower())

# ─── Xtream ─────────────────────────────────────────────────
def xtream_auth(base, u, p):
    url = f"{base}/player_api.php?username={u}&password={p}"
    data = fetch_json(url, {"User-Agent": BROWSER_UA})
    return data

def xtream_categories(base, u, p, ctype):
    # ctype: live / vod / series
    action_map = {"live": "get_live_categories", "vod": "get_vod_categories"}
    action = action_map.get(ctype, "get_live_categories")
    url = f"{base}/player_api.php?username={u}&password={p}&action={action}"
    try:
        data = fetch_json(url, {"User-Agent": BROWSER_UA})
        return {str(c["category_id"]): c["category_name"] for c in data}
    except Exception:
        return {}

def xtream_live(base, u, p):
    cats = xtream_categories(base, u, p, "live")
    url = f"{base}/player_api.php?username={u}&password={p}&action=get_live_streams"
    data = fetch_json(url, {"User-Agent": BROWSER_UA}, timeout=45)
    channels = []
    for ch in data:
        sid = ch.get("stream_id")
        cid = str(ch.get("category_id", ""))
        channels.append({
            "name":      ch.get("name", "?"),
            "group":     cats.get(cid, "Live"),
            "logo":      ch.get("stream_icon", ""),
            "epg_id":    ch.get("epg_channel_id", ""),
            "num":       str(ch.get("num", "")),
            "stream_id": sid,
            "url":       f"{base}/live/{u}/{p}/{sid}.ts",
        })
    return channels

def xtream_vod(base, u, p):
    cats = xtream_categories(base, u, p, "vod")
    url = f"{base}/player_api.php?username={u}&password={p}&action=get_vod_streams"
    data = fetch_json(url, {"User-Agent": BROWSER_UA}, timeout=60)
    channels = []
    for v in data:
        sid = v.get("stream_id")
        cid = str(v.get("category_id", ""))
        channels.append({
            "name":      v.get("name", "?"),
            "group":     cats.get(cid, "VOD"),
            "logo":      v.get("stream_icon", ""),
            "epg_id":    "",
            "num":       "",
            "stream_id": sid,
            "url":       f"{base}/movie/{u}/{p}/{sid}.mp4",
        })
    return channels

# ─── MAC Portal ─────────────────────────────────────────────
def mac_handshake(portal, mac):
    url = f"{portal}portal.php?type=stb&action=handshake&JsHttpRequest=1-xml"
    headers = {
        "User-Agent": MAG_UA,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{portal}portal.php",
        "Cookie": f"mac={mac}; stb_lang=en; timezone=Europe/Amsterdam",
    }
    data = fetch_json(url, headers)
    js = data.get("js", {})
    token = js.get("token") if isinstance(js, dict) else None
    return token

def mac_channels(portal, mac, token):
    base_headers = {
        "User-Agent": MAG_UA,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{portal}portal.php",
        "Cookie": f"mac={mac}; stb_lang=en; timezone=Europe/Amsterdam",
    }
    if token:
        base_headers["Authorization"] = f"Bearer {token}"

    # Try get_all_channels first
    try:
        url = f"{portal}portal.php?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
        data = fetch_json(url, base_headers, timeout=30)
        js = data.get("js", {})
        if isinstance(js, dict):
            ch = js.get("data", [])
            if ch:
                return _mac_normalize(ch)
    except Exception:
        pass

    # Fallback: paginated get_ordered_list
    all_ch = []
    page = 1
    while True:
        try:
            url = (f"{portal}portal.php?type=itv&action=get_ordered_list"
                   f"&genre=*&p={page}&JsHttpRequest=1-xml")
            data = fetch_json(url, base_headers, timeout=25)
            js = data.get("js")
            if not isinstance(js, dict):
                break
            chunk = js.get("data", [])
            total = int(js.get("total_items", 0))
            if not chunk:
                break
            all_ch.extend(chunk)
            if total and len(all_ch) >= total:
                break
            if len(chunk) < 14:
                break
            page += 1
            time.sleep(0.05)
        except Exception:
            break

    return _mac_normalize(all_ch)

def _mac_normalize(raw):
    out = []
    for obj in raw:
        grp = (obj.get("genre_name") or obj.get("category_name") or
               str(obj.get("tv_genre_id", "")) or "")
        cmd = str(obj.get("cmd", "")).strip()
        # Extract URL from cmd string
        parts = cmd.split()
        url = next((p for p in reversed(parts)
                    if p.startswith(("http://", "https://", "rtmp"))), cmd)
        out.append({
            "name":      obj.get("name", "?"),
            "group":     grp,
            "logo":      obj.get("logo", ""),
            "epg_id":    obj.get("xmltv_id", ""),
            "num":       str(obj.get("number", "")),
            "stream_id": "",
            "url":       url,
        })
    return out

# ─── M3U Parse ──────────────────────────────────────────────
def m3u_fetch(url):
    raw = fetch(url, {"User-Agent": BROWSER_UA, "Accept": "*/*"}, timeout=40)
    return m3u_parse(raw)

def m3u_parse(text):
    channels = []
    meta = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            meta = {}
            t = re.search(r'tvg-name="([^"]*)"', line)
            g = re.search(r'group-title="([^"]*)"', line)
            l = re.search(r'tvg-logo="([^"]*)"', line)
            e = re.search(r'tvg-id="([^"]*)"', line)
            n = re.search(r'tvg-chno="([^"]*)"', line)
            meta["name"] = (t.group(1).strip() if t else
                            (line.split(",", 1)[1].strip() if "," in line else "?"))
            meta["group"] = g.group(1).strip() if g else ""
            meta["logo"] = l.group(1).strip() if l else ""
            meta["epg_id"] = e.group(1).strip() if e else ""
            meta["num"] = n.group(1).strip() if n else ""
        elif line.startswith(("http://", "https://", "rtmp")):
            channels.append({
                "name":      meta.get("name", "?"),
                "group":     meta.get("group", ""),
                "logo":      meta.get("logo", ""),
                "epg_id":    meta.get("epg_id", ""),
                "num":       meta.get("num", ""),
                "stream_id": "",
                "url":       line,
            })
            meta = {}
    return channels

# ─── Vercel Handler ─────────────────────────────────────────
def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
    }

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silence default logs

    def _send(self, status, body):
        self.send_response(status)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._send(400, {"error": "Invalid JSON body"})

        action = body.get("action", "")

        try:
            # ── Xtream Auth ──
            if action == "xtream_auth":
                base = body.get("base", "").rstrip("/")
                u = body.get("user", "")
                p = body.get("pass", "")
                if not ok_url(base) or not u:
                    return self._send(400, {"error": "base/user kosong"})
                data = xtream_auth(base, u, p)
                return self._send(200, {"ok": True, "data": data})

            # ── Xtream Live ──
            elif action == "xtream_live":
                base = body.get("base", "").rstrip("/")
                u = body.get("user", "")
                p = body.get("pass", "")
                if not ok_url(base) or not u:
                    return self._send(400, {"error": "base/user kosong"})
                channels = xtream_live(base, u, p)
                return self._send(200, {"ok": True, "channels": channels,
                                        "count": len(channels)})

            # ── Xtream VOD ──
            elif action == "xtream_vod":
                base = body.get("base", "").rstrip("/")
                u = body.get("user", "")
                p = body.get("pass", "")
                if not ok_url(base) or not u:
                    return self._send(400, {"error": "base/user kosong"})
                channels = xtream_vod(base, u, p)
                return self._send(200, {"ok": True, "channels": channels,
                                        "count": len(channels)})

            # ── MAC Auth ──
            elif action == "mac_auth":
                portal = body.get("portal", "").rstrip("/") + "/"
                mac = body.get("mac", "").upper().strip()
                if not ok_url(portal):
                    return self._send(400, {"error": "Portal URL tidak valid"})
                if not ok_mac(mac):
                    return self._send(400, {"error": "MAC address tidak valid"})
                token = mac_handshake(portal, mac)
                return self._send(200, {"ok": True, "token": token,
                                        "portal": portal, "mac": mac})

            # ── MAC Channels ──
            elif action == "mac_channels":
                portal = body.get("portal", "").rstrip("/") + "/"
                mac = body.get("mac", "").upper().strip()
                token = body.get("token", "")
                if not ok_url(portal) or not ok_mac(mac):
                    return self._send(400, {"error": "Portal/MAC tidak valid"})
                channels = mac_channels(portal, mac, token)
                return self._send(200, {"ok": True, "channels": channels,
                                        "count": len(channels)})

            # ── M3U Fetch ──
            elif action == "m3u_fetch":
                url = body.get("url", "").strip()
                if not ok_url(url):
                    return self._send(400, {"error": "URL tidak valid"})
                channels = m3u_fetch(url)
                return self._send(200, {"ok": True, "channels": channels,
                                        "count": len(channels)})

            else:
                return self._send(400, {"error": f"Unknown action: {action}"})

        except urllib.error.URLError as e:
            return self._send(502, {"error": f"Gagal koneksi ke server: {str(e.reason)}"})
        except json.JSONDecodeError:
            return self._send(502, {"error": "Respons server bukan JSON valid"})
        except Exception as e:
            return self._send(500, {"error": str(e)})
