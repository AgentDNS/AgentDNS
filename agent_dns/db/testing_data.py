"""
测试数据生成文件，包含20条随机生成的智能体数据
"""

test_data = [
    {
        "agent_name": "文档助手",
        "address": "http://doc-assistant.ai:8080/api/v1",
        "description": "专业的文档处理助手，可以帮助用户进行文档总结、翻译和格式转换",
        "tags": "文档处理 翻译 总结 格式转换"
    },
    {
        "agent_name": "代码专家",
        "address": "http://code-expert.ai:8081/api/v1",
        "description": "专业的代码审查和优化助手，支持多种编程语言，提供代码重构建议",
        "tags": "代码审查 重构 编程 优化"
    },
    {
        "agent_name": "数据分析师",
        "address": "http://data-analyst.ai:8082/api/v1",
        "description": "专业的数据分析助手，提供数据可视化、统计分析和预测建模服务",
        "tags": "数据分析 可视化 统计 预测"
    },
    {
        "agent_name": "图像处理器",
        "address": "http://image-processor.ai:8083/api/v1",
        "description": "专业的图像处理助手，支持图像编辑、风格转换和图像生成",
        "tags": "图像处理 编辑 风格转换 AI绘画"
    },
    {
        "agent_name": "语音助手",
        "address": "http://voice-assistant.ai:8084/api/v1",
        "description": "专业的语音处理助手，提供语音识别、转写和语音合成服务",
        "tags": "语音识别 语音合成 转写 ASR"
    },
    {
        "agent_name": "翻译专家",
        "address": "http://translation-expert.ai:8085/api/v1",
        "description": "多语言翻译助手，支持100多种语言的实时翻译和本地化服务",
        "tags": "翻译 多语言 本地化 实时"
    },
    {
        "agent_name": "知识库管理",
        "address": "http://knowledge-base.ai:8086/api/v1",
        "description": "智能知识库管理助手，帮助构建和维护企业知识库系统",
        "tags": "知识库 管理 企业 维护"
    },
    {
        "agent_name": "市场分析师",
        "address": "http://market-analyst.ai:8087/api/v1",
        "description": "市场趋势分析助手，提供市场调研、竞品分析和趋势预测",
        "tags": "市场分析 调研 竞品 预测"
    },
    {
        "agent_name": "法律顾问",
        "address": "http://legal-advisor.ai:8088/api/v1",
        "description": "AI法律顾问，提供法律咨询、合同审查和法规解读服务",
        "tags": "法律 咨询 合同 法规"
    },
    {
        "agent_name": "客服机器人",
        "address": "http://customer-service.ai:8089/api/v1",
        "description": "7x24小时智能客服，提供自动问答和工单处理服务",
        "tags": "客服 问答 工单 自动化"
    },
    {
        "agent_name": "医疗顾问",
        "address": "http://medical-advisor.ai:8090/api/v1",
        "description": "AI医疗咨询助手，提供初步诊断建议和健康管理指导",
        "tags": "医疗 诊断 健康 咨询"
    },
    {
        "agent_name": "教育助手",
        "address": "http://education-assistant.ai:8091/api/v1",
        "description": "个性化学习助手，提供课程推荐和学习进度跟踪",
        "tags": "教育 学习 课程 个性化"
    },
    {
        "agent_name": "金融分析师",
        "address": "http://financial-analyst.ai:8092/api/v1",
        "description": "金融市场分析助手，提供投资建议和风险评估",
        "tags": "金融 投资 风险 分析"
    },
    {
        "agent_name": "音乐创作",
        "address": "http://music-creator.ai:8093/api/v1",
        "description": "AI音乐创作助手，可以生成原创音乐和编曲",
        "tags": "音乐 创作 编曲 生成"
    },
    {
        "agent_name": "游戏设计师",
        "address": "http://game-designer.ai:8094/api/v1",
        "description": "游戏关卡设计助手，提供游戏机制设计和平衡性建议",
        "tags": "游戏 设计 关卡 平衡"
    },
    {
        "agent_name": "安全专家",
        "address": "http://security-expert.ai:8095/api/v1",
        "description": "网络安全分析助手，提供安全评估和漏洞检测服务",
        "tags": "安全 评估 漏洞 检测"
    },
    {
        "agent_name": "运维助手",
        "address": "http://devops-assistant.ai:8096/api/v1",
        "description": "系统运维助手，提供服务器监控和故障诊断服务",
        "tags": "运维 监控 故障 诊断"
    },
    {
        "agent_name": "HR助手",
        "address": "http://hr-assistant.ai:8097/api/v1",
        "description": "人力资源管理助手，协助简历筛选和员工管理",
        "tags": "人事 招聘 管理 筛选"
    },
    {
        "agent_name": "视频编辑",
        "address": "http://video-editor.ai:8098/api/v1",
        "description": "AI视频编辑助手，提供视频剪辑、特效制作和字幕生成",
        "tags": "视频 编辑 特效 字幕"
    },
    {
        "agent_name": "研究助手",
        "address": "http://research-assistant.ai:8099/api/v1",
        "description": "学术研究助手，协助文献检索和实验数据分析",
        "tags": "研究 文献 实验 分析"
    }
] 

