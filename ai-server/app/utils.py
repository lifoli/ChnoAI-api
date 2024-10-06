import logging
import warnings
from functools import wraps
from app.type import Message, QA
from supabase import Client

# langfuse
from langfuse import Langfuse
langfuse = Langfuse()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


# Configure logging
def deprecated(func):
    """Decorator to log a method call and warn about deprecation."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Log when the method is called
        logger.info(f"Called method: {func.__name__}")
        
        # Issue a deprecation warning
        warnings.warn(f"{func.__name__} is deprecated and will be removed in a future version.",
                      category=DeprecationWarning, stacklevel=2)
        
        # Call the original function
        return func(*args, **kwargs)
    
    return wrapper

def format_message(conversation: list[Message]) -> list[QA]:
    """
    Formats a given conversation into a list of dictionaries, each containing
    a 'q' (question) and 'a' (answer) pair.

    Args:
        conversation (List[Dict[str, str]]): The conversation as a list of message dictionaries.
    
    Returns:
        List[Dict[str, str]]: A list of formatted conversation pairs in the form of 
                              [{'q': str, 'a': str}, ...].
    """
    
    formatted_conversation = []
    
    # Iterate over the conversation two messages at a time (question/answer pairs)
    for i in range(0, len(conversation), 2):
        try:
            q_message = conversation[i]["message_content"]
            a_message = conversation[i + 1]["message_content"]
            formatted_conversation.append({"q": q_message, "a": a_message})
        except IndexError:
            # Skip if there is no complete q/a pair
            break
    
    return formatted_conversation


# conversation_id로  메세지 데이터 조회
def fetch_messages(database:Client, conversation_id:int) -> list[Message]:
    try:
        response = database.table("messages") \
                    .select("sequence_number, message_type, message_content") \
                    .eq("conversation_id", conversation_id) \
                    .order("sequence_number", desc=False) \
                    .execute()
        
        messages = response.data
        if len(messages) == 0 :
            raise Exception(f"No messages related conversation {conversation_id}")

    except Exception as e:
        print(f"Internal server error: {str(e)}") 
    
    return messages

@deprecated 
def load_conversation(chat_name="chat_ex2"): # deprecated 

    # langfuse에서 대화 세트 가져오기(chat_ex1 -> 짧은 대화, chat_ex2 -> 긴 대화)
    try:
        conversation_data = langfuse.get_prompt(chat_name).prompt
    except Exception as e:
        print(f"Error fetching conversation data: {e}")
        conversation_data = []

    return conversation_data