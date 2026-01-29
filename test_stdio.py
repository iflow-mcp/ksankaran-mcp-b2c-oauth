#!/usr/bin/env python3
"""测试 MCP 服务器的 stdio 协议"""
import asyncio
import json
import sys
import os
import subprocess

async def test_server():
    """测试 MCP 服务器"""
    
    # 启动服务器进程
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "server.py", "--transport", "stdio",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/app/auto-mcp-upload/data/2218"
    )
    
    # 等待服务器启动
    await asyncio.sleep(2)
    
    # 检查进程是否成功启动
    if proc.returncode is not None:
        stderr = await proc.stderr.read()
        print(f"服务器启动失败: {stderr.decode()}")
        return False
    
    print("✅ 服务器启动成功")
    
    # 发送初始化请求
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    
    proc.stdin.write(json.dumps(init_request).encode() + b'\n')
    await proc.stdin.drain()
    
    # 读取响应
    response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=30)
    response = json.loads(response_line.decode())
    
    print(f"初始化响应: {response}")
    
    if "error" in response:
        print(f"❌ 初始化失败: {response['error']}")
        return False
    
    print("✅ 初始化成功")
    
    # 发送 list_tools 请求
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    proc.stdin.write(json.dumps(list_tools_request).encode() + b'\n')
    await proc.stdin.drain()
    
    # 读取响应
    response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=30)
    response = json.loads(response_line.decode())
    
    print(f"工具列表响应: {response}")
    
    if "error" in response:
        print(f"❌ 获取工具列表失败: {response['error']}")
        return False
    
    if "result" in response and "tools" in response["result"]:
        tools = response["result"]["tools"]
        print(f"🛠️  成功获取到 {len(tools)} 个工具:")
        for i, tool in enumerate(tools, 1):
            name = tool.get("name", "未知工具")
            description = tool.get("description", "无描述")
            print(f"   {i}. {name}")
            print(f"      描述: {description}")
            if "inputSchema" in tool and "properties" in tool["inputSchema"]:
                params = list(tool["inputSchema"]["properties"].keys())
                print(f"      参数: {params}")
        
        print("✅ 测试成功！")
        return True
    else:
        print("❌ 响应格式不正确")
        return False
    
    # 清理
    proc.terminate()
    await proc.wait()

if __name__ == "__main__":
    success = asyncio.run(test_server())
    sys.exit(0 if success else 1)
