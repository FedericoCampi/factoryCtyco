"""Project-scoped native MCP client. Credentials never leave local memory."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request

PROJECT = Path(__file__).resolve().parents[1]


class Client:
    def __init__(self):
        self.url = "http://127.0.0.1:3000/mcp"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-MCP-Capability-Token": (PROJECT / "Saved/MCP/capability-token").read_text().strip(),
        }
        self.sequence = 0

    def request(self, method, params=None, notification=False):
        self.sequence += 1
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        if not notification:
            message["id"] = self.sequence
        req = urllib.request.Request(self.url, data=json.dumps(message).encode(), headers=self.headers, method="POST")
        with urllib.request.urlopen(req, timeout=180) as response:
            if response.headers.get("Mcp-Session-Id"):
                self.headers["Mcp-Session-Id"] = response.headers["Mcp-Session-Id"]
            raw = response.read().decode()
        if notification or not raw.strip():
            return {}
        if raw.lstrip().startswith("{"):
            answer = json.loads(raw)
        else:
            answer = next(json.loads(line[5:].strip()) for line in raw.splitlines()
                          if line.startswith("data:") and json.loads(line[5:].strip()).get("id") == self.sequence)
        if "error" in answer:
            raise RuntimeError(str(answer["error"]))
        return answer["result"]

    def start(self):
        result = self.request("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                              "clientInfo": {"name": "arena-visual-polish", "version": "1.0"}})
        self.headers["MCP-Protocol-Version"] = result["protocolVersion"]
        self.request("notifications/initialized", notification=True)
        project = self.request("resources/read", {"uri": "ue://project"})
        if "FactoryCtyco" not in json.dumps(project):
            raise RuntimeError("The MCP editor is not FactoryCtyco")
        return result

    def close(self):
        if "Mcp-Session-Id" in self.headers:
            try:
                with urllib.request.urlopen(urllib.request.Request(self.url, headers=self.headers, method="DELETE"), timeout=5):
                    pass
            except Exception:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("request_file", nargs="?")
    args = parser.parse_args()
    client = Client()
    try:
        server = client.start()
        if args.request_file:
            path = Path(args.request_file).resolve()
            if not path.is_relative_to(PROJECT):
                raise ValueError("Request files must be within FactoryCtyco")
            request = json.loads(path.read_text(encoding="utf-8-sig"))
            result = client.request(request["method"], request.get("params"))
        else:
            result = {"server": server["serverInfo"], "tools": client.request("tools/list")}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
        evidence = PROJECT / "Saved/VisualPolishWork" / ("UnrealMCP-" + stamp + ".json")
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result.get("structuredContent", result), ensure_ascii=False, indent=2))
        print("MCP evidence: " + str(evidence))
        if result.get("isError"):
            raise SystemExit(1)
    finally:
        client.close()
