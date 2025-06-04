#!/usr/bin/env python
"""
AgentDNS - Agent发现与通信DNS服务
"""
import os
from fastapi import FastAPI
from agent_dns.api import AgentDNSServer
from agent_dns.db.milvus import AgentDNSDB

# 创建FastAPI应用
app = FastAPI(
    title="AgentDNS",
    description="Agent发现与通信DNS服务",
    version="1.0.0"
)

# 获取数据库URL
db_url = os.getenv("DB_URL")

# 初始化 MilvusDB 客户端 (可以从环境变量等配置)
# TODO: Add proper configuration for Milvus URI and Token, e.g., from environment variables
milvus_client = AgentDNSDB()

# 创建并初始化服务器
server = AgentDNSServer(db_url=db_url, milvus_db=milvus_client)

# 注册路由
app.include_router(server.router, prefix="/api/v1")

# 添加健康检查端点
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # 仅在直接运行时使用，生产环境应该使用命令行运行uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True  # 开发模式下启用热重载
    ) 