from db_client import get_db_client
from supabase import Client
from typing import List, Dict, Any
from question_compressor import QA, CodeStorage

class ProcessedQnADBHandler:
    def __init__(self):
        self.database: Client = get_db_client()

    def insert_processed_qna(self, processed_qna_pairs: List[QA]):
        """
        processed_qna_pairs 데이터를 processed_qna 테이블에 삽입하는 메서드.

        Args:
            processed_qna_pairs (List[Dict[str, Any]]): Q&A 쌍 데이터 리스트.

        Returns:
            Response: 삽입 결과 응답.
        """
        # 삽입할 데이터 준비
        formatted_data = []
        for pair in processed_qna_pairs:
            formatted_data.append({
                "message_id": pair["q"]["message_id"],
                "pair_number": pair["pair_num"],
                "processed_message": pair["q"]["message_content"]
            })
            formatted_data.append({
                "message_id": pair["a"]["message_id"],
                "pair_number": pair["pair_num"],
                "processed_message": pair["a"]["message_content"]
            })
        
        # 데이터 삽입
        try:
            response = self.database.table("processed_qna").insert(formatted_data).execute()
            return response.data
        except Exception as e:
            print(f"Internal server error: {str(e)}") 
            return None
        
