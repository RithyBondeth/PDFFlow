FROM node:22-alpine AS build
WORKDIR /app

# Keep lockfile handling identical locally and in the image. The npm bundled
# with the moving Node 22 image can lag behind the lockfile generator.
RUN npm install --global npm@11.9.0

# `npm ci` installs exactly the locked tree: reproducible, and it avoids
# npm's resolver choking on a cold install of this dependency graph.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# The Nitro output is fully self-contained, so the runtime image carries no
# node_modules and no source.
FROM node:22-alpine AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    NITRO_HOST=0.0.0.0 \
    PORT=3000 \
    NUXT_PUBLIC_API_BASE=/api

COPY --from=build /app/.output ./.output

USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
