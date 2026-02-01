"""
文档处理模块 - PDF解析和文本切分
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import re
import hashlib
from datetime import datetime

import pdfplumber


@dataclass
class DocumentChunk:
    """文档片段数据类"""

    text: str
    page: int
    section: str
    paper_id: str
    chunk_id: str = ""
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.chunk_id:
            # 生成唯一ID
            content = f"{self.paper_id}_{self.page}_{self.section}_{self.text[:50]}"
            self.chunk_id = hashlib.md5(content.encode()).hexdigest()[:16]


class PDFParser:
    """PDF文档解析器 - 提取文本和结构"""

    # 章节标题正则表达式
    SECTION_PATTERNS = [
        r"^\d+\.\s+\w+",  # 1. Introduction
        r"^(Abstract|Introduction|Related\s+Work|Methodology?|Methods?|Experiments?|Results?|Discussion|Conclusion|Conclusions|References?|Acknowledgments?)$",
        r"^[IVX]+\.\s+\w+",  # I. Introduction, II. Method
        r"^\d+\.\d+\s+\w+",  # 1.1 Background
    ]

    def __init__(self, pdf_path: str, paper_id: Optional[str] = None):
        """
        初始化PDF解析器

        Args:
            pdf_path: PDF文件路径
            paper_id: 论文唯一标识，默认从文件名生成
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        self.paper_id = paper_id or self._generate_paper_id()
        self.section_pattern = re.compile(
            "|".join(self.SECTION_PATTERNS), re.IGNORECASE
        )

    def _generate_paper_id(self) -> str:
        """从文件名生成论文ID"""
        filename = self.pdf_path.stem
        # 移除特殊字符，限制长度
        clean_name = re.sub(r"[^\w\s-]", "", filename)
        clean_name = re.sub(r"[-\s]+", "_", clean_name)
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{clean_name}_{timestamp}"

    def parse(
        self, min_chunk_length: int = 100, max_chunk_length: int = 2000
    ) -> List[DocumentChunk]:
        """
        解析PDF文档

        Args:
            min_chunk_length: 最小片段长度（字符数）
            max_chunk_length: 最大片段长度（字符数）

        Returns:
            DocumentChunk列表
        """
        chunks = []

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                current_section = "Unknown"
                paper_metadata = {
                    "total_pages": len(pdf.pages),
                    "file_name": self.pdf_path.name,
                    "file_size": self.pdf_path.stat().st_size,
                    "parsed_at": datetime.now().isoformat(),
                }

                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text or not text.strip():
                        continue

                    # 识别章节标题并更新当前章节
                    lines = text.split("\n")
                    for line in lines[:10]:  # 只检查前10行，避免误识别
                        if self._is_section_header(line.strip()):
                            current_section = line.strip()
                            break

                    # 按段落切分
                    paragraphs = self._split_paragraphs(text, min_chunk_length)

                    for para in paragraphs:
                        # 如果段落太长，进一步切分
                        if len(para) > max_chunk_length:
                            sub_chunks = self._chunk_text(para, max_chunk_length)
                            for sub_chunk in sub_chunks:
                                if len(sub_chunk.strip()) >= min_chunk_length:
                                    chunks.append(
                                        DocumentChunk(
                                            text=sub_chunk.strip(),
                                            page=page_num,
                                            section=current_section,
                                            paper_id=self.paper_id,
                                            metadata={
                                                **paper_metadata,
                                                "char_count": len(sub_chunk),
                                                "is_sub_chunk": True,
                                            },
                                        )
                                    )
                        else:
                            chunks.append(
                                DocumentChunk(
                                    text=para.strip(),
                                    page=page_num,
                                    section=current_section,
                                    paper_id=self.paper_id,
                                    metadata={
                                        **paper_metadata,
                                        "char_count": len(para),
                                        "is_sub_chunk": False,
                                    },
                                )
                            )

        except Exception as e:
            raise RuntimeError(f"解析PDF失败: {str(e)}") from e

        return chunks

    def _is_section_header(self, line: str) -> bool:
        """判断是否为章节标题"""
        if not line or len(line) > 100:
            return False

        # 检查是否匹配章节模式
        if self.section_pattern.match(line.strip()):
            return True

        # 额外的启发式规则
        # 全大写且较短（可能是章节标题）
        if line.isupper() and 5 < len(line) < 50:
            return True

        # 包含特定关键词
        keywords = [
            "abstract",
            "introduction",
            "conclusion",
            "method",
            "result",
            "discussion",
        ]
        if any(keyword in line.lower() for keyword in keywords):
            return True

        return False

    def _split_paragraphs(self, text: str, min_length: int = 50) -> List[str]:
        """将文本分割为段落"""
        # 按多个换行符分割（段落分隔）
        paragraphs = re.split(r"\n\s*\n", text)

        # 过滤并清理
        result = []
        for para in paragraphs:
            clean = para.strip()
            # 移除多余的空白字符
            clean = re.sub(r"\s+", " ", clean)
            if len(clean) >= min_length:
                result.append(clean)

        return result

    def _chunk_text(self, text: str, max_length: int) -> List[str]:
        """将长文本切分为较小的片段"""
        chunks = []
        sentences = self._split_sentences(text)

        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > max_length and current_chunk:
                # 保存当前片段
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        # 添加最后一个片段
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """将文本分割为句子"""
        # 使用正则表达式匹配句子结尾
        sentence_endings = r"(?<=[.!?])\s+(?=[A-Z])"
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]

    def extract_metadata(self) -> Dict:
        """提取PDF元数据（标题、作者等）"""
        metadata = {
            "paper_id": self.paper_id,
            "file_path": str(self.pdf_path),
            "file_name": self.pdf_path.name,
        }

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # 尝试从第一页提取标题和作者
                first_page = pdf.pages[0]
                text = first_page.extract_text()

                if text:
                    lines = text.split("\n")[:20]  # 检查前20行

                    # 启发式提取标题（通常是最长的行，在第一页上半部分）
                    title_candidates = [
                        line.strip() for line in lines if 20 < len(line.strip()) < 200
                    ]
                    if title_candidates:
                        metadata["title"] = title_candidates[0]

                    # 尝试找到作者（通常在标题下方，包含@或机构名）
                    for line in lines:
                        if "@" in line or "University" in line or "Institute" in line:
                            metadata["author_hint"] = line.strip()
                            break

                # 获取PDF文档元数据
                if pdf.metadata:
                    pdf_meta = pdf.metadata
                    metadata["pdf_metadata"] = {
                        "title": pdf_meta.get("Title"),
                        "author": pdf_meta.get("Author"),
                        "creator": pdf_meta.get("Creator"),
                        "producer": pdf_meta.get("Producer"),
                        "creation_date": pdf_meta.get("CreationDate"),
                    }

        except Exception as e:
            metadata["extraction_error"] = str(e)

        return metadata


