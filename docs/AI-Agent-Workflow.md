# AI Agent 工作流程解析

Matt Pocock Skills 的核心设计围绕一个循环：**需求 → 编码 → 反馈 → 架构维护**

---

## 完整工作流

```mermaid
flowchart TB
    START([新任务开始]) --> GRILL{/grill-me<br/>或 /grill-with-docs}

    GRILL -->|"产出 CONTEXT.md"| CONTEXT[共享术语库]
    CONTEXT --> PRD{明确需求后}

    PRD -->|生成产品需求| TOPRD[/to-prd]
    PRD -->|拆解任务| TOISSUES[/to-issues]

    TOPRD --> ASSIGN[分配任务]
    TOISSUES --> ASSIGN

    ASSIGN -->|分配给 AI 或自己| TDD{/tdd<br/>测试驱动开发}

    TDD -->|写测试 → 红| TEST_RED[红: 写一个失败的测试]
    TEST_RED --> CODE[/diagnose<br/>调试诊断]
    CODE -->|修复 → 绿| TEST_GREEN[绿: 让测试通过]
    TEST_GREEN --> REFACTOR[重构]
    REFACTOR -->|Bug 出现| BUG{出 Bug?}

    BUG -->|是| DIAGNOSE[/diagnose<br/>诊断流程]
    DIAGNOSE --> TEST_RED

    BUG -->|否| DONE{任务完成?}

    DONE -->|否| TDD
    DONE -->|是| ARCH[/improve-codebase-architecture<br/>架构优化]

    ARCH -->|每隔几天跑一次| CONTEXT

    style START fill:#4CAF50,stroke:#388E3C,color:#fff,stroke-width:2px
    style GRILL fill:#FF9800,stroke:#F57C00,color:#fff,stroke-width:2px
    style TDD fill:#2196F3,stroke:#1976D2,color:#fff,stroke-width:2px
    style DIAGNOSE fill:#9C27B0,stroke:#7B1FA2,color:#fff,stroke-width:2px
    style ARCH fill:#607D8B,stroke:#455A64,color:#fff,stroke-width:2px
    style CONTEXT fill:#FFF9C4,stroke:#FBC02D,color:#333
```

---

## 三条核心反馈循环

| 循环 | 工具 | 触发时机 | 产出物 |
|------|------|---------|--------|
| **需求对齐循环** | `/grill-me` → `CONTEXT.md` | 每次新任务开始 | `CONTEXT.md` |
| **编码质量循环** | `/tdd` → 红绿重构 → `/diagnose` | 每次写代码 | 测试 + 可运行代码 |
| **架构维护循环** | `/improve-codebase-architecture` | 每隔几天跑一次 | 架构优化建议 |

---

## 共享语言机制（关键创新）

`CONTEXT.md` 是整个工作流的粘合剂：

```markdown
# 共享术语

| 术语 | 含义 |
|------|------|
| 素材化级联问题 | 当课程章节中的某课时获得实际位置时触发的问题 |
| PI 事件 | 学生完成某个学习活动时触发的事件 |
```

### 为什么有效

```
优化前: "当课程章节中的某个课时在文件系统中获得实际位置时出现问题"
优化后: "素材化级联问题"
```

- 把长描述压缩成精确术语
- AI 每次理解成本大幅降低
- Token 节省约 **75%**

---

## caveman 模式（省 token 终极手段）

当你和 AI 已经建立好共享术语库后，切到 `/caveman` 模式：

```
✅ 用缩写、术语、梗沟通
✅ 不解释上下文
✅ AI 用同样方式回应
```

### 典型使用场景

- AI 已经开始正确干活后
- 微调 / 小改动
- 快速迭代阶段

---

## 本质洞察

> AI Agent 失败的原因 **90% 都在需求对齐环节**，而不是编码能力。

`/grill-me` 就是来解决这个问题的 —— 在 AI 开始写代码之前，先把它"拷问"清楚。

```
        ┌─────────────────────────────────────┐
        │         传统工作流                    │
        │  需求 → AI 自由发挥 → 结果不对 → 返工   │
        └─────────────────────────────────────┘

        ┌─────────────────────────────────────┐
        │         Skills 工作流                │
        │  需求 → /grill-me 拷问 → 需求对齐     │
        │       → /tdd 测试先行 → 代码正确      │
        │       → /improve 架构维护             │
        └─────────────────────────────────────┘
```

---

## 快速命令参考

| 命令 | 用途 |
|------|------|
| `/grill-me` | 需求深入提问（非代码任务） |
| `/grill-with-docs` | 需求提问 + 生成共享术语文档 |
| `/tdd` | 测试驱动开发，红绿重构循环 |
| `/diagnose` | 调试诊断，定位复杂 Bug |
| `/improve-codebase-architecture` | 架构优化建议 |
| `/to-prd` | 当前对话 → 产品需求文档 |
| `/to-issues` | 拆解为可领养的 GitHub Issue |
| `/zoom-out` | 宏观视角理解陌生代码 |
| `/caveman` | 极简沟通模式，节省 75% token |
| `/write-a-skill` | 创建新的自定义技能 |

---

*基于 [mattpocock/skills](https://github.com/mattpocock/skills) 构建*
