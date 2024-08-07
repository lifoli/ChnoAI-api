#api/categorize_questions.py

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

categorize_questions_bp = Blueprint('categorize_questions', __name__)

@categorize_questions_bp.route('/categorize-questions', methods=['POST'])
def categorize_questions():
    data = request.json
    conversation_id = data.get('conversation_id')
    questions = data.get('questions')

    categorized_questions = []

    for question in questions:
        sequence_number = question.get('sequence_number')
        question_text = question.get('question_text')

        categorized_question = categorize_question(question_text)
        categorized_question.update({
            "sequence_number": sequence_number,
            "question_text": question_text
        })

        categorized_questions.append(categorized_question)

    response = {
        "categorized_questions": categorized_questions
    }
    
    print("categorize_questions response: ", response)

    return jsonify(response)

def categorize_question(question_text):
    prompt = f"""
    Analyze the following question and categorize it by extracting OS tags, tech stack tags, language tags, framework tags, question type (implementation/error/explanation), and requirements:

    Question: "{question_text}"

    Output format(JSON):
    {{
        "os_tags": [list of OS tags],
        "tech_stack_tags": [list of tech stack tags],
        "language_tags": [list of language tags],
        "framework_tags": [list of framework tags],
        "question_type": [question type],
        "requirements": [extracted requirements]
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that helps to categorize questions and should output a valid JSON object."},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" },
        max_tokens=150
    )
    
    result = response.choices[0].message.content
    
    # Ensure the result is valid JSON
    try:
        json_result = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise ValueError(f"Failed to parse JSON response: {result}")
    
    return json_result

def parse_result(result):
    return result  # 이미 JSON 객체이므로 그대로 반환
