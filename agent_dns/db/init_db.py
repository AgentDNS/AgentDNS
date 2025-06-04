#!/usr/bin/env python
"""
数据库初始化脚本 - 用于创建数据库表
"""
import argparse

from agent_dns.db.database import Database


def init_db(db_url: str = None):
    """初始化数据库"""
    # 创建数据库连接
    db = Database(db_url)
    
    # 创建所有表
    print("创建数据库表...")
    db.create_tables()
    print("数据库表创建完成")


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="AgentDNS数据库初始化工具")
    parser.add_argument(
        "--db-url", 
        type=str, 
        default=None, 
        help="数据库连接URL，例如：mysql+pymysql://username:password@localhost/agentdns"
    )
    
    args = parser.parse_args()
    
    # 初始化数据库
    init_db(args.db_url)
    
    print("数据库初始化完成")


if __name__ == "__main__":
    main() 