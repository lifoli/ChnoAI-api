import os
import re
import time

from dotenv import load_dotenv
from typing import Annotated, TypedDict, List, Tuple, Optional
from tqdm import tqdm

# langchin
from langchain_upstage import ChatUpstage
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# langgraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode

# langfuse
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

# 평가 함수 불러오기
from evaluation_utils import EvaluationUtils
from evaluate_score import evaluate_processed_answer, evaluate_coherence  

langfuse_handler = CallbackHandler()
langfuse = Langfuse()

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

class CodeStorage(TypedDict):
    code_description: str
    code_index:str
    code_snippet: str

class QA(TypedDict):
    q: str
    a: str

class GraphState(TypedDict):
    processing_data: Optional[QA]                 # 현재 처리 중인 Q&A pair
    not_processed_conversations: List[QA]         # 아직 처리되지 않은 Q&A pair 리스트
    processed_conversations: List[QA]             # 처리된 Q&A pair 리스트
    code_documents: List[CodeStorage]             # 처리된 코드 문서 정보 리스트



class QnAProcessor:
    """
    QnAProcessor 클래스는 Q&A 쌍을 처리하는 데 사용됩니다.
    이 클래스는 질문과 답변에서 코드 스니펫을 추출하고, 해당 코드를 LLM을 사용하여 설명으로 대체합니다.

    Attributes:
    - pair_list (List[QA]): 처리할 Q&A 쌍의 리스트.
    - model: LLM 모델 인스턴스.
    - code_documents (List[CodeStorage]): 각 Q&A 쌍에 대한 코드 문서 정보를 저장하는 리스트.

    Methods:
    - process_qna_pair(): Q&A 쌍을 처리하고 코드 스니펫을 설명으로 대체하며, 최종 Q&A 쌍과 코드 문서 리스트를 반환합니다.
    - extract_code_and_replace_with_description(qna_pair): 질문과 답변에서 코드를 추출하고 설명으로 대체합니다.
    - backtick_process_with_llm(answer): 답변 내 코드에 백틱(```)을 추가하여 명확하게 표시합니다.
    - describe_code_with_llm(code_snippet): LLM을 사용하여 주어진 코드 스니펫에 대한 설명을 생성합니다.
    - summarize_question_with_llm(question): LLM을 사용하여 주어진 질문을 요약합니다.
    """

    def __init__(self, qna_list: List[QA], model) -> None:
        self.qna_list = qna_list
        self.model = model
        self.code_documents: List[CodeStorage] = []

    
    def process_qna_pair(self, graph_state:GraphState) -> GraphState:
        """Q&A 쌍을 처리하고 코드 스니펫을 설명으로 대체하며, 최종 Q&A 쌍과 코드 문서 리스트를 반환"""
        for index, qna_pair in tqdm(self.qna_list, desc="Processing Q&A Pairs", unit="pair"):
            graph_state["processing_data"] = qna_pair

            question = qna_pair["q"]
            answer = qna_pair["a"]

            coherent_score = 0
            while coherent_score < 0.8:
                summarized_question = self.summarize_question_with_llm(question)
                coherence_result = evaluate_coherence(question, summarized_question)
                coherent_score = coherence_result.get("coherence_score")
                coherent_reason = coherence_result.get("reason")
                print("coherent score : ", coherent_score)
                print("coherent result : ", coherent_reason)
                if coherent_score < 0.8:
                    print("Coherent score 기준점을 넘지 못하여 다시 summarize 실행 중...")
            
            # coherent_score >= 0.8 이면 summarized_question 반영 
            graph_state["processing_data"]["q"] = summarized_question

            recall_score = 0
            processed_answer = ""
            while recall_score < 0.95:
                processed_answer = self.backtick_process_with_llm(answer)
                evaluation_results = evaluate_processed_answer(answer, processed_answer)
                recall_score = evaluation_results.get("recall")
                print("recall score : ", recall_score)

                if recall_score < 0.95:
                    print("Recall score 기준점을 넘지 못하여 다시 backtick 처리 실행 중...")

            print("\nBacktick Processing Evaluation Results:\n", evaluation_results)
            graph_state["processing_data"]["a"] = processed_answer
            
            question_without_code, answer_without_code = self.extract_code_and_replace_with_description(summarized_question, processed_answer)            
            graph_state["code_documents"] = self.code_documents
            qna_pair["q"] = question_without_code
            qna_pair["a"] = answer_without_code

            graph_state["processing_data"] = qna_pair
            self.qna_list[index] = qna_pair
            graph_state["processed_conversations"].append(qna_pair)

        return graph_state
    
    
    def extract_code_and_replace_with_description(self, question:str, answer:str, description_prefix="Code_Snippet") -> Tuple[str, str]:
        """질문과 답변에서 코드 스니펫을 추출하고 설명으로 대체"""

        code_pattern = r"```(.*?)```"
        code_index_counter = len(self.code_documents)

        def _replace_code_with_placeholder(match):
            nonlocal code_index_counter
            code_snippet = match.group(1).strip()
            # LLM 호출로 코드 설명 생성
            code_description = self.describe_code_with_llm(code_snippet=code_snippet)
            code_index_counter +=1
            code_index = f"{description_prefix}_{code_index_counter}"
            
            placeholder = f"{code_index}: {code_description}"

            # 코드 저장
            code_storage = CodeStorage(
                code_snippet=code_snippet,
                code_index=code_index,
                code_description=code_description,
            )
            self.code_documents.append(code_storage)

            return f"<-- {placeholder} -->"

        question_without_code = re.sub(code_pattern, _replace_code_with_placeholder, question, flags=re.DOTALL)
        answer_without_code = re.sub(code_pattern, _replace_code_with_placeholder, answer, flags=re.DOTALL)
        return question_without_code, answer_without_code
    
    def backtick_process_with_llm(self, answer):
        """LLM을 사용하여 코드에 백틱 추가."""
        backtick_processor: Annotated[str, HumanMessage] = langfuse.get_prompt("backtick_processor")
        prompt = backtick_processor.compile(answer=answer)
        response = self.model.invoke(prompt)
        return response.content.strip()


    def describe_code_with_llm(self, code_snippet:str) -> str:
        """LLM을 사용하여 코드 설명 생성."""
        short_code_description: Annotated[str, HumanMessage] = langfuse.get_prompt("short_code_description")
        prompt = short_code_description.compile(code_snippet=code_snippet)
        response = self.model.invoke(prompt)
        return response.content.strip()
    
    
    def summarize_question_with_llm(self, question):
        """LLM을 사용하여 질문 요약."""
        question_summarizer: Annotated[str, HumanMessage] = langfuse.get_prompt("question_summarizer")
        prompt = question_summarizer.compile(question=question)
        response = self.model.invoke(prompt)
        return response.content.strip()




#####
EXAMPLE1_CONVERSATION_ID = 146
EXAMPLE3_CONVERSATION_ID = 170
evaulation_utils = EvaluationUtils()
conversation_data = evaulation_utils.get_messages_by_conversation_id(EXAMPLE3_CONVERSATION_ID)

#usage for example
llm  = ChatOpenAI(model='gpt-4o-mini', temperature=0, max_tokens=None,
    timeout=None,
    max_retries=1,
    api_key = openai_api_key
)
# llm = ChatUpstage(model='solar-pro')

qna_processor = QnAProcessor(conversation_data, llm)

# Start the timer
start_time = time.time()

graph_state = GraphState(
    not_processed_conversations=conversation_data,
    processing_data=None,
    processed_conversations=[],
    code_documents=[]
)


# Process Q&A pairs with a progress bar
processed_graph_state = qna_processor.process_qna_pair(graph_state)

# Stop the timer
end_time = time.time()

# Calculate elapsed time
elapsed_time = end_time - start_time
print(f"Execution Time: {elapsed_time:.2f} seconds")



