import os
import re
from dotenv import load_dotenv
from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from typing import Annotated, TypedDict
from evaluation_utils import EvaluationUtils
from evaluate_score import evaluate_processed_answer, evaluate_summarization, evaluate_coherence  # 평가 함수 불러오기

load_dotenv()

langfuse_handler = CallbackHandler()
langfuse = Langfuse()
model = ChatUpstage(model="solar-pro")

EXAMPLE1_CONVERSATION_ID = 146 

evaluation_utils = EvaluationUtils()

class q_and_a(TypedDict):
    q: str
    a: str

class GraphState(TypedDict):
    not_processed_conversations: list[q_and_a]
    processed_conversations: list[q_and_a]
    result: str  

def describe_code_with_llm(code_snippet, model):
    short_code_description: Annotated[str, HumanMessage] = langfuse.get_prompt("short_code_description")
    prompt = short_code_description.compile(code_snippet=code_snippet)
    response = model.invoke(prompt)
    return response.content.strip()

def summarize_question_with_llm(question, model):
    question_summarizer: Annotated[str, HumanMessage] = langfuse.get_prompt("question_summarizer")
    prompt = question_summarizer.compile(question=question)
    response = model.invoke(prompt)
    return response.content.strip()

def backtick_process_with_llm(answer, model):
    backtick_processor: Annotated[str, HumanMessage] = langfuse.get_prompt("backtick_processor")
    prompt = backtick_processor.compile(answer=answer)
    response = model.invoke(prompt)
    return response.content.strip()

def extract_code_and_replace_with_description(question, answer, code_storage, model, description_prefix="Code_Snippet"):
    code_pattern = r"```(.*?)```" 
    def replace_code_with_placeholder(match):
        code_snippet = match.group(1).strip()
        code_description = describe_code_with_llm(code_snippet, model)
        code_id = f"{description_prefix}_{len(code_storage) + 1}"
        placeholder = f"<-- {code_id}: {code_description} -->"
        code_storage.append(f"{code_id}:\n{code_snippet}\n")
        return placeholder
    question_without_code = re.sub(code_pattern, replace_code_with_placeholder, question, flags=re.DOTALL)
    answer_without_code = re.sub(code_pattern, replace_code_with_placeholder, answer, flags=re.DOTALL)
    result = f"Me: {question_without_code}\nChatGPT: {answer_without_code}"
    return result, code_storage
def process_single_q_and_a(state: GraphState, model):
    code_document = []
    original_question = state["not_processed_conversations"][1]["q"]
    answer = state["not_processed_conversations"][1]["a"]

    #print("Original Question:", original_question)
    summarized_question = summarize_question_with_llm(original_question, model)
    #print("Summarized Question:", summarized_question)

    # SummarizationMetric 실행
    evaluate_coherence(original_question, summarized_question)
    evaluate_summarization(original_question, summarized_question)

    processed_answer = backtick_process_with_llm(answer, model)
    result, code_document = extract_code_and_replace_with_description(summarized_question, processed_answer, code_document, model)

    evaluation_results = evaluate_processed_answer(answer, processed_answer)
    
    #print("Result (with code placeholders):\n", result)
    print("\nExtracted Code:\n", "\n".join(code_document))
    print("\nBacktick Processing Evaluation Results:\n", evaluation_results)

try:
    conversation_data = evaluation_utils.get_messages_by_conversation_id(EXAMPLE1_CONVERSATION_ID)
except Exception as e:
    print(f"Error fetching conversation data: {e}")
    conversation_data = []

graph_state = GraphState(
    not_processed_conversations=conversation_data,
    processed_conversations=[],
    result=""
)

# Process Q&A example
process_single_q_and_a(graph_state, model)
