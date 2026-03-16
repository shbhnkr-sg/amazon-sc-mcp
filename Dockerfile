FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache git

RUN git clone https://github.com/mattcoatsworth/AmazonSeller-mcp-server.git .

RUN npm install

RUN npm install supergateway

EXPOSE 3000

CMD ["npx", "supergateway", "--stdio", "node src/index.js", "--port", "3000", "--host", "0.0.0.0"]
