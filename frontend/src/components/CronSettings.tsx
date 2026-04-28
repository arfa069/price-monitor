import { useEffect, useState } from 'react'
import { Button, Card, Input, message, Space } from 'antd'

import { configApi } from '@/api/config'

export default function CronSettings() {
  const [cron, setCron] = useState('')
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(true)

  useEffect(() => {
    configApi.getJobCrawlCron().then((res) => {
      setCron(res.data.job_crawl_cron || res.data.default || '')
      setFetching(false)
    }).catch(() => {
      setCron('0 9 * * *')
      setFetching(false)
    })
  }, [])

  const handleSave = async () => {
    setLoading(true)
    try {
      await configApi.updateJobCrawlCron(cron || null)
      message.success('保存成功')
    } catch {
      message.error('保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card size="small" title="职位爬取定时设置" style={{ marginBottom: 16 }}>
      <Space>
        <Input
          value={cron}
          onChange={(e) => setCron(e.target.value)}
          placeholder="0 9 * * *"
          style={{ width: 200 }}
          disabled={fetching}
        />
        <Button type="primary" onClick={handleSave} loading={loading}>
          保存
        </Button>
      </Space>
      <div style={{ marginTop: 8, color: '#888', fontSize: 12 }}>
        默认每天早上 9 点执行，格式为 5 段 cron 表达式（分 时 日 月 周）
      </div>
    </Card>
  )
}