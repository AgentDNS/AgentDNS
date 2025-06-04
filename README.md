# AgentDNS

AgentDNS是一个用于Agent发现和通信的DNS服务，使Agent能够发现并调用其他Agent。

## 主要功能

1. **智能Agent搜索**：使用RAG技术解析Agent需求（自然语言描述），智能匹配最合适的Agent
2. **地址解析**：解析Agent地址（如`agentdns://alibaba/paperagent`）到具体Agent信息，支持中文地址
3. **组织管理**：解析组织地址（如`agentdns://alibaba`）下的所有Agent
4. **注册服务**：Agent服务商可以注册组织信息和Agent信息

## 系统设计

AgentDNS使用简洁的地址格式：`agentdns://organization/agent_name`，通过API提供查询和注册服务。系统集成了向量数据库(Milvus)和大语言模型，提供智能的语义搜索能力。

### 数据模型

- **Agent**：包含地址、组织、功能描述、接口列表、API URL、token费用等信息
- **Organization**：包含名称、地址、描述等组织信息

### 系统架构

- **核心解析器**：处理地址解析和Agent匹配
- **RAG搜索引擎**：基于Milvus向量数据库的语义搜索
- **数据存储**：MySQL存储结构化数据，Milvus存储向量数据
- **API服务**：提供HTTP接口，支持URL编码的中文地址

## 快速开始

### 1. 环境要求

- Python 3.8+
- MySQL 数据库
- Milvus 向量数据库
- DASHSCOPE API Key (用于嵌入和聊天模型)
- Git（可选，用于克隆代码）

### 2. 获取代码

```bash
# 克隆项目（如果有Git）
git clone <repository_url>
cd agent-dns

# 或直接下载代码包解压
```

### 3. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 配置数据库

```bash
# 1. 登录MySQL
mysql -u root -p

# 2. 创建数据库
CREATE DATABASE agentdns CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 3. 创建用户并授权（根据需要修改用户名和密码）
CREATE USER 'agentdns'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON agentdns.* TO 'agentdns'@'localhost';
FLUSH PRIVILEGES;
```

### 6. 启动Milvus服务

```bash
# 使用Docker启动Milvus (推荐)
curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh
bash standalone_embed.sh start

pip install pymilvus

# 或参考Milvus官方文档进行安装
```

### 7. 配置环境变量

```bash
# 设置数据库连接
export DB_URL='mysql+pymysql://agentdns:your_password@localhost/agentdns'

# 设置DASHSCOPE API Key
export DASHSCOPE_API_KEY='your_dashscope_api_key'
```

### 8. 初始化数据库表

```bash
# 运行数据库初始化脚本
python -m agent_dns.db.init_db --db-url mysql+pymysql://agentdns:your_password@localhost/agentdns
```

### 9. 填充测试数据

```bash
# 向MySQL和Milvus填充测试数据
python -m agent_dns.db.testing_data
```

### 10. 运行服务

```bash
# 使用uvicorn运行（开发环境）
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 生产环境运行（使用多个工作进程）
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

服务启动后，可以通过以下地址访问：
- API文档：http://localhost:8000/docs
- API基础路径：http://localhost:8000/api/v1/

### 11. 运行示例

```bash
# 运行示例代码
python simple_example.py
```

## API示例

### 1. 通过自然语言搜索Agent

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "我需要一个能够处理图像的AI助手", "limit": 3}'
```

### 2. 解析Agent地址（支持中文）

```bash
# 中文地址会自动进行URL编码处理
curl "http://localhost:8000/api/v1/resolve/agent/agentdns://testorg/图像处理器_3"
```

### 3. 列出组织下的所有Agent

```bash
curl "http://localhost:8000/api/v1/list/organization/agentdns://testorg/agents"
```

### 4. 注册组织

```bash
curl -X POST "http://localhost:8000/api/v1/register/organization" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Example Corp",
       "address": "agentdns://example",
       "description": "示例组织"
     }'
```

### 5. 注册Agent

```bash
curl -X POST "http://localhost:8000/api/v1/register/agent" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "TextSummarizer",
       "address": "agentdns://example/text-summarizer",
       "organization": "example",
       "description": "文本摘要生成器",
       "interfaces": [
         {
           "name": "summarize",
           "description": "生成文本摘要",
           "parameters": {
             "text": "需要总结的文本",
             "max_length": "摘要最大长度"
           }
         }
       ],
       "urls": "https://api.example.com/agent/summarizer",
       "token_cost": 0.001,
       "capabilities": ["summarization", "text-processing"]
     }'
```

