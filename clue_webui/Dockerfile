# Stage 1: Build the React-based web UI
FROM node:24.1.0-slim AS build
WORKDIR /app

# Only copy dependencies first for better cache utilization
COPY package.json package-lock.json ./
RUN npm ci --silent

# Copy the rest and build
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
WORKDIR /

# Use envsubst support for templated config
ENV NGINX_RESOLVER=127.0.0.11
ENV NGINX_RESOLVER_VALID=30s

# Copy built UI files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy Nginx config template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Leverage official entrypoint’s envsubst mechanism
# Ensures template is applied and then Nginx is started
CMD ["nginx", "-g", "daemon off;"]

EXPOSE 80
