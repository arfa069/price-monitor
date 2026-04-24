import { useState } from 'react'
import { Modal, Input, Table, Select, Button, Steps, message } from 'antd'

const detectPlatform = (url: string): string | null => {
  const u = url.toLowerCase()
  if (u.includes('jd.com') || u.includes('item.jd')) return 'jd'
  if (u.includes('taobao.com') || u.includes('tmall.com')) return 'taobao'
  if (u.includes('amazon.')) return 'amazon'
  return null
}

interface Props {
  open: boolean
  onCancel: () => void
  onImport: (items: { url: string; platform: string; title?: string }[]) => void
  confirmLoading: boolean
  existingUrls: string[]
}

export default function BatchImportModal({ open, onCancel, onImport, confirmLoading, existingUrls }: Props) {
  const [step, setStep] = useState(0)
  const [rawText, setRawText] = useState('')
  const [items, setItems] = useState<{ url: string; platform: string | null }[]>([])

  const handleParse = () => {
    const lines = rawText.split('\n').map((l) => l.trim()).filter(Boolean)
    if (lines.length === 0) { message.warning('请输入至少一个 URL'); return }
    if (lines.length > 100) { message.warning('单次最多导入 100 个 URL'); return }

    const parsed = lines.map((url) => ({ url, platform: detectPlatform(url) }))
    // Deduplicate within input
    const seen = new Set<string>()
    const deduped: typeof parsed = []
    for (const item of parsed) {
      if (!seen.has(item.url)) { seen.add(item.url); deduped.push(item) }
    }
    // Check against existing
    const final = deduped.filter((item) => !existingUrls.includes(item.url))
    if (final.length === 0) { message.warning('所有 URL 均已存在'); return }
    if (final.length < deduped.length) message.info(`已跳过 ${deduped.length - final.length} 个重复 URL`)

    setItems(final)
    setStep(1)
  }

  const handlePlatformChange = (index: number, platform: string) => {
    setItems((prev) => prev.map((item, i) => i === index ? { ...item, platform } : item))
  }

  const handleConfirm = () => {
    const hasUnknown = items.some((item) => !item.platform)
    if (hasUnknown) { message.error('存在无法识别平台的 URL，请手动选择'); return }
    onImport(items.map((item) => ({ url: item.url, platform: item.platform! as 'taobao' | 'jd' | 'amazon' })))
    // Reset
    setRawText('')
    setItems([])
    setStep(0)
  }

  const handleCancel = () => {
    setRawText('')
    setItems([])
    setStep(0)
    onCancel()
  }

  return (
    <Modal
      title="批量导入商品"
      open={open}
      onCancel={handleCancel}
      footer={
        step === 0 ? (
          <Button type="primary" onClick={handleParse} disabled={!rawText.trim()}>下一步</Button>
        ) : (
          <>
            <Button onClick={handleCancel}>取消</Button>
            <Button type="primary" onClick={handleConfirm} loading={confirmLoading}>确认导入 ({items.length})</Button>
          </>
        )
      }
    >
      <Steps current={step} style={{ marginBottom: 20 }} items={[{ title: '粘贴 URL' }, { title: '确认平台' }]} />

      {step === 0 && (
        <div>
          <Input.TextArea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="每行一个 URL，例如：&#10;https://item.jd.com/10001234.html&#10;https://detail.tmall.com/item.htm?id=12345"
            rows={8}
            allowClear
          />
          <div style={{ color: '#64748b', fontSize: 12, marginTop: 8 }}>
            支持平台：jd.com / taobao.com / tmall.com / amazon.（每行一个，最多 100 个）
          </div>
        </div>
      )}

      {step === 1 && (
        <Table
          dataSource={items}
          rowKey="url"
          size="small"
          pagination={false}
          scroll={{ y: 300 }}
          columns={[
            { title: 'URL', dataIndex: 'url', ellipsis: true },
            {
              title: '平台',
              dataIndex: 'platform',
              width: 140,
              render: (platform: string | null, _: any, index: number) => {
                if (platform) {
                  const labels: Record<string, string> = { jd: '京东', taobao: '淘宝', amazon: '亚马逊' }
                  return labels[platform] || platform
                }
                return (
                  <Select
                    size="small"
                    style={{ width: '100%' }}
                    placeholder="选择平台"
                    onChange={(v) => handlePlatformChange(index, v)}
                    options={[
                      { label: '京东', value: 'jd' },
                      { label: '淘宝', value: 'taobao' },
                      { label: '亚马逊', value: 'amazon' },
                    ]}
                  />
                )
              },
            },
          ]}
        />
      )}
    </Modal>
  )
}
