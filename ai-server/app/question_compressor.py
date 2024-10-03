import os
import re
import time

from dotenv import load_dotenv
from typing import Annotated, TypedDict, List, Tuple, Dict
from tqdm import tqdm
from supabase import Client

# langchin
from langchain_upstage import ChatUpstage
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain.prompts import PromptTemplate

# langgraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode

# langfuse
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from fetch_messages import CONVERSATION_ID_EXAMPLE_2, Message, fetch_messages
from db_client import get_db_client

langfuse_handler = CallbackHandler()
langfuse = Langfuse()

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

class CodeStorage(TypedDict):
    code_description: str
    code_snippet: str

class ChatMessage(TypedDict):
    message_id: int
    message_type: str
    message_content: str
    code_documents : List[CodeStorage]

class QA(TypedDict):
    pair_num : int
    q: ChatMessage
    a: ChatMessage

class GraphState(TypedDict):
    conversation_id : int
    original_data: List[QA]
    processed_data: List[QA]

class GraphState(TypedDict):
    conversation_id : int
    original_data: List[str]
    processed_data: List[str]
    code_documents:List[str]

class QnAPairCreator:
    """
    QnAPairCreator는 주어진 대화 ID에 대해 메시지를 가져오고,
    질문과 답변 쌍(QA)을 생성하는 클래스를 정의합니다.

    Attributes:
        conversation_id (int): Q&A 쌍을 생성할 대화의 ID.
    """

    def __init__(self, conversation_id: int):
        """
        QnAPairCreator의 생성자입니다.

        Args:
            conversation_id (int): Q&A 쌍을 생성할 대화의 ID.
        """
        self.conversation_id = conversation_id

    def create_qna_pairs(self, database:Client) -> List[QA]:
        """
        대화 ID에 해당하는 메시지를 가져와 Q&A 쌍을 생성합니다.

        Returns:
            List[QA]: 질문과 답변 쌍의 리스트.
        """
        # TODO fetch_messages를 사용해 데이터 조회
        chat_ex: List[Message] = fetch_messages(database, self.conversation_id)
        return self._format_message(chat_ex)

    def _format_message(self, chat_ex: List[Message]) -> List[QA]:
        """
        주어진 메시지 리스트를 Q&A 쌍으로 포맷팅합니다.

        Args:
            chat_ex (List[Message]): 포맷팅할 메시지 리스트.

        Returns:
            List[QA]: 포맷팅된 질문과 답변 쌍의 리스트.
        """
        formatted_chat_ex = []
        
        # chat_ex의 각 element를 ChatMessage로 변환 후 2개씩 짝지음
        for i in range(0, len(chat_ex) - 1):
            # message_type에 따라 question과 answer를 구분
            if chat_ex[i]["message_type"] == "question" and chat_ex[i + 1]["message_type"] == "answer":
                # 질문 메시지 생성
                q_message = ChatMessage(
                    message_id=chat_ex[i]["id"],
                    message_type=chat_ex[i]["message_type"],
                    message_content=chat_ex[i]["message_content"]
                )

                # 답변 메시지 생성
                a_message = ChatMessage(
                    message_id=chat_ex[i + 1]["id"],
                    message_type=chat_ex[i + 1]["message_type"],
                    message_content=chat_ex[i + 1]["message_content"]
                )
                # Q&A 쌍 생성
                qa_pair = QA(
                    pair_num=(i // 2) + 1,
                    q=q_message,
                    a=a_message
                )
                
                # q와 a의 쌍을 formatted_chat_ex에 추가
                formatted_chat_ex.append(qa_pair)
        return formatted_chat_ex


class QnAProcessor:

    """
    QnAProcessor 클래스는 Q&A 쌍을 처리하는 데 사용됩니다. 
    이 클래스는 질문과 답변에서 코드 스니펫을 추출하고, 해당 코드를 LLM을 사용하여 설명으로 대체합니다.
    
    Attributes:
    - pair_list (List[QA]): 처리할 Q&A 쌍의 리스트.
    - model: LLM 모델 인스턴스.
    - code_documents (dict): 각 Q&A 쌍에 대한 코드 문서 정보를 저장하는 딕셔너리.

    Methods:
    - process_qna_pair(): Q&A 쌍을 처리하고 코드 스니펫을 설명으로 대체하며, 최종 Q&A 쌍과 코드 문서 딕셔너리를 반환합니다.
    - extract_code_and_replace_with_description(qna_pair): 질문과 답변에서 코드를 추출하고 설명으로 대체합니다.
    - replace_code_with_description(message, description_prefix): 코드 설명을 생성하고 메시지에서 코드 스니펫을 대체합니다.
    - determine_code_from_message(message_content): 메시지에서 코드 스니펫을 구분합니다.
    - describe_code_with_llm(code_snippet): LLM을 사용하여 주어진 코드 스니펫에 대한 설명을 생성합니다.
    - summarize_question_with_llm(question): LLM을 사용하여 주어진 질문을 요약합니다.
    """
        

    def __init__(self, pair_list: List[QA], model) -> None:
        self.pair_list = pair_list
        self.model = model
        self.code_documents: List[CodeStorage] = []

    
    def process_qna_pair(self):
        """Q&A 쌍을 처리하고 코드 스니펫을 설명으로 대체."""
        for qna_pair in tqdm(self.pair_list,  desc="Processing Q&A Pairs", unit="pair"):
            # 코드 추출 및 설명으로 대체
            question_without_code, answer_without_code, question_code_document, answer_code_document = self.extract_code_and_replace_with_description(qna_pair)
            # 질문 요약하기
            summarized_question = self.summarize_question_with_llm(question_without_code)
            
            qna_pair["q"]["message_content"] = summarized_question
            qna_pair["q"]["code_documents"] = question_code_document

            qna_pair["a"]["message_content"] = answer_without_code
            qna_pair["a"]["code_documents"] = answer_code_document

        return self.pair_list
    
    def extract_code_and_replace_with_description(self, qna_pair:QA) -> Tuple[str, str, List[CodeStorage], List[CodeStorage]]:
        """질문과 답변에서 코드를 추출하고 설명으로 대체."""

        question = qna_pair["q"]
        answer = qna_pair["a"]

        question_with_code_replaced, question_code_document = self.replace_code_with_description(message=question)
        answer_with_code_replaced, answer_code_document = self.replace_code_with_description(message=answer)
        
        return question_with_code_replaced, answer_with_code_replaced, question_code_document, answer_code_document
    

    def replace_code_with_description(self, message: ChatMessage, description_prefix="Code_Snippet") -> Tuple[str, List[CodeStorage]]:
        """코드 설명 생성 및 대체."""        
        code_document = []
        updated_message_content = self.determine_code_from_message(message["message_content"])
        code_pattern = r"```(.*?)```"

        def replace_code(match):
            code_snippet = match.group(1).strip()
            # LLM 호출로 코드 설명 생성
            description = self.describe_code_with_llm(code_snippet=code_snippet)
            
            code_description = f"{description_prefix}_{len(code_document) + 1}: {description}"

            # 코드 저장
            code_document.append(CodeStorage(
                code_snippet=code_snippet,
                code_description=code_description,
            ))

            return f"<-- {code_description} -->"

        replaced_message = re.sub(code_pattern, replace_code, updated_message_content, flags=re.DOTALL)
        return replaced_message, code_document
    
    def determine_code_from_message(self, message_content: str) -> str:
        """메시지에서 코드 스니펫을 구분."""
        prompt_template = PromptTemplate(
            template="Please wrap the code sections in the following message with backticks::\n\n{message_content}",
            input_variables=["message_content"]
        )
        prompt = prompt_template.format(message_content=message_content)
        # LLM 호출 및 결과 가져오기
        response = self.model.invoke(prompt)
        # print("\n코드 추출\n" + response.content)
        return response.content # 코드 스니펫 리스트로 반환


    def describe_code_with_llm(self, code_snippet:str) -> str:
        """LLM을 사용하여 코드 설명 생성."""
        short_code_description: Annotated[str, HumanMessage] = langfuse.get_prompt("short_code_description")
        prompt = short_code_description.compile(code_snippet=code_snippet)
        response = self.model.invoke(prompt)
        return response.content.strip()
    
    def summarize_question_with_llm(self, question:str) -> str:
        """LLM을 사용하여 질문 요약."""
        question_summarizer : Annotated[str, HumanMessage] = langfuse.get_prompt("question_summarizer")
        prompt = question_summarizer.compile(question=question)
        response = self.model.invoke(prompt)
        return response.content.strip()




#####
database = get_db_client()
qna_creator = QnAPairCreator(CONVERSATION_ID_EXAMPLE_2)
formatted_qna_data = qna_creator.create_qna_pairs(database)

#usage for example
llm  = ChatOpenAI(model='gpt-4o-mini', temperature=0, max_tokens=None,
    timeout=None,
    max_retries=1,
    api_key = openai_api_key
)
# llm = ChatUpstage(model='solar-pro')

qna_processor = QnAProcessor(formatted_qna_data, llm)

# Start the timer
start_time = time.time()

# Process Q&A pairs with a progress bar
processed_qna_pair, code_documents = qna_processor.process_qna_pair()

# Stop the timer
end_time = time.time()

# Calculate elapsed time
elapsed_time = end_time - start_time
print(f"Execution Time: {elapsed_time:.2f} seconds")
