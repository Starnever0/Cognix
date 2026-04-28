#!/usr/bin/env python3
"""
Cognix记忆增强智能体命令行交互入口
"""
import os
import argparse
from dotenv import load_dotenv
from agent import CognixAgent

def main():
    # 加载环境变量
    load_dotenv()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Cognix记忆增强智能体')
    parser.add_argument('--provider', type=str, choices=['openai', 'anthropic'], 
                        help='LLM供应商，覆盖环境变量配置')
    parser.add_argument('--model', type=str, help='模型名称，覆盖环境变量配置')
    parser.add_argument('--base-url', type=str, help='API地址，覆盖环境变量配置')
    args = parser.parse_args()
    
    # 初始化智能体
    agent = CognixAgent(
        provider=args.provider,
        model=args.model,
        base_url=args.base_url
    )
    
    print("=" * 60)
    print(f"🤖 Cognix 记忆增强智能体 (供应商: {agent.provider}, 模型: {agent.model})")
    print("=" * 60)
    print("提示：")
    print("- 输入 'clear' 清除对话历史")
    print("- 输入 'exit' 或 'quit' 退出程序")
    print("- 智能体会自动记住你的信息和偏好")
    print("=" * 60)
    print()
    
    while True:
        try:
            user_input = input("你: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["exit", "quit"]:
                print("👋 再见！")
                break
                
            if user_input.lower() == "clear":
                agent.clear_history()
                print("🧹 对话历史已清除")
                print()
                continue
            
            print("思考中...", end="\r")
            response = agent.chat(user_input)
            print(" " * 20, end="\r")
            print(f"助理: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 出错了: {str(e)}")
            print()

if __name__ == "__main__":
    main()
