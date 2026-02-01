import React, { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Button,
  Input,
  Upload,
  Modal,
  Progress,
  Space,
  Tag,
  Popconfirm,
  message,
  Empty,
  Spin,
} from 'antd'
import {
  UploadOutlined,
  FileTextOutlined,
  EyeOutlined,
  DeleteOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { paperAPI } from '../services/api'

const { Search } = Input

// 模拟论文数据（实际应从API获取）
const mockPapers = [
  {
    paper_id: 'paper_001',
    title: 'BERT: Pre-training of Deep Bidirectional Transformers',
    total_chunks: 45,
    entities_extracted: 45,
    relations_extracted: 78,
    success: true,
  },
  {
    paper_id: 'paper_002',
    title: 'Language Models are Few-Shot Learners (GPT-3)',
    total_chunks: 62,
    entities_extracted: 62,
    relations_extracted: 105,
    success: true,
  },
  {
    paper_id: 'paper_003',
    title: 'Attention Is All You Need',
    total_chunks: 38,
    entities_extracted: 38,
    relations_extracted: 54,
    success: true,
  },
]

function PaperManagement() {
  const [papers, setPapers] = useState(mockPapers)
  const [loading, setLoading] = useState(false)
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [searchKeyword, setSearchKeyword] = useState('')
  
  // 过滤论文
  const filteredPapers = papers.filter(paper =>
    paper.title.toLowerCase().includes(searchKeyword.toLowerCase()) ||
    paper.paper_id.toLowerCase().includes(searchKeyword.toLowerCase())
  )
  
  // 上传论文
  const handleUpload = async (file) => {
    setUploading(true)
    setUploadProgress(0)
    
    // 模拟上传进度
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 90) {
          clearInterval(interval)
          return 90
        }
        return prev + 10
      })
    }, 500)
    
    try {
      // 实际API调用
      // const result = await paperAPI.upload(file)
      
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 3000))
      
      clearInterval(interval)
      setUploadProgress(100)
      
      // 添加新论文到列表
      const newPaper = {
        paper_id: `paper_${Date.now()}`,
        title: file.name.replace('.pdf', ''),
        total_chunks: Math.floor(Math.random() * 50) + 20,
        entities_extracted: Math.floor(Math.random() * 60) + 20,
        relations_extracted: Math.floor(Math.random() * 100) + 30,
        success: true,
      }
      
      setPapers([newPaper, ...papers])
      message.success('论文上传并处理成功！')
      setUploadModalVisible(false)
    } catch (error) {
      message.error('上传失败：' + error.message)
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
    
    return false // 阻止自动上传
  }
  
  // 删除论文
  const handleDelete = async (paperId) => {
    try {
      // await paperAPI.delete(paperId)
      setPapers(papers.filter(p => p.paper_id !== paperId))
      message.success('论文已删除')
    } catch (error) {
      message.error('删除失败：' + error.message)
    }
  }
  
  // 查看图谱
  const handleViewGraph = (paperId) => {
    // 导航到图谱页面并传递paperId
    window.location.href = `/graph?paper_id=${paperId}`
  }
  
  return (
    <div className="page-container">
      <Card
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 18, fontWeight: 500 }}>📄 论文管理</span>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setUploadModalVisible(true)}
            >
              上传论文
            </Button>
          </div>
        }
        className="card-shadow"
      >
        {/* 搜索栏 */}
        <div style={{ marginBottom: 24 }}>
          <Search
            placeholder="搜索论文标题或ID..."
            allowClear
            enterButton={<><SearchOutlined /> 搜索</>}
            size="large"
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            style={{ maxWidth: 500 }}
          />
        </div>
        
        {/* 论文列表 */}
        {loading ? (
          <div className="loading-spin">
            <Spin size="large" tip="加载中..." />
          </div>
        ) : filteredPapers.length > 0 ? (
          <Row gutter={[16, 16]}>
            {filteredPapers.map(paper => (
              <Col xs={24} sm={12} lg={8} key={paper.paper_id}>
                <Card
                  hoverable
                  className="card-shadow"
                  actions={[
                    <Button 
                      type="link" 
                      icon={<EyeOutlined />}
                      onClick={() => handleViewGraph(paper.paper_id)}
                    >
                      查看图谱
                    </Button>,
                    <Popconfirm
                      title="确定要删除这篇论文吗？"
                      description="删除后将无法恢复"
                      onConfirm={() => handleDelete(paper.paper_id)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button type="link" danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>,
                  ]}
                >
                  <Card.Meta
                    avatar={<FileTextOutlined style={{ fontSize: 32, color: '#1890ff' }} />}
                    title={
                      <div style={{ 
                        fontSize: 16, 
                        fontWeight: 500,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {paper.title}
                      </div>
                    }
                    description={
                      <Space direction="vertical" size="small" style={{ marginTop: 8 }}>
                        <Tag color="blue">{paper.paper_id}</Tag>
                        <div style={{ color: '#666', fontSize: 14 }}>
                          实体: <strong>{paper.entities_extracted}</strong> 个 | 
                          关系: <strong>{paper.relations_extracted}</strong> 个
                        </div>
                      </Space>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无论文数据"
          >
            <Button type="primary" onClick={() => setUploadModalVisible(true)}>
              上传论文
            </Button>
          </Empty>
        )}
      </Card>
      
      {/* 上传弹窗 */}
      <Modal
        title="上传论文"
        open={uploadModalVisible}
        onCancel={() => {
          if (!uploading) {
            setUploadModalVisible(false)
            setUploadProgress(0)
          }
        }}
        footer={[
          <Button 
            key="cancel" 
            onClick={() => setUploadModalVisible(false)}
            disabled={uploading}
          >
            取消
          </Button>,
        ]}
        closable={!uploading}
        maskClosable={!uploading}
      >
        <div style={{ padding: '20px 0' }}>
          <Upload.Dragger
            accept=".pdf"
            beforeUpload={handleUpload}
            showUploadList={false}
            disabled={uploading}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">点击或拖拽PDF文件到此区域上传</p>
            <p className="ant-upload-hint">
              支持单个PDF文件，系统将自动提取知识并构建图谱
            </p>
          </Upload.Dragger>
          
          {uploading && (
            <div style={{ marginTop: 24 }}>
              <Progress percent={uploadProgress} status="active" />
              <p style={{ textAlign: 'center', color: '#666', marginTop: 8 }}>
                正在处理论文，请稍候...
              </p>
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}

export default PaperManagement