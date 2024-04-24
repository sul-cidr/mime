FROM node:18-alpine

RUN apk update \
  && apk add --no-cache libc6-compat \
  && corepack enable && corepack prepare pnpm@9.0.6 --activate

# Container is used with live-reload so we don't want the Vite cache stored on bind-mounted host filesystem
ENV VITE_CACHE_DIR=/tmp

# Store all of pnpm's stores, caches, and runtime data outside /app, so that the host filesystem can be 
#  bind mounted over the top without complications.  Note that absolute paths won't work here.
ENV MODULES_DIR=../node_modules

WORKDIR /app2
EXPOSE 5173
COPY . .
RUN pnpm --modules-dir $MODULES_DIR --virtual-store-dir $MODULES_DIR/.pnpm --store-dir $MODULES_DIR/.pnpm-store install
ENTRYPOINT pnpm dev --host
