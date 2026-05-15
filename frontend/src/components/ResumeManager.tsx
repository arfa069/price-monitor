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
import { DeleteOutlined, EditOutlined, EyeOutlined, UploadOutlined } from '@ant-design/icons'
import { useCreateResume, useDeleteResume, useResumes, useUpdateResume } from '@/hooks/api'
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
  const updateResume = useUpdateResume()
  const deleteResume = useDeleteResume()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [resumeName, setResumeName] = useState('')
  const [resumeText, setResumeText] = useState('')
  const [viewResume, setViewResume] = useState<UserResume | null>(null)
  const [editResume, setEditResume] = useState<UserResume | null>(null)
  const [editName, setEditName] = useState('')
  const [editText, setEditText] = useState('')

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

  const openView = (resume: UserResume) => {
    setViewResume(resume)
  }

  const openEdit = (resume: UserResume) => {
    setEditResume(resume)
    setEditName(resume.name)
    setEditText(resume.resume_text)
  }

  const handleEdit = async () => {
    if (!editResume) return
    if (!editName.trim()) {
      message.error('Please enter resume name')
      return
    }
    if (!editText.trim()) {
      message.error('Please enter resume content')
      return
    }
    try {
      await updateResume.mutateAsync({
        id: editResume.id,
        data: { name: editName.trim(), resume_text: editText.trim() },
      })
      message.success('Resume updated')
      setEditResume(null)
      refetch()
    } catch {
      message.error('Update failed')
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
                    <Button size="small" icon={<EyeOutlined />} onClick={() => openView(resume)}>
                      View
                    </Button>
                    <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(resume)}>
                      Edit
                    </Button>
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

      {/* View Resume Modal */}
      <Modal
        title={viewResume?.name || 'View Resume'}
        open={!!viewResume}
        onCancel={() => setViewResume(null)}
        footer={
          <Button onClick={() => setViewResume(null)}>Close</Button>
        }
        width={720}
      >
        <Typography.Paragraph
          style={{
            whiteSpace: 'pre-wrap',
            fontFamily: 'var(--font-mono)',
            fontSize: 13,
            lineHeight: 1.6,
            background: 'var(--color-surface-soft)',
            padding: 16,
            borderRadius: 8,
            margin: 0,
          }}
        >
          {viewResume?.resume_text}
        </Typography.Paragraph>
      </Modal>

      {/* Edit Resume Modal */}
      <Modal
        title={`Edit: ${editResume?.name || ''}`}
        open={!!editResume}
        onOk={handleEdit}
        onCancel={() => setEditResume(null)}
        confirmLoading={updateResume.isPending}
        width={720}
        okText="Save"
      >
        <Space orientation="vertical" style={{ width: '100%' }} size={16}>
          <div>
            <Typography.Text strong>Resume Name</Typography.Text>
            <Input
              aria-label="Edit Resume Name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              placeholder="e.g. Frontend Resume v1"
              style={{ marginTop: 6 }}
            />
          </div>
          <div>
            <Typography.Text strong>Resume Content</Typography.Text>
            <Input.TextArea
              aria-label="Edit Resume Content"
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              placeholder="Edit resume content"
              autoSize={{ minRows: 12, maxRows: 20 }}
            />
          </div>
        </Space>
      </Modal>
    </Card>
  )
}
