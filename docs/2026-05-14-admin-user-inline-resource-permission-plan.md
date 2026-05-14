# 用户管理行内编辑与资源权限可修改 — 实施计划

**目标:** 将用户管理的“编辑用户”交互从弹窗改为表格行内展开面板，并将资源权限从“只能新增/撤销”升级为“可新增、可修改、可撤销”。

**当前问题:**

- 用户管理页点击“编辑”或“资源权限”会打开 `Modal`，上下文从表格中断开。
- 资源权限表当前只有“撤销”按钮，不能直接修改资源类型、资源 ID 或权限动作。
- 新增资源权限弹窗中的“资源ID”需要管理员手动填内部 ID，缺少修改已有授权时的低摩擦入口。

**设计方向:**

- 保留用户管理页作为主工作台，点击某一行“编辑”后，在该用户行下方展开一个内嵌面板。
- 展开面板内使用 `Tabs`：
  - `基本信息`：编辑用户名、邮箱、角色、状态。
  - `资源权限`：查看、修改、新增、撤销资源授权。
- “新建用户”仍可保留现有弹窗，避免把创建流程和行内编辑改动混在一起。
- 遵循 `doc/DESIGN.md`：数据密集后台、表格横向滚动、按钮使用胶囊风格，行内展开面板避免做成大面积浮层卡片。

---

## 现有代码入口

**Frontend:**

- `frontend/src/pages/AdminUsers.tsx`
  - 当前拥有 `modalOpen`、`editingUser`、`modalTab`、`grantModalOpen` 状态。
  - 当前 `handleEdit()` / `handleResourcePermissions()` 都会打开 `Modal`。
  - 当前 `ResourcePermissionsTab` 只展示表格，并支持 `useRevokeResourcePermission()`。
  - 当前 `GrantPermissionModal` 只负责新增授权。
- `frontend/src/api/admin.ts`
  - 当前有 `listResourcePermissions()`、`grantResourcePermission()`、`revokeResourcePermission()`。
- `frontend/src/hooks/api.ts`
  - 当前有 `useResourcePermissions()`、`useGrantResourcePermission()`、`useRevokeResourcePermission()`。
- `frontend/src/types/index.ts`
  - 当前有 `ResourcePermission` / `ResourcePermissionGrant` 等类型。

**Backend:**

- `backend/app/api/admin.py`
  - 当前有：
    - `POST /admin/resource-permissions`
    - `GET /admin/resource-permissions`
    - `DELETE /admin/resource-permissions/{permission_id}`
  - 当前没有 `PATCH /admin/resource-permissions/{permission_id}`。
- `backend/app/schemas/admin.py`
  - 当前有资源权限新增和响应 schema。
- `backend/app/models/resource_permission.py`
  - 当前唯一约束为 `subject_id + subject_type + resource_type + resource_id + permission`。

---

## 目标交互

### 用户列表行

管理员点击某一行“编辑”后：

- 表格只展开当前行，其他展开行自动收起。
- 展开面板显示在该用户行下方。
- 默认进入 `基本信息` Tab。
- 点击“资源权限”按钮时也展开同一行，但默认进入 `资源权限` Tab。

建议状态模型：

```ts
const [expandedUserId, setExpandedUserId] = useState<number | null>(null);
const [expandedTab, setExpandedTab] = useState<"info" | "permissions">("info");
const [editingForms] = Form.useForm();
```

`Table` 使用 Ant Design 的 `expandable.expandedRowRender`，并通过受控 `expandedRowKeys` 保证只展开一行。

展开/收起动画：

- 用户行下方编辑面板需要有明确的“下拉展开”动效。
- 动画时长指定为 `1000ms`，用于从表格行下方向下展开内容区。
- 展开方向：高度从 `0` 过渡到内容高度，同时 `opacity 0 -> 1`，内容轻微 `translateY(-8px) -> 0`。
- 收起方向：高度回到 `0`，`opacity 1 -> 0`。
- 动画仅用于行内编辑面板，不影响表格分页、筛选、普通按钮 hover。
- 必须尊重 `prefers-reduced-motion`：用户开启减少动画时，直接展开/收起，不播放 1 秒动画。
- 因 Ant Design Table 的 `expandedRowRender` 内容高度不是固定值，推荐使用 Framer Motion 的 `AnimatePresence` + `motion.div` 包裹展开内容，而不是只靠 CSS `height: auto` 过渡。

建议实现：

```tsx
<AnimatePresence initial={false}>
  {expandedUserId === record.id && (
    <motion.div
      initial={{ height: 0, opacity: 0, y: -8 }}
      animate={{ height: 'auto', opacity: 1, y: 0 }}
      exit={{ height: 0, opacity: 0, y: -8 }}
      transition={{ duration: prefersReducedMotion ? 0 : 1, ease: 'easeInOut' }}
      style={{ overflow: 'hidden' }}
    >
      <UserInlineEditor ... />
    </motion.div>
  )}
</AnimatePresence>
```

