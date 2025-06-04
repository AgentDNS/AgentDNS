from typing import List

REFLECT_SYSTEM_TEMPLATE = """
你是人工智能助手。用户正在寻找一些智能体工具，他的需求在<query>标签内。现在，我们已经搜索到了一些工具，它们的名字和功能描述都放在一个字典列表中，并被<tools>标签包围。
请结合用户的原始需求与搜索到的智能体工具的描述，分别判断每个工具是否真正对用户的需求有帮助，回答有用的工具在列表中的下标。\n
注意：\n
1）每一个工具的下标之间用单个空格隔开\n
2）下标是0到列表长度-1之间的整数
3）如果所有的工具都对用户没有帮助，你应该回答None\n
4）如果输入的工具列表为空，也回答None
4）你要么回答一组被空格分隔的下标。要么回答None。请严格遵守回答格式，在回答中不要带有任何额外的字符。\n
"""
REFLECT_USER_TEMPLATE = "<query>{}</query>\n<tools>{}</tools>"

EXTRACT_SYSTEM_TEMPLATE = """你是一位人工智能助手。接下来，用户需要查找一些智能体工具，并将他们的需求以自然语言的形式告诉你。
你需要从用户的每一个要求中提取出不多于10个精炼的功能关键词
（根据用户使用的语言，使用中文或英文；如果某一专有名词更适合用某一语言，你可以单独使用更合适的语言回答这一关键词。），每个关键词不应超过四个汉字（若为单词则无限制），
除非关键词中包含重要的专业术语。
在你的回答中，除了提取出的关键词，不应包含任何多余的文字或字符。
用户同一个需求提取出的关键词之间以单个空格连接；用户不同需求的关键词之间以换行符连接。\n
以下为一个合适的单轮对话示例：\n
用户：\n一个帮助查找和总结学术论文的AI助手\n
回复：\n论文搜索 论文总结"""


def reflect_valid_check(res: str, N: int):
    if res == "None":
        return True
    indices = res.split(' ')
    try:
        for i in indices:
            num = int(i)
            if num < 0 or num >= N:
                print(f"Invalid index: {num} is out of range for a list of length {N}")
                raise IndexError
    except (ValueError, IndexError) as e:
        print("Invalid indices.")
        print(e)
        return False
    
    return True

def unwarp_reflection(res: str, tool_list: List[dict]):
    if res == "None":
        return []
    indices = res.split(' ')
    return [tool_list[int(i)] for i in indices]