# Conaly API

## 프로젝트 설명

Conaly API는 Express와 TypeScript를 기반으로 구축된 RESTful API입니다. 이 프로젝트는 개발 및 배포 환경 모두에서 Docker와 Docker Compose를 사용하여 손쉽게 설정하고 실행할 수 있습니다.

## 요구 사항

- Node.js 18.x
- Docker
- Docker Compose

## 프로젝트 설정

### 1. 레포지토리 클론

```
git clone <your-repository-url>
cd conaly-api
```

### 2. 환경 변수 설정

프로젝트 루트에 .env 파일을 생성하고 다음 내용을 추가합니다:

```
PORT=8080
MONGO_URI=your_mongo_uri
```

### 3. 의존성 설치

로컬 개발 환경

```
npm install
```

## Docker 설정

### Dockerfile

Dockerfile은 개발 및 배포 환경 모두에서 사용됩니다. 다음과 같이 설정되어 있습니다:

```
# Use the official Node.js 18 image
FROM node:18

# Set environment variable
ENV NODE_ENV=development

# Create and change to the app directory
WORKDIR /usr/src/app

# Copy application dependency manifests to the container image.
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code to the container image.
COPY . .

# For development, install dev dependencies
RUN if [ "$NODE_ENV" = "development" ]; then npm install --only=dev; fi

# Build the TypeScript code (only in production)
RUN if [ "$NODE_ENV" = "production" ]; then npm run build; fi

# Default command
CMD [ "npm", "start" ]

# Expose port 8080
EXPOSE 8080
```

## Docker Compose 설정

### 개발 환경

docker-compose-dev.yml 파일을 사용하여 개발 환경을 설정합니다:

```
version: "3"
services:
  app:
    build:
      context: .
      args:
        NODE_ENV: development
    volumes:
      - .:/usr/src/app
    ports:
      - "8080:8080"
    command: npx nodemon --exec npx ts-node src/index.ts

```

## 배포 환경

docker-compose.yml 파일을 사용하여 배포 환경을 설정합니다:

```
version: "3"
services:
  app:
    build:
      context: .
      args:
        NODE_ENV: production
    ports:
      - "8080:8080"
```

## 스크립트

package.json 파일의 스크립트는 다음과 같습니다:

```
"scripts": {
  "build": "tsc",                       // TypeScript 파일을 JavaScript로 컴파일
  "start": "node dist/index.js",        // 컴파일된 파일을 실행
  "dev": "nodemon --exec ts-node src/index.ts"  // 개발 환경에서 사용
}
```

## 애플리케이션 실행

### 개발 환경

개발 환경에서는 docker-compose-dev.yml 파일을 사용하여 컨테이너를 실행합니다:

```
docker-compose -f docker-compose-dev.yml up
```

또는 로컬 환경에서 직접 실행할 수 있습니다:

```
npm run dev
```

### 배포 환경

배포 환경에서는 기본 docker-compose.yml 파일을 사용하여 컨테이너를 실행합니다:

```
docker-compose up
```

배포 환경에서 TypeScript 파일을 컴파일하고 실행하려면 다음 명령어를 사용합니다:

```
npm run build
npm start
```

## 추가 정보

MongoDB 연결: .env 파일에 MONGO_URI를 설정하여 MongoDB에 연결합니다.
포트 설정: 기본적으로 포트 8080에서 애플리케이션이 실행됩니다. 필요한 경우 .env 파일에서 포트를 변경할 수 있습니다.
이 프로젝트에 대한 질문이나 문제가 발생하면 이슈 트래커에 문제를 제출하세요.

이 README 파일은 프로젝트 설정, 개발 및 배포 환경에서의 실행 방법을 포함하여 필요한 모든 정보를 제공합니다. 각 단계에 대한 명확한 설명과 함께 사용 방법을 상세히 설명하여 사용자가 쉽게 따라할 수 있도록 작성되었습니다.
