# william

AI news aggregator — auto-collects, ranks, and publishes a weekly newsletter.

## Architecture

- **Backend**: FastAPI + SQLite, scheduled news/video collection via Tavily + YouTube APIs, GPT-based ranking
- **Frontend**: Next.js newsletter UI
- **Deploy**: Docker images built by GitHub Actions (ARM64), pulled on Raspberry Pi, exposed via Cloudflare Tunnel

## Local dev

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.dev.example .env.dev   # fill in API keys (or use existing .env.dev)
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Pi setup (one-time)

```bash
ssh pi@192.168.1.234
mkdir -p ~/Deployment/william
cd ~/Deployment/william

# Create .env.prod with:
cat > .env.prod << 'EOF'
OPENAI_API_KEY=...
YOUTUBE_API_KEY=...
TAVILY_API_KEY=...
TUNNEL_TOKEN=...
NEWSLETTER_DATABASE_URL=sqlite:////app/data/newsletter.db
CORS_ORIGINS=http://localhost:3000
EOF
```

## Deploy

Push to `main` → GitHub Actions builds ARM64 images → push to Docker Hub.

Then run:

```bash
./deploy.sh
```

This syncs `docker-compose.yml` to the Pi and pulls the latest images. Watchtower also auto-updates every 5 minutes.
