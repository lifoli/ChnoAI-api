from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict
from fetch_messages import fetch_messages, CONVERSATION_ID_EXAMPLE_1, CONVERSATION_ID_EXAMPLE_2

class GraphState(TypedDict):
    conversation_id: int
    messages: list

def get_processed_graph_state(state:GraphState) -> GraphState:
    conversation_id= state["conversation_id"]
    
    messages = fetch_messages(conversation_id)

    processed_graph_state = GraphState(
      conversation_id=conversation_id,
      messages=messages,
    )

    return processed_graph_state  


memory = MemorySaver()

fetch_messages_graph = StateGraph(GraphState)

fetch_messages_graph.add_node("fetch_messages", get_processed_graph_state)

fetch_messages_graph.set_entry_point("fetch_messages")

compiled_graph = fetch_messages_graph.compile(checkpointer=memory)

# 들어갈 graph_state를 정의
graph_state = GraphState(
    conversation_id=CONVERSATION_ID_EXAMPLE_1, # 테스트 할 conversation id로 변경
    messages=[],
)

final_state = compiled_graph.invoke(
    graph_state,
    config={
        "configurable": {"thread_id": 42}
    }
)

# 결과 확인
# print("Final State Messages:", final_state["messages"]) 