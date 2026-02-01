import React, { useState, useRef, useEffect } from 'react'
import {
  Card,
  Input,
  Button,
  Space,
  Tag,
  Spin,
  Drawer,
  List,
  Typography,
  message,
} from 'antd'
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  InfoCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'

const { TextArea } = Input
const { Text } = Typography

// 模拟问答数据
const mockQAHistory = [
  {
    question: '这篇论文使用了什么数据集？',
    answer: '根据论文内容，该研究使用了ImageNet-1K和COCO两个主要数据集。ImageNet-1K包含1000个类别的图像分类数据集，用于预训练模型；COCO是目标检测和分割数据集，用于下游任务评估。',
    entities: 8,
    relations: 12,
    responseTime: 1.2,
  },
]

// 快速提问选项
const quickQuestions = [
  '这篇论文的主要贡献是什么？',
  '使用了什么方法？',
  '实验结果如何？',
  '有哪些创新点？',
  '对比了哪些baseline？',
]

function QAAssistant() {
  const [question, setQuestion] = useState('')
  const [chatHistory, setChatHistory] = useState(mockQAHistory)
  const [loading, setLoading] = useState(false)
  const [contextDrawerVisible, setContextDrawerVisible] = useState(false)
  const [currentContext, setCurrentContext] = useState(null)
  const messagesEndRef = useRef(null)
  
  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }
  
  useEffect(() => {
    scrollToBottom()
  }, [chatHistory])
  
  // 发送问题
  const handleSend = async () => {
    if (!question.trim()) {
      message.warning('请输入问题')
      return
    }
    
    setLoading(true)
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // 模拟回答
    const answer = `关于"${question}"，根据知识图谱中的信息：\n\n该论文主要采用了深度学习方法，使用了大规模数据集进行训练，并在多个基准测试中取得了优异的表现。具体细节包括模型架构的创新、训练策略的优化以及评估指标的改进。`
    
    const newQA = {
      question: question,
      answer: answer,
      entities: Math.floor(Math.random() * 10) + 5,
      relations: Math.floor(Math.random() * 15) + 8,
      responseTime: (Math.random() * 2 + 0.5).toFixed(1),
    }
    
    setChatHistory([...chatHistory, newQA])
    setQuestion('')
    setLoading(false)
  }
  
  // 快速提问
  const handleQuickQuestion = (q) => {
    setQuestion(q)
    // 可选：自动发送
    // setTimeout(() => handleSend(), 100)
  }
  
  // 查看上下文
  const handleViewContext = (qa) => {
    setCurrentContext({
      entities: [
        { name: 'BERT', type: 'Model', description: '双向编码器表示模型' },
        { name: 'GPT-3', type: 'Model', description: '生成式预训练模型' },
        { name: 'ImageNet', type: 'Dataset', description: '图像分类数据集' },
        { name: 'Transformer', type: 'Method', description: '自注意力机制' },
      ],
      relations: [
        { from: 'BERT', to: 'Transformer', type: 'BASED_ON' },
        { from: 'GPT-3', to: 'Transformer', type: 'BASED_ON' },
        { from: 'BERT', to: 'ImageNet', type: 'EVALUATED_ON' },
      ],
    })
    setContextDrawerVisible(true)
  }
  
  return (
    <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column', padding: 16 }}>
      {/* 聊天记录区域 */}
      <Card
        className="card-shadow"
        bodyStyle={{ 
          padding: 24, 
          height: 'calc(100vh - 250px)', 
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
        style={{ flex: 1, marginBottom: 16 }}
      >
        {chatHistory.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', marginTop: 100 }}>
            <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <p>开始提问吧！我将基于知识图谱为你解答</p>
          </div>
        ) : (
          chatHistory.map((qa, index) => (
            <div key={index}>
              {/* 用户问题 */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
                <Card
                  size="small"
                  style={{
                    maxWidth: '70%',
                    background: '#1890ff',
                    color: '#fff',
                    border: 'none',
                  }}
                  bodyStyle={{ padding: '12px 16px' }}
                >
                  <Space>
                    <span>{qa.question}</span>
                    <UserOutlined />
                  </Space>
                </Card>
              </div>
              
              {/* AI回答 */}
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <Card
                  size="small"
                  style={{ maxWidth: '80%', background: '#f5f5f5', border: 'none' }}
                  bodyStyle={{ padding: '12px 16px' }}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <RobotOutlined style={{ color: '#1890ff' }} />
                      <Text strong>知识图谱助手</Text>
                    </Space>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                      {qa.answer}
                    </div>
                    <Space style={{ marginTop: 8 }}>
                      <Tag icon={<InfoCircleOutlined />} color="blue">
                        {qa.entities} 个实体
                      </Tag>
                      <Tag icon={<InfoCircleOutlined />} color="green">
                        {qa.relations} 个关系
                      </Tag>
                      <Tag icon={<ClockCircleOutlined />}>
                        {qa.responseTime}s
                      </Tag>
                      <Button 
                        type="link" 
                        size="small"
                        onClick={() => handleViewContext(qa)}
                      >
                        查看上下文
                      </Button>
                    </Space>
                  </Space>
                </Card>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <Card
              size="small"
              style={{ background: '#f5f5f5', border: 'none' }}
              bodyStyle={{ padding: '12px 16px' }}
            >
              <Space>
                <RobotOutlined style={{ color: '#1890ff' }} />
                <Spin size="small" />
                <Text type="secondary">思考中...</Text>
              </Space>
            </Card>
          </div>
        )}
        <div ref={messagesEndRef} />
      </Card>
      
      {/* 输入区域 */}
      <Card className="card-shadow" bodyStyle={{ padding: '16px 24px' }}>
        <div style={{ display: 'flex', gap: 12 }}>
          <TextArea
            placeholder="输入你的问题..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            autoSize={{ minRows: 2, maxRows: 4 }}
            style={{ flex: 1 }}
            disabled={loading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            style={{ height: 'auto' }}
          >
            发送
          </Button>
        </div>
        
        {/* 快速提问 */}
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ marginRight: 8 }}>快速提问:</Text>
          <Space size="small" wrap>
            {quickQuestions.map((q, index) => (
              <Tag
                key={index}
                style={{ cursor: 'pointer' }}
                onClick={() => handleQuickQuestion(q)}
              >
                {q}
              </Tag>
            ))}
          </Space>
        </div>
      </Card>
      
      {/* 上下文抽屉 */}
      <Drawer
        title="检索上下文"
        placement="right"
        onClose={() => setContextDrawerVisible(false)}
        open={contextDrawerVisible}
        width={400}
      >
        {currentContext && (
          <div>
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ color: '#666', marginBottom: 12 }}>
                <InfoCircleOutlined /> 相关实体 ({currentContext.entities.length})
              </h4>
              <List
                size="small"
                dataSource={currentContext.entities}
                renderItem={(item) => (
                  <List.Item>
                    <div>
                      <Tag color="blue">{item.type}</Tag>
                      <strong style={{ marginLeft: 8 }}>{item.name}</strong>
                      <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
                        {item.description}
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            </div>
            
            <div>
              <h4 style={{ color: '#666', marginBottom: 12 }}>
                <InfoCircleOutlined /> 实体关系 ({currentContext.relations.length})
              </h4>
              <List
                size="small"
                dataSource={currentContext.relations}
                renderItem={(item) => (
                  <List.Item>
                    <div style={{ fontSize: 14 }}>
                      <strong>{item.from}</strong>
                      <Tag style={{ margin: '0 8px' }} size="small">{item.type}</Tag>
                      <strong>{item.to}</strong>
                    </div>
                  </List.Item>
                )}
              />
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}

export default QAAssistant