import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def get_db_client() -> Client:
    """
    Supabase 클라이언트를 생성하고 반환하는 함수.

    Returns:
        Client: Supabase 클라이언트 인스턴스.
    """
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY 환경 변수가 설정되지 않았습니다.")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)
