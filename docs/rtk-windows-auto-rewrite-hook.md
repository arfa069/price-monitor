# RTK Auto-rewrite Hook on Windows

这份方案用于替代原来的 `rtk hook claude`，解决 RTK 在原生 Windows 上无法直接做 auto-rewrite 的问题。

## 结论

可以重写，而且没必要复刻 RTK 的规则引擎。

更稳妥的做法是：

1. 让 Claude 的 `PreToolUse` hook 在 Windows 上走 `PowerShell`
2. 从标准输入读取 Claude 发来的 JSON
3. 只在 `tool_name == "Bash"` 且 `tool_input.command` 存在时处理
4. 调用 `rtk rewrite -- "<原命令>"` 获取 RTK 官方重写结果
5. 用 `hookSpecificOutput.updatedInput` 把完整的 `tool_input` 回写给 Claude

这样做的好处是：

- 不需要手写 RTK 的重写规则
- 跟随 RTK 官方 `rewrite` 子命令演进
- 比公开讨论里常见的版本更安全，因为会保留 `description`、`timeout`、`run_in_background` 等 Bash 输入字段，而不是只回传一个新的 `command`

## 推荐配置

### 方案 A：项目级配置

把脚本保存在当前仓库的 `.claude/hooks/rtk-auto-rewrite.ps1`，然后在项目的 `.claude/settings.local.json` 或 `.claude/settings.json` 里加入：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "npx block-no-verify@1.1.2"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "shell": "powershell",
            "command": "& \"$CLAUDE_PROJECT_DIR/.claude/hooks/rtk-auto-rewrite.ps1\""
          }
        ]
      }
    ]
  }
}
```

### 方案 B：全局配置

如果要替换您当前 `C:\\Users\\arfac\\.claude\\settings.json` 里的这段：

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "rtk hook claude"
    }
  ]
}
```

改成：

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "shell": "powershell",
      "command": "& \"$env:USERPROFILE\\.claude\\hooks\\rtk-auto-rewrite.ps1\""
    }
  ]
}
```

然后把本仓库里的 `.claude/hooks/rtk-auto-rewrite.ps1` 复制到：

```text
C:\Users\arfac\.claude\hooks\rtk-auto-rewrite.ps1
```

## 如果执行策略拦截 `.ps1`

如果系统执行策略阻止脚本执行，把 hook command 改成下面这版：

```json
{
  "type": "command",
  "shell": "powershell",
  "command": "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"$env:USERPROFILE\\.claude\\hooks\\rtk-auto-rewrite.ps1\""
}
```

## 跟公开讨论相比，这里修正了什么

1. 不再依赖 `bash -lc`、Unix 路径、单引号转义和 `jq`
2. 直接利用 Claude 官方支持的 `shell: \"powershell\"`
3. 不只回传 `{ \"command\": \"...\" }`，而是保留整个 `tool_input`
4. 在命令已经是 `rtk ...` 时直接跳过，避免二次包装
5. 以 `rtk rewrite` 作为单一真相源，而不是自己维护 Windows 版重写规则

## 已知边界

- 这只是重写 Bash 工具输入，不会影响非 Bash 工具
- 如果 `rtk rewrite` 判断某个命令无需代理，hook 会静默放行
- 如果 `rtk` 不在 `PATH`，hook 会静默放行
- 如果您在项目级再定义新的 `PreToolUse` 配置，需要确保不会把现有其他 hook 覆盖掉
