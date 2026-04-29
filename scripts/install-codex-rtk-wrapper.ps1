param(
    [string[]]$Commands = @(
        "git",
        "gh",
        "aws",
        "psql",
        "npm",
        "npx",
        "pnpm",
        "yarn",
        "bun",
        "jest",
        "vitest",
        "prisma",
        "tsc",
        "next",
        "prettier",
        "playwright",
        "dotnet",
        "docker",
        "kubectl",
        "node",
        "python",
        "python3",
        "pip",
        "pip3",
        "uv",
        "uvx",
        "pytest",
        "mypy",
        "ruff",
        "cargo",
        "go",
        "golangci-lint"
    )
)

$ErrorActionPreference = "Stop"

function Get-CodexPathDirectory {
    $codexCommand = Get-Command codex -ErrorAction Stop
    $codexBinDir = Split-Path -Parent $codexCommand.Source
    $codexPackageRoot = Join-Path $codexBinDir "node_modules\@openai\codex"
    if (-not (Test-Path -LiteralPath $codexPackageRoot)) {
        throw "Unable to locate Codex package root at $codexPackageRoot"
    }

    $platformPackage = Get-ChildItem -LiteralPath (Join-Path $codexPackageRoot "node_modules\@openai") -Directory |
        Where-Object { $_.Name -like "codex-win32-*" } |
        Select-Object -First 1
    if (-not $platformPackage) {
        throw "Unable to locate Codex Windows platform package under $codexPackageRoot"
    }

    $vendorRoot = Join-Path $platformPackage.FullName "vendor"
    if (-not (Test-Path -LiteralPath $vendorRoot)) {
        throw "Unable to locate Codex vendor root under $($platformPackage.FullName)"
    }

    $targetTripleDir = Get-ChildItem -LiteralPath $vendorRoot -Directory | Select-Object -First 1
    if (-not $targetTripleDir) {
        throw "Unable to locate Codex target triple directory under $vendorRoot"
    }

    $pathDir = Join-Path $targetTripleDir.FullName "path"
    if (-not (Test-Path -LiteralPath $pathDir)) {
        throw "Unable to locate Codex vendor path directory at $pathDir"
    }

    return $pathDir
}

function Get-DispatcherContent {
    return @'
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Command,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"

function Resolve-RtkPath {
    $candidates = @(
        (Get-Command rtk.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Get-Command rtk -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Join-Path $HOME ".local\bin\rtk.exe")
    ) | Where-Object { $_ }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "Unable to locate rtk.exe"
}

function Get-RewrittenCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter()]
        [string[]]$Args = @()
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $argumentList = @("hook", "check", $Name) + $Args
        $process = Start-Process -FilePath $rtkPath `
            -ArgumentList $argumentList `
            -NoNewWindow `
            -Wait `
            -PassThru `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath

        $output = @()
        if (Test-Path -LiteralPath $stdoutPath) {
            $output += Get-Content -LiteralPath $stdoutPath
        }
        if (Test-Path -LiteralPath $stderrPath) {
            $output += Get-Content -LiteralPath $stderrPath
        }

        if ($process.ExitCode -ne 0) {
            return $null
        }

        foreach ($line in $output) {
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }

            if ($line -match '^\[rtk\]') {
                continue
            }

            return $line.Trim()
        }
    } finally {
        Remove-Item -LiteralPath $stdoutPath, $stderrPath -ErrorAction SilentlyContinue
    }

    return $null
}

$wrapperDir = (Split-Path -Parent $MyInvocation.MyCommand.Path).TrimEnd("\")
$pathEntries = $env:PATH -split ';'
$filteredEntries = New-Object System.Collections.Generic.List[string]

foreach ($entry in $pathEntries) {
    if ([string]::IsNullOrWhiteSpace($entry)) {
        continue
    }

    try {
        $normalized = [System.IO.Path]::GetFullPath($entry).TrimEnd("\")
    } catch {
        $normalized = $entry.TrimEnd("\")
    }

    if ($normalized -ieq $wrapperDir) {
        continue
    }

    $filteredEntries.Add($entry)
}

$env:PATH = $filteredEntries -join ';'
$env:CODEX_RTK_WRAPPER_ACTIVE = "1"

$rtkPath = Resolve-RtkPath
$rewrittenCommand = Get-RewrittenCommand -Name $Command -Args $Arguments

if (-not [string]::IsNullOrWhiteSpace($rewrittenCommand)) {
    Invoke-Expression $rewrittenCommand
    exit $LASTEXITCODE
}

& $Command @Arguments
exit $LASTEXITCODE
'@
}

function Get-WrapperContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName
    )

    return @"
@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0rtk-dispatch.ps1" "$CommandName" %*
exit /b %ERRORLEVEL%
"@
}

$pathDir = Get-CodexPathDirectory
New-Item -ItemType Directory -Force -Path $pathDir | Out-Null

$dispatcherPath = Join-Path $pathDir "rtk-dispatch.ps1"
Set-Content -LiteralPath $dispatcherPath -Value (Get-DispatcherContent) -Encoding ASCII -NoNewline

foreach ($commandName in $Commands) {
    $wrapperPath = Join-Path $pathDir "$commandName.cmd"
    Set-Content -LiteralPath $wrapperPath -Value (Get-WrapperContent -CommandName $commandName) -Encoding ASCII -NoNewline
}

$rtkDocPath = Join-Path $HOME ".codex\RTK.md"
$rtkDoc = @'
# RTK - Rust Token Killer (Codex CLI)

## Auto Rewrite

Codex on Windows does not expose a native pre-tool rewrite hook.

This machine uses a Codex PATH wrapper install instead:

- Common executable commands are checked through `rtk hook check`
- If RTK knows how to rewrite the command, the wrapper executes the RTK rewrite automatically
- If RTK has no rewrite for that command shape, the wrapper falls back to the original command
- The `[rtk] /!\ No hook installed` banner is expected in this wrapper mode and does not mean the wrapper failed
- PowerShell cmdlets and absolute executable paths are not auto-rewritten

## Rule

Rely on the automatic wrapper for covered commands.

For commands that are not covered, explicitly prefix them with `rtk` when you want RTK filtering.

Examples:

```bash
git status
npm run build
uv run pytest -q
rtk Get-ChildItem -Force
rtk C:\path\to\tool.exe --help
```

## Verification

```bash
git status
npm run build
rtk gain
```
'@
Set-Content -LiteralPath $rtkDocPath -Value $rtkDoc -Encoding UTF8 -NoNewline

Write-Output "Installed Codex RTK wrappers into: $pathDir"
Write-Output "Wrapped commands: $($Commands -join ', ')"
Write-Output "Updated: $rtkDocPath"
