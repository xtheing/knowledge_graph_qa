"""
知识图谱问答流程编排
"""

from typing import Dict, Any, Optional, List
import os

from ..ingestion.pdf_parser import DocumentLoader, DocumentChunk
from ..extraction.entity_extractor import KnowledgeExtractor
from ..storage.neo4j_client import Neo4jClient, GraphBuilder
from ..storage.chroma_client import ChromaClient
from ..retrieval.hybrid_searcher import HybridSearcher, ContextBuilder
from ..qa.answer_generator import AnswerGenerator, QAEvaluator


class KnowledgeGraphQAChain:
    """完整的知识图谱问答流程链"""

    def __init__(
        self,
        neo4j_uri: str = None,
        neo4j_user: str = None,
        neo4j_password: str = None,
        chroma_dir: str = "./data/chroma_db",
        llm_model: str = "gpt-4",
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        初始化问答流程链

        Args:
            neo4j_uri: Neo4j连接URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
            chroma_dir: Chroma数据目录
            llm_model: LLM模型名称
            embedding_model: 嵌入模型名称
        """
        # 从环境变量获取配置（如果没有提供）
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD", "password")

        # 初始化存储客户端
        print("初始化存储客户端...")
        self.neo4j = Neo4jClient(
            uri=self.neo4j_uri, user=self.neo4j_user, password=self.neo4j_password
        )
        self.chroma = ChromaClient(persist_directory=chroma_dir)

        # 初始化检索和生成组件
        print("初始化检索和生成组件...")
        self.searcher = HybridSearcher(
            chroma_client=self.chroma,
            neo4j_client=self.neo4j,
            embedding_model=embedding_model,
        )
        self.generator = AnswerGenerator(model_name=llm_model)
        self.evaluator = QAEvaluator()

        print("✓ 问答流程链初始化完成")

    def close(self):
        """关闭所有连接"""
        self.neo4j.close()
        print("✓ 所有连接已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def ask(
        self,
        question: str,
        paper_id: Optional[str] = None,
        include_context: bool = False,
        include_evaluation: bool = False,
    ) -> Dict[str, Any]:
        """
        执行问答流程

        Args:
            question: 用户问题
            paper_id: 可选的论文ID过滤
            include_context: 是否返回检索上下文
            include_evaluation: 是否评估回答质量

        Returns:
            问答结果字典
        """
        try:
            # 1. 混合检索
            search_result = self.searcher.search(
                query=question, top_k_vectors=10, graph_depth=2, paper_id=paper_id
            )

            # 2. 格式化上下文
            context = self.searcher.format_context(search_result)

            # 3. 生成答案
            answer_result = self.generator.generate(context, question)

            # 4. 组装结果
            result = {
                "question": question,
                "answer": answer_result["answer"],
                "retrieved_entities": search_result["subgraph"]["nodes"],
                "retrieved_relations": search_result["subgraph"]["relationships"],
                "total_entities": search_result["total_entities"],
                "total_relations": search_result["total_relations"],
                "success": answer_result["success"],
            }

            if include_context:
                result["context"] = context

            # 5. 评估回答质量
            if include_evaluation:
                eval_metrics = self.evaluator.evaluate(
                    question=question, answer=answer_result["answer"], context=context
                )
                result["evaluation"] = eval_metrics

            return result

        except Exception as e:
            return {
                "question": question,
                "answer": f"问答过程出错: {str(e)}",
                "success": False,
                "error": str(e),
            }

    def ask_stream(self, question: str, paper_id: Optional[str] = None):
        """
        流式问答（逐字返回答案）

        Args:
            question: 用户问题
            paper_id: 可选的论文ID过滤

        Yields:
            答案片段
        """
        # 先执行检索（无法流式）
        search_result = self.searcher.search(
            query=question, top_k_vectors=10, graph_depth=2, paper_id=paper_id
        )

        context = self.searcher.format_context(search_result)

        # 使用LangChain的流式功能
        from langchain.callbacks import StreamingStdOutCallbackHandler

        streaming_llm = AnswerGenerator(model_name="gpt-4", temperature=0.3)

        # 这里简化处理，实际应使用LangChain的astream方法
        result = streaming_llm.generate(context, question)
        yield result["answer"]


class KnowledgeGraphPipeline:
    """知识图谱构建流程"""

    def __init__(
        self,
        neo4j_uri: str = None,
        neo4j_user: str = None,
        neo4j_password: str = None,
        chroma_dir: str = "./data/chroma_db",
        llm_model: str = "gpt-4",
    ):
        """初始化构建流程"""
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD", "password")
        self.chroma_dir = chroma_dir
        self.llm_model = llm_model

        # 初始化组件
        self.document_loader = DocumentLoader()
        self.knowledge_extractor = KnowledgeExtractor(model_name=llm_model)

        # 存储客户端（延迟初始化）
        self._neo4j = None
        self._chroma = None
        self._graph_builder = None

    @property
    def neo4j(self):
        if self._neo4j is None:
            self._neo4j = Neo4jClient(
                uri=self.neo4j_uri, user=self.neo4j_user, password=self.neo4j_password
            )
        return self._neo4j

    @property
    def chroma(self):
        if self._chroma is None:
            self._chroma = ChromaClient(persist_directory=self.chroma_dir)
        return self._chroma

    @property
    def graph_builder(self):
        if self._graph_builder is None:
            self._graph_builder = GraphBuilder(self.neo4j)
        return self._graph_builder

    def process_paper(
        self, pdf_path: str, paper_id: Optional[str] = None, max_chunks: int = 50
    ) -> Dict[str, Any]:
        """
        处理单篇论文并构建知识图谱

        Args:
            pdf_path: PDF文件路径
            paper_id: 论文ID（可选）
            max_chunks: 最大处理片段数

        Returns:
            处理结果统计
        """
        print(f"\n{'=' * 60}")
        print(f"处理论文: {pdf_path}")
        print(f"{'=' * 60}\n")

        try:
            # 1. 加载文档
            print("📄 步骤1: 解析PDF文档...")
            chunks, metadata = self.document_loader.load_single(pdf_path, paper_id)
            print(f"   ✓ 提取 {len(chunks)} 个文本片段")

            # 限制处理片段数
            if len(chunks) > max_chunks:
                print(f"   ℹ 限制处理前 {max_chunks} 个片段")
                chunks = chunks[:max_chunks]

            # 2. 知识抽取
            print("\n🧠 步骤2: 抽取知识...")
            knowledge = self.knowledge_extractor.extract_from_paper(chunks, metadata)
            entities = knowledge["entities"]
            relations = knowledge["relations"]
            print(f"   ✓ 抽取 {len(entities)} 个实体, {len(relations)} 个关系")

            # 3. 构建图数据库
            print("\n💾 步骤3: 存入Neo4j图数据库...")
            neo4j_stats = self.graph_builder.build_from_extraction(entities, relations)
            print(
                f"   ✓ 成功创建 {neo4j_stats['entities']} 个实体, {neo4j_stats['relations']} 个关系"
            )

            # 4. 存入向量库
            print("\n📊 步骤4: 存入Chroma向量库...")
            entity_ids = self.chroma.add_entities(entities)
            print(f"   ✓ 成功添加 {len(entity_ids)} 个向量实体")

            print(f"\n{'=' * 60}")
            print(f"✅ 论文处理完成!")
            print(f"{'=' * 60}\n")

            return {
                "success": True,
                "paper_id": metadata["paper_id"],
                "title": metadata.get("title", "Unknown"),
                "total_chunks": len(chunks),
                "entities_extracted": len(entities),
                "relations_extracted": len(relations),
                "entities_stored": neo4j_stats["entities"],
                "relations_stored": neo4j_stats["relations"],
                "vectors_stored": len(entity_ids),
                "metadata": metadata,
            }

        except Exception as e:
            print(f"\n❌ 处理失败: {str(e)}")
            return {"success": False, "error": str(e), "pdf_path": pdf_path}

    def process_directory(
        self, directory: str, pattern: str = "*.pdf", max_chunks_per_paper: int = 50
    ) -> List[Dict[str, Any]]:
        """
        批量处理目录中的所有PDF

        Args:
            directory: PDF目录
            pattern: 文件匹配模式
            max_chunks_per_paper: 每篇论文最大片段数

        Returns:
            处理结果列表
        """
        import glob
        from pathlib import Path

        pdf_files = list(Path(directory).glob(pattern))
        print(f"发现 {len(pdf_files)} 个PDF文件\n")

        results = []
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n处理第 {i}/{len(pdf_files)} 个文件...")
            result = self.process_paper(str(pdf_file), max_chunks=max_chunks_per_paper)
            results.append(result)

        # 统计
        successful = sum(1 for r in results if r["success"])
        print(f"\n{'=' * 60}")
        print(f"批量处理完成: {successful}/{len(results)} 成功")
        print(f"{'=' * 60}\n")

        return results

    def close(self):
        """关闭所有连接"""
        if self._neo4j:
            self._neo4j.close()
        print("✓ 所有连接已关闭")


# 便捷的函数接口
def process_paper(
    pdf_path: str, paper_id: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """
    便捷函数：处理单篇论文

    Args:
        pdf_path: PDF文件路径
        paper_id: 论文ID
        **kwargs: 其他配置参数

    Returns:
        处理结果
    """
    pipeline = KnowledgeGraphPipeline(**kwargs)
    try:
        result = pipeline.process_paper(pdf_path, paper_id)
        return result
    finally:
        pipeline.close()


def ask_question(
    question: str,
    paper_id: Optional[str] = None,
    include_context: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """
    便捷函数：问答

    Args:
        question: 问题
        paper_id: 可选的论文ID过滤
        include_context: 是否返回上下文
        **kwargs: 其他配置参数

    Returns:
        问答结果
    """
    chain = KnowledgeGraphQAChain(**kwargs)
    try:
        result = chain.ask(question, paper_id, include_context=include_context)
        return result
    finally:
        chain.close()


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) > 2 and sys.argv[1] == "--process":
        # 处理论文模式
        pdf_path = sys.argv[2]
        result = process_paper(pdf_path)

        print("\n处理结果:")
        for key, value in result.items():
            print(f"  {key}: {value}")

    elif len(sys.argv) > 2 and sys.argv[1] == "--ask":
        # 问答模式
        question = sys.argv[2]
        paper_id = sys.argv[3] if len(sys.argv) > 3 else None

        result = ask_question(question, paper_id, include_context=True)

        print(f"\n问题: {result['question']}")
        print(f"\n答案:\n{result['answer']}")

        if result.get("context"):
            print(f"\n上下文:\n{result['context'][:500]}...")

    else:
        print("用法:")
        print("  python chain.py --process <pdf_path>")
        print("  python chain.py --ask <question> [paper_id]")
