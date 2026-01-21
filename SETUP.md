# Server Setup Guide

This guide describes how to set up the Activity Info Runner server from scratch on a Linux VPS (e.g., Ubuntu 22.04).

## Prerequisites

- A Linux server (VPS) with a public IP address.
- A domain name pointing to your server's IP (e.g., `runner.example.com`).
- Root or sudo access to the server.

## 1. Install Docker & Docker Compose

Update your package list and install Docker:

```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## 2. Prepare the Application

1. **Clone the repository** (or just copy the necessary files: `docker-compose.prod.yml`).

```bash
mkdir activity-info-runner
cd activity-info-runner
# Copy docker-compose.prod.yml here
```

2. **Set Environment Variables**. Create a `.env` file:

```bash
# .env
API_TOKEN=your_activity_info_api_token
TEMPORAL_VERSION=1.29.1
TEMPORAL_ADMINTOOLS_VERSION=1.29.1-tctl-1.18.4-cli-1.5.0
TEMPORAL_UI_VERSION=2.34.0
POSTGRESQL_VERSION=16
POSTGRES_PASSWORD=temporal
POSTGRES_USER=temporal
```

## 3. Deploy the Stack

Run the production compose file:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Check logs to ensure everything started correctly:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

## 4. Set up Public Access (Nginx + SSL)

To expose your application securely on `https://runner.example.com`:

1. **Install Nginx and Certbot**:

```bash
sudo apt install nginx certbot python3-certbot-nginx
```

2. **Configure Nginx**:
   Create `/etc/nginx/sites-available/runner` with the following content:

   ```nginx
   server {
       server_name runner.example.com;

       location / {
           # Proxy to the Frontend Container (port 8080)
           proxy_pass http://localhost:8080;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       # The frontend Nginx already handles /api/ -> backend:8000 routing,
       # so we just need to proxy everything to port 8080.
   }
   ```

3. **Enable the site**:

```bash
sudo ln -s /etc/nginx/sites-available/runner /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

4. **Enable SSL (HTTPS)**:

```bash
sudo certbot --nginx -d runner.example.com
```

Now your application should be accessible at `https://runner.example.com`.