### 基本信息 Tab

字段：

- 用户名
- 邮箱
- 角色
- 状态

操作：

- `保存`
- `取消`

规则：

- admin 不能编辑 super_admin 用户，沿用现有 `canEdit` 逻辑。
- 保存成功后刷新用户列表，并保持当前行展开或按实现复杂度关闭展开行；推荐保持展开并更新表单值。

### 资源权限 Tab

表格列：

- 资源类型
- 资源 ID
- 权限
- 授予时间
- 操作

操作：

- `新增权限`
- `编辑`
- `保存`
- `取消`
- `撤销`

编辑模式建议：

- 每次只允许编辑一条资源权限，降低状态复杂度。
- 点击某条权限的“编辑”后，该行变为内联表单：
  - `资源类型`：Select，选项 `product` / `job` / `user`
  - `资源ID`：Input，支持具体 ID 或 `*`
  - `权限`：Select，选项 `read` / `write` / `delete` / `*`
- `保存` 调用新的 PATCH 接口。
- `取消` 恢复展示态。

新增权限：

- 可以继续使用小弹窗，也可以在权限表格顶部插入一行“新增表单”。
- 推荐第一版保留小弹窗，减少与“行内展开”改造的耦合。
- 但新增成功后应刷新当前用户的资源权限 query，并保持展开行不关闭。

---

## Backend 计划

### Task 1: 增加资源权限更新接口

**Files:**

- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/app/api/admin.py`
- Add/Modify tests: `backend/tests/test_resource_permission.py` 或新增 `backend/tests/test_admin_resource_permissions.py`

新增 schema：

```python
class ResourcePermissionUpdate(BaseModel):
    resource_type: str | None = None
    resource_id: str | None = None
    permission: str | None = None
```

新增接口：

```python
@admin_router.patch(
    "/resource-permissions/{permission_id}",
    response_model=ResourcePermissionResponse,
)
async def update_resource_permission(...):
    ...
```

验证规则：

- 需要 `require_permission("user:manage")`，与新增/撤销保持一致。
- `resource_type` 限定为 `product` / `job` / `user`。
- `permission` 限定为 `read` / `write` / `delete` / `*`。
- `resource_id` 不能为空；允许 `*`。
- 更新后若违反唯一约束，返回 400，提示“资源权限已存在”。
- 成功更新后写 audit log，建议 action 为 `permission.update`。

测试覆盖：

- super_admin/admin with `user:manage` 可以修改资源权限。
- 无权限用户 PATCH 返回 403。
- 修改不存在权限返回 404。
- 修改为重复授权返回 400。
- 修改成功后返回新 `resource_type/resource_id/permission`。
- audit 记录使用 best-effort，不应阻断更新成功。

---

## Frontend 计划

### Task 2: API 与 hooks 增加 update resource permission

**Files:**

- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/hooks/api.ts`

新增类型：

```ts
export type ResourcePermissionUpdate = {
  resource_type?: string;
  resource_id?: string;
  permission?: string;
};
```

新增 API：

```ts
updateResourcePermission: async (
  id: number,
  data: ResourcePermissionUpdate,
): Promise<ResourcePermission> => {
  const response = await api.patch<ResourcePermission>(
    `/admin/resource-permissions/${id}`,
    data,
  );
  return response.data;
};
```

新增 hook：

```ts
export const useUpdateResourcePermission = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: ResourcePermissionUpdate;
    }) => adminApi.updateResourcePermission(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resource-permissions"] });
    },
  });
};
```

### Task 3: 用户编辑从 Modal 改为行内展开

**Files:**

- Modify: `frontend/src/pages/AdminUsers.tsx`
- Optional CSS: `frontend/src/index.css`

删除或停用：

- 编辑用户用的 `modalOpen`
- 编辑用户用的主 `Modal`
- `handleEdit()` 打开 Modal 的逻辑
- `handleResourcePermissions()` 打开 Modal 的逻辑

保留：

- `GrantPermissionModal` 可继续作为新增资源权限的轻量弹窗。
- “新建用户” Modal 可暂时保留，降低变更风险。

新增组件建议：

```tsx
function UserInlineEditor({
  user,
  initialTab,
  onClose,
  onSaved,
}: ...)
```

内部结构：

- `Tabs`
- `UserInfoInlineForm`
- `ResourcePermissionsEditor`

表格配置：

```tsx
<Table
  expandable={{
    expandedRowKeys: expandedUserId ? [expandedUserId] : [],
    expandedRowRender: (record) => (
      <UserInlineEditor user={record} ... />
    ),
    expandIcon: () => null,
    rowExpandable: () => true,
  }}
/>
```

注意：

