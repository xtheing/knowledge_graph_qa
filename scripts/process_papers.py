#!/usr/bin/env python3
"""
论文处理脚本 - 命令行工具
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.qa.chain import KnowledgeGraphPipeline
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="处理学术论文并构建知识图谱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单篇论文
  python process_papers.py -f /path/to/paper.pdf
  
  # 批量处理目录
  python process_papers.py -d /path/to/papers/
  
  # 指定论文ID
  python process_papers.py -f /path/to/paper.pdf --paper-id my_paper_001
  
  # 限制处理片段数
  python process_papers.py -f /path/to/paper.pdf --max-chunks 30
        """,
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-f", "--file", help="单个PDF文件路径")
    input_group.add_argument("-d", "--directory", help="PDF文件目录")

    # 可选参数
    parser.add_argument("--paper-id", help="指定论文ID（默认自动生成）")
    parser.add_argument(
        "--max-chunks", type=int, default=50, help="每篇论文最大处理片段数（默认50）"
    )
    parser.add_argument(
        "--pattern", default="*.pdf", help="文件匹配模式（默认*.pdf，仅批量处理时有效）"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")

    args = parser.parse_args()

    # 初始化流程
    pipeline = KnowledgeGraphPipeline()

    try:
        if args.file:
            # 处理单篇论文
            if not os.path.exists(args.file):
                print(f"错误: 文件不存在: {args.file}")
                sys.exit(1)

            if not args.file.endswith(".pdf"):
                print(f"错误: 只支持PDF文件")
                sys.exit(1)

            print(f"处理文件: {args.file}")
            result = pipeline.process_paper(
                pdf_path=args.file, paper_id=args.paper_id, max_chunks=args.max_chunks
            )

            # 输出结果
            if result["success"]:
                print("\n" + "=" * 60)
                print("✅ 处理成功!")
                print("=" * 60)
                print(f"论文ID: {result['paper_id']}")
                print(f"标题: {result.get('title', 'Unknown')}")
                print(f"处理片段: {result['total_chunks']}")
                print(
                    f"实体: {result['entities_extracted']} 个（抽取）/ {result['entities_stored']} 个（存储）"
                )
                print(
                    f"关系: {result['relations_extracted']} 个（抽取）/ {result['relations_stored']} 个（存储）"
                )
                print(f"向量: {result['vectors_stored']} 个")
            else:
                print("\n" + "=" * 60)
                print("❌ 处理失败!")
                print("=" * 60)
                print(f"错误: {result.get('error', 'Unknown error')}")
                sys.exit(1)

        elif args.directory:
            # 批量处理目录
            if not os.path.isdir(args.directory):
                print(f"错误: 目录不存在: {args.directory}")
                sys.exit(1)

            print(f"批量处理目录: {args.directory}")
            print(f"文件模式: {args.pattern}")
            print(f"最大片段数: {args.max_chunks}\n")

            results = pipeline.process_directory(
                directory=args.directory,
                pattern=args.pattern,
                max_chunks_per_paper=args.max_chunks,
            )

            # 统计结果
            successful = [r for r in results if r["success"]]
            failed = [r for r in results if not r["success"]]

            print("\n" + "=" * 60)
            print("📊 批量处理统计")
            print("=" * 60)
            print(f"总计: {len(results)} 个文件")
            print(f"成功: {len(successful)} 个")
            print(f"失败: {len(failed)} 个")

            if successful:
                total_entities = sum(r["entities_stored"] for r in successful)
                total_relations = sum(r["relations_stored"] for r in successful)
                print(f"\n累计存储:")
                print(f"  实体: {total_entities} 个")
                print(f"  关系: {total_relations} 个")

            if failed and args.verbose:
                print("\n失败的文件:")
                for r in failed:
                    print(
                        f"  - {r.get('pdf_path', 'Unknown')}: {r.get('error', 'Unknown error')}"
                    )

    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
    finally:
        pipeline.close()
        print("\n✓ 完成")


if __name__ == "__main__":
    main()
