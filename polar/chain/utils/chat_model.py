from langchain.chat_models import ChatOpenAI
from nl2logic.config import nl2logic_config as config

def openai_chat_model():
    return ChatOpenAI(
        model=config.langchain.openai.chat_model,
        openai_api_key=config.langchain.openai.api_key,
        temperature=config.langchain.openai.temperature
    )