- 不要让 AntD 默认展开图标占用额外列；通过 `expandIcon: () => null` 或 CSS 隐藏。
- 展开面板应有明确顶部边界和浅背景，但不要做成“卡片套卡片”。
- 切换分页、搜索、角色筛选时关闭展开行，避免编辑到已经不在当前列表的数据。
- 行内展开/收起必须实现 `1000ms` 下拉动画；实现后用浏览器确认内容不跳动、不遮挡下一行。

### Task 4: 资源权限表支持编辑

**Files:**

- Modify: `frontend/src/pages/AdminUsers.tsx`
- Optional extract: `frontend/src/components/ResourcePermissionsEditor.tsx`

推荐拆分：

- `ResourcePermissionsTab` 改名/拆出为 `ResourcePermissionsEditor`
- 增加 `editingPermissionId`
- 增加 `permissionForm` 或局部 row state

编辑行字段：

```tsx
type PermissionEditValues = {
  resource_type: string;
  resource_id: string;
  permission: string;
};
```

按钮状态：

- 普通行：`编辑`、`撤销`
- 编辑行：`保存`、`取消`
- 保存中：对应行按钮 loading

资源 ID 输入说明：

- placeholder: `例如 13，多个授权请新增多条；* 表示全部`
- 修改单条权限时不支持逗号批量，因为 PATCH 目标是一条 grant。
- 批量新增仍可在 `授予新权限` 弹窗中支持 `13,6,4`。

### Task 5: 文案与可用性

用户管理资源权限页中补充紧凑说明，不用大段教程：

- 在新增弹窗的资源 ID 下方使用 `Form.Item extra`：
  - `填列表中的内部 ID；* 表示该类型全部资源。多个 ID 用英文逗号分隔。`
- 在编辑行的资源 ID 下方或 tooltip 中说明：
  - `修改单条授权只填一个 ID 或 *。`

---

## 验证计划

### Backend

按项目命令执行：

```powershell
powershell.exe -Command "cd C:/Users/arfac/price-monitor/backend; pytest tests/test_resource_permission.py tests/test_admin_permissions.py -v"
powershell.exe -Command "cd C:/Users/arfac/price-monitor/backend; pytest"
```

如修改 touched 文件较多，补跑定向 ruff：

```powershell
powershell.exe -Command "cd C:/Users/arfac/price-monitor/backend; ruff check app/api/admin.py app/schemas/admin.py tests/test_resource_permission.py"
```

### Frontend

```powershell
powershell.exe -Command "cd C:/Users/arfac/price-monitor/frontend; npx eslint src/pages/AdminUsers.tsx src/api/admin.ts src/hooks/api.ts src/types/index.ts"
powershell.exe -Command "cd C:/Users/arfac/price-monitor/frontend; npm run build"
```

完整 `npm run lint` 当前仓库已有无关失败，执行后需如实区分新旧问题。

### Browser QA

启动服务：

```powershell
powershell.exe -Command "cd C:/Users/arfac/price-monitor; powershell -ExecutionPolicy Bypass -File 'scripts/start_server.ps1'"
```

浏览器检查：

- 登录 `default123 / 123456`。
- 打开用户管理。
- 点击某用户“编辑”，该行下方展开面板，不出现编辑用户 Modal。
- 在 `基本信息` Tab 修改状态或邮箱后保存，列表刷新且数据正确。
- 点击某用户“资源权限”，该行下方展开并默认进入资源权限 Tab。
- 点击已有权限“编辑”，修改权限值并保存，表格更新。
- 尝试把权限修改为重复 grant，页面提示后不关闭编辑行。
- 点击“授予新权限”，新增成功后权限列表刷新。
- 点击“撤销”，授权被删除。
- 控制台无新增 error；接口请求包括：
  - `GET /api/admin/resource-permissions?user_id=... => 200`
  - `PATCH /api/admin/resource-permissions/{id} => 200`

---

## 风险与边界

- `resource_id` 当前是字符串，`*` 与数字 ID 共用同一字段；前端不能把它强制转换为 number。
- PATCH 单条权限时不支持逗号批量修改；批量能力只保留在新增授权中。
- 行内展开编辑会改变 AntD Table 的布局，高风险点是横向滚动和移动端宽度；必须浏览器实际检查。
- 不在本次计划中实现资源选择器下拉搜索商品/职位/用户；如果后续要做，可以新增 resource picker，但那会扩大接口和性能范围。
- 不改变资源权限核心语义：owner 隐式拥有自己资源权限，ACL 只表示额外 grant，不实现 deny。

---

## 交付清单

- [ ] `PATCH /admin/resource-permissions/{permission_id}` 后端接口和测试。
- [ ] 前端 API/hook/type 支持资源权限更新。
- [ ] 用户编辑从 Modal 改为表格行内展开。
- [ ] 资源权限表支持单条内联编辑。
- [ ] 新增/撤销权限流程保持可用。
- [ ] 后端测试、前端构建、定向 lint、浏览器 QA 有明确证据。
