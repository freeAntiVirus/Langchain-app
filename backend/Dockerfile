FROM node:20-slim AS build

# Install system dependencies needed by Tectonic
RUN apt-get update && \
    apt-get install -y curl tar && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Download & install Tectonic binary
RUN curl -fsSL https://drop-sh.fullyjustified.net | sh && \
    mv tectonic /usr/local/bin/tectonic && \
    chmod +x /usr/local/bin/tectonic

WORKDIR /app
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]