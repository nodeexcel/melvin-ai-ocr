FROM node:20-alpine

WORKDIR /frontend

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

RUN npm run build

ENV PORT=3036
CMD ["npm", "start"]
