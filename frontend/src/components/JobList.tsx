import { useMemo } from 'react'
import { Button, Card, Input, Select, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import type { Job } from '@/types'

interface JobListProps {
  jobs?: Job[]
  total: number
  isLoading?: boolean
  onViewDetail: (job: Job) => void
  onCrawlAll?: () => Promise<void>
  crawlAllLoading?: boolean
  filters: { keyword?: string; is_active?: boolean }
  onFilterChange: (filters: { keyword?: string; is_active?: boolean }) => void
  page: number
  pageSize: number
  onPageChange: (page: number) => void
  matchScores?: Record<number, number>
}

type StatusFilterValue = 'all' | 'active' | 'inactive'

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
  matchScores,
}: JobListProps) {
  const statusValue: StatusFilterValue =
    filters.is_active === undefined ? 'all' : filters.is_active ? 'active' : 'inactive'

  const columns: ColumnsType<Job> = useMemo(
    () => [
      { title: 'ID', dataIndex: 'id', width: 80 },
      {
        title: '匹配',
        key: 'match_score',
        width: 90,
        render: (_, record) => {
          const score = matchScores?.[record.id]
          if (!score) return null
          return (
            <Tag color={score >= 80 ? 'green' : score >= 60 ? 'orange' : 'default'}>
              {score}
            </Tag>
          )
        },
      },
      {
        title: '职位',
        dataIndex: 'title',
        ellipsis: true,
        render: (title: string, record) =>
          record.url ? (
            <a href={record.url} target="_blank" rel="noopener noreferrer" title="在新标签页打开职位">
              {title}
            </a>
          ) : (
            title
          ),
      },
      { title: '公司', dataIndex: 'company', width: 200, ellipsis: true },
      { title: '薪资', dataIndex: 'salary', width: 120 },
      { title: '地点', dataIndex: 'location', width: 120, ellipsis: true },
      {
        title: '状态',
        dataIndex: 'is_active',
        width: 90,
        render: (active: boolean) => (
          <Tag color={active ? 'success' : 'default'}>{active ? '活跃' : '失效'}</Tag>
        ),
      },
      {
        title: '最近更新',
        dataIndex: 'last_updated_at',
        width: 180,
        render: (value: string) => new Date(value).toLocaleString('zh-CN'),
      },
      {
        title: '操作',
        key: 'action',
        width: 100,
        render: (_, record) => (
          <Button size="small" onClick={(e) => { e.stopPropagation(); onViewDetail(record) }}>
            查看
          </Button>
        ),
      },
    ],
    [matchScores, onViewDetail],
  )

  return (
    <Card style={{ marginTop: 16 }} title="职位列表">
      <Space style={{ marginBottom: 12 }} wrap>
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="关键词搜索职位或公司"
          value={filters.keyword}
          onChange={(e) => onFilterChange({ ...filters, keyword: e.target.value })}
          style={{ width: 240 }}
        />
        <Select
          style={{ width: 140 }}
          value={statusValue}
          onChange={(value: StatusFilterValue) =>
            onFilterChange({
              ...filters,
              is_active: value === 'all' ? undefined : value === 'active',
            })
          }
          options={[
            { label: '全部状态', value: 'all' },
            { label: '活跃', value: 'active' },
            { label: '失效', value: 'inactive' },
          ]}
        />
        {onCrawlAll && (
          <Button icon={<ReloadOutlined />} loading={crawlAllLoading} onClick={onCrawlAll}>
            全量抓取
          </Button>
        )}
      </Space>

      <Table
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={jobs || []}
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: (next) => onPageChange(next),
          showSizeChanger: false,
        }}
      />
    </Card>
  )
}
