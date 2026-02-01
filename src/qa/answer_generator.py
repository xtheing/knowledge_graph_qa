"""
答案生成模块 - 基于知识图谱的问答
"""

from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class AnswerGenerator:
    """基于知识图谱的答案生成器"""

    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ):
        """
        初始化答案生成器

        Args:
            model_name: LLM模型名称
            temperature: 温度参数
            max_tokens: 最大生成token数
        """
        self.llm = ChatOpenAI(
            model=model_name, temperature=temperature, max_tokens=max_tokens
        )
        self.prompt = self._build_prompt()
        self.chain = self.prompt | self.llm | StrOutputParser()

    def _build_prompt(self) -> ChatPromptTemplate:
        """构建问答提示模板"""
        template = """你是一个专业的学术问答助手。请基于提供的知识图谱上下文回答用户问题。

重要说明：
1. 只使用提供的上下文信息，不要引入外部知识
2. 如果上下文中没有相关信息，请明确说明"根据知识图谱中的信息，无法回答该问题"
3. 答案应该准确、简洁，并引用相关实体
4. 如果涉及多个实体，请说明它们之间的关系
5. 对于复杂的概念，请逐步解释
6. 回答使用中文

知识图谱上下文:
{context}

用户问题:
{question}

请提供结构化的回答，包含：
1. 直接答案
2. 相关概念解释（如需要）
3. 引用到的关键实体

回答:"""

        return ChatPromptTemplate.from_template(template)

    def generate(
        self, context: str, question: str, include_citations: bool = True
    ) -> Dict[str, Any]:
        """
        生成答案

        Args:
            context: 知识图谱上下文
            question: 用户问题
            include_citations: 是否包含引用

        Returns:
            包含答案和相关信息的字典
        """
        try:
            # 生成答案
            answer = self.chain.invoke({"context": context, "question": question})

            # 提取使用的实体（简单启发式）
            used_entities = self._extract_entities_from_context(context)

            return {
                "question": question,
                "answer": answer,
                "context_length": len(context),
                "used_entities": used_entities[:10],  # 限制数量
                "success": True,
            }

        except Exception as e:
            return {
                "question": question,
                "answer": f"生成答案时出错: {str(e)}",
                "context_length": len(context),
                "used_entities": [],
                "success": False,
                "error": str(e),
            }

    def generate_with_citations(
        self, context: str, question: str, citations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成带引用的答案

        Args:
            context: 知识图谱上下文
            question: 用户问题
            citations: 引用信息字典

        Returns:
            包含答案和引用的字典
        """
        # 构建带引用的提示
        citation_prompt = self._build_citation_prompt()
        citation_chain = citation_prompt | self.llm | StrOutputParser()

        # 格式化引用
        citation_text = self._format_citations(citations)

        try:
            answer = citation_chain.invoke(
                {"context": context, "question": question, "citations": citation_text}
            )

            return {
                "question": question,
                "answer": answer,
                "citations": citations,
                "success": True,
            }

        except Exception as e:
            return {
                "question": question,
                "answer": f"生成答案时出错: {str(e)}",
                "citations": citations,
                "success": False,
            }

    def _build_citation_prompt(self) -> ChatPromptTemplate:
        """构建带引用的提示模板"""
        template = """你是一个专业的学术问答助手。请基于知识图谱上下文回答问题，并在答案中标注引用。

引用格式：使用 [1], [2] 等标记，对应提供的引用列表。

知识图谱上下文:
{context}

可用引用:
{citations}

用户问题:
{question}

要求：
1. 只使用上下文中的信息
2. 在相关事实后标注引用标记，如 "该方法在ImageNet上达到了95%的准确率[1]"
3. 如果无法回答，明确说明
4. 回答使用中文

回答:"""

        return ChatPromptTemplate.from_template(template)

    def _format_citations(self, citations: Dict[str, Any]) -> str:
        """格式化引用信息"""
        lines = []
        for key, info in citations.items():
            line = f"{key}: {info['name']} ({info['type']})"
            if info.get("paper_id"):
                line += f" - 来源: {info['paper_id']}"
            lines.append(line)
        return "\n".join(lines)

    def _extract_entities_from_context(self, context: str) -> List[str]:
        """从上下文中提取使用的实体名称"""
        # 简单启发式：提取方括号中的类型标记后的名称
        import re

        # 匹配 "- [Type] Name:" 或 "- [Type] Name" 模式
        pattern = r"- \[([^\]]+)\] ([^:\n]+)"
        matches = re.findall(pattern, context)

        entities = []
        for match in matches:
            entity_name = match[1].strip()
            # 清理描述部分（如果有）
            if ":" in entity_name:
                entity_name = entity_name.split(":")[0].strip()
            entities.append(entity_name)

        return entities


class QuestionClassifier:
    """问题分类器 - 识别问题类型以优化检索策略"""

    QUESTION_TYPES = {
        "FACTUAL": "事实性问题（What/Which）",
        "COMPARISON": "比较性问题（Compare/Difference）",
        "CAUSAL": "因果性问题（Why/How）",
        "RELATIONAL": "关系性问题（Relationship）",
        "SUMMARY": "总结性问题（Overview）",
    }

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.1)
        self.prompt = self._build_prompt()
        self.chain = self.prompt | self.llm | StrOutputParser()

    def _build_prompt(self) -> ChatPromptTemplate:
        template = """请分析以下学术问题的类型，返回最匹配的类型标签。

问题类型：
- FACTUAL: 事实性问题，询问具体信息（如：什么是BERT？使用了什么数据集？）
- COMPARISON: 比较性问题，询问对比或差异（如：方法A和方法B有什么区别？）
- CAUSAL: 因果性问题，询问原因或机制（如：为什么这个方法有效？如何工作的？）
- RELATIONAL: 关系性问题，询问实体间关系（如：方法A和方法B的关系是什么？）
- SUMMARY: 总结性问题，询问概览（如：这篇论文的主要贡献是什么？）

问题: {question}

请只输出类型标签（如：FACTUAL），不要其他解释。"""

        return ChatPromptTemplate.from_template(template)

    def classify(self, question: str) -> str:
        """分类问题类型"""
        try:
            result = self.chain.invoke({"question": question})
            question_type = result.strip().upper()

            if question_type in self.QUESTION_TYPES:
                return question_type
            else:
                return "FACTUAL"  # 默认类型

        except Exception:
            return "FACTUAL"


class QAEvaluator:
    """问答评估器 - 评估回答质量"""

    def __init__(self):
        pass

    def evaluate(self, question: str, answer: str, context: str) -> Dict[str, Any]:
        """
        评估回答质量

        Returns:
            评估结果字典
        """
        metrics = {}

        # 1. 答案长度
        metrics["answer_length"] = len(answer)

        # 2. 上下文覆盖率（简单检查）
        context_entities = self._extract_entities(context)
        covered_entities = sum(
            1 for e in context_entities if e.lower() in answer.lower()
        )
        metrics["context_coverage"] = (
            covered_entities / len(context_entities) if context_entities else 0
        )

        # 3. 拒绝回答检测
        refusal_phrases = [
            "无法回答",
            "不知道",
            "没有相关信息",
            "根据知识图谱中的信息，无法",
            "cannot answer",
            "no information",
            "unable to",
        ]
        metrics["is_refusal"] = any(
            phrase in answer.lower() for phrase in refusal_phrases
        )

        # 4. 置信度（综合评分）
        if metrics["is_refusal"]:
            metrics["confidence"] = 0.0
        else:
            # 基于覆盖率和答案长度计算
            confidence = min(
                1.0,
                metrics["context_coverage"] * 0.7
                + min(1.0, metrics["answer_length"] / 500) * 0.3,
            )
            metrics["confidence"] = round(confidence, 2)

        return metrics

    def _extract_entities(self, context: str) -> List[str]:
        """从上下文中提取实体"""
        import re

        pattern = r"- \[([^\]]+)\] ([^:\n]+)"
        matches = re.findall(pattern, context)
        return [match[1].strip() for match in matches]


if __name__ == "__main__":
    # 测试代码
    import sys
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from dotenv import load_dotenv

    load_dotenv()

    # 初始化生成器
    generator = AnswerGenerator()

    # 测试上下文
    context = """相关概念和实体:
- [Method] BERT: 一种基于Transformer的预训练语言模型
- [Method] GPT: 生成式预训练Transformer模型
- [Dataset] ImageNet: 大规模图像识别数据集
- [Metric] F1 Score: 精确率和召回率的调和平均

实体间关系:
- BERT → [BASED_ON] → Transformer
- GPT → [COMPARES_TO] → BERT
- ResNet → [EVALUATED_ON] → ImageNet"""

    question = "BERT和GPT有什么区别？"

    print(f"问题: {question}")
    print(f"\n上下文:\n{context}\n")

    # 生成答案
    result = generator.generate(context, question)

    print(f"答案:\n{result['answer']}")
    print(f"\n使用的实体: {result['used_entities']}")
    print(f"上下文长度: {result['context_length']}")
    print(f"成功: {result['success']}")
