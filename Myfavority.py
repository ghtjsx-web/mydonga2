import os
import sys
import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# LangChain 컴포넌트 임포트
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# .env 환경 변수 로드
load_dotenv()


# =========================================================
# 1. Pydantic 스키마 및 뉴스 수집 데이터 모델
# =========================================================
class ConflictNewsQuery(BaseModel):
    """전쟁 및 글로벌 분쟁 뉴스 조회를 위한 스키마"""
    region: str = Field(
        default="global",
        description="조회할 분쟁 지역 (예: 'ukraine_russia', 'middle_east', 'asia_pacific', 'global')"
    )
    time_slot: str = Field(
        default="morning",
        description="수집 회차 시간대 ('morning': 1회차 아침 09:00, 'afternoon': 2회차 점심 13:00, 'evening': 3회차 저녁 18:00)"
    )


# =========================================================
# 2. 뉴스 수집 도구 (@tool)
# =========================================================
@tool(args_schema=ConflictNewsQuery)
def fetch_conflict_news(region: str = "global", time_slot: str = "morning") -> str:
    """현재 전 세계에서 발생하는 주요 전쟁/군사 분쟁 관련 최신 속보 뉴스를 수집하는 도구"""
    time_slot_names = {
        "morning": "1회차 (09:00 아침 브리핑)",
        "afternoon": "2회차 (13:00 정오 브리핑)",
        "evening": "3회차 (18:00 일일 마감 종합 브리핑)"
    }
    slot_label = time_slot_names.get(time_slot, time_slot)
    
    # 시간대별 주요 분쟁 지역 속보 시뮬레이션 데이터베이스
    news_database = {
        "morning": [
            "【동유럽 전선】 우크라이나 동부 돈바스 및 쿠르스크 접경 지역에서 무인기(드론) 공방 지속, 방공망 요격 작전 강화",
            "【중동 전선】 홍해 일대 상선 대상 드론 공격 시도 차단, 다국적 연합 해군 경계 태세 최고조 유지",
            "【국제 안보】 UN 안보리 긴급회의 소집 논의 및 분쟁 지역 인도주의적 구호 회랑 개설 촉구 성명 발표"
        ],
        "afternoon": [
            "【동유럽 전선】 서방 주요국 신규 방공 미사일 및 정밀 유도탄 추가 지원 패키지 발표",
            "【중동 전선】 국경 지대 국지적 포격전 발생 및 인근 민간인 대피령 발령, 주요 원유 수송로 긴장감 고조",
            "【외교/협상】 중립국 중재 하에 임시 휴전 및 포로 교환을 위한 실무 협상단 비공개 접촉 보도"
        ],
        "evening": [
            "【동유럽 전선】 야간 대규모 전력망 및 에너지 기반시설 타격 시도 및 긴급 복구반 가동",
            "【중동 전선】 지역 내 주요 군사 기지 경계 강화 및 인근 영공 비행 제한 조치 발표",
            "【글로벌 파급】 국제 유가(WTI/브렌트유) 및 곡물 가격 변동성 확대, 글로벌 공급망 안보 경보 격상"
        ]
    }
    
    selected_news = news_database.get(time_slot, news_database["morning"])
    formatted_news = "\n".join([f"  • {item}" for item in selected_news])
    
    return f"📡 [{slot_label} 글로벌 분쟁/전쟁 뉴스 속보]:\n{formatted_news}"


# =========================================================
# 3. JSON 저장 및 관리 헬퍼 함수
# =========================================================
def save_daily_briefing_to_json(daily_report: Dict[str, Any]) -> str:
    """일일 3회 수집 내역 및 종합 분석 리포트를 data2/war_news_briefing.json에 저장"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data2")
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, "war_news_briefing.json")

        existing_data = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
            except Exception:
                existing_data = []

        existing_data.append(daily_report)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        return file_path
    except Exception as e:
        print(f"⚠️ [JSON 저장 실패]: {e}")
        return ""


# =========================================================
# 4. LLM 기반 3회차 정보 수집 및 종합 취합 엔진
# =========================================================
class WarNewsCollector:
    """관심사(전쟁/분쟁 뉴스)를 매일 3회 수집하고 종합 취합(Synthesis)하는 에이전트 클래스"""
    
    def __init__(self):
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if openrouter_key:
            self.model = ChatOpenAI(
                model="openai/gpt-4o-mini",
                openai_api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.2
            )
        elif openai_key:
            self.model = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=openai_key,
                temperature=0.2
            )
        else:
            raise ValueError("OPENROUTER_API_KEY 또는 OPENAI_API_KEY가 필요합니다.")

        # 종합 취합용 LCEL 프롬프트 체인
        self.synthesis_prompt = ChatPromptTemplate.from_template(
            "당신은 글로벌 국제 안보 및 군사 분쟁 전문 수석 분석관입니다.\n\n"
            "오늘 하루 동안 3회에 걸쳐 수집된 전쟁 및 군사 분쟁 뉴스 속보입니다:\n\n"
            "【1회차 - 아침 수집 (09:00)】\n{morning_news}\n\n"
            "【2회차 - 점심 수집 (13:00)】\n{afternoon_news}\n\n"
            "【3회차 - 저녁 수집 (18:00)】\n{evening_news}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "위 3회차 수집 정보들을 바탕으로 다음 형식에 맞추어 [오늘의 글로벌 전쟁 동향 일일 종합 분석 보고서]를 명확하고 전문적으로 작성해주세요:\n\n"
            "1. 🎯 일일 전황 종합 요약 (3줄 핵심 요약)\n"
            "2. 🗺️ 주요 전선별 핵심 변동 사항 (동유럽 / 중동 / 기타)\n"
            "3. 🤝 외교, 협상 및 국제사회 동향\n"
            "4. 🌐 경제 및 글로벌 에너지/물류 공급망 영향 평가\n"
            "5. ⚠️ 향후 24~48시간 주요 관전 포인트 및 안보 전망"
        )
        self.synthesis_chain = self.synthesis_prompt | self.model | StrOutputParser()

    def collect_single_slot(self, slot: str) -> str:
        """특정 회차(morning / afternoon / evening)의 뉴스 수집"""
        return fetch_conflict_news.invoke({"region": "global", "time_slot": slot})

    def run_daily_3times_collection_and_synthesis(self) -> Dict[str, Any]:
        """하루 3회 수집을 순차 수행하고 일일 종합 리포트를 취합 생성"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        print(f"\n==================================================")
        print(f"🌍 [{today_str}] 글로벌 전쟁 뉴스 1일 3회 수집 및 종합 시작")
        print(f"==================================================")

        # 1회차 아침 수집
        print("\n⏳ [1/3] 아침(09:00) 1회차 뉴스 수집 중...")
        morning_news = self.collect_single_slot("morning")
        print(morning_news)

        # 2회차 점심 수집
        print("\n⏳ [2/3] 점심(13:00) 2회차 뉴스 수집 중...")
        afternoon_news = self.collect_single_slot("afternoon")
        print(afternoon_news)

        # 3회차 저녁 수집
        print("\n⏳ [3/3] 저녁(18:00) 3회차 뉴스 수집 중...")
        evening_news = self.collect_single_slot("evening")
        print(evening_news)

        # 3회차 데이터 종합 취합 보고서 생성
        print("\n🧠 [LLM 종합 취합] 3회차 수집 뉴스를 분석하여 일일 종합 보고서 작성 중...")
        final_synthesis = self.synthesis_chain.invoke({
            "morning_news": morning_news,
            "afternoon_news": afternoon_news,
            "evening_news": evening_news
        })

        daily_report = {
            "report_id": str(uuid.uuid4())[:8],
            "date": today_str,
            "topic": "글로벌 전쟁 및 군사 분쟁 동향",
            "collection_frequency": "1일 3회 (아침 09:00, 점심 13:00, 저녁 18:00)",
            "raw_collections": {
                "morning": morning_news,
                "afternoon": afternoon_news,
                "evening": evening_news
            },
            "executive_summary_report": final_synthesis,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # JSON 저장
        saved_path = save_daily_briefing_to_json(daily_report)

        print("\n" + "=" * 65)
        print("📑 [오늘의 글로벌 전쟁 동향 일일 종합 분석 보고서]")
        print("=" * 65)
        print(final_synthesis)
        print("=" * 65)
        if saved_path:
            print(f"💾 종합 데이터가 안전하게 저장되었습니다: {saved_path}")

        return daily_report


# =========================================================
# 5. 스케줄러 및 CLI 메뉴
# =========================================================
def show_saved_history():
    """저장된 브리핑 이력 조회"""
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data2", "war_news_briefing.json")
    if not os.path.exists(file_path):
        print("\n📭 저장된 전쟁 뉴스 브리핑 파일이 없습니다.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"\n📂 총 {len(records)}건의 일일 종합 보고서가 저장되어 있습니다:")
    for idx, r in enumerate(records, 1):
        print(f"\n[{idx}] 일자: {r.get('date')} | ID: {r.get('report_id')} | 작성시각: {r.get('created_at')}")
        print(f"주제: {r.get('topic')}")
        print("-" * 50)
        print(r.get("executive_summary_report", "")[:250] + "...\n[전체 내용 생략]")


def start_scheduler_loop(collector: WarNewsCollector):
    """지정된 시간(09:00, 13:00, 18:00)에 자동으로 3회 수집 및 종합하는 스케줄러 루프"""
    print("\n⏰ [실시간 스케줄러 가동] 매일 09:00 / 13:00 / 18:00 에 자동 수집을 실행합니다.")
    print("💡 중단하려면 Ctrl + C 를 누르세요.\n")

    daily_buffer = {}

    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        today_key = now.strftime("%Y-%m-%d")

        if today_key not in daily_buffer:
            daily_buffer[today_key] = {}

        # 09:00 아침 1회차
        if current_time == "09:00" and "morning" not in daily_buffer[today_key]:
            print(f"\n[09:00 알림] 1회차 아침 전쟁 뉴스 수집 중...")
            daily_buffer[today_key]["morning"] = collector.collect_single_slot("morning")

        # 13:00 점심 2회차
        elif current_time == "13:00" and "afternoon" not in daily_buffer[today_key]:
            print(f"\n[13:00 알림] 2회차 점심 전쟁 뉴스 수집 중...")
            daily_buffer[today_key]["afternoon"] = collector.collect_single_slot("afternoon")

        # 18:00 저녁 3회차 및 일일 종합 취합
        elif current_time == "18:00" and "evening" not in daily_buffer[today_key]:
            print(f"\n[18:00 알림] 3회차 저녁 전쟁 뉴스 수집 및 종합 취합 실행...")
            collector.run_daily_3times_collection_and_synthesis()
            daily_buffer[today_key]["evening"] = True

        time.sleep(30)


def main():
    print("=" * 65)
    print("⚔️ 글로벌 전쟁 뉴스 매일 3회 수집 & 종합 취합 시스템 (Myfavority)")
    print("=" * 65)

    try:
        collector = WarNewsCollector()
    except Exception as e:
        print(f"❌ [초기화 오류] {e}")
        return

    while True:
        print("\n[메뉴 선택]")
        print("1. ⚡ [즉시 실행] 오늘 3회차 뉴스 수집 및 일일 종합 리포트 생성")
        print("2. 🕒 [스케줄러] 매일 3회(09:00, 13:00, 18:00) 자동 수집 백그라운드 모드")
        print("3. 📁 [기록 조회] data2/war_news_briefing.json 저장 내역 확인")
        print("4. 🚪 종료")

        choice = input("\n메뉴 번호를 입력하세요 (1~4): ").strip()

        if choice == "1":
            collector.run_daily_3times_collection_and_synthesis()
        elif choice == "2":
            try:
                start_scheduler_loop(collector)
            except KeyboardInterrupt:
                print("\n⏹️ 스케줄러가 중단되었습니다.")
        elif choice == "3":
            show_saved_history()
        elif choice == "4":
            print("👋 프로그램을 종료합니다.")
            break
        else:
            print("⚠️ 올바른 번호를 입력해주세요.")


if __name__ == "__main__":
    main()
