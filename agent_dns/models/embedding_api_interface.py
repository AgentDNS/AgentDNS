import torch
import os
import logging
import getpass
from openai import OpenAI
from abc import ABC
from typing import List

class EmbedAPIInterface(ABC):
    """通用的向量化API接口抽象类"""
    
    def __init__(self, model_name: str, base_url: str = None, embed_dim: int = None, api_key_env_name: str = None):
        self.model_name = model_name
        self.base_url = base_url
        self.embed_dim = embed_dim
        self.api_key_env_name = api_key_env_name
        self.api_key = self.get_api_key()
        self.client = self._init_client()
    
    def _init_client(self):
        """初始化API客户端"""
        return OpenAI(
            api_key=self.api_key, 
            base_url=self.base_url,
        )
    
    def get_api_key(self) -> str:
        """获取API密钥"""
        logging.info(f"正在初始化API key")
        api_key = os.getenv(self.api_key_env_name)
        if api_key:
            return api_key
        print(f"未找到环境变量 {self.api_key_env_name}")
        api_key = getpass.getpass(f"请输入您的API key: ")
        
        if not api_key:
            raise ValueError("API key不能为空")
            
        return api_key
    
    def embed(self, query: str | List[str], squeeze=False):
        """发起对话"""
        completion = self.client.embeddings.create(
            model=self.model_name,
            input=query,  # Both str and list
            dimensions=self.embed_dim,
            encoding_format="float"
        )

        return self.unwrap_output(completion, squeeze)
    
    def unwrap_output(self, output):
        """解析API输出"""
        return output.data

class QwenEmbedAPIInterface(EmbedAPIInterface):  
    def __init__(self, model_name="text-embedding-v3", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", embed_dim=1024):
        super().__init__(
            model_name=model_name,
            base_url=base_url,
            embed_dim=embed_dim,
            api_key_env_name="DASHSCOPE_API_KEY"
        )
    
    def unwrap_output(self, output, squeeze=False):
        if not output or not output.data:
            return None
        if squeeze and len(output.data) == 1:
            return output.data[0].embedding
        embed_list = [e.embedding for e in output.data]
        return embed_list

if __name__ == "__main__":
    model = QwenEmbedAPIInterface()
    rep = model.embed("好吃")
    print(rep)
    print(len(rep))