import { useState, useEffect } from 'react'
import { Layout, Menu, Button } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  ShoppingCartOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'

const { Sider, Content, Header, Footer } = Layout

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

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          background: '#001529',
        }}
      >
        <div
          style={{
            color: '#fff',
            fontSize: 18,
            fontWeight: 'bold',
          }}
        >
          价格监控系统
        </div>
        <div style={{ flex: 1 }} />
        <Button
          type="text"
          icon={<ReloadOutlined />}
          style={{ color: '#fff' }}
          onClick={onRefresh}
        >
          刷新
        </Button>
      </Header>
      <Layout>
        <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
          <div
            style={{
              height: 32,
              margin: 16,
              color: '#fff',
              fontSize: 16,
              fontWeight: 'bold',
              textAlign: 'center',
              overflow: 'hidden',
              whiteSpace: 'nowrap',
            }}
          >
            {collapsed ? '价' : '价格监控'}
          </div>
          <Menu
            theme="dark"
            selectedKeys={[selectedKey]}
            onClick={({ key }) => navigate(key)}
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
        <Layout>
          <Content
            style={{
              margin: '24px 16px',
              padding: 24,
              minHeight: 280,
              background: '#fff',
            }}
          >
            {children}
          </Content>
        </Layout>
      </Layout>
      <Footer
        style={{
          textAlign: 'center',
          padding: '12px 24px',
          background: '#001529',
          color: '#fff',
          fontSize: 12,
        }}
      >
        价格监控系统 v1.0 · 最后更新: {new Date().toLocaleString('zh-CN')}
      </Footer>
    </Layout>
  )
}
