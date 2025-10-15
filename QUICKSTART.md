# AgentDNS Quick Start Guide

## Quick Install

### Prerequisites

- Linux OS
- Python 3.10+
- Docker and Docker Compose (for Milvus, PostgreSQL, Redis)

### 1. Clone repository

```bash
git clone https://github.com/AgentDNS/AgentDNS.git
cd AgentDNS
```

### 2. Start database

```bash
docker-compose up postgres redis milvus -d
```

### 3. Generate ENCRYPTION_KEY

```bash
cd agentdns-backend
python generate_encryption_key.py
```

### 4. Config .env

#### 1) ENCRYPTION_KEY configuration

```bash 
ENCRYPTION_KEY=your-secret-key-here
```

#### 2) OpenAI API Configuration

```bash
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
OPENAI_EMBEDDING_MODEL=doubao-embedding-text-240715
OPENAI_MAX_TOKENS=4096
```

### 4. Run agentdns-backend

```bash 
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Get help

- Read more: [README.md](README.md)
- Issues: GitHub Issues
- Email: enfangcui@gmail.com

---

**Quick start complete!** 🎉 You can now use AgentDNS!