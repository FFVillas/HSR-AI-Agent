import operator
from typing import Annotated, List, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # standard chat history
    messages: Annotated[List, add_messages] 
    # Your custom "Fact Sheet" accumulator
    knowledge: Annotated[List[str], operator.add]