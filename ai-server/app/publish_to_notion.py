import os
import requests
from dotenv import load_dotenv
# .env 파일의 환경 변수 로드
load_dotenv()
from openai import OpenAI
client = OpenAI()
import json
import re

from flask import Blueprint, request, jsonify



NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

def markdown_to_notion_blocks(content):
    lines = content.split('\n')
    blocks = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('# '):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": line[2:]}
                    }]
                }
            })
        elif line.startswith('## '):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": line[3:]}
                    }]
                }
            })
        elif line.startswith('### '):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": line[4:]}
                    }]
                }
            })
        elif line.startswith('- '):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": line[2:]}
                    }]
                }
            })
        elif line.startswith('```'):
            code_block = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_block.append(lines[i])
                i += 1
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": '\n'.join(code_block)}
                    }],
                    "language": "plain text"
                }
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": line}
                    }]
                }
            })
        i += 1
    
    return blocks

def format_content(content):
    try:
        prompt = f"""
        Review the following blog drafts and combine them into a single cohesive and polished blog post. Ensure that the final content flows well, maintains a consistent tone, and covers all the points mentioned in the drafts. Format the content using Markdown and code blocks as necessary to ensure it renders well on Notion. Keep in mind that this post is likely about implementing a specific feature, fixing a bug, or explaining a concept, rather than covering the entire project. The author is a developer aiming to document and share knowledge and insights gained during the development process.

        Blog Drafts:
        {content}

        Output format(JSON):
        {{
            "title": [Generated title],
            "content": [Final combined and polished blog post in Markdown]
        }}
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that helps to review and ghost write the blog drafts and merge them into a professional developer blog post."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" },        
            max_tokens=8000
        )
        result = response.choices[0].message.content
        
        
        json_result = json.loads(result)

        title = json_result.get("title", "No Title Found")
        content = json_result.get("content", "No Content Found").strip()

        

    except Exception as e:
        print("")

    return title, content

def create_notion_page(title, content, question_type, os_tags, framework_tags, language_tags, tech_stack_tags):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    print(question_type, os_tags, framework_tags, language_tags, tech_stack_tags)

    content_blocks = markdown_to_notion_blocks(content)

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "title": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "Question_Type": {
                "multi_select": [{"name": tag} for tag in question_type]
            },
            "OS_Tags": {
                "multi_select": [{"name": tag} for tag in os_tags]
            },
            "Framework_Tags": {
                "multi_select": [{"name": tag} for tag in framework_tags]
            },
            "Language_Tags": {
                "multi_select": [{"name": tag} for tag in language_tags]
            },
            "Tech_Stack_Tags": {
                "multi_select": [{"name": tag} for tag in tech_stack_tags]
            }
        },
        "children": content_blocks
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

publish_to_notion_bp = Blueprint('publish_to_notion', __name__)

@publish_to_notion_bp.route('/publish-to-notion', methods=['POST'])
def publish_to_notion():
    data = request.json
    title = data.get('title')
    content = data.get('content')
    question_type = data.get('question_type', [])
    os_tags = data.get('os_tags', [])
    framework_tags = data.get('framework_tags', [])
    language_tags = data.get('language_tags', [])
    tech_stack_tags = data.get('tech_stack_tags', [])
    try:
        if (os_tags.__len__() == 0 and framework_tags.__len__() == 0 and language_tags.__len__() == 0 and tech_stack_tags.__len__() == 0):
            formatted_title, formatted_content = format_content(content)
    except Exception as e:
        print("")
    if not formatted_title or not formatted_content:
        return jsonify({"error": "Title and content are required"}), 400

    response = create_notion_page(formatted_title, formatted_content, question_type, os_tags, framework_tags, language_tags, tech_stack_tags)
    print("hihi", response)
    if 'id' in response:
        return jsonify({"message": "Notion page created successfully", "page_id": response['id'], "url": response['url'], "public_url": response['public_url']}), 200
    else:
        return jsonify({"error": "Failed to create Notion page", "details": response}), 500
