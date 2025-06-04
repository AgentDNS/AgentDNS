import time
import logging
from typing import List
from abc import ABC, abstractmethod

from pymilvus import MilvusClient
from pymilvus import DataType, Function, FunctionType
from pymilvus import AnnSearchRequest, WeightedRanker, RRFRanker

from langchain.text_splitter import RecursiveCharacterTextSplitter

from agent_dns.models.chat_api_interface import QwenAPIInterface
from agent_dns.models.embedding_api_interface import QwenEmbedAPIInterface
from agent_dns.models.prompt import REFLECT_SYSTEM_TEMPLATE, REFLECT_USER_TEMPLATE, EXTRACT_SYSTEM_TEMPLATE
from agent_dns.models.prompt import reflect_valid_check, unwarp_reflection

logging.basicConfig(level = logging.INFO)


DEFAULT_URI = "http://localhost:19530"
TOKEN = "root:Milvus"
DNS_COL_NAME = "agent"


class MilvusDBBase(ABC):
    def __init__(self, 
                 uri=DEFAULT_URI, 
                 token=TOKEN, 
                 col_name="rag", 
                 **kwargs):
        self.client = MilvusClient(
            uri=uri,
            token=token,
            timeout=None
        )
        self.uri = uri
        self.col_name = col_name
        self.display_field = []
        self.id_field = ""
        self.set_f_attr()

    def init_collection(self, overwrite=False):
        # Collection存在, 只有overwrite为True时, 重新创建Collection
        if self.client.has_collection(self.col_name):
            if not overwrite:
                logging.info("Milvus collection named {} at {} exists. \n Initialization skipped.".format(self.col_name, self.uri))
                return
            else:
                self.client.drop_collection(self.col_name)
        
        # Collection不存在, 直接创建
        schema = self.set_schema()
        indices = self.set_indices()
        self.client.create_collection(
            collection_name = self.col_name,
            schema = schema,
            index_params = indices
        )

    @abstractmethod
    def set_schema(self):
        pass

    @abstractmethod
    def set_indices(self):
        pass

    @abstractmethod
    def set_f_attr(self, f_dict=None):
        pass

    def remove_collection(self):
        if self.client.has_collection(self.col_name):
            self.client.drop_collection(self.col_name)

    @abstractmethod
    def insert_item(self, data):
        pass
    
    def delete_item(self, ids=None, filter=""):
        if self.client.has_collection(self.col_name):
            del_count_dict = self.client.delete(
                collection_name=self.col_name,
                ids=ids,
                filter=filter
            )
            return del_count_dict
        return None

    def display(self):
        res = self.client.query(
            collection_name = self.col_name,
            filter = self.id_field + " >= 0 ",
            output_fields = self.display_field,
        )
        for d in res:
            print(d)

    def unwrap_search_result(self, res):
        count = 1
        for r in res:
            print("======Results for Query {}======".format(count))
            for item in r:
                print("Search Result: ")
                print(item)
            count += 1


