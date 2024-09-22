from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict
from test_messages import fetch_messages

# Example URL
URL_EXAMPLE_1 = "https://chatgpt.com/share/68e6ee7c-23ee-4527-bf3d-7d4d4f4e98f8"
URL_EXAMPLE_2 = "https://chatgpt.com/share/6de493cf-d959-4b58-8cab-338f665ee851"

class GraphState(TypedDict):
    conversation_id: str
    messages: list
    url: str

def get_processed_graph_state(state:GraphState) -> GraphState:
    url= state["url"]
    
    final_conversation_id, final_messages = fetch_messages(url)

    processed_graph_state = GraphState(
      conversation_id=final_conversation_id,
      messages=final_messages,
      url=graph_state["url"]  
    )

    return processed_graph_state  


memory = MemorySaver()

fetch_messages_graph = StateGraph(GraphState)

fetch_messages_graph.add_node("fetch_messages", get_processed_graph_state)

fetch_messages_graph.set_entry_point("fetch_messages")

compiled_graph = fetch_messages_graph.compile(checkpointer=memory)

# 들어갈 graph_state를 정의
graph_state = GraphState(
    conversation_id="", 
    messages=[],
    url=URL_EXAMPLE_1  # 호출할 URL -> 테스트할 URL 변경
)

final_state = compiled_graph.invoke(
    graph_state,
    config={
        "configurable": {"thread_id": 42}
    }
)

# 결과 확인
# print("Final State Messages:", final_state["messages"]) 