
import streamlit as st
import uuid
import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. 환경 변수 로드 및 클라이언트 초기화
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. 페이지 설정
st.set_page_config(page_title="openai_test.py", layout="wide", page_icon="🤖")

# 3. 페르소나 데이터 정의 (OpenAI 모델에 최적화)
PERSONAS = {
    "🍎 영어 선생님": (
        "너는 학생의 언어적 잠재력을 끌어올리는 '하버드 출신 전문 영어 튜너'이다.\n"
        "### 지침:\n"
        "1. 질문자가 한국어로 물어도 답변의 본문은 반드시 '영어'로만 작성하라.\n"
        "2. 답변 끝에 아주 짧은 한 문장 정도로만 한국어 격려를 덧붙여라.\n"
        "3. 문법 교정 시 뉘앙스를 설명하고, 마지막에 [Today's Key Expressions] 섹션을 제공하라."
    ),
    "💻 코드 리뷰어": (
        "너는 실리콘밸리 '냉철한 시니어 개발 팀장'이다. 타협은 없으며 성능과 가독성을 중시한다.\n"
        "### 지침:\n"
        "1. 냉소적인 말투로 시작하고, '우아한 코드'의 기술적 팩트를 교육하라.\n"
        "2. 보안, 메모리, 시간 복잡도를 엄격히 비판하고 개선된 코드를 제시하라."
    ),
    "📜 조선 선비": (
        "너는 퇴계 이황의 가르침을 따르는 '성균관의 깐깐한 선비'이다.\n"
        "### 지침:\n"
        "1. 하오체와 고풍스러운 어휘를 사용하고 사서삼경 구절을 인용하라.\n"
        "2. 현대 기술을 '서양의 술수'라 칭하되 그 안의 이치(理)를 논하라."
    ),
    "🌿 심리 상담가": (
        "너는 따뜻하지만 통찰력 있는 '임상 심리학 박사'이다.\n"
        "### 지침:\n"
        "1. 반영적 경청을 수행하고 전문 심리학 이론을 부드럽게 설명하라.\n"
        "2. 스스로 답을 찾게 돕는 철학적 질문을 던지고 위로의 문장으로 마무리하라."
    )
}

# 4. 세션 상태 초기화
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "file_context" not in st.session_state:
    st.session_state["file_context"] = ""
if "uploaded_file_name" not in st.session_state:
    st.session_state["uploaded_file_name"] = ""
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

# 5. 유틸리티 함수 ---
def create_new_chat(persona_name):
    new_id = uuid.uuid4()
    st.session_state.chat_sessions[new_id] = {
        "persona": persona_name,
        "messages": [],
        "title": f"{persona_name} 대화"
    }
    st.session_state.current_session_id = new_id

def delete_chat(session_id):
    del st.session_state.chat_sessions[session_id]
    if st.session_state.current_session_id == session_id:
        st.session_state.current_session_id = None

# 6. 사이드바 UI ---
with st.sidebar:
    st.title("🎭 openai_test.py ")
    
    if st.session_state.current_session_id:
        curr_p = st.session_state.chat_sessions[st.session_state.current_session_id]["persona"]
        st.success(f"현재 역할: **{curr_p}**")
        
        if curr_p == "💻 코드 리뷰어":
            st.divider()
            st.subheader("📁 코드 분석")
            uploaded_file = st.file_uploader(
                "분석할 파일을 업로드하세요", 
                type=['py', 'js', 'java', 'txt', 'cpp', 'html', 'css'], 
                key=f"uploader_{st.session_state['uploader_key']}"
            )
            
            if uploaded_file:
                try:
                    file_content = uploaded_file.read().decode("utf-8")
                    st.session_state["file_context"] = f"### [분석 대상 파일: {uploaded_file.name}]\n```\n{file_content}\n```"
                    st.session_state["uploaded_file_name"] = uploaded_file.name
                    st.info(f"✅ {uploaded_file.name} 로드됨")
                except Exception as e:
                    st.error(f"파일 읽기 오류: {e}")
    
    st.divider()
    st.subheader("➕ 새 대화 시작")
    cols = st.columns(2)
    for i, p_name in enumerate(PERSONAS.keys()):
        with cols[i % 2]:
            if st.button(p_name, use_container_width=True):
                create_new_chat(p_name)
                st.session_state["file_context"] = ""
                st.session_state["uploaded_file_name"] = ""
                st.rerun()

    st.divider()
    st.subheader("💬 대화 목록")
    sids = list(st.session_state.chat_sessions.keys())[::-1]
    for sid in sids:
        is_active = sid == st.session_state.current_session_id
        col_txt, col_del = st.columns([0.8, 0.2])
        with col_txt:
            label = f"{'✅ ' if is_active else ''}{st.session_state.chat_sessions[sid]['title']}"
            if st.button(label, key=f"nav_{sid}", use_container_width=True):
                st.session_state.current_session_id = sid
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{sid}"):
                delete_chat(sid)
                st.rerun()

# 7. 메인 채팅 UI ---
if st.session_state.current_session_id:
    curr_chat = st.session_state.chat_sessions[st.session_state.current_session_id]
    st.subheader(f" {curr_chat['persona']}와 대화 중")
    st.divider()

    # 과거 메시지 출력
    for msg in curr_chat["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("메시지를 입력하세요..."):
        clean_prompt = prompt.strip()
        
        if clean_prompt:
            display_prompt = clean_prompt
            if st.session_state["uploaded_file_name"]:
                display_prompt = f"📂 **분석 대상 파일:** `{st.session_state['uploaded_file_name']}`\n\n{clean_prompt}"

            curr_chat["messages"].append({"role": "user", "content": display_prompt})
            with st.chat_message("user"):
                st.markdown(display_prompt)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                full_response = ""
                
                # OpenAI를 위한 메시지 구성
                # System Message에 페르소나 지침과 파일 컨텍스트를 주입합니다.
                system_instruction = f"{PERSONAS[curr_chat['persona']]}\n\n[Background Data]\n{st.session_state['file_context']}"
                
                messages = [{"role": "system", "content": system_instruction}]
                # 이전 대화 내역 추가 (히스토리 유지)
                for m in curr_chat["messages"][:-1]:
                    messages.append({"role": m["role"], "content": m["content"]})
                # 현재 질문 추가
                messages.append({"role": "user", "content": clean_prompt})
                
                try:
                    # OpenAI Streaming 호출
                    response = client.chat.completions.create(
                        model="gpt-4o",  # 또는 "gpt-4o-mini"
                        messages=messages,
                        stream=True
                    )
                    
                    for chunk in response:
                        if chunk.choices[0].delta.content is not None:
                            token = chunk.choices[0].delta.content
                            full_response += token
                            placeholder.markdown(full_response + "▌")
                    
                    placeholder.markdown(full_response)
                    curr_chat["messages"].append({"role": "assistant", "content": full_response})
                    
                    # 파일 세션 리셋
                    st.session_state["file_context"] = ""
                    st.session_state["uploaded_file_name"] = ""
                    st.session_state["uploader_key"] += 1
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"OpenAI 연결 실패: {e}")
else:
    st.info("👈 왼쪽 사이드바에서 역할을 선택하여 새로운 대화를 시작해 보세요!")