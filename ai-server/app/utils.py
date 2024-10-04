from operator import not_
import os
from tabnanny import check
# .env 파일의 환경 변수를 로드합니다.
from certifi import contents
from dotenv import load_dotenv
from supabase import create_client, Client
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
# langchin
from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from typing import Annotated, Literal, TypedDict

# langfuse
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
langfuse_handler = CallbackHandler()
langfuse = Langfuse()
database: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class q_and_a(TypedDict):
    q: str
    a: str

class GraphState(TypedDict):
    not_processed_conversations: list[q_and_a]
    processed_conversations: list[q_and_a]
    result: str  # 수정된 변수명

def format_message(chat_ex):
    formatted_chat_ex = []
    # chat_ex를 순회하면서 2개의 요소씩 묶어서 formatted_chat_ex에 추가합니다.
    for i in range(1, len(chat_ex) - 1, 2):
        formatted_chat_ex.append({"q": chat_ex[i]["content"], "a": chat_ex[i + 1]["content"]})
    return formatted_chat_ex

def load_conversation(chat_name="chat_ex2"):
        # langfuse에서 대화 세트 가져오기(chat_ex1 -> 짧은 대화, chat_ex2 -> 긴 대화)
        try:
            conversation_data = langfuse.get_prompt(chat_name).prompt
        except Exception as e:
            print(f"Error fetching conversation data: {e}")
            conversation_data = []

        return conversation_data

# conversation_id로  메세지 데이터 조회
def fetch_messages(conversation_id) -> list:
    try:
        response = database.table("messages") \
                    .select("sequence_number, message_type, message_content") \
                    .eq("conversation_id", conversation_id) \
                    .order("sequence_number", desc=False) \
                    .execute()
        
        messages = response.data
        if len(messages) == 0 :
            raise Exception(f"No messages related conversation {conversation_id}")

    except Exception as e:
        print(f"Internal server error: {str(e)}") 

    
    return messages
