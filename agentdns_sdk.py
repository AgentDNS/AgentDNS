from typing import List, Dict, Any, Optional
import requests

class AgentDNSClient:
    """AgentDNS API客户端SDK"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化客户端
        
        Args:
            base_url: AgentDNS服务器地址
        """
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
    
    def register_organization(self, 
        name: str,
        address: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """注册组织
        
        Args:
            name: 组织名称
            address: 组织地址（例如：agentdns://example）
            description: 组织描述
            
        Returns:
            注册成功的组织信息
        """
        org_data = {
            "name": name,
            "address": address,
            "description": description,
        }
            
        response = requests.post(f"{self.api_base}/register/organization", json=org_data)
        response.raise_for_status()
        return response.json()
    
    def register_agent(self,
        name: str,
        address: str,
        organization: str,
        description: str,
        interfaces: List[Dict[str, Any]],
        urls: List[str],
        token_cost: float = 0.0,
        capabilities: List[str] = None
    ) -> Dict[str, Any]:
        """注册Agent
        
        Args:
            name: Agent名称
            address: Agent地址（例如：agentdns://example/agent）
            organization: 所属组织
            description: Agent描述
            interfaces: 接口列表
            urls: API URL列表
            token_cost: 每次调用的token费用
            capabilities: Agent能力标签列表
            
        Returns:
            注册成功的Agent信息
        """
        agent_data = {
            "name": name,
            "address": address,
            "organization": organization,
            "description": description,
            "interfaces": interfaces,
            "urls": urls,
            "token_cost": token_cost,
            "capabilities": capabilities or []
        }
        
        response = requests.post(f"{self.api_base}/register/agent", json=agent_data)
        response.raise_for_status()
        return response.json()
    
    def resolve_agent(self, address: str) -> Dict[str, Any]:
        """解析Agent地址
        
        Args:
            address: Agent地址（例如：agentdns://example/agent）
            
        Returns:
            Agent详细信息
        """
        response = requests.get(f"{self.api_base}/resolve/agent/{address}")
        response.raise_for_status()
        return response.json()
    
    def search_agents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索Agent
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            匹配的Agent列表
        """
        search_data = {
            "query": query,
            "limit": limit
        }
        
        response = requests.post(f"{self.api_base}/search", json=search_data)
        response.raise_for_status()
        return response.json()
    
    def resolve_organization(self, address: str) -> Dict[str, Any]:
        """解析组织地址
        
        Args:
            address: 组织地址（例如：agentdns://example）
            
        Returns:
            组织详细信息
        """
        response = requests.get(f"{self.api_base}/resolve/organization/{address}")
        response.raise_for_status()
        return response.json()
    
    def list_organization_agents(self, org_address: str) -> List[Dict[str, Any]]:
        """列出组织下的所有Agent
        
        Args:
            org_address: 组织地址（例如：agentdns://example）
            
        Returns:
            组织下的Agent列表
        """
        response = requests.get(f"{self.api_base}/list/organization/{org_address}/agents")
        response.raise_for_status()
        return response.json() 