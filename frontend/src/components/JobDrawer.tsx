import { useState } from 'react'
import { Button, Descriptions, Drawer, Select, Space, Tag, Typography, App } from 'antd'
import { useMatchResults, useResumes, useTriggerMatch } from '@/hooks/api'
import type { Job } from '@/types'

interface JobDrawerProps {
  open: boolean
  job: Job | null
  onClose: () => void
}

export default function JobDrawer({ open, job, onClose }: JobDrawerProps) {
  const message = App.useApp().message
  const { data: resumes } = useResumes()
  const { data: matchResults, refetch } = useMatchResults({
    job_id: job?.id,
    page: 1,
    page_size: 20,
  })
  const triggerMatch = useTriggerMatch()
  const [selectedResumeId, setSelectedResumeId] = useState<number | undefined>()

  const currentMatch = matchResults?.items?.[0]

  const handleAnalyze = async () => {
    if (!selectedResumeId || !job) return
    try {
      await triggerMatch.mutateAsync({ resume_id: selectedResumeId, job_ids: [job.id] })
      await refetch()
      message.success('Match analysis complete')
    } catch {
      message.error('Match analysis failed')
    }
  }

  return (
    <Drawer title="Job Details" open={open} onClose={onClose} size="large">
      {!job ? (
        <Typography.Text type="secondary">No job information</Typography.Text>
      ) : (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="Job ID">{job.job_id}</Descriptions.Item>
            <Descriptions.Item label="Title">{job.title || '-'}</Descriptions.Item>
            <Descriptions.Item label="Company">{job.company || '-'}</Descriptions.Item>
            <Descriptions.Item label="Salary">{job.salary || '-'}</Descriptions.Item>
            <Descriptions.Item label="Salary Range">
              {job.salary_min ?? '-'} ~ {job.salary_max ?? '-'} K
            </Descriptions.Item>
            <Descriptions.Item label="Location">{job.location || '-'}</Descriptions.Item>
            <Descriptions.Item label="Experience">{job.experience || '-'}</Descriptions.Item>
            <Descriptions.Item label="Education">{job.education || '-'}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={job.is_active ? 'success' : 'default'}>
                {job.is_active ? 'Active' : 'Inactive'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="First Seen">
              {new Date(job.first_seen_at).toLocaleString('en-US')}
            </Descriptions.Item>
            <Descriptions.Item label="Last Updated">
              {new Date(job.last_updated_at).toLocaleString('en-US')}
            </Descriptions.Item>
            <Descriptions.Item label="Link">
              {job.url ? (
                <Button type="link" aria-label="Open original page in new window" onClick={() => window.open(job.url!, '_blank')}>
                  Open Original Page
                </Button>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Description">
              <Typography.Paragraph style={{ marginBottom: 0 }}>
                {job.description || '-'}
              </Typography.Paragraph>
            </Descriptions.Item>
          </Descriptions>

          <div style={{ marginTop: 24, padding: 16, background: '#f8fafc', borderRadius: 8 }}>
            <Typography.Title level={5}>Match Analysis</Typography.Title>

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
                    {currentMatch.match_score} pts
                  </Tag>
                  <Tag>{currentMatch.apply_recommendation || '-'}</Tag>
                </Space>
                <Typography.Paragraph style={{ marginBottom: 0 }}>
                  {currentMatch.match_reason || '-'}
                </Typography.Paragraph>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  Model: {currentMatch.llm_model_used || '-'} ·{' '}
                  {new Date(currentMatch.updated_at).toLocaleString('en-US')}
                </Typography.Text>
              </Space>
            ) : (
              <Space orientation="vertical" style={{ width: '100%' }} size={12}>
                <Typography.Text type="secondary">Select a resume to analyze this job.</Typography.Text>
                <Space wrap>
                  <Select
                    style={{ width: 220 }}
                    placeholder="Select Resume"
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
                    Start Analysis
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
