"""
Neo4j图数据库客户端
"""

from typing import List, Dict, Optional, Any
from neo4j import GraphDatabase, Driver, Session
import json

from ..extraction.entity_extractor import Entity, Relation


class Neo4jClient:
    """Neo4j图数据库客户端 - 管理知识图谱存储"""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
    ):
        """
        初始化Neo4j客户端

        Args:
            uri: Neo4j连接URI
            user: 用户名
            password: 密码
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[Driver] = None
        self._connect()

    def _connect(self):
        """建立数据库连接"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            # 测试连接
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                if record and record["num"] == 1:
                    print("✓ Neo4j连接成功")
        except Exception as e:
            raise ConnectionError(f"无法连接到Neo4j: {str(e)}")

    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            print("✓ Neo4j连接已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def create_constraints(self):
        """创建数据库约束和索引"""
        constraints = [
            "CREATE CONSTRAINT entity_name_paper IF NOT EXISTS FOR (e:Entity) REQUIRE (e.name, e.paper_id) IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_paper_index IF NOT EXISTS FOR (e:Entity) ON (e.paper_id)",
            "CREATE INDEX entity_section_index IF NOT EXISTS FOR (e:Entity) ON (e.section)",
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"约束创建失败（可能已存在）: {e}")

            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    print(f"索引创建失败（可能已存在）: {e}")

        print("✓ 数据库约束和索引已创建")

    def create_entity(self, entity: Entity) -> bool:
        """
        创建实体节点

        Args:
            entity: 实体对象

        Returns:
            是否成功创建
        """
        query = """
        MERGE (e:Entity {name: $name, paper_id: $paper_id})
        SET e.type = $type,
            e.description = $description,
            e.section = $section,
            e.page = $page,
            e.source_text = $source_text,
            e.updated_at = datetime()
        ON CREATE SET e.created_at = datetime()
        RETURN e.name AS name
        """

        try:
            with self.driver.session() as session:
                result = session.run(
                    query,
                    name=entity.name,
                    paper_id=entity.paper_id,
                    type=entity.type,
                    description=entity.description,
                    section=entity.section,
                    page=entity.page,
                    source_text=entity.source_text[:500],  # 限制长度
                )
                return result.single() is not None
        except Exception as e:
            print(f"创建实体失败 {entity.name}: {str(e)}")
            return False

    def create_entities_batch(
        self, entities: List[Entity], batch_size: int = 100
    ) -> int:
        """
        批量创建实体

        Args:
            entities: 实体列表
            batch_size: 批处理大小

        Returns:
            成功创建的实体数
        """
        count = 0

        for i in range(0, len(entities), batch_size):
            batch = entities[i : i + batch_size]

            query = """
            UNWIND $entities AS entity
            MERGE (e:Entity {name: entity.name, paper_id: entity.paper_id})
            SET e.type = entity.type,
                e.description = entity.description,
                e.section = entity.section,
                e.page = entity.page,
                e.source_text = entity.source_text,
                e.updated_at = datetime()
            ON CREATE SET e.created_at = datetime()
            RETURN count(e) AS count
            """

            try:
                with self.driver.session() as session:
                    # 转换实体为字典列表
                    entity_dicts = [
                        {
                            "name": e.name,
                            "paper_id": e.paper_id,
                            "type": e.type,
                            "description": e.description,
                            "section": e.section,
                            "page": e.page,
                            "source_text": e.source_text[:500],
                        }
                        for e in batch
                    ]

                    result = session.run(query, entities=entity_dicts)
                    count += len(batch)
            except Exception as e:
                print(f"批量创建实体失败: {str(e)}")

        return count

    def create_relationship(self, relation: Relation) -> bool:
        """
        创建关系

        Args:
            relation: 关系对象

        Returns:
            是否成功创建
        """
        # 使用动态关系类型
        query = f"""
        MATCH (from:Entity {{name: $from_name, paper_id: $paper_id}})
        MATCH (to:Entity {{name: $to_name, paper_id: $paper_id}})
        MERGE (from)-[r:{relation.type}]->(to)
        SET r.description = $description,
            r.updated_at = datetime()
        ON CREATE SET r.created_at = datetime()
        RETURN r
        """

        try:
            with self.driver.session() as session:
                result = session.run(
                    query,
                    from_name=relation.from_entity,
                    to_name=relation.to_entity,
                    paper_id=relation.paper_id,
                    description=relation.description,
                )
                return result.single() is not None
        except Exception as e:
            print(
                f"创建关系失败 {relation.from_entity} -> {relation.to_entity}: {str(e)}"
            )
            return False

    def create_relations_batch(
        self, relations: List[Relation], batch_size: int = 100
    ) -> int:
        """
        批量创建关系

        Args:
            relations: 关系列表
            batch_size: 批处理大小

        Returns:
            成功创建的关系数
        """
        count = 0

        # 按关系类型分组处理（Neo4j需要静态关系类型）
        type_groups = {}
        for relation in relations:
            if relation.type not in type_groups:
                type_groups[relation.type] = []
            type_groups[relation.type].append(relation)

        for rel_type, rel_list in type_groups.items():
            for i in range(0, len(rel_list), batch_size):
                batch = rel_list[i : i + batch_size]

                query = f"""
                UNWIND $relations AS relation
                MATCH (from:Entity {{name: relation.from_name, paper_id: relation.paper_id}})
                MATCH (to:Entity {{name: relation.to_name, paper_id: relation.paper_id}})
                MERGE (from)-[r:{rel_type}]->(to)
                SET r.description = relation.description,
                    r.updated_at = datetime()
                ON CREATE SET r.created_at = datetime()
                RETURN count(r) AS count
                """

                try:
                    with self.driver.session() as session:
                        relation_dicts = [
                            {
                                "from_name": r.from_entity,
                                "to_name": r.to_entity,
                                "paper_id": r.paper_id,
                                "description": r.description,
                            }
                            for r in batch
                        ]

                        result = session.run(query, relations=relation_dicts)
                        count += len(batch)
                except Exception as e:
                    print(f"批量创建关系失败 ({rel_type}): {str(e)}")

        return count

    def get_subgraph(
        self, entity_names: List[str], paper_id: Optional[str] = None, depth: int = 2
    ) -> Dict[str, List]:
        """
        获取子图

        Args:
            entity_names: 起始实体名称列表
            paper_id: 可选的论文ID过滤
            depth: 遍历深度

        Returns:
            {"nodes": [...], "relationships": [...]}
        """
        if paper_id:
            query = f"""
            MATCH path = (n:Entity)-[*1..{depth}]-(m:Entity)
            WHERE n.name IN $entity_names AND n.paper_id = $paper_id
            RETURN path
            LIMIT 100
            """
            params = {"entity_names": entity_names, "paper_id": paper_id}
        else:
            query = f"""
            MATCH path = (n:Entity)-[*1..{depth}]-(m:Entity)
            WHERE n.name IN $entity_names
            RETURN path
            LIMIT 100
            """
            params = {"entity_names": entity_names}

        nodes = {}
        relationships = []

        try:
            with self.driver.session() as session:
                result = session.run(query, params)

                for record in result:
                    path = record["path"]

                    # 提取节点
                    for node in path.nodes:
                        node_id = f"{node['name']}_{node['paper_id']}"
                        if node_id not in nodes:
                            nodes[node_id] = {
                                "name": node["name"],
                                "type": node.get("type", "Unknown"),
                                "description": node.get("description", ""),
                                "paper_id": node["paper_id"],
                            }

                    # 提取关系
                    for rel in path.relationships:
                        relationships.append(
                            {
                                "from": rel.start_node["name"],
                                "to": rel.end_node["name"],
                                "type": rel.type,
                                "description": rel.get("description", ""),
                            }
                        )

        except Exception as e:
            print(f"获取子图失败: {str(e)}")

        return {"nodes": list(nodes.values()), "relationships": relationships}

    def get_entity_neighbors(
        self, entity_name: str, paper_id: Optional[str] = None, depth: int = 1
    ) -> Dict[str, List]:
        """
        获取实体的邻居节点

        Args:
            entity_name: 实体名称
            paper_id: 可选的论文ID
            depth: 遍历深度

        Returns:
            {"nodes": [...], "relationships": [...]}
        """
        return self.get_subgraph([entity_name], paper_id, depth)

    def search_entities(
        self,
        keyword: str,
        paper_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """
        关键词搜索实体

        Args:
            keyword: 搜索关键词
            paper_id: 可选的论文ID过滤
            entity_type: 可选的实体类型过滤
            limit: 返回数量限制

        Returns:
            实体列表
        """
        conditions = ["(e.name CONTAINS $keyword OR e.description CONTAINS $keyword)"]
        params = {"keyword": keyword, "limit": limit}

        if paper_id:
            conditions.append("e.paper_id = $paper_id")
            params["paper_id"] = paper_id

        if entity_type:
            conditions.append("e.type = $entity_type")
            params["entity_type"] = entity_type

        where_clause = " AND ".join(conditions)

        query = f"""
        MATCH (e:Entity)
        WHERE {where_clause}
        RETURN e
        LIMIT $limit
        """

        entities = []
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                for record in result:
                    node = record["e"]
                    entities.append(
                        {
                            "name": node["name"],
                            "type": node.get("type", "Unknown"),
                            "description": node.get("description", ""),
                            "paper_id": node["paper_id"],
                            "section": node.get("section", ""),
                            "page": node.get("page", 0),
                        }
                    )
        except Exception as e:
            print(f"搜索实体失败: {str(e)}")

        return entities

    def get_all_entities(
        self, paper_id: Optional[str] = None, limit: int = 1000
    ) -> List[Dict]:
        """获取所有实体"""
        if paper_id:
            query = """
            MATCH (e:Entity)
            WHERE e.paper_id = $paper_id
            RETURN e
            LIMIT $limit
            """
            params = {"paper_id": paper_id, "limit": limit}
        else:
            query = """
            MATCH (e:Entity)
            RETURN e
            LIMIT $limit
            """
            params = {"limit": limit}

        entities = []
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                for record in result:
                    node = record["e"]
                    entities.append(
                        {
                            "name": node["name"],
                            "type": node.get("type", "Unknown"),
                            "description": node.get("description", ""),
                            "paper_id": node["paper_id"],
                        }
                    )
        except Exception as e:
            print(f"获取实体失败: {str(e)}")

        return entities

    def delete_paper(self, paper_id: str) -> bool:
        """
        删除论文及其所有知识

        Args:
            paper_id: 论文ID

        Returns:
            是否成功删除
        """
        query = """
        MATCH (e:Entity)
        WHERE e.paper_id = $paper_id
        DETACH DELETE e
        """

        try:
            with self.driver.session() as session:
                session.run(query, paper_id=paper_id)
                print(f"✓ 已删除论文 {paper_id} 的所有数据")
                return True
        except Exception as e:
            print(f"删除论文失败: {str(e)}")
            return False

    def clear_database(self) -> bool:
        """清空整个数据库（谨慎使用！）"""
        confirm = input("确定要清空整个数据库吗？输入 'yes' 确认: ")
        if confirm != "yes":
            print("操作已取消")
            return False

        query = "MATCH (n) DETACH DELETE n"

        try:
            with self.driver.session() as session:
                session.run(query)
                print("✓ 数据库已清空")
                return True
        except Exception as e:
            print(f"清空数据库失败: {str(e)}")
            return False

    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        stats = {}

        queries = {
            "total_entities": "MATCH (e:Entity) RETURN count(e) AS count",
            "total_relations": "MATCH ()-[r]->() RETURN count(r) AS count",
            "entity_types": "MATCH (e:Entity) RETURN e.type AS type, count(e) AS count",
            "papers": "MATCH (e:Entity) RETURN DISTINCT e.paper_id AS paper_id, count(e) AS count",
        }

        try:
            with self.driver.session() as session:
                for key, query in queries.items():
                    result = session.run(query)

                    if key in ["total_entities", "total_relations"]:
                        record = result.single()
                        stats[key] = record["count"] if record else 0
                    else:
                        stats[key] = [
                            {"name": r[key.rstrip("s")], "count": r["count"]}
                            for r in result
                        ]
        except Exception as e:
            print(f"获取统计信息失败: {str(e)}")

        return stats


class GraphBuilder:
    """图谱构建器 - 整合实体和关系的批量存储"""

    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j = neo4j_client

    def build_from_extraction(
        self,
        entities: List[Entity],
        relations: List[Relation],
        show_progress: bool = True,
    ) -> Dict[str, int]:
        """
        从抽取结果构建知识图谱

        Args:
            entities: 实体列表
            relations: 关系列表
            show_progress: 是否显示进度

        Returns:
            {"entities": 创建数, "relations": 创建数}
        """
        print(f"开始构建图谱: {len(entities)} 个实体, {len(relations)} 个关系")

        # 创建实体
        print("创建实体...")
        entity_count = self.neo4j.create_entities_batch(entities)
        print(f"✓ 成功创建 {entity_count} 个实体")

        # 创建关系
        print("创建关系...")
        relation_count = self.neo4j.create_relations_batch(relations)
        print(f"✓ 成功创建 {relation_count} 个关系")

        return {"entities": entity_count, "relations": relation_count}

    def build_from_paper_knowledge(self, knowledge: Dict) -> Dict[str, int]:
        """
        从论文知识构建图谱

        Args:
            knowledge: extract_from_paper返回的知识字典

        Returns:
            {"entities": 创建数, "relations": 创建数}
        """
        entities = knowledge.get("entities", [])
        relations = knowledge.get("relations", [])

        return self.build_from_extraction(entities, relations)


if __name__ == "__main__":
    # 测试代码
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # 连接数据库
    client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
    )

    # 创建约束和索引
    client.create_constraints()

    # 获取统计信息
    stats = client.get_statistics()
    print("\n数据库统计:")
    print(f"  实体总数: {stats.get('total_entities', 0)}")
    print(f"  关系总数: {stats.get('total_relations', 0)}")

    # 关闭连接
    client.close()
