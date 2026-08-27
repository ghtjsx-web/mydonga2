import os
import sys
import math
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# LangChain 및 langchain_classic 컴포넌트 임포트 (순수 Python 모듈)
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langchain_classic.agents import AgentExecutor

# Windows 터미널 출력 인코딩 설정 (UTF-8 지원)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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
# 1. data2/jejumath.json 파일 저장 헬퍼 함수
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
        print(f"⚠️ [Error] jejumath.json 저장 중 오류 발생: {e}")
        return ""


# =========================================================
# 2. Pydantic BaseModel 상속 입력 스키마 정의
# =========================================================
class MathQuery(BaseModel):
    """수학 연산 및 내장 함수 처리를 위한 입력 스키마"""
    operation: str = Field(
        ..., 
        description="수행할 수학 연산 또는 내장 함수 ('add', 'subtract', 'multiply', 'divide', 'abs', 'round', 'sqrt', 'pow')"
    )
    num1: float = Field(..., description="첫 번째 숫자 (또는 sqrt, round 등의 대상 숫자)")
    num2: Optional[float] = Field(default=0.0, description="두 번째 숫자 (pow의 지수, round의 자릿수, 사칙연산의 피연산자, abs 두 수의 차이 등)")

    def calculate(self) -> float:
        """수학 내장 함수 매핑 딕셔너리를 활용하여 연산을 수행하고 결과를 반환하는 메서드"""
        op = self.operation.lower().strip()

        # 1. 기본 사칙연산
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


class JejuQuery(BaseModel):
    """제주도 정보(날씨, 관광지, 특산물/맛집, 여행팁) 조회를 위한 입력 스키마"""
    category: str = Field(
        ..., 
        description="조회할 제주 정보 카테고리 ('weather', 'tourist_spot', 'food', 'tip')"
    )
    location: str = Field(default="제주도 전체", description="조회할 제주 세부 지역 (예: 서귀포, 애월, 성산, 제주시)")
    date: Optional[str] = Field(default="today", description="조회할 날짜 (예: 오늘, 내일, YYYY-MM-DD)")

    def get_jeju_info(self) -> str:
        """제주 요청 카테고리에 맞는 요약 정보를 반환하는 메서드"""
        if self.category == "weather":
            return f"🌤️ [{self.location}] {self.date} 날씨: 맑음, 기온: 22°C (여행하기 좋은 날씨입니다)"
        elif self.category == "tourist_spot":
            return f"🌋 [{self.location}] 대표 추천 관광지: 성산일출봉, 섭지코지, 한라산 국립공원, 곽지해수욕장"
        elif self.category == "food":
            return f"🍊 [{self.location}] 추천 특산물 및 맛집: 흑돼지 구이, 제주 감귤/한라봉, 고기국수, 갈치조림"
        elif self.category == "tip":
            return f"💡 [{self.location}] 제주 여행 팁: 렌터카 사전 예약 필수, 해안도로 드라이브 추천, 일몰 시간 확인"
        else:
            return f"🏝️ [{self.location}] 제주도 가이드 정보 제공 완료"


# =========================================================
# 3. @tool 데코레이터 적용 (args_schema 인자 활용)
# =========================================================
@tool(args_schema=MathQuery)
def math_tool(operation: str, num1: float, num2: Optional[float] = 0.0) -> str:
    """수학 계산을 수행하는 툴입니다. ('add', 'subtract', 'multiply', 'divide', 'abs', 'round', 'sqrt', 'pow' 연산 지원)"""
    query = MathQuery(operation=operation, num1=num1, num2=num2)
    result = query.calculate()
    return f"계산 결과 ({operation}): {result}"


@tool(args_schema=JejuQuery)
def jeju_tool(category: str, location: str = "제주도 전체", date: str = "today") -> str:
    """제주도의 날씨, 관광지, 특산물/맛집, 여행 팁 정보를 제공하는 전용 툴입니다."""
    query = JejuQuery(category=category, location=location, date=date)
    return query.get_jeju_info()


