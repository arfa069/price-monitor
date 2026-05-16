import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { alertsApi } from "@/api/alerts";
import { adminApi } from "@/api/admin";
import { configApi } from "@/api/config";
import { crawlApi } from "@/api/crawl";
import { jobMatchApi } from "@/api/job_match";
import { jobsApi } from "@/api/jobs";
import { productsApi } from "@/api/products";
import type {
	AlertUpdateRequest,
	CrawlLog,
	JobCrawlLog,
	JobSearchConfigUpdate,
	MatchAnalyzeRequest,
	ResourcePermissionGrant,
	ResourcePermissionUpdate,
	UserResumeCreateRequest,
	UserResumeUpdateRequest,
} from "@/types";

export type CrawlNowMutationResult =
	| { type: "skipped"; reason?: string }
	| { type: "error"; reason?: string }
	| {
			type: "completed";
			total: number;
			success: number;
			errors: number;
			details: unknown[];
	  };

export const useProducts = (params: {
	platform?: string;
	active?: boolean;
	keyword?: string;
	page?: number;
	size?: number;
}) =>
	useQuery({
		queryKey: [
			"products",
			params.platform ?? "",
			params.active ?? "",
			params.keyword ?? "",
			params.page ?? 1,
			params.size ?? 15,
		],
		queryFn: () => productsApi.list(params).then((res) => res.data),
		staleTime: 10_000,
	});

export const useCreateProduct = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: productsApi.create,
		onSuccess: () => qc.invalidateQueries({ queryKey: ["products"] }),
	});
};

export const useUpdateProduct = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({
			id,
			data,
		}: {
			id: number;
			data: Parameters<typeof productsApi.update>[1];
		}) => productsApi.update(id, data),
		onSuccess: () => qc.invalidateQueries({ queryKey: ["products"] }),
	});
};

export const useDeleteProduct = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: productsApi.delete,
		onSuccess: () => qc.invalidateQueries({ queryKey: ["products"] }),
	});
};

export const useBatchCreate = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: productsApi.batchCreate,
		onSuccess: () => qc.invalidateQueries({ queryKey: ["products"] }),
	});
};

export const useBatchDelete = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: productsApi.batchDelete,
		onSuccess: () => qc.invalidateQueries({ queryKey: ["products"] }),
	});
};

export const useBatchUpdate = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ ids, active }: { ids: number[]; active?: boolean }) =>
			productsApi.batchUpdate(ids, active),
		onSuccess: () => qc.invalidateQueries({ queryKey: ["products"] }),
	});
};

export const useConfig = () =>
	useQuery({
		queryKey: ["config"],
		queryFn: () => configApi.get().then((res) => res.data),
	});

export const useUpdateConfig = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: configApi.update,
		onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
	});
};

export const useProductHistory = (id: number, days = 30) =>
	useQuery({
		queryKey: ["product-history", id, days],
		queryFn: () => productsApi.history(id, days).then((res) => res.data),
		enabled: !!id,
	});

export const useCrawlNow = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: async (): Promise<CrawlNowMutationResult> => {
			const response = await crawlApi.crawlNow();
			const data = response.data;
			if (data.status === "skipped")
				return { type: "skipped", reason: data.reason };
			if (data.status === "error")
				return { type: "error", reason: data.reason };

			const taskId = data.task_id!;
			for (let attempts = 0; attempts < 60; attempts += 1) {
				await new Promise((resolve) => setTimeout(resolve, 3000));
				try {
					const statusRes = await crawlApi.getStatus(taskId);
					const status = statusRes.data;
					if (status.status === "completed") {
						const resultRes = await crawlApi.getResult(taskId);
						const result = resultRes.data;
						qc.invalidateQueries({ queryKey: ["crawl-logs"] });
						return {
							type: "completed",
							total: result.total ?? 0,
							success: result.success ?? 0,
							errors: result.errors ?? 0,
							details: result.details ?? [],
						};
					}
					if (status.status === "failed")
						return { type: "error", reason: status.reason };
				} catch (e) {
					console.warn("Polling error:", e);
				}
			}
			return { type: "error", reason: "timeout_polling" };
		},
	});
};

