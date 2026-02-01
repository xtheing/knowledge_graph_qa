import React, { useState, useEffect } from 'react'
import {
  Card,
  Input,
  Select,
  Row,
  Col,
  Tag,
  Space,
  Button,
  Modal,
  Pagination,
  Empty,
  Statistic,
  Tooltip,
} from 'antd'
import {
  SearchOutlined,
  EyeOutlined,
  ApartmentOutlined,
  InfoCircleOutlined,
  TagOutlined,
  FileTextOutlined,
  LinkOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'

const { Search } = Input
const { Option } = Select

// 实体类型选项
const entityTypes = ['全部', 'Concept', 'Method', 'Dataset', 'Model', 'Metric', 'Result', 'Paper']

// 模拟实体数据
const mockEntities = [
  { id: 1, name: 'BERT', type: 'Model', description: '双向编码器表示模型', paperId: 'paper_001', relations: 12 },
  { id: 2, name: 'GPT-3', type: 'Model', description: '生成式预训练Transformer', paperId: 'paper_002', relations: 15 },
  { id: 3, name: 'Transformer', type: 'Method', description: '自注意力机制架构', paperId: 'paper_003', relations: 18 },
  { id: 4, name: 'ImageNet', type: 'Dataset', description: '大规模图像分类数据集', paperId: 'paper_001', relations: 8 },
  { id: 5, name: 'COCO', type: 'Dataset', description: '目标检测和分割数据集', paperId: 'paper_002', relations: 6 },
  { id: 6, name: 'Top-1 Accuracy', type: 'Metric', description: 'Top-1准确率', paperId: 'paper_001', relations: 5 },
  { id: 7, name: 'NLP', type: 'Concept', description: '自然语言处理', paperId: 'paper_001', relations: 10 },
  { id: 8, name: 'LLM', type: 'Concept', description: '大语言模型', paperId: 'paper_002', relations: 14 },
  { id: 9, name: 'ResNet', type: 'Model', description: '残差神经网络', paperId: 'paper_003', relations: 9 },
  { id: 10, name: 'BERT论文', type: 'Paper', description: 'BERT原始论文', paperId: 'paper_001', relations: 45 },
]

// 类型颜色映射
const typeColors = {
  Concept: '#5470c6',
  Method: '#91cc75',
  Dataset: '#fac858',
  Model: '#ee6666',
  Metric: '#73c0de',
  Result: '#3ba272',
  Paper: '#fc8452',
}

function EntityBrowser() {
  const [entities, setEntities] = useState(mockEntities)
  const [filteredEntities, setFilteredEntities] = useState(mockEntities)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [selectedType, setSelectedType] = useState('全部')
  const [selectedPaper, setSelectedPaper] = useState('全部')
  const [currentPage, setCurrentPage] = useState(1)
  const [modalVisible, setModalVisible] = useState(false)
  const [selectedEntity, setSelectedEntity] = useState(null)
  const pageSize = 9
  
  // 统计信息
  const stats = {
    total: entities.length,
    byType: entityTypes.slice(1).map(type => ({
      type,
      count: entities.filter(e => e.type === type).length,
    })).filter(item => item.count > 0),
  }
  
  // 过滤实体
  useEffect(() => {
    let result = entities
    
    if (searchKeyword) {
      result = result.filter(e => 
        e.name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
        e.description.toLowerCase().includes(searchKeyword.toLowerCase())
      )
    }
    
    if (selectedType !== '全部') {
      result = result.filter(e => e.type === selectedType)
    }
    
    if (selectedPaper !== '全部') {
      result = result.filter(e => e.paperId === selectedPaper)
    }
    
    setFilteredEntities(result)
    setCurrentPage(1)
  }, [searchKeyword, selectedType, selectedPaper, entities])
  
  // 分页数据
  const paginatedEntities = filteredEntities.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )
  
  // 查看实体详情
  const handleViewEntity = (entity) => {
    setSelectedEntity({
      ...entity,
      relations: [
        { to: 'Transformer', type: 'BASED_ON' },
        { to: 'NLP', type: 'APPLIES_TO' },
        { to: 'GPT-3', type: 'COMPARES_TO' },
        { to: 'Attention', type: 'USES' },
      ],
    })
    setModalVisible(true)
  }
  
  // 在图谱中查看
  const handleViewInGraph = (entityName) => {
    window.location.href = `/graph?entity=${encodeURIComponent(entityName)}`
  }
  
  return (
    <div className="page-container">
      <Card className="card-shadow">
        {/* 标题和统计 */}
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ marginBottom: 16 }}>
            <DatabaseOutlined /> 实体浏览器
          </h2>
          <Space size="large">
            <Statistic title="总实体数" value={stats.total} />
            {stats.byType.map(item => (
              <Statistic 
                key={item.type}
                title={item.type}
                value={item.count}
                valueStyle={{ color: typeColors[item.type] }}
              />
            ))}
          </Space>
        </div>
        
        {/* 搜索和筛选 */}
        <div style={{ marginBottom: 24 }}>
          <Row gutter={16}>
            <Col flex="auto">
              <Search
                placeholder="搜索实体名称或描述..."
                allowClear
                enterButton={<><SearchOutlined /> 搜索</>}
                size="large"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
              />
            </Col>
            <Col>
              <Select
                placeholder="实体类型"
                value={selectedType}
                onChange={setSelectedType}
                style={{ width: 140 }}
                size="large"
              >
                {entityTypes.map(type => (
                  <Option key={type} value={type}>{type}</Option>
                ))}
              </Select>
            </Col>
            <Col>
              <Select
                placeholder="论文"
                value={selectedPaper}
                onChange={setSelectedPaper}
                style={{ width: 140 }}
                size="large"
              >
                <Option value="全部">全部论文</Option>
                <Option value="paper_001">paper_001</Option>
                <Option value="paper_002">paper_002</Option>
                <Option value="paper_003">paper_003</Option>
              </Select>
            </Col>
          </Row>
        </div>
        
        {/* 实体列表 */}
        {paginatedEntities.length > 0 ? (
          <>
            <Row gutter={[16, 16]}>
              {paginatedEntities.map(entity => (
                <Col xs={24} sm={12} lg={8} key={entity.id}>
                  <Card
                    hoverable
                    className="card-shadow"
                    actions={[
                      <Tooltip title="查看详情">
                        <Button 
                          type="link" 
                          icon={<EyeOutlined />}
                          onClick={() => handleViewEntity(entity)}
                        >
                          查看
                        </Button>
                      </Tooltip>,
                      <Tooltip title="在图谱中查看">
                        <Button 
                          type="link" 
                          icon={<ApartmentOutlined />}
                          onClick={() => handleViewInGraph(entity.name)}
                        >
                          图谱
                        </Button>
                      </Tooltip>,
                    ]}
                  >
                    <div style={{ marginBottom: 12 }}>
                      <Tag 
                        color={typeColors[entity.type] || '#999'}
                        style={{ fontSize: 12, marginBottom: 8 }}
                      >
                        {entity.type}
                      </Tag>
                    </div>
                    <h3 style={{ marginBottom: 8, fontSize: 18 }}>{entity.name}</h3>
                    <p style={{ color: '#666', marginBottom: 12, height: 40, overflow: 'hidden' }}>
                      {entity.description}
                    </p>
                    <Space>
                      <Tag icon={<FileTextOutlined />} size="small">
                        {entity.paperId}
                      </Tag>
                      <Tag icon={<LinkOutlined />} color="blue" size="small">
                        {entity.relations} 关系
                      </Tag>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
            
            {/* 分页 */}
            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <Pagination
                current={currentPage}
                total={filteredEntities.length}
                pageSize={pageSize}
                onChange={setCurrentPage}
                showSizeChanger={false}
                showQuickJumper
                showTotal={(total) => `共 ${total} 个实体`}
              />
            </div>
          </>
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="未找到匹配的实体"
          />
        )}
      </Card>
      
      {/* 实体详情弹窗 */}
      <Modal
        title="实体详情"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setModalVisible(false)}>
            关闭
          </Button>,
          <Button 
            key="graph" 
            type="primary"
            icon={<ApartmentOutlined />}
            onClick={() => {
              setModalVisible(false)
              handleViewInGraph(selectedEntity?.name)
            }}
          >
            在图谱中查看
          </Button>,
        ]}
        width={560}
      >
        {selectedEntity && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <Tag
                color={typeColors[selectedEntity.type] || '#999'}
                style={{ fontSize: 16, padding: '4px 16px', marginBottom: 12 }}
              >
                {selectedEntity.type}
              </Tag>
              <h2 style={{ margin: '8px 0' }}>{selectedEntity.name}</h2>
            </div>
            
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ color: '#666', marginBottom: 8 }}>
                <InfoCircleOutlined /> 描述
              </h4>
              <p style={{ lineHeight: 1.6, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                {selectedEntity.description}
              </p>
            </div>
            
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ color: '#666', marginBottom: 8 }}>
                <FileTextOutlined /> 来源
              </h4>
              <Tag color="blue">{selectedEntity.paperId}</Tag>
            </div>
            
            <div>
              <h4 style={{ color: '#666', marginBottom: 8 }}>
                <LinkOutlined /> 相关关系
              </h4>
              <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                {selectedEntity.relations?.map((rel, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '8px 12px',
                      background: '#f5f5f5',
                      borderRadius: 4,
                      marginBottom: 8,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <span>→ <strong>{rel.to}</strong></span>
                    <Tag size="small">{rel.type}</Tag>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default EntityBrowser