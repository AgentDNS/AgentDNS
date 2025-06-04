import torch
import os
import logging
import getpass
from openai import OpenAI
from abc import ABC

class ChatAPIInterface(ABC):
    """通用的对话API接口抽象类"""
    
    def __init__(self, model_name: str, base_url: str = None, api_key_env_name: str = None):
        self.model_name = model_name
        self.base_url = base_url
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
    
    def chat(self, query: str, chat_history=None, system_prompt="You are a helpful assistant."):
        """发起对话"""
        messages = []
        if chat_history is not None:
            messages.extend(chat_history)
            
        messages.extend([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': query}
        ])
        
        completion = self.client.chat.completions.create(
            model = self.model_name,
            messages = messages
        )
        return self.unwrap_output(completion)
    
    def unwrap_output(self, output):
        """解析API输出"""
        return output.choices[0].message.content

class QwenAPIInterface(ChatAPIInterface):  
    def __init__(self, model_name="qwen-max", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"):
        super().__init__(
            model_name=model_name,
            base_url=base_url,
            api_key_env_name="DASHSCOPE_API_KEY"
        )

if __name__ == "__main__":
    model = QwenAPIInterface()
    model.chat("你好")