"""Read-only Unreal MCP checks; never print authentication headers."""
import json
from pathlib import Path
import tomllib
import urllib.error
import urllib.request


class MCP:
    def __init__(self, config):
        self.url = config['url']
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
            **config.get('http_headers', {}),
        }
        self.next_id = 0

    def request(self, method, params=None, notification=False):
        self.next_id += 1
        message = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            message['params'] = params
        if not notification:
            message['id'] = self.next_id
        request = urllib.request.Request(
            self.url, data=json.dumps(message).encode(), headers=self.headers, method='POST'
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            session = response.headers.get('Mcp-Session-Id')
            if session:
                self.headers['Mcp-Session-Id'] = session
            raw = response.read().decode()
        if notification or not raw.strip():
            return {}
        if raw.lstrip().startswith('{'):
            answer = json.loads(raw)
        else:
            answers = [json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith('data:')]
            answer = next(item for item in answers if item.get('id') == self.next_id)
        if 'error' in answer:
            raise RuntimeError('JSON-RPC error: ' + str(answer['error'].get('code')))
        return answer['result']

    def close(self):
        if 'Mcp-Session-Id' not in self.headers:
            return
        try:
            request = urllib.request.Request(self.url, headers=self.headers, method='DELETE')
            with urllib.request.urlopen(request, timeout=5):
                pass
        except (urllib.error.HTTPError, urllib.error.URLError):
            pass


config_path = Path(r'C:\Users\Usuario\.codex\config.toml')
with config_path.open('rb') as handle:
    config = tomllib.load(handle)
reports = {}
for name in ('unreal-engine',):
    client = MCP(config['mcp_servers'][name])
    try:
        init = client.request('initialize', {
            'protocolVersion': '2025-03-26', 'capabilities': {},
            'clientInfo': {'name': 'arena-connection-check', 'version': '1.0'},
        })
        client.headers['MCP-Protocol-Version'] = init['protocolVersion']
        client.request('notifications/initialized', notification=True)
        tools = client.request('tools/list').get('tools', [])
        report = {'initialized': True, 'server': init['serverInfo'], 'tool_count': len(tools)}
        report['tools'] = [tool['name'] for tool in tools]
        project = client.request('resources/read', {'uri': 'ue://project'})
        texts = '\n'.join(item.get('text', '') for item in project.get('contents', []))
        report['project_resource_read'] = True
        report['is_arena_project'] = 'FactoryCtyco' in texts
        if not report['is_arena_project']:
            raise RuntimeError('Connected Unreal project is not FactoryCtyco.')
        reports[name] = report
    except urllib.error.HTTPError as exc:
        reports[name] = {'ok': False, 'http_status': exc.code}
    except Exception as exc:
        reports[name] = {'ok': False, 'error': type(exc).__name__, 'detail': str(exc)[:200]}
    finally:
        client.close()
print(json.dumps(reports, indent=2))
if any(report.get('ok') is False for report in reports.values()):
    raise SystemExit(1)
