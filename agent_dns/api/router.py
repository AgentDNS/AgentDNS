from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
import urllib.parse

from agent_dns.models.agent import Agent, Organization, AgentQuery
from agent_dns.core.resolver import AgentResolver
from agent_dns.db.storage import Storage


class AgentDNSRouter:
    """API路由器"""
    
    def __init__(self, storage: Storage, resolver: AgentResolver):
        self.storage = storage
        self.resolver = resolver
        self.router = APIRouter()
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册API路由"""
        # 查询API
        self.router.add_api_route(
            "/search",
            self.search_agents,
            methods=["POST"],
            response_model=List[Agent],
            summary="通过自然语言搜索Agent",
            description="根据自然语言描述搜索合适的Agent"
        )
        
        # 解析API
        self.router.add_api_route(
            "/resolve/agent/{address:path}",
            self.resolve_agent,
            methods=["GET"],
            response_model=Agent,
            summary="解析Agent地址",
            description="根据Agent地址解析Agent详细信息"
        )
        
        self.router.add_api_route(
            "/resolve/organization/{address:path}",
            self.resolve_organization,
            methods=["GET"],
            response_model=Organization,
            summary="解析组织地址",
            description="根据组织地址解析组织详细信息"
        )
        
        self.router.add_api_route(
            "/list/organization/{address:path}/agents",
            self.list_organization_agents,
            methods=["GET"],
            response_model=List[Agent],
            summary="列出组织下的所有Agent",
            description="获取某个组织下注册的所有Agent"
        )
        
        # 注册API
        self.router.add_api_route(
            "/register/organization",
            self.register_organization,
            methods=["POST"],
            response_model=Organization,
            summary="注册组织",
            description="向AgentDNS注册新组织"
        )
        
        self.router.add_api_route(
            "/register/agent",
            self.register_agent,
            methods=["POST"],
            response_model=Agent,
            summary="注册Agent",
            description="向AgentDNS注册新Agent"
        )
    
    async def search_agents(self, query: AgentQuery) -> List[Agent]:
        """搜索Agent"""
        return self.resolver.search_agents(query.query, query.limit)
    
    async def resolve_agent(self, address: str) -> Agent:
        """解析Agent地址"""
        # URL解码处理汉字
        address = urllib.parse.unquote(address)
        
        # 确保地址格式规范
        if not address.startswith("agentdns://"):
            address = f"agentdns://{address}"
            
        agent = self.resolver.resolve_agent(address)
        if not agent:
            raise HTTPException(status_code=404, detail=f"未找到Agent: {address}")
        return agent
    
    async def resolve_organization(self, address: str) -> Organization:
        """解析组织地址"""
        # URL解码处理汉字
        address = urllib.parse.unquote(address)
        
        # 确保地址格式规范
        if not address.startswith("agentdns://"):
            address = f"agentdns://{address}"
            
        organization = self.resolver.resolve_organization(address)
        if not organization:
            raise HTTPException(status_code=404, detail=f"未找到组织: {address}")
        return organization
    
    async def list_organization_agents(self, address: str) -> List[Agent]:
        """列出组织下的所有Agent"""
        # URL解码处理汉字
        address = urllib.parse.unquote(address)
        
        # 确保地址格式规范
        if not address.startswith("agentdns://"):
            address = f"agentdns://{address}"
            
        return self.resolver.list_organization_agents(address)
    
    async def register_organization(self, org: Organization) -> Organization:
        """注册组织"""
        # 确保地址格式规范
        if not org.address.startswith("agentdns://"):
            org.address = f"agentdns://{org.address}"
            
        self.storage.add_organization(org)
        return org
    
    async def register_agent(self, agent: Agent) -> Agent:
        """注册Agent"""
        # 确保地址格式规范
        if not agent.address.startswith("agentdns://"):
            agent.address = f"agentdns://{agent.address}"
            
        # 检查组织是否存在
        org_address = f"agentdns://{agent.organization}"
        organization = self.resolver.resolve_organization(org_address)
        
        if not organization:
            raise HTTPException(
                status_code=404, 
                detail=f"无法注册Agent: 组织 '{agent.organization}' 不存在"
            )
            
        self.storage.add_agent(agent)
        return agent 