import React, { useState } from 'react'
import { Layout, Menu, Button, theme } from 'antd'
import {
  FileTextOutlined,
  ApartmentOutlined,
  MessageOutlined,
  DatabaseOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'

const { Header, Sider, Content } = Layout

function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()
  
  const menuItems = [
    {
      key: '/papers',
      icon: <FileTextOutlined />,
      label: '论文管理',
    },
    {
      key: '/graph',
      icon: <ApartmentOutlined />,
      label: '知识图谱',
    },
    {
      key: '/qa',
      icon: <MessageOutlined />,
      label: '问答助手',
    },
    {
      key: '/entities',
      icon: <DatabaseOutlined />,
      label: '实体浏览',
    },
  ]
  
  const handleMenuClick = ({ key }) => {
    navigate(key)
  }
  
  const selectedKey = location.pathname === '/' ? '/papers' : location.pathname
  
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        theme="light"
        style={{
          boxShadow: '2px 0 8px rgba(0,0,0,0.08)',
          zIndex: 10,
        }}
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          borderBottom: '1px solid #f0f0f0',
          fontWeight: 'bold',
          fontSize: collapsed ? 14 : 18,
          color: '#1890ff',
        }}>
          {collapsed ? 'KG' : '知识图谱问答'}
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0 }}
        />
      </Sider>
      
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
            zIndex: 9,
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              fontSize: '16px',
              width: 42,
              height: 42,
            }}
          />
          <div style={{ fontSize: 16, fontWeight: 500 }}>
            知识图谱问答系统
          </div>
          <div style={{ width: 42 }} />
        </Header>
        
        <Content
          style={{
            margin: 0,
            padding: 0,
            minHeight: 280,
            background: '#f5f7fa',
            borderRadius: borderRadiusLG,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout