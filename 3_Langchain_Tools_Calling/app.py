import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage

load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in .env file")


@tool
def request_human_chat() -> str:
    """Activate human chat when user requests it."""
    print("\n" + "="*50)
    print("HUMAN CHAT ACTIVATED")
    print("="*50 + "\n")
    return "Human chat has been activated. A human representative will be with you shortly."


def main():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    llm_with_tools = llm.bind_tools([request_human_chat])
    messages = []
    
    print("\nWelcome to the Chatbot! Type 'exit' to quit.\n")
    
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("\nGoodbye!")
            break
        if not user_input:
            continue
        
        messages.append(HumanMessage(content=user_input))
        
        try:
            response = llm_with_tools.invoke(messages)
            messages.append(response)
            
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    print(f"\n[Tool Call: {tool_call['name']}]")
                    tool_result = request_human_chat.invoke(tool_call.get('args', {}))
                    messages.append(ToolMessage(content=tool_result, tool_call_id=tool_call['id']))
                    final_response = llm_with_tools.invoke(messages)
                    if final_response.content:
                        print(f"\nBot: {final_response.content}")
                    messages.append(final_response)
            else:
                print(f"\nBot: {response.content}")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
