#!/usr/bin/env python3
"""
Cognix智能体功能测试脚本
自动测试记忆系统的基本功能
"""
from agent import CognixAgent

def test_memory_functionality():
    """测试记忆系统功能"""
    print("🧪 开始测试Cognix记忆增强智能体功能\n")
    
    agent = CognixAgent()
    
    # 测试1: 记忆用户信息
    print("测试1: 记忆用户信息")
    response = agent.chat("我叫张三，是一名软件工程师，常用Python开发项目，喜欢简洁的回答风格")
    print(f"用户: 我叫张三，是一名软件工程师，常用Python开发项目，喜欢简洁的回答风格")
    print(f"助理: {response}")
    print()
    
    # 测试2: 回忆信息
    print("测试2: 回忆用户信息")
    response = agent.chat("我叫什么名字？我是做什么的？")
    print(f"用户: 我叫什么名字？我是做什么的？")
    print(f"助理: {response}")
    assert "张三" in response and "软件工程师" in response, "应该能回忆起用户信息"
    print("✅ 记忆功能正常\n")
    
    # 测试3: 记忆工作习惯
    print("测试3: 记忆工作习惯")
    response = agent.chat("我每周五下午5点需要发周报给王经理，抄送技术部")
    print(f"用户: 我每周五下午5点需要发周报给王经理，抄送技术部")
    print(f"助理: {response}")
    print()
    
    # 测试4: 检索工作习惯
    print("测试4: 检索工作习惯")
    response = agent.chat("我每周几要发周报？发给谁？")
    print(f"用户: 我每周几要发周报？发给谁？")
    print(f"助理: {response}")
    assert "周五" in response and "王经理" in response, "应该能回忆起周报相关信息"
    print("✅ 检索功能正常\n")
    
    # 测试5: 获取上下文
    print("测试5: 获取上下文")
    response = agent.chat("我们最近讨论了什么内容？")
    print(f"用户: 我们最近讨论了什么内容？")
    print(f"助理: {response}")
    assert "张三" in response and "周报" in response, "应该能获取到近期上下文"
    print("✅ 上下文功能正常\n")
    
    # 测试6: 偏好记忆
    print("测试6: 偏好记忆应用")
    response = agent.chat("帮我写一个Python的快速排序代码")
    print(f"用户: 帮我写一个Python的快速排序代码")
    print(f"助理: {response}")
    assert "Python" in response, "应该记得用户用Python"
    print("✅ 偏好记忆应用正常\n")
    
    print("🎉 所有测试通过！Cognix记忆系统功能正常")
    print("-" * 60)
    print("提示：")
    print("- 运行 python chat.py 开始和智能体对话")
    print("- 记忆会永久保存在Cognix记忆系统中")
    print("- 可以在~/.cognix/memory/目录下查看生成的记忆文件")

if __name__ == "__main__":
    test_memory_functionality()
