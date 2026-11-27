"""The lab page's small server, on this computer only.

It serves the page, the clips and the sample that make_sample.py wrote, and it saves what Basel does:
the checked word boundaries in gold.json and each recording in recordings/.

    python tools/lab/server.py LAB_DIR [PORT]
"""

import json
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent.parent / "demo" / "fonts"
TAKES = ("correct", "mistake")


class Lab(SimpleHTTPRequestHandler):
    lab: Path

    def translate_path(self, path):
        path = path.split("?")[0]
        if path in ("/", "/index.html"):
            return str(HERE / "index.html")
        if path.startswith("/fonts/"):
            return str(FONTS / Path(path).name)
        if path.startswith("/recordings/"):
            return str(self.lab / "recordings" / Path(path).name)
        if path.startswith("/clips/"):
            return str(self.lab / "clips" / Path(path).name)
        if path == "/sample.json":
            return str(self.lab / "sample.json")
        return str(HERE / "missing")

    def do_GET(self):
        if self.path == "/state":
            gold = self.lab / "gold.json"
            recordings = sorted(p.name for p in (self.lab / "recordings").glob("*-*.*"))
            return self.send_json({"gold": json.loads(gold.read_text("utf-8")) if gold.exists() else {},
                                   "recordings": recordings})
        return super().do_GET()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/gold":
            gold = json.loads(body)
            tmp = self.lab / "gold.json.tmp"
            tmp.write_text(json.dumps(gold, ensure_ascii=False, indent=1), "utf-8")
            tmp.replace(self.lab / "gold.json")
            return self.send_json({"saved": len(gold)})
        m = re.fullmatch(r"/recording/(\d+)/(\w+)", self.path)
        if m and m.group(2) in TAKES and body:
            folder = self.lab / "recordings"
            folder.mkdir(exist_ok=True)
            ext = "mp4" if "mp4" in self.headers.get("Content-Type", "") else "webm"
            for old in folder.glob(f"{int(m.group(1)):02d}-{m.group(2)}.*"):
                old.unlink()
            name = f"{int(m.group(1)):02d}-{m.group(2)}.{ext}"
            (folder / name).write_bytes(body)
            return self.send_json({"saved": name})
        self.send_error(400)

    def send_json(self, data):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def main():
    Lab.lab = Path(sys.argv[1]).expanduser()
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8766
    print(f"lab on http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Lab).serve_forever()


if __name__ == "__main__":
    main()