export const useAlerts = (productId?: number) =>
	useQuery({
		queryKey: ["alerts", productId],
		queryFn: () =>
			alertsApi
				.list(productId !== undefined ? { product_id: productId } : undefined)
				.then((res) => res.data),
		enabled: productId !== undefined,
	});

export const useAllAlerts = () =>
	useQuery({
		queryKey: ["alerts", "all"],
		queryFn: () => alertsApi.list().then((res) => res.data),
	});

export const useCreateAlert = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: alertsApi.create,
		onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
	});
};

export const useUpdateAlert = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ id, data }: { id: number; data: AlertUpdateRequest }) =>
			alertsApi.update(id, data),
		onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
	});
};

export const useDeleteAlert = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: alertsApi.delete,
		onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
	});
};

export const useCrawlLogs = (params?: {
	product_id?: number;
	hours?: number;
	limit?: number;
}) =>
	useQuery<CrawlLog[]>({
		queryKey: ["crawl-logs", params],
		queryFn: () => crawlApi.getLogs(params).then((res) => res.data),
		refetchInterval: 60_000,
	});

export const useJobCrawlLogs = (params?: {
	search_config_id?: number;
	status?: string;
	hours?: number;
	limit?: number;
}) =>
	useQuery<JobCrawlLog[]>({
		queryKey: ["job-crawl-logs", params],
		queryFn: () => jobsApi.getCrawlLogs(params).then((res) => res.data),
		refetchInterval: 60_000,
	});

export const useJobConfigs = (active?: boolean) =>
	useQuery({
		queryKey: ["job-configs", active],
		queryFn: () => jobsApi.getConfigs(active).then((res) => res.data),
	});

export const useJobConfig = (id: number) =>
	useQuery({
		queryKey: ["job-config", id],
		queryFn: () => jobsApi.getConfig(id).then((res) => res.data),
		enabled: !!id,
	});

export const useCreateJobConfig = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: jobsApi.createConfig,
		onSuccess: () => qc.invalidateQueries({ queryKey: ["job-configs"] }),
	});
};

export const useUpdateJobConfig = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ id, data }: { id: number; data: JobSearchConfigUpdate }) =>
			jobsApi.updateConfig(id, data),
		onSuccess: () => qc.invalidateQueries({ queryKey: ["job-configs"] }),
	});
};

export const useDeleteJobConfig = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: jobsApi.deleteConfig,
		onSuccess: () => qc.invalidateQueries({ queryKey: ["job-configs"] }),
	});
};

export const useJobs = (params?: {
	search_config_id?: number;
	keyword?: string;
	company?: string;
	salary_min?: number;
	salary_max?: number;
	location?: string;
	is_active?: boolean;
	sort_by?: string;
	sort_order?: string;
	page?: number;
	page_size?: number;
}) =>
	useQuery({
		queryKey: ["jobs", params],
		queryFn: () => jobsApi.getJobs(params).then((res) => res.data),
		staleTime: 30_000,
	});

export const useJob = (jobId: string) =>
	useQuery({
		queryKey: ["job", jobId],
		queryFn: () => jobsApi.getJob(jobId).then((res) => res.data),
		enabled: !!jobId,
	});

