param(
    [string]$CodexConfig = 'C:\Users\Usuario\.codex\config.toml'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$tokenPath = Join-Path $projectRoot 'Saved/MCP/capability-token'
$unrealToken = [IO.File]::ReadAllText($tokenPath).Trim()
if ($unrealToken -notmatch '^[a-f0-9]{64}$') { throw 'Invalid Unreal capability token.' }

$config = [IO.File]::ReadAllText($CodexConfig)
$headerPattern = '(?m)^(X-MCP-Capability-Token\s*=\s*)"[^"\r\n]*"'
if ([regex]::Matches($config, $headerPattern).Count -ne 1) { throw 'Expected exactly one Unreal token header; configuration left unchanged.' }
$config = [regex]::Replace($config, $headerPattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $m.Groups[1].Value + '"' + $unrealToken + '"' })

$backup = $CodexConfig + '.arena-mcp-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak'
Copy-Item -LiteralPath $CodexConfig -Destination $backup
[IO.File]::WriteAllText($CodexConfig, $config, (New-Object Text.UTF8Encoding($false)))
Write-Output 'Unreal MCP connection token updated. No credentials printed.'
Write-Output ('Configuration backup: ' + $backup)