# Added import statements
import os
import sys
from typing import List, Dict, Any

# Adjust path to import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .storage import Storage
from ..models.agent import Agent, Organization, AgentInterface

# AGENT_DATA alias for consistency if used elsewhere, otherwise test_data is fine.
AGENT_DATA: List[Dict[str, Any]] = test_data

def populate_mysql_from_test_data():
    """
    Populates the MySQL database with agent and organization data
    derived from the test_data list.
    """
    print("Initializing Storage for MySQL...")
    # Assuming DB_URL is set in environment or storage handles default
    storage = Storage(db_url=os.getenv("DB_URL")) 
    print("Storage initialized.")

    default_org_name = "testorg"
    default_org_address = f"agentdns://{default_org_name}"
    default_org_description = "Default Test Organization generated from testing_data.py"

    # Check if default organization exists, if not, create it
    existing_org = storage.get_organization(address=default_org_address)
    if not existing_org:
        print(f"Organization '{default_org_name}' not found, creating...")
        org_to_add = Organization(
            name=default_org_name,
            address=default_org_address,
            description=default_org_description
        )
        storage.add_organization(org_to_add)
        print(f"Organization '{default_org_name}' created.")
    else:
        print(f"Organization '{default_org_name}' already exists.")

    print(f"Populating agents for organization '{default_org_name}'...")
    added_count = 0
    skipped_count = 0
    
    for i, item in enumerate(AGENT_DATA):
        agent_name_slug = item['agent_name'].lower().replace(' ', '_').replace('-', '_')
        agent_dns_address = f"agentdns://{default_org_name}/{agent_name_slug}_{i}" # Ensure uniqueness with index

        print(f"Processing agent: {item['agent_name']} with address {agent_dns_address}")

        # Check if agent already exists by its AgentDNS address
        existing_agent = storage.get_agent_by_address(address=agent_dns_address)
        if existing_agent:
            print(f"Agent with address {agent_dns_address} already exists. Skipping.")
            skipped_count += 1
            continue

        agent_to_add = Agent(
            name=item['agent_name'],
            address=agent_dns_address,
            organization=default_org_name, # Organization name
            description=item['description'],
            interfaces=[],  # Default: empty list
            urls=item['address'],  # 直接存储为字符串，不是列表
            token_cost=0.0,  # Default
            capabilities=item['tags'].split(' ') if item['tags'] else []
        )
        
        try:
            storage.add_agent(agent_to_add)
            print(f"Successfully added agent: {agent_to_add.name}")
            added_count += 1
        except Exception as e:
            print(f"Error adding agent {agent_to_add.name}: {e}")
            # Potentially log more details or re-raise if critical

    print(f"Finished populating MySQL from test_data.")
    print(f"Added: {added_count} agents, Skipped: {skipped_count} agents (already existed)")

if __name__ == "__main__":
    # This allows running the script directly to populate the DB
    print("Starting MySQL data population script...")
    # Ensure SQLAlchemy warning from models.py doesn't clutter too much if it appears here
    populate_mysql_from_test_data()
    print("MySQL data population script finished.")

# Ensure the original test_data list is still easily accessible if needed by other parts (like milvus.py)
# For example, if milvus.py directly imports test_data from this file.
# The AGENT_DATA alias helps if other modules specifically look for that name.
# If milvus.py or other files import `test_data`, it's still available. 