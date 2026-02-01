import React, { useEffect, useRef, useState } from 'react'
import { Card, Input, Select, Drawer, Tag, Space, Button, message } from 'antd'
import { SearchOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { ExtensionCategory, Graph, IElementEvent } from '@antv/g6'

const { Search } = Input
const { Option } = Select

// 模拟图谱数据
const mockGraphData = {
  nodes: [
    { id: 'BERT', label: 'BERT', type: 'Model', description: '双向编码器表示模型' },
    { id: 'GPT-3', label: 'GPT-3', type: 'Model', description: '生成式预训练Transformer' },
    { id: 'Transformer', label: 'Transformer', type: 'Method', description: '自注意力机制架构' },
    { id: 'Attention', label: 'Attention', type: 'Concept', description: '注意力机制' },
    { id: 'NLP', label: 'NLP', type: 'Concept', description: '自然语言处理' },
    { id: 'LLM', label: 'LLM', type: 'Concept', description: '大语言模型' },
    { id: 'ImageNet', label: 'ImageNet', type: 'Dataset', description: '图像分类数据集' },
    { id: 'COCO', label: 'COCO', type: 'Dataset', description: '目标检测数据集' },
    { id: 'Top-1', label: 'Top-1', type: 'Metric', description: 'Top-1准确率' },
    { id: 'Paper1', label: 'BERT论文', type: 'Paper', description: 'BERT原始论文' },
  ],
  edges: [
    { source: 'BERT', target: 'Transformer', label: 'BASED_ON' },
    { source: 'GPT-3', target: 'Transformer', label: 'BASED_ON' },
    { source: 'Transformer', target: 'Attention', label: 'USES' },
    { source: 'BERT', target: 'NLP', label: 'APPLIES_TO' },
    { source: 'GPT-3', target: 'LLM', label: 'PART_OF' },
    { source: 'BERT', target: 'GPT-3', label: 'COMPARES_TO' },
    { source: 'Paper1', target: 'BERT', label: 'PART_OF' },
  ],
}

// 节点类型颜色映射
const typeColors = {
  Concept: '#5470c6',
  Method: '#91cc75',
  Dataset: '#fac858',
  Model: '#ee6666',
  Metric: '#73c0de',
  Result: '#3ba272',
  Paper: '#fc8452',
}

function GraphVisualization() {
  const containerRef = useRef(null)
  const graphRef = useRef(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [layout, setLayout] = useState('force')
  const [depth, setDepth] = useState(2)
  
  useEffect(() => {
    if (!containerRef.current) return
    
    // 初始化G6图谱
    const graph = new Graph({
      container: containerRef.current,
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight || 600,
      background: '#f5f7fa',
      layout: {
        type: 'force',
        preventOverlap: true,
        linkDistance: 150,
      },
      node: {
        style: {
          size: (d) => d.type === 'Paper' ? 60 : 40,
          fill: (d) => typeColors[d.type] || '#999',
          stroke: '#fff',
          lineWidth: 2,
          labelText: (d) => d.label,
          labelFill: '#fff',
          labelFontSize: 12,
          labelFontWeight: 'bold',
        },
        state: {
          highlight: {
            stroke: '#1890ff',
            lineWidth: 4,
          },
        },
      },
      edge: {
        style: {
          stroke: '#999',
          lineWidth: 2,
          labelText: (d) => d.label,
          labelFontSize: 10,
          labelFill: '#666',
          endArrow: true,
        },
      },
      behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    })
    
    // 渲染数据
    graph.setData(mockGraphData)
    graph.render()
    
    // 绑定点击事件
    graph.on('node:click', (event) => {
      const nodeData = event.target.getData()
      setSelectedNode(nodeData)
      setDrawerVisible(true)
    })
    
    graphRef.current = graph
    
    // 响应窗口大小变化
    const handleResize = () => {
      if (containerRef.current && graphRef.current) {
        graphRef.current.setSize(
          containerRef.current.clientWidth,
          containerRef.current.clientHeight || 600
        )
      }
    }
    
    window.addEventListener('resize', handleResize)
    
    return () => {
      window.removeEventListener('resize', handleResize)
      graph.destroy()
    }
  }, [])
  
  // 搜索实体
  const handleSearch = (value) => {
    if (!graphRef.current || !value) return
    
    const graph = graphRef.current
    const nodes = graph.getNodeData()
    const targetNode = nodes.find(n => 
      n.label.toLowerCase().includes(value.toLowerCase())
    )
    
    if (targetNode) {
      graph.setElementState(targetNode.id, 'highlight')
      graph.focusElement(targetNode.id)
      setSelectedNode(targetNode)
      setDrawerVisible(true)
    } else {
      message.info('未找到匹配的实体')
    }
  }
  
  // 切换布局
  const handleLayoutChange = (value) => {
    setLayout(value)
    if (graphRef.current) {
      graphRef.current.setLayout({
        type: value,
        preventOverlap: true,
      })
      graphRef.current.layout()
    }
  }
  
  return (
    <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      {/* 顶部工具栏 */}
      <Card
        style={{ margin: 16, marginBottom: 0 }}
        bodyStyle={{ padding: '16px 24px' }}
        className="card-shadow"
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Search
            placeholder="搜索实体..."
            allowClear
            enterButton={<><SearchOutlined /> 搜索</>}
            onSearch={handleSearch}
            style={{ width: 300 }}
          />
          
          <Space>
            <span>布局:</span>
            <Select value={layout} onChange={handleLayoutChange} style={{ width: 120 }}>
              <Option value="force">力导向</Option>
              <Option value="circular">环形</Option>
              <Option value="grid">网格</Option>
            </Select>
            
            <span>层级:</span>
            <Select value={depth} onChange={setDepth} style={{ width: 80 }}>
              <Option value={1}>1跳</Option>
              <Option value={2}>2跳</Option>
              <Option value={3}>3跳</Option>
            </Select>
          </Space>
        </div>
      </Card>
      
      {/* 图谱容器 */}
      <div style={{ flex: 1, padding: 16, position: 'relative' }}>
        <Card
          className="card-shadow"
          bodyStyle={{ padding: 0, height: '100%' }}
          style={{ height: '100%' }}
        >
          <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
          
          {/* 图例 */}
          <div
            style={{
              position: 'absolute',
              bottom: 24,
              left: 24,
              background: 'rgba(255,255,255,0.95)',
              padding: '12px 16px',
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <div style={{ fontWeight: 'bold', marginBottom: 8 }}>图例</div>
            <Space direction="vertical" size="small">
              {Object.entries(typeColors).map(([type, color]) => (
                <div key={type} style={{ display: 'flex', alignItems: 'center' }}>
                  <span
                    style={{
                      width: 12,
                      height: 12,
                      background: color,
                      borderRadius: '50%',
                      marginRight: 8,
                    }}
                  />
                  <span>{type}</span>
                </div>
              ))}
            </Space>
          </div>
        </Card>
      </div>
      
      {/* 实体详情抽屉 */}
      <Drawer
        title="实体详情"
        placement="right"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={360}
      >
        {selectedNode && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <Tag
                color={typeColors[selectedNode.type] || '#999'}
                style={{ fontSize: 16, padding: '4px 12px' }}
              >
                {selectedNode.type}
              </Tag>
              <h2 style={{ marginTop: 12, marginBottom: 8 }}>{selectedNode.label}</h2>
            </div>
            
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ color: '#666', marginBottom: 8 }}>
                <InfoCircleOutlined /> 描述
              </h4>
              <p style={{ color: '#333', lineHeight: 1.6 }}>
                {selectedNode.description || '暂无描述'}
              </p>
            </div>
            
            <div>
              <h4 style={{ color: '#666', marginBottom: 8 }}>相关关系</h4>
              <Space direction="vertical" style={{ width: '100%' }}>
                {mockGraphData.edges
                  .filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
                  .map((edge, index) => {
                    const isSource = edge.source === selectedNode.id
                    const otherNode = isSource ? edge.target : edge.source
                    return (
                      <div
                        key={index}
                        style={{
                          padding: '8px 12px',
                          background: '#f5f5f5',
                          borderRadius: 4,
                          fontSize: 14,
                        }}
                      >
                        {isSource ? '→' : '←'} <strong>{otherNode}</strong>
                        <Tag style={{ marginLeft: 8 }} size="small">{edge.label}</Tag>
                      </div>
                    )
                  })}
              </Space>
            </div>
            
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Button type="primary" block>
                在图谱中高亮显示
              </Button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}

export default GraphVisualization