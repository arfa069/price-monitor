import { useMemo, useState } from 'react'
import { Button, Card, Empty, Select, Space, Spin, Table, Tag, useApp } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useMatchResults, useResumes, useTriggerMatch } from '@/hooks/api'
import { jobsApi } from '@/api/jobs'
import type { MatchResultWithJob } from '@/types'

export default function MatchResultList() {
  const [resumeId, setResumeId] = useState<number | undefined>()
  const [minScore, setMinScore] = useState<number | undefined>(70)
  const [page, setPage] = useState(1)
  const pageSize = 20

  const { data: resumes } = useResumes()
  const { data: matchResults, isLoading, refetch } = useMatchResults({
    resume_id: resumeId,
    min_score: minScore,
    page,
    page_size: pageSize,
  })
  const triggerMatch = useTriggerMatch()
  const { message } = useApp()

  const handleTriggerMatch = async () => {
    if (!resumeId) {
      message.warning('请先选择简历')
      return
    }
    try {
      const jobsResp = await jobsApi.getJobs({ page: 1, page_size: 100 })
      const jobIds = jobsResp.data.items.map((job) => job.id)
      await triggerMatch.mutateAsync({ resume_id: resumeId, job_ids: jobIds })
      message.success('匹配分析完成')
      refetch()
    } catch {
      message.error('匹配分析失败')
    }
  }

  const columns: ColumnsType<MatchResultWithJob> = useMemo(
    () => [
      {
        title: '匹配分',
        dataIndex: 'match_score',
        width: 90,
        render: (score: number) => (
          <Tag color={score >= 80 ? 'green' : score >= 60 ? 'orange' : 'default'}>{score}</Tag>
        ),
      },
      {
        title: '建议',
        dataIndex: 'apply_recommendation',
        width: 110,
        render: (value: string | null) => {
          const color =
            value === '强烈推荐' ? 'green' : value === '可以考虑' ? 'blue' : 'default'
          return <Tag color={color}>{value || '-'}</Tag>
        },
      },
      { title: '职位', dataIndex: 'job_title', ellipsis: true },
      { title: '公司', dataIndex: 'job_company', width: 160, ellipsis: true },
      { title: '薪资', dataIndex: 'job_salary', width: 120 },
      {
        title: '原因',
        dataIndex: 'match_reason',
        ellipsis: true,
        render: (value: string | null) => value || '-',
      },
      {
        title: '分析时间',
        dataIndex: 'updated_at',
        width: 180,
        render: (value: string) => new Date(value).toLocaleString('zh-CN'),
      },
    ],
    [],
  )

  return (
    <Card title="匹配结果">
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          style={{ width: 220 }}
          placeholder="选择简历"
          allowClear
          value={resumeId}
          onChange={(value) => {
            setResumeId(value)
            setPage(1)
          }}
          options={resumes?.map((resume) => ({ label: resume.name, value: resume.id }))}
        />
        <Select
          style={{ width: 160 }}
          value={minScore}
          onChange={(value) => {
            setMinScore(value)
            setPage(1)
          }}
          options={[
            { label: '全部分数', value: undefined },
            { label: '70 分以上', value: 70 },
            { label: '80 分以上', value: 80 },
            { label: '90 分以上', value: 90 },
          ]}
        />
        <Button type="primary" disabled={!resumeId} loading={triggerMatch.isPending} onClick={handleTriggerMatch}>
          重新分析
        </Button>
      </Space>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin />
        </div>
      ) : !matchResults?.items.length ? (
        <Empty description="暂无匹配结果" />
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
          onRow={(record) => ({
            onClick: () => record.job_url && window.open(record.job_url, '_blank'),
            style: { cursor: record.job_url ? 'pointer' : 'default' },
          })}
        />
      )}
    </Card>
  )
}
