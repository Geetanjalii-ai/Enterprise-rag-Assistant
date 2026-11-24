# Stage 1: Build the Vite + React TypeScript Application
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies with cached layer
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build assets
COPY . .

# Build argument for API base URL (empty string allows relative /api/v1 proxying via Nginx)
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Stage 2: Serve production bundle with Nginx
FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with reverse proxy and SSE streaming support
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
