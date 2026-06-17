FROM node:20-alpine

WORKDIR /frontend

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Receive the API URL at build time so Next.js can bake it into the bundle.
# Pass via: docker compose build --build-arg NEXT_PUBLIC_API_URL=http://...
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

ENV PORT=3036
CMD ["npm", "start"]
