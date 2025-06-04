import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from agent_dns.models.agent import Agent, Organization
from agent_dns.db.database import Database
from agent_dns.db.models import AgentModel, OrganizationModel


class Storage:
    """数据存储接口"""
    
    def __init__(self, db_url: str = None):
        """初始化存储系统
        
        Args:
            db_url: 数据库连接URL，默认从环境变量读取
        """
        # 初始化数据库连接
        self.db = Database(db_url)
        
        # 确保数据库表存在
        self.db.create_tables()
    
    def add_organization(self, organization: Organization) -> None:
        """添加或更新组织"""
        with self.db.session_scope() as session:
            # 检查是否已存在
            org = session.query(OrganizationModel).filter_by(address=organization.address).first()
            
            if org:
                # 更新现有组织
                org.name = organization.name
                org.description = organization.description
            else:
                # 创建新组织
                org = OrganizationModel(
                    address=organization.address,
                    name=organization.name,
                    description=organization.description
                )
                session.add(org)
    
    def get_organization(self, address: str) -> Optional[Organization]:
        """根据地址获取组织"""
        with self.db.session_scope() as session:
            org = session.query(OrganizationModel).filter_by(address=address).first()
            if org:
                return Organization(**org.to_dict())
            return None
    
    def list_organizations(self) -> List[Organization]:
        """列出所有组织"""
        with self.db.session_scope() as session:
            orgs = session.query(OrganizationModel).all()
            return [Organization(**org.to_dict()) for org in orgs]
    
    def add_agent(self, agent: Agent) -> None:
        """添加或更新Agent"""
        agent_dict = agent.model_dump(mode='json')
        
        with self.db.session_scope() as session:
            # 检查是否已存在
            agent_model = session.query(AgentModel).filter_by(address=agent.address).first()
            
            if agent_model:
                # 更新现有Agent
                agent_model.name = agent.name
                agent_model.description = agent.description
                agent_model.organization_address = f"agentdns://{agent.organization}" if not agent.organization.startswith("agentdns://") else agent.organization
                agent_model.token_cost = agent.token_cost
                agent_model.interfaces = [interface.model_dump(mode='json') for interface in agent.interfaces]
                agent_model.urls = agent.urls  # 直接赋值字符串
                agent_model.capabilities = agent.capabilities
            else:
                # 创建新Agent
                agent_model = AgentModel(
                    address=agent.address,
                    name=agent.name,
                    description=agent.description,
                    organization_address=f"agentdns://{agent.organization}" if not agent.organization.startswith("agentdns://") else agent.organization,
                    token_cost=agent.token_cost,
                    interfaces=[interface.model_dump(mode='json') for interface in agent.interfaces],
                    urls=agent.urls,  # 直接赋值字符串
                    capabilities=agent.capabilities
                )
                session.add(agent_model)
    
    def get_agent_by_address(self, address: str) -> Optional[Agent]:
        """根据地址获取Agent"""
        with self.db.session_scope() as session:
            agent_model = session.query(AgentModel).filter_by(address=address).first()
            
            if agent_model:
                agent_dict = agent_model.to_dict()
                return Agent(**agent_dict)
            return None
        
    def get_agent_by_url(self, url: str) -> Optional[Agent]:
        """根据URL获取Agent"""
        with self.db.session_scope() as session:
            agent_model = session.query(AgentModel).filter_by(urls=url).first()
            
            if agent_model:
                agent_dict = agent_model.to_dict()
                return Agent(**agent_dict)
            return None
    
    def list_agents(self, organization: Optional[str] = None) -> List[Agent]:
        """列出所有Agent或指定组织的Agent"""
        with self.db.session_scope() as session:
            query = session.query(AgentModel)
            
            if organization:
                # 如果没有指定agentdns://前缀，添加前缀
                if not organization.startswith("agentdns://"):
                    organization = f"agentdns://{organization}"
                query = query.filter_by(organization_address=organization)
            
            agents = query.all()
            return [Agent(**agent.to_dict()) for agent in agents]
        
    def search_agents_by_capabilities(self, capabilities: List[str]) -> List[Agent]:
        """根据能力标签搜索Agent"""
        with self.db.session_scope() as session:
            # MySQL不支持直接查询JSON数组包含关系
            # 这里获取所有Agent然后在Python中过滤
            all_agents = session.query(AgentModel).all()
            result = []
            
            for agent_model in all_agents:
                agent_capabilities = set(agent_model.capabilities)
                if any(cap in agent_capabilities for cap in capabilities):
                    result.append(Agent(**agent_model.to_dict()))
            
            return result
    
    def delete_agent(self, address: str) -> bool:
        """删除Agent"""
        with self.db.session_scope() as session:
            agent = session.query(AgentModel).filter_by(address=address).first()
            if agent:
                session.delete(agent)
                return True
            return False
    
    def get_agent_by_id(self, agent_id: int) -> Optional[Agent]:
        """根据 ID 获取 Agent"""
        with self.db.session_scope() as session:
            agent_model = session.query(AgentModel).filter_by(id=agent_id).first()
            
            if agent_model:
                agent_dict = agent_model.to_dict()
                # AgentModel.to_dict() 返回的 "organization" 是地址，需要转换为 Pydantic Agent 模型期望的 organization 名称
                # Agent Pydantic model expects organization name, not full address
                parsed_org_address = agent_dict["organization"]
                if isinstance(parsed_org_address, str) and "://" in parsed_org_address:
                    agent_dict["organization"] = parsed_org_address.split("://", 1)[1]

                # 确保 interfaces, urls, capabilities 是列表
                # Pydantic Agent model fields:
                # interfaces: List[Interface]
                # urls: List[HttpUrl]
                # capabilities: List[str]
                # AgentModel.to_dict() should already provide them in correct basic types (list of dicts, list of str)
                # but ensure they are not None if model expects non-Optional list
                
                # The Agent Pydantic model will handle parsing of interfaces into Interface objects
                # and urls into HttpUrl objects.
                return Agent(**agent_dict)
            return None
    
    def delete_organization(self, address: str) -> bool:
        """删除组织"""
        with self.db.session_scope() as session:
            org = session.query(OrganizationModel).filter_by(address=address).first()
            if org:
                session.delete(org)
                return True
            return False 