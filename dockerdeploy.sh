#!/bin/bash

# 색상 변수 설정 (기존 상단부)
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

CONTAINER_NAME="my-python-app"
IMAGE_NAME="my-python-app"
IMAGE_TAG="latest"

# 1. 기존 컨테이너 확인 및 제거 (여기에 fi가 빠졌는지 확인)
echo -e "${YELLOW}기존 컨테이너 확인 중...${NC}"
if [ "$(docker ps -aq -f name=^/${CONTAINER_NAME}$)" ]; then
    echo -e "${YELLOW}기존 컨테이너 중지 및 삭제 중...${NC}"
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# 2. .env 파일 유무에 따른 컨테이너 실행 분기
if [ -f .env ]; then
    echo -e "${GREEN}.env 환경 변수를 로드하여 컨테이너 실행 중...${NC}"
    docker run -d \
        --name $CONTAINER_NAME \
        --env-file .env \
        -p 8501:8501 \
        --restart unless-stopped \
        $IMAGE_NAME:$IMAGE_TAG
else
    echo -e "${YELLOW}환경 변수 없이 컨테이너 실행 중...${NC}"
    echo -e "${YELLOW}주의: OPENAI_API_KEY가 설정되지 않으면 애플리케이션이 작동하지 않을 수 있습니다.${NC}"
    docker run -d \
        --name $CONTAINER_NAME \
        -p 8501:8501 \
        --restart unless-stopped \
        $IMAGE_NAME:$IMAGE_TAG
fi

# 3. 실행 결과 확인
if [ $? -eq 0 ]; then
    echo -e "${GREEN}=== 배포 완료! ===${NC}"
    echo -e "${GREEN}컨테이너 이름: $CONTAINER_NAME${NC}"
    echo -e "${GREEN}접속 URL: http://localhost:8501${NC}"
    echo -e "${GREEN}EC2의 경우: http://<EC2-퍼블릭-IP>:8501${NC}"
    echo ""
    echo -e "${YELLOW}컨테이너 로그 확인: docker logs -f $CONTAINER_NAME${NC}"
    echo -e "${YELLOW}컨테이너 중지: docker stop $CONTAINER_NAME${NC}"
    echo -e "${YELLOW}컨테이너 시작: docker start $CONTAINER_NAME${NC}"
else
    echo -e "${RED}컨테이너 실행 실패!${NC}"
    exit 1
fi