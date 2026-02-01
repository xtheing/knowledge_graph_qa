"""
FastAPI服务 - 知识图谱问答API
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import uuid
from datetime import datetime
import shutil

from ..qa.chain import KnowledgeGraphQAChain, KnowledgeGraphPipeline
from ..storage.neo4j_client import Neo4jClient
from ..storage.chroma_client import ChromaClient

# 创建FastAPI应用
app = FastAPI(
    title="知识图谱问答系统 API",
    description="基于学术论文的知识图谱构建与问答系统",
    version="1.0.0",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局客户端实例（延迟初始化）
_qa_chain = None
_neo4j_client = None
_chroma_client = None


def get_qa_chain() -> KnowledgeGraphQAChain:
    """获取问答链实例（单例）"""
    global _qa_chain
    if _qa_chain is None:
        _qa_chain = KnowledgeGraphQAChain()
    return _qa_chain


def get_neo4j_client() -> Neo4jClient:
    """获取Neo4j客户端（单例）"""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
        )
    return _neo4j_client


def get_chroma_client() -> ChromaClient:
    """获取Chroma客户端（单例）"""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = ChromaClient(
            persist_directory=os.getenv("CHROMA_DIR", "./data/chroma_db")
        )
    return _chroma_client


# ============ 请求/响应模型 ============


class QuestionRequest(BaseModel):
    """问答请求"""

    question: str = Field(..., description="用户问题", min_length=1, max_length=1000)
    paper_id: Optional[str] = Field(None, description="可选的论文ID过滤")
    include_context: bool = Field(False, description="是否返回检索上下文")
    include_evaluation: bool = Field(False, description="是否评估回答质量")


class QuestionResponse(BaseModel):
    """问答响应"""

    question: str
    answer: str
    success: bool
    retrieved_entities: List[Dict[str, Any]]
    retrieved_relations: List[Dict[str, Any]]
    total_entities: int
    total_relations: int
    context: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PaperProcessRequest(BaseModel):
    """论文处理请求"""

    paper_id: Optional[str] = Field(None, description="论文ID（可选，默认自动生成）")
    max_chunks: int = Field(50, description="最大处理片段数", ge=1, le=200)


class PaperProcessResponse(BaseModel):
    """论文处理响应"""

    success: bool
    paper_id: Optional[str] = None
    title: Optional[str] = None
    total_chunks: int = 0
    entities_extracted: int = 0
    relations_extracted: int = 0
    entities_stored: int = 0
    relations_stored: int = 0
    vectors_stored: int = 0
    error: Optional[str] = None


class EntitySearchRequest(BaseModel):
    """实体搜索请求"""

    keyword: str = Field(..., description="搜索关键词", min_length=1)
    paper_id: Optional[str] = Field(None, description="可选的论文ID过滤")
    entity_type: Optional[str] = Field(None, description="可选的实体类型过滤")
    limit: int = Field(20, description="返回数量限制", ge=1, le=100)


class GraphStatsResponse(BaseModel):
    """图谱统计响应"""

    total_entities: int
    total_relations: int
    entity_types: List[Dict[str, Any]]
    papers: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    version: str
    timestamp: str
    neo4j_connected: bool
    chroma_connected: bool


# ============ API端点 ============


@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径"""
    return {"message": "知识图谱问答系统 API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    neo4j_ok = False
    chroma_ok = False

    try:
        neo4j = get_neo4j_client()
        # 简单测试连接
        neo4j_ok = True
    except:
        pass

    try:
        chroma = get_chroma_client()
        stats = chroma.get_collection_stats()
        chroma_ok = True
    except:
        pass

    return HealthResponse(
        status="healthy" if (neo4j_ok and chroma_ok) else "degraded",
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        neo4j_connected=neo4j_ok,
        chroma_connected=chroma_ok,
    )


@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    问答接口

    基于知识图谱回答用户问题
    """
    try:
        chain = get_qa_chain()
        result = chain.ask(
            question=request.question,
            paper_id=request.paper_id,
            include_context=request.include_context,
            include_evaluation=request.include_evaluation,
        )

        return QuestionResponse(
            question=result["question"],
            answer=result["answer"],
            success=result["success"],
            retrieved_entities=result["retrieved_entities"],
            retrieved_relations=result["retrieved_relations"],
            total_entities=result["total_entities"],
            total_relations=result["total_relations"],
            context=result.get("context"),
            evaluation=result.get("evaluation"),
            error=result.get("error"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/papers/upload", response_model=PaperProcessResponse)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    paper_id: Optional[str] = None,
    max_chunks: int = 50,
):
    """
    上传并处理论文

    上传PDF文件，自动抽取知识并构建图谱
    """
    # 验证文件类型
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持PDF文件")

    # 生成paper_id
    if not paper_id:
        paper_id = f"paper_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d')}"

    # 保存上传的文件
    upload_dir = "./data/papers"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{paper_id}.pdf")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    finally:
        file.file.close()

    # 处理论文
    try:
        pipeline = KnowledgeGraphPipeline()
        result = pipeline.process_paper(file_path, paper_id, max_chunks)
        pipeline.close()

        return PaperProcessResponse(
            success=result["success"],
            paper_id=result.get("paper_id"),
            title=result.get("title"),
            total_chunks=result.get("total_chunks", 0),
            entities_extracted=result.get("entities_extracted", 0),
            relations_extracted=result.get("relations_extracted", 0),
            entities_stored=result.get("entities_stored", 0),
            relations_stored=result.get("relations_stored", 0),
            vectors_stored=result.get("vectors_stored", 0),
            error=result.get("error"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.get("/papers/{paper_id}/entities")
async def get_paper_entities(paper_id: str, limit: int = 100):
    """获取论文的所有实体"""
    try:
        neo4j = get_neo4j_client()
        entities = neo4j.get_all_entities(paper_id=paper_id, limit=limit)
        return {"paper_id": paper_id, "entities": entities, "total": len(entities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/entities/search")
async def search_entities(request: EntitySearchRequest):
    """搜索实体"""
    try:
        neo4j = get_neo4j_client()
        entities = neo4j.search_entities(
            keyword=request.keyword,
            paper_id=request.paper_id,
            entity_type=request.entity_type,
            limit=request.limit,
        )
        return {
            "keyword": request.keyword,
            "entities": entities,
            "total": len(entities),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/entities/{entity_name}/neighbors")
async def get_entity_neighbors(
    entity_name: str, paper_id: Optional[str] = None, depth: int = 1
):
    """获取实体的邻居节点"""
    try:
        neo4j = get_neo4j_client()
        subgraph = neo4j.get_entity_neighbors(
            entity_name=entity_name, paper_id=paper_id, depth=depth
        )
        return {
            "entity": entity_name,
            "depth": depth,
            "nodes": subgraph["nodes"],
            "relationships": subgraph["relationships"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=GraphStatsResponse)
async def get_stats():
    """获取知识图谱统计信息"""
    try:
        neo4j = get_neo4j_client()
        stats = neo4j.get_statistics()

        return GraphStatsResponse(
            total_entities=stats.get("total_entities", 0),
            total_relations=stats.get("total_relations", 0),
            entity_types=stats.get("entity_types", []),
            papers=stats.get("papers", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """删除论文及其知识"""
    try:
        # 删除Neo4j中的数据
        neo4j = get_neo4j_client()
        neo4j.delete_paper(paper_id)

        # 删除Chroma中的数据
        chroma = get_chroma_client()
        chroma.delete_entities_by_paper(paper_id)

        return {"message": f"论文 {paper_id} 已删除", "paper_id": paper_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    global _qa_chain, _neo4j_client, _chroma_client

    if _qa_chain:
        _qa_chain.close()
    if _neo4j_client:
        _neo4j_client.close()

    print("✓ 服务已关闭，资源已清理")


if __name__ == "__main__":
    import uvicorn

    # 从环境变量读取配置
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"

    print(f"启动API服务: http://{host}:{port}")
    print(f"API文档: http://{host}:{port}/docs")

    uvicorn.run("src.api.main:app", host=host, port=port, reload=reload, workers=1)
