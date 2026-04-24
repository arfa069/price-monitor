import React from 'react'
import { Modal, Segmented, Card, Table, Skeleton, Empty, Tag, Button } from 'antd'
import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts'
import type { Product } from '@/types'

interface PriceTrendModalProps {
  open: boolean
  product: Product | null | undefined
  onCancel: () => void
}

type TimeRange = 7 | 30 | 90 | 0

// 错误边界组件
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: any) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, textAlign: 'center' }}>
          <p style={{ color: '#ef4444' }}>渲染错误</p>
          <p style={{ fontSize: 12, color: '#666' }}>{this.state.error?.message}</p>
          <Button size="small" onClick={() => this.setState({ hasError: false, error: null })}>
            重试
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}

export default class PriceTrendModal extends React.Component<PriceTrendModalProps> {
  state: { timeRange: TimeRange } = {
    timeRange: 30,
  }

  setTimeRange = (value: TimeRange) => {
    this.setState({ timeRange: value })
  }

  render() {
    const { open, product, onCancel } = this.props
    const { timeRange } = this.state

    if (!open || !product) return null

    return (
      <Modal
        title={`${product.title} 价格趋势`}
        open={open}
        onCancel={onCancel}
        footer={null}
        width={700}
      >
        <ErrorBoundary>
          <PriceTrendContent
            productId={product.id}
            timeRange={timeRange}
            onTimeRangeChange={this.setTimeRange}
          />
        </ErrorBoundary>
      </Modal>
    )
  }
}

interface PriceTrendContentProps {
  productId: number
  timeRange: TimeRange
  onTimeRangeChange: (range: TimeRange) => void
}

function PriceTrendContent({ productId, timeRange, onTimeRangeChange }: PriceTrendContentProps) {
  // 模拟加载状态
  const [loading, setLoading] = React.useState(true)
  const [data, setData] = React.useState<any[]>([])
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    setLoading(true)
    setError(null)
    fetch(`/api/products/${productId}/history?days=${timeRange === 0 ? '' : timeRange}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((json) => {
        setData(json)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [productId, timeRange])

  const options = [
    { label: '7天', value: 7 },
    { label: '30天', value: 30 },
    { label: '90天', value: 90 },
    { label: '全部', value: 0 },
  ]

  // 计算统计
  const stats = React.useMemo(() => {
    if (!data || data.length === 0) return null
    const prices = data.map((r) => Number(r.price))  // 转换为数字
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)
    const currentPrice = prices[prices.length - 1]
    let dropCount = 0
    for (let i = 1; i < prices.length; i++) {
      if (prices[i] < prices[i - 1]) dropCount++
    }
    return { minPrice, maxPrice, currentPrice, dropCount }
  }, [data])

  // 价格变化趋势标签
  const priceTrend = React.useMemo(() => {
    if (!data || data.length < 2) return null
    const first = Number(data[0].price)
    const last = Number(data[data.length - 1].price)
    const diff = last - first
    const percent = ((diff / first) * 100).toFixed(1)
    if (diff < 0) {
      return { color: 'green', text: `↓ ${Math.abs(Number(percent))}% (降)` }
    } else if (diff > 0) {
      return { color: 'red', text: `↑ ${percent}% (涨)` }
    }
    return { color: 'default', text: '持平' }
  }, [data])

  const tableColumns = [
    {
      title: '时间',
      dataIndex: 'scraped_at',
      width: 180,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '价格',
      dataIndex: 'price',
      render: (v: any, _: any, idx: number) => {
        const numV = Number(v)
        const prev = idx > 0 ? Number(data[idx - 1].price) : numV
        const color = numV < prev ? '#22c55e' : numV > prev ? '#ef4444' : undefined
        return <span style={{ color, fontWeight: 500 }}>¥{numV.toFixed(2)}</span>
      },
    },
  ]

  if (loading) return <Skeleton active style={{ margin: '20px 0' }} />

  if (error) return <Empty description={`加载失败: ${error}`} style={{ margin: '40px 0' }} />

  if (!data || data.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 0' }}>
        <Empty description="暂无价格记录" />
      </div>
    )
  }

  return (
    <div style={{ padding: '16px 0' }}>
      {/* 时间范围选择 */}
      <Segmented
        value={timeRange}
        onChange={(v) => onTimeRangeChange(v as TimeRange)}
        options={options}
        style={{ marginBottom: 16 }}
      />

      {/* 统计卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        <Card size="small" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#64748b' }}>最低价</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#22c55e' }}>¥{stats?.minPrice.toFixed(2)}</div>
        </Card>
        <Card size="small" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#64748b' }}>最高价</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#ef4444' }}>¥{stats?.maxPrice.toFixed(2)}</div>
        </Card>
        <Card size="small" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#64748b' }}>当前价</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#2563eb' }}>¥{stats?.currentPrice.toFixed(2)}</div>
        </Card>
        <Card size="small" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#64748b' }}>降价次数</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#f97316' }}>{stats?.dropCount}次</div>
        </Card>
      </div>

      {/* 价格趋势 */}
      {priceTrend && (
        <div style={{ marginBottom: 16 }}>
          <Tag color={priceTrend.color} style={{ fontSize: 14, padding: '4px 12px' }}>
            周期内变化: {priceTrend.text}
          </Tag>
        </div>
      )}

      {/* 价格折线图 */}
      <div style={{ width: '100%', height: 200, marginBottom: 20 }} id="chart-container">
        <LineChart width={600} height={200} data={[...data].reverse()} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <XAxis
            dataKey="scraped_at"
            tickFormatter={(v) => new Date(v).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            tickFormatter={(v) => `¥${v}`}
            tick={{ fontSize: 12 }}
            domain={['dataMin - 1', 'dataMax + 1']}
            width={60}
          />
          <Tooltip
            formatter={(value: any) => [`¥${Number(value).toFixed(2)}`, '价格']}
            labelFormatter={(label) => new Date(label).toLocaleString('zh-CN')}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#2563eb"
            strokeWidth={2}
            dot={{ fill: '#2563eb', strokeWidth: 0, r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </div>

      {/* 价格记录表格 */}
      <Table
        size="small"
        dataSource={[...data].reverse()}
        columns={tableColumns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />
    </div>
  )
}
