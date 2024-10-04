from typing import TypedDict

class CodeStorage(TypedDict):
    code_description: str
    code_index:str
    code_snippet: str

class QA(TypedDict):
    q: str
    a: str