import { useState, useMemo, useEffect } from 'react'
import {
  Table, Button, Space, Input, Select, Tag, Popconfirm,
  Card, message, notification, Row, Col, Alert, Tooltip,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ImportOutlined,
  SearchOutlined, LineChartOutlined, ExportOutlined,
  RocketOutlined, ReloadOutlined, HistoryOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Product, BatchOperationResult, BatchImportRow, ProductFormValues, CrawlLog } from '@/types'
import {
  useProducts, useCreateProduct, useUpdateProduct, useDeleteProduct,
  useBatchCreate, useBatchDelete, useBatchUpdate, useCrawlNow, useAllAlerts,
  useCrawlLogs,
} from '@/hooks/api'
import BatchImportModal from '@/components/BatchImportModal'
import ProductFormModal from '@/components/ProductFormModal'
import PriceTrendModal from '@/components/PriceTrendModal'

const PLATFORM_COLORS: Record<string, string> = {
  taobao: '#f97316',
  jd: '#dc2626',
  amazon: '#2563eb',
}

export default function ProductsPage() {
  const [page, setPage] = useState(1)
  const [size] = useState(15)
  const [platform, setPlatform] = useState<string | undefined>()
  const [active, setActive] = useState<boolean | undefined>()
  const [keyword, setKeyword] = useState('')
  const [debouncedKeyword, setDebouncedKeyword] = useState('')
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [createFormOpen, setCreateFormOpen] = useState(false)
  const [editModal, setEditModal] = useState<{ open: boolean; record?: Product }>({ open: false })
  const [batchImportOpen, setBatchImportOpen] = useState(false)
  const [trendModal, setTrendModal] = useState<{ open: boolean; product?: Product }>({ open: false })

  // Debounce keyword: delay 400ms after last keystroke
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedKeyword(keyword), 400)
    return () => clearTimeout(timer)
  }, [keyword])

  const { data, isLoading, isError, refetch } = useProducts({
    page,
    size,
    platform,
    active,
    keyword: debouncedKeyword || undefined,
  })
  const createMutation = useCreateProduct()
  const updateMutation = useUpdateProduct()
  const deleteMutation = useDeleteProduct()
  const batchCreate = useBatchCreate()
  const batchDelete = useBatchDelete()
  const batchUpdate = useBatchUpdate()
  const crawlNow = useCrawlNow()
  const { data: crawlLogs, isLoading: logsLoading, refetch: refetchLogs } = useCrawlLogs({ limit: 10 })
  const { data: alertsData } = useAllAlerts()
  const alertMap = useMemo(() => {
    const map = new Map<number, { threshold_percent: number; active: boolean }>()
    alertsData?.forEach((alert) => {
      map.set(alert.product_id, {
        threshold_percent: alert.threshold_percent || 0,
        active: alert.active,
      })
    })
    return map
  }, [alertsData])

  // Auto-rollback page when current page becomes empty after batch delete
  useEffect(() => {
    if (data && data.items.length === 0 && data.total > 0 && page > 1) {
      setPage(page => page - 1)
    }
  }, [data?.items?.length, data?.total])

  const columns: ColumnsType<Product> = useMemo(() => [
    { title: 'ID', dataIndex: 'id', width: 60, sorter: true },
    {
      title: '平台',
      dataIndex: 'platform',
      width: 90,
      render: (v: string) => (
        <Tag color={PLATFORM_COLORS[v] || 'default'}>
          {v === 'taobao' ? '淘宝' : v === 'jd' ? '京东' : '亚马逊'}
        </Tag>
      ),
      filters: [
        { text: '淘宝', value: 'taobao' },
        { text: '京东', value: 'jd' },
        { text: '亚马逊', value: 'amazon' },
      ],
      onFilter: (value: any, record: Product) => record.platform === value,
    },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'active',
      width: 80,
      render: (v: boolean) => v ? <Tag color="success">启用</Tag> : <Tag color="error">停用</Tag>,
      filters: [
        { text: '启用', value: true },
        { text: '停用', value: false },
      ],
      onFilter: (value: any, record: Product) => record.active === value,
    },
    { title: '创建时间', dataIndex: 'created_at', width: 180, render: (v: string) => new Date(v).toLocaleString('zh-CN') },
    {
      title: '告警',
      key: 'alert',
      width: 80,
      render: (_: any, record: Product) => {
        const alert = alertMap.get(record.id)
        if (!alert) return <Tag>未设置</Tag>
        return alert.active ? (
          <Tag color="orange">{String(alert.threshold_percent)}%</Tag>
        ) : (
          <Tag color="default">{String(alert.threshold_percent)}% (停用)</Tag>
        )
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 380,
      render: (_, record: Product) => (
        <Space size={4}>
          <Button size="small" icon={<ExportOutlined />} onClick={() => window.open(record.url, '_blank')}>查看</Button>
          <Button size="small" icon={<LineChartOutlined />} onClick={() => setTrendModal({ open: true, product: record })}>趋势</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => setEditModal({ open: true, record })}>编辑</Button>
          <Popconfirm title="确定删除此商品？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], [])  // deleteMutation stable — no need in deps

  const handleDelete = (id: number) => {
    deleteMutation.mutate(id, {
      onSuccess: () => message.success('删除成功'),
      onError: () => message.error('删除失败'),
    })
  }

  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) return
    batchDelete.mutate(selectedRowKeys as number[], {
      onSuccess: (res) => {
        const results = res.data
        showBatchResult('批量删除', results)
        setSelectedRowKeys([])
      },
      onError: (err: any) => message.error('批量操作失败：' + (err.message || '未知错误')),
    })
  }

  const handleBatchUpdate = (active: boolean) => {
    if (selectedRowKeys.length === 0) return
    batchUpdate.mutate({ ids: selectedRowKeys as number[], active }, {
      onSuccess: (res) => {
        const results = res.data
        showBatchResult(active ? '批量启用' : '批量停用', results)
        setSelectedRowKeys([])
      },
      onError: (err: any) => message.error('批量操作失败：' + (err.message || '未知错误')),
    })
  }

  const showBatchResult = (action: string, results: BatchOperationResult[]) => {
    const successCount = results.filter((r) => r.success).length
    const failCount = results.length - successCount
    const failedItems = results.filter((r) => !r.success)

    message.success(`${action}: ${successCount} 成功`)
    if (failCount > 0) {
      notification.error({
        message: `${action}: ${failCount} 失败`,
        description: failedItems.map((r) => `${r.url || `ID:${r.id}`} - ${r.error}`).join('\n'),
        duration: 0,
      })
    }
  }

  const handleFormSubmit = (values: ProductFormValues) => {
    if (editModal.record) {
      updateMutation.mutate({ id: editModal.record.id, data: values }, {
        onSuccess: () => {
          message.success('更新成功')
          setEditModal({ open: false })
        },
      })
    } else {
      createMutation.mutate(values as ProductFormValues & { platform: NonNullable<ProductFormValues['platform']> }, {
        onSuccess: () => {
          message.success('添加成功')
          setCreateFormOpen(false)
        },
        onError: (err: any) => message.error('添加失败：' + (err.message || '未知错误')),
      })
    }
  }

  const handleBatchImport = (items: BatchImportRow[]) => {
    batchCreate.mutate(items as any, {
      onSuccess: (res) => {
        const results = res.data
        showBatchResult('批量导入', results)
      },
    })
  }

  const handleCrawlNow = () => {
    message.loading({ content: '正在启动爬取任务...', key: 'crawl', duration: 0 })
    crawlNow.mutate(undefined, {
      onSuccess: (res: any) => {
        if (res.type === 'skipped') {
          message.warning({ content: '没有需要爬取的活跃商品', key: 'crawl' })
        } else if (res.type === 'error') {
          message.error({ content: '爬取失败：' + (res.reason || '未知错误'), key: 'crawl' })
        } else {
          message.success({
            content: `爬取完成：${res.success || 0} 成功，${res.errors || 0} 失败`,
            key: 'crawl',
          })
        }
      },
      onError: (err: any) => {
        message.error({ content: '爬取请求失败：' + (err.message || '未知错误'), key: 'crawl' })
      },
    })
  }

  return (
    <div>
      <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
        {/* Action bar */}
        <Card size="small">
          <Row gutter={[8, 8]} align="middle">
            <Col flex="auto">
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateFormOpen(true)}>新增</Button>
                <Button icon={<ImportOutlined />} onClick={() => setBatchImportOpen(true)}>批量导入</Button>
                <Popconfirm title="确定删除选中项？" onConfirm={handleBatchDelete} disabled={selectedRowKeys.length === 0}>
                  <Button danger icon={<DeleteOutlined />} disabled={selectedRowKeys.length === 0}>批量删除</Button>
                </Popconfirm>
                <Button onClick={() => handleBatchUpdate(true)} disabled={selectedRowKeys.length === 0}>批量启用</Button>
                <Button onClick={() => handleBatchUpdate(false)} disabled={selectedRowKeys.length === 0}>批量停用</Button>
                <Button icon={<RocketOutlined />} onClick={handleCrawlNow} loading={crawlNow.isPending}>手动爬取</Button>
              </Space>
            </Col>
            <Col>
              <Space>
                <Input
                  placeholder="搜索标题/URL"
                  prefix={<SearchOutlined />}
                  allowClear
                  style={{ width: 200 }}
                  onChange={(e) => setKeyword(e.target.value)}
                />
                <Select
                  placeholder="平台"
                  allowClear
                  style={{ width: 120 }}
                  options={[
                    { label: '淘宝', value: 'taobao' },
                    { label: '京东', value: 'jd' },
                    { label: '亚马逊', value: 'amazon' },
                  ]}
                  onChange={(v) => setPlatform(v)}
                />
                <Select
                  placeholder="状态"
                  allowClear
                  style={{ width: 100 }}
                  options={[
                    { label: '启用', value: true },
                    { label: '停用', value: false },
                  ]}
                  onChange={(v) => setActive(v)}
                />
              </Space>
            </Col>
          </Row>
        </Card>

        {/* Error state */}
        {isError && (
          <Alert
            type="error"
            message="加载失败"
            description="无法获取商品列表，请检查网络或重试。"
            action={<Button size="small" onClick={() => refetch()}>重试</Button>}
            style={{ marginBottom: 16 }}
          />
        )}

        {/* Data table */}
        <Table<Product>
          rowKey="id"
          columns={columns}
          dataSource={data?.items || []}
          loading={isLoading}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys),
          }}
          pagination={{
            current: page,
            pageSize: size,
            total: data?.total || 0,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p) => setPage(p),
            showSizeChanger: false,
          }}
          locale={{
            emptyText: (
              <div style={{ padding: '40px 0' }}>
                <p style={{ color: '#64748b', marginBottom: 16 }}>暂无商品</p>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateFormOpen(true)}>
                  添加第一个商品
                </Button>
              </div>
            ),
          }}
        />

        {/* Selection info */}
        {selectedRowKeys.length > 0 && (
          <div style={{ color: '#64748b', fontSize: 12 }}>
            已选择 {selectedRowKeys.length} 项（仅当前页有效）
          </div>
        )}
      </Space>

      {/* Crawl Logs Panel */}
      <Card
        size="small"
        title={
          <Space>
            <HistoryOutlined />
            最近爬取记录
            {crawlLogs && (
              <span style={{ fontSize: 12, color: '#64748b' }}>
                ({crawlLogs.length} 条)
              </span>
            )}
          </Space>
        }
        extra={
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => refetchLogs()}
            loading={logsLoading}
          >
            刷新
          </Button>
        }
        style={{ marginTop: 16 }}
      >
        {logsLoading && ((crawlLogs as unknown as CrawlLog[])?.length ?? 0) === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: '#64748b' }}>
            加载中...
          </div>
        ) : crawlLogs && crawlLogs.length > 0 ? (
          <Table
            size="small"
            dataSource={crawlLogs}
            rowKey="id"
            pagination={false}
            scroll={{ x: 800 }}
            columns={[
              {
                title: '时间',
                dataIndex: 'timestamp',
                width: 160,
                render: (v: string) => new Date(v).toLocaleString('zh-CN'),
              },
              {
                title: '平台',
                dataIndex: 'platform',
                width: 80,
                render: (v: string) => {
                  const colors: Record<string, string> = { taobao: '#f97316', jd: '#dc2626', amazon: '#2563eb' }
                  return <Tag color={colors[v] || 'default'}>{v === 'taobao' ? '淘宝' : v === 'jd' ? '京东' : v || '-'}</Tag>
                },
              },
              {
                title: '状态',
                dataIndex: 'status',
                width: 100,
                render: (v: string) => {
                  const config: Record<string, { color: string; text: string }> = {
                    SUCCESS: { color: 'success', text: '成功' },
                    ERROR: { color: 'error', text: '失败' },
                    SKIPPED: { color: 'default', text: '跳过' },
                  }
                  const c = config[v] || { color: 'default', text: v || '-' }
                  return <Tag color={c.color}>{c.text}</Tag>
                },
              },
              {
                title: '价格',
                dataIndex: 'price',
                width: 100,
                render: (v: number) => v ? `¥${v}` : '-',
              },
              {
                title: '错误信息',
                dataIndex: 'error_message',
                ellipsis: true,
                render: (v: string) => v ? (
                  <Tooltip title={v}>
                    <span style={{ color: '#dc2626' }}>{v}</span>
                  </Tooltip>
                ) : '-',
              },
            ]}
          />
        ) : (
          <div style={{ padding: 20, textAlign: 'center', color: '#64748b' }}>
            暂无爬取记录
          </div>
        )}
      </Card>

      {/* Create/Edit modal */}
      <ProductFormModal
        open={createFormOpen || editModal.open}
        record={editModal.record}
        onCancel={() => { setCreateFormOpen(false); setEditModal({ open: false }) }}
        onSubmit={handleFormSubmit}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      />

      {/* Batch import modal */}
      <BatchImportModal
        open={batchImportOpen}
        onCancel={() => setBatchImportOpen(false)}
        onImport={handleBatchImport}
        confirmLoading={batchCreate.isPending}
        existingUrls={data?.items.map((p) => p.url) || []}
      />

      {/* Price trend modal */}
      <PriceTrendModal
        open={trendModal.open}
        product={trendModal.product}
        onCancel={() => setTrendModal({ open: false })}
      />
    </div>
  )
}
