# 1. 가벼운 slim 이미지 사용
FROM python:3.12-slim

# 2. 필수 패키지만 설치 (최소화)
# - curl: Streamlit 상태 체크(Healthcheck)용으로 자주 쓰임
# - build-essential: 만약 나중에 C 확장 모듈이 필요한 라이브러리가 추가될 때를 대비
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 종속성 설치 (캐시 활용을 위해 복사 순서 중요)
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir -r requirements.txt

# 5. 소스 코드 복사
COPY . .

# 6. Streamlit 전용 포트 노출 (기본값 8501)
EXPOSE 8501

# 7. 실행 명령어 (기본 옵션 추가)
CMD ["streamlit", "run", "openai_test.py", "--server.port=8501", "--server.address=0.0.0.0"]