from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
import os

from agent_dns.db.models import Base

class Database:
    """数据库连接管理"""
    
    def __init__(self, db_url: str = None):
        """初始化数据库连接
        
        Args:
            db_url: 数据库连接URL。如果为None，则从环境变量 "DB_URL" 读取。
        """
        final_db_url = db_url # 使用一个新变量来存储最终的URL

        if final_db_url is None:
            print("DEBUG: db_url argument was None, trying os.environ.get(\"DB_URL\")")
            final_db_url = os.environ.get("DB_URL") # 直接尝试获取 "DB_URL"
            if final_db_url is None:
                # 如果环境变量 "DB_URL" 也没有设置，则配置错误
                raise ValueError("Database URL not provided via argument or DB_URL environment variable.")
        
        # 确保在引擎创建前打印最终使用的URL
        print(f"INFO: Database class will connect with DB_URL: {final_db_url}")
        
        # 创建数据库引擎
        self.engine = create_engine(
            final_db_url,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False  # 在生产中可以设为False，调试时可设为True
        )
        
        # 创建会话工厂
        self.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # 创建线程安全的会话
        self.Session = scoped_session(self.session_factory)
        
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
        
    def drop_tables(self):
        """删除所有表"""
        Base.metadata.drop_all(self.engine)
        
    @contextmanager
    def session_scope(self):
        """提供事务管理的会话上下文管理器"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close() 