export const useCrawlAllJobs = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: async (): Promise<{
			type: "completed" | "error";
			total?: number;
			success?: number;
			errors?: number;
			reason?: string;
		}> => {
			const response = await jobsApi.crawlAll();
			const taskId = response.data.task_id;
			for (let attempt = 0; attempt < 60; attempt += 1) {
				await new Promise((resolve) => setTimeout(resolve, 3000));
				try {
					const statusRes = await jobsApi.getCrawlStatus(taskId);
					const s = statusRes.data;
					if (s.status === "completed") {
						const resultRes = await jobsApi.getCrawlResult(taskId);
						const r = resultRes.data;
						qc.invalidateQueries({ queryKey: ["jobs"] });
						qc.invalidateQueries({ queryKey: ["job-configs"] });
						return {
							type: "completed",
							total: r.total,
							success: r.success,
							errors: r.errors,
						};
					}
					if (s.status === "failed")
						return { type: "error", reason: "crawl task failed" };
				} catch (e) {
					console.warn("Job crawl polling error:", e);
				}
			}
			return { type: "error", reason: "timeout_polling" };
		},
	});
};

export const useCrawlSingleJob = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: async (
			configId: number,
		): Promise<{
			type: "completed" | "error";
			total?: number;
			success?: number;
			errors?: number;
			reason?: string;
		}> => {
			const response = await jobsApi.crawlSingle(configId);
			const taskId = response.data.task_id;
			for (let attempt = 0; attempt < 60; attempt += 1) {
				await new Promise((resolve) => setTimeout(resolve, 3000));
				try {
					const statusRes = await jobsApi.getCrawlStatus(taskId);
					const s = statusRes.data;
					if (s.status === "completed") {
						const resultRes = await jobsApi.getCrawlResult(taskId);
						const r = resultRes.data;
						qc.invalidateQueries({ queryKey: ["jobs"] });
						qc.invalidateQueries({ queryKey: ["job-configs"] });
						return {
							type: "completed",
							total: r.total,
							success: r.success,
							errors: r.errors,
						};
					}
					if (s.status === "failed")
						return { type: "error", reason: "crawl task failed" };
				} catch (e) {
					console.warn("Job crawl polling error:", e);
				}
			}
			return { type: "error", reason: "timeout_polling" };
		},
	});
};

export const useResumes = () =>
	useQuery({
		queryKey: ["resumes"],
		queryFn: () => jobMatchApi.listResumes().then((res) => res.data),
	});

export const useCreateResume = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (data: UserResumeCreateRequest) =>
			jobMatchApi.createResume(data),
		onSuccess: () => qc.invalidateQueries({ queryKey: ["resumes"] }),
	});
};

export const useUpdateResume = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ id, data }: { id: number; data: UserResumeUpdateRequest }) =>
			jobMatchApi.updateResume(id, data),
		onSuccess: () => qc.invalidateQueries({ queryKey: ["resumes"] }),
	});
};

export const useDeleteResume = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (id: number) => jobMatchApi.deleteResume(id),
		onSuccess: () => qc.invalidateQueries({ queryKey: ["resumes"] }),
	});
};

export const useMatchResults = (params?: {
	resume_id?: number;
	job_id?: number;
	min_score?: number;
	page?: number;
	page_size?: number;
}) =>
	useQuery({
		queryKey: ["match-results", params],
		queryFn: () => jobMatchApi.listMatchResults(params).then((res) => res.data),
	});

export const useTriggerMatch = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (data: MatchAnalyzeRequest) =>
			jobMatchApi.triggerMatchAsync(data).then(
				(resp) =>
					resp.data as {
						status: string;
						task_id: string | null;
						total: number;
					},
			),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: ["match-results"] });
			qc.invalidateQueries({ queryKey: ["jobs"] });
		},
	});
};

export const useResourcePermissions = (params: {
	user_id?: number;
	resource_type?: string;
	page?: number;
	page_size?: number;
}) =>
	useQuery({
		queryKey: ["resource-permissions", params],
		queryFn: () => adminApi.listResourcePermissions(params),
	});

export const useGrantResourcePermission = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (grant: ResourcePermissionGrant) =>
			adminApi.grantResourcePermission(grant),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: ["resource-permissions"] });
		},
	});
};

export const useRevokeResourcePermission = () => {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (id: number) => adminApi.revokeResourcePermission(id),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: ["resource-permissions"] });
		},
	});
};

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
