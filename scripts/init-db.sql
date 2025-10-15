-- AgentDNS数据库初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建索引来提高查询性能
-- 这些索引会在SQLAlchemy创建表后自动应用

-- 为服务名称和描述创建全文搜索索引
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_search 
-- ON services USING gin(to_tsvector('english', name || ' ' || description));

-- 为服务标签创建GIN索引
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_tags 
-- ON services USING gin(tags);

-- 为使用记录创建时间索引
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usage_timestamp 
-- ON usage_records (created_at);

-- 为计费记录创建复合索引
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billing_user_date 
-- ON billing_records (user_id, created_at);

-- 设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agentdns;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO agentdns;

-- 打印初始化完成信息
DO $$
BEGIN
    RAISE NOTICE 'AgentDNS数据库初始化完成';
END $$; 