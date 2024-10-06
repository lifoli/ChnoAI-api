from flask import Flask, request, jsonify, render_template
import requests
from playwright.sync_api import sync_playwright
import sys
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from langfuse.callback import CallbackHandler
from app.utils import fetch_messages

from app.subtitle_generator.subtitle_generator import SubtitleGenerator
from app.processing_qna.qna_processor import run_pipeline
from app.processing_qna.processed_qna_db import ProcessedQnADBHandler
from app.writer.writer import compiled_graph, GraphState
from datetime import datetime

# 블루프린트 등록
from .categorize_questions import categorize_questions_bp
from .summarize_answers import summarize_answers_bp
from .draft_implementation_blog import draft_implementation_blog_bp
from .draft_debugging_blog import draft_debugging_blog_bp
from .draft_explanation_blog import draft_explanation_blog_bp
from .review_and_finalize_blog import review_and_finalize_blog_bp

from .publish_to_notion import publish_to_notion_bp
langfuse_handler = CallbackHandler()



def create_app():
    app = Flask(__name__)

    load_dotenv()

    # 블루프린트 등록
    app.register_blueprint(categorize_questions_bp, url_prefix='/')
    app.register_blueprint(summarize_answers_bp, url_prefix='/')
    app.register_blueprint(draft_implementation_blog_bp, url_prefix='/')
    app.register_blueprint(draft_debugging_blog_bp, url_prefix='/')
    app.register_blueprint(draft_explanation_blog_bp, url_prefix='/')
    app.register_blueprint(review_and_finalize_blog_bp, url_prefix='/')
    app.register_blueprint(publish_to_notion_bp, url_prefix='/')

    # Supabase URL 및 Key 가져오기
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    database: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route("/process-url", methods=["GET"])
    def process_url():
        url = request.args.get('url')
        print("Processing URL:", url)

        if not url:
            return "URL is required", 400

        try:
            chat_url, chat_room_title, data = run_headless_browser(url)
            return jsonify({"chatUrl": chat_url, "chatRoomTitle": chat_room_title, "data": data}), 200
        except Exception as e:
            return str(e), 500


    def run_headless_browser(url):
        if not url.startswith("https://chatgpt.com/share/"):
            raise ValueError("Invalid URL")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 불필요한 리소스 차단
            page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font"] else route.continue_())

            page.goto(url, wait_until="networkidle")

            chat_url = page.url
            chat_room_title = page.query_selector("h1").inner_text()

            user_messages = page.query_selector_all('[data-message-author-role="user"]')
            print(f"Found {len(user_messages)} user messages")
            sys.stdout.flush()
            user_texts = [msg.inner_text() for msg in user_messages]
            print(f"User messages: {user_texts}")
            sys.stdout.flush()

            assistant_messages = page.query_selector_all('[data-message-author-role="assistant"]')
            print(f"Found {len(assistant_messages)} assistant messages")
            sys.stdout.flush()
            assistant_texts = [msg.inner_text() for msg in assistant_messages]
            print(f"Assistant messages: {assistant_texts}")
            sys.stdout.flush()

            data = [{"question": question, "answer": assistant_texts[index] if index < len(assistant_texts) else ""} for index, question in enumerate(user_texts)]

            browser.close()
            return chat_url, chat_room_title, data


    @app.route('/generate-blog2', methods=['POST'])
    def generate_blog2():
        data = request.json
        conversation_id = data.get('conversation_id')
        messages = fetch_messages(database, conversation_id)
        # 1. 목차 생성
        generatorClass = SubtitleGenerator(config_path = "app/configs/subtitle_generator.yaml");
        result = generatorClass(messages)


        # 2. 질문 압축 및 코드 추출
        processed_qna_list, code_documents = run_pipeline("solar-pro", conversation_id);

        # 블로그 작성 모듈 이전에 목차 생성 모듈에서 나온 결과 전처리
        ## 목차 딕셔너리의 value 리스트 내에 있는 값들을 모두 문자열로 처리
        for key, value in result[1].items():
            result[1][key] = [str(v) for v in value]

        # 블로그 작성 모듈 이전에 질문 압축 및 코드 추출 모듈에서 나온 결과 전처리
        ## Database 삽입 및 조회를 위한 인스턴스 생성
        qna_db_handler = ProcessedQnADBHandler()
        ## 질문 압축 및 코드 추출 모듈에서 나온 결과 전처리
        processed_code_documents = qna_db_handler._format_extracted_code(code_documents)

        # 3. 블로그 작성
        ## 들어갈 graph_state를 정의
        graph_state = GraphState(
            preprocessed_conversations=processed_qna_list,
            code_document=processed_code_documents,
            message_to_index_dict=result[1],
            final_documents=result[0]
        )

        ## graph_state를 이용하여 블로그 작성
        final_state = compiled_graph.invoke(
            graph_state, 
            config={
                "configurable": {"thread_id": 42}, 
                "callbacks": [langfuse_handler]}
        )

        final_technote = format_input(final_state["final_documents"]);
        title = get_current_datetime()


        # 6. 노션 페이지 생성 및 게시
        notion_title = title
        notion_content = final_technote
        question_type = []
        requirements = []
        framework_tags = []
        language_tags = []
        os_tags = []
        tech_stack_tags = []




        notion_response = requests.post('http://localhost:4000/publish-to-notion', json={
            "title": notion_title, 
            "content": notion_content, 
            "question_type": question_type,
            "os_tags": os_tags,
            "framework_tags": framework_tags,
            "language_tags": language_tags,
            "tech_stack_tags": tech_stack_tags
        })

        
        if notion_response.status_code == 200:
            notion_page_id = notion_response.json().get('page_id')
            notion_page_url = notion_response.json().get('url')
            notion_page_public_url = notion_response.json().get('public_url')
            return jsonify({"message": "Blog generated and published to Notion successfully", "notion_page_id": notion_page_id, "notion_page_url": notion_page_url, "notion_page_public_url": notion_page_public_url}), 200
        else:
            return jsonify({"error": "Failed to publish to Notion", "details": notion_response.json()}), 500
        return jsonify({"result": result, "processed_qna_list":processed_qna_list,"code_documents": code_documents, "final_state": final_state}), 200
    def format_input(input_dict):
        # 입력된 딕셔너리의 값들을 줄바꿈으로 연결하여 하나의 문자열로 만듭니다.
        return '\n'.join(input_dict.values())
    
    def get_current_datetime():
        # 현재 날짜와 시간을 가져옵니다
        now = datetime.now()
        # 연-월-일 시:분 형식으로 변환합니다
        formatted_datetime = now.strftime("%Y년 %m월 %d일 %H시 %M분")
        return formatted_datetime




    @app.route('/generate-blog', methods=['POST'])
    def test():
        data = request.json
        conversation_id = data.get('conversation_id')

        # 1. 메시지 가져오기
        questions = get_messages(conversation_id, message_type='question')
        answers = get_messages(conversation_id, message_type='answer')
        
        # 2. 질문 카테고라이징
        categorize_input = {
            "conversation_id": conversation_id,
            "questions": questions
        }
        categorize_response = requests.post('http://localhost:4000/categorize-questions', json=categorize_input, headers={"Content-Type": "application/json"})
        print("")
        if categorize_response.status_code != 200:
            return jsonify({"error": "Error categorizing questions"}), categorize_response.status_code
        
        try:
            categorized_questions = categorize_response.json().get('categorized_questions')
        except ValueError:
            return jsonify({"error": "Invalid JSON response from categorize-questions API"}), 500
        
        
        # 3. 질문에 대한 답변 요약
        summarize_input = {
            "categorized_questions": categorized_questions,
            "answers": answers
        }
        summarize_response = requests.post('http://localhost:4000/summarize-answers', json=summarize_input, headers={"Content-Type": "application/json"})
        if summarize_response.status_code != 200:
            return jsonify({"error": "Error summarizing answers"}), summarize_response.status_code
        
        try:
            summarized_questions_answers = summarize_response.json().get('summarized_answers')
        except ValueError:
            return jsonify({"error": "Invalid JSON response from summarize-answers API"}), 500
        
        # 4. 블로그 초안 작성
        drafts = []
        for summarized_item in summarized_questions_answers:
            for item in summarized_item:  # summarized_questions_answers가 이중 리스트 구조임
                question_types = item['question_type']  # 'question_type' 리스트 직접 접근

                draft_input = item

                draft_response = None

                if 'implementation' in question_types:
                    draft_response = requests.post('http://localhost:4000/draft-implementation-blog', json=[draft_input], headers={"Content-Type": "application/json"})
                    print("draft_implementation_blog response status: ", draft_response.status_code)
                    if draft_response.status_code == 200:
                        drafts.append(draft_response.json())
                    else:
                        print("Error in draft_implementation_blog: ", draft_response.json())

                if 'error' in question_types:
                    draft_response = requests.post('http://localhost:4000/draft-debugging-blog', json=[draft_input], headers={"Content-Type": "application/json"})
                    print("draft_debugging_blog response status: ", draft_response.status_code)
                    if draft_response.status_code == 200:
                        drafts.append(draft_response.json())
                    else:
                        print("Error in draft_debugging_blog: ", draft_response.json())

                if 'explanation' in question_types:
                    draft_response = requests.post('http://localhost:4000/draft-explanation-blog', json=[draft_input], headers={"Content-Type": "application/json"})
                    print("draft_explanation_blog response status: ", draft_response.status_code)
                    if draft_response.status_code == 200:
                        drafts.append(draft_response.json())
                    else:
                        print("Error in draft_explanation_blog: ", draft_response.json())

        print("Drafts: ", drafts)

        # drafts가 비어 있는지 확인하고 비어 있으면 이후 단계를 스킵
        if not drafts:
            return jsonify({"error": "No drafts generated"}), 400

        # 5. 블로그 초안 취합 및 최종 블로그 포스트 작성
        review_input = {
            "drafts": drafts
        }
        review_response = requests.post('http://localhost:4000/review-and-finalize-blog', json=review_input)
        
        if review_response.status_code != 200:
            return jsonify({"error": "Error reviewing and finalizing blog"}), review_response.status_code
        
        try:
            final_blog = review_response.json().get('output')
        except ValueError:
            return jsonify({"error": "Invalid JSON response from review-and-finalize-blog API"}), 500
        
        # 6. 노션 페이지 생성 및 게시
        notion_title = final_blog.get('title')
        notion_content = final_blog.get('content')
        question_type = final_blog.get('question_type', [])
        requirements = final_blog.get('requirements', [])
        framework_tags = final_blog.get('framework_tags', [])
        language_tags = final_blog.get('language_tags', [])
        os_tags = final_blog.get('os_tags', [])
        tech_stack_tags = final_blog.get('tech_stack_tags', [])

        notion_response = requests.post('http://localhost:4000/publish-to-notion', json={
            "title": notion_title, 
            "content": notion_content, 
            "question_type": question_type,
            "os_tags": os_tags,
            "framework_tags": framework_tags,
            "language_tags": language_tags,
            "tech_stack_tags": tech_stack_tags
        })
        
        if notion_response.status_code == 200:
            notion_page_id = notion_response.json().get('page_id')
            notion_page_url = notion_response.json().get('url')
            notion_page_public_url = notion_response.json().get('public_url')
            return jsonify({"message": "Blog generated and published to Notion successfully", "notion_page_id": notion_page_id, "notion_page_url": notion_page_url, "notion_page_public_url": notion_page_public_url, "notion_content": notion_content}), 200
        else:
            return jsonify({"error": "Failed to publish to Notion", "details": notion_response.json()}), 500

    def get_messages(conversation_id, message_type):
        response = database.table('messages').select('sequence_number, message_content').eq('conversation_id', conversation_id).eq('message_type', message_type).order('sequence_number').execute()
        messages = response.data
        return [{"sequence_number": msg["sequence_number"], "question_text": msg["message_content"]} for msg in messages]

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
    