import requests
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage 

from dotenv import load_dotenv
load_dotenv()

@tool
def get_weather(city: str) -> str:
    """도시의 실시간 날씨를 조회합니다."""
    try:
        # ko.wttr.in은 API 키 없이 실시간 날씨를 한국어로 제공하는 무료 서비스입니다.
        # format=3 옵션은 "도시명: 날씨상태 기온" 형태의 간결한 텍스트를 반환합니다.
        url = f"https://ko.wttr.in/{city}?format=3"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        # 반환 예시: "Jeju: ⛅️ +28°C"
        weather_info = response.text.strip()
        
        return f"{city}의 실제 날씨 정보: {weather_info}"
    except Exception as e:
        return f"{city}의 날씨를 가져오는 데 실패했습니다: {e}"

# --- 아래부터는 기존 코드와 동일합니다 ---
model = ChatOpenAI(model="gpt-4o-mini",  temperature=0)

tools = [get_weather]
tool_dict = { "get_weather": get_weather}

llm_with_tools = model.bind_tools(tools) 


messages = [
    SystemMessage("당신은 사용자의 질문에 답변을 하기 위해 tools를 사용할 수 있다."),
    HumanMessage("제주도 날씨 상황 알려줘")
]                        

response = llm_with_tools.invoke(messages)
messages.append(response)

if response.tool_calls:
    for tool_call in response.tool_calls:
        selected_tool = tool_dict.get(tool_call['name'])
        tool_result = selected_tool.invoke(tool_call)
        
        tool_msg = ToolMessage(
            content=str(tool_result),
            tool_call_id=tool_call['id']
        )
        messages.append(tool_msg)


final_response = llm_with_tools.invoke(messages)
print("=== LLM 최종 답변 ===")
print(final_response.content)

# ... (하단의 계산기 예제 등은 그대로 두시면 됩니다)

print()
print('@tool두번째 예제')
@tool
def calculator(expression: str) -> str:
    """
    수식을 계산한다.
    예: 10+20, 30*5
    """
    return str(eval(expression))


print('연산결과값 =', calculator.invoke({"expression":"100+200"}) )
print()
print()


print('@tool세번째 예제')
@tool
def add(a: int, b: int) -> int:
    """두 숫자를 더함"""
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """두 숫자를 곱함"""
    return a * b

print('더하기결과 =', add.invoke({"a": 5, "b": 3}))
print('곱하기결과 =', multiply.invoke({"a": 5, "b": 3}))