class AgentDNSDB(MilvusDBBase):
    def __init__(self, 
                uri=DEFAULT_URI, 
                token=TOKEN, 
                col_name=DNS_COL_NAME, 
                **kwargs):
        super().__init__(uri, token, col_name, **kwargs)
        self.embed_model = QwenEmbedAPIInterface()
        self.embed_dim = self.embed_model.embed_dim
        self.chat_model = QwenAPIInterface()
    
    def set_schema(self):
        schema = MilvusClient.create_schema(
            auto_id=True,
            enable_dynamic_field=True,
        )

        analyzer_params = {
            "tokenizer": "jieba"
        }

        # 可以与mysql数据库的id保持一致，如此一来id就要自己设置了
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="agent_name", datatype=DataType.VARCHAR, max_length=128)
        schema.add_field(field_name="address", datatype=DataType.VARCHAR, max_length=256)
        schema.add_field(field_name="description", datatype=DataType.VARCHAR, max_length=256, enable_analyzer=True, analyzer_params=analyzer_params)
        schema.add_field(field_name="tags", datatype=DataType.VARCHAR, max_length=128, enable_analyzer=True, analyzer_params=analyzer_params)
        schema.add_field(field_name="description_vector", datatype=DataType.FLOAT_VECTOR, dim=self.embed_dim)
        schema.add_field(field_name="tags_vector", datatype=DataType.FLOAT_VECTOR, dim=self.embed_dim)
        schema.add_field(field_name="tags_bm25", datatype=DataType.SPARSE_FLOAT_VECTOR)
        schema.add_field(field_name="description_bm25", datatype=DataType.SPARSE_FLOAT_VECTOR)
        functions_tag = Function(
            name="bm25_t",
            function_type=FunctionType.BM25,
            input_field_names=["tags"],
            output_field_names="tags_bm25",
        )
        functions_des = Function(
            name="bm25_d",
            function_type=FunctionType.BM25,
            input_field_names=["description"],
            output_field_names="description_bm25",
        )

        schema.add_function(functions_tag)
        schema.add_function(functions_des)

        return schema

    def set_indices(self):
        index_params = self.client.prepare_index_params()
        
        index_params.add_index(
            field_name = "description_vector", 
            index_type = "AUTOINDEX",
            metric_type = "COSINE"
        )
        index_params.add_index(
            field_name = "tags_vector", 
            index_type = "AUTOINDEX",
            metric_type = "COSINE"
        )
        index_params.add_index(
            field_name="tags_bm25",
            index_type="AUTOINDEX",
            metric_type="BM25",
        )
        index_params.add_index(
            field_name="description_bm25",
            index_type="AUTOINDEX",
            metric_type="BM25",
        )

        return index_params
    
    def set_f_attr(self, f_dict=None):
        self.id_field = "id"
        self.display_field = ["id", "agent_name", "address", "description", "tags"]
        self.search_field = ["agent_name", "address", "description", "tags"]
    
    def insert_item(self, data):
        logging.info("正在插入Agent数据...")
        start_time = time.time()

        #### data: List[Dict]. keys: agent_name, address, description, tags]
        # TODO:从description生成tags
        inserted_data = []
        for item in data:
            des_vec = self.embed_query(item["description"])
            tag_vec = self.embed_query(item["tags"])
            inserted_data.append({"agent_name": item["agent_name"],
                                  "address": item["address"],
                                  "description": item["description"],
                                  "tags": item["tags"],
                                  "description_vector": des_vec,
                                  "tags_vector": tag_vec,
                                })
        self.client.insert(collection_name=self.col_name, data=inserted_data)
        insert_time = time.time()
        logging.info("数据插入总时长: {}s".format(insert_time - start_time))

    def embed_query(self, q: str | List[str]):
        return self.embed_model.embed(q, squeeze=True)
    
    def embed_queries(self, q: str | List[str]):
        return self.embed_model.embed(q, squeeze=False)
    
    def extract_functions(self, query: str | List[str]):
        ''' 从用户query中提取功能关键词'''
        if isinstance(query, str):
            query = [query]

        system_prompt = EXTRACT_SYSTEM_TEMPLATE
        user_reqs = '\n'.join(query)
        print("requirements: {}".format(user_reqs))
        res = self.chat_model.chat(user_reqs, chat_history=None, system_prompt=system_prompt).split('\n')
        return res
    
    def RRF_hybrid_search(self, original_queries, query_tags, k_search=10, k_rerank=3, coeff=60):
        if isinstance(original_queries, str):
            original_queries = [original_queries]
        if isinstance(query_tags, str):
            query_tags = [query_tags]

        # 全文搜索 - 描述
        search_param_1 = {
            "data": original_queries,
            "anns_field": "description_bm25",
            "param": {
                "metric_type": "BM25",
            },
            "limit": k_search
        }
        request_1 = AnnSearchRequest(**search_param_1)
    
        # 向量搜索 - 标签
        search_param_2 = {
            "data": self.embed_queries(query_tags),
            "anns_field": "tags_vector",
            "param": {
                "metric_type": "COSINE",
            },
            "limit": k_search
        }
        request_2 = AnnSearchRequest(**search_param_2)

        # 全文搜索 - 标签
        search_param_3 = {
            "data": query_tags,
            "anns_field": "description_bm25",
            "param": {
                "metric_type": "BM25",
            },
            "limit": k_search
        }
        request_3 = AnnSearchRequest(**search_param_3)

        # 搜索结果重排
        reqs = [request_1, request_2, request_3]

        reranker = RRFRanker(coeff)
        res = self.client.hybrid_search(
            collection_name=self.col_name,
            reqs=reqs,
            ranker=reranker,
            limit=k_rerank,
            output_fields=self.search_field
        )
        return res
    
    def unwrap_search_result(self, res, verbose=False):
        count = 1
        res_list = []
        for r in res:
            if verbose:
                print("======Search results for Query {}======".format(count))
            cur_list = []
            for item in r:
                cur_list.append(item["entity"])
                if verbose:
                    print(item["entity"])
            res_list.append(cur_list)
            count += 1
        if len(res) == 1:
            return res_list[0]
        return res_list

    def filter_tools(self, query: str | List[str], tool_list: List[dict] | List[List[dict]], squeeze=False):
        if isinstance(query, str):
            query = [query]
            tool_list = [tool_list]
        assert len(query) == len(tool_list)

        tailored_list = []
        system_prompt = REFLECT_SYSTEM_TEMPLATE
        for i in range(len(query)):
            user_prompt = REFLECT_USER_TEMPLATE.format(query[i], tool_list[i])
            res = self.chat_model.chat(user_prompt, None, system_prompt)
            if reflect_valid_check(res, len(tool_list[i])):
               tailored_list.append(unwarp_reflection(res, tool_list[i]))
            else:
                tailored_list.append([])

        if squeeze and len(tailored_list) == 1:
            tailored_list = tailored_list[0]

        return tailored_list
    
    def search(self, query: str | List[str], top_k=5, verbose=False):
        query_tags = self.extract_functions(query)
        if verbose:
            print("提取到关键词: ", query_tags)

        search_res = self.RRF_hybrid_search(query, query_tags, k_search=max(top_k * 2, 10), k_rerank=top_k, coeff=100)
        tools = self.unwrap_search_result(search_res, verbose=verbose)
        recommended_tools = self.filter_tools(query, tools, squeeze=False)

        if verbose:
            print("推荐用户使用的工具： ")
            for i in range(len(recommended_tools)):
                print("用户需求：", query[i])
                print("建议工具：")
                for tool in recommended_tools[i]:
                    print(tool)

        return recommended_tools


if __name__ == "__main__":
    def create_test_dataset():
        from agent_dns.db.testing_data import test_data
        db.init_collection(overwrite=True)
        db.insert_item(test_data)
        time.sleep(5)
        db.display()
        
    db = AgentDNSDB()
    # 初始化milvus数据库； 需要时解除注释
    create_test_dataset()

    query = ["一个帮助查找和总结学术论文的AI助手", "阅读外文文献有关的AI工具"]
    db.search(query, verbose=True)