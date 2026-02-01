#!/usr/bin/env python3
"""
Neo4j数据库初始化脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.neo4j_client import Neo4jClient
from dotenv import load_dotenv

load_dotenv()


def setup_neo4j():
    """初始化Neo4j数据库"""
    print("初始化Neo4j数据库...")
    print("=" * 60)

    # 连接配置
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    print(f"连接URI: {uri}")
    print(f"用户名: {user}")

    try:
        # 创建客户端
        client = Neo4jClient(uri=uri, user=user, password=password)

        # 创建约束和索引
        print("\n创建约束和索引...")
        client.create_constraints()

        # 获取统计信息
        print("\n获取统计信息...")
        stats = client.get_statistics()

        print("\n当前数据库状态:")
        print(f"  实体总数: {stats.get('total_entities', 0)}")
        print(f"  关系总数: {stats.get('total_relations', 0)}")

        if stats.get("entity_types"):
            print("\n  实体类型分布:")
            for et in stats["entity_types"]:
                print(f"    - {et['name']}: {et['count']}")

        if stats.get("papers"):
            print(f"\n  已存储论文: {len(stats['papers'])} 篇")

        print("\n" + "=" * 60)
        print("✓ Neo4j初始化完成")
        print("=" * 60)

        client.close()
        return True

    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        print("\n请检查:")
        print("  1. Neo4j是否已启动")
        print("  2. 连接URI是否正确")
        print("  3. 用户名密码是否正确")
        return False


def reset_neo4j():
    """清空Neo4j数据库（危险操作！）"""
    print("⚠️  警告: 这将删除Neo4j中的所有数据!")
    confirm = input("请输入 'DELETE ALL DATA' 确认: ")

    if confirm != "DELETE ALL DATA":
        print("操作已取消")
        return False

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    try:
        client = Neo4jClient(uri=uri, user=user, password=password)
        client.clear_database()
        client.close()
        return True
    except Exception as e:
        print(f"清空失败: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Neo4j数据库管理工具")
    parser.add_argument("--reset", action="store_true", help="清空数据库（危险！）")

    args = parser.parse_args()

    if args.reset:
        success = reset_neo4j()
    else:
        success = setup_neo4j()

    sys.exit(0 if success else 1)
