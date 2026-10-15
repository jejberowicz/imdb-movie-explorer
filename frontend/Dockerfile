# Front image: build the app with Node, then serve the static files with nginx running without root.
FROM node:24.22.0-alpine AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
# Without install scripts: no dependency needs one, and a compromised one couldn't run code at build time.
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.30.6-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
