#!/usr/bin/env python3
"""
问答测试脚本
"""

import argparse
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.qa.chain import KnowledgeGraphQAChain
from dotenv import load_dotenv

load_dotenv()


def interactive_mode(chain: KnowledgeGraphQAChain):
    """交互式问答模式"""
    print("\n" + "=" * 60)
    print("知识图谱问答系统 - 交互模式")
    print("=" * 60)
    print("命令:")
    print("  :quit 或 :q - 退出")
    print("  :context 或 :c - 显示检索上下文")
    print("  :eval 或 :e - 评估回答质量")
    print("  :paper <id> - 设置论文ID过滤")
    print("  :clear - 清除当前论文ID")
    print("=" * 60 + "\n")

    current_paper_id = None
    last_result = None

    while True:
        try:
            # 获取用户输入
            user_input = input("\n你: ").strip()

            if not user_input:
                continue

            # 处理命令
            if user_input.lower() in [":quit", ":q"]:
                print("再见!")
                break

            elif user_input.lower() in [":context", ":c"]:
                if last_result and "context" in last_result:
                    print("\n上下文:")
                    print(last_result["context"])
                else:
                    print("还没有上下文，请先提问")
                continue

            elif user_input.lower() in [":eval", ":e"]:
                if last_result:
                    result = chain.ask(
                        question=last_result["question"],
                        paper_id=current_paper_id,
                        include_evaluation=True,
                    )
                    print("\n评估结果:")
                    if "evaluation" in result:
                        for key, value in result["evaluation"].items():
                            print(f"  {key}: {value}")
                else:
                    print("还没有回答，请先提问")
                continue

            elif user_input.lower().startswith(":paper "):
                current_paper_id = user_input[7:].strip()
                print(f"设置论文ID: {current_paper_id}")
                continue

            elif user_input.lower() == ":clear":
                current_paper_id = None
                print("清除论文ID过滤")
                continue

            # 执行问答
            print("\n思考中...")
            result = chain.ask(
                question=user_input, paper_id=current_paper_id, include_context=False
            )

            last_result = result

            # 显示答案
            print(f"\n助手: {result['answer']}")

            # 显示检索统计
            if result["success"]:
                print(
                    f"\n[检索到 {result['total_entities']} 个实体, {result['total_relations']} 个关系]"
                )
            else:
                print(f"\n[错误: {result.get('error', 'Unknown')}")

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n错误: {str(e)}")


def single_question(chain: KnowledgeGraphQAChain, question: str, paper_id: str = None):
    """单问题模式"""
    print(f"\n问题: {question}")
    if paper_id:
        print(f"论文ID: {paper_id}")
    print("思考中...\n")

    result = chain.ask(
        question=question,
        paper_id=paper_id,
        include_context=True,
        include_evaluation=True,
    )

    print(f"答案: {result['answer']}\n")

    if result["success"]:
        print(f"检索统计:")
        print(f"  实体: {result['total_entities']} 个")
        print(f"  关系: {result['total_relations']} 个")

        if result.get("evaluation"):
            print(f"\n质量评估:")
            for key, value in result["evaluation"].items():
                print(f"  {key}: {value}")

        if result.get("context"):
            print(f"\n检索上下文:\n{result['context'][:500]}...")


def batch_questions(
    chain: KnowledgeGraphQAChain, questions_file: str, paper_id: str = None
):
    """批量问答模式"""
    try:
        with open(questions_file, "r", encoding="utf-8") as f:
            questions = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    except Exception as e:
        print(f"读取问题文件失败: {str(e)}")
        return

    print(f"\n批量问答: {len(questions)} 个问题\n")

    results = []
    for i, question in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {question}")

        result = chain.ask(question=question, paper_id=paper_id)
        results.append(
            {
                "question": question,
                "answer": result["answer"],
                "success": result["success"],
            }
        )

        print(f"  -> {result['answer'][:100]}...\n")

    # 保存结果
    output_file = f"qa_results_{Path(questions_file).stem}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="知识图谱问答测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式问答
  python ask.py
  
  # 单问题
  python ask.py -q "这篇论文使用了什么方法？"
  
  # 指定论文ID
  python ask.py -q "数据集是什么？" --paper-id paper_001
  
  # 批量问答
  python ask.py -f questions.txt
        """,
    )

    parser.add_argument("-q", "--question", help="单个问题")
    parser.add_argument("-f", "--file", help="问题列表文件（每行一个问题）")
    parser.add_argument("--paper-id", help="论文ID过滤")
    parser.add_argument("--output", help="批量问答结果输出文件")

    args = parser.parse_args()

    # 初始化问答链
    print("初始化问答系统...")
    chain = KnowledgeGraphQAChain()

    try:
        if args.file:
            # 批量模式
            batch_questions(chain, args.file, args.paper_id)
        elif args.question:
            # 单问题模式
            single_question(chain, args.question, args.paper_id)
        else:
            # 交互模式
            interactive_mode(chain)

    except KeyboardInterrupt:
        print("\n\n再见!")
    finally:
        chain.close()


if __name__ == "__main__":
    main()
