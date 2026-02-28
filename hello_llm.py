import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 1. 启动开锁匠，读取 .env 文件里的 API Key
load_dotenv()

# 2. 召唤大模型！(这是 LangChain 最核心的封装)
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="deepseek-chat", # 替换为你申请的实际模型名称，比如 glm-4
    base_url="https://api.deepseek.com" # 如果是国内模型，通常需要填它的专属 API 地址；如果是原版 OpenAI 则不需要这行
)

# 3. 向大模型喊出你的第一句话
print("正在向大模型发送消息，请稍候...")
response = llm.invoke("你好，我是刚学 Python 的大学生，正在写我的第一个 AI 项目，请用一句带有赛博朋克风格的霸气话语鼓励我！")

# 4. 见证奇迹的时刻，打印它的回答！
print("\n🤖 大模型的回答：")
print(response.content)