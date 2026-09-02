# 🚀 Deployment Guide

This guide covers deploying the HR Management System (backend + frontend) to the internet for free.

---

## Architecture

```
Frontend (Netlify)  →  Backend (Render)  →  OpenRouter API (LLM)
     React/Vite         FastAPI + ChromaDB       Qwen 2.5 72B
```

---

## Step 1: Deploy Backend on Render (Free)

### 1.1 Rename the requirements file
The file `deploy_requirements.txt` at the project root contains all Python dependencies.
Rename it to `requirements.txt` (replacing the existing folder) before deploying.

```bash
# Remove the requirements.txt folder
rm -rf requirements.txt
# Rename the deploy file
mv deploy_requirements.txt requirements.txt
```

### 1.2 Create a Render account
- Go to [render.com](https://render.com)
- Sign up with GitHub

### 1.3 Create a new Web Service
1. Click **New +** → **Web Service**
2. Connect your GitHub repo: `Yahya781/Human-Intelligence-System`
3. Configure:
   - **Name:** `hr-management-api`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

### 1.4 Set Environment Variables
In Render dashboard → **Environment** tab, add:

| Key | Value |
|-----|-------|
| `OPENROUTER_API_KEY` | `sk-or-v1-...` (your key) |
| `OPENROUTER_MODEL` | `qwen/qwen-2.5-72b-instruct:free` |
| `OPENROUTER_MODEL_BACKUP` | `nvidia/nemotron-3-ultra-550b-a55b:free` |

### 1.5 Deploy
- Click **Create Web Service**
- Wait for build to complete
- Your API will be live at: `https://hr-management-api.onrender.com`
- Swagger docs at: `https://hr-management-api.onrender.com/docs`

### ⚠️ Free Tier Limitations
- Service sleeps after 15 min of inactivity (first request after sleep takes ~30s)
- 750 hours/month of runtime
- ChromaDB data is **ephemeral** on free tier (resets on redeploy)
  - Data is rebuilt from JSON files on startup (see `app/services.py`)
  - For persistent data, upgrade to paid tier or use external DB

---

## Step 2: Deploy Frontend on Netlify (Free)

### 2.1 Create a Netlify account
- Go to [netlify.com](https://app.netlify.com)
- Sign up with GitHub

### 2.2 Import the project
1. Click **Add new site** → **Import an existing project**
2. Connect your GitHub account and select `Yahya781/Human-Intelligence-System`
3. Configure:
   - **Base directory:** `frontend`
   - **Build command:** `npm run build`
   - **Publish directory:** `frontend/dist`
   - **Node version:** 18 (or leave default)

> A `netlify.toml` file is already included in the `frontend/` folder
> with the correct build settings and SPA redirect rules.

### 2.3 Set Environment Variables
In Netlify → **Site settings** → **Environment variables**, add:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://hr-management-api.onrender.com` |

### 2.4 Frontend API config (already done)
The frontend reads the `VITE_API_URL` env var in production:

```javascript
const BASE = import.meta.env.VITE_API_URL || '/api'
```

- **Dev:** falls back to `/api` (Vite proxy → localhost:8000)
- **Prod:** uses the Netlify env var → your Render backend URL

### 2.5 Deploy
- Click **Deploy site**
- Your frontend will be live at: `https://hr-management-system.netlify.app`
- Netlify auto-deploys on every GitHub push

---

## Step 3: Update CORS for Production

In `app/main.py`, the CORS settings already read from the `CORS_ORIGINS` env var.
On Render, set:

```
CORS_ORIGINS=https://hr-management-system.netlify.app
```

If you need multiple origins, comma-separate them:

```
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,https://hr-management-system.netlify.app
```

---

## Step 4: Verify Deployment

1. Visit your backend Swagger docs: `https://hr-management-api.onrender.com/docs`
2. Test the `/candidates` endpoint — should return JSON
3. Visit your frontend: `https://hr-management-system.netlify.app`
4. Go to **View Matches** → select a job → verify AI ranking works

---

## Alternative: Deploy Everything on Render

If you prefer one platform, Render can also serve the frontend:

1. Build the frontend: `cd frontend && npm run build`
2. Configure Render to serve the `frontend/dist` folder as static files
3. Use a single Render service with both backend and static frontend

---

## Quick Reference

| Service | URL | Purpose |
|---------|-----|---------|
| Backend API | `https://hr-management-api.onrender.com` | FastAPI + ChromaDB |
| Swagger Docs | `https://hr-management-api.onrender.com/docs` | API documentation |
| Frontend | `https://hr-management-system.netlify.app` | React UI |

---

## Troubleshooting

### Backend won't start
- Check Render logs for import errors
- Ensure `requirements.txt` is a file, not a folder
- Verify `OPENROUTER_API_KEY` is set in Render environment

### Frontend can't reach API
- Verify `VITE_API_URL` is set in Netlify env vars
- Check that `CORS_ORIGINS` on Render includes your Netlify URL
- Ensure backend URL is correct (no trailing slash)
- After changing env vars, trigger a new deploy in Netlify

### ChromaDB errors
- ChromaDB is ephemeral on free tier — data resets on redeploy
- The app rebuilds ChromaDB from JSON on startup
- For persistent storage, upgrade to Render paid tier
