from operator import not_
import os
import re
from tabnanny import check
# .env 파일의 환경 변수를 로드합니다.
from certifi import contents
from dotenv import load_dotenv
load_dotenv()

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

class q_and_a(TypedDict):
    q: str
    a: str

class GraphState(TypedDict): 
    preprocessed_conversations: list[q_and_a]
    code_document: dict
    message_to_index_dict: dict
    final_documents: dict
    '''
    Writing 모듈 실행을 위해 필요한 Inputs
    1. preprocessed_conversations -> 서현님 모듈에서 전처리된 QA 세트: list[q_and_a] 
    2. code_document -> 서현님 모듈에서 만든 코드 딕셔너리 dict{'Code_Snippet_1': 'code'}
    3. message_to_index_dict -> 지환님 모듈에서 만든 각 QA 세트에 해당하는 indices: dict['0': [1-1, 1-2, 1-3]] ('0'은 첫 번째 QA 세트를 지칭)
    4. final_documents -> 작성 중인 문서들: dict['1-1': '## 1-1) heading']
    '''

langfuse_handler = CallbackHandler()
langfuse = Langfuse()

import re

##########################평가 관련 함수 정의###############################

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

##########################평가 관련 함수 정의###############################

##########################블로그 초안 작성하는 노드와 관련 함수 정의###############################

model = ChatUpstage(model="solar-pro")

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

def make_final_documents(state: GraphState):
    preprocessed_conversations = state['preprocessed_conversations']
    for i in range(len(preprocessed_conversations)):
        qa = preprocessed_conversations[i]
        indices_for_qa = state['message_to_index_dict'][str(i)]
        #print('QA', i, 'processing...')
        for index in indices_for_qa:
            document = state['final_documents'][index]
            for i in range(10):
                generated_doc, _ = write(model, qa, document)
                updated_doc = remove_after_second_hashes(generated_doc.content)
                if not ('[Q]' in updated_doc) and not ('```' in updated_doc):
                    break
                else:
                    pass
                    #print('[Q] or ``` included error')
            state['final_documents'][index] = updated_doc
            #print('doc', index, '...')
    return state

##########################블로그 초안 작성하는 노드와 관련 함수 정의###############################

##################블로그 초안을 받아 하나의 코드가 하나의 목차에만 들어가게 수정하는 노드와 관련 함수 정의##############

def extract_heading(text):
    start_index = text.find("##")
    if start_index == -1: return ""
    
    end_index = text.find("\n", start_index)
    if end_index == -1: return text[start_index:].strip()
    
    return text[start_index+2:end_index].strip()

def find_indices_and_snippet_with_code_id(code_id: str, doc_dict):
    #입력 code id: Code_Snippet_1
    #code snippet이 들어 있는 목차의 1. 인덱스 리스트, 2. 제목 리스트, 3. 설명을 포함한 전체 code snippet를 반환
    pattern = fr"<-- {code_id}: .*? -->"
    indices_list = []
    heading_list = []
    whole_snippet = 'None'
    for key in doc_dict:
        text = doc_dict[key]
        match = re.search(pattern, text)
        if match:
            heading = extract_heading(text)
            indices_list.append(key)
            heading_list.append(heading)
            whole_snippet = match.group().strip()
    return indices_list, heading_list, whole_snippet

def make_heading_list_for_prompt(heading_list):
    text = ''
    for heading in heading_list:
        text = text + heading + '\n'
    return text[:-1]

def document_refinement(state: GraphState):
    # 그래프 스테이트에서 code_list를 받아오도록 변경, 아래 코드 삭제 요함
    # code_list = list(loaded_data['EXAMPLE9']['code_document'].keys())
    code_list = list(state['code_document'].keys())
    document_refinement_1 = langfuse.get_prompt("document_refinement_1")
    document_refinement_2 = langfuse.get_prompt("document_refinement_2")
    for code_id in code_list:
        #print(code_id, 'processing...')
        indices_list, heading_list, whole_snippet = find_indices_and_snippet_with_code_id(code_id, state['final_documents'])
        if len(indices_list) < 2:
            #print('no founded')
            continue        
        indices = make_heading_list_for_prompt(heading_list)

        prompt = document_refinement_1.compile(code_snippet=whole_snippet, indices=indices)
        for i in range(10):
            selected = model.invoke(prompt)
            selected = selected.content
            if selected in indices_list:
                break
            else:
                pass
                #print('selecting error')
        for index in indices_list:
            if selected != index:
                #print(index, '...')
                doc = state['final_documents'][index]
                prompt = document_refinement_2.compile(code_snippet=whole_snippet, doc=doc)
                updated = model.invoke(prompt)
                state['final_documents'][index] = updated.content
    return state

##################블로그 초안을 받아 하나의 코드가 하나의 목차에만 들어가게 수정하는 노드와 관련 함수 정의##############

######################작성한 블로그의 코드 스니펫을 원래 코드로 교체 및 헤딩 표시(#) 지우기######################

def replace_code_snippets(document, snippets_dict):
    # Code_Snippet_1 및 Code_Snippet_2 키를 사용해 대체할 패턴을 찾음
    for snippet_key in snippets_dict:
        # 대체할 패턴을 정의
        pattern = f"<-- {snippet_key}:.*?-->"
        # document 내에서 해당 placeholder를 딕셔너리의 value로 대체
        document = re.sub(pattern, "```" + snippets_dict[snippet_key] + "```\n", document)
    
    return document

def make_blog(state: GraphState):
    for index in state['final_documents']:
        text = state['final_documents'][index]
        t = replace_code_snippets(text, state['code_document'])
        t = t.lstrip('#')
        t = t.lstrip(' ')
        state['final_documents'][index] = t
        #print(t, end='\n\n')
    return state

######################작성한 블로그의 코드 스니펫을 원래 코드로 교체 및 헤딩 표시(#) 지우기######################

##########################그래프 내의 요소(node, edge)들을 정의###############################3
# 메모리를 정의
memory = MemorySaver() 

# 새로운 graph 정의
writer_graph = StateGraph(GraphState)

# 사용할 node를 정의(다른 단계를 수행할 node를 제작하고 싶다면 여기에 node를 추가)
writer_graph.add_node("블로그 초안 작성", make_final_documents)
writer_graph.add_node("블로그 글 다듬기", document_refinement)
writer_graph.add_node("블로그 글 후처리", make_blog)


# 그래프 시작점정의
writer_graph.set_entry_point("블로그 초안 작성")

# Define Edges
writer_graph.add_edge('블로그 초안 작성', "블로그 글 다듬기")
writer_graph.add_edge("블로그 글 다듬기", "블로그 글 후처리")
##########################그래프 내의 요소(node, edge)들을 정의###############################3

# 그래프를 컴파일
compiled_graph = writer_graph.compile(checkpointer=memory)

# 아래코드 배포시에 주석처리
################ 아래는 example9 데이터가 들어있는 json 파일에서 데이터를 불러와 테스트해보는 코드 ################

# import json

# with open('data_for_writing.json', 'r', encoding='utf-8') as json_file:
#     loaded_data = json.load(json_file)


    
# ##########################그래프 실행###############################


# # 들어갈 graph_state를 정의
# graph_state = GraphState(
#     preprocessed_conversations=loaded_data['EXAMPLE9']['preprocessed_conversations'],
#     code_document=loaded_data['EXAMPLE9']['code_document'],
#     message_to_index_dict=loaded_data['EXAMPLE9']['message_to_index_dict'],
#     final_documents=loaded_data['EXAMPLE9']['final_documents']
# )

# # 그래프를 실행
# final_state = compiled_graph.invoke(
#     graph_state, 
#     config={
#         "configurable": {"thread_id": 42}, 
#         "callbacks": [langfuse_handler]}
# )
##########################그래프 실행###############################

# # eval
# precision, recall = overall_precision_recall(graph_state['final_documents'], loaded_data['EXAMPLE9']['GT_document'])
# print(f"Overall Precision: {precision:.2f}")
# print(f"Overall Recall: {recall:.2f}")

# 만든 최종 그래프 출력
# for text in list(final_state['final_documents'].values()):
#     print(text, end='\n\n')