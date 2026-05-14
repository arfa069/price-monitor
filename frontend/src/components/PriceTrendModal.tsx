import { useMemo, useState, type ReactNode } from 'react'
import { Card, Empty, Modal, Segmented, Skeleton, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipValueType,
  XAxis,
  YAxis,
} from 'recharts'
import { useProductHistory } from '@/hooks/api'
import type { PriceHistoryRecord, Product } from '@/types'

interface PriceTrendModalProps {
  open: boolean
  product: Product | null | undefined
  onCancel: () => void
}

type TimeRange = 7 | 30 | 90 | 0

const formatTooltipValue = (value: TooltipValueType | undefined) => {
  const amount = Array.isArray(value) ? Number(value[0] ?? 0) : Number(value ?? 0)
  return [`¥${amount.toFixed(2)}`, 'Price'] as const
}

const formatTooltipLabel = (label: ReactNode) => {
  if (typeof label === 'string' || typeof label === 'number') {
    return new Date(label).toLocaleString('zh-CN')
  }
  return label
}

export default function PriceTrendModal({
  open,
  product,
  onCancel,
}: PriceTrendModalProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>(30)

  if (!open || !product) return null

  return (
    <Modal
      title={`${product.title || 'Product'} Price Trend`}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={760}
    >
      <PriceTrendContent
        productId={product.id}
        timeRange={timeRange}
        onTimeRangeChange={setTimeRange}
      />
    </Modal>
  )
}

interface PriceTrendContentProps {
  productId: number
  timeRange: TimeRange
  onTimeRangeChange: (range: TimeRange) => void
}

function PriceTrendContent({
  productId,
  timeRange,
  onTimeRangeChange,
}: PriceTrendContentProps) {
  const days = timeRange === 0 ? 3650 : timeRange
  const { data = [], isLoading, error } = useProductHistory(productId, days)

  const stats = useMemo(() => {
    if (data.length === 0) return null
    const prices = data.map((record) => Number(record.price))
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)
    const currentPrice = prices[prices.length - 1]
    let dropCount = 0
    for (let index = 1; index < prices.length; index += 1) {
      if (prices[index] < prices[index - 1]) {
        dropCount += 1
      }
    }
    return { minPrice, maxPrice, currentPrice, dropCount }
  }, [data])

  const priceTrend = useMemo(() => {
    if (data.length < 2) return null
    const first = Number(data[0].price)
    const last = Number(data[data.length - 1].price)
    const diff = last - first
    const percent = first === 0 ? 0 : Number((((diff / first) * 100)).toFixed(1))

    if (diff < 0) {
      return { color: 'green', text: `Drop ${Math.abs(percent)}%` }
    }
    if (diff > 0) {
      return { color: 'red', text: `Rise ${percent}%` }
    }
    return { color: 'default', text: 'Flat' }
  }, [data])

  const reversedData = useMemo(() => [...data].reverse(), [data])

  const tableColumns: ColumnsType<PriceHistoryRecord> = [
    {
      title: 'Date',
      dataIndex: 'scraped_at',
      width: 180,
      render: (value: string) => new Date(value).toLocaleString('zh-CN'),
    },
    {
      title: 'Price',
      dataIndex: 'price',
      render: (value: number, _record: PriceHistoryRecord, index: number) => {
        const numericValue = Number(value)
        const previousValue =
          index > 0 ? Number(reversedData[index - 1].price) : numericValue
        const color =
          numericValue < previousValue
            ? '#22c55e'
            : numericValue > previousValue
              ? '#ef4444'
              : undefined
        return <span style={{ color, fontWeight: 500 }}>¥{numericValue.toFixed(2)}</span>
      },
    },
  ]

  if (isLoading) {
    return <Skeleton active style={{ margin: '20px 0' }} />
  }

  if (error) {
    return (
      <Empty
        description={`Load failed: ${error instanceof Error ? error.message : 'Unknown error'}`}
        style={{ margin: '40px 0' }}
      />
    )
  }

  if (data.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 0' }}>
        <Empty description="No price records yet" />
      </div>
    )
  }

  return (
    <div style={{ padding: '16px 0' }}>
      <Segmented
        value={timeRange}
        onChange={(value) => onTimeRangeChange(value as TimeRange)}
        options={[
          { label: '7d', value: 7 },
          { label: '30d', value: 30 },
          { label: '90d', value: 90 },
          { label: 'All', value: 0 },
        ]}
        style={{ marginBottom: 16 }}
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 12,
          marginBottom: 20,
        }}
      >
        <Card size="small" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: 'var(--color-muted)' }}>Lowest</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--color-success)' }}>
            ¥{stats?.minPrice.toFixed(2)}
          </div>
        </Card>
        <Card size="small" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: 'var(--color-muted)' }}>Highest</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--color-error)' }}>
            ¥{stats?.maxPrice.toFixed(2)}
          </div>
        </Card>
        <Card size="small" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: 'var(--color-muted)' }}>Current</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--color-info)' }}>
            ¥{stats?.currentPrice.toFixed(2)}
          </div>
        </Card>
        <Card size="small" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: 'var(--color-muted)' }}>Drops</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--color-warning)' }}>
            {stats?.dropCount}
          </div>
        </Card>
      </div>

      {priceTrend && (
        <div style={{ marginBottom: 16 }}>
          <Tag color={priceTrend.color} style={{ fontSize: 14, padding: '4px 12px' }}>
            Period change: {priceTrend.text}
          </Tag>
        </div>
      )}

      <div style={{ width: '100%', height: 240, marginBottom: 20 }}>
        <ResponsiveContainer>
          <LineChart
            data={reversedData}
            margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
          >
            <XAxis
              dataKey="scraped_at"
              tickFormatter={(value: string) =>
                new Date(value).toLocaleDateString('zh-CN', {
                  month: '2-digit',
                  day: '2-digit',
                })
              }
              tick={{ fontSize: 12 }}
            />
            <YAxis
              tickFormatter={(value: number) => `¥${value}`}
              tick={{ fontSize: 12 }}
              width={60}
            />
            <Tooltip
              formatter={formatTooltipValue}
              labelFormatter={formatTooltipLabel}
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
        </ResponsiveContainer>
      </div>

      <Table
        size="small"
        dataSource={reversedData}
        columns={tableColumns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />
    </div>
  )
}