class DocumentLoader:
    """文档加载器 - 批量处理多个PDF"""

    def __init__(self, min_chunk_length: int = 100, max_chunk_length: int = 2000):
        self.min_chunk_length = min_chunk_length
        self.max_chunk_length = max_chunk_length

    def load_single(
        self, pdf_path: str, paper_id: Optional[str] = None
    ) -> Tuple[List[DocumentChunk], Dict]:
        """
        加载单个PDF文档

        Returns:
            (chunks列表, 元数据字典)
        """
        parser = PDFParser(pdf_path, paper_id)
        chunks = parser.parse(self.min_chunk_length, self.max_chunk_length)
        metadata = parser.extract_metadata()

        return chunks, metadata

    def load_directory(
        self, directory: str, pattern: str = "*.pdf"
    ) -> List[Tuple[List[DocumentChunk], Dict]]:
        """
        批量加载目录中的所有PDF

        Args:
            directory: PDF目录路径
            pattern: 文件匹配模式

        Returns:
            (chunks列表, 元数据字典) 的列表
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        results = []
        pdf_files = list(dir_path.glob(pattern))

        print(f"发现 {len(pdf_files)} 个PDF文件")

        for pdf_file in pdf_files:
            try:
                print(f"处理: {pdf_file.name}")
                chunks, metadata = self.load_single(str(pdf_file))
                results.append((chunks, metadata))
                print(f"  ✓ 提取 {len(chunks)} 个片段")
            except Exception as e:
                print(f"  ✗ 处理失败: {str(e)}")

        return results


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        loader = DocumentLoader()
        chunks, metadata = loader.load_single(pdf_path)

        print(f"\n论文ID: {metadata['paper_id']}")
        print(f"提取片段数: {len(chunks)}")
        print(f"\n前3个片段预览:")
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"\n--- 片段 {i} ---")
            print(f"章节: {chunk.section}")
            print(f"页码: {chunk.page}")
            print(f"内容: {chunk.text[:200]}...")
    else:
        print("用法: python pdf_parser.py <pdf_path>")
