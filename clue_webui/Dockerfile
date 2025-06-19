FROM node:24.1.0-slim AS build

WORKDIR /app

# Build the Web UI
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build

# Serve the Web UI with Nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80