import os
import sys
import math
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import streamlit as st

# LangChain 및 langchain_classic 컴포넌트 임포트
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_classic.agents import AgentExecutor

# Windows 터미널 출력 인코딩 설정 (UTF-8 지원)
sys.stdout.reconfigure(encoding='utf-8')

# .env 환경 변수 로드
load_dotenv()


# =========================================================
# 0. 수학 관련 내장 함수 및 math 모듈 매핑 딕셔너리
# =========================================================
MATH_FUNCTIONS = {
    'abs': abs,
    'round': round,
    'sqrt': math.sqrt,
    'pow': math.pow
}


# =========================================================
# 1. data2/jejumath.json 저장 헬퍼 함수
# =========================================================
def save_result_to_json(question: str, response: str, tool_logs: Optional[List[Dict[str, Any]]] = None) -> str:
    """처리 결과 내용을 data2 폴더의 jejumath.json 파일에 누적 저장"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data2")
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, "jejumath.json")

        new_entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "response": response,
            "tool_logs": tool_logs if tool_logs is not None else []
        }

        # 기존 JSON 데이터 로드
        data_list = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data_list = json.load(f)
                    if not isinstance(data_list, list):
                        data_list = [data_list]
            except Exception:
                data_list = []

        data_list.append(new_entry)

        # JSON 파일 저장 (UTF-8, indent=2)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)

        return file_path
    except Exception as e:
        st.error(f"⚠️ jejumath.json 저장 중 오류 발생: {e}")
        return ""


# =========================================================
# 2. Pydantic BaseModel 상속 입력 스키마 정의
# =========================================================
class MathQuery(BaseModel):
    """수학 연산 및 내장 함수 처리를 위한 입력 스키마"""
    operation: str = Field(
        ..., 
        description="수행할 연산 또는 함수 ('add', 'subtract', 'multiply', 'divide', 'abs', 'round', 'sqrt', 'pow')"
    )
    num1: float = Field(..., description="첫 번째 숫자 (또는 sqrt, round 등의 대상 숫자)")
    num2: Optional[float] = Field(default=0.0, description="두 번째 숫자 (pow 지수, round 자릿수, 사칙연산 피연산자 등)")

    def calculate(self) -> float:
        """수학 내장 함수 매핑 딕셔너리를 활용하여 연산을 수행하고 결과를 반환하는 메서드"""
        op = self.operation.lower().strip()

        # 1. 사칙연산
        if op == "add":
            return self.num1 + (self.num2 if self.num2 is not None else 0.0)
        elif op == "subtract":
            return self.num1 - (self.num2 if self.num2 is not None else 0.0)
        elif op == "multiply":
            return self.num1 * (self.num2 if self.num2 is not None else 0.0)
        elif op == "divide":
            if self.num2 == 0 or self.num2 is None:
                raise ValueError("0으로 나눌 수 없습니다.")
            return self.num1 / self.num2

        # 2. 수학 내장 함수 (MATH_FUNCTIONS) 매핑 처리
        elif op in MATH_FUNCTIONS:
            func = MATH_FUNCTIONS[op]
            if op == "abs":
                if self.num2 is not None and self.num2 != 0.0:
                    return func(self.num1 - self.num2)
                return func(self.num1)
            elif op == "round":
                decimals = int(self.num2) if self.num2 is not None else 0
                return func(self.num1, decimals)
            elif op == "sqrt":
                if self.num1 < 0:
                    raise ValueError("음수의 제곱근은 계산할 수 없습니다.")
                return func(self.num1)
            elif op == "pow":
                exp = self.num2 if self.num2 is not None else 2.0
                return func(self.num1, exp)
        else:
            raise ValueError(f"지원하지 않는 연산 타입입니다: {self.operation}")


class WeatherQuery(BaseModel):
    """날씨 조회 정보를 정의하는 입력 스키마"""
    location: str = Field(..., description="조회할 도시 또는 지역 이름 (예: 서울, 제주도)")
    date: Optional[str] = Field(default="today", description="조회할 날짜 (예: 오늘, 내일, YYYY-MM-DD)")
    unit: str = Field(default="celsius", description="온도 단위 ('celsius' 또는 'fahrenheit')")

    def get_info(self) -> str:
        """날씨 요청 요약 문자열을 반환하는 메서드"""
        unit_str = "섭씨(°C)" if self.unit == "celsius" else "화씨(°F)"
        return f"[{self.location}] {self.date} 날씨 정보 (단위: {unit_str}, 상태: 맑음, 기온: 24{unit_str})"


# =========================================================
# 3. @tool 데코레이터 적용 (args_schema 인자 활용)
# =========================================================
@tool(args_schema=MathQuery)
def math_tool(operation: str, num1: float, num2: Optional[float] = 0.0) -> str:
    """수학 계산을 수행하는 툴입니다. ('add', 'subtract', 'multiply', 'divide', 'abs', 'round', 'sqrt', 'pow' 연산 지원)"""
    query = MathQuery(operation=operation, num1=num1, num2=num2)
    result = query.calculate()
    return f"계산 결과 ({operation}): {result}"


@tool(args_schema=WeatherQuery)
def weather_tool(location: str, date: str = "today", unit: str = "celsius") -> str:
    """지역 및 날짜별 날씨 정보를 조회하는 툴입니다."""
    query = WeatherQuery(location=location, date=date, unit=unit)
    return query.get_info()


# 툴 목록
tools = [math_tool, weather_tool]


# =========================================================
# 4. Streamlit UI 및 세션(Session State) 관리
# =========================================================
st.set_page_config(
    page_title="AI 스마트 어시스턴트 (AgentExecutor)",
    page_icon="🤖",
    layout="wide"
)

# 세션 상태 초기화 (st.session_state)
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# 사이드바 (Sidebar) 구성
st.sidebar.title("⚙️ AgentExecutor 설정")
st.sidebar.markdown("---")

# OpenRouter API 키 상태 확인
api_key = os.getenv("OPENROUTER_API_KEY")
if api_key:
    st.sidebar.success("🔑 OpenRouter API 연결됨")
else:
    st.sidebar.error("⚠️ OPENROUTER_API_KEY를 .env에서 찾을 수 없습니다.")

# 대화 세션 초기화 버튼
if st.sidebar.button("🗑️ 대화 기록 초기화 (Clear Session)", use_container_width=True):
    st.session_state["messages"] = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.metric("💬 현재 세션 대화 수", f"{len(st.session_state['messages'])}개")

# 모델 파라미터 설정
temperature = st.sidebar.slider("Temperature (창의성)", min_value=0.0, max_value=1.0, value=0.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("💡 빠른 질문 예시")
preset_query = ""
if st.sidebar.button("🌤️ 서울 오늘 날씨 알려줘", use_container_width=True):
    preset_query = "서울 오늘 날씨 알려줘"
if st.sidebar.button("🔢 abs(2 - 17) 계산해줘", use_container_width=True):
    preset_query = "abs(2 - 17) 계산해줘"
if st.sidebar.button("📐 sqrt(144)와 pow(3, 4) 계산해줘", use_container_width=True):
    preset_query = "sqrt(144)와 pow(3, 4) 계산해줘"
if st.sidebar.button("🏝️ 제주도 날씨와 round(3.14159, 2)", use_container_width=True):
    preset_query = "제주도 날씨 알려주고 round(3.14159, 2) 계산해줘"

# 저장된 data2/jejumath.json 확인 Expander
st.sidebar.markdown("---")
st.sidebar.subheader("📁 저장된 JSON 데이터")
json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data2", "jejumath.json")
if os.path.exists(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        st.sidebar.caption(f"💾 `data2/jejumath.json` 에 `{len(saved_data)}`건 저장됨")
        with st.sidebar.expander("📄 jejumath.json 내용 미리보기"):
            st.json(saved_data)
    except Exception:
        pass


# =========================================================
# 5. AgentExecutor 인스턴스 초기화 (from langchain_classic.agents import AgentExecutor)
# =========================================================
@st.cache_resource
def get_agent_executor(temp: float) -> AgentExecutor:
    model = ChatOpenAI(
        model="openai/gpt-4o-mini",
        openai_api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=temp
    )
    
    # Prompt + Tools -> AgentExecutor 생성
    model_with_tools = model.bind_tools(tools)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 수학 계산(사칙연산, abs, round, sqrt, pow 등)과 날씨 조회가 가능한 스마트 AI 에이전트입니다. 도구를 적극 활용하여 정확하고 친절하게 답변하세요."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    agent = prompt | model_with_tools
    
    return AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        return_intermediate_steps=True,
        max_iterations=15
    )


agent_executor = get_agent_executor(temperature)

# 메인 화면 구성
st.title("🤖 AI 스마트 어시스턴트 (AgentExecutor)")
st.caption("수학 내장함수 (`abs`, `round`, `sqrt`, `pow`) + `langchain_classic.agents.AgentExecutor` + `data2/jejumath.json` 저장")

# 이전 세션 대화 기록 출력
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "tool_logs" in msg and msg["tool_logs"]:
            with st.expander("🔧 AgentExecutor 실행 도구 (intermediate_steps)"):
                st.json(msg["tool_logs"])

# 사용자 입력 받기
user_input = st.chat_input("질문을 입력하세요...")
if preset_query:
    user_input = preset_query

if user_input:
    # 1. 사용자 질문을 세션 상태에 추가 및 화면 출력
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. 세션 대화 기록을 LangChain 메시지 객체로 변환 (Multi-turn Context)
    chat_history = []
    for m in st.session_state["messages"][:-1]:
        if m["role"] == "user":
            chat_history.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            chat_history.append(AIMessage(content=m["content"]))

    # 3. AgentExecutor 실행
    with st.chat_message("assistant"):
        with st.spinner("🤖 AgentExecutor가 도구를 추론하고 답변을 생성 중입니다..."):
            try:
                result = agent_executor.invoke({
                    "input": user_input,
                    "chat_history": chat_history
                })
                
                output_text = result["output"]
                intermediate_steps = result.get("intermediate_steps", [])

                st.markdown(output_text)
                
                if intermediate_steps:
                    with st.expander("🔧 AgentExecutor 실행 도구 (intermediate_steps)"):
                        st.json(intermediate_steps)

                # 4. 처리 결과를 data2/jejumath.json 파일에 저장
                saved_path = save_result_to_json(
                    question=user_input,
                    response=output_text,
                    tool_logs=intermediate_steps
                )
                if saved_path:
                    st.toast("💾 data2/jejumath.json 저장 완료!", icon="✅")

                # 세션에 최종 AI 메시지 저장
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": output_text,
                    "tool_logs": intermediate_steps
                })
            except Exception as e:
                error_msg = f"❌ 에이전트 실행 중 오류가 발생했습니다: {str(e)}"
                st.error(error_msg)
                st.session_state["messages"].append({"role": "assistant", "content": error_msg})
