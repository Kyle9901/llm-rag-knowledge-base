import os
from dotenv import load_dotenv

# 1. 召唤开锁匠：读取 .env 文件里的所有内容，加载到系统的环境变量中
load_dotenv()

# 2. 从环境变量中拿出你的 API Key
my_api_key = os.getenv("OPENAI_API_KEY")

# 3. 验证一下有没有拿到（出于安全，我们只打印前 5 个字符，不要把完整的密码打印出来！）
if my_api_key:
    print("✅ 成功拿到 API Key！前缀是：", my_api_key[:5] + "******")
else:
    print("❌ 完蛋，没找到 API Key，检查一下 .env 文件是不是写错了？")