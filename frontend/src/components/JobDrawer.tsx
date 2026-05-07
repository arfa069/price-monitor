import { useState } from 'react'
import { Button, Descriptions, Drawer, Select, Space, Tag, Typography, useApp } from 'antd'
import { useMatchResults, useResumes, useTriggerMatch } from '@/hooks/api'
import type { Job } from '@/types'

interface JobDrawerProps {
  open: boolean
  job: Job | null
  onClose: () => void
}

export default function JobDrawer({ open, job, onClose }: JobDrawerProps) {
  const { data: resumes } = useResumes()
  const { data: matchResults, refetch } = useMatchResults({
    job_id: job?.id,
    page: 1,
    page_size: 20,
  })
  const triggerMatch = useTriggerMatch()
  const [selectedResumeId, setSelectedResumeId] = useState<number | undefined>()
  const { message } = useApp()

  const currentMatch = matchResults?.items?.[0]

  const handleAnalyze = async () => {
    if (!selectedResumeId || !job) return
    try {
      await triggerMatch.mutateAsync({ resume_id: selectedResumeId, job_ids: [job.id] })
      await refetch()
      message.success('匹配分析完成')
    } catch {
      message.error('匹配分析失败')
    }
  }

  return (
    <Drawer title="职位详情" open={open} onClose={onClose} size="large">
      {!job ? (
        <Typography.Text type="secondary">暂无职位信息</Typography.Text>
      ) : (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="职位 ID">{job.job_id}</Descriptions.Item>
            <Descriptions.Item label="标题">{job.title || '-'}</Descriptions.Item>
            <Descriptions.Item label="公司">{job.company || '-'}</Descriptions.Item>
            <Descriptions.Item label="薪资">{job.salary || '-'}</Descriptions.Item>
            <Descriptions.Item label="薪资范围">
              {job.salary_min ?? '-'} ~ {job.salary_max ?? '-'} K
            </Descriptions.Item>
            <Descriptions.Item label="地点">{job.location || '-'}</Descriptions.Item>
            <Descriptions.Item label="经验">{job.experience || '-'}</Descriptions.Item>
            <Descriptions.Item label="学历">{job.education || '-'}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={job.is_active ? 'success' : 'default'}>
                {job.is_active ? '活跃' : '失效'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="首次发现">
              {new Date(job.first_seen_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="最近更新">
              {new Date(job.last_updated_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="链接">
              {job.url ? (
                <Button type="link" aria-label="在新窗口打开原始页面" onClick={() => window.open(job.url!, '_blank')}>
                  打开原始页面
                </Button>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="描述">
              <Typography.Paragraph style={{ marginBottom: 0 }}>
                {job.description || '-'}
              </Typography.Paragraph>
            </Descriptions.Item>
          </Descriptions>

          <div style={{ marginTop: 24, padding: 16, background: '#f8fafc', borderRadius: 8 }}>
            <Typography.Title level={5}>匹配分析</Typography.Title>

            {currentMatch ? (
              <Space orientation="vertical" size={8}>
                <Space>
                  <Tag
                    color={
                      currentMatch.match_score >= 80
                        ? 'green'
                        : currentMatch.match_score >= 60
                          ? 'orange'
                          : 'default'
                    }
                  >
                    {currentMatch.match_score} 分
                  </Tag>
                  <Tag>{currentMatch.apply_recommendation || '-'}</Tag>
                </Space>
                <Typography.Paragraph style={{ marginBottom: 0 }}>
                  {currentMatch.match_reason || '-'}
                </Typography.Paragraph>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  模型：{currentMatch.llm_model_used || '-'} ·{' '}
                  {new Date(currentMatch.updated_at).toLocaleString('zh-CN')}
                </Typography.Text>
              </Space>
            ) : (
              <Space orientation="vertical" style={{ width: '100%' }} size={12}>
                <Typography.Text type="secondary">选择一份简历来分析这个职位。</Typography.Text>
                <Space wrap>
                  <Select
                    style={{ width: 220 }}
                    placeholder="选择简历"
                    value={selectedResumeId}
                    onChange={setSelectedResumeId}
                    options={resumes?.map((resume) => ({ label: resume.name, value: resume.id }))}
                  />
                  <Button
                    type="primary"
                    disabled={!selectedResumeId}
                    loading={triggerMatch.isPending}
                    onClick={handleAnalyze}
                  >
                    开始分析
                  </Button>
                </Space>
              </Space>
            )}
          </div>
        </>
      )}
    </Drawer>
  )
}
