from typing import List, Optional
import re

from agent_dns.models.agent import Agent, Organization
from agent_dns.db.storage import Storage
from agent_dns.db.milvus import AgentDNSDB


class AgentResolver:
    """Agent DNS解析器"""
    
    def __init__(self, storage: Storage, milvus_db: AgentDNSDB):
        self.storage = storage
        self.milvus_db = milvus_db
    
    def parse_address(self, address: str) -> dict:
        """解析Agent地址
        
        格式：agentdns://organization/agent_name
        """
        pattern = r"agentdns://([^/]+)(?:/([^/]+))?"
        match = re.match(pattern, address)
        
        if not match:
            raise ValueError(f"无效的Agent地址格式: {address}")
        
        org_name = match.group(1)
        agent_name = match.group(2)
        
        return {
            "organization": org_name,
            "agent_name": agent_name
        }
    
    def resolve_agent(self, address: str) -> Optional[Agent]:
        """根据地址解析Agent信息"""
        return self.storage.get_agent_by_address(address)
    
    def resolve_organization(self, address: str) -> Optional[Organization]:
        """根据地址解析组织信息"""
        return self.storage.get_organization(address)
    
    def list_organization_agents(self, org_address: str) -> List[Agent]:
        """列出组织下的所有Agent"""
        org = self.resolve_organization(org_address)
        if not org:
            return []
        
        # 从组织地址中提取组织名称
        org_name = self.parse_address(org_address)["organization"]
        return self.storage.list_agents(organization=org_name)
    
    def search_agents(self, query: str, limit: int = 5) -> List[Agent]:
        """根据自然语言描述使用RAG搜索适合的Agent"""
        # 调用 MilvusDB 的 search 方法
        # Milvus search is expected to return a list of dicts.
        # Based on milvus.py's set_f_attr, output_fields from Milvus search results
        # should include: ["id" (Milvus ID), "agent_name", "address" (AgentDNS address), "description", "tags"]
        
        milvus_search_response = self.milvus_db.search(query=query, top_k=limit, verbose=True) # Returns e.g. [[dict1, dict2, ...]]
        
        resolved_agents: List[Agent] = []
        # Check if response is not empty and the first list of results is not empty
        if milvus_search_response and milvus_search_response[0]: 
            actual_milvus_results = milvus_search_response[0] # This is [dict1, dict2, ...]
            for milvus_agent_data in actual_milvus_results: # milvus_agent_data is now a dict
                agent_address = milvus_agent_data.get("address") # Get AgentDNS address
                
                if agent_address:
                    # 从SQL数据库获取完整的Agent信息
                    # 使用 agent_address (应该是唯一的AgentDNS地址) 来查询
                    print(agent_address)
                    full_agent_info = self.storage.get_agent_by_url(url=agent_address)
                    if full_agent_info:
                        resolved_agents.append(full_agent_info)
                    else:
                        # Log if an agent found in Milvus is not in SQL, if necessary
                        print(f"Warning: Agent with address '{agent_address}' found in Milvus but not in SQL DB.")
                else:
                    print(f"Warning: Milvus search result missing 'address': {milvus_agent_data}")

                if len(resolved_agents) >= limit: # Ensure we don't exceed the requested limit
                    break 
        
        return resolved_agents 