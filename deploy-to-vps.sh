#!/bin/bash
# Foroshgram — Production Deployment Script
# Run this on the VPS (185.204.168.57) as root or with sudo

set -e

echo "🚀 Foroshgram Production Deployment"
echo "===================================="

# 1. System packages
apt-get update && apt-get install -y \
    docker.io docker-compose nginx certbot python3-certbot-nginx \
    git curl wget ufw

# 2. Start docker
systemctl enable docker && systemctl start docker

# 3. Clone project (if not already)
if [ ! -d "/opt/foroshgram" ]; then
    git clone https://github.com/YOUR_REPO/foroshgram.git /opt/foroshgram
else
    cd /opt/foroshgram && git pull
fi

cd /opt/foroshgram

# 4. Create production .env files
cat > telegram_order_bot/.env << 'EOF'
BOT_TOKEN=8921572262:AAF57sD_SE_BjXUUnQqi8aT41bA90FCxeQU
ADMIN_IDS=8497713691
DATABASE_URL=postgresql+asyncpg://foroshgram:${POSTGRES_PASSWORD}@postgres:5432/foroshgram
STORE_NAME=فروشگرام
ZARINPAL_MERCHANT_ID=YOUR_ZARINPAL_MERCHANT_ID
ZARINPAL_SANDBOX=false
ZARINPAL_CALLBACK_URL=https://telegramorder.ir/bot/payment/callback
NOTIFICATION_CHANNEL_ID=-1001234567890
PROXY_URL=YOUR_PROXY_IF_NEEDED
EOF

cat > telegram_order_website/.env.production << 'EOF'
DATABASE_URL=postgresql://foroshgram:${POSTGRES_PASSWORD}@postgres:5432/foroshgram
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGE_ME_STRONG_PASSWORD
JWT_SECRET=$(openssl rand -hex 32)
NEXTAUTH_URL=https://telegramorder.ir
NODE_ENV=production
EOF

# 5. Create docker-compose.prod.yml
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: foroshgram_postgres
    environment:
      POSTGRES_DB: foroshgram
      POSTGRES_USER: foroshgram
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U foroshgram -d foroshgram"]
      interval: 10s
      timeout: 5s
      retries: 5

  bot:
    build:
      context: ./telegram_order_bot
      dockerfile: Dockerfile
    container_name: foroshgram_bot
    env_file:
      - ./telegram_order_bot/.env
    environment:
      DATABASE_URL: postgresql+asyncpg://foroshgram:${POSTGRES_PASSWORD}@postgres:5432/foroshgram
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  website:
    build:
      context: ./telegram_order_website
      dockerfile: Dockerfile
    container_name: foroshgram_website
    env_file:
      - ./telegram_order_website/.env.production
    environment:
      DATABASE_URL: postgresql://foroshgram:${POSTGRES_PASSWORD}@postgres:5432/foroshgram
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postgres_data:
EOF

# 6. Nginx config
cat > /etc/nginx/sites-available/telegramorder.ir << 'EOF'
# Foroshgram — Nginx Configuration

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# Upstream for Next.js
upstream website {
    server 127.0.0.1:3000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name telegramorder.ir www.telegramorder.ir;

    # ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all HTTP to HTTPS (after cert obtained)
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name telegramorder.ir www.telegramorder.ir;

    # SSL (will be filled by certbot)
    ssl_certificate /etc/letsencrypt/live/telegramorder.ir/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/telegramorder.ir/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Static files from Next.js
    location /_next/static/ {
        proxy_pass http://website;
        proxy_cache_valid 200 1y;
        add_header Cache-Control "public, immutable";
    }

    # Public uploads/images
    location /uploads/ {
        proxy_pass http://website;
        proxy_cache_valid 200 30d;
    }

    # API routes - rate limited
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://website;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Login - stricter rate limit
    location /login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://website;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin/Seller panels - rate limited
    location /admin/ {
        limit_req zone=api burst=30 nodelay;
        proxy_pass http://website;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /seller/ {
        limit_req zone=api burst=30 nodelay;
        proxy_pass http://website;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main app
    location / {
        proxy_pass http://website;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
EOF

# 7. Enable site
ln -sf /etc/nginx/sites-available/telegramorder.ir /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 8. SSL Certificate
certbot --nginx -d telegramorder.ir -d www.telegramorder.ir --non-interactive --agree-tos -m admin@telegramorder.ir --redirect

# 9. Firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 10. Start services
cd /opt/foroshgram
export POSTGRES_PASSWORD=$(openssl rand -hex 16)
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" > .env.prod

docker-compose -f docker-compose.prod.yml up -d --build

# 11. Create systemd service for auto-start
cat > /etc/systemd/system/foroshgram.service << 'EOF'
[Unit]
Description=Foroshgram Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/foroshgram
EnvironmentFile=/opt/foroshgram/.env.prod
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable foroshgram.service

echo ""
echo "✅ Deployment Complete!"
echo "========================"
echo "Website: https://telegramorder.ir"
echo "Bot: @dasttiarfrooshbot (check logs: docker logs -f foroshgram_bot)"
echo "PostgreSQL: Internal only"
echo ""
echo "Next steps:"
echo "1. Edit telegram_order_bot/.env with ZARINPAL_MERCHANT_ID"
echo "2. Edit telegram_order_website/.env.production with strong ADMIN_PASSWORD"
echo "3. Restart: systemctl restart foroshgram"
echo "4. Check logs: journalctl -u foroshgram -f"
echo ""
echo "PostgreSQL password saved in /opt/foroshgram/.env.prod"
cat /opt/foroshgram/.env.prod