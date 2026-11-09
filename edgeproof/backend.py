import json
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request

DEFAULT_PORT = 8091
STARTUP_TIMEOUT_S = 180
REQUEST_TIMEOUT_S = 300
POLL_S = 0.5

_REPO_BIN = os.path.join(os.path.dirname(__file__), "..", "llama.cpp", "build", "bin", "llama-server")


def find_server():
    for c in (os.environ.get("EDGEPROOF_LLAMA_SERVER"), shutil.which("llama-server"), _REPO_BIN):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return os.path.abspath(c)
    raise FileNotFoundError("llama-server not found: install llama.cpp, put llama-server on PATH, "
                            "or set EDGEPROOF_LLAMA_SERVER=/path/to/llama-server")


def gpu_used_mb():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout
        return int(out.split()[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def gpu_info():
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except OSError:
        return "unknown"


class LlamaServer:
    def __init__(self, model, port=DEFAULT_PORT, ctx=4096, ngl=99, binary=None, log=None):
        self.model, self.port, self.url = model, port, f"http://127.0.0.1:{port}"
        self.cmd = [binary or find_server(), "-m", model, "--jinja",
                    "-ngl", str(ngl), "-c", str(ctx), "--port", str(port), "--no-webui"]
        self.log = log or os.devnull
        self.peak_mb = self.base_mb = None

    def __enter__(self):
        self.base_mb = gpu_used_mb()
        self.proc = subprocess.Popen(self.cmd, stdout=open(self.log, "w"), stderr=subprocess.STDOUT)
        deadline = time.time() + STARTUP_TIMEOUT_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"llama-server exited ({self.proc.returncode}); see {self.log}")
            try:
                urllib.request.urlopen(self.url + "/health", timeout=2)
                break
            except OSError:
                time.sleep(POLL_S)
        else:
            self.proc.kill()
            raise RuntimeError(f"llama-server did not become healthy in {STARTUP_TIMEOUT_S} s")
        self.peak_mb, self._stop = gpu_used_mb(), threading.Event()
        threading.Thread(target=self._poll, daemon=True).start()
        return self

    def _poll(self):
        while not self._stop.wait(POLL_S):
            m = gpu_used_mb()
            if m is not None and (self.peak_mb is None or m > self.peak_mb):
                self.peak_mb = m

    def __exit__(self, *exc):
        self._stop.set()
        self.proc.terminate()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def vram_mb(self):
        if self.peak_mb is None or self.base_mb is None:
            return None
        return self.peak_mb - self.base_mb

    def chat(self, messages, tools, temperature, seed, parallel_tool_calls=None):
        body = {"messages": messages, "tools": tools, "temperature": temperature, "seed": seed, "verbose": True}
        if parallel_tool_calls is not None:
            body["parallel_tool_calls"] = parallel_tool_calls
        req = urllib.request.Request(self.url + "/v1/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        t0 = time.perf_counter()
        elapsed = lambda: (time.perf_counter() - t0) * 1000
        try:
            resp = json.load(urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S))
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            kind = "parser_rejected" if e.code == 500 and "does not match" in body else "server_error"
            return {"content": f"[{kind}] HTTP {e.code}: {body[:200]}", "_error": kind}, elapsed()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            return {"content": f"[server_error] {e}", "_error": "server_error"}, elapsed()
        msg = resp["choices"][0]["message"]
        raw = (resp.get("__verbose") or {}).get("content")
        if raw is not None:
            msg["_raw"] = raw
        return msg, elapsed()


def parse_tool_calls(msg):
    out = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
            if not isinstance(args, dict):
                args = None
        except (json.JSONDecodeError, TypeError):
            args = None
        out.append({"tool": fn.get("name"), "args": args, "raw": tc})
    return out
