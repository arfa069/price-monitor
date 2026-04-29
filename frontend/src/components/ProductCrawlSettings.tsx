import { useEffect, useState } from 'react'
import { Button, Card, Input, message, Space } from 'antd'
import { configApi } from '@/api/config'

const CRON_DRAFT_KEY = 'product_crawl_cron_draft'
const TZ_DRAFT_KEY = 'product_crawl_timezone_draft'

export default function ProductCrawlSettings() {
  const [cron, setCron] = useState('')
  const [timezone, setTimezone] = useState('Asia/Shanghai')
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(true)

  useEffect(() => {
    configApi.get().then((res) => {
      setCron(res.data.crawl_cron || res.data.default || '')
      setTimezone(res.data.crawl_timezone || 'Asia/Shanghai')
      setFetching(false)
    }).catch(() => {
      setFetching(false)
    })
  }, [])

  // Restore local draft if backend value differs from draft
  useEffect(() => {
    if (fetching) return
    const draft = localStorage.getItem(CRON_DRAFT_KEY)
    if (draft && draft !== cron) {
      const tz = localStorage.getItem(TZ_DRAFT_KEY) || 'Asia/Shanghai'
      message.info(`检测到未保存的草稿: ${draft}，已自动恢复`)
      setCron(draft)
      setTimezone(tz)
    }
  }, [fetching])

  const handleSave = async () => {
    if (!cron.trim()) {
      message.error('请输入 Cron 表达式')
      return
    }
    setLoading(true)
    try {
      await configApi.update({ crawl_cron: cron.trim(), crawl_timezone: timezone })
      localStorage.removeItem(CRON_DRAFT_KEY)
      localStorage.removeItem(TZ_DRAFT_KEY)
      message.success('保存成功')
    } catch {
      message.error('保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveDraft = () => {
    localStorage.setItem(CRON_DRAFT_KEY, cron)
    localStorage.setItem(TZ_DRAFT_KEY, timezone)
    message.success('草稿已保存到本地')
  }

  return (
    <Card size="small" title="商品爬取定时设置" style={{ marginBottom: 16 }}>
      <Space>
        <Input
          value={cron}
          onChange={(e) => setCron(e.target.value)}
          placeholder="0 9 * * *"
          style={{ width: 200 }}
          disabled={fetching}
          autoComplete="off"
          name="product-cron"
        />
        <Input
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          placeholder="Asia/Shanghai"
          style={{ width: 160 }}
          disabled={fetching}
          autoComplete="off"
          name="product-timezone"
        />
        <Button type="primary" onClick={handleSave} loading={loading}>
          保存
        </Button>
        <Button onClick={handleSaveDraft} disabled={fetching}>
          保存草稿
        </Button>
      </Space>
      <div style={{ marginTop: 8, color: '#888', fontSize: 12 }}>
        默认每天早上 9 点执行，格式为 5 段 cron 表达式（分 时 日 月 周）
      </div>
    </Card>
  )
}