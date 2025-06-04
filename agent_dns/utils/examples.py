"""示例数据生成工具"""
from typing import List
from pydantic import HttpUrl

from agent_dns.models.agent import Agent, AgentInterface, Organization
from agent_dns.db.storage import Storage


def create_example_organization() -> List[Organization]:
    """创建示例组织数据"""
    return [
        Organization(
            name="阿里巴巴",
            address="agentdns://alibaba",
            description="阿里巴巴集团",
            website="https://www.alibaba.com"
        ),
        Organization(
            name="腾讯",
            address="agentdns://tencent",
            description="腾讯科技有限公司",
            website="https://www.tencent.com"
        ),
        Organization(
            name="百度",
            address="agentdns://baidu",
            description="百度公司",
            website="https://www.baidu.com"
        )
    ]


def create_example_agents() -> List[Agent]:
    """创建示例Agent数据"""
    return [
        Agent(
            name="论文Agent",
            address="agentdns://alibaba/paperagent",
            organization="alibaba",
            description="一个帮助用户总结和分析学术论文的Agent",
            interfaces=[
                AgentInterface(
                    name="summarize",
                    description="总结论文内容",
                    parameters={"paper_url": "论文URL", "max_length": "最大摘要长度"}
                ),
                AgentInterface(
                    name="analyze",
                    description="分析论文贡献和方法",
                    parameters={"paper_url": "论文URL"}
                )
            ],
            urls=["https://api.alibaba.com/agents/paper"],
            token_cost=0.002,
            capabilities=["summarization", "paper-analysis", "academic"]
        ),
        Agent(
            name="代码助手",
            address="agentdns://alibaba/codeassistant",
            organization="alibaba",
            description="一个帮助用户编写、优化和调试代码的Agent",
            interfaces=[
                AgentInterface(
                    name="generate",
                    description="生成代码",
                    parameters={"language": "编程语言", "description": "功能描述"}
                ),
                AgentInterface(
                    name="review",
                    description="代码审查",
                    parameters={"code": "代码内容", "language": "编程语言"}
                )
            ],
            urls=["https://api.alibaba.com/agents/code"],
            token_cost=0.005,
            capabilities=["code-generation", "code-review", "debugging"]
        ),
        Agent(
            name="翻译助手",
            address="agentdns://tencent/translator",
            organization="tencent",
            description="一个多语言翻译Agent，支持100多种语言之间的互译",
            interfaces=[
                AgentInterface(
                    name="translate",
                    description="翻译文本",
                    parameters={"text": "源文本", "source_lang": "源语言", "target_lang": "目标语言"}
                )
            ],
            urls=["https://api.tencent.com/agents/translate"],
            token_cost=0.001,
            capabilities=["translation", "multilingual"]
        ),
        Agent(
            name="搜索助手",
            address="agentdns://baidu/searchassistant",
            organization="baidu",
            description="一个高级网络搜索Agent，能够从互联网获取最新信息",
            interfaces=[
                AgentInterface(
                    name="search",
                    description="搜索信息",
                    parameters={"query": "搜索查询", "limit": "结果数量"}
                )
            ],
            urls=["https://api.baidu.com/agents/search"],
            token_cost=0.002,
            capabilities=["web-search", "information-retrieval"]
        )
    ]


def load_example_data(storage: Storage) -> None:
    """加载示例数据到存储"""
    # 添加组织
    for org in create_example_organization():
        storage.add_organization(org)
    
    # 添加Agent
    for agent in create_example_agents():
        storage.add_agent(agent)
    
    print(f"已加载 {len(create_example_organization())} 个示例组织和 {len(create_example_agents())} 个示例Agent")


if __name__ == "__main__":
    # 直接运行此脚本将加载示例数据
    storage = Storage()
    load_example_data(storage) 