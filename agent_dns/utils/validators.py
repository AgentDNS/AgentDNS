import re
from typing import Tuple, Optional


def validate_agent_address(address: str) -> Tuple[bool, Optional[str]]:
    """验证Agent地址格式
    
    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 错误信息)
    """
    if not address:
        return False, "地址不能为空"
        
    # 检查前缀
    if not address.startswith("agentdns://"):
        return False, "地址必须以 'agentdns://' 开头"
    
    # 验证格式
    pattern = r"agentdns://([^/]+)/([^/]+)$"
    match = re.match(pattern, address)
    
    if not match:
        return False, "地址格式无效，应为 'agentdns://organization/agent_name'"
    
    return True, None


def validate_organization_address(address: str) -> Tuple[bool, Optional[str]]:
    """验证组织地址格式
    
    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 错误信息)
    """
    if not address:
        return False, "地址不能为空"
        
    # 检查前缀
    if not address.startswith("agentdns://"):
        return False, "地址必须以 'agentdns://' 开头"
    
    # 验证格式
    pattern = r"agentdns://([^/]+)$"
    match = re.match(pattern, address)
    
    if not match:
        return False, "地址格式无效，应为 'agentdns://organization'"
    
    return True, None


def normalize_address(address: str) -> str:
    """标准化地址格式"""
    if not address.startswith("agentdns://"):
        return f"agentdns://{address}"
    return address 