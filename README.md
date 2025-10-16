<!-- markdownlint-disable MD001 MD041 -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/AgentDNS/AgentDNS/raw/main/images/logo-dark.png" width="300">
    <img alt="AgentDNS" src="https://github.com/AgentDNS/AgentDNS/raw/main/images/logo-light.png" width="300">
  </picture>
</p>

<h3 align="center">
A DNS-Inspired Service Discovery Layer for LLM Agents
</h3>

---
**Important Notice: Upcoming Breaking Changes (Q4 2025)**

We are working on a major update to this project, which is scheduled for release between **October and December 2025**. This new version will contain **breaking changes**. **We strongly advise against using this upcoming release in production** until a stable version is available and you have verified compatibility.

---

*Latest News* 🔥

- **[2025/10] We are open-sourcing the AgentDNS system!** The backend, frontend, SDK, and multi-protocol adapters will be released progressively.
- **[2025/06] Our AgentDNS paper was released!** We introduced AgentDNS, a system for LLM Agent service discovery, dedicated to building infrastructure for general-purpose AI agents. Check it out on [arXiv](https://arxiv.org/html/2505.22368v1).


![AgentDNS Logo](https://img.shields.io/badge/AgentDNS-v0.1.0-blue.svg)

## Overview

**AgentDNS** is a root-domain naming and service discovery system designed for LLM Agents. It provides a complete solution for service registration, discovery, proxying, and management to help AI Agents find and consume services easily.

### Key Features

- **Semantic Discovery** - Vector-based semantic search for services
- **Secure Proxy** - Built-in auth and API key management
- **Usage Analytics** - Detailed usage and billing
- **Multi-Protocol** - HTTPS, MCP, A2A, etc.
- **Monitoring & Alerts** - Real-time service status

### Architecture


<p align="center">
  <img src="https://github.com/AgentDNS/AgentDNS/raw/main/images/arch.png" alt="AgentDNS Architecture" width="70%">
</p>


## Getting Started

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


### 5. Run agentdns-backend

```bash 
cd agentdns-backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```


### 6. Create Admin Account

After the first start, create the admin test account:

```bash
cd agentdns-backend
python scripts/create_admin_user.py

# Default credentials
# Username: admin
# Password: agentdns_666
# Change the password in production
```

### 7. Verify Deployment

Check service status with these URLs:

```bash
# Health check
curl http://localhost:8000/health

# Root path
curl http://localhost:8000/
```

Expected response:
```json
{
  "message": "Welcome to the AgentDNS API",
  "version": "0.1.0",
  "docs": "/docs"
}
```

## 🛠️ Developer Guide


### 📁 Project Structure

```
agentdns-backend/
├── app/                    # application
│   ├── api/               # API routes
│   │   ├── client/        # client APIs
│   │   ├── auth.py        # auth
│   │   ├── services.py    # services
│   │   └── ...
│   ├── core/              # core config
│   │   ├── config.py      # configuration
│   │   ├── security.py    # security
│   │   └── ...
│   ├── models/            # ORM models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # business logic
│   ├── database.py        # DB connection
│   └── main.py           # app entrypoint
├── scripts/               # helper scripts
├── requirements.txt       # dependencies
├── .env.example          # env template
└── README.md             # docs
```


### Main API endpoints

| Endpoint | Method | Description |
|------|------|------|
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/auth/token` | POST | User login |
| `/api/v1/services/` | GET | List services |
| `/api/v1/services/` | POST | Create service |
| `/api/v1/discovery/search` | POST | Service discovery |
| `/api/v1/proxy/{path}` | ANY | Service proxy |

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add some AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under Apache License.


**AgentDNS** - Make service discovery simple and efficient for AI Agents 🚀