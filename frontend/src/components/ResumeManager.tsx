import { useState } from 'react'
import {
  App,
  Button,
  Card,
  Empty,
  Input,
  message,
  Modal,
  Popconfirm,
  Space,
  Spin,
  Typography,
} from 'antd'
import { DeleteOutlined, UploadOutlined } from '@ant-design/icons'
import { useCreateResume, useDeleteResume, useResumes } from '@/hooks/api'
import type { UserResume } from '@/types'

interface ResumeManagerProps {
  onSelectResume?: (resume: UserResume) => void
  selectedResumeId?: number
}

export default function ResumeManager({ onSelectResume, selectedResumeId }: ResumeManagerProps) {
  const message = App.useApp().message
  const { data: resumes, isLoading, refetch } = useResumes()
  const createResume = useCreateResume()
  const deleteResume = useDeleteResume()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [resumeName, setResumeName] = useState('')
  const [resumeText, setResumeText] = useState('')

  const handleUpload = async () => {
    if (!resumeName.trim()) {
      message.error('请输入简历名称')
      return
    }
    if (!resumeText.trim()) {
      message.error('请输入简历内容')
      return
    }
    try {
      await createResume.mutateAsync({
        name: resumeName.trim(),
        resume_text: resumeText.trim(),
      })
      message.success('简历上传成功')
      setUploadOpen(false)
      setResumeName('')
      setResumeText('')
      refetch()
    } catch {
      message.error('上传失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteResume.mutateAsync(id)
      message.success('简历已删除')
      refetch()
    } catch {
      message.error('删除失败')
    }
  }

  return (
    <Card title="简历管理">
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>
          上传简历
        </Button>
      </Space>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin />
        </div>
      ) : !resumes?.length ? (
        <Empty description="暂无简历，请先上传一份简历" />
      ) : (
        <div style={{ display: 'grid', gap: 12 }}>
          {resumes.map((resume) => (
            <Card
              key={resume.id}
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
                      {selectedResumeId === resume.id ? '已选择' : '选择'}
                    </Button>
                  ) : null}
                  <Popconfirm title="确认删除这份简历吗？" onConfirm={() => handleDelete(resume.id)}>
                    <Button danger size="small" icon={<DeleteOutlined />}>
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              }
            >
              <Typography.Text type="secondary">
                上传时间：{new Date(resume.created_at).toLocaleString('zh-CN')}
              </Typography.Text>
            </Card>
          ))}
        </div>
      )}

      <Modal
        title="上传简历"
        open={uploadOpen}
        onOk={handleUpload}
        onCancel={() => setUploadOpen(false)}
        confirmLoading={createResume.isPending}
        width={720}
      >
        <Space orientation="vertical" style={{ width: '100%' }} size={16}>
          <div>
            <Typography.Text strong>简历名称</Typography.Text>
            <Input
              aria-label="简历名称"
              value={resumeName}
              onChange={(e) => setResumeName(e.target.value)}
              placeholder="例如：前端简历 v1"
              style={{ marginTop: 6 }}
            />
          </div>
          <div>
            <Typography.Text strong>简历内容</Typography.Text>
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>
              先用纯文本粘贴，后续如果要支持文件解析再扩展上传格式。
            </Typography.Text>
            <Input.TextArea
              aria-label="简历内容"
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="粘贴完整简历内容"
              autoSize={{ minRows: 12, maxRows: 20 }}
            />
          </div>
        </Space>
      </Modal>
    </Card>
  )
}
