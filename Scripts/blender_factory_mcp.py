"""MCP stdio client for the upstream mcp-for-blender package.

This starts only the MCP server subprocess, never Blender. Start a dedicated
Blender GUI with blender_factory_mcp_bootstrap.py first. All connection evidence
and server scratch data stay in Saved/VisualPolishWork/BlenderMCP.

Upstream: https://github.com/ahujasid/mcp-for-blender
Verified distribution: https://pypi.org/project/mcp-for-blender/2.0.0/
"""
import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time


PROJECT = Path(__file__).resolve().parents[1]
WORK = PROJECT / "Saved" / "VisualPolishWork" / "BlenderMCP"


def project_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(PROJECT):
        raise ValueError("Expected a path inside FactoryCtyco: " + str(path))
    return path


class StdioMCP:
    def __init__(self, python, runtime, port, output):
        self.output = output
        self.counter = 0
        self.incoming = queue.Queue()
        self.transcript = (output / "mcp-transcript.jsonl").open("w", encoding="utf-8")
        self.stderr = (output / "server.log").open("w", encoding="utf-8")
        scratch = WORK / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(runtime),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
            "BLENDER_MCP_DISABLE_TELEMETRY": "1",
            "DISABLE_TELEMETRY": "true",
            "APPDATA": str(scratch),
            "TMP": str(scratch),
            "TEMP": str(scratch),
        })
        # --target installs need site.addsitedir so pywin32's .pth can register
        # its local modules and DLL directory; no system-wide postinstall runs.
        start_server = "import site; site.addsitedir(" + repr(str(runtime)) + "); from blender_mcp.server import main; main()"
        self.process = subprocess.Popen(
            [str(python), "-u", "-c", start_server, "--host", "127.0.0.1", "--port", str(port)],
            cwd=PROJECT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.stderr, text=True, encoding="utf-8", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.process.stdout:
            try:
                self.incoming.put(json.loads(line))
            except json.JSONDecodeError:
                self.incoming.put({"protocol_diagnostic": line.rstrip()})
        self.incoming.put({"process_closed": True})

    def _log(self, direction, message):
        self.transcript.write(json.dumps({"direction": direction, "message": message}, ensure_ascii=False) + "\n")
        self.transcript.flush()

    def send(self, method, params=None, notification=False, timeout=55):
        self.counter += 1
        message = {"jsonrpc": "2.0", "method": method}
        if not notification:
            message["id"] = self.counter
        if params is not None:
            message["params"] = params
        self._log("request", message)
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        if notification:
            return None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                answer = self.incoming.get(timeout=max(0.05, deadline - time.monotonic()))
            except queue.Empty:
                break
            self._log("response", answer)
            if answer.get("process_closed"):
                raise RuntimeError("MCP server exited. See " + str(self.output / "server.log"))
            if answer.get("id") != self.counter:
                continue
            if "error" in answer:
                raise RuntimeError("MCP JSON-RPC error: " + json.dumps(answer["error"]))
            return answer["result"]
        raise TimeoutError("MCP method timed out: " + method)

    def close(self):
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=3)
        self.transcript.close()
        self.stderr.close()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inspect", "execute", "screenshot", "call"))
    parser.add_argument("--runtime", default=str(WORK / "runtime"))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--code-file")
    parser.add_argument("--tool")
    parser.add_argument("--arguments-file")
    parser.add_argument("--timeout", type=float, default=55)
    parser.add_argument("--user-prompt", default="hagamoslo. moejoremos esteticamente, iremos iterando hasta la solucion")
    args = parser.parse_args()
    runtime = project_path(args.runtime)
    if not (runtime / "blender_mcp" / "server.py").is_file():
        raise RuntimeError("Install the verified upstream MCP package into " + str(runtime) + " first.")
    if not 1024 <= args.port <= 65535:
        raise ValueError("Invalid local Blender port")
    output = WORK / ("Call-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ"))
    output.mkdir(parents=True, exist_ok=False)
    client = StdioMCP(Path(args.python), runtime, args.port, output)
    report = {"passed": False, "output": str(output), "calls": []}
    try:
        initialized = client.send("initialize", {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "FactoryCtyco-FactoryVisuals", "version": "1.0"},
        })
        save_json(output / "initialize.json", initialized)
        client.send("notifications/initialized", notification=True)
        tools = client.send("tools/list")
        save_json(output / "tools.json", tools)
        schemas = {tool["name"]: tool for tool in tools["tools"]}
        report.update(server=initialized["serverInfo"], tools=list(schemas))

        def call(name, arguments):
            if name not in schemas:
                raise RuntimeError("Server does not expose MCP tool " + name)
            properties = schemas[name].get("inputSchema", {}).get("properties", {})
            if "user_prompt" in properties:
                arguments.setdefault("user_prompt", args.user_prompt)
            result = client.send("tools/call", {"name": name, "arguments": arguments}, timeout=args.timeout)
            save_json(output / (name + ".json"), result)
            report["calls"].append(name)
            texts = [item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"]
            if result.get("isError") or any(text.startswith(("Error executing", "Rejected by safe mode", "Error:")) for text in texts):
                raise RuntimeError("MCP tool failed: " + "\n".join(texts)[:4000])
            print(json.dumps({"tool": name, "text": "\n".join(texts)[:8000]}, ensure_ascii=False))
            return result

        if args.mode == "inspect":
            if "get_addon_status" in schemas:
                call("get_addon_status", {})
            call("get_scene_info", {})
        elif args.mode == "execute":
            if not args.code_file:
                raise ValueError("execute requires --code-file inside FactoryCtyco")
            code_file = project_path(args.code_file)
            source = code_file.read_text(encoding="utf-8")
            # Send the exact reviewed source through MCP, but give it normal
            # file semantics so authoring scripts can resolve project paths.
            context = {"__file__": str(code_file), "__name__": "__main__", "__package__": None}
            code = "_factory_scope = " + repr(context) + "\nexec(compile(" + repr(source) + ", " + repr(str(code_file)) + ", 'exec'), _factory_scope)"
            call("execute_blender_code", {"code": code})
        elif args.mode == "screenshot":
            result = call("get_viewport_screenshot", {"max_size": 1400})
            for index, content in enumerate(result.get("content", [])):
                if content.get("type") == "image":
                    suffix = ".png" if content.get("mimeType") == "image/png" else ".jpg"
                    path = output / ("viewport-" + str(index) + suffix)
                    path.write_bytes(base64.b64decode(content["data"]))
                    report.setdefault("screenshots", []).append(str(path))
            if not report.get("screenshots"):
                raise RuntimeError("MCP screenshot tool returned no image")
        else:
            if not args.tool:
                raise ValueError("call requires --tool from tools/list")
            arguments = json.loads(project_path(args.arguments_file).read_text(encoding="utf-8")) if args.arguments_file else {}
            call(args.tool, arguments)
        report["passed"] = True
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        client.close()
        save_json(output / "report.json", report)
        (WORK / "latest-call.txt").write_text(str(output), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
