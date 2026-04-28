#!/usr/bin/env python3
"""
Autodream 数据库迁移脚本
执行此脚本创建用户习惯表和升级现有数据库
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from cognix.storage.sqlite_store import sqlite_store

def run_migration():
    print("开始执行Autodream数据库迁移...")
    
    # 初始化数据库表（SQLiteStore初始化时会自动创建不存在的表）
    # user_habits表会在SQLiteStore._init_tables中自动创建
    print("✅ 用户习惯表(user_habits)创建完成")
    
    # 检查并添加现有表缺失的字段（如果需要）
    conn = sqlite_store.conn
    cursor = conn.cursor()
    
    # 检查preferences表是否有weight字段
    cursor.execute("PRAGMA table_info(preferences)")
    columns = [row[1] for row in cursor.fetchall()]
    if "weight" not in columns:
        cursor.execute("ALTER TABLE preferences ADD COLUMN weight REAL DEFAULT 1.0")
        print("✅ preferences表添加weight字段完成")
    
    conn.commit()
    print("\n🎉 数据库迁移完成！")
    print("\n使用说明：")
    print("1. 在.env文件中添加配置 AUTODREAM_ENABLED=true 开启Autodream功能")
    print("2. 可选配置：")
    print("   AUTODREAM_SCHEDULE_INTERVAL=24  # 定时执行间隔，单位小时")
    print("   AUTODREAM_DEDUPLICATION_THRESHOLD=0.85  # 去重相似度阈值")
    
    return True

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        sys.exit(1)
