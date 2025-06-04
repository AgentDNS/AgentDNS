from typing import List, Dict, Optional
from pydantic import BaseModel, Field, HttpUrl


class AgentInterface(BaseModel):
    """Agent接口定义"""
    name: str = Field(..., description="接口名称")
    description: str = Field(..., description="接口描述")
    parameters: Dict = Field(default_factory=dict, description="接口参数")
    
    
class Agent(BaseModel):
    """Agent信息模型"""
    name: str = Field(..., description="Agent名称")
    address: str = Field(..., description="Agent地址，例如：agentdns://alibaba/paperagent")
    organization: str = Field(..., description="所属组织")
    description: str = Field(..., description="功能描述")
    interfaces: List[AgentInterface] = Field(default_factory=list, description="接口列表")
    urls: str = Field(..., description="API URL地址")
    token_cost: float = Field(0, description="每次调用的token费用")
    capabilities: List[str] = Field(default_factory=list, description="Agent能力标签")
    
    
class Organization(BaseModel):
    """组织信息模型"""
    name: str = Field(..., description="组织名称")
    address: str = Field(..., description="组织地址，例如：agentdns://alibaba")
    description: str = Field("", description="组织描述")
    
    
class AgentQuery(BaseModel):
    """Agent查询请求"""
    query: str = Field(..., description="自然语言查询")
    limit: int = Field(5, description="返回结果限制数量") 