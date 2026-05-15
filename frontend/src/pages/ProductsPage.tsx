import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
	Alert,
	App,
	Button,
	Col,
	Input,
	Popconfirm,
	Row,
	Select,
	Space,
	Table,
	Tag,
	Tooltip,
	notification,
} from "antd";
import {
	DeleteOutlined,
	EditOutlined,
	ExportOutlined,
	HistoryOutlined,
	ImportOutlined,
	LineChartOutlined,
	PlusOutlined,
	ReloadOutlined,
	RocketOutlined,
	SearchOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import BatchImportModal from "@/components/BatchImportModal";
import PriceTrendModal from "@/components/PriceTrendModal";
import ProductFormModal, {
	type ProductFormSubmitValues,
} from "@/components/ProductFormModal";
import {
	useAllAlerts,
	useBatchCreate,
	useBatchDelete,
	type CrawlNowMutationResult,
	useCreateAlert,
	useCreateProduct,
	useCrawlLogs,
	useCrawlNow,
	useDeleteProduct,
	useProducts,
	useUpdateAlert,
	useUpdateProduct,
} from "@/hooks/api";
import { useAuth } from "@/contexts/AuthContext";
import { useStaggerAnimation } from "@/hooks/useStaggerAnimation";
import type {
	BatchCreateItem,
	BatchImportRow,
	BatchOperationResult,
	CrawlLog,
	Product,
} from "@/types";

const PLATFORM_BADGE_CLASS: Record<string, string> = {
	taobao: "platform-badge--taobao",
	jd: "platform-badge--jd",
	amazon: "platform-badge--amazon",
};

const PLATFORM_LABEL: Record<string, string> = {
	taobao: "Taobao",
	jd: "JD",
	amazon: "Amazon",
};

function PlatformBadge({ value }: { value: string | null | undefined }) {
	if (!value) return <Tag>-</Tag>;
	const cls = PLATFORM_BADGE_CLASS[value];
	const label = PLATFORM_LABEL[value] ?? value;
	if (!cls) return <Tag>{label}</Tag>;
	return <span className={`platform-badge ${cls}`}>{label}</span>;
}

type AlertInfo = {
	id: number;
	threshold_percent: number;
	active: boolean;
};

const getErrorMessage = (error: unknown) =>
	error instanceof Error ? error.message : "Unknown error";

export default function ProductsPage() {
	const { user } = useAuth();
	const stagger = useStaggerAnimation(0.05, 0.05);
	const canCrawl = user?.role !== "admin";
	const message = App.useApp().message;
	const [page, setPage] = useState(1);
	const [size, setSize] = useState(15);
	const [platform, setPlatform] = useState<string | undefined>();
	const [active, setActive] = useState<boolean | undefined>();
	const [keyword, setKeyword] = useState("");
	const [debouncedKeyword, setDebouncedKeyword] = useState("");
	const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
	const [createFormOpen, setCreateFormOpen] = useState(false);
	const [editModal, setEditModal] = useState<{
		open: boolean;
		record?: Product;
	}>({
		open: false,
	});
	const [batchImportOpen, setBatchImportOpen] = useState(false);
	const [trendModal, setTrendModal] = useState<{
		open: boolean;
		product?: Product;
	}>({
		open: false,
	});

	useEffect(() => {
		const timer = setTimeout(() => setDebouncedKeyword(keyword), 400);
		return () => clearTimeout(timer);
	}, [keyword]);

	const { data, isLoading, isError, refetch } = useProducts({
		page,
		size,
		platform,
		active,
		keyword: debouncedKeyword || undefined,
	});
	const createMutation = useCreateProduct();
	const updateMutation = useUpdateProduct();
	const deleteMutation = useDeleteProduct();
	const batchCreate = useBatchCreate();
	const batchDelete = useBatchDelete();
	const crawlNow = useCrawlNow();
	const createAlertMutation = useCreateAlert();
	const updateAlertMutation = useUpdateAlert();
	const {
		data: crawlLogs,
		isLoading: logsLoading,
		refetch: refetchLogs,
	} = useCrawlLogs({ limit: 10 });
	const { data: alertsData } = useAllAlerts();
	const productItems = data?.items ?? [];
	const crawlLogItems = crawlLogs ?? [];

	const alertMap = useMemo(() => {
		const map = new Map<number, AlertInfo>();
		alertsData?.forEach((alert) => {
			map.set(alert.product_id, {
				id: alert.id,
				threshold_percent: alert.threshold_percent || 0,
				active: alert.active,
			});
		});
		return map;
	}, [alertsData]);

	const showBatchResult = (action: string, results: BatchOperationResult[]) => {
		const successCount = results.filter((item) => item.success).length;
		const failedItems = results.filter((item) => !item.success);

		message.success(`${action}: ${successCount} succeeded`);
		if (failedItems.length > 0) {
			notification.error({
				message: `${action}: ${failedItems.length} failed`,
				description: failedItems
					.map((item) => `${item.url || `ID:${item.id}`} - ${item.error}`)
					.join("\n"),
				duration: 0,
			});
		}
	};

	const handleDelete = (id: number) => {
		const shouldGoPrev = page > 1 && productItems.length === 1;
		deleteMutation.mutate(id, {
			onSuccess: () => {
				if (shouldGoPrev) {
					setPage((current) => Math.max(1, current - 1));
				}
				message.success("Deleted successfully");
			},
			onError: () => message.error("Delete failed"),
		});
	};

	const handleBatchDelete = () => {
		if (selectedRowKeys.length === 0) return;
		const currentPageCount = productItems.length;
		const shouldGoPrev =
			page > 1 &&
			currentPageCount > 0 &&
			selectedRowKeys.length >= currentPageCount;

		batchDelete.mutate(selectedRowKeys as number[], {
			onSuccess: (response) => {
				if (shouldGoPrev) {
					setPage((current) => Math.max(1, current - 1));
				}
				showBatchResult("Batch Delete", response.data);
				setSelectedRowKeys([]);
			},
			onError: (error) =>
				message.error(`Batch operation failed: ${getErrorMessage(error)}`),
		});
	};

	const handleFormSubmit = async (values: ProductFormSubmitValues) => {
		const { alert, ...productValues } = values;

		try {
			let productId: number;

			if (editModal.record) {
				await updateMutation.mutateAsync({
					id: editModal.record.id,
					data: productValues,
				});
				productId = editModal.record.id;
			} else {
				if (!productValues.platform) {
					throw new Error("Please select a platform");
				}
				const result = await createMutation.mutateAsync({
					...productValues,
					platform: productValues.platform,
				});
				productId = result.data.id;
			}

			if (alert.enabled) {
				if (alert.existingId) {
					await updateAlertMutation.mutateAsync({
						id: alert.existingId,
						data: { threshold_percent: alert.threshold, active: true },
					});
				} else {
					await createAlertMutation.mutateAsync({
						product_id: productId,
						threshold_percent: alert.threshold,
						active: true,
					});
				}
			} else if (alert.existingId) {
				await updateAlertMutation.mutateAsync({
					id: alert.existingId,
					data: { active: false },
				});
			}

			message.success(
				editModal.record ? "Updated successfully" : "Added successfully",
			);
			setEditModal({ open: false });
			setCreateFormOpen(false);
		} catch (error) {
			message.error(
				`${editModal.record ? "Update" : "Add"} failed: ${getErrorMessage(error)}`,
			);
		}
	};

	const handleBatchImport = (items: BatchImportRow[]) => {
		const payload: BatchCreateItem[] = items.map((item) => ({
			url: item.url,
			platform: item.platform as BatchCreateItem["platform"],
			title: item.title,
		}));
		batchCreate.mutate(payload, {
			onSuccess: (response) => {
				showBatchResult("Batch Import", response.data);
				setBatchImportOpen(false);
			},
			onError: (error) =>
				message.error(`Import failed: ${getErrorMessage(error)}`),
		});
	};

	const handleCrawlNow = () => {
		message.loading({
			content: "Starting crawl task...",
			key: "crawl",
			duration: 0,
		});
		crawlNow.mutate(undefined, {
			onSuccess: (result: CrawlNowMutationResult) => {
				if (result.type === "skipped") {
					message.warning({
						content: "No active products to crawl",
						key: "crawl",
					});
					return;
				}
				if (result.type === "error") {
					message.error({
						content: `Crawl failed: ${result.reason || "Unknown error"}`,
						key: "crawl",
					});
					return;
				}
				message.success({
					content: `Crawl completed: ${result.success} succeeded, ${result.errors} failed`,
					key: "crawl",
				});
			},
			onError: (error) => {
				message.error({
					content: `Crawl request failed: ${getErrorMessage(error)}`,
					key: "crawl",
				});
			},
		});
	};

	const columns: ColumnsType<Product> = [
		{ title: "ID", dataIndex: "id", width: 60 },
		{
			title: "Platform",
			dataIndex: "platform",
			width: 90,
			render: (value: string) => <PlatformBadge value={value} />,
		},
		{ title: "Title", dataIndex: "title", ellipsis: true },
		{
			title: "Status",
			dataIndex: "active",
			width: 80,
			render: (value: boolean) =>
				value ? (
					<Tag color="success">Active</Tag>
				) : (
					<Tag color="error">Inactive</Tag>
				),
		},
		{
			title: "Created",
			dataIndex: "created_at",
			width: 180,
			render: (value: string) =>
				new Intl.DateTimeFormat("en-US", {
					dateStyle: "medium",
					timeStyle: "short",
				}).format(new Date(value)),
		},
		{
			title: "Alert",
			key: "alert",
			width: 80,
			render: (_value: unknown, record: Product) => {
				const alert = alertMap.get(record.id);
				if (!alert) return <Tag>Not set</Tag>;
				return alert.active ? (
					<Tag color="orange">{String(alert.threshold_percent)}%</Tag>
				) : (
					<Tag color="default">Inactive</Tag>
				);
			},
		},
		{
			title: "Actions",
			key: "action",
			width: 380,
			render: (_value: unknown, record: Product) => (
				<Space size={8}>
					<Button
						size="small"
						icon={<ExportOutlined />}
						aria-label="Open product link in new window"
						onClick={() => window.open(record.url, "_blank")}
					>
						View
					</Button>
					<Button
						size="small"
						icon={<LineChartOutlined />}
						onClick={() => setTrendModal({ open: true, product: record })}
					>
						Trend
					</Button>
					<Button
						size="small"
						icon={<EditOutlined />}
						onClick={() => setEditModal({ open: true, record })}
					>
						Edit
					</Button>
					<Popconfirm
						title="Delete this product?"
						onConfirm={() => handleDelete(record.id)}
					>
						<Button size="small" danger icon={<DeleteOutlined />}>
							Delete
						</Button>
					</Popconfirm>
				</Space>
			),
		},
	];

	const crawlLogColumns: ColumnsType<CrawlLog> = [
		{
			title: "Time",
			dataIndex: "timestamp",
			width: 160,
			render: (value: string) =>
				new Intl.DateTimeFormat("en-US", {
					dateStyle: "medium",
					timeStyle: "short",
				}).format(new Date(value)),
		},
		{
			title: "Platform",
			dataIndex: "platform",
			width: 80,
			render: (value: string | null) => <PlatformBadge value={value} />,
		},
		{
			title: "Status",
			dataIndex: "status",
			width: 100,
			render: (value: string | null) => {
				const configMap: Record<string, { color: string; text: string }> = {
					SUCCESS: { color: "success", text: "Success" },
					ERROR: { color: "error", text: "Failed" },
					SKIPPED: { color: "default", text: "Skipped" },
				};
				const config = value ? configMap[value] : undefined;
				return (
					<Tag color={config?.color || "default"}>
						{config?.text || value || "-"}
					</Tag>
				);
			},
		},
		{
			title: "Price",
			dataIndex: "price",
			width: 100,
			render: (value: number | null) => (value ? `¥${value}` : "-"),
		},
		{
			title: "Error",
			dataIndex: "error_message",
			ellipsis: true,
			render: (value: string | null) =>
				value ? (
					<Tooltip title={value}>
						<span style={{ color: "var(--color-error)" }}>{value}</span>
					</Tooltip>
				) : (
					"-"
				),
		},
	];

	return (
		<div className="page-root">
			{/* Page header — lime color block */}
			<div className="page-header bg-lime">
				<div className="page-header-inner">
					<div>
						<p className="page-eyebrow">Data Management</p>
						<h1 className="page-title">Product Management</h1>
						<p className="page-subtitle">
							Track price changes for Taobao, JD, and Amazon products
						</p>
					</div>
				</div>
			</div>

			<motion.div
				variants={stagger.container}
				initial="hidden"
				animate="show"
				style={{ width: "100%" }}
			>
				<Space orientation="vertical" size="middle" style={{ width: "100%" }}>
					{/* Toolbar card */}
					<motion.div
						variants={stagger.item}
						className="fg-card fg-card-toolbar"
					>
						<Row gutter={[12, 12]} align="middle">
							<Col flex="auto">
								<Space wrap size={8}>
									<Button
										icon={<ImportOutlined style={{ fontSize: 14 }} />}
										onClick={() => setBatchImportOpen(true)}
										className="fg-btn-secondary"
									>
										Batch Import
									</Button>
									<Popconfirm
										title="Delete selected items?"
										onConfirm={handleBatchDelete}
										disabled={selectedRowKeys.length === 0}
									>
										<Button
											danger
											icon={<DeleteOutlined style={{ fontSize: 14 }} />}
											disabled={selectedRowKeys.length === 0}
											className="fg-btn-danger"
										>
											Batch Delete
										</Button>
									</Popconfirm>
									<Button
										icon={<PlusOutlined style={{ fontSize: 14 }} />}
										onClick={() => setCreateFormOpen(true)}
										className="fg-btn-secondary"
									>
										Add Product
									</Button>
									{canCrawl && (
										<Button
											icon={<RocketOutlined style={{ fontSize: 14 }} />}
											onClick={handleCrawlNow}
											loading={crawlNow.isPending}
											className="fg-btn-secondary"
										>
											Crawl Now
										</Button>
									)}
								</Space>
							</Col>
							<Col>
								<Space size={8}>
									<Input
										placeholder="Search title or URL"
										autoComplete="off"
										suffix={
											<SearchOutlined
												style={{
													color: "var(--color-muted)",
													fontSize: 16,
												}}
											/>
										}
										onChange={(e) => setKeyword(e.target.value)}
										style={{
											width: 260,
										}}
									/>
									<Select
										placeholder="Platform"
										allowClear
										style={{ width: 110, fontFamily: "var(--font-body)" }}
										options={[
											{ label: "Taobao", value: "taobao" },
											{ label: "JD", value: "jd" },
											{ label: "Amazon", value: "amazon" },
										]}
										onChange={(value) => setPlatform(value)}
										className="fg-select"
									/>
									<Select
										placeholder="Status"
										allowClear
										style={{ width: 95, fontFamily: "var(--font-body)" }}
										options={[
											{ label: "Active", value: true },
											{ label: "Inactive", value: false },
										]}
										onChange={(value) => setActive(value)}
										className="fg-select"
									/>
								</Space>
							</Col>
						</Row>
					</motion.div>

					{isError && (
						<Alert
							type="error"
							message="Load Failed"
							description="Unable to fetch product list. Please check your network or try again."
							action={
								<Button size="small" onClick={() => refetch()}>
									Retry
								</Button>
							}
							style={{ marginBottom: 16 }}
						/>
					)}

					<motion.div variants={stagger.item}>
						<Table<Product>
							rowKey="id"
							columns={columns}
							dataSource={productItems}
							loading={isLoading}
							scroll={{ x: "max-content" }}
							rowSelection={{
								selectedRowKeys,
								onChange: (keys) => setSelectedRowKeys(keys),
							}}
							pagination={{
								current: page,
								pageSize: size,
								total: data?.total ?? 0,
								showSizeChanger: true,
								showTotal: (totalCount) => `Total ${totalCount} items`,
								onChange: (nextPage, nextSize) => {
									setPage(nextPage);
									if (nextSize) setSize(nextSize);
								},
							}}
							locale={{
								emptyText: (
									<div style={{ padding: "40px 0", textAlign: "center" }}>
										<p
											style={{
												fontFamily: "var(--font-body)",
												fontSize: 16,
												fontWeight: 330,
												color: "var(--color-muted)",
												marginBottom: 16,
											}}
										>
											No products yet. Click to add your first one.
										</p>
										<Button
											type="primary"
											icon={<PlusOutlined style={{ fontSize: 14 }} />}
											onClick={() => setCreateFormOpen(true)}
											className="fg-btn-primary"
										>
											Add First Product
										</Button>
									</div>
								),
							}}
						/>
					</motion.div>

					{selectedRowKeys.length > 0 && (
						<div style={{ color: "var(--color-muted)", fontSize: 12 }}>
							Selected {selectedRowKeys.length} items (current page only)
						</div>
					)}
				</Space>
			</motion.div>

			<div className="fg-card" style={{ marginTop: 16 }}>
				<div className="fg-card-header">
					<Space>
						<HistoryOutlined style={{ fontSize: 14 }} />
						<span
							style={{
								fontFamily: "var(--font-body)",
								fontSize: 15,
								fontWeight: 480,
								color: "var(--color-ink)",
							}}
						>
							Recent Crawl Logs
						</span>
						{crawlLogItems.length > 0 && (
							<span
								style={{
									fontFamily: "'JetBrains Mono', monospace",
									fontSize: 11,
									color: "var(--color-muted)",
									letterSpacing: "0.4px",
								}}
							>
								({crawlLogItems.length} items)
							</span>
						)}
					</Space>
					<Button
						size="small"
						icon={<ReloadOutlined style={{ fontSize: 13 }} />}
						onClick={() => refetchLogs()}
						loading={logsLoading}
						className="fg-btn-secondary fg-btn-sm"
					>
						Refresh
					</Button>
				</div>
				{logsLoading && crawlLogItems.length === 0 ? (
					<div
						style={{
							padding: 20,
							textAlign: "center",
							fontFamily: "var(--font-body)",
							fontSize: 14,
							color: "var(--color-muted)",
						}}
					>
						Loading...
					</div>
				) : crawlLogItems.length > 0 ? (
					<Table
						size="small"
						dataSource={crawlLogItems}
						rowKey="id"
						pagination={false}
						scroll={{ x: 800 }}
						columns={crawlLogColumns}
					/>
				) : (
					<div
						style={{
							padding: 20,
							textAlign: "center",
							fontFamily: "var(--font-body)",
							fontSize: 14,
							color: "var(--color-muted)",
						}}
					>
						No crawl records
					</div>
				)}
			</div>

			<ProductFormModal
				key={editModal.record?.id ?? "new"}
				open={createFormOpen || editModal.open}
				record={editModal.record}
				existingAlert={
					editModal.record ? alertMap.get(editModal.record.id) : undefined
				}
				onCancel={() => {
					setCreateFormOpen(false);
					setEditModal({ open: false });
				}}
				onSubmit={handleFormSubmit}
				confirmLoading={createMutation.isPending || updateMutation.isPending}
			/>

			<BatchImportModal
				open={batchImportOpen}
				onCancel={() => setBatchImportOpen(false)}
				onImport={handleBatchImport}
				confirmLoading={batchCreate.isPending}
				existingUrls={productItems.map((product) => product.url)}
			/>

			<PriceTrendModal
				open={trendModal.open}
				product={trendModal.product}
				onCancel={() => setTrendModal({ open: false })}
			/>
		</div>
	);
}