## 项目结构

```
agent_dns/
├── api/              # API模块
│   ├── router.py     # API路由（含URL解码）
│   └── server.py     # FastAPI服务器
├── core/             # 核心模块
│   └── resolver.py   # Agent解析器（集成RAG搜索）
├── db/               # 数据库模块
│   ├── database.py   # 数据库连接
│   ├── init_db.py    # 数据库初始化
│   ├── models.py     # SQLAlchemy模型
│   ├── milvus.py     # Milvus向量数据库
│   ├── storage.py    # 数据存储
│   └── testing_data.py # 测试数据填充
├── models/           # Pydantic数据模型
│   ├── agent.py      # Agent和组织模型
│   ├── chat_api_interface.py    # 聊天模型接口
│   ├── embedding_api_interface.py # 嵌入模型接口
│   └── prompt.py     # 提示词模板
└── utils/            # 工具类
    ├── validators.py # 地址验证工具
    └── examples.py   # 示例工具
```

## 数据库设计

### MySQL表结构

- **organizations**: 存储组织信息
- **agents**: 存储Agent信息，其中：
  - `urls`: VARCHAR(512) - 存储单个API URL（已从JSON列表改为字符串）
  - `address`: VARCHAR(255) - AgentDNS地址，支持中文
  - `capabilities`: JSON - 能力标签列表
  - `interfaces`: JSON - 接口定义列表

### Milvus集合结构

- **agent**: 存储Agent的向量化数据，包含：
  - `agent_name`: 名称
  - `address`: AgentDNS地址
  - `description`: 描述
  - `tags`: 标签
  - `description_vector`: 描述的向量嵌入
  - `tags_vector`: 标签的向量嵌入

## 配置说明

### 环境变量

- `DB_URL`: MySQL数据库连接URL
- `DASHSCOPE_API_KEY`: 通义千问API密钥
- `PORT`: 服务端口，默认8000
- `HOST`: 服务监听地址，默认0.0.0.0

### Milvus配置

默认连接配置：
- URI: http://localhost:19530
- Token: root:Milvus
- 集合名: agent

## 特性说明

### 1. RAG智能搜索

系统使用检索增强生成(RAG)技术：
- 使用通义千问嵌入模型将Agent描述和标签向量化
- 支持BM25全文搜索和向量语义搜索
- 使用RRF(Reciprocal Rank Fusion)混合排序算法
- 支持自然语言查询意图理解

### 2. 中文地址支持

- 支持中文Agent名称和地址
- 自动处理URL编码/解码
- 示例：`agentdns://testorg/图像处理器_3`

### 3. 数据一致性

- MySQL存储结构化数据
- Milvus存储向量数据
- 通过地址字段保持数据同步
- 测试数据填充脚本包含重复检查机制

## 生产环境部署建议

1. **使用进程管理器**
   ```bash
   # 使用 supervisor 管理进程
   [program:agentdns]
   command=/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   directory=/path/to/agent-dns
   user=agentdns
   autostart=true
   autorestart=true
   environment=DB_URL="mysql+pymysql://username:password@localhost/agentdns",DASHSCOPE_API_KEY="your_key"
   ```

2. **使用 Nginx 反向代理**
   ```nginx
   server {
       listen 80;
       server_name your_domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

3. **Docker部署**
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   COPY . .
   
   ENV DB_URL=mysql+pymysql://username:password@mysql:3306/agentdns
   ENV DASHSCOPE_API_KEY=your_key
   
   EXPOSE 8000
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

## 常见问题

### Q: 搜索功能返回空结果？
A: 确保已正确配置DASHSCOPE_API_KEY，并且Milvus服务正在运行。可以运行测试数据填充脚本来添加示例数据。

### Q: 中文地址解析失败？
A: 确保客户端正确进行URL编码，服务端会自动处理解码。

### Q: 数据不一致问题？
A: 运行测试数据填充脚本时会自动检查重复，避免数据不一致。

## 贡献

欢迎提交Pull Request或Issue来改进项目。 