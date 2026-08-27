# pydantic 기반 LangChain Tool 정의 및 주식/시간 조회 예제
import os
import sys
from datetime import datetime
import pytz
import yfinance as yf
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# Windows 콘솔 UTF-8 한글 출력 인코딩 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# .env 환경변수 로드
load_dotenv()

# OpenAI 또는 OpenRouter 모델 설정
api_key = os.getenv("OPENAI_API_KEY")
openrouter_key = os.getenv("OPENROUTER_API_KEY")

if api_key:
    model = ChatOpenAI(model="gpt-4o", openai_api_key=api_key)
elif openrouter_key:
    model = ChatOpenAI(
        model="openai/gpt-4o-mini",
        openai_api_key=openrouter_key,
        base_url="https://openrouter.ai/api/v1"
    )
else:
    raise ValueError("OPENAI_API_KEY 또는 OPENROUTER_API_KEY가 .env 파일에 설정되어 있어야 합니다.")


# ==========================================
# 1. Pydantic 스키마 정의
# ==========================================
class StockHistoryInput(BaseModel):
    ticker: str = Field(..., title='주식코드', description='주식 티커 심볼 (예: NVDA, AAPL, MSFT, TSLA)')
    period: str = Field(..., title='기간', description='주식 데이터 조회 기간 (예: 1d, 5d, 1mo, 1y)')


# ==========================================
# 2. 도구(Tools) 정의
# ==========================================
@tool(args_schema=StockHistoryInput)
def get_yf_stock_history(ticker: str, period: str) -> str:
    """주식 종목의 가격 데이터(시가, 종가, 고가, 저가, 거래량 등)를 조회하는 함수"""
    try:
        stock = yf.Ticker(ticker=ticker)
        history = stock.history(period=period)
        if history.empty:
            return f"'{ticker}'에 대한 주가 데이터를 조회할 수 없습니다."
        return history.to_markdown()
    except Exception as e:
        return f"주가 데이터 조회 중 오류 발생: {e}"


@tool
def get_current_time(timezone: str, location: str) -> str:
    """
    현재 시간을 YYYY-MM-DD HH:MM:SS 형식으로 반환하는 함수
    
    Args:
        timezone (str): 타임존 (예: "Asia/Seoul", "America/New_York"). 실제 유효한 타임존이어야 함.
        location (str): 지역명 (예: "서울", "뉴욕"). LLM 답변 생성에 사용됨.
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        return f"{timezone} ({location}) 현재시간 {now}"
    except Exception as e:
        return f"시간 조회 실패: {e}"


# ==========================================
# 3. 모델에 도구 바인딩 및 실행
# ==========================================
tools = [get_current_time, get_yf_stock_history]
tool_dict = {tool_obj.name: tool_obj for tool_obj in tools}

llm_with_tools = model.bind_tools(tools)

# 질문 대상 종목: 엔비디아(NVDA)로 변경
messages = [
    SystemMessage(content="당신은 사용자의 질문에 정확하고 친절하게 답변하기 위해 제공된 도구(Tools)를 적극적으로 활용하는 금융 및 정보 전문 AI 어시스턴트입니다."),
    HumanMessage(content="엔비디아(NVDA)의 최근 3일간 주가 정보와 뉴욕 현재 시간은 어떻게 되지?")
]

print("=" * 60)
print("🤖 AI에게 질문 요청 중...")
print(f"👉 질문: {messages[1].content}")
print("=" * 60)

response = llm_with_tools.invoke(messages)
messages.append(response)

# 도구 호출이 발생했을 때 결과 전달 및 재질의
if response.tool_calls:
    print(f"🔧 호출된 도구 수: {len(response.tool_calls)}개")
    for tool_call in response.tool_calls:
        print(f"  - 도구 실행: {tool_call['name']}({tool_call['args']})")
        selected_tool = tool_dict.get(tool_call["name"])
        tool_result = selected_tool.invoke(tool_call)
        
        tool_msg = ToolMessage(
            content=str(tool_result),
            tool_call_id=tool_call["id"]
        )
        messages.append(tool_msg)
    
    # 도구 실행 결과를 반영한 최종 답변 생성
    final_response = llm_with_tools.invoke(messages)
else:
    final_response = response

print("\n" + "=" * 60)
print("📋 최종 AI 응답:")
print("=" * 60)
print(final_response.content)
print("=" * 60)