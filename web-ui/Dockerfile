FROM node:18-alpine

RUN apk update \
  && apk add --no-cache libc6-compat \
  && corepack enable && corepack prepare pnpm@7.32.2 --activate

# Container is used with live-reload so we don't want the Vite cache stored on bind-mounted host filesystem
ENV VITE_CACHE_DIR=/tmp

WORKDIR /app
EXPOSE 3000
COPY . .
ENTRYPOINT ["pnpm", "dev", "--host"]
