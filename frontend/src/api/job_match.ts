import api from './client'
import type {
  MatchAnalyzeRequest,
  MatchAnalyzeResponse,
  MatchResultListResponse,
  UserResume,
  UserResumeCreateRequest,
  UserResumeUpdateRequest,
} from '@/types'

export const jobMatchApi = {
  listResumes: () => api.get<UserResume[]>('/jobs/resumes'),
  createResume: (data: UserResumeCreateRequest) => api.post<UserResume>('/jobs/resumes', data),
  updateResume: (id: number, data: UserResumeUpdateRequest) =>
    api.patch<UserResume>(`/jobs/resumes/${id}`, data),
  deleteResume: (id: number) => api.delete(`/jobs/resumes/${id}`),
  listMatchResults: (params?: {
    resume_id?: number
    job_id?: number
    min_score?: number
    page?: number
    page_size?: number
  }) => api.get<MatchResultListResponse>('/jobs/match-results', { params }),
  triggerMatch: (data: MatchAnalyzeRequest) =>
    api.post<MatchAnalyzeResponse>('/jobs/match-results/analyze', data),
  triggerMatchAsync: (data: MatchAnalyzeRequest) =>
    api.post<{ status: string; task_id: string | null; total: number }>('/jobs/match-results/analyze-async', data),
  getMatchTaskStatus: (taskId: string) =>
    api.get<{ task_id: string; status: string; total: number; success: number; errors: number; reason?: string }>(`/jobs/tasks/${taskId}`),
}
