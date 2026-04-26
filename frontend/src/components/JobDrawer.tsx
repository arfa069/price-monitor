import { Button, Descriptions, Drawer, Tag, Typography } from 'antd'
import type { Job } from '@/types'

interface JobDrawerProps {
  open: boolean
  job: Job | null
  onClose: () => void
}

export default function JobDrawer({ open, job, onClose }: JobDrawerProps) {
  return (
    <Drawer title="职位详情" open={open} onClose={onClose} size="large">
      {!job ? (
        <Typography.Text type="secondary">暂无职位信息</Typography.Text>
      ) : (
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
              <Button type="link" onClick={() => window.open(job.url!, '_blank')}>
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
      )}
    </Drawer>
  )
}
