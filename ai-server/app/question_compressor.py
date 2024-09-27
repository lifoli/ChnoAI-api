import os
import re
from dotenv import load_dotenv
from typing import Annotated, TypedDict, List

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


langfuse_handler = CallbackHandler()
langfuse = Langfuse()

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

class ChatMessage(TypedDict):
    message_id: int
    message_type: str
    message_content: str

class QA(TypedDict):
    qa_pair_num : int
    q: ChatMessage
    a: ChatMessage

class CodeStorage(TypedDict):
    message_id: int
    code_id: int
    code_snippet: str
    description: str

class GraphState(TypedDict):
    conversation_id : int
    original_data: List[QA]
    processed_data: List[QA]
    code_docs: List[CodeStorage]


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

    def create_qna_pairs(self) -> List[QA]:
        """
        대화 ID에 해당하는 메시지를 가져와 Q&A 쌍을 생성합니다.

        Returns:
            List[QA]: 질문과 답변 쌍의 리스트.
        """
        # TODO fetch_messages를 사용해 데이터 조회
        chat_ex: List[Message] = fetch_messages(self.conversation_id)
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
                    message_type=chat_ex[i]["message_type"],
                    message_content=chat_ex[i + 1]["message_content"]
                )
                # Q&A 쌍 생성
                qa_pair = QA(
                    qa_pair_num=(i // 2) + 1,
                    q=q_message,
                    a=a_message
                )
                
                # q와 a의 쌍을 formatted_chat_ex에 추가
                formatted_chat_ex.append(qa_pair)
        return formatted_chat_ex

llm  = ChatOpenAI(model='gpt-4o-mini', temperature=0, max_tokens=None,
    timeout=None,
    max_retries=1,
    api_key = openai_api_key
)
# llm = ChatUpstage(model='solar-pro')

# short code description 
def describe_code_with_llm(code_snippet, model):

    short_code_description: Annotated[str, HumanMessage] = langfuse.get_prompt("short_code_description")

    prompt = short_code_description.compile(code_snippet = code_snippet)

    response = model.invoke(prompt)
    
    return response.content.strip()

### TODO LLM 이용하여 코드 스니펫을 추출해야 함.. 
def detemine_code_from_message(model, message_content: str) -> List[str]:
    """ 메시지에서 코드 스니펫을 구분. 
        코드 스니펫 시작과 끝에 ``` 을 붙여 구분
    """
    prompt_template = PromptTemplate(
        template="다음 메시지에서 코드에 해당하는 부분을 백틱으로 감싸 주세요:\n\n{message_content}",
        input_variables=["message_content"]
    )

    prompt = prompt_template.format(
        message_content= message_content)

    # LLM 호출 및 결과 가져오기
    response = model.invoke(prompt)
    print("\n코드 추출\n" + response.content)
    return response.content


def replace_code_with_description(message:ChatMessage, code_docs: List[CodeStorage], model, description_prefix="Code_Snippet") -> str:
    """코드 설명 생성 및 대체."""

    updated_message_content = detemine_code_from_message(model, message["message_content"])
    code_pattern = r"```(.*?)```"
    
    def replace_code(match):
        code_snippet = match.group(1).strip()

        # LLM 호출로 코드 설명 생성
        code_description = describe_code_with_llm(code_snippet=code_snippet, model=model)
        
        code_id = f"{description_prefix}_{len(code_docs) + 1}"
        
        # 코드 저장
        code_docs.append(CodeStorage(
            code_id=code_id,
            code_snippet=code_snippet,
            description=code_description,
            message_id=message["message_id"]
        ))
        
        return f"<-- {code_id}: {code_description} -->"
    
    final_message = re.sub(code_pattern, replace_code, updated_message_content, flags=re.DOTALL)
    return final_message, code_docs

def extract_code_and_replace_with_description(qna_pair:QA, code_docs: List[CodeStorage], model, description_prefix="Code_Snippet"):
    """질문과 답변에서 코드를 추출하고 설명으로 대체."""
    
    question = qna_pair["q"]
    answer = qna_pair["a"]
    # 메세지 에서 코드 추출 및 설명 대체
    question_with_code_replaced = replace_code_with_description(question, code_docs, model, description_prefix)
    answer_with_code_replaced = replace_code_with_description(answer, code_docs, model, description_prefix)

    
    return question_with_code_replaced, answer_with_code_replaced, code_docs


# TODO : 좀더 좋은 prompt. in context example 추가해놓기
def summarize_question_with_llm(question, model):
    question_summarizer : Annotated[str, HumanMessage] = langfuse.get_prompt("question_summarizer")

    prompt = question_summarizer.compile(question=question)

    response = model.invoke(prompt)
    return response.content.strip()

#usage
def process_single_q_and_a(qna_pair_list:List[QA], model):
    code_document = []
    # 5번째 question과 answer for example
    qna_pair = qna_pair_list[5]

    # 요약된 질문을 이용해 코드 추출 및 설명으로 대체
    question_without_code, answer_without_code, code_document = extract_code_and_replace_with_description(qna_pair, code_document, model)

    # 질문 요약하기
    summarized_question = summarize_question_with_llm(question_without_code, model)

    qna_pair_list[5]["q"]["message_content"] = summarized_question
    qna_pair_list[5]["a"]["message_content"] = answer_without_code

    processed_qna_pair = qna_pair_list

    return processed_qna_pair, code_document



#####
qna_creator = QnAPairCreator(CONVERSATION_ID_EXAMPLE_2)
formatted_qna_data = qna_creator.create_qna_pairs()

#usage for example
processed_qna_pair, code_document = process_single_q_and_a(formatted_qna_data, llm)
print("\nProcssed \n", processed_qna_pair[5])
print("\nCode Document (추출된 코드):\n", "\n", code_document)