import { useMemo } from "react";
import { Button, Card, Input, Select, Space, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import type { Job } from "@/types";

interface JobListProps {
	jobs?: Job[];
	total: number;
	isLoading?: boolean;
	onViewDetail: (job: Job) => void;
	onCrawlAll?: () => Promise<void>;
	crawlAllLoading?: boolean;
	filters: { keyword?: string; is_active?: boolean };
	onFilterChange: (filters: { keyword?: string; is_active?: boolean }) => void;
	page: number;
	pageSize: number;
	onPageChange: (page: number) => void;
	onPageSizeChange?: (pageSize: number) => void;
	matchScores?: Record<number, number>;
}

type StatusFilterValue = "all" | "active" | "inactive";

export default function JobList({
	jobs,
	total,
	isLoading,
	onViewDetail,
	onCrawlAll,
	crawlAllLoading,
	filters,
	onFilterChange,
	page,
	pageSize,
	onPageChange,
	onPageSizeChange,
	matchScores,
}: JobListProps) {
	const statusValue: StatusFilterValue =
		filters.is_active === undefined
			? "all"
			: filters.is_active
				? "active"
				: "inactive";

	const columns: ColumnsType<Job> = useMemo(
		() => [
			{ title: "ID", dataIndex: "id", width: 80 },
			{
				title: "Match",
				key: "match_score",
				width: 90,
				render: (_, record) => {
					const score = matchScores?.[record.id];
					if (!score) return null;
					return (
						<Tag
							color={score >= 80 ? "green" : score >= 60 ? "orange" : "default"}
						>
							{score}
						</Tag>
					);
				},
			},
			{
				title: "Job Title",
				dataIndex: "title",
				ellipsis: true,
				render: (title: string, record) =>
					record.url ? (
						<a
							href={record.url}
							target="_blank"
							rel="noopener noreferrer"
							title="Open job in new tab"
						>
							{title}
						</a>
					) : (
						title
					),
			},
			{ title: "Company", dataIndex: "company", width: 200, ellipsis: true },
			{ title: "Salary", dataIndex: "salary", width: 120 },
			{ title: "Location", dataIndex: "location", width: 120, ellipsis: true },
			{
				title: "Status",
				dataIndex: "is_active",
				width: 90,
				render: (active: boolean) => (
					<Tag color={active ? "success" : "default"}>
						{active ? "Active" : "Inactive"}
					</Tag>
				),
			},
			{
				title: "Last Updated",
				dataIndex: "last_updated_at",
				width: 180,
				render: (value: string) => new Date(value).toLocaleString("en-US"),
			},
			{
				title: "Actions",
				key: "action",
				width: 100,
				render: (_, record) => (
					<Button
						size="small"
						onClick={(e) => {
							e.stopPropagation();
							onViewDetail(record);
						}}
					>
						View
					</Button>
				),
			},
		],
		[matchScores, onViewDetail],
	);

	return (
		<Card style={{ marginTop: 16 }} title="Job List">
			<Space style={{ marginBottom: 12 }} wrap>
				<Input
					allowClear
					suffix={
						<SearchOutlined
							style={{ fontSize: 14, color: "var(--color-muted)" }}
						/>
					}
					placeholder="Search jobs or companies"
					value={filters.keyword}
					autoComplete="off"
					onChange={(e) =>
						onFilterChange({ ...filters, keyword: e.target.value })
					}
					style={{
						width: 320,
						fontFamily: "var(--font-body)",
						borderRadius: "var(--radius-pill)",
					}}
				/>
				<Select
					style={{ width: 140, fontFamily: "var(--font-body)" }}
					className="fg-select"
					value={statusValue}
					onChange={(value: StatusFilterValue) =>
						onFilterChange({
							...filters,
							is_active: value === "all" ? undefined : value === "active",
						})
					}
					options={[
						{ label: "All Statuses", value: "all" },
						{ label: "Active", value: "active" },
						{ label: "Inactive", value: "inactive" },
					]}
				/>
				{onCrawlAll && (
					<Button
						icon={<ReloadOutlined />}
						loading={crawlAllLoading}
						onClick={onCrawlAll}
					>
						Crawl All
					</Button>
				)}
			</Space>

			<Table
				rowKey="id"
				loading={isLoading}
				columns={columns}
				dataSource={jobs || []}
				scroll={{ x: "max-content" }}
				pagination={{
					current: page,
					pageSize,
					total,
					showSizeChanger: true,
					onChange: (next, nextSize) => {
						onPageChange(next);
						if (nextSize && nextSize !== pageSize) onPageSizeChange?.(nextSize);
					},
				}}
			/>
		</Card>
	);
}
