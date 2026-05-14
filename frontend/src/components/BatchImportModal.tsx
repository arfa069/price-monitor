import { useState } from 'react'
import { Button, Input, Modal, Select, Steps, Table, App } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { BatchImportRow } from '@/types'

type ParsedItem = {
  url: string
  platform: 'jd' | 'taobao' | 'amazon' | null
}

type ParsedPlatform = NonNullable<ParsedItem['platform']>

const PLATFORM_LABELS: Record<ParsedPlatform, string> = {
  jd: 'JD',
  taobao: 'Taobao',
  amazon: 'Amazon',
}

const PLATFORM_OPTIONS: Array<{ label: string; value: ParsedPlatform }> = [
  { label: 'JD', value: 'jd' },
  { label: 'Taobao', value: 'taobao' },
  { label: 'Amazon', value: 'amazon' },
]

const detectPlatform = (url: string): ParsedItem['platform'] => {
  const lowerUrl = url.toLowerCase()
  if (lowerUrl.includes('jd.com') || lowerUrl.includes('item.jd')) return 'jd'
  if (lowerUrl.includes('taobao.com') || lowerUrl.includes('tmall.com')) return 'taobao'
  if (lowerUrl.includes('amazon.')) return 'amazon'
  return null
}

interface Props {
  open: boolean
  onCancel: () => void
  onImport: (items: BatchImportRow[]) => void
  confirmLoading: boolean
  existingUrls: string[]
}

export default function BatchImportModal({
  open,
  onCancel,
  onImport,
  confirmLoading,
  existingUrls,
}: Props) {
  const message = App.useApp().message
  const [step, setStep] = useState(0)
  const [rawText, setRawText] = useState('')
  const [items, setItems] = useState<ParsedItem[]>([])

  const handleParse = () => {
    const lines = rawText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)

    if (lines.length === 0) {
      message.warning('Please enter at least one URL')
      return
    }
    if (lines.length > 100) {
      message.warning('Maximum 100 URLs per import')
      return
    }

    const parsed = lines.map((url) => ({ url, platform: detectPlatform(url) }))
    const seen = new Set<string>()
    const deduped: ParsedItem[] = []
    for (const item of parsed) {
      if (!seen.has(item.url)) {
        seen.add(item.url)
        deduped.push(item)
      }
    }

    const filtered = deduped.filter((item) => !existingUrls.includes(item.url))
    if (filtered.length === 0) {
      message.warning('All URLs already exist')
      return
    }
    if (filtered.length < deduped.length) {
      message.info(`Skipped ${deduped.length - filtered.length} duplicate URL(s)`)
    }

    setItems(filtered)
    setStep(1)
  }

  const handlePlatformChange = (index: number, platform: ParsedPlatform) => {
    setItems((prev) =>
      prev.map((item, itemIndex) =>
        itemIndex === index ? { ...item, platform } : item,
      ),
    )
  }

  const handleConfirm = () => {
    if (items.some((item) => !item.platform)) {
      message.error('Some URLs have unrecognized platform, please select manually')
      return
    }

    onImport(
      items.map((item) => ({
        url: item.url,
        platform: item.platform!,
      })),
    )
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

  const columns: ColumnsType<ParsedItem> = [
    { title: 'URL', dataIndex: 'url', ellipsis: true },
    {
      title: 'Platform',
      dataIndex: 'platform',
      width: 140,
      render: (platform: ParsedItem['platform'], _record, index) => {
        if (platform) {
          return PLATFORM_LABELS[platform]
        }
        return (
          <Select<ParsedPlatform>
            size="small"
            style={{ width: '100%' }}
            placeholder="Select Platform"
            onChange={(value) => handlePlatformChange(index, value)}
            options={PLATFORM_OPTIONS}
          />
        )
      },
    },
  ]

  return (
    <Modal
      title="Batch Import Products"
      open={open}
      onCancel={handleCancel}
      footer={
        step === 0 ? (
          <Button type="primary" onClick={handleParse} disabled={!rawText.trim()}>
            Next
          </Button>
        ) : (
          <>
            <Button onClick={handleCancel}>Cancel</Button>
            <Button type="primary" onClick={handleConfirm} loading={confirmLoading}>
              Confirm Import ({items.length})
            </Button>
          </>
        )
      }
    >
      <Steps
        current={step}
        style={{ marginBottom: 20 }}
        items={[{ title: 'Paste URLs' }, { title: 'Confirm Platform' }]}
      />

      {step === 0 ? (
        <div>
          <Input.TextArea
            aria-label="Paste multiple URLs, one per line"
            autoComplete="off"
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder={
              'One URL per line, e.g.:\nhttps://item.jd.com/10001234.html\nhttps://detail.tmall.com/item.htm?id=12345'
            }
            rows={8}
            allowClear
          />
          <div style={{ color: 'var(--color-muted)', fontSize: 12, marginTop: 8 }}>
            Supports jd.com, taobao.com, tmall.com, amazon., max 100 per batch
          </div>
        </div>
      ) : (
        <Table
          dataSource={items}
          rowKey="url"
          size="small"
          pagination={false}
          scroll={{ y: 300 }}
          columns={columns}
        />
      )}
    </Modal>
  )
}
