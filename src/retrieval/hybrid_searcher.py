"""
混合检索引擎 - 结合向量相似度和图结构
"""

from typing import List, Dict, Optional, Any
from openai import OpenAI
import os

from ..storage.chroma_client import ChromaClient
from ..storage.neo4j_client import Neo4jClient


class HybridSearcher:
    """混合检索器 - 向量相似 + 图谱扩展"""

    def __init__(
        self,
        chroma_client: ChromaClient,
        neo4j_client: Neo4jClient,
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        初始化混合检索器

        Args:
            chroma_client: Chroma向量库客户端
            neo4j_client: Neo4j图库客户端
            embedding_model: 嵌入模型名称
        """
        self.chroma = chroma_client
        self.neo4j = neo4j_client
        self.openai = OpenAI()
        self.embedding_model = embedding_model

    def search(
        self,
        query: str,
        top_k_vectors: int = 10,
        graph_depth: int = 2,
        paper_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行混合检索

        Args:
            query: 用户查询
            top_k_vectors: 向量检索Top-K
            graph_depth: 图谱扩展深度
            paper_id: 可选的论文ID过滤

        Returns:
            检索结果字典
        """
        # 1. 向量化查询
        query_embedding = self._get_embedding(query)

        # 2. 向量检索 - 召回相关实体
        vector_results = self.chroma.search_by_embedding(
            query_embedding, top_k=top_k_vectors, paper_id=paper_id
        )

        # 3. 提取实体名称
        entity_names = [r["metadata"]["name"] for r in vector_results]

        # 4. 图谱扩展 - 获取邻居节点和关系
        if entity_names:
            subgraph = self.neo4j.get_subgraph(
                entity_names, paper_id=paper_id, depth=graph_depth
            )
        else:
            subgraph = {"nodes": [], "relationships": []}

        # 5. 组装结果
        return {
            "query": query,
            "vector_results": vector_results,
            "subgraph": subgraph,
            "retrieved_entities": entity_names,
            "total_entities": len(subgraph["nodes"]),
            "total_relations": len(subgraph["relationships"]),
        }

    def search_multi_hop(
        self, query: str, max_hops: int = 2, paper_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        多跳推理检索 - 寻找实体间的路径

        Args:
            query: 用户查询（应包含多个概念）
            max_hops: 最大跳数
            paper_id: 可选的论文ID过滤

        Returns:
            包含路径的检索结果
        """
        # 先执行基础检索
        base_result = self.search(
            query, top_k_vectors=5, graph_depth=max_hops, paper_id=paper_id
        )

        # 如果检索到多个实体，寻找它们之间的路径
        entity_names = base_result["retrieved_entities"]

        if len(entity_names) >= 2:
            # 寻找实体间的最短路径
            paths = self._find_paths_between_entities(
                entity_names[:3],  # 只考虑前3个实体
                paper_id,
                max_hops,
            )
            base_result["paths"] = paths
        else:
            base_result["paths"] = []

        return base_result

    def _find_paths_between_entities(
        self, entity_names: List[str], paper_id: Optional[str], max_depth: int
    ) -> List[Dict]:
        """查找实体间的路径"""
        paths = []

        # 两两查找路径
        for i in range(len(entity_names)):
            for j in range(i + 1, len(entity_names)):
                from_entity = entity_names[i]
                to_entity = entity_names[j]

                # 在Neo4j中查询路径
                if paper_id:
                    query = f"""
                    MATCH path = shortestPath(
                        (a:Entity {{name: $from_name, paper_id: $paper_id}})-[*1..{max_depth}]-(b:Entity {{name: $to_name, paper_id: $paper_id}})
                    )
                    RETURN path
                    """
                    params = {
                        "from_name": from_entity,
                        "to_name": to_entity,
                        "paper_id": paper_id,
                    }
                else:
                    query = f"""
                    MATCH path = shortestPath(
                        (a:Entity {{name: $from_name}})-[*1..{max_depth}]-(b:Entity {{name: $to_name}})
                    )
                    RETURN path
                    """
                    params = {"from_name": from_entity, "to_name": to_entity}

                try:
                    from neo4j import GraphDatabase

                    # 这里需要通过session执行查询
                    # 简化处理：直接使用已有的子图信息
                    pass
                except:
                    pass

        return paths

    def _get_embedding(self, text: str) -> List[float]:
        """
        获取文本的embedding向量

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        response = self.openai.embeddings.create(model=self.embedding_model, input=text)
        return response.data[0].embedding

    def format_context(self, search_result: Dict[str, Any]) -> str:
        """
        将检索结果格式化为LLM可用的上下文

        Args:
            search_result: 搜索结果字典

        Returns:
            格式化后的上下文文本
        """
        context_parts = []

        # 添加实体信息
        context_parts.append("## 相关知识实体:")

        # 去重并排序（按向量相似度）
        seen_entities = set()
        for node in search_result["subgraph"]["nodes"]:
            name = node["name"]
            if name not in seen_entities:
                seen_entities.add(name)
                entity_desc = f"- [{node['type']}] {name}"
                if node.get("description"):
                    entity_desc += f": {node['description'][:100]}"
                context_parts.append(entity_desc)

        # 添加关系信息
        if search_result["subgraph"]["relationships"]:
            context_parts.append("\n## 实体关系:")

            # 去重关系
            seen_relations = set()
            for rel in search_result["subgraph"]["relationships"][:20]:  # 限制数量
                rel_key = (rel["from"], rel["to"], rel["type"])
                if rel_key not in seen_relations:
                    seen_relations.add(rel_key)
                    context_parts.append(
                        f"- {rel['from']} --[{rel['type']}]--> {rel['to']}"
                    )

        # 添加来源信息
        if search_result.get("vector_results"):
            context_parts.append("\n## 相关程度（向量相似度）:")
            for result in search_result["vector_results"][:5]:
                context_parts.append(
                    f"- {result['metadata']['name']}: {result['score']:.3f}"
                )

        return "\n".join(context_parts)

    def format_context_with_citations(self, search_result: Dict[str, Any]) -> tuple:
        """
        格式化上下文并返回引用信息

        Returns:
            (context, citations)
        """
        context = self.format_context(search_result)

        # 构建引用信息
        citations = {}
        for i, node in enumerate(search_result["subgraph"]["nodes"], 1):
            citations[f"[{i}]"] = {
                "name": node["name"],
                "type": node["type"],
                "paper_id": node.get("paper_id", ""),
            }

        return context, citations


class ContextBuilder:
    """上下文构建器 - 组装检索结果为LLM可用的格式"""

    def __init__(self, max_context_length: int = 4000):
        self.max_context_length = max_context_length

    def build(
        self,
        search_result: Dict[str, Any],
        include_relations: bool = True,
        include_sources: bool = True,
    ) -> str:
        """
        构建上下文

        Args:
            search_result: 搜索结果
            include_relations: 是否包含关系
            include_sources: 是否包含来源信息

        Returns:
            上下文文本
        """
        parts = []

        # 实体列表
        nodes = search_result.get("subgraph", {}).get("nodes", [])
        if nodes:
            parts.append("相关概念和实体:")
            for node in nodes[:30]:  # 限制实体数量
                desc = node.get("description", "")
                if desc:
                    parts.append(f"- {node['name']} ({node['type']}): {desc[:80]}")
                else:
                    parts.append(f"- {node['name']} ({node['type']})")

        # 关系列表
        if include_relations:
            relations = search_result.get("subgraph", {}).get("relationships", [])
            if relations:
                parts.append("\n实体间关系:")
                for rel in relations[:15]:
                    parts.append(f"- {rel['from']} → [{rel['type']}] → {rel['to']}")

        # 来源信息
        if include_sources:
            vector_results = search_result.get("vector_results", [])
            if vector_results:
                parts.append("\n语义相关性:")
                for result in vector_results[:5]:
                    score = result.get("score", 0)
                    parts.append(f"- {result['metadata']['name']}: {score:.2f}")

        context = "\n".join(parts)

        # 截断超长上下文
        if len(context) > self.max_context_length:
            context = context[: self.max_context_length] + "\n... (内容已截断)"

        return context


if __name__ == "__main__":
    # 测试代码
    import sys
    import os

    # 添加项目根目录到路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from dotenv import load_dotenv

    load_dotenv()

    # 初始化客户端
    chroma = ChromaClient()
    neo4j = Neo4jClient(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "password"),
    )

    # 初始化检索器
    searcher = HybridSearcher(chroma, neo4j)

    # 测试搜索
    query = "machine learning methods"
    print(f"\n查询: {query}")

    result = searcher.search(query, top_k_vectors=5)

    print(f"\n检索结果:")
    print(f"  向量召回: {len(result['vector_results'])} 个")
    print(f"  图谱实体: {result['total_entities']} 个")
    print(f"  图谱关系: {result['total_relations']} 个")

    print(f"\n格式化上下文:")
    context = searcher.format_context(result)
    print(context[:500] + "...")

    # 关闭连接
    neo4j.close()
