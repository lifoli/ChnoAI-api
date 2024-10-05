
import os
import requests
from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from langchain_upstage import ChatUpstage, UpstageEmbeddings
from langchain_core.messages import HumanMessage
from typing import List, TypedDict, Annotated
import numpy as np
from evaluation_utils import EvaluationUtils

load_dotenv()

# Initialize Langfuse and models
langfuse_handler = CallbackHandler()
langfuse = Langfuse()
model = ChatUpstage(model="solar-pro")
passage_embeddings = UpstageEmbeddings(model="solar-embedding-1-large-passage")
evaluation_utils = EvaluationUtils()

API_URL = "https://api.upstage.ai/v1/solar/chat/completions"
HEADERS = {"Authorization": f"Bearer {os.getenv('UPSTAGE_API_KEY')}"}

class q_and_a(TypedDict):
    q: str
    a: str

def contains_korean(text: str) -> bool:
    return any('가' <= char <= '힣' for char in text)

def embed_text(text: str, embedding_model):
    return embedding_model.embed_documents([text])

def calculate_similarity(embedded_query, embedded_documents):
    embedded_query = np.array(embedded_query)
    embedded_documents = np.array(embedded_documents)
    similarity = np.dot(embedded_query, embedded_documents.T)
    return np.squeeze(similarity)

def translate_text_with_api(text: str, model: str) -> str:

    data = {
        "model": model,
        "messages": [{"role": "user", "content": text}],
        "stream": False
    }

    response = requests.post(API_URL, headers=HEADERS, json=data)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"Translation API error: {response.status_code}, {response.text}")
        return text

def translate_q_and_a(conversation_list: List[q_and_a], translation_model: str, passage_embeddings):
    translated_conversations = []
    
    for conversation in conversation_list:
        question = conversation['q']
        answer = conversation['a']

        # Translate the question if it contains Korean
        if contains_korean(question):
            attempts = 0  
            similarity_q = 0.0
            translated_q = question

            while (similarity_q < 0.5 or contains_korean(translated_q)) and attempts < 5:
                translated_q = translate_text_with_api(question, translation_model)

                # Calculate similarity between original and translated question
                embedded_query = passage_embeddings.embed_documents([question])
                embedded_translated_q = passage_embeddings.embed_documents([translated_q])
                similarity_q = calculate_similarity(embedded_query, embedded_translated_q)
                #print(f"질문 번역 유사도 (시도 {attempts + 1}): {similarity_q:.4f}")
                #print(f"질문 번역에 한국어 포함 여부: {contains_korean(translated_q)}")
                attempts += 1

            if attempts == 5:
                #print(f"최대 재시도 횟수 도달. 질문 최종 번역: {translated_q}")
        else:
            translated_q = question  # If the question is already in English, no translation needed

        # Translate the answer if it contains Korean
        if contains_korean(answer):
            attempts = 0 
            similarity_a = 0.0
            translated_a = answer

            while (similarity_a < 0.5 or contains_korean(translated_a)) and attempts < 5:
                translated_a = translate_text_with_api(answer, translation_model)

                # Calculate similarity between original and translated answer
                embedded_answer = passage_embeddings.embed_documents([answer])
                embedded_translated_a = passage_embeddings.embed_documents([translated_a])
                similarity_a = calculate_similarity(embedded_answer, embedded_translated_a)
                #print(f"답변 번역 유사도 (시도 {attempts + 1}): {similarity_a:.4f}")
                #print(f"답변 번역에 한국어 포함 여부: {contains_korean(translated_a)}")
                attempts += 1

            if attempts == 5:
                #print(f"최대 재시도 횟수 도달. 답변 최종 번역: {translated_a}")
        else:
            translated_a = answer  # If the answer is already in English, no translation needed

        translated_conversations.append(q_and_a(q=translated_q, a=translated_a))

    return translated_conversations

if __name__ == "__main__":
    EXAMPLE1_CONVERSATION_ID = 162
    try:
        conversation_data = evaluation_utils.get_messages_by_conversation_id(EXAMPLE1_CONVERSATION_ID)
    except Exception as e:
        print(f"Error fetching conversation data: {e}")
        conversation_data = []

    translated_result = translate_q_and_a(conversation_data, "solar-1-mini-translate-koen", passage_embeddings)

    for idx, conversation in enumerate(translated_result):
        print(f"번역된 질문 {idx+1}: {conversation['q']}")
        print(f"번역된 답변 {idx+1}: {conversation['a']}")
