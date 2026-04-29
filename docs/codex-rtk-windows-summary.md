# Codex + RTK Windows Auto-Rewrite Summary

## Conclusion

This work does not turn Codex on Windows into a tool with an official native hook. Instead, it provides a practical PATH-level auto-rewrite solution for Codex.

In effect, common shell commands issued by Codex can now pass through RTK's rewrite logic first. If RTK knows how to optimize a command, the wrapper runs the RTK rewrite. If RTK does not know that command shape, the wrapper falls back to the original command.

## Why This Approach Was Used

Codex on Windows currently does not expose an obvious native pre-tool rewrite hook like Claude Code `PreToolUse`.

Running `rtk init -g --codex` was confirmed to do only prompt-level setup:

- Generate global [RTK.md](C:\Users\arfac\.codex\RTK.md)
- Reference that file from global `AGENTS.md`

That means official `--codex` support is currently instruction-only, not execution-layer interception.

Further inspection showed that Codex inserts its own vendor `path` directory at the front of child-process `PATH`. That directory already contains helper binaries such as `rg.exe`.

Because that path is already first in resolution order, it can host wrapper scripts for commands like `git`, `npm`, and `python`, allowing command interception before the real executable is resolved.

## Final Design

A new installer script was added at [install-codex-rtk-wrapper.ps1](C:\Users\arfac\price-monitor\scripts\install-codex-rtk-wrapper.ps1).

The script does three things:

1. Finds the active Codex vendor `path` directory.
2. Writes a dispatcher script plus a set of `*.cmd` wrappers into that directory.
3. Updates the global [RTK.md](C:\Users\arfac\.codex\RTK.md) instructions so they describe automatic wrapper behavior instead of pure manual prefixing.

The deployed wrapper directory is:

```text
C:\Users\arfac\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\path
```

## How The Wrapper Works

The final implementation does not blindly convert every command into `rtk <cmd> ...`.

That approach was rejected because RTK is not a generic prefixer. It only knows how to rewrite certain command shapes.

The dispatcher logic is:

1. Receive the original command, such as `git status`.
2. Ask RTK by calling `rtk hook check git status`.
3. If RTK returns a valid rewrite, such as `rtk git status`, execute that rewrite.
4. If RTK returns no rewrite, such as for `node --version`, execute the original command unchanged.
5. Temporarily remove the wrapper directory from `PATH` before executing the resolved command, so the wrapper does not recursively call itself.

This makes RTK itself the source of truth for rewrite decisions.

## Wrapped Commands

The installer currently generates wrappers for:

- `git`
- `gh`
- `aws`
- `psql`
- `npm`
- `npx`
- `pnpm`
- `yarn`
- `bun`
- `jest`
- `vitest`
- `prisma`
- `tsc`
- `next`
- `prettier`
- `playwright`
- `dotnet`
- `docker`
- `kubectl`
- `node`
- `python`
- `python3`
- `pip`
- `pip3`
- `uv`
- `uvx`
- `pytest`
- `mypy`
- `ruff`
- `cargo`
- `go`
- `golangci-lint`

This list means those commands are intercepted first. It does not mean RTK necessarily rewrites every invocation of each command.

## Validation Results

Several Codex-style PowerShell tests were run.

### 1. Command Resolution

`Get-Command git` resolved to the wrapper:

```text
...\vendor\x86_64-pc-windows-msvc\path\git.cmd
```

That confirmed the wrapper directory is ahead of the real executable in command lookup.

### 2. Known Rewrite Path

`git status --short --branch` successfully passed through RTK rewrite behavior and returned the expected repository status output.

This confirmed that RTK-supported commands are being intercepted and rewritten.

### 3. Derived Rewrite Path

`python -m pytest --version` was recognized by RTK as a pytest-style command and routed through RTK's pytest handling.

This showed the solution works for semantic rewrite cases, not only literal command-name matches.

### 4. Safe Fallback

`node --version` was not broken by the wrapper. It fell back to the original command and returned the normal Node.js version output:

```text
v22.22.1
```

This confirmed that unsupported commands continue to work normally.

## Problems Encountered And Fixes

Several Windows and PowerShell issues had to be corrected:

- A broken here-string terminator initially caused the installer script to fail to parse.
- Recursive path discovery for the Codex vendor directory was unreliable on Windows, so path detection was changed to explicit directory construction.
- The first dispatcher version directly called `rtk <cmd> ...`, which failed for commands RTK does not expose as direct subcommands. This was replaced with `rtk hook check`.
- PowerShell `2>&1` converted native stderr into `ErrorRecord` objects under `Stop` mode, causing false failures. The implementation was changed to temporary file redirection for stdout and stderr.
- Warning-line filtering initially used `-like "[rtk]*"`, which was incorrect because PowerShell treats `[]` as wildcard character sets. This was replaced with a literal regex match against `^\[rtk\]`.

These fixes were required to make the wrapper reliable.

## Remaining Limits

This solution is usable, but it is not equivalent to a native Codex hook.

- It is a PATH-level wrapper, not a first-class Codex hook API.
- PowerShell built-in cmdlets are not auto-rewritten, such as `Get-Content` and `Get-ChildItem`.
- Absolute executable paths are not auto-rewritten.
- RTK still prints the banner:

```text
[rtk] /!\ No hook installed — run `rtk init -g` for automatic token savings
```

In this wrapper mode that banner is expected. It does not mean the wrapper failed. It only means RTK does not see an official hook registration.

## Files And Configuration Updated

The relevant changes are:

- New installer script: [install-codex-rtk-wrapper.ps1](C:\Users\arfac\price-monitor\scripts\install-codex-rtk-wrapper.ps1)
- Repo-level RTK reference in [AGENTS.md](C:\Users\arfac\price-monitor\AGENTS.md)
- Updated global Codex instructions in [RTK.md](C:\Users\arfac\.codex\RTK.md)

The live deployed wrapper files themselves are stored in the global Codex vendor `path` directory, not in the repository.

## Maintenance

The main future maintenance case is a Codex upgrade.

If Codex is upgraded, its vendor directory may change or be overwritten. In that case, rerun:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\arfac\price-monitor\scripts\install-codex-rtk-wrapper.ps1
```

That will:

- Rediscover the current Codex install path
- Recreate the wrappers
- Refresh the global [RTK.md](C:\Users\arfac\.codex\RTK.md)

## One-Line Summary

On Windows, Codex now uses a vendor-PATH RTK wrapper layer that asks RTK whether a command should be rewritten. If RTK knows the command, the wrapper auto-rewrites it. If RTK does not, the original command runs unchanged.
