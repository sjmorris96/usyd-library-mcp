# USyd Library MCP Server

Connects Claude to the University of Sydney Library catalogue via the Primo search API.

## What it does

Gives Claude two tools:
- **search_library** – search the USyd catalogue for books, articles, journals, and more
- **get_library_databases** – find subject-specific research databases

## Deploy to Railway (free)

### 1. Create a GitHub repository

1. Go to [github.com](https://github.com) and sign in (or create a free account)
2. Click **New repository**
3. Name it `usyd-library-mcp`, set it to **Public**, click **Create repository**
4. Upload these files: `server.py`, `requirements.txt`, `Procfile`, `railway.toml`

### 2. Deploy on Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **New Project → Deploy from GitHub repo**
3. Select your `usyd-library-mcp` repository
4. Railway will detect the Python app and start building

### 3. Add your API key (optional)

If you have a Primo API key:
1. In Railway, go to your project → **Variables**
2. Add: `PRIMO_API_KEY` = your key

If you skip this, the server uses the public catalogue endpoint (works fine for most searches).

### 4. Get your URL

1. In Railway, go to **Settings → Networking → Generate Domain**
2. Your URL will look like: `https://usyd-library-mcp-production.up.railway.app`

### 5. Connect to Claude

1. Go to [claude.ai/settings/connectors](https://claude.ai/settings/connectors)
2. Click **Add custom connector**
3. Name: `USyd Library`
4. URL: your Railway URL + `/mcp` (e.g. `https://your-app.up.railway.app/mcp`)
5. Click **Add** then **Connect**

## Usage examples

Once connected, you can ask Claude things like:
- "Search the USyd library for books on urban planning"
- "Find recent articles about CRISPR gene editing in the library"
- "What databases does USyd have for psychology research?"
