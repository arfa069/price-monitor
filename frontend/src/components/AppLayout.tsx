import { useState, useEffect, useRef } from 'react'
import { App, Layout, Menu, Button, Drawer, Avatar, Space } from 'antd'
import type { MenuProps } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  TeamOutlined,
  ShoppingCartOutlined,
  ScheduleOutlined,
  BarsOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useAuth } from '@/contexts/AuthContext'
import { useThemeContext } from '@/components/ThemeProvider'

const MOBILE_BREAKPOINT = 768

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const appMessage = App.useApp().message
  const [collapsed, setCollapsed] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useThemeContext()

  const handleLogout = () => {
    logout()
    appMessage.success('已退出登录')
    navigate('/login', { replace: true })
  }

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined style={{ fontSize: 14 }} />,
      label: '个人信息',
      onClick: () => { setUserMenuOpen(false); navigate('/profile') },
    },
    {
      key: 'settings',
      icon: <SettingOutlined style={{ fontSize: 14 }} />,
      label: '账号设置',
      onClick: () => { setUserMenuOpen(false); navigate('/settings') },
    },
    ...(user?.role === 'admin' || user?.role === 'super_admin'
      ? [
        {
          key: 'admin/users',
          icon: <TeamOutlined style={{ fontSize: 14 }} />,
          label: '用户管理',
          onClick: () => { setUserMenuOpen(false); navigate('/admin/users') },
        },
        {
          key: 'admin/audit-logs',
          icon: <ScheduleOutlined style={{ fontSize: 14 }} />,
          label: '审计日志',
          onClick: () => { setUserMenuOpen(false); navigate('/admin/audit-logs') },
        },
      ]
      : []),
    { type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined style={{ fontSize: 14 }} />,
      label: '退出登录',
      danger: true,
      onClick: () => { setUserMenuOpen(false); handleLogout() },
    },
  ]

  // 点击外部关闭用户菜单
  useEffect(() => {
    if (!userMenuOpen) return
    const handleDocClick = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    // 用 setTimeout 确保当前点击事件不会立即触发关闭
    const timer = setTimeout(() => {
      document.addEventListener('click', handleDocClick)
    }, 0)
    return () => {
      clearTimeout(timer)
      document.removeEventListener('click', handleDocClick)
    }
  }, [userMenuOpen])

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const selectedKey = location.pathname.startsWith('/schedule')
    ? '/schedule'
    : location.pathname.startsWith('/jobs')
      ? '/jobs'
      : location.pathname.startsWith('/products')
        ? '/products'
        : location.pathname.startsWith('/admin')
          ? location.pathname
          : '/products'

  const siderWidth = collapsed ? 60 : 200

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
    if (isMobile) setDrawerOpen(false)
  }

  const menuItems = [
    {
      key: '/jobs',
      icon: <TeamOutlined style={{ fontSize: 14 }} />,
      label: '职位管理',
    },
    {
      key: '/products',
      icon: <ShoppingCartOutlined style={{ fontSize: 14 }} />,
      label: '商品管理',
    },
    {
      key: '/schedule',
      icon: <ScheduleOutlined style={{ fontSize: 14 }} />,
      label: '定时配置',
    },
    ...(user?.role === 'admin' || user?.role === 'super_admin'
      ? [
        {
          key: '/admin/users',
          icon: <TeamOutlined style={{ fontSize: 14 }} />,
          label: '用户管理',
        },
        {
          key: '/admin/audit-logs',
          icon: <ScheduleOutlined style={{ fontSize: 14 }} />,
          label: '审计日志',
        },
      ]
      : []),
  ]

  return (
    <Layout style={{ minHeight: '100vh', background: 'var(--color-canvas)' }}>
      {/* Top Nav */}
      <Layout.Header
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 300,
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          height: 56,
          background: 'var(--color-canvas)',
          borderBottom: '1px solid var(--color-hairline)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'var(--color-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-on-primary)',
              fontSize: 15,
              fontWeight: 700,
              fontFamily: "var(--font-body)",
              letterSpacing: '-0.5px',
            }}
          >
            价
          </div>
          <div
            style={{
              color: 'var(--color-ink)',
              fontSize: 18,
              fontWeight: 480,
              letterSpacing: '-0.2px',
              fontFamily: "var(--font-body)",
            }}
          >
            价格监控
          </div>
        </div>

        <div style={{ flex: 1 }} />

        {isMobile ? (
          <Button
            type="text"
            icon={<BarsOutlined />}
            style={{ color: 'var(--color-ink)', fontSize: 16 }}
            onClick={() => setDrawerOpen(true)}
            aria-label="打开菜单"
          />
        ) : (
          <>
            <Button
              type="text"
              onClick={toggleTheme}
              style={{
                color: 'var(--color-ink)',
                fontFamily: "var(--font-body)",
                borderRadius: 50,
                padding: '4px 10px',
                height: 36,
                fontSize: 16,
              }}
              aria-label={theme === 'light' ? '切换到暗色模式' : '切换到亮色模式'}
            >
              {theme === 'light' ? '🌙' : '☀️'}
            </Button>

            {/* 用户菜单 — 完全手动控制，绕过 antd Dropdown 事件 bug */}
            <div ref={userMenuRef} style={{ position: 'relative' }}>
              <Button
                type="text"
                style={{
                  color: 'var(--color-ink)',
                  height: 'auto',
                  padding: '4px 8px',
                  fontFamily: "var(--font-body)",
                  fontSize: 14,
                  fontWeight: 400,
                  borderRadius: 50,
                }}
                aria-label="用户菜单"
                onClick={(e) => {
                  e.stopPropagation()
                  setUserMenuOpen(prev => !prev)
                }}
              >
                <Space size={6}>
                  <Avatar
                    size={28}
                    icon={<UserOutlined />}
                    style={{
                      backgroundColor: 'var(--color-surface-soft)',
                      color: 'var(--color-ink)',
                      fontSize: 12,
                      border: '1px solid var(--color-hairline)',
                    }}
                  />
                  <span style={{ fontSize: 14, fontWeight: 400 }}>
                    {user?.username || '用户'}
                  </span>
                </Space>
              </Button>

              {userMenuOpen && (
                <div
                  style={{
                    position: 'absolute',
                    top: 'calc(100% + 4px)',
                    right: 0,
                    zIndex: 1050,
                    minWidth: 160,
                    background: 'var(--color-canvas)',
                    borderRadius: 12,
                    boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                    border: '1px solid var(--color-hairline)',
                    padding: '4px',
                    fontFamily: 'var(--font-body)',
                    fontSize: 14,
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <Menu
                    mode="vertical"
                    selectable={false}
                    items={userMenuItems}
                    style={{
                      border: 'none',
                      background: 'transparent',
                      boxShadow: 'none',
                    }}
                  />
                </div>
              )}
            </div>

            <Button
              type="text"
              icon={<BarsOutlined style={{ fontSize: 14 }} />}
              style={{
                color: 'var(--color-ink)',
                fontFamily: "var(--font-body)",
                borderRadius: 50,
                padding: '4px 10px',
                height: 36,
              }}
              onClick={() => setCollapsed(!collapsed)}
              aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
            />
          </>
        )}
      </Layout.Header>

      {/* Desktop Sidebar */}
      {!isMobile && (
        <Layout.Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          style={{
            position: 'fixed',
            top: 56,
            left: 0,
            bottom: 48,
            zIndex: 100,
            background: 'var(--color-surface-soft)',
            overflow: 'auto',
            borderRadius: '0 24px 24px 0',
            borderRight: '1px solid var(--color-hairline)',
            marginTop: 8,
            marginBottom: 8,
          }}
          width={200}
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
              marginTop: 12,
              padding: '0 8px',
            }}
            items={menuItems}
          />
        </Layout.Sider>
      )}

      {/* Mobile Drawer */}
      {isMobile && (
        <Drawer
          placement="left"
          onClose={() => setDrawerOpen(false)}
          open={drawerOpen}
          width={220}
          styles={{
            body: { padding: 0, background: 'var(--color-surface-soft)' },
            header: { display: 'none' },
          }}
        >
          <div
            style={{
              padding: '16px',
              borderBottom: '1px solid var(--color-hairline)',
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
                background: 'var(--color-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-on-primary)',
                fontSize: 13,
                fontWeight: 700,
              }}
            >
              价
            </div>
            <span
              style={{
                fontWeight: 480,
                fontSize: 15,
                color: 'var(--color-ink)',
                fontFamily: "var(--font-body)",
              }}
            >
              价格监控
            </span>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            onClick={handleMenuClick}
            style={{
              border: 'none',
              background: 'transparent',
              marginTop: 8,
              padding: '0 8px',
            }}
            items={menuItems}
          />
        </Drawer>
      )}

      {/* Main Content */}
      <div
        style={{
          flex: 1,
          marginTop: 56,
          marginBottom: 48,
          marginLeft: isMobile ? 0 : siderWidth,
          padding: '24px',
          background: 'var(--color-canvas)',
          minHeight: 'calc(100vh - 104px)',
          overflow: 'auto',
        }}
      >
        {children}
      </div>

      {/* Footer */}
      <Layout.Footer
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 300,
          textAlign: 'center',
          padding: '12px 24px',
          height: 48,
          background: 'var(--color-canvas)',
          color: 'var(--color-ink)',
          fontSize: 12,
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: '0.6px',
          textTransform: 'uppercase',
          borderTop: '1px solid var(--color-hairline)',
        }}
      >
        价格监控系统 © 2026
      </Layout.Footer>
    </Layout>
  )
}
