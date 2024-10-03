from supabase import Client
from typing import TypedDict, List

CONVERSATION_ID_EXAMPLE_1 = 146
CONVERSATION_ID_EXAMPLE_2 = 152

class Message(TypedDict):
    id: int
    conversation_id: int
    sequence_number: int
    message_type: str
    message_content: str

# conversation_id로  메세지 데이터 조회
def fetch_messages(database: Client, conversation_id: int) -> List[Message]:
    try:
        response = database.table("messages") \
                    .select("id, conversation_id, sequence_number, message_type, message_content") \
                    .eq("conversation_id", conversation_id) \
                    .order("sequence_number", desc=False) \
                    .execute()
        
        messages = response.data
        if len(messages) == 0 :
            raise Exception(f"No messages related conversation {conversation_id}")

    except Exception as e:
        print(f"Internal server error: {str(e)}") 
    return messages

# Usage example, 테스트할 conversation_id로 변경
# messages = fetch_messages(CONVERSATION_ID_EXAMPLE_1) 
# print(messages)

