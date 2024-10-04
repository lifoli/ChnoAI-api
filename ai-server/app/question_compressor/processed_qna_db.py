from supabase import Client
from typing import List
from db_client import get_db_client
from type import CodeStorage, QA

class ProcessedQnADBHandler:
    def __init__(self):
        self.database: Client = get_db_client()  

    # Q&A 데이터를 'processed_qna' 테이블에 삽입하는 메서드
    def insert_processed_qna(self, conversation_id: int, model:str, processed_content: List[QA]):
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
            "conversation_id": conversation_id,  # 대화 ID
            "model":model,  
            "processed_content": processed_content  # Q&A 데이터 리스트
        }).execute()
            return response.data  
        except Exception as e:
            
            print(f"Internal server error: {str(e)}")
            return None

    # 추출된 코드 데이터를 'extracted_code' 테이블에 삽입하는 메서드
    def insert_extracted_code(self, conversation_id: int, model:str, processed_qna_id: int, code_document: List[CodeStorage]):
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
            "model":model,  
            "processed_qna_id": processed_qna_id,  
            "code_document": code_document 
        }).execute()
            return response.data  
        except Exception as e:
            print(f"Internal server error: {str(e)}")
            return None
        
    def insert_qna_and_code(self, conversation_id: int, model:str, processed_content: List[QA], code_document: List[CodeStorage]):
        """
        processed_qna 테이블에 Q&A 데이터를 삽입하고, 해당 ID를 사용해 extracted_code 테이블에 코드 데이터를 삽입하는 메서드.

        Args:
            conversation_id (int): 대화의 ID
            processed_content (List[QA]): Q&A 쌍 데이터를 포함하는 리스트
            code_document (List[CodeStorage]): 코드 문서 데이터를 포함하는 리스트

        Returns:
            bool: 두 테이블에 모두 성공적으로 삽입되었는지 여부
        """
        try:
            # Q&A 데이터를 먼저 삽입
            processed_qna = self.insert_processed_qna(conversation_id, model, processed_content)
            processed_qna_id = processed_qna[0]["id"]

            # 삽입된 Q&A 데이터의 ID가 유효한 경우에만 코드 데이터를 삽입
            if processed_qna_id is not None:
                response = self.insert_extracted_code(conversation_id, model, processed_qna_id, code_document)
                if response is not None:
                    print("Q&A 및 코드 문서 데이터가 성공적으로 삽입되었습니다.")
                    return True
                else:
                    print("코드 문서 데이터 삽입 실패.")
                    return False
            else:
                print("Q&A 데이터 삽입 실패.")
                return False
        except Exception as e:
            print(f"Internal server error: {str(e)}")
            return False
    
    def get_qna_and_code(self, conversation_id: int, model:str):
        processed_qna_conversation = None
        code_document = None
        
        try:
            # 'processed_qna' 테이블에서 가장 최신의 Q&A 가져오기
            response = self.database.table("processed_qna") \
                                    .select("id, processed_content") \
                                    .eq("conversation_id", conversation_id) \
                                    .eq("model", model) \
                                    .order("id", desc=True) \
                                    .limit(1) \
                                    .execute()
            
            processed_qna = response.data
            if not processed_qna:
                raise Exception(f"No Q&A found for conversation {conversation_id}")
            
            processed_qna_id = processed_qna[0]["id"]
            processed_qna_conversation = processed_qna[0]["processed_content"]

            # 'extracted_code' 테이블에서 가장 최신의 코드 문서 가져오기
            response = self.database.table("extracted_code") \
                                    .select("code_document") \
                                    .eq("processed_qna_id", processed_qna_id) \
                                    .eq("model", model) \
                                    .order("id", desc=True) \
                                    .limit(1) \
                                    .execute()
            
            extracted_code = response.data
            if not extracted_code:
                raise Exception(f"No extracted code found for conversation {conversation_id}")
            
            code_document = self._format_extracted_code(items=extracted_code[0]["code_document"])

        except Exception as e:
            print(f"Internal server error: {str(e)}") 

        # Q&A와 코드 문서 반환 (값이 없을 경우 None 반환)
        return processed_qna_conversation, code_document

    
    def _format_extracted_code(self, items):
        result_dict = {item['code_index']: item['code_snippet'] for item in items}
        return result_dict

