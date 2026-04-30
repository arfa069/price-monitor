import { useState } from 'react'
import { Card } from 'antd'
import {
  useCrawlAllJobs,
  useCrawlSingleJob,
  useCreateJobConfig,
  useDeleteJobConfig,
  useJobConfigs,
  useJobs,
  useUpdateJobConfig,
} from '@/hooks/api'
import JobConfigList from '@/components/JobConfigList'
import JobDrawer from '@/components/JobDrawer'
import JobList from '@/components/JobList'
import type { Job, JobSearchConfigCreate } from '@/types'

export default function JobsPage() {
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [isActive, setIsActive] = useState<boolean | undefined>(undefined)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)

  const { data: configs, isLoading: configsLoading, refetch: refetchConfigs } = useJobConfigs()
  const createConfig = useCreateJobConfig()
  const updateConfig = useUpdateJobConfig()
  const deleteConfig = useDeleteJobConfig()

  const { data: jobsResp, isLoading: jobsLoading, refetch: refetchJobs } = useJobs({
    keyword: keyword || undefined,
    is_active: isActive,
    page,
    page_size: pageSize,
  })

  const crawlAll = useCrawlAllJobs()
  const crawlSingle = useCrawlSingleJob()

  const handleCreateConfig = async (data: JobSearchConfigCreate) => {
    await createConfig.mutateAsync(data)
    await refetchConfigs()
  }

  const handleUpdateConfig = async (id: number, data: Partial<JobSearchConfigCreate>) => {
    await updateConfig.mutateAsync({ id, data })
    await refetchConfigs()
  }

  const handleDeleteConfig = async (id: number) => {
    await deleteConfig.mutateAsync(id)
    await refetchConfigs()
  }

  const handleCrawlSingle = async (id: number) => {
    await crawlSingle.mutateAsync(id)
    await refetchJobs()
    await refetchConfigs()
  }

  const handleCrawlAll = async () => {
    await crawlAll.mutateAsync()
    await refetchJobs()
    await refetchConfigs()
  }

  const handleViewDetail = (job: Job) => {
    setSelectedJob(job)
    setDrawerOpen(true)
  }

  const handleFilterChange = (filters: { keyword?: string; is_active?: boolean }) => {
    setPage(1)
    if (filters.keyword !== undefined) setKeyword(filters.keyword)
    setIsActive(filters.is_active)
  }

  return (
    <div>
      <h1
        style={{
          fontSize: 24,
          color: '#1f2937',
          marginBottom: 24,
          fontWeight: 500,
        }}
      >
        职位管理
      </h1>


      <Card size="small">
        <JobConfigList
          configs={configs}
          isLoading={configsLoading}
          onCreate={handleCreateConfig}
          onUpdate={handleUpdateConfig}
          onDelete={handleDeleteConfig}
          onCrawl={handleCrawlSingle}
          createLoading={createConfig.isPending}
          updateLoading={updateConfig.isPending}
          crawlLoading={crawlSingle.isPending}
        />
      </Card>

      <JobList
        jobs={jobsResp?.items || []}
        total={jobsResp?.total || 0}
        isLoading={jobsLoading}
        onViewDetail={handleViewDetail}
        onCrawlAll={handleCrawlAll}
        crawlAllLoading={crawlAll.isPending}
        filters={{ keyword, is_active: isActive }}
        onFilterChange={handleFilterChange}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
      />

      <JobDrawer open={drawerOpen} job={selectedJob} onClose={() => setDrawerOpen(false)} />
    </div>
  )
}
