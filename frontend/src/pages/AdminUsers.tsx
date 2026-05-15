import { useCallback, useEffect, useMemo, useState } from "react";
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
			message.error(getAdminErrorMessage(error, "Failed to fetch user list"));
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
				message.success("User updated");
			} else {
				const createData: UserCreate = {
					username: values.username,
					email: values.email,
					password: values.password ?? "",
					role: values.role || "user",
				};
				await adminApi.createUser(createData);
				message.success("User created");
			}
			setModalOpen(false);
			fetchUsers();
		} catch (error: unknown) {
			if (!isFormValidationError(error)) {
				message.error(getAdminErrorMessage(error, "Operation failed"));
			}
		}
	};

	const handleDelete = useCallback(
		async (id: number) => {
			try {
				await adminApi.deleteUser(id);
				message.success("User deleted");
				fetchUsers();
			} catch (error: unknown) {
				message.error(getAdminErrorMessage(error, "Delete failed"));
			}
		},
		[message, fetchUsers],
	);

	const handleExpandEdit = useCallback(
		(user: User) => {
			setExpandedUserId(user.id);
			setExpandedTab("info");
			editingInfoForm.setFieldsValue({
				username: user.username,
				email: user.email,
				role: user.role,
				is_active: user.is_active,
			});
		},
		[editingInfoForm],
	);

	const handleExpandClose = useCallback(() => {
		setExpandedUserId(null);
	}, []);

	const handleInfoSave = useCallback(async () => {
		try {
			const values = (await editingInfoForm.validateFields()) as UserFormValues;
			const updateData: UserUpdate = {
				username: values.username,
				email: values.email,
				role: values.role,
				is_active: values.is_active,
			};
			await adminApi.updateUser(expandedUserId!, updateData);
			message.success("User updated");
			setExpandedUserId(null);
			fetchUsers();
		} catch (error: unknown) {
			if (!isFormValidationError(error)) {
				message.error(getAdminErrorMessage(error, "Operation failed"));
			}
		}
	}, [editingInfoForm, expandedUserId, message, fetchUsers]);

	const columns = useMemo(
		() => [
			{ title: "ID", dataIndex: "id", width: 60 },
			{ title: "Username", dataIndex: "username" },
			{ title: "Email", dataIndex: "email" },
			{
				title: "Role",
				dataIndex: "role",
				render: (role: string) => {
					const map: Record<string, string> = {
						user: "User",
						admin: "Admin",
						super_admin: "Super Admin",
					};
					return map[role] || role;
				},
			},
			{
				title: "Status",
				dataIndex: "is_active",
				render: (active: boolean) => (
					<Tag color={active ? "success" : "error"}>
						{active ? "Active" : "Disabled"}
					</Tag>
				),
			},
			{
				title: "Registered",
				dataIndex: "created_at",
				render: (v: string) => new Date(v).toLocaleString(),
			},
			{
				title: "Actions",
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
								Edit
							</Button>
							<Popconfirm
								title={`Delete user ${record.username}? This action cannot be undone.`}
								onConfirm={() => handleDelete(record.id)}
								disabled={!canEdit}
							>
								<Button
									size="small"
									danger
									icon={<DeleteOutlined />}
									disabled={!canEdit}
								>
									Delete
								</Button>
							</Popconfirm>
						</Space>
					);
				},
			},
		],
		[isSuperAdmin, handleExpandEdit, handleDelete],
	);

	const expandable = useMemo(
		() => ({
			expandedRowKeys: expandedUserId !== null ? [expandedUserId] : [],
			expandedRowRender: (record: User) => (
				<AnimatePresence>
					{expandedUserId === record.id && (
						<motion.div
							initial={{ height: 0, opacity: 0 }}
							animate={{ height: "auto", opacity: 1 }}
							exit={{ height: 0, opacity: 0 }}
							transition={{
								height: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] },
								opacity: { duration: 0.2 },
							}}
							style={{ overflow: "hidden" }}
						>
							<UserInlineEditor
								user={record}
								activeTab={expandedTab}
								onTabChange={setExpandedTab}
								onClose={handleExpandClose}
								onInfoSave={handleInfoSave}
								infoForm={editingInfoForm}
							/>
						</motion.div>
					)}
				</AnimatePresence>
			),
			expandIcon: () => null,
			rowExpandable: () => true,
		}),
		[
			expandedUserId,
			expandedTab,
			handleExpandClose,
			handleInfoSave,
			editingInfoForm,
		],
	);

	return (
		<div>
			{/* Page header — lilac for admin section (DESIGN.md: Lilac — User) */}
			<div className="page-header bg-admin">
				<div className="page-header-inner">
					<div>
						<p className="page-eyebrow">System Admin</p>
						<h1 className="page-title">User Management</h1>
						<p className="page-subtitle">
							Manage user accounts, roles, and access permissions
						</p>
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
						aria-label="Search username or email"
						placeholder="Search username or email"
						allowClear
						autoComplete="off"
						style={{
							width: 320,
							fontFamily: "var(--font-body)",
							borderRadius: "var(--radius-pill)",
						}}
						onSearch={(value) => setSearch(value)}
						onChange={(e) => setSearch(e.target.value)}
					/>
					<Select
						placeholder="Filter by Role"
						allowClear
						style={{ width: 120, fontFamily: "var(--font-body)" }}
						onChange={setRoleFilter}
						className="fg-select"
					>
						<Select.Option value="user">User</Select.Option>
						<Select.Option value="admin">Admin</Select.Option>
					</Select>
					<Button
						icon={<PlusOutlined style={{ fontSize: 14 }} />}
						onClick={handleCreate}
						className="fg-btn-secondary"
					>
						New User
					</Button>
					<div style={{ flex: 1 }} />
				</motion.div>

				<motion.div variants={stagger.item}>
					<Table
						columns={columns}
						dataSource={users}
						rowKey="id"
						loading={loading}
						scroll={{ x: "100%" }}
						expandable={expandable}
						pagination={{
							current: page,
							pageSize,
							total,
							showSizeChanger: true,
							showTotal: (total) => `Total ${total} items`,
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
				title={editingUser ? "Edit User" : "New User"}
				open={modalOpen}
				onOk={modalTab === "info" ? handleSubmit : undefined}
				onCancel={() => setModalOpen(false)}
				okText={editingUser ? "Save" : "Create"}
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
							label: "Basic Info",
							children: (
								<Form form={form} layout="vertical">
									<Form.Item
										name="username"
										label="Username"
										rules={[{ required: true, min: 3 }]}
									>
										<Input />
									</Form.Item>
									<Form.Item
										name="email"
										label="Email"
										rules={[{ required: true, type: "email" }]}
									>
										<Input />
									</Form.Item>
									{!editingUser && (
										<Form.Item
											name="password"
											label="Password"
											rules={[{ required: true, min: 6 }]}
										>
											<Input.Password />
										</Form.Item>
									)}
									<Form.Item name="role" label="Role" initialValue="user">
										<Select>
											<Select.Option value="user">User</Select.Option>
											<Select.Option value="admin">Admin</Select.Option>
											{isSuperAdmin && (
												<Select.Option value="super_admin">
													Super Admin
												</Select.Option>
											)}
										</Select>
									</Form.Item>
									{editingUser && (
										<Form.Item
											name="is_active"
											label="Status"
											valuePropName="checked"
										>
											<Switch
												checkedChildren="Active"
												unCheckedChildren="Disabled"
											/>
										</Form.Item>
									)}
								</Form>
							),
						},
						{
							key: "permissions",
							label: "Resource Permissions",
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
				<p>No resource permissions</p>
				<Button size="small" onClick={onGrant}>
					Grant Permission
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
					{ title: "Resource Type", dataIndex: "resource_type", width: 90 },
					{ title: "Resource ID", dataIndex: "resource_id", ellipsis: true },
					{ title: "Permission", dataIndex: "permission", width: 90 },
					{
						title: "Granted At",
						dataIndex: "created_at",
						width: 130,
						render: (value: string) =>
							new Date(value).toLocaleDateString("zh-CN"),
					},
					{
						title: "Actions",
						width: 90,
						render: (_value: unknown, record: ResourcePermission) => (
							<Popconfirm
								title="Revoke this permission?"
								onConfirm={() => revoke.mutate(record.id)}
							>
								<Button size="small" danger loading={revoke.isPending}>
									Revoke
								</Button>
							</Popconfirm>
						),
					},
				]}
			/>
			<Button style={{ marginTop: 12 }} size="small" onClick={onGrant}>
				Grant Permission
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
		message.success(`Granted ${result.granted} permissions`);
		setRawResourceIds("");
		setPermission(undefined);
		onClose();
	};

	return (
		<Modal
			title="Grant Resource Permission"
			open={open}
			onOk={handleSubmit}
			onCancel={onClose}
			width={480}
			okText="Confirm Grant"
			confirmLoading={grant.isPending}
			okButtonProps={{ disabled: !resourceIds.length || !permission }}
		>
			<Form layout="vertical">
				<Form.Item label="Resource Type">
					<Select
						value={resourceType}
						onChange={(value) => {
							setResourceType(value);
							setRawResourceIds("");
						}}
						options={[
							{ label: "Product", value: "product" },
							{ label: "Job", value: "job" },
							{ label: "User", value: "user" },
						]}
					/>
				</Form.Item>
				<Form.Item
					label="Resource ID"
					extra="Enter internal ID; * for all resources of this type. Separate multiple IDs with commas."
				>
					<Input
						value={rawResourceIds}
						placeholder="Separate multiple resource IDs with commas, * for all"
						onChange={(event) => setRawResourceIds(event.target.value)}
					/>
				</Form.Item>
				<Form.Item label="Permission">
					<Select
						value={permission}
						placeholder="Select Permission"
						onChange={setPermission}
						options={[
							{ label: "Read", value: "read" },
							{ label: "Write", value: "write" },
							{ label: "Delete", value: "delete" },
							{ label: "All (*)", value: "*" },
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
	infoForm: ReturnType<typeof Form.useForm>[0];
}

function UserInlineEditor({
	user,
	activeTab,
	onTabChange,
	onClose,
	onInfoSave,
	infoForm,
}: UserInlineEditorProps) {
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
					Editing: {user.username} ({user.email})
				</span>
				<Button size="small" onClick={onClose} style={{ marginLeft: "auto" }}>
					Collapse
				</Button>
			</div>
			<Tabs
				activeKey={activeTab}
				onChange={(key) => onTabChange(key as "info" | "permissions")}
				items={[
					{
						key: "info",
						label: "Basic Info",
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
										label="Username"
										rules={[{ required: true, min: 3 }]}
										style={{ flex: 1, minWidth: 120 }}
									>
										<Input />
									</Form.Item>
									<Form.Item
										name="email"
										label="Email"
										rules={[{ required: true, type: "email" }]}
										style={{ flex: 1, minWidth: 160 }}
									>
										<Input />
									</Form.Item>
									<Form.Item name="role" label="Role" style={{ width: 140 }}>
										<Select>
											<Select.Option value="user">User</Select.Option>
											<Select.Option value="admin">Admin</Select.Option>
											{isSuperAdmin && (
												<Select.Option value="super_admin">
													Super Admin
												</Select.Option>
											)}
										</Select>
									</Form.Item>
									<Form.Item
										name="is_active"
										label="Status"
										valuePropName="checked"
										style={{ width: 100 }}
									>
										<Switch
											checkedChildren="Active"
											unCheckedChildren="Disabled"
										/>
									</Form.Item>
								</div>
								<Space style={{ marginTop: 8 }}>
									<Button type="primary" onClick={onInfoSave}>
										Save
									</Button>
									<Button onClick={onClose}>Cancel</Button>
								</Space>
							</Form>
						),
					},
					{
						key: "permissions",
						label: "Resource Permissions",
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
			message.success("Permission updated");
			setEditingPermId(null);
		} catch (error: unknown) {
			message.error(getAdminErrorMessage(error, "Update failed"));
		}
	};

	if (isLoading) return <Spin />;

	return (
		<div>
			<Form form={editForm}>
				<Table<ResourcePermission>
					dataSource={perms}
					rowKey="id"
					size="small"
					pagination={false}
					columns={[
						{
							title: "Resource Type",
							dataIndex: "resource_type",
							width: 90,
							render: (v: string, record: ResourcePermission) =>
								editingPermId === record.id ? (
									<Form.Item name="resource_type" style={{ margin: 0 }}>
										<Select size="small" style={{ width: 80 }}>
											<Select.Option value="product">Product</Select.Option>
											<Select.Option value="job">Job</Select.Option>
											<Select.Option value="user">User</Select.Option>
										</Select>
									</Form.Item>
								) : (
									v
								),
						},
						{
							title: "Resource ID",
							dataIndex: "resource_id",
							ellipsis: true,
							render: (v: string, record: ResourcePermission) =>
								editingPermId === record.id ? (
									<Form.Item name="resource_id" style={{ margin: 0 }}>
										<Input
											size="small"
											style={{ width: 100 }}
											placeholder="e.g. 13 or *"
										/>
										<div
											style={{
												fontSize: 11,
												color: "var(--color-muted)",
												marginTop: 2,
											}}
										>
											For single grant, enter one ID or *
										</div>
									</Form.Item>
								) : (
									v
								),
						},
						{
							title: "Permission",
							dataIndex: "permission",
							width: 100,
							render: (v: string, record: ResourcePermission) =>
								editingPermId === record.id ? (
									<Form.Item name="permission" style={{ margin: 0 }}>
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
							title: "Granted At",
							dataIndex: "created_at",
							width: 130,
							render: (v: string) => new Date(v).toLocaleDateString("zh-CN"),
						},
						{
							title: "Actions",
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
											Save
										</Button>
										<Button size="small" onClick={cancelEdit}>
											Cancel
										</Button>
									</Space>
								) : (
									<Space size={4}>
										<Button size="small" onClick={() => startEdit(record)}>
											Edit
										</Button>
										<Popconfirm
											title="Revoke this permission?"
											onConfirm={() => revoke.mutate(record.id)}
										>
											<Button size="small" danger loading={revoke.isPending}>
												Revoke
											</Button>
										</Popconfirm>
									</Space>
								),
						},
					]}
				/>
			</Form>
			<Button
				style={{ marginTop: 12 }}
				size="small"
				onClick={() => setGrantModalOpen(true)}
			>
				Grant Permission
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
