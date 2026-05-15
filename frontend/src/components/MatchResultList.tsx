import { useMemo, useRef, useState } from "react";
import {
	Button,
	Card,
	Empty,
	Select,
	Space,
	Spin,
	Table,
	Tag,
	App,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useMatchResults, useResumes, useTriggerMatch } from "@/hooks/api";
import { jobMatchApi } from "@/api/job_match";
import type { MatchResultWithJob } from "@/types";

export default function MatchResultList() {
	const message = App.useApp().message;
	const [resumeId, setResumeId] = useState<number | undefined>();
	const [minScore, setMinScore] = useState<number>(70);
	const [page, setPage] = useState(1);
	const pageSize = 20;
	const [taskProgress, setTaskProgress] = useState<{
		total: number;
		success: number;
	} | null>(null);
	const pollRef = useRef<ReturnType<typeof setInterval>>();
	const currentTaskId = useRef<string | null>(null);

	const { data: resumes } = useResumes();
	const {
		data: matchResults,
		isLoading,
		refetch,
	} = useMatchResults({
		resume_id: resumeId,
		min_score: minScore,
		page,
		page_size: pageSize,
	});
	const triggerMatch = useTriggerMatch();

	const handleTriggerMatch = async () => {
		if (!resumeId) {
			message.warning("Please select a resume first");
			return;
		}
		// 清除之前的轮询
		if (pollRef.current) clearInterval(pollRef.current);
		setTaskProgress(null);

		try {
			const result = await triggerMatch.mutateAsync({ resume_id: resumeId });
			const { task_id, total } = result;

			if (!task_id || total === 0) {
				message.success("All jobs are already up to date.");
				refetch();
				return;
			}

			currentTaskId.current = task_id;
			setTaskProgress({ total, success: 0 });
			message.success("Match analysis started.");

			// 轮询进度
			pollRef.current = setInterval(async () => {
				try {
					const statusRes = await jobMatchApi.getMatchTaskStatus(task_id);
					const s = statusRes.data;
					// 跳过旧任务的回调
					if (currentTaskId.current !== task_id) return;

					setTaskProgress({ total: s.total, success: s.success });
					refetch();

					if (s.status === "completed" || s.status === "failed") {
						currentTaskId.current = null;
						if (pollRef.current) clearInterval(pollRef.current);
						pollRef.current = undefined;
						if (s.status === "completed") {
							message.success({
								content: `Match analysis completed for ${s.total} jobs.`,
								duration: 10,
							});
							setTimeout(() => setTaskProgress(null), 10000);
						} else {
							message.error("Match analysis failed.");
							setTaskProgress(null);
						}
					}
				} catch {
					// polling error, retry next interval
				}
			}, 5000);
		} catch (err) {
			console.error("Match analysis failed:", err);
			message.error("Match analysis failed to start");
		}
	};

	const columns: ColumnsType<MatchResultWithJob> = useMemo(
		() => [
			{
				title: "Match Score",
				dataIndex: "match_score",
				width: 90,
				render: (score: number) => (
					<Tag
						color={score >= 80 ? "green" : score >= 60 ? "orange" : "default"}
					>
						{score}
					</Tag>
				),
			},
			{
				title: "Recommendation",
				dataIndex: "apply_recommendation",
				width: 110,
				render: (value: string | null) => {
					const color =
						value === "Strongly Recommended"
							? "green"
							: value === "Consider"
								? "blue"
								: "default";
					return <Tag color={color}>{value || "-"}</Tag>;
				},
			},
			{ title: "Job Title", dataIndex: "job_title", ellipsis: true },
			{
				title: "Company",
				dataIndex: "job_company",
				width: 160,
				ellipsis: true,
			},
			{ title: "Salary", dataIndex: "job_salary", width: 120 },
			{
				title: "Reason",
				dataIndex: "match_reason",
				ellipsis: true,
				render: (value: string | null) => value || "-",
			},
			{
				title: "Analysis Time",
				dataIndex: "updated_at",
				width: 180,
				render: (value: string) =>
					new Intl.DateTimeFormat("en-US", {
						dateStyle: "medium",
						timeStyle: "short",
					}).format(new Date(value)),
			},
			{
				title: "Link",
				key: "job_url",
				width: 60,
				render: (_: unknown, record: MatchResultWithJob) =>
					record.job_url ? (
						<a href={record.job_url} target="_blank" rel="noopener noreferrer">
							View
						</a>
					) : null,
			},
		],
		[],
	);

	return (
		<Card
			title={
				<Space>
					<span>Match Results</span>
					{taskProgress && (
						<span
							style={{
								fontSize: 12,
								color: "var(--color-muted)",
							}}
						>
							Completed: {taskProgress.success}/{taskProgress.total}
						</span>
					)}
				</Space>
			}
		>
			<Space style={{ marginBottom: 16 }} wrap>
				<Select
					style={{ width: 220 }}
					placeholder="Select Resume"
					allowClear
					value={resumeId}
					onChange={(value) => {
						setResumeId(value);
						setPage(1);
					}}
					options={resumes?.map((resume) => ({
						label: resume.name,
						value: resume.id,
					}))}
				/>
				<Select
					style={{ width: 160 }}
					value={minScore}
					onChange={(value) => {
						setMinScore(value);
						setPage(1);
					}}
					options={[
						{ label: "All Scores", value: 0 },
						{ label: "70+", value: 70 },
						{ label: "80+", value: 80 },
						{ label: "90+", value: 90 },
					]}
				/>
				<Button
					type="primary"
					disabled={!resumeId}
					loading={triggerMatch.isPending}
					onClick={handleTriggerMatch}
				>
					Re-analyze
				</Button>
			</Space>

			{isLoading ? (
				<div style={{ textAlign: "center", padding: 24 }}>
					<Spin />
				</div>
			) : !matchResults?.items.length ? (
				<Empty description="No Match Results" />
			) : (
				<Table
					rowKey="id"
					columns={columns}
					dataSource={matchResults.items}
					pagination={{
						current: page,
						pageSize,
						total: matchResults.total,
						showSizeChanger: false,
						onChange: setPage,
					}}
				/>
			)}
		</Card>
	);
}
