# 베이스 이미지로 Node 18 사용
FROM node:18

# 작업 디렉토리 설정
WORKDIR /usr/src/app

# 의존성 파일 복사
COPY package*.json ./

# 의존성 설치
RUN npm install

# nodemon 설치
RUN npm install -g nodemon

# 앱 소스 복사
COPY . .

# 포트 개방
EXPOSE 8000

# 개발 모드에서 서버 실행
CMD ["npm", "run", "dev"]