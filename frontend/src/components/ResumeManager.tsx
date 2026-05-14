import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  App,
  Button,
  Card,
  Empty,
  Input,
  Modal,
  Popconfirm,
  Space,
  Spin,
  Typography,
} from 'antd'
import { DeleteOutlined, UploadOutlined } from '@ant-design/icons'
import { useCreateResume, useDeleteResume, useResumes } from '@/hooks/api'
import { useStaggerAnimation } from '@/hooks/useStaggerAnimation'
import type { UserResume } from '@/types'

interface ResumeManagerProps {
  onSelectResume?: (resume: UserResume) => void
  selectedResumeId?: number
}

export default function ResumeManager({ onSelectResume, selectedResumeId }: ResumeManagerProps) {
  const message = App.useApp().message
  const stagger = useStaggerAnimation(0.05, 0.05)
  const { data: resumes, isLoading, refetch } = useResumes()
  const createResume = useCreateResume()
  const deleteResume = useDeleteResume()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [resumeName, setResumeName] = useState('')
  const [resumeText, setResumeText] = useState('')

  const handleUpload = async () => {
    if (!resumeName.trim()) {
      message.error('Please enter resume name')
      return
    }
    if (!resumeText.trim()) {
      message.error('Please enter resume content')
      return
    }
    try {
      await createResume.mutateAsync({
        name: resumeName.trim(),
        resume_text: resumeText.trim(),
      })
      message.success('Resume uploaded successfully')
      setUploadOpen(false)
      setResumeName('')
      setResumeText('')
      refetch()
    } catch {
      message.error('Upload failed')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteResume.mutateAsync(id)
      message.success('Resume deleted')
      refetch()
    } catch {
      message.error('Delete failed')
    }
  }

  return (
    <Card title="Resume Management">
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>
          Upload Resume
        </Button>
      </Space>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin />
        </div>
      ) : !resumes?.length ? (
        <Empty description="No resumes, please upload one first" />
      ) : (
        <motion.div
          variants={stagger.container}
          initial="hidden"
          animate="show"
          style={{ display: 'grid', gap: 12 }}
        >
          {resumes.map((resume) => (
            <motion.div key={resume.id} variants={stagger.item}>
              <Card
                size="small"
                title={resume.name}
                extra={
                  <Space>
                    {onSelectResume ? (
                      <Button
                        type={selectedResumeId === resume.id ? 'primary' : 'default'}
                        size="small"
                        onClick={() => onSelectResume(resume)}
                      >
                        {selectedResumeId === resume.id ? 'Selected' : 'Select'}
                      </Button>
                    ) : null}
                    <Popconfirm title="Confirm delete this resume?" onConfirm={() => handleDelete(resume.id)}>
                      <Button danger size="small" icon={<DeleteOutlined />}>
                        Delete
                      </Button>
                    </Popconfirm>
                  </Space>
                }
              >
                <Typography.Text type="secondary">
                  Uploaded: {new Date(resume.created_at).toLocaleString('en-US')}
                </Typography.Text>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}

      <Modal
        title="Upload Resume"
        open={uploadOpen}
        onOk={handleUpload}
        onCancel={() => setUploadOpen(false)}
        confirmLoading={createResume.isPending}
        width={720}
      >
        <Space orientation="vertical" style={{ width: '100%' }} size={16}>
          <div>
            <Typography.Text strong>Resume Name</Typography.Text>
            <Input
              aria-label="Resume Name"
              value={resumeName}
              onChange={(e) => setResumeName(e.target.value)}
              placeholder="e.g. Frontend Resume v1"
              style={{ marginTop: 6 }}
            />
          </div>
          <div>
            <Typography.Text strong>Resume Content</Typography.Text>
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>
              Paste as plain text for now. File parsing support may be added later.
            </Typography.Text>
            <Input.TextArea
              aria-label="Resume Content"
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="Paste full resume content"
              autoSize={{ minRows: 12, maxRows: 20 }}
            />
          </div>
        </Space>
      </Modal>
    </Card>
  )
}
