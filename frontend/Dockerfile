FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["sh", "-c", "npx serve -s dist -l tcp://0.0.0.0:${PORT:-3000}"]
