param(
    [Parameter(Mandatory=$true)][ValidateSet('vision','text')][string]$Stage,
    [Parameter(Mandatory=$true)][string]$ModelPath,
    [string]$ProjectorPath,
    [string]$LlamaPath = '.local/llama/llama-server.exe',
    [string]$ConfigPath = 'configs/advanced-v2.json',
    [string]$LogPrefix = '.local/release-server'
)
$ErrorActionPreference = 'Stop'
$settings = (Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json).runtime.$Stage
$binary = (Resolve-Path -LiteralPath $LlamaPath).Path
$weights = (Resolve-Path -LiteralPath $ModelPath).Path
$serverArguments = @('-m', ('"' + $weights + '"'), '--host', '127.0.0.1', '--port', $settings.port,
    '--alias', $settings.alias, '--ctx-size', $settings.ctx_size, '--threads', $settings.threads,
    '--parallel', $settings.parallel, '--device', $settings.device, '--n-gpu-layers', $settings.n_gpu_layers)
if ($Stage -eq 'vision') {
    if (-not $ProjectorPath) { throw 'Vision requires ProjectorPath' }
    $projector = (Resolve-Path -LiteralPath $ProjectorPath).Path
    $serverArguments += @('--mmproj', ('"' + $projector + '"'), '--image-min-tokens', $settings.image_min_tokens, '--image-max-tokens', $settings.image_max_tokens)
} else {
    $serverArguments += '--jinja'
}
$parent = Split-Path -Parent ([System.IO.Path]::GetFullPath($LogPrefix))
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$process = Start-Process -FilePath $binary -ArgumentList $serverArguments -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput ($LogPrefix + '.out.log') -RedirectStandardError ($LogPrefix + '.err.log')
$process.Id
