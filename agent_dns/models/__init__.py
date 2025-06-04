"""数据模型"""

from agent_dns.models.agent import (
    Agent,
    AgentInterface,
    Organization,
    AgentQuery
)

from agent_dns.models.chat_api_interface import QwenAPIInterface
from agent_dns.models.embedding_api_interface import QwenEmbedAPIInterface

__all__ = [
    "Agent",
    "AgentInterface",
    "Organization",
    "AgentQuery",
    "QwenEmbedAPIInterface",
    "QwenAPIInterface",
] 