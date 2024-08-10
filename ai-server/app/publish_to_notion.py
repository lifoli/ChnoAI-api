import os
import requests
import re
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify

# .env 파일의 환경 변수 로드
load_dotenv()

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
    
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400

    response = create_notion_page(title, content, question_type, os_tags, framework_tags, language_tags, tech_stack_tags)
    print("hihi", response)
    if 'id' in response:
        return jsonify({"message": "Notion page created successfully", "page_id": response['id'], "url": response['url'], "public_url": response['public_url']}), 200
    else:
        return jsonify({"error": "Failed to create Notion page", "details": response}), 500
