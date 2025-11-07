# ---------- Stage 1: Build ----------
FROM node:20-slim AS build

# Install tectonic and required system dependencies
RUN apt-get update && \
    apt-get install -y tectonic && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
    
# Set working directory
WORKDIR /app

# Copy dependency files first (for caching)
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Build the app for production
RUN npm run build

# ---------- Stage 2: Serve with NGINX ----------
FROM nginx:alpine

# Copy build output from the previous stage
COPY --from=build /app/build /usr/share/nginx/html

# Optional: Custom nginx config for single-page apps (React Router etc.)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (Render auto-detects this)
EXPOSE 80

# Start NGINX
CMD ["nginx", "-g", "daemon off;"]