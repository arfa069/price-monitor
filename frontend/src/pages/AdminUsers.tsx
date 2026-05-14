import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  App,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Popconfirm,
  Switch,
  Tag,
  Tabs,
  Spin,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  LockOutlined,
} from "@ant-design/icons";
import { adminApi, type UserCreate, type UserUpdate } from "@/api/admin";
import { useAuth } from "@/contexts/AuthContext";
import { useStaggerAnimation } from "@/hooks/useStaggerAnimation";
import {
  useGrantResourcePermission,
  useResourcePermissions,
  useRevokeResourcePermission,
  useUpdateResourcePermission,
} from "@/hooks/api";
import type {
  ResourcePermission,
  ResourcePermissionUpdate,
  User,
} from "@/types";

type AdminApiError = {
  response?: {
    data?: {
      detail?: string;
    };
  };
};

type UserFormValues = {
  username: string;
  email: string;
  password?: string;
  role?: string;
  is_active?: boolean;
};

type FormValidationError = {
  errorFields?: unknown[];
};

function getAdminErrorMessage(error: unknown, fallback: string) {
  const detail = (error as AdminApiError).response?.data?.detail;
  return detail || fallback;
}

function isFormValidationError(error: unknown): error is FormValidationError {
  return Array.isArray((error as FormValidationError).errorFields);
}

export default function AdminUsersPage() {
  const message = App.useApp().message;
  const { user: currentUser } = useAuth();
  const stagger = useStaggerAnimation(0.05, 0.05);
  const isSuperAdmin = currentUser?.role === "super_admin";
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string | undefined>();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [modalTab, setModalTab] = useState<"info" | "permissions">("info");
  const [grantModalOpen, setGrantModalOpen] = useState(false);
  const [grantTargetUser, setGrantTargetUser] = useState<User | null>(null);
  const [form] = Form.useForm();

  const [expandedUserId, setExpandedUserId] = useState<number | null>(null);
  const [expandedTab, setExpandedTab] = useState<"info" | "permissions">(
    "info",
  );
  const [editingInfoForm] = Form.useForm();

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminApi.listUsers({
        page,
        page_size: pageSize,
        search,
        role: roleFilter,
      });
      setUsers(response.items);
      setTotal(response.total);
    } catch (error: unknown) {
      message.error(getAdminErrorMessage(error, "获取用户列表失败"));
    } finally {
      setLoading(false);
    }
  }, [message, page, pageSize, roleFilter, search]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchUsers();
  }, [fetchUsers]);

  const handleCreate = () => {
    setEditingUser(null);
    setGrantTargetUser(null);
    setModalTab("info");
    form.resetFields();
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = (await form.validateFields()) as UserFormValues;
      if (editingUser) {
        const updateData: UserUpdate = {
          username: values.username,
          email: values.email,
          role: values.role,
          is_active: values.is_active,
        };
        await adminApi.updateUser(editingUser.id, updateData);
        message.success("用户已更新");
      } else {
        const createData: UserCreate = {
          username: values.username,
          email: values.email,
          password: values.password ?? "",
          role: values.role || "user",
        };
        await adminApi.createUser(createData);
        message.success("用户已创建");
      }
      setModalOpen(false);
      fetchUsers();
    } catch (error: unknown) {
      if (!isFormValidationError(error)) {
        message.error(getAdminErrorMessage(error, "操作失败"));
      }
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await adminApi.deleteUser(id);
      message.success("用户已删除");
      fetchUsers();
    } catch (error: unknown) {
      message.error(getAdminErrorMessage(error, "删除失败"));
    }
  };

  const handleExpandEdit = (user: User) => {
    setExpandedUserId(user.id);
    setExpandedTab("info");
    editingInfoForm.setFieldsValue({
      username: user.username,
      email: user.email,
      role: user.role,
      is_active: user.is_active,
    });
  };

  const handleExpandPermissions = (user: User) => {
    setExpandedUserId(user.id);
    setExpandedTab("permissions");
  };

  const handleExpandClose = () => {
    setExpandedUserId(null);
  };

  const handleInfoSave = async () => {
    try {
      const values = (await editingInfoForm.validateFields()) as UserFormValues;
      const updateData: UserUpdate = {
        username: values.username,
        email: values.email,
        role: values.role,
        is_active: values.is_active,
      };
      await adminApi.updateUser(expandedUserId!, updateData);
      message.success("用户已更新");
      setExpandedUserId(null);
      fetchUsers();
    } catch (error: unknown) {
      if (!isFormValidationError(error)) {
        message.error(getAdminErrorMessage(error, "操作失败"));
      }
    }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "用户名", dataIndex: "username" },
    { title: "邮箱", dataIndex: "email" },
    {
      title: "角色",
      dataIndex: "role",
      render: (role: string) => {
        const map: Record<string, string> = {
          user: "普通用户",
          admin: "管理员",
          super_admin: "系统管理员",
        };
        return map[role] || role;
      },
    },
    {
      title: "状态",
      dataIndex: "is_active",
      render: (active: boolean) => (
        <Tag color={active ? "success" : "error"}>
          {active ? "正常" : "已禁用"}
        </Tag>
      ),
    },
    {
      title: "注册时间",
      dataIndex: "created_at",
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: "操作",
      render: (_value: unknown, record: User) => {
        // Admin cannot edit/delete super_admin users
        const canEdit = isSuperAdmin || record.role !== "super_admin";
        return (
          <Space size={4}>
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleExpandEdit(record)}
              disabled={!canEdit}
            >
              编辑
            </Button>
            <Button
              size="small"
              onClick={() => handleExpandPermissions(record)}
            >
              资源权限
            </Button>
            <Popconfirm
              title={`确定删除用户 ${record.username}？此操作不可恢复。`}
              onConfirm={() => handleDelete(record.id)}
              disabled={!canEdit}
            >
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                disabled={!canEdit}
              >
                删除
              </Button>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      {/* Page header — lilac for admin section (DESIGN.md: Lilac — 用户) */}
      <div className="page-header bg-admin">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">系统管理</p>
            <h1 className="page-title">用户管理</h1>
            <p className="page-subtitle">管理系统用户账号、角色与访问权限</p>
          </div>
        </div>
      </div>

      <motion.div variants={stagger.container} initial="hidden" animate="show">
        {/* Toolbar */}
        <motion.div
          variants={stagger.item}
          style={{
            marginBottom: 16,
            display: "flex",
            gap: 8,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <Input.Search
            aria-label="搜索用户名或邮箱"
            placeholder="搜索用户名或邮箱"
            onSearch={setSearch}
            style={{ width: 200, fontFamily: "var(--font-body)" }}
            className="fg-input"
          />
          <Select
            placeholder="筛选角色"
            allowClear
            style={{ width: 120, fontFamily: "var(--font-body)" }}
            onChange={setRoleFilter}
            className="fg-select"
          >
            <Select.Option value="user">普通用户</Select.Option>
            <Select.Option value="admin">管理员</Select.Option>
          </Select>
          <Button
            icon={<PlusOutlined style={{ fontSize: 14 }} />}
            onClick={handleCreate}
            className="fg-btn-secondary"
          >
            新建用户
          </Button>
          <div style={{ flex: 1 }} />
        </motion.div>

        <motion.div variants={stagger.item}>
          <Table
            columns={columns}
            dataSource={users}
            rowKey="id"
            loading={loading}
            scroll={{ x: "max-content" }}
            expandable={{
              expandedRowKeys: expandedUserId !== null ? [expandedUserId] : [],
              expandedRowRender: (record: User) => (
                <AnimatePresence initial={false}>
                  {expandedUserId === record.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0, y: -8 }}
                      animate={{ height: "auto", opacity: 1, y: 0 }}
                      exit={{ height: 0, opacity: 0, y: -8 }}
                      transition={{ duration: 0, ease: "easeInOut" }}
                      style={{ overflow: "hidden" }}
                    >
                      <UserInlineEditor
                        user={record}
                        activeTab={expandedTab}
                        onTabChange={setExpandedTab}
                        onClose={handleExpandClose}
                        onInfoSave={handleInfoSave}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              ),
              expandIcon: () => null,
              rowExpandable: () => true,
            }}
            pagination={{
              current: page,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (p, ps) => {
                setPage(p);
                setPageSize(ps);
                setExpandedUserId(null);
              },
            }}
          />
        </motion.div>
      </motion.div>

      <Modal
        title={editingUser ? "编辑用户" : "新建用户"}
        open={modalOpen}
        onOk={modalTab === "info" ? handleSubmit : undefined}
        onCancel={() => setModalOpen(false)}
        okText={editingUser ? "保存" : "创建"}
        footer={modalTab === "info" ? undefined : null}
        width={editingUser ? 720 : 520}
        forceRender
      >
        <Tabs
          activeKey={modalTab}
          onChange={(key) => setModalTab(key as "info" | "permissions")}
          items={[
            {
              key: "info",
              label: "基本信息",
              children: (
                <Form form={form} layout="vertical">
                  <Form.Item
                    name="username"
                    label="用户名"
                    rules={[{ required: true, min: 3 }]}
                  >
                    <Input />
                  </Form.Item>
                  <Form.Item
                    name="email"
                    label="邮箱"
                    rules={[{ required: true, type: "email" }]}
                  >
                    <Input />
                  </Form.Item>
                  {!editingUser && (
                    <Form.Item
                      name="password"
                      label="密码"
                      rules={[{ required: true, min: 6 }]}
                    >
                      <Input.Password />
                    </Form.Item>
                  )}
                  <Form.Item name="role" label="角色" initialValue="user">
                    <Select>
                      <Select.Option value="user">普通用户</Select.Option>
                      <Select.Option value="admin">管理员</Select.Option>
                      {isSuperAdmin && (
                        <Select.Option value="super_admin">
                          系统管理员
                        </Select.Option>
                      )}
                    </Select>
                  </Form.Item>
                  {editingUser && (
                    <Form.Item
                      name="is_active"
                      label="状态"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="正常" unCheckedChildren="禁用" />
                    </Form.Item>
                  )}
                </Form>
              ),
            },
            {
              key: "permissions",
              label: "资源权限",
              disabled: !editingUser,
              children: grantTargetUser ? (
                <ResourcePermissionsTab
                  userId={grantTargetUser.id}
                  onGrant={() => setGrantModalOpen(true)}
                />
              ) : null,
            },
          ]}
        />
      </Modal>
      {grantTargetUser && (
        <GrantPermissionModal
          userId={grantTargetUser.id}
          open={grantModalOpen}
          onClose={() => setGrantModalOpen(false)}
        />
      )}
    </div>
  );
}

function ResourcePermissionsTab({
  userId,
  onGrant,
}: {
  userId: number;
  onGrant: () => void;
}) {
  const { data, isLoading } = useResourcePermissions({ user_id: userId });
  const revoke = useRevokeResourcePermission();
  const perms = data?.items ?? [];

  if (isLoading) return <Spin />;
  if (perms.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "24px 0",
          color: "var(--color-muted)",
        }}
      >
        <LockOutlined style={{ fontSize: 32, marginBottom: 8 }} />
        <p>暂无资源权限</p>
        <Button size="small" onClick={onGrant}>
          授予权限
        </Button>
      </div>
    );
  }

  return (
    <div>
      <Table<ResourcePermission>
        dataSource={perms}
        rowKey="id"
        size="small"
        pagination={false}
        columns={[
          { title: "资源类型", dataIndex: "resource_type", width: 90 },
          { title: "资源ID", dataIndex: "resource_id", ellipsis: true },
          { title: "权限", dataIndex: "permission", width: 90 },
          {
            title: "授予时间",
            dataIndex: "created_at",
            width: 130,
            render: (value: string) =>
              new Date(value).toLocaleDateString("zh-CN"),
          },
          {
            title: "操作",
            width: 90,
            render: (_value: unknown, record: ResourcePermission) => (
              <Popconfirm
                title="确定撤销此权限？"
                onConfirm={() => revoke.mutate(record.id)}
              >
                <Button size="small" danger loading={revoke.isPending}>
                  撤销
                </Button>
              </Popconfirm>
            ),
          },
        ]}
      />
      <Button style={{ marginTop: 12 }} size="small" onClick={onGrant}>
        授予新权限
      </Button>
    </div>
  );
}

function GrantPermissionModal({
  userId,
  open,
  onClose,
}: {
  userId: number;
  open: boolean;
  onClose: () => void;
}) {
  const message = App.useApp().message;
  const grant = useGrantResourcePermission();
  const [resourceType, setResourceType] = useState("product");
  const [rawResourceIds, setRawResourceIds] = useState("");
  const [permission, setPermission] = useState<string>();

  const resourceIds = rawResourceIds
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const handleSubmit = async () => {
    if (!resourceIds.length || !permission) return;
    const result = await grant.mutateAsync({
      subject_id: userId,
      resource_type: resourceType,
      resource_ids: resourceIds,
      permission,
    });
    message.success(`已授予 ${result.granted} 项权限`);
    setRawResourceIds("");
    setPermission(undefined);
    onClose();
  };

  return (
    <Modal
      title="授予资源权限"
      open={open}
      onOk={handleSubmit}
      onCancel={onClose}
      width={480}
      okText="确认授予"
      confirmLoading={grant.isPending}
      okButtonProps={{ disabled: !resourceIds.length || !permission }}
    >
      <Form layout="vertical">
        <Form.Item label="资源类型">
          <Select
            value={resourceType}
            onChange={(value) => {
              setResourceType(value);
              setRawResourceIds("");
            }}
            options={[
              { label: "商品", value: "product" },
              { label: "职位", value: "job" },
              { label: "用户", value: "user" },
            ]}
          />
        </Form.Item>
        <Form.Item
          label="资源ID"
          extra="填列表中的内部 ID；* 表示该类型全部资源。多个 ID 用英文逗号分隔。"
        >
          <Input
            value={rawResourceIds}
            placeholder="多个资源 ID 用英文逗号分隔，* 表示全部"
            onChange={(event) => setRawResourceIds(event.target.value)}
          />
        </Form.Item>
        <Form.Item label="权限">
          <Select
            value={permission}
            placeholder="选择权限"
            onChange={setPermission}
            options={[
              { label: "读取 (read)", value: "read" },
              { label: "编辑 (write)", value: "write" },
              { label: "删除 (delete)", value: "delete" },
              { label: "全部 (*)", value: "*" },
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── Inline user editor (expanded row) ───────────────────────────────────────

interface UserInlineEditorProps {
  user: User;
  activeTab: "info" | "permissions";
  onTabChange: (tab: "info" | "permissions") => void;
  onClose: () => void;
  onInfoSave: () => void;
}

function UserInlineEditor({
  user,
  activeTab,
  onTabChange,
  onClose,
  onInfoSave,
}: UserInlineEditorProps) {
  const [infoForm] = Form.useForm();
  const isSuperAdmin = true; // inline editing is for super_admin context

  return (
    <div
      style={{
        padding: "16px 24px",
        background: "var(--color-surface)",
        borderRadius: 8,
        marginBottom: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
        <span style={{ fontWeight: 600, color: "var(--color-text)" }}>
          正在编辑：{user.username}（{user.email}）
        </span>
        <Button size="small" onClick={onClose} style={{ marginLeft: "auto" }}>
          收起
        </Button>
      </div>
      <Tabs
        activeKey={activeTab}
        onChange={(key) => onTabChange(key as "info" | "permissions")}
        items={[
          {
            key: "info",
            label: "基本信息",
            children: (
              <Form
                form={infoForm}
                layout="vertical"
                initialValues={{
                  username: user.username,
                  email: user.email,
                  role: user.role,
                  is_active: user.is_active,
                }}
              >
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                  <Form.Item
                    name="username"
                    label="用户名"
                    rules={[{ required: true, min: 3 }]}
                    style={{ flex: 1, minWidth: 120 }}
                  >
                    <Input />
                  </Form.Item>
                  <Form.Item
                    name="email"
                    label="邮箱"
                    rules={[{ required: true, type: "email" }]}
                    style={{ flex: 1, minWidth: 160 }}
                  >
                    <Input />
                  </Form.Item>
                  <Form.Item name="role" label="角色" style={{ width: 140 }}>
                    <Select>
                      <Select.Option value="user">普通用户</Select.Option>
                      <Select.Option value="admin">管理员</Select.Option>
                      {isSuperAdmin && (
                        <Select.Option value="super_admin">
                          系统管理员
                        </Select.Option>
                      )}
                    </Select>
                  </Form.Item>
                  <Form.Item
                    name="is_active"
                    label="状态"
                    valuePropName="checked"
                    style={{ width: 100 }}
                  >
                    <Switch checkedChildren="正常" unCheckedChildren="禁用" />
                  </Form.Item>
                </div>
                <Space style={{ marginTop: 8 }}>
                  <Button type="primary" onClick={onInfoSave}>
                    保存
                  </Button>
                  <Button onClick={onClose}>取消</Button>
                </Space>
              </Form>
            ),
          },
          {
            key: "permissions",
            label: "资源权限",
            children: <InlineResourcePermissionsEditor userId={user.id} />,
          },
        ]}
      />
    </div>
  );
}

// ── Inline resource permissions editor ─────────────────────────────────────

interface InlineResourcePermissionsEditorProps {
  userId: number;
}

function InlineResourcePermissionsEditor({
  userId,
}: InlineResourcePermissionsEditorProps) {
  const message = App.useApp().message;
  const { data, isLoading } = useResourcePermissions({ user_id: userId });
  const revoke = useRevokeResourcePermission();
  const update = useUpdateResourcePermission();
  const [grantModalOpen, setGrantModalOpen] = useState(false);
  const [editingPermId, setEditingPermId] = useState<number | null>(null);
  const [editForm] = Form.useForm();

  const perms = data?.items ?? [];

  const startEdit = (perm: ResourcePermission) => {
    setEditingPermId(perm.id);
    editForm.setFieldsValue({
      resource_type: perm.resource_type,
      resource_id: perm.resource_id,
      permission: perm.permission,
    });
  };

  const cancelEdit = () => {
    setEditingPermId(null);
    editForm.resetFields();
  };

  const saveEdit = async () => {
    try {
      const values = await editForm.validateFields();
      await update.mutateAsync({
        id: editingPermId!,
        data: values as ResourcePermissionUpdate,
      });
      message.success("权限已更新");
      setEditingPermId(null);
    } catch (error: unknown) {
      message.error(getAdminErrorMessage(error, "更新失败"));
    }
  };

  if (isLoading) return <Spin />;

  return (
    <div>
      <Table<ResourcePermission>
        dataSource={perms}
        rowKey="id"
        size="small"
        pagination={false}
        columns={[
          { title: "资源类型", dataIndex: "resource_type", width: 90 },
          {
            title: "资源ID",
            dataIndex: "resource_id",
            ellipsis: true,
            render: (v: string, record: ResourcePermission) =>
              editingPermId === record.id ? (
                <Form.Item style={{ margin: 0 }}>
                  <Input
                    size="small"
                    style={{ width: 100 }}
                    name="resource_id"
                    placeholder="例如 13 或 *"
                  />
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--color-muted)",
                      marginTop: 2,
                    }}
                  >
                    修改单条授权只填一个 ID 或 *
                  </div>
                </Form.Item>
              ) : (
                v
              ),
          },
          {
            title: "权限",
            dataIndex: "permission",
            width: 100,
            render: (v: string, record: ResourcePermission) =>
              editingPermId === record.id ? (
                <Form.Item style={{ margin: 0 }}>
                  <Select size="small" style={{ width: 80 }}>
                    <Select.Option value="read">read</Select.Option>
                    <Select.Option value="write">write</Select.Option>
                    <Select.Option value="delete">delete</Select.Option>
                    <Select.Option value="*">*</Select.Option>
                  </Select>
                </Form.Item>
              ) : (
                v
              ),
          },
          {
            title: "资源类型",
            dataIndex: "resource_type",
            width: 90,
            render: (v: string, record: ResourcePermission) =>
              editingPermId === record.id ? (
                <Form.Item style={{ margin: 0 }}>
                  <Select size="small" style={{ width: 80 }}>
                    <Select.Option value="product">商品</Select.Option>
                    <Select.Option value="job">职位</Select.Option>
                    <Select.Option value="user">用户</Select.Option>
                  </Select>
                </Form.Item>
              ) : (
                v
              ),
          },
          {
            title: "授予时间",
            dataIndex: "created_at",
            width: 130,
            render: (v: string) => new Date(v).toLocaleDateString("zh-CN"),
          },
          {
            title: "操作",
            width: 120,
            render: (_v: unknown, record: ResourcePermission) =>
              editingPermId === record.id ? (
                <Space size={4}>
                  <Button
                    size="small"
                    type="primary"
                    loading={update.isPending}
                    onClick={saveEdit}
                  >
                    保存
                  </Button>
                  <Button size="small" onClick={cancelEdit}>
                    取消
                  </Button>
                </Space>
              ) : (
                <Space size={4}>
                  <Button size="small" onClick={() => startEdit(record)}>
                    编辑
                  </Button>
                  <Popconfirm
                    title="确定撤销此权限？"
                    onConfirm={() => revoke.mutate(record.id)}
                  >
                    <Button size="small" danger loading={revoke.isPending}>
                      撤销
                    </Button>
                  </Popconfirm>
                </Space>
              ),
          },
        ]}
      />
      <Button
        style={{ marginTop: 12 }}
        size="small"
        onClick={() => setGrantModalOpen(true)}
      >
        授予新权限
      </Button>
      {grantModalOpen && (
        <GrantPermissionModal
          userId={userId}
          open={grantModalOpen}
          onClose={() => setGrantModalOpen(false)}
        />
      )}
    </div>
  );
}
