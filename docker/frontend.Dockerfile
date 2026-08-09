# AI 网文作者 Agent - 前端镜像（开发模式）
FROM node:20-alpine

WORKDIR /app

COPY frontend/package.json ./
RUN npm install

COPY frontend/ .

EXPOSE 5173
CMD ["npm", "run", "dev"]
