
from db_client import get_db_client
#################################################################
# example1
EXAMPLE1_CONVERSATION_ID = 146

# example5
EXAMPLE5_CONVERSATION_ID = 162

# example6
EXAMPLE6_CONVERSATION_ID = 153
#################################################################



class EvaluationUtils:
  def __init__(self) -> None:
      self.database = get_db_client()

  def format_messages(self, messages):
    """
    get_messages_by_conversation_id의 결과를 포맷팅합니다.
    
    :param messages: get_messages_by_conversation_id의 결과
    """
    formatted_messages = []
    # 두 번씩 반복하며 q, a를 순서대로 가져옴
    for i in range(0, len(messages), 2):
      formatted_messages.append({
        "q": messages[i]["message_content"],
        "a": messages[i+1]["message_content"],
      })
    return formatted_messages


  # conversation_id값을 통해 해당 대화의 메시지를 가져옴
  def get_messages_by_conversation_id(self, conversation_id: int):
        """
        Add a new criteria to the evaluation_criteria list.
        
        :param criteria: A single evaluation criteria to be added.
        """
        
        response = self.database.table("messages_for_eval") \
                    .select("sequence_number, message_type, message_content") \
                    .eq("conversation_id", conversation_id) \
                    .order("sequence_number", desc=False) \
                    .execute()
        messages = response.data
        formatted_messages = self.format_messages(messages)
        return formatted_messages
  

  # conversation_id값을 통해 완성된 노트의 인덱스를 가져옴
  def get_indices_by_conversation_id(self, conversation_id: int):
    # Step 1: conversations_for_eval 테이블과 tech_notes_for_eval 테이블에서 conversation_id에 해당하는 tech_notes_for_eval의 id를 가져옴
    response_notes = self.database.table('tech_notes_for_eval').select('id') \
        .eq('conversation_id', conversation_id).execute()
    print(response_notes)
    if response_notes.data:
        tech_note_ids = [item['id'] for item in response_notes.data]

        # Step 2: tech_note_indexs_for_eval 테이블에서 해당하는 tech_note_ids와 매칭되는 index_name을 가져옴
        response_indices = self.database.table('tech_note_indexs_for_eval').select('index_name') \
            .in_('tech_note_id', tech_note_ids).order('index_name', desc=False).execute()
        

        if response_indices.data:
            return [item['index_name'] for item in response_indices.data]
        else:
            print("No indices found.")
            return []
    else:
        print("No matching tech notes found for the given conversation ID.")
        return []
  
  def get_message_to_index_dict_by_conversation_id(self, conversation_id: int):
    # 키는 db상 messages_for_eval 테이블의 id, 값은 메시지 내용입니다.
    message_dict = {}
    # 키는 db상의 tech_note_indexs_for_eval 테이블의 id, 값은 인덱스 이름입니다.
    index_dict = {}
    # 키는 메시지 messages_for_eval 테이블의 id, 값은 인덱스의 tech_note_indexs_for_eval 테이블의 id가 담겨있는 리스트 입니다.
    message_to_index_dict = {}
    # Step 1:
    messages = self.database.table('messages_for_eval').select('id, message_content').eq('conversation_id', conversation_id).order('sequence_number', desc=False).execute()
    if messages.data:
        for message in messages.data:
            message_dict[message['id']] = message['message_content']
    else:
        print("No messages found.")
        return {}
    
    # Step 2:
    tech_note = self.database.table('tech_notes_for_eval').select('id').eq('conversation_id', conversation_id).execute()
    if tech_note.data:
        tech_note_id = tech_note.data[0]['id']
        indices = self.database.table('tech_note_indexs_for_eval').select('id, index_name').eq('tech_note_id', tech_note_id).order('index_number', desc=False).execute()
        if indices.data:
            for index in indices.data:
                index_dict[index['id']] = index['index_name']
        else:
            print("No indices found.")
            return {}
    else:
        print("No matching tech notes found for the given conversation ID.")
        return {}
    
    # Step 3:
    messages = message_dict.keys()
    # message_id가 messages에 있는 경우에만 message_to_tech_note_index_for_eval 테이블에서 해당하는 tech_note_index_id를 가져옴
    message_to_tech_note_index = self.database.table('message_to_tech_note_index_for_eval').select('message_id, tech_note_index_id').in_('message_id', messages).execute()
    print(message_to_tech_note_index)
    if message_to_tech_note_index.data:
        for item in message_to_tech_note_index.data:
            if item['message_id'] in message_to_index_dict:
                message_to_index_dict[item['message_id']].append(item['tech_note_index_id'])
            else:
                message_to_index_dict[item['message_id']] = [item['tech_note_index_id']]
    else:
        print("No matching message to tech note index found.")
        return {}


    return {
        "message_dict": message_dict,
        "index_dict": index_dict,
        "message_to_index_dict": message_to_index_dict
    }



# 함수 실행
evaluation_utils = EvaluationUtils()
# messages = evaluation_utils.get_messages_by_conversation_id(EXAMPLE1_CONVERSATION_ID)
# data = evaluation_utils.get_indices_by_conversation_id(EXAMPLE1_CONVERSATION_ID)

data = evaluation_utils.get_message_to_index_dict_by_conversation_id(EXAMPLE1_CONVERSATION_ID)
