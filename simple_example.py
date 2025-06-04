from agentdns_sdk import AgentDNSClient

# 导入测试数据
from agent_dns.db.testing_data import test_data

# 创建AgentDNS客户端实例
client = AgentDNSClient("http://localhost:8000")

def register_organization():
    """注册组织"""
    try:
        org = client.register_organization(
            name="Example Corp",
            address="agentdns://example",
            description="示例组织"
        )
        print("组织注册成功！")
        print(org)
    except Exception as e:
        print(f"组织注册失败: {e}")

def register_agent():
    """注册多个Agent（来自testing_data.py）"""
    print(f"开始注册 {len(test_data)} 个Agent...")
    success_count = 0
    
    for i, item in enumerate(test_data):
        try:
            # 生成唯一的agentdns地址
            agent_name_slug = item['agent_name'].lower().replace(' ', '_').replace('-', '_')
            agent_dns_address = f"agentdns://example/{agent_name_slug}_{i}"
            
            # 将tags转换为capabilities列表
            capabilities = item['tags'].split(' ') if item['tags'] else []
            
            agent = client.register_agent(
                name=item['agent_name'],
                address=agent_dns_address,
                organization="example",
                description=item['description'],
                interfaces=[
                    {
                        "name": "default_interface",
                        "description": f"{item['agent_name']}的默认接口",
                        "parameters": {
                            "query": "用户查询",
                            "options": "额外选项"
                        }
                    }
                ],
                urls=[item['address']],  # HTTP URL from test_data
                token_cost=1.0,
                capabilities=capabilities
            )
            print(f"✓ Agent注册成功: {item['agent_name']} ({agent_dns_address})")
            success_count += 1
        except Exception as e:
            print(f"✗ Agent注册失败: {item['agent_name']} - {e}")
    
    print(f"\n总计: {success_count}/{len(test_data)} 个Agent注册成功")

def resolve_agent():
    """解析一个Agent"""
    try:
        agent = client.resolve_agent("agentdns://testorg/图像处理器_3")
        print("\nAgent信息:")
        print(f"名称: {agent['name']}")
        print(f"地址: {agent['address']}")
        print(f"描述: {agent['description']}")
        print(f"组织: {agent['organization']}")
        print(f"链接: {agent['urls']}")
        print(f"能力: {agent['capabilities']}")
        print(f"token_cost: {agent['token_cost']}")
        print("\n接口:")
        for interface in agent['interfaces']:
            print(f"- {interface['name']}: {interface['description']}")
    except Exception as e:
        print(f"解析失败: {e}")

def search_agents():
    """搜索Agent"""
    try:
        agents = client.search_agents("有没有论文助手", limit=5)
        print(f"\n找到 {len(agents)} 个相关Agent:")
        for i, agent in enumerate(agents, 1):
            print(f"\n{i}. {agent['name']} ({agent['address']})")
            print(f"   描述: {agent['description']}")
            print(f"   组织: {agent['organization']}")
            print(f"   能力: {agent['capabilities']}")
            print("   接口:")
            for interface in agent['interfaces']:
                print(f"   - {interface['name']}: {interface['description']}")
    except Exception as e:
        print(f"搜索失败: {e}")

if __name__ == "__main__":
    print("1. 注册组织")
    register_organization()
    
    print("\n2. 注册Agent")
    register_agent()
    
    print("\n3. 解析Agent")
    resolve_agent()
    
    print("\n4. 搜索Agent")
    search_agents() 