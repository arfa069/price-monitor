import { useState, useMemo } from 'react'
import {
  Table, Button, Space, Input, Select, Tag, Popconfirm,
  Modal, Form, message, notification, Card, Row, Col,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ImportOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Product, BatchOperationResult } from '@/types'
import {
  useProducts, useCreateProduct, useUpdateProduct, useDeleteProduct,
  useBatchCreate, useBatchDelete, useBatchUpdate,
} from '@/hooks/api'
import BatchImportModal from '@/components/BatchImportModal'
import ProductFormModal from '@/components/ProductFormModal'

const PLATFORM_COLORS: Record<string, string> = {
  taobao: '#13c2c2',
  jd: '#722ed1',
  amazon: '#1890ff',
}

export default function ProductsPage() {
  const [page, setPage] = useState(1)
  const [size] = useState(15)
  const [filters, setFilters] = useState<Record<string, any>>({})
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [createFormOpen, setCreateFormOpen] = useState(false)
  const [editModal, setEditModal] = useState<{ open: boolean; record?: Product }>({ open: false })
  const [batchImportOpen, setBatchImportOpen] = useState(false)

  const { data, isLoading, refetch } = useProducts({ page, size, ...filters })
  const createMutation = useCreateProduct()
  const updateMutation = useUpdateProduct()
  const deleteMutation = useDeleteProduct()
  const batchCreate = useBatchCreate()
  const batchDelete = useBatchDelete()
  const batchUpdate = useBatchUpdate()

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
      render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag color="red">停用</Tag>,
      filters: [
        { text: '启用', value: true },
        { text: '停用', value: false },
      ],
      onFilter: (value: any, record: Product) => record.active === value,
    },
    { title: '创建时间', dataIndex: 'created_at', width: 180, render: (v: string) => new Date(v).toLocaleString('zh-CN') },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record: Product) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => setEditModal({ open: true, record })}>编辑</Button>
          <Popconfirm title="确定删除此商品？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], [deleteMutation])

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

  const handleFormSubmit = (values: any) => {
    if (editModal.record) {
      updateMutation.mutate({ id: editModal.record.id, data: values }, {
        onSuccess: () => {
          message.success('更新成功')
          setEditModal({ open: false })
        },
      })
    } else {
      createMutation.mutate(values, {
        onSuccess: () => {
          message.success('添加成功')
          setCreateFormOpen(false)
        },
        onError: () => message.error('添加失败'),
      })
    }
  }

  const handleBatchImport = (items: { url: string; platform: string; title?: string }[]) => {
    batchCreate.mutate(items as any, {
      onSuccess: (res) => {
        const results = res.data
        showBatchResult('批量导入', results)
      },
    })
  }

  return (
    <div>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
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
              </Space>
            </Col>
            <Col>
              <Space>
                <Input
                  placeholder="搜索标题/URL"
                  prefix={<SearchOutlined />}
                  allowClear
                  style={{ width: 200 }}
                  onChange={(e) => setFilters((f) => ({ ...f, keyword: e.target.value || undefined }))}
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
                  onChange={(v) => setFilters((f) => ({ ...f, platform: v }))}
                />
                <Select
                  placeholder="状态"
                  allowClear
                  style={{ width: 100 }}
                  options={[
                    { label: '启用', value: true },
                    { label: '停用', value: false },
                  ]}
                  onChange={(v) => setFilters((f) => ({ ...f, active: v }))}
                />
              </Space>
            </Col>
          </Row>
        </Card>

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
                <p style={{ color: '#888', marginBottom: 16 }}>暂无商品</p>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateFormOpen(true)}>
                  添加第一个商品
                </Button>
              </div>
            ),
          }}
        />

        {/* Selection info */}
        {selectedRowKeys.length > 0 && (
          <div style={{ color: '#888', fontSize: 12 }}>
            已选择 {selectedRowKeys.length} 项（仅当前页有效）
          </div>
        )}
      </Space>

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
    </div>
  )
}
