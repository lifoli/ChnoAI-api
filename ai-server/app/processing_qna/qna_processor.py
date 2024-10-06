import os
import re
import time

from dotenv import load_dotenv
from typing import Annotated, List, Tuple
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
from app.processing_qna.evaluation_utils import EvaluationUtils
from app.processing_qna.evaluate_score import evaluate_processed_answer, evaluate_coherence  

from app.type import CodeStorage, QA, QAProcessorGraphState as GraphState
from app.constants import CONVERSATION_ID
from app.processing_qna.processed_qna_db import ProcessedQnADBHandler

langfuse_handler = CallbackHandler()
langfuse = Langfuse()

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")


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
    
    def process_qna_pair(self, graph_state:GraphState, MAX_ITERATION:int=3) -> Tuple[List[QA], List[CodeStorage]]:
        """Q&A 쌍을 처리하고 코드 스니펫을 설명으로 대체하며, 최종 Q&A 쌍과 코드 문서 리스트를 반환"""
        for qna_pair in tqdm(self.qna_list, desc="Processing Q&A Pairs", unit="pair"):
            graph_state["processing_data"] = qna_pair

            question = qna_pair["q"]
            answer = qna_pair["a"]

            coherent_score = 0
            best_summarized_question = "" 
            for i in range(MAX_ITERATION):
                summarized_question = self.summarize_question_with_llm(question)
                coherence_result = evaluate_coherence(question, summarized_question)
                
                current_score  = coherence_result.get("coherence_score")
                coherent_reason = coherence_result.get("reason")
                
                print(f"Iteration {i + 1}/{MAX_ITERATION}")
                print(f"Coherent score: {current_score }")
                print(f"Coherent reason: {coherent_reason}")

                if current_score > coherent_score:
                    coherent_score = current_score
                    best_summarized_question = summarized_question 
                
                if coherent_score >= 0.8:
                    print("Coherent score 기준점을 넘음. 반복 종료.")
                    break
                else:
                    print("Coherent score 기준점을 넘지 못하여 다시 summarize 실행 중...")
            
            # coherent_score >= 0.8 이면 summarized_question 반영 
            graph_state["processing_data"]["q"] = best_summarized_question


            recall_score = 0
            best_processed_answer = ""
            for i in range(MAX_ITERATION):
                processed_answer = self.backtick_process_with_llm(answer)
                evaluation_results = evaluate_processed_answer(answer, processed_answer)
                
                current_recall_score = evaluation_results.get("recall")
                print(f"Iteration {i + 1}/{MAX_ITERATION}")
                print(f"Recall score: {current_recall_score}")

                if current_recall_score > recall_score:
                    recall_score = current_recall_score
                    best_processed_answer = processed_answer  
                
                if recall_score >= 0.90:
                    print("Recall score 기준점을 넘음. 반복 종료.")
                    break
                else:
                    print("Recall score 기준점을 넘지 못하여 다시 backtick 처리 실행 중...")

            graph_state["processing_data"]["a"] = best_processed_answer
            
            question_without_code, answer_without_code = self.extract_code_and_replace_with_description(summarized_question, processed_answer)            
            graph_state["code_documents"] = self.code_documents
            qna_pair["q"] = question_without_code
            qna_pair["a"] = answer_without_code

            graph_state["processing_data"] = qna_pair
            graph_state["processed_conversations"].append(qna_pair)

        return self.qna_list, self.code_documents
    
    
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



def run_pipeline(model_name, conversation_id) :
    # 평가시에 gpt-4o-mini 모델 사용
    if model_name == "gpt-4o-mini":
        model= ChatOpenAI(model='gpt-4o-mini', temperature=0, max_tokens=None,
            timeout=None,
            max_retries=1,
            api_key = openai_api_key
        )
    else : model = ChatUpstage(model='solar-pro')

    evaulation_utils = EvaluationUtils()
    conversation_data = evaulation_utils.get_messages_by_conversation_id(conversation_id)
    qna_processor = QnAProcessor(conversation_data, model)

    init_graph_state = GraphState(
        not_processed_conversations=conversation_data,
        processing_data=None,
        processed_conversations=[],
        code_documents=[]
    )

    # Start the timer
    start_time = time.time()

    # Process Q&A pairs with a progress bar
    processed_qna_list, code_documents = qna_processor.process_qna_pair(graph_state=init_graph_state)

    # Stop the timer
    end_time = time.time()

    # Calculate elapsed time
    elapsed_time = end_time - start_time
    print(f"Execution Time: {elapsed_time:.2f} seconds")

    return processed_qna_list, code_documents



if __name__ == "__main__":
    model_name = "solar-pro"

    conversation_id = CONVERSATION_ID["EXAMPLE_1"]
    processed_qna_list, code_documents = run_pipeline(model_name, conversation_id)

    # Database 삽입 및 조회를 위한 인스턴스 생성
    qna_db_handler = ProcessedQnADBHandler()

    # Database에 데이터 삽입
    qna_db_handler.insert_qna_and_code(
        conversation_id=conversation_id,
        model = model_name,
        processed_content=processed_qna_list,
        code_document=code_documents
    )


    # Database에서 데이터 조회
    processed_qna, code_document = qna_db_handler.get_qna_and_code(conversation_id=conversation_id, model=model_name)
    
    print(f"processed_qna\n {processed_qna} \n")
    print(f"code_document\n {code_document} \n")
