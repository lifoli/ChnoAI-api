import requests

# Example URL
URL_EXAMPLE_1 = "https://chatgpt.com/share/68e6ee7c-23ee-4527-bf3d-7d4d4f4e98f8"
URL_EXAMPLE_2 = "https://chatgpt.com/share/6de493cf-d959-4b58-8cab-338f665ee851"

# URL로 메세지 데이터 조회
def fetch_messages(url, user_id=11) -> dict:
    
    # url -> tech_note, conversation
    tech_note_response = requests.post(
        'http://localhost:4000/create/link', 
        json={"url": url, "userId": user_id}
    )
        
    if tech_note_response.status_code != 201:
        print(f"Failed to create tech note: {tech_note_response.status_code}, {tech_note_response.text}")
        return "", []

    tech_note_data = tech_note_response.json().get("techNoteData")
    conversation_id = tech_note_data.get("conversation_id")

    if conversation_id == "" :
      print("Not Found Convesation ID")
      return "", []

    # conversation ID -> messages           
    message_response = requests.get(f'http://localhost:4000/messages/{conversation_id}')  

    if message_response.status_code == 200:
        data = message_response.json()
        messages = data.get("messages", [])     
    else:
        print(f"Failed to fetch messages: {message_response.status_code}, {message_response.text}")
        messages = []

    return conversation_id, messages


# Usage example, 테스트할 URL로 변경
convesation_id, messages = fetch_messages(URL_EXAMPLE_1) 

