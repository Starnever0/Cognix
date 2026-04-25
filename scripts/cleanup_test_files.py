#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理测试文件脚本

用法:
    python cleanup_test_files.py [DIR] [--all]
    
参数:
    DIR          指定要删除的目录路径
    --all        删除项目根目录下所有 tmp* 开头的临时目录
"""

import sys
import shutil
from pathlib import Path
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="清理测试文件")
    parser.add_argument('directory', nargs='?', type=str, default=None,
                        help='指定要删除的目录路径')
    parser.add_argument('--all', action='store_true',
                        help='删除项目根目录下所有 tmp* 开头的临时目录')
    return parser.parse_args()


def delete_directory(dir_path):
    """删除指定目录"""
    try:
        dir_path = Path(dir_path)
        if not dir_path.exists():
            print(f"[跳过] 目录不存在: {dir_path}")
            return False
        
        if not dir_path.is_dir():
            print(f"[错误] 不是目录: {dir_path}")
            return False
        
        print(f"[删除] {dir_path}")
        shutil.rmtree(dir_path)
        print(f"[OK] 已删除: {dir_path}")
        return True
    except Exception as e:
        print(f"[错误] 删除失败: {dir_path}, 错误: {e}")
        return False


def find_all_temp_dirs(project_root):
    """查找项目根目录下所有 tmp* 开头的临时目录"""
    temp_dirs = []
    root_path = Path(project_root)
    
    for item in root_path.iterdir():
        if item.is_dir() and item.name.startswith('tmp'):
            temp_dirs.append(item)
    
    return temp_dirs


def main():
    args = parse_args()
    project_root = Path(__file__).parent.parent
    
    if args.all:
        # 删除所有临时目录
        temp_dirs = find_all_temp_dirs(project_root)
        
        if not temp_dirs:
            print("[信息] 没有找到临时目录")
            return
        
        print(f"[信息] 找到 {len(temp_dirs)} 个临时目录:")
        for d in temp_dirs:
            print(f"  - {d}")
        
        # 确认删除
        response = input("\n确认删除以上目录? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            deleted_count = 0
            for d in temp_dirs:
                if delete_directory(d):
                    deleted_count += 1
            print(f"\n[完成] 共删除 {deleted_count} 个目录")
        else:
            print("[取消] 未删除任何目录")
    
    elif args.directory:
        # 删除指定目录
        delete_directory(args.directory)
    
    else:
        # 显示帮助
        print("请指定目录或使用 --all 选项")
        print("运行 'python cleanup_test_files.py --help' 查看帮助")


if __name__ == "__main__":
    main()
