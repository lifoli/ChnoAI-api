#api/review_and_finalize_blog.py

from flask import Blueprint, request, jsonify
from openai import OpenAI
client = OpenAI()
from dotenv import load_dotenv
import os
import json
import re

# .env 파일의 환경 변수 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
openai_api_key = os.getenv('OPENAI_API_KEY')

# OpenAI API 키 설정
client.api_key = openai_api_key

review_and_finalize_blog_bp = Blueprint('review_and_finalize_blog', __name__)

@review_and_finalize_blog_bp.route('/review-and-finalize-blog', methods=['POST'])
def review_and_finalize_blog():
    data = request.json
    drafts = data.get('drafts')

    title, content, question_types, requirements, framework_tags, language_tags, os_tags, tech_stack_tags = generate_final_blog(drafts)

    response = {
        "input": drafts,
        "output": {
            "title": title,
            "content": content,
            "question_type": question_types,
            "requirements": requirements,
            "framework_tags": framework_tags,
            "language_tags": language_tags,
            "os_tags": os_tags,
            "tech_stack_tags": tech_stack_tags
        }
    }
    
    return jsonify(response)

def generate_final_blog(drafts):
    draft_texts = "\n\n".join(draft['output']['draft_content'] for draft in drafts)

    # 각 항목을 수집하기 위해 리스트 초기화
    question_types = []
    requirements = []
    framework_tags = []
    language_tags = []
    os_tags = []
    tech_stack_tags = []

    for draft in drafts:
        input_data = draft.get('input', [])
        for item in input_data:
            if 'question_type' in item:
                question_types.extend(item['question_type'])
            if 'requirements' in item:
                requirements.extend(item['requirements'])
            if 'framework_tags' in item:
                framework_tags.extend(item['framework_tags'])
            if 'language_tags' in item:
                language_tags.extend(item['language_tags'])
            if 'os_tags' in item:
                os_tags.extend(item['os_tags'])
            if 'tech_stack_tags' in item:
                tech_stack_tags.extend(item['tech_stack_tags'])

    prompt = f"""
    Review the following blog drafts and combine them into a single cohesive and polished blog post. Ensure that the final content flows well, maintains a consistent tone, and covers all the points mentioned in the drafts. Format the content using Markdown and code blocks as necessary to ensure it renders well on Notion. Keep in mind that this post is likely about implementing a specific feature, fixing a bug, or explaining a concept, rather than covering the entire project. The author is a developer aiming to document and share knowledge and insights gained during the development process.

    Blog Drafts:
    {draft_texts}

    Output format(JSON):
    {{
        "title": [Generated title],
        "content": [Final combined and polished blog post in Markdown]
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that helps to review and ghost write the blog drafts and merge them into a professional developer blog post."},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" },        
        max_tokens=3000
    )
    result = response.choices[0].message.content
    
    
    json_result = json.loads(result)

    title = json_result.get("title", "No Title Found")
    content = json_result.get("content", "No Content Found").strip()

    # 중복 제거
    question_types = list(set(question_types))
    requirements = list(set(requirements))
    framework_tags = list(set(framework_tags))
    language_tags = list(set(language_tags))
    os_tags = list(set(os_tags))
    tech_stack_tags = list(set(tech_stack_tags))

    return title, content, question_types, requirements, framework_tags, language_tags, os_tags, tech_stack_tags
