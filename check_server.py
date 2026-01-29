#!/usr/bin/env python3
"""检查服务器启动"""
import asyncio
import sys
import os

async def check_server():
    """检查服务器启动"""
    
    # 启动服务器进程
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "server.py", "--transport", "stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd="/app/auto-mcp-upload/data/2218",
        env={**os.environ, "PYTHONUNBUFFERED": "1"}
    )
    
    # 等待服务器启动
    await asyncio.sleep(2)
    
    # 检查进程状态
    print(f"进程 ID: {proc.pid}")
    print(f"返回码: {proc.returncode}")
    
    # 读取 stderr
    stderr_data = await proc.stderr.read()
    print(f"Stderr: {stderr_data.decode()}")
    
    # 读取 stdout
    stdout_data = await proc.stdout.read()
    print(f"Stdout: {stdout_data.decode()}")
    
    # 清理
    proc.terminate()
    await proc.wait()

if __name__ == "__main__":
    asyncio.run(check_server())