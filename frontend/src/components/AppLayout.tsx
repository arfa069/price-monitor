import { useState, useEffect } from 'react'
import { Layout, Menu, Button } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  ShoppingCartOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  BarsOutlined,
} from '@ant-design/icons'

const { Sider, Header, Footer } = Layout

export default function AppLayout({
  children,
  onRefresh
}: {
  children: React.ReactNode
  onRefresh?: () => void
}) {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const [selectedKey, setSelectedKey] = useState('/products')

  useEffect(() => {
    const path = location.pathname
    if (path.startsWith('/products')) setSelectedKey('/products')
    else if (path === '/schedule') setSelectedKey('/schedule')
  }, [location])

  const siderWidth = collapsed ? 60 : 180

  return (
    <Layout style={{ minHeight: '100vh', background: '#f1f5f9' }}>
      {/* Header - 固定在顶部 */}
      <Header
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          height: 56,
          background: '#0f172a',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        }}
      >
        <div
          style={{
            color: '#fff',
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: '-0.5px',
          }}
        >
          价格监控系统
        </div>
        <div style={{ flex: 1 }} />
        <Button
          type="text"
          icon={<BarsOutlined />}
          style={{ color: '#fff' }}
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? '展开菜单' : '收起菜单'}
        />
        <Button
          type="text"
          icon={<ReloadOutlined />}
          style={{ color: '#fff' }}
          onClick={onRefresh}
        >
          刷新
        </Button>
      </Header>

      {/* Sidebar - 固定在左侧，不超出 footer */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{
          position: 'fixed',
          top: 56,
          left: 0,
          bottom: 40,
          zIndex: 100,
          background: '#f8fafc',
          boxShadow: '1px 0 3px rgba(0,0,0,0.04)',
          overflow: 'auto',
        }}
        width={180}
        collapsedWidth={60}
        trigger={null}
      >
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={({ key }) => navigate(key)}
          style={{
            border: 'none',
            background: 'transparent',
            marginTop: 8,
          }}
          items={[
            {
              key: '/products',
              icon: <ShoppingCartOutlined />,
              label: '商品管理',
            },
            {
              key: '/schedule',
              icon: <ClockCircleOutlined />,
              label: '定时配置',
            },
          ]}
        />
      </Sider>

      {/* Content - 在 sidebar 和 footer 之间 */}
      <div
        style={{
          flex: 1,
          marginTop: 56,
          marginBottom: 56,
          marginLeft: siderWidth,
          padding: 20,
          background: '#fff',
          borderRadius: 8,
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          minHeight: 'calc(100vh - 112px)',
          overflow: 'auto',
        }}
      >
        {/* 覆盖 Card 边框，让子页面样式统一 */}
        <style>{`
          .ant-card-bordered {
            border: none !important;
            box-shadow: none !important;
          }
          .ant-table-wrapper {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            overflow: hidden;
          }
        `}</style>
        {children}
      </div>

      {/* Footer - 固定在底部 */}
      <Footer
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 1000,
          textAlign: 'center',
          padding: '12px 24px',
          height: 40,
          background: '#fff',
          color: '#94a3b8',
          fontSize: 12,
          borderTop: '1px solid #e2e8f0',
        }}
      >
        价格监控系统 v1.0
      </Footer>
    </Layout>
  )
}
