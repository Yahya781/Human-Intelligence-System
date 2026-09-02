// ── API Client ──
// Dev:  Vite proxy /api → http://127.0.0.1:8000
// Prod: VITE_API_URL env var (set on Vercel/Netlify)

const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json()
}

// ── Candidates ──

export async function uploadCVText(cvText) {
  return request('/upload-cv', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cv_text: cvText }),
  })
}

export async function uploadCVPDF(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('/upload-cv-pdf', {
    method: 'POST',
    body: formData,
  })
}

// ── Jobs ──

export async function createJob(jobData) {
  return request('/create-job', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(jobData),
  })
}

export async function uploadJobText(jobText) {
  return request('/upload-job', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: jobText,
  })
}

export async function uploadJobPDF(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('/upload-job-pdf', {
    method: 'POST',
    body: formData,
  })
}

// ── Matching ──

export async function getMatches(jobId) {
  return request(`/matches/${jobId}`)
}

// ── Data (read JSON files directly via a new endpoint, or use existing data) ──
// We'll add lightweight endpoints to main.py for listing candidates and jobs.

export async function getCandidates() {
  return request('/candidates')
}

export async function getJobs() {
  return request('/jobs')
}
