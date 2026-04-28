#!/usr/bin/env python3
"""
清理测试文件脚本

使用方法：
    python cleanup_test_files.py <目录>        # 清理指定目录
    python cleanup_test_files.py --all          # 清理所有临时测试目录
"""

import os
import sys
import shutil
import argparse
from pathlib import Path


def cleanup_directory(dir_path):
    """清理单个目录"""
    path = Path(dir_path)
    if not path.exists():
        print(f"目录不存在：{dir_path}")
        return False
    
    confirm = input(f"确认删除目录及其所有内容？\n  {path.absolute()}\n(y/n): ")
    if confirm.lower() != 'y':
        print("取消删除")
        return False
    
    try:
        shutil.rmtree(path)
        print(f"已删除：{path}")
        return True
    except Exception as e:
        print(f"删除失败：{e}")
        return False


def find_temp_test_dirs():
    """查找临时测试目录"""
    project_root = Path(__file__).parent.parent
    temp_dirs = []
    
    # 查找以tmp或test开头的目录
    for item in project_root.iterdir():
        if item.is_dir():
            name = item.name.lower()
            if name.startswith('tmp') or name.startswith('test_'):
                temp_dirs.append(item)
    
    return temp_dirs


def main():
    parser = argparse.ArgumentParser(description="清理测试文件")
    parser.add_argument('directory', nargs='?', help='要清理的目录')
    parser.add_argument('--all', action='store_true', help='清理所有临时测试目录')
    parser.add_argument('-f', '--force', action='store_true', help='不询问确认')
    
    args = parser.parse_args()
    
    if args.all:
        temp_dirs = find_temp_test_dirs()
        if not temp_dirs:
            print("没有找到临时测试目录")
            return
        
        print(f"找到 {len(temp_dirs)} 个临时目录：")
        for d in temp_dirs:
            print(f"  - {d}")
        
        if not args.force:
            confirm = input("确认删除所有？(y/n): ")
            if confirm.lower() != 'y':
                print("取消")
                return
        
        deleted = 0
        for d in temp_dirs:
            try:
                shutil.rmtree(d)
                print(f"已删除：{d}")
                deleted += 1
            except Exception as e:
                print(f"删除失败 {d}：{e}")
        
        print(f"\n完成！删除了 {deleted} 个目录")
        
    elif args.directory:
        cleanup_directory(args.directory)
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
