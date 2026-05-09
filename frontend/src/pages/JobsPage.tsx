import { useMemo, useState } from 'react'
import { Card, Tabs } from 'antd'
import {
  useCrawlAllJobs,
  useCrawlSingleJob,
  useCreateJobConfig,
  useDeleteJobConfig,
  useJobConfigs,
  useJobs,
  useMatchResults,
  useUpdateJobConfig,
} from '@/hooks/api'
import JobConfigList from '@/components/JobConfigList'
import JobDrawer from '@/components/JobDrawer'
import JobList from '@/components/JobList'
import MatchResultList from '@/components/MatchResultList'
import ResumeManager from '@/components/ResumeManager'
import { useAuth } from '@/contexts/AuthContext'
import type { Job, JobSearchConfigCreate } from '@/types'

export default function JobsPage() {
  const { user } = useAuth()
  const canCrawl = user?.role !== 'admin'
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [isActive, setIsActive] = useState<boolean | undefined>(undefined)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [activeTab, setActiveTab] = useState('configs')

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
  const { data: allMatches } = useMatchResults({ page: 1, page_size: 100 })

  const crawlAll = useCrawlAllJobs()
  const crawlSingle = useCrawlSingleJob()

  const matchScores = useMemo(() => {
    const map: Record<number, number> = {}
    allMatches?.items.forEach((item) => {
      map[item.job_id] = Math.max(map[item.job_id] ?? 0, item.match_score)
    })
    return map
  }, [allMatches])

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

  const items = [
    {
      key: 'configs',
      label: '搜索配置',
      children: (
        <>
          <Card size="small">
            <JobConfigList
              configs={configs}
              isLoading={configsLoading}
              onCreate={handleCreateConfig}
              onUpdate={handleUpdateConfig}
              onDelete={handleDeleteConfig}
              onCrawl={canCrawl ? handleCrawlSingle : undefined}
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
            onCrawlAll={canCrawl ? handleCrawlAll : undefined}
            crawlAllLoading={crawlAll.isPending}
            filters={{ keyword, is_active: isActive }}
            onFilterChange={handleFilterChange}
            page={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            matchScores={matchScores}
          />
        </>
      ),
    },
    {
      key: 'resume',
      label: '简历管理',
      children: <ResumeManager />,
    },
    {
      key: 'matches',
      label: '匹配结果',
      children: <MatchResultList />,
    },
  ]

  return (
    <div>
      {/* Page header — cream color block */}
      <div className="page-header bg-cream">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">职位搜索</p>
            <h1 className="page-title">职位管理</h1>
            <p className="page-subtitle">配置 Boss 直聘职位搜索规则，智能匹配候选人</p>
          </div>
        </div>
      </div>

      {/* Tab sections */}
      <div style={{ marginTop: 24 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={items}
        />
      </div>

      <JobDrawer open={drawerOpen} job={selectedJob} onClose={() => setDrawerOpen(false)} />
    </div>
  )
}
