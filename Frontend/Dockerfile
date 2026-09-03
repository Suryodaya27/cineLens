FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Next.js needs env vars at build time — provide defaults
ENV IMGBB_API_KEY=placeholder
ENV API_ENDPOINT=http://api:8000/analyze

RUN npm run build

CMD ["npm", "start"]
