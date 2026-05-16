import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Card, Table, Tag, Tabs } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  useCrawlAllJobs,
  useCrawlSingleJob,
  useCreateJobConfig,
  useDeleteJobConfig,
  useJobConfigs,
  useJobCrawlLogs,
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
import { useStaggerAnimation } from '@/hooks/useStaggerAnimation'
import type { Job, JobCrawlLog, JobSearchConfigCreate } from '@/types'

export default function JobsPage() {
  const { user } = useAuth()
  const stagger = useStaggerAnimation(0.05, 0.05)
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
  const { data: jobCrawlLogs, isLoading: logsLoading } = useJobCrawlLogs({ limit: 20 })

  const matchScores = useMemo(() => {
    const map: Record<number, number> = {}
    allMatches?.items.forEach((item) => {
      map[item.job_id] = Math.max(map[item.job_id] ?? 0, item.match_score)
    })
    return map
  }, [allMatches])

  const configNameMap = useMemo(() => {
    const map: Record<number, string> = {}
    configs?.forEach((c) => { map[c.id] = c.name })
    return map
  }, [configs])

  const crawlLogColumns: ColumnsType<JobCrawlLog> = [
    {
      title: 'Time',
      dataIndex: 'scraped_at',
      width: 160,
      render: (value: string) =>
        new Intl.DateTimeFormat('en-US', {
          dateStyle: 'medium',
          timeStyle: 'short',
        }).format(new Date(value)),
    },
    {
      title: 'Config',
      dataIndex: 'search_config_id',
      width: 120,
      render: (id: number) => configNameMap[id] || `#${id}`,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 100,
      render: (value: string) => {
        const config: Record<string, { color: string; text: string }> = {
          SUCCESS: { color: 'success', text: 'Success' },
          ERROR: { color: 'error', text: 'Failed' },
        }
        const c = config[value]
        return <Tag color={c?.color || 'default'}>{c?.text || value}</Tag>
      },
    },
    {
      title: 'New Jobs',
      dataIndex: 'new_jobs_count',
      width: 80,
      render: (value: number | null) => (value !== null ? value : '-'),
    },
    {
      title: 'Total',
      dataIndex: 'total_jobs_count',
      width: 80,
      render: (value: number | null) => (value !== null ? value : '-'),
    },
    {
      title: 'Error',
      dataIndex: 'error_message',
      render: (value: string | null) =>
        value ? (
          <span style={{ color: '#ff4d4f', cursor: 'pointer' }} title={value}>
            {value.length > 40 ? `${value.slice(0, 40)}...` : value}
          </span>
        ) : null,
    },
  ]

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
      label: 'Search Config',
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
      label: 'Resume Management',
      children: <ResumeManager />,
    },
    {
      key: 'matches',
      label: 'Match Results',
      children: <MatchResultList />,
    },
    {
      key: 'logs',
      label: 'Crawl Logs',
      children: (
        <Card size="small" title="Recent Job Crawl Logs">
          <Table<JobCrawlLog>
            columns={crawlLogColumns}
            dataSource={jobCrawlLogs}
            rowKey="id"
            loading={logsLoading}
            size="small"
            pagination={false}
          />
        </Card>
      ),
    },
  ]

  return (
    <div>
      {/* Page header — cream color block */}
      <div className="page-header bg-cream">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">Job Search</p>
            <h1 className="page-title">Job Management</h1>
            <p className="page-subtitle">Configure Boss Zhipin job search rules, intelligently match candidates</p>
          </div>
        </div>
      </div>

      {/* Tab sections */}
      <motion.div
        variants={stagger.container}
        initial="hidden"
        animate="show"
        style={{ marginTop: 24 }}
      >
        <motion.div variants={stagger.item}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={items}
          />
        </motion.div>
      </motion.div>

      <JobDrawer open={drawerOpen} job={selectedJob} onClose={() => setDrawerOpen(false)} />
    </div>
  )
}
