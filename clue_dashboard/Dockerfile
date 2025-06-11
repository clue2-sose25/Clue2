FROM node:24.1.0-slim AS build

WORKDIR /app

# Build the Dashboard
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build

# Serve the dashboard with Nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
# Forward nginx logs to the Docker logger
#RUN ln -sf /dev/stdout /var/log/nginx/access.log \
#    && ln -sf /dev/stderr /var/log/nginx/error.log

EXPOSE 80
