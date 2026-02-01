"""
知识抽取模块 - 使用LLM提取实体和关系
"""

import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ..ingestion.pdf_parser import DocumentChunk


@dataclass
class Entity:
    """知识实体"""

    name: str
    type: str
    description: str
    paper_id: str
    section: str = ""
    page: int = 0
    source_text: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "paper_id": self.paper_id,
            "section": self.section,
            "page": self.page,
            "source_text": self.source_text[:200],  # 限制长度
        }


@dataclass
class Relation:
    """实体关系"""

    from_entity: str
    to_entity: str
    type: str
    description: str
    paper_id: str

    def to_dict(self) -> Dict:
        return {
            "from": self.from_entity,
            "to": self.to_entity,
            "type": self.type,
            "description": self.description,
            "paper_id": self.paper_id,
        }


class EntityExtractor:
    """实体抽取器 - 使用LLM从文本中抽取实体"""

    # 实体类型定义
    ENTITY_TYPES = [
        "Concept",  # 核心概念、理论、定义
        "Method",  # 方法、算法、技术、框架
        "Dataset",  # 数据集、语料、基准
        "Model",  # 模型、架构、网络结构
        "Metric",  # 评估指标、性能度量
        "Result",  # 实验结果、发现、结论
        "Problem",  # 研究问题、挑战
        "Application",  # 应用场景、应用领域
    ]

    # 关系类型定义
    RELATION_TYPES = [
        "USES",  # 使用（方法→数据集）
        "BASED_ON",  # 基于（方法→方法/理论）
        "ACHIEVES",  # 达到（模型→指标值）
        "COMPARES_TO",  # 对比（方法↔方法）
        "PART_OF",  # 部分（组件→整体）
        "LEADS_TO",  # 导致（实验→结论）
        "APPLIES_TO",  # 应用于（方法→场景）
        "EVALUATED_ON",  # 在...上评估（模型→数据集）
        "IMPROVES",  # 改进（新方法→旧方法）
        "CITES",  # 引用（论文→论文）
    ]

    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ):
        self.llm = ChatOpenAI(
            model=model_name, temperature=temperature, max_tokens=max_tokens
        )
        self.prompt = self._build_prompt()
        self.chain = self.prompt | self.llm | StrOutputParser()

    def _build_prompt(self) -> ChatPromptTemplate:
        """构建抽取提示模板"""
        entity_types_str = ", ".join(self.ENTITY_TYPES)
        relation_types_str = ", ".join(self.RELATION_TYPES)

        template = f"""你是一个专业的学术论文知识抽取助手。请从以下论文段落中抽取结构化知识。

实体类型包括：{entity_types_str}

关系类型包括：{relation_types_str}

抽取规则：
1. 只提取明确提到的核心概念、方法、数据集等
2. 每个实体应包含：名称、类型、简短描述
3. 关系应准确反映实体间的逻辑联系
4. 如果段落中没有明确的知识，返回空列表
5. 确保抽取的知识准确、完整

论文段落内容：
{{text}}

请以JSON格式输出（不要包含任何其他解释）：
{{
  "entities": [
    {{
      "name": "实体名称",
      "type": "实体类型",
      "description": "简短描述（50字以内）"
    }}
  ],
  "relations": [
    {{
      "from": "起始实体名称",
      "to": "目标实体名称",
      "type": "关系类型",
      "description": "关系描述（可选）"
    }}
  ]
}}

只输出JSON，不要添加markdown代码块标记或其他说明文字。"""

        return ChatPromptTemplate.from_template(template)

    def extract(self, chunk: DocumentChunk) -> Dict[str, List]:
        """
        从单个文本片段抽取知识

        Returns:
            {"entities": List[Entity], "relations": List[Relation]}
        """
        try:
            # 调用LLM抽取
            result_text = self.chain.invoke({"text": chunk.text})

            # 解析JSON结果
            knowledge = self._parse_json(result_text)

            # 转换为实体和关系对象
            entities = []
            for e in knowledge.get("entities", []):
                if self._validate_entity(e):
                    entity = Entity(
                        name=e["name"],
                        type=e["type"],
                        description=e.get("description", ""),
                        paper_id=chunk.paper_id,
                        section=chunk.section,
                        page=chunk.page,
                        source_text=chunk.text[:500],  # 保存源文本片段
                    )
                    entities.append(entity)

            relations = []
            for r in knowledge.get("relations", []):
                if self._validate_relation(r, entities):
                    relation = Relation(
                        from_entity=r["from"],
                        to_entity=r["to"],
                        type=r["type"],
                        description=r.get("description", ""),
                        paper_id=chunk.paper_id,
                    )
                    relations.append(relation)

            return {"entities": entities, "relations": relations}

        except Exception as e:
            print(f"抽取失败: {str(e)}")
            return {"entities": [], "relations": []}

    def extract_batch(
        self,
        chunks: List[DocumentChunk],
        max_workers: int = 3,
        show_progress: bool = True,
    ) -> List[Dict[str, List]]:
        """
        批量抽取知识

        Args:
            chunks: 文本片段列表
            max_workers: 并行线程数
            show_progress: 是否显示进度条

        Returns:
            抽取结果列表
        """
        results = []

        if show_progress:
            chunks = tqdm(chunks, desc="抽取知识")

        # 串行处理（避免API限流）
        for chunk in chunks:
            result = self.extract(chunk)
            results.append(result)

        return results

    def _parse_json(self, text: str) -> Dict:
        """解析LLM返回的JSON文本"""
        # 移除markdown代码块标记
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

        # 尝试解析JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass

            # 返回空结果
            return {"entities": [], "relations": []}

    def _validate_entity(self, entity: Dict) -> bool:
        """验证实体格式"""
        if not entity.get("name") or not entity.get("type"):
            return False

        if entity["type"] not in self.ENTITY_TYPES:
            return False

        # 清理名称
        entity["name"] = entity["name"].strip()
        if len(entity["name"]) < 2 or len(entity["name"]) > 100:
            return False

        return True

    def _validate_relation(self, relation: Dict, entities: List[Entity]) -> bool:
        """验证关系格式"""
        if (
            not relation.get("from")
            or not relation.get("to")
            or not relation.get("type")
        ):
            return False

        if relation["type"] not in self.RELATION_TYPES:
            return False

        # 检查实体是否存在
        entity_names = {e.name for e in entities}
        if relation["from"] not in entity_names or relation["to"] not in entity_names:
            # 允许跨片段的关系，但给出警告
            pass

        return True


class EntityAligner:
    """实体对齐器 - 合并相似实体"""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.openai = None  # 延迟初始化

    def align(
        self, entities: List[Entity], relations: List[Relation]
    ) -> Tuple[List[Entity], List[Relation]]:
        """
        对齐实体，合并相似实体

        Args:
            entities: 原始实体列表
            relations: 原始关系列表

        Returns:
            (对齐后的实体列表, 更新后的关系列表)
        """
        if not entities:
            return [], []

        # 按类型分组
        type_groups = {}
        for entity in entities:
            if entity.type not in type_groups:
                type_groups[entity.type] = []
            type_groups[entity.type].append(entity)

        # 在每个类型组内合并相似实体
        merged_entities = []
        entity_mapping = {}  # 原始名称 -> 合并后名称

        for entity_type, group in type_groups.items():
            # 简单的字符串相似度合并
            group_merged = self._merge_by_similarity(group)

            for merged_entity, original_names in group_merged:
                merged_entities.append(merged_entity)
                for orig_name in original_names:
                    entity_mapping[orig_name] = merged_entity.name

        # 更新关系中的实体名称
        updated_relations = []
        for relation in relations:
            new_from = entity_mapping.get(relation.from_entity, relation.from_entity)
            new_to = entity_mapping.get(relation.to_entity, relation.to_entity)

            if new_from != new_to:  # 避免自环
                relation.from_entity = new_from
                relation.to_entity = new_to
                updated_relations.append(relation)

        return merged_entities, updated_relations

    def _merge_by_similarity(
        self, entities: List[Entity]
    ) -> List[Tuple[Entity, List[str]]]:
        """
        基于字符串相似度合并实体

        Returns:
            [(合并后的实体, 原始名称列表)]
        """
        if not entities:
            return []

        # 使用简单的字符串相似度（编辑距离）
        from difflib import SequenceMatcher

        def similar(a, b):
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        merged = []
        used = set()

        for i, entity in enumerate(entities):
            if i in used:
                continue

            # 找到所有相似的实体
            similar_group = [entity]
            original_names = [entity.name]
            used.add(i)

            for j, other in enumerate(entities[i + 1 :], start=i + 1):
                if j in used:
                    continue

                if similar(entity.name, other.name) > self.similarity_threshold:
                    similar_group.append(other)
                    original_names.append(other.name)
                    used.add(j)

            # 合并实体（选择最完整的描述）
            best_entity = max(similar_group, key=lambda e: len(e.description))
            merged.append((best_entity, original_names))

        return merged


class KnowledgeExtractor:
    """知识抽取主类 - 整合抽取和对齐流程"""

    def __init__(
        self,
        model_name: str = "gpt-4",
        enable_alignment: bool = True,
        alignment_threshold: float = 0.85,
    ):
        self.entity_extractor = EntityExtractor(model_name)
        self.entity_aligner = (
            EntityAligner(alignment_threshold) if enable_alignment else None
        )
        self.enable_alignment = enable_alignment

    def extract_from_chunks(
        self, chunks: List[DocumentChunk], batch_size: int = 5
    ) -> Dict[str, List]:
        """
        从文本片段抽取完整知识

        Args:
            chunks: 文本片段列表
            batch_size: 批处理大小

        Returns:
            {"entities": List[Entity], "relations": List[Relation]}
        """
        print(f"开始从 {len(chunks)} 个片段抽取知识...")

        # 批量抽取
        all_results = self.entity_extractor.extract_batch(chunks)

        # 合并所有结果
        all_entities = []
        all_relations = []

        for result in all_results:
            all_entities.extend(result["entities"])
            all_relations.extend(result["relations"])

        print(f"原始抽取: {len(all_entities)} 个实体, {len(all_relations)} 个关系")

        # 实体对齐（可选）
        if self.enable_alignment and self.entity_aligner:
            print("进行实体对齐...")
            all_entities, all_relations = self.entity_aligner.align(
                all_entities, all_relations
            )
            print(f"对齐后: {len(all_entities)} 个实体, {len(all_relations)} 个关系")

        return {"entities": all_entities, "relations": all_relations}

    def extract_from_paper(
        self, chunks: List[DocumentChunk], metadata: Dict
    ) -> Dict[str, Any]:
        """
        从整篇论文抽取知识

        Args:
            chunks: 论文文本片段
            metadata: 论文元数据

        Returns:
            包含实体、关系和元数据的完整知识图谱
        """
        # 抽取知识
        knowledge = self.extract_from_chunks(chunks)

        # 添加论文节点
        paper_entity = Entity(
            name=metadata.get("title", metadata["paper_id"]),
            type="Paper",
            description=f"论文: {metadata.get('title', metadata['paper_id'])}",
            paper_id=metadata["paper_id"],
            section="",
            page=0,
        )

        # 将论文与其他实体建立PART_OF关系
        paper_relations = []
        for entity in knowledge["entities"]:
            if entity.type != "Paper":
                rel = Relation(
                    from_entity=entity.name,
                    to_entity=paper_entity.name,
                    type="PART_OF",
                    description="",
                    paper_id=metadata["paper_id"],
                )
                paper_relations.append(rel)

        # 组装结果
        return {
            "paper_id": metadata["paper_id"],
            "metadata": metadata,
            "entities": [paper_entity] + knowledge["entities"],
            "relations": knowledge["relations"] + paper_relations,
        }


if __name__ == "__main__":
    # 测试代码
    from ..ingestion.pdf_parser import DocumentLoader

    import sys
    import os

    # 添加项目根目录到路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]

        # 加载文档
        loader = DocumentLoader()
        chunks, metadata = loader.load_single(pdf_path)

        print(f"\n论文: {metadata.get('title', metadata['paper_id'])}")
        print(f"片段数: {len(chunks)}")

        # 抽取知识（只处理前5个片段作为测试）
        extractor = KnowledgeExtractor(model_name="gpt-4")
        result = extractor.extract_from_paper(chunks[:5], metadata)

        print(f"\n抽取结果:")
        print(f"实体数量: {len(result['entities'])}")
        print(f"关系数量: {len(result['relations'])}")

        print("\n实体列表:")
        for entity in result["entities"][:10]:  # 只显示前10个
            print(f"  - [{entity.type}] {entity.name}")

        print("\n关系列表:")
        for relation in result["relations"][:10]:
            print(
                f"  - {relation.from_entity} --[{relation.type}]--> {relation.to_entity}"
            )
    else:
        print("用法: python entity_extractor.py <pdf_path>")
