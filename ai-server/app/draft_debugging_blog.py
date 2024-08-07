#api/draft_debugging_blog.py

from flask import Blueprint, request, jsonify
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

draft_debugging_blog_bp = Blueprint('draft_debugging_blog', __name__)

@draft_debugging_blog_bp.route('/draft-debugging-blog', methods=['POST'])
def draft_debugging_blog():
    data = request.json
    
    # 데이터 형식 확인
    if not isinstance(data, list):
        return jsonify({"error": "Invalid input format, expected a list"}), 400
    
    summarized_questions_answers = data
    
    draft_content = ""

    for item in summarized_questions_answers:
        if not isinstance(item, dict):
            return jsonify({"error": f"Invalid item format, expected a dictionary but got {type(item)}"}), 400
        draft_content += generate_debugging_blog_draft(item)

    response = {
        "input": summarized_questions_answers,
        "output": {
            "draft_content": draft_content
        }
    }
    
    print("Response: ", response)
    return jsonify(response)

def generate_debugging_blog_draft(item):
    prompt = f"""
    Based on the following summarized question and answer, generate a draft blog post for debugging. Include sections for requirements, problem description, situation and solution summary, key code blocks, and key explanations.

    Summarized Question and Answer:
    Frameworks: "{item.get('framework_tags', [])}"
    OS: "{item.get('os_tags', [])}"
    Tech Stack: "{item.get('tech_stack_tags', [])}"
    Requirements: "{item.get('requirements', [])}"
    Situation-Solution: "{item.get('situation_solution', '')}"
    Key Code Blocks: {item.get('key_code_blocks', [])}
    Key Explanations: "{item.get('key_explanations', [])}"

    Output format:
    ### Requirements
    {item.get('requirements', [])}
    
    ### Problem Description
    Describe the problem here.
    
    ### Situation and Solution Summary
    {item.get('situation_solution',[])}
    
    ### Key Code Blocks
    {item.get('key_code_blocks'),[]}
    
    ### Key Explanations
    {item.get('key_explanations'),[]}
    
    Answer:
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that helps to write expert development error fixing and debugging blog draft."},
            {"role": "user", "content": prompt}
        ],        
        max_tokens=1000
    )
    draft_content = response.choices[0].message.content
    
    print("draft_debugging_blog response: ", draft_content)

    
    return draft_content
