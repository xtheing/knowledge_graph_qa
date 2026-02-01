"""
Chroma向量数据库客户端
"""

from typing import List, Dict, Optional, Any
import hashlib
import json

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from ..extraction.entity_extractor import Entity


class ChromaClient:
    """Chroma向量数据库客户端 - 管理语义检索"""

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "knowledge_entities",
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        初始化Chroma客户端

        Args:
            persist_directory: 数据持久化目录
            collection_name: 集合名称
            embedding_model: OpenAI嵌入模型名称
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model

        # 初始化嵌入函数
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=None,  # 从环境变量读取
            model_name=embedding_model,
        )

        # 初始化客户端
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

        print(f"✓ Chroma连接成功: {collection_name}")

    def _generate_id(self, entity: Entity) -> str:
        """为实体生成唯一ID"""
        content = f"{entity.name}_{entity.paper_id}_{entity.type}"
        return hashlib.md5(content.encode()).hexdigest()

    def add_entity(self, entity: Entity) -> str:
        """
        添加单个实体

        Args:
            entity: 实体对象

        Returns:
            实体ID
        """
        entity_id = self._generate_id(entity)

        # 构建文档文本（用于嵌入）
        document = f"{entity.name}: {entity.description}"

        # 元数据
        metadata = {
            "name": entity.name,
            "type": entity.type,
            "paper_id": entity.paper_id,
            "section": entity.section,
            "page": entity.page,
        }

        self.collection.add(ids=[entity_id], documents=[document], metadatas=[metadata])

        return entity_id

    def add_entities(self, entities: List[Entity], batch_size: int = 100) -> List[str]:
        """
        批量添加实体

        Args:
            entities: 实体列表
            batch_size: 批处理大小

        Returns:
            实体ID列表
        """
        ids = []

        for i in range(0, len(entities), batch_size):
            batch = entities[i : i + batch_size]

            batch_ids = [self._generate_id(e) for e in batch]
            batch_documents = [f"{e.name}: {e.description}" for e in batch]
            batch_metadatas = [
                {
                    "name": e.name,
                    "type": e.type,
                    "paper_id": e.paper_id,
                    "section": e.section,
                    "page": e.page,
                }
                for e in batch
            ]

            self.collection.add(
                ids=batch_ids, documents=batch_documents, metadatas=batch_metadatas
            )

            ids.extend(batch_ids)

        return ids

    def search(
        self,
        query_text: str,
        top_k: int = 10,
        paper_id: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        向量相似度搜索

        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            paper_id: 可选的论文ID过滤
            entity_type: 可选的实体类型过滤

        Returns:
            搜索结果列表
        """
        # 构建过滤条件
        where_clause = {}
        if paper_id:
            where_clause["paper_id"] = paper_id
        if entity_type:
            where_clause["type"] = entity_type

        # 执行查询
        if where_clause:
            results = self.collection.query(
                query_texts=[query_text], n_results=top_k, where=where_clause
            )
        else:
            results = self.collection.query(query_texts=[query_text], n_results=top_k)

        # 格式化结果
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append(
                {
                    "id": results["ids"][0][i],
                    "score": 1 - results["distances"][0][i],  # 转换为相似度
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                }
            )

        return formatted_results

    def search_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        paper_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        使用预计算嵌入向量搜索

        Args:
            query_embedding: 查询嵌入向量
            top_k: 返回结果数量
            paper_id: 可选的论文ID过滤

        Returns:
            搜索结果列表
        """
        where_clause = None
        if paper_id:
            where_clause = {"paper_id": paper_id}

        if where_clause:
            results = self.collection.query(
                query_embeddings=[query_embedding], n_results=top_k, where=where_clause
            )
        else:
            results = self.collection.query(
                query_embeddings=[query_embedding], n_results=top_k
            )

        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append(
                {
                    "id": results["ids"][0][i],
                    "score": 1 - results["distances"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                }
            )

        return formatted_results

    def get_entity(self, entity_id: str) -> Optional[Dict]:
        """
        根据ID获取实体

        Args:
            entity_id: 实体ID

        Returns:
            实体信息或None
        """
        try:
            result = self.collection.get(ids=[entity_id])
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0],
                    "metadata": result["metadatas"][0],
                }
        except Exception as e:
            print(f"获取实体失败: {str(e)}")

        return None

    def delete_entities_by_paper(self, paper_id: str) -> bool:
        """
        删除某篇论文的所有实体

        Args:
            paper_id: 论文ID

        Returns:
            是否成功
        """
        try:
            # 先查询要删除的实体
            results = self.collection.get(where={"paper_id": paper_id})

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                print(f"✓ 已删除论文 {paper_id} 的 {len(results['ids'])} 个向量实体")
                return True
            else:
                print(f"论文 {paper_id} 没有向量实体")
                return True

        except Exception as e:
            print(f"删除实体失败: {str(e)}")
            return False

    def get_collection_stats(self) -> Dict:
        """获取集合统计信息"""
        count = self.collection.count()
        return {
            "total_entities": count,
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory,
        }

    def reset_collection(self) -> bool:
        """重置集合（删除所有数据）"""
        confirm = input("确定要清空向量库吗？输入 'yes' 确认: ")
        if confirm != "yes":
            print("操作已取消")
            return False

        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"},
            )
            print("✓ 向量库已重置")
            return True
        except Exception as e:
            print(f"重置失败: {str(e)}")
            return False


if __name__ == "__main__":
    # 测试代码
    client = ChromaClient()

    # 查看统计
    stats = client.get_collection_stats()
    print(f"\n向量库统计:")
    print(f"  实体总数: {stats['total_entities']}")

    # 测试搜索
    if stats["total_entities"] > 0:
        results = client.search("machine learning", top_k=5)
        print(f"\n搜索结果:")
        for r in results:
            print(f"  - {r['metadata']['name']} (相似度: {r['score']:.3f})")
