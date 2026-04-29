import { useState, useEffect } from 'react'
import { Layout, Menu, Button, Drawer } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  TeamOutlined,
  ShoppingCartOutlined,
  ReloadOutlined,
  BarsOutlined,
} from '@ant-design/icons'

const { Sider, Header, Footer } = Layout

const MOBILE_BREAKPOINT = 768

export default function AppLayout({
  children,
  onRefresh
}: {
  children: React.ReactNode
  onRefresh?: () => void
}) {
  const [collapsed, setCollapsed] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const selectedKey = location.pathname.startsWith('/jobs')
    ? '/jobs'
    : '/products'

  const siderWidth = collapsed ? 60 : 180

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
    // Close drawer on mobile after navigation
    if (isMobile) {
      setDrawerOpen(false)
    }
  }

  const menuItems = [
    {
      key: '/jobs',
      icon: <TeamOutlined />,
      label: '职位管理',
    },
    {
      key: '/products',
      icon: <ShoppingCartOutlined />,
      label: '商品管理',
    },
  ]

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
        {/* Logo - 品牌标识 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: 18,
              fontWeight: 800,
              fontFamily: 'system-ui, sans-serif',
              boxShadow: '0 2px 8px rgba(59, 130, 246, 0.4)',
            }}
          >
            价
          </div>
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
        </div>
        <div style={{ flex: 1 }} />
        {/* 移动端始终显示汉堡菜单按钮 */}
        {isMobile ? (
          <Button
            type="text"
            icon={<BarsOutlined />}
            style={{ color: '#fff' }}
            onClick={() => setDrawerOpen(true)}
            aria-label="打开菜单"
          />
        ) : (
          <>
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
              aria-label="刷新页面数据"
            >
              刷新
            </Button>
          </>
        )}
      </Header>

      {/* Desktop Sidebar - 固定在左侧，不超出 footer */}
      {!isMobile && (
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
            onClick={handleMenuClick}
            style={{
              border: 'none',
              background: 'transparent',
              marginTop: 8,
            }}
            items={menuItems}
          />
        </Sider>
      )}

      {/* Mobile Drawer */}
      {isMobile && (
        <Drawer
          placement="left"
          onClose={() => setDrawerOpen(false)}
          open={drawerOpen}
          width={220}
          styles={{
            body: { padding: 0, background: '#f8fafc' },
          }}
        >
          <div
            style={{
              padding: '20px 16px',
              borderBottom: '1px solid #e2e8f0',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 6,
                background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: 14,
                fontWeight: 800,
              }}
            >
              价
            </div>
            <span style={{ fontWeight: 600, color: '#334155' }}>价格监控系统</span>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            onClick={handleMenuClick}
            style={{
              border: 'none',
              background: 'transparent',
              marginTop: 8,
            }}
            items={menuItems}
          />
          <div style={{ padding: '16px' }}>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={() => {
                onRefresh?.()
                setDrawerOpen(false)
              }}
              block
            >
              刷新
            </Button>
          </div>
        </Drawer>
      )}

      {/* Content - 在 sidebar 和 footer 之间 */}
      <div
        style={{
          flex: 1,
          marginTop: 56,
          marginBottom: 56,
          marginLeft: isMobile ? 0 : siderWidth,
          padding: 20,
          background: '#fff',
          borderRadius: isMobile ? 0 : 8,
          boxShadow: isMobile ? 'none' : '0 1px 3px rgba(0,0,0,0.04)',
          minHeight: 'calc(100vh - 112px)',
          overflow: 'auto',
        }}
      >
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
