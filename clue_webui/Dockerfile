FROM node:24.1.0-slim AS build

WORKDIR /app

# Build the Web UI
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build

# Serve the Web UI with Nginx
FROM nginx:alpine
ENV NGINX_RESOLVER=127.0.0.11

COPY --from=build /app/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/templates/default.conf.template

CMD ["/bin/sh", "-c", "envsubst '\$NGINX_RESOLVER' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'" ]

EXPOSE 80