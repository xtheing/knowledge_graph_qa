# 知识图谱问答系统

基于学术论文的知识图谱构建与智能问答系统。使用大模型从论文中自动提取结构化知识，构建知识图谱，并支持基于图谱的智能问答。

## 系统架构

```
PDF文档 → 文本提取 → 知识抽取(LLM) → 图谱构建 → 向量化存储
                                      ↓
用户问题 → 混合检索(向量+图谱) → LLM推理 → 智能答案
```

## 核心特性

- **自动知识抽取**: 使用GPT-4自动从论文中提取实体和关系
- **混合检索**: 结合向量相似度和图结构的多级检索
- **知识图谱存储**: Neo4j图数据库存储结构，Chroma向量库存储语义
- **智能问答**: 基于知识图谱上下文的大模型推理
- **完整API**: RESTful API支持文件上传、问答、实体查询

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd knowledge_graph_qa

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的API密钥
OPENAI_API_KEY=your_openai_api_key
NEO4J_PASSWORD=your_neo4j_password
```

### 3. 启动数据库

```bash
# 使用Docker启动Neo4j
docker run -d \
  --name neo4j-knowledge \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5-community

# 初始化Neo4j
python scripts/setup_neo4j.py
```

### 4. 处理论文

```bash
# 处理单篇论文
python scripts/process_papers.py -f /path/to/paper.pdf

# 批量处理目录
python scripts/process_papers.py -d /path/to/papers/
```

### 5. 启动问答服务

```bash
# 方式1: 命令行交互式问答
python scripts/ask.py

# 方式2: 启动API服务
python -m src.api.main

# 访问API文档: http://localhost:8000/docs
```

## 使用示例

### API调用示例

```python
import requests

# 上传论文
with open("paper.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/papers/upload",
        files={"file": f}
    )
result = response.json()

# 问答
response = requests.post(
    "http://localhost:8000/ask",
    json={
        "question": "这篇论文使用了什么数据集？",
        "paper_id": result["paper_id"]
    }
)
print(response.json()["answer"])
```

### Python代码示例

```python
from src.qa.chain import KnowledgeGraphQAChain

# 初始化
chain = KnowledgeGraphQAChain()

# 问答
result = chain.ask(
    question="BERT和GPT有什么区别？",
    paper_id="paper_001",
    include_context=True
)

print(f"答案: {result['answer']}")
print(f"检索到 {result['total_entities']} 个实体")

# 关闭连接
chain.close()
```

## 项目结构

```
knowledge_graph_qa/
├── src/
│   ├── ingestion/         # 文档处理
│   │   └── pdf_parser.py  # PDF解析
│   ├── extraction/        # 知识抽取
│   │   └── entity_extractor.py  # LLM抽取实体关系
│   ├── storage/           # 数据存储
│   │   ├── neo4j_client.py      # 图数据库
│   │   └── chroma_client.py     # 向量库
│   ├── retrieval/         # 检索引擎
│   │   └── hybrid_searcher.py   # 混合检索
│   ├── qa/                # 问答引擎
│   │   ├── answer_generator.py  # 答案生成
│   │   └── chain.py             # 流程编排
│   └── api/               # API服务
│       └── main.py        # FastAPI服务
├── scripts/               # 工具脚本
│   ├── process_papers.py  # 论文处理
│   ├── ask.py            # 问答工具
│   └── setup_neo4j.py    # 数据库初始化
├── config/
│   └── settings.yaml     # 配置文件
├── requirements.txt      # Python依赖
├── .env.example         # 环境变量模板
└── README.md            # 本文件
```

## 技术栈

- **PDF解析**: pdfplumber
- **知识抽取**: LangChain + OpenAI GPT-4
- **图数据库**: Neo4j
- **向量数据库**: Chroma
- **API框架**: FastAPI
- **嵌入模型**: text-embedding-3-small

## 实体类型

- **Concept**: 核心概念、理论
- **Method**: 方法、算法、技术
- **Dataset**: 数据集、语料
- **Model**: 模型、架构
- **Metric**: 评估指标
- **Result**: 实验结果
- **Paper**: 论文本身

## 关系类型

- **USES**: 使用
- **BASED_ON**: 基于
- **ACHIEVES**: 达到
- **COMPARES_TO**: 对比
- **PART_OF**: 部分
- **LEADS_TO**: 导致
- **CITES**: 引用

## API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API信息 |
| `/health` | GET | 健康检查 |
| `/ask` | POST | 问答 |
| `/papers/upload` | POST | 上传论文 |
| `/papers/{id}` | DELETE | 删除论文 |
| `/papers/{id}/entities` | GET | 获取论文实体 |
| `/entities/search` | POST | 搜索实体 |
| `/stats` | GET | 统计信息 |

## 配置说明

编辑 `config/settings.yaml` 调整系统配置：

```yaml
extraction:
  batch_size: 5           # LLM批处理大小
  max_chunks_per_paper: 50 # 每篇论文最大片段数

retrieval:
  vector_top_k: 10        # 向量检索Top-K
  graph_depth: 2          # 图谱遍历深度

qa:
  model: gpt-4            # 问答模型
  temperature: 0.3        # 生成温度
```

## 性能优化建议

1. **批处理**: 调整`batch_size`和`max_chunks_per_paper`参数
2. **缓存**: 热门查询结果可添加Redis缓存
3. **异步**: 使用Celery处理论文上传任务
4. **索引**: Neo4j中添加适当的索引加速查询

## 常见问题

**Q: 为什么抽取的实体很少？**
A: 检查`max_chunks_per_paper`设置，或论文内容是否太简短。

**Q: 问答结果不准确？**
A: 尝试调整`graph_depth`增加检索范围，或检查知识抽取质量。

**Q: API响应慢？**
A: 大模型调用是主要耗时点，考虑使用更快的模型（如gpt-3.5-turbo）。

## 开发计划

- [x] 基础PDF解析和知识抽取
- [x] Neo4j + Chroma混合存储
- [x] 混合检索引擎
- [x] RESTful API
- [ ] 前端可视化界面
- [ ] 多模态知识抽取（图表、公式）
- [ ] 实体对齐优化
- [ ] 支持更多LLM提供商

## 许可证

MIT License

## 贡献

欢迎提交Issue和PR！

## 联系方式

如有问题，请提交Issue或联系维护者。