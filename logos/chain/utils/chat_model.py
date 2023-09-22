from langchain.chat_models import ChatOpenAI
from nl2logic.config import nl2logic_config as config

openai_chat_model = ChatOpenAI(
    model=config.langchain.openai.chat_model,
    openai_api_key=config.langchain.openai.api_key,
)
