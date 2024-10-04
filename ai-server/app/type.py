from typing import TypedDict, Optional

class Message(TypedDict):
    id: int
    conversation_id: int
    sequence_number: int
    message_type: str
    message_content: str

class q_and_a(TypedDict):
    q: str
    a: str 

class CodeStorage(TypedDict):
    code_description: str
    code_index:str
    code_snippet: str

class QA(TypedDict):
    q: str
    a: str

class QAProcessorGraphState(TypedDict):
    processing_data: Optional[QA]                 # 현재 처리 중인 Q&A pair
    not_processed_conversations: list[QA]         # 아직 처리되지 않은 Q&A pair 리스트
    processed_conversations: list[QA]             # 처리된 Q&A pair 리스트
    code_documents: list[CodeStorage]             # 처리된 코드 문서 정보 리스트

class WriterGraphState(TypedDict): 
    preprocessed_conversations: list[q_and_a]
    code_document: dict
    message_to_index_dict: dict
    final_documents: dict