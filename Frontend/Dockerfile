FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Next.js needs env vars at build time — accept from docker-compose build args
ARG IMGBB_API_KEY=placeholder
ENV IMGBB_API_KEY=${IMGBB_API_KEY}
ENV API_ENDPOINT=http://api:8000/analyze

RUN npm run build

CMD ["npm", "start"]
