# from langchain import LangChain
from openai import OpenAI
client = OpenAI()
from dotenv import load_dotenv
import os
import json

# .env 파일의 환경 변수 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
openai_api_key = os.getenv('OPENAI_API_KEY')

# OpenAI API 키 설정
client.api_key = openai_api_key

from flask import Blueprint, request, jsonify

summarize_answers_bp = Blueprint('summarize_answers', __name__)

@summarize_answers_bp.route('/summarize-answers', methods=['POST'])
def summarize_answers():
    data = request.json
    categorized_questions = data.get('categorized_questions')
    answers = data.get('answers')
    
    # 답변을 sequence_number 기준으로 매핑
    answers_dict = {answer['sequence_number']: answer['question_text'] for answer in answers}
    
    summarized_answers = []

    for question in categorized_questions:
        sequence_number = question.get('sequence_number')
        answer_text = answers_dict.get(sequence_number, '')

        summarized_answer = summarize_answer(question, answer_text)
        flattened_answer = ([{
            **summarized_answer,
            "sequence_number": sequence_number,
            "question_text": question.get('question_text'),
            "question_type": question.get('question_type', []),
            "requirements": question.get('requirements', []),
            "framework_tags": question.get('framework_tags', []),
            "language_tags": question.get('language_tags', []),
            "os_tags": question.get('os_tags', []),
            "tech_stack_tags": question.get('tech_stack_tags', [])
        }])

        summarized_answers.append(flattened_answer)

    response = {
        "summarized_answers": summarized_answers
    }
    
    print("summarize_answers response: ", response)

    

    return jsonify(response)

def summarize_answer(question, answer_text):
    prompt = f"""
    Summarize the following answer to extract the essential "situation-solution summary", "core code blocks", and "key explanations". Ensure the summary is concise and only includes the most critical information. The core code blocks should be minimal, including only the essential parts necessary for understanding the solution.

    Question: "{question['question_text']}"
    Answer: "{answer_text}"

    Output format(JSON):
    {{
        "situation_solution": "Concise summary of the situation and solution",
        "key_code_blocks": ["Minimal essential code block 1", "Minimal essential code block 2"],
        "key_explanations": ["Key explanation 1", "Key explanation 2"]
    }}

    Answer:

    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that helps to analyze and summarize the ChatGPT generated answers into 'the situation and the provided solution', find the 'essential code blocks for the requirements' and 'key explanations from provided answers' by ChatGPT."},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" },        
        max_tokens=500
    )
    result = response.choices[0].message.content
    
    # Ensure the result is valid JSON
    try:
        json_result = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise ValueError(f"Failed to parse JSON response: {result}")
    
    return json_result
