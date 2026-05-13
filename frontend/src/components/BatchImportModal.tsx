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
  jd: '京东',
  taobao: '淘宝',
  amazon: '亚马逊',
}

const PLATFORM_OPTIONS: Array<{ label: string; value: ParsedPlatform }> = [
  { label: '京东', value: 'jd' },
  { label: '淘宝', value: 'taobao' },
  { label: '亚马逊', value: 'amazon' },
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
      message.warning('请输入至少一个 URL')
      return
    }
    if (lines.length > 100) {
      message.warning('单次最多导入 100 个 URL')
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
      message.warning('所有 URL 都已存在')
      return
    }
    if (filtered.length < deduped.length) {
      message.info(`已跳过 ${deduped.length - filtered.length} 个重复 URL`)
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
      message.error('存在无法识别平台的 URL，请手动选择')
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
      title: '平台',
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
            placeholder="选择平台"
            onChange={(value) => handlePlatformChange(index, value)}
            options={PLATFORM_OPTIONS}
          />
        )
      },
    },
  ]

  return (
    <Modal
      title="批量导入商品"
      open={open}
      onCancel={handleCancel}
      footer={
        step === 0 ? (
          <Button type="primary" onClick={handleParse} disabled={!rawText.trim()}>
            下一步
          </Button>
        ) : (
          <>
            <Button onClick={handleCancel}>取消</Button>
            <Button type="primary" onClick={handleConfirm} loading={confirmLoading}>
              确认导入 ({items.length})
            </Button>
          </>
        )
      }
    >
      <Steps
        current={step}
        style={{ marginBottom: 20 }}
        items={[{ title: '粘贴 URL' }, { title: '确认平台' }]}
      />

      {step === 0 ? (
        <div>
          <Input.TextArea
            aria-label="批量粘贴 URL，每行一个"
            autoComplete="off"
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder={
              '每行一个 URL，例如：\nhttps://item.jd.com/10001234.html\nhttps://detail.tmall.com/item.htm?id=12345'
            }
            rows={8}
            allowClear
          />
          <div style={{ color: 'var(--color-muted)', fontSize: 12, marginTop: 8 }}>
            支持 `jd.com`、`taobao.com`、`tmall.com`、`amazon.`，每次最多 100 条
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
