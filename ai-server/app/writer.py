from operator import not_
import os
import re
from tabnanny import check
# .env 파일의 환경 변수를 로드합니다.
from certifi import contents
from dotenv import load_dotenv
load_dotenv()
import json

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

from evaluation_utils import EvaluationUtils
#from question_compressor import process_single_q_and_a

#################################################################
# example1
EXAMPLE1_CONVERSATION_ID = 146

# example5
EXAMPLE5_CONVERSATION_ID = 162

# example6
EXAMPLE6_CONVERSATION_ID = 153
#################################################################

evaluation_utils = EvaluationUtils()
langfuse_handler = CallbackHandler()
langfuse = Langfuse()
model = ChatUpstage(model="solar-pro")

class q_and_a(TypedDict):
    q: str
    a: str

class GraphState(TypedDict):
    not_processed_conversations: list[q_and_a]
    processed_conversations: list[q_and_a]
    result: str  
    preprocessed_conversations: list[q_and_a]
    code_document: dict
    message_to_index_dict: dict
    final_documents: dict

    '''
    Writing 모듈 실행을 위해 필요한 Inputs
    1. preprocessed QA sets: list[q_and_a] 
    2. code_document: list
    3. 각각의 QA에 해당하는 indices: dict[message_id: index_list]
    4. 작성 중인 문서들: dict[index: content]
    '''

# 이하는 evaluation functions

# code_snippet 찾는 함수
def find_code_snippets(text):
    pattern = r"<-- Code_Snippet_\d+: .*? -->"
    return re.findall(pattern, text)

# precision 및 recall 계산 함수
def calculate_precision_recall(true_positive, generated_total, gt_total):
    # Precision = TP / (TP + FP)
    precision = true_positive / generated_total if generated_total else 0
    
    # Recall = TP / (TP + FN)
    recall = true_positive / gt_total if gt_total else 0
    
    return precision, recall

# 전체 문서에 대해 목차별로 true_positive 계산 후 전체 precision/recall 계산
def overall_precision_recall(generated_doc, gt_doc):
    total_true_positive = 0
    total_generated_snippets = 0
    total_gt_snippets = 0
    
    for section in generated_doc:
        # generated_doc과 gt_doc에서 목차에 해당하는 내용을 추출
        generated_content = generated_doc[section]
        gt_content = gt_doc[section]
        
        # 각각의 문서에서 code_snippet 추출
        generated_snippets = find_code_snippets(generated_content)
        gt_snippets = find_code_snippets(gt_content)
        
        # 각 목차에서 true_positive 계산
        true_positive = len(set(generated_snippets) & set(gt_snippets))
        
        # 총 true_positive, generated_snippets, gt_snippets 합산
        total_true_positive += true_positive
        total_generated_snippets += len(generated_snippets)
        total_gt_snippets += len(gt_snippets)
    
    # 전체 precision/recall 계산
    precision, recall = calculate_precision_recall(total_true_positive, total_generated_snippets, total_gt_snippets)
    
    return precision, recall

# 이하는 writer 모듈 동작을 위한 functions

def write(model, q_and_a, document):
    writing_prompt = langfuse.get_prompt("writing_prompt")
    prompt = writing_prompt.compile(q=q_and_a['q'], a=q_and_a['a'], document=document)
    updated_doc = model.invoke(prompt)
    return updated_doc, prompt

def remove_after_second_hashes(text):
    # '##'를 기준으로 문자열을 나누기
    parts = text.split('##')
    
    # 두 번째 '##' 이후의 내용 삭제
    if len(parts) > 2:
        return '## ' + parts[1].strip()  # '##' 포함 첫 번째 부분만 반환
    return text  # '##'가 두 번 이상 없을 때는 원래 문자열 반환

def make_final_documents(state: GraphState, model):
    preprocessed_conversations = state['preprocessed_conversations']
    for i in range(len(preprocessed_conversations)):
        qa = preprocessed_conversations[i]
        indices_for_qa = state['message_to_index_dict'][str(i)]
        #print('QA', i, 'processing...')
        for index in indices_for_qa:
            document = state['final_documents'][index]
            generated_doc, _ = write(model, qa, document)
            updated_doc = remove_after_second_hashes(generated_doc.content)
            state['final_documents'][index] = updated_doc
            #print('doc', index, '...')
    return 0

# 아래는 example9 데이터가 들어있는 json 파일에서 데이터를 불러와 테스트해보는 코드

with open('data_for_writing.json', 'r') as json_file:
    loaded_data = json.load(json_file)

graph_state = GraphState(
    not_processed_conversations=loaded_data['EXAMPLE9']['conversations'],
    processed_conversations=None,
    result=None,
    preprocessed_conversations=loaded_data['EXAMPLE9']['preprocessed_conversations'],
    code_document=loaded_data['EXAMPLE9']['code_document'],
    message_to_index_dict=loaded_data['EXAMPLE9']['message_to_index_dict'],
    final_documents=loaded_data['EXAMPLE9']['final_documents']
)

# write
make_final_documents(graph_state, model)

# eval
precision, recall = overall_precision_recall(graph_state['final_documents'], loaded_data['EXAMPLE9']['GT_document'])
print(f"Overall Precision: {precision:.2f}")
print(f"Overall Recall: {recall:.2f}")