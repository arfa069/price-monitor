[CmdletBinding()]
param(
    [Parameter(ValueFromPipeline = $true)]
    [AllowEmptyString()]
    [string[]]$InputObject
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Exit-Silently {
    exit 0
}

function Write-HookLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OriginalCommand,
        [Parameter(Mandatory = $true)]
        [string]$RewrittenCommand
    )

    try {
        $projectDir = $env:CLAUDE_PROJECT_DIR
        if (-not [string]::IsNullOrWhiteSpace($projectDir)) {
            $logDir = Join-Path $projectDir '.claude'
            $logPath = Join-Path $logDir 'rtk-auto-rewrite.log'
        } else {
            $logDir = Join-Path (Get-Location) '.claude'
            $logPath = Join-Path $logDir 'rtk-auto-rewrite.log'
        }
        if (-not (Test-Path -LiteralPath $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        $line = '{0} | {1} -> {2}' -f $timestamp, $OriginalCommand, $RewrittenCommand
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    } catch {
        # Logging must never break the hook path.
    }
}

function Quote-WindowsArgument {
    param(
        [AllowEmptyString()]
        [string]$Value
    )

    if ($null -eq $Value) {
        return '""'
    }

    if ($Value -eq '') {
        return '""'
    }

    if ($Value -notmatch '[\s"]') {
        return $Value
    }

    $builder = New-Object System.Text.StringBuilder
    [void]$builder.Append('"')
    $backslashCount = 0

    foreach ($char in $Value.ToCharArray()) {
        if ($char -eq '\') {
            $backslashCount++
            continue
        }

        if ($char -eq '"') {
            if ($backslashCount -gt 0) {
                [void]$builder.Append(('\' * ($backslashCount * 2)))
                $backslashCount = 0
            }
            [void]$builder.Append('\"')
            continue
        }

        if ($backslashCount -gt 0) {
            [void]$builder.Append(('\' * $backslashCount))
            $backslashCount = 0
        }

        [void]$builder.Append($char)
    }

    if ($backslashCount -gt 0) {
        [void]$builder.Append(('\' * ($backslashCount * 2)))
    }

    [void]$builder.Append('"')
    return $builder.ToString()
}

function Invoke-RtkRewrite {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RtkPath,
        [Parameter(Mandatory = $true)]
        [string]$CommandText
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $RtkPath
    $psi.Arguments = 'rewrite -- ' + (Quote-WindowsArgument -Value $CommandText)
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    return [pscustomobject]@{
        StdOut = $stdout
        StdErr = $stderr
        ExitCode = $process.ExitCode
    }
}

$rawInput = if ($null -ne $InputObject -and $InputObject.Count -gt 0) {
    $InputObject -join [Environment]::NewLine
} else {
    [Console]::In.ReadToEnd()
}

if ([string]::IsNullOrWhiteSpace($rawInput)) {
    Exit-Silently
}

try {
    $payload = $rawInput | ConvertFrom-Json
} catch {
    Exit-Silently
}

$toolName = [string]$payload.tool_name
if ($toolName -ne 'Bash') {
    Exit-Silently
}

$toolInput = $payload.tool_input
if ($null -eq $toolInput) {
    Exit-Silently
}

$originalCommand = [string]$toolInput.command
if ([string]::IsNullOrWhiteSpace($originalCommand)) {
    Exit-Silently
}

if ($originalCommand -match '^\s*rtk(?:\.exe)?\b') {
    Exit-Silently
}

$rtk = Get-Command rtk -ErrorAction SilentlyContinue
if ($null -eq $rtk) {
    Exit-Silently
}

# Pass the full shell command as a single argument so RTK can reuse its
# existing cross-platform rewrite engine instead of re-implementing rules here.
$rewriteResult = Invoke-RtkRewrite -RtkPath $rtk.Source -CommandText $originalCommand
$rewrittenCommand = $rewriteResult.StdOut
if ($null -eq $rewrittenCommand) {
    Exit-Silently
}

if ($rewrittenCommand -is [array]) {
    $rewrittenCommand = ($rewrittenCommand -join [Environment]::NewLine)
}

$rewrittenCommand = ([string]$rewrittenCommand).Trim()
if ([string]::IsNullOrWhiteSpace($rewrittenCommand)) {
    Exit-Silently
}

if ($rewrittenCommand -eq $originalCommand.Trim()) {
    Exit-Silently
}

Write-HookLog -OriginalCommand $originalCommand -RewrittenCommand $rewrittenCommand

$updatedInput = [ordered]@{}
foreach ($property in $toolInput.PSObject.Properties) {
    $updatedInput[$property.Name] = $property.Value
}
$updatedInput.command = $rewrittenCommand

$response = @{
    hookSpecificOutput = @{
        hookEventName = 'PreToolUse'
        permissionDecision = 'allow'
        updatedInput = $updatedInput
    }
}

$response | ConvertTo-Json -Depth 100 -Compress | Write-Output
