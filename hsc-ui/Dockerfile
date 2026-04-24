FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y \
      tectonic \
      dvisvgm \
      ghostscript \
      nginx \
      curl && \
    rm -rf /var/lib/apt/lists/*

# install node
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

WORKDIR /app
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

# nginx setup
COPY nginx.conf /etc/nginx/sites-available/default

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]