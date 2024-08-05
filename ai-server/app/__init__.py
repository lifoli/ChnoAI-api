from flask import Flask, request, jsonify, render_template
import requests
from playwright.sync_api import sync_playwright

def create_app():
    app = Flask(__name__)

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

            page.goto(url, wait_until="domcontentloaded")

            chat_url = page.url
            chat_room_title = page.query_selector("h1").inner_text()

            user_messages = page.query_selector_all('[data-message-author-role="user"]')
            user_texts = [msg.inner_text() for msg in user_messages]

            assistant_messages = page.query_selector_all('[data-message-author-role="assistant"]')
            assistant_texts = [msg.inner_text() for msg in assistant_messages]

            data = [{"question": question, "answer": assistant_texts[index] if index < len(assistant_texts) else ""} for index, question in enumerate(user_texts)]

            browser.close()
            return chat_url, chat_room_title, data

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)