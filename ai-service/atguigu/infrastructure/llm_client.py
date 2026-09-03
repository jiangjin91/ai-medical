"""
通过LangChain定义LLM客户端
模块之间的组件导入的标准写法：
1.导入sdk自带的
2.导入第三方的
3.导入自己定义
"""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from atguigu.config.settings import settings

# 初始化模型
llm_client: BaseChatModel = init_chat_model(
    model_provider="openai",
    model=settings.llm_model,
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url
)

if __name__ == '__main__':
    ai_message: AIMessage = llm_client.invoke("天道酬勤")
    print(ai_message.content)

    chain = llm_client | StrOutputParser() # | LCEL表达式：
    chain_msg = chain.invoke("百二雄关终属楚")
    print(chain_msg)
