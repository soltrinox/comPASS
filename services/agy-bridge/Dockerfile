FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY src ./src
COPY scripts ./scripts
COPY docs ./docs

RUN chmod +x /app/scripts/fake-agy.js

EXPOSE 8791

CMD ["npm", "start"]