# 툴 리스트 구성
tools = [math_tool, jeju_tool]


# =========================================================
# 4. AgentExecutor 초기화 함수
# =========================================================
def create_jeju_math_agent() -> AgentExecutor:
    """ChatOpenAI 및 tools를 바인딩하여 AgentExecutor 인스턴스를 생성"""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if openrouter_key:
        model = ChatOpenAI(
            model="openai/gpt-4o-mini",
            openai_api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.0
        )
    elif openai_key:
        model = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=openai_key,
            temperature=0.0
        )
    else:
        raise ValueError("OPENROUTER_API_KEY 또는 OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")

    # Prompt + Tools -> AgentExecutor 생성
    model_with_tools = model.bind_tools(tools)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 제주도 여행 가이드 및 정확한 수학 계산(사칙연산, abs, round, sqrt, pow 등) 도구를 겸비한 친절한 AI 어시스턴트입니다. 도구를 적극 활용하여 답변하세요."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    agent = prompt | model_with_tools

    return AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=False,
        return_intermediate_steps=True,
        max_iterations=15
    )


# =========================================================
# 5. 콘솔 CLI 실행 및 테스트 루프
# =========================================================
def run_cli():
    print("=" * 65)
    print("🍊 제주 여행 & 🔢 수학 내장함수(abs, round, sqrt, pow) AI Agent")
    print("=" * 65)
    print("💡 종료하려면 'exit', 'quit', 또는 'q'를 입력하세요.\n")

    try:
        agent_executor = create_jeju_math_agent()
    except Exception as e:
        print(f"❌ [에이전트 초기화 오류] {e}")
        return

    chat_history: List[BaseMessage] = []

    # 수학 내장함수 및 제주 정보 샘플 질문 테스트
    sample_queries = [
        "제주도 오늘 날씨 알려줘",
        "abs(2 - 17) 계산해줘",
        "sqrt(144)와 pow(3, 4) 계산해줘",
        "round(3.141592, 2) 계산해주고 서귀포 맛집 추천해줘"
    ]

    print("🚀 [자동 테스트 시작]")
    for query in sample_queries:
        print(f"\n👤 [질문]: {query}")
        result = agent_executor.invoke({
            "input": query,
            "chat_history": chat_history
        })

        output_text = result.get("output", "")
        steps = result.get("intermediate_steps", [])

        if steps:
            print("🔧 [실행된 도구 로그]:")
            for s in steps:
                print(f"  - 도구: {s['tool']}({s['args']}) -> {s['output']}")

        print(f"🤖 [AI 답변]:\n{output_text}")

        # JSON 파일 저장
        saved_file = save_result_to_json(
            question=query,
            response=output_text,
            tool_logs=steps
        )
        if saved_file:
            print(f"💾 [저장 완료] -> {saved_file}")

        # 히스토리 갱신
        chat_history.append(HumanMessage(content=query))
        chat_history.append(AIMessage(content=output_text))

    print("\n" + "=" * 65)
    print("💬 [대화 모드 시작] 직접 질문을 입력해보세요 (예: sqrt(256), pow(2, 10)):")
    print("=" * 65)

    while True:
        try:
            user_input = input("\n👉 질문 입력: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("👋 대화를 종료합니다. 혼저옵서예!")
                break

            result = agent_executor.invoke({
                "input": user_input,
                "chat_history": chat_history
            })

            output_text = result.get("output", "")
            steps = result.get("intermediate_steps", [])

            if steps:
                print("\n🔧 [실행된 도구 로그]:")
                for s in steps:
                    print(f"  - 도구: {s['tool']}({s['args']}) -> {s['output']}")

            print(f"\n🤖 [AI 답변]:\n{output_text}")

            saved_file = save_result_to_json(
                question=user_input,
                response=output_text,
                tool_logs=steps
            )
            if saved_file:
                print(f"💾 [JSON 저장 완료] {saved_file}")

            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=output_text))

        except KeyboardInterrupt:
            print("\n👋 프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"❌ [오류 발생]: {e}")


if __name__ == "__main__":
    run_cli()
