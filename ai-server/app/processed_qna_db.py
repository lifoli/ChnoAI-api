from supabase import Client
from typing import List
from db_client import get_db_client
from question_compressor import QA, CodeStorage

class ProcessedQnADBHandler:
    def __init__(self):
        self.database: Client = get_db_client()  

    # Q&A 데이터를 'processed_qna' 테이블에 삽입하는 메서드
    def insert_processed_qna(self, convesation_id: int, processed_content: List[QA]):
        """
        processed_qna_pairs 데이터를 processed_qna 테이블에 삽입하는 메서드.

        Args:
            convesation_id (int): 삽입할 데이터가 속한 대화의 ID
            processed_content (List[QA]): Q&A 쌍 데이터를 포함하는 리스트

        Returns:
            Response: 삽입 결과를 담은 응답 객체
        """
        # 데이터베이스에 데이터를 삽입하고 결과를 반환
        try:
            response = self.database.table("processed_qna").insert({
            "convesation_id": convesation_id,  # 대화 ID
            "processed_content": processed_content  # Q&A 데이터 리스트
        }).execute()
            return response.data  
        except Exception as e:
            
            print(f"Internal server error: {str(e)}")
            return None

    # 추출된 코드 데이터를 'extracted_code' 테이블에 삽입하는 메서드
    def insert_extracted_code(self, conversation_id: int, processed_qna_id: int, code_document: List[CodeStorage]):
        """
        추출된 코드 데이터를 extracted_code 테이블에 삽입하는 메서드.

        Args:
            conversation_id (int): 대화의 ID
            processed_qna_id (int): 관련된 Q&A 데이터의 ID
            code_document (List[CodeStorage]): 코드 문서 데이터를 포함하는 리스트

        Returns:
            Response: 삽입 결과를 담은 응답 객체
        """        
        try:
            response = self.database.table("extracted_code").insert({
            "conversation_id": conversation_id,  
            "processed_qna_id": processed_qna_id,  
            "code_document": code_document 
        }).execute()
            return response.data  
        except Exception as e:
            print(f"Internal server error: {str(e)}")
            return None
