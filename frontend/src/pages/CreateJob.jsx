import { useState } from 'react'
import { createJob, uploadJobText, uploadJobPDF } from '../api'

export default function CreateJob() {
  const [tab, setTab] = useState('manual')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Manual form state
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [skills, setSkills] = useState('')

  // Text paste state
  const [jobText, setJobText] = useState('')

  // PDF state
  const [file, setFile] = useState(null)

  const handleManual = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await createJob({
        title,
        description,
        required_skills: skills.split(',').map(s => s.trim()).filter(Boolean),
      })
      setResult(data.job)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleText = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await uploadJobText(jobText)
      setResult(data.job)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handlePDF = async (e) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await uploadJobPDF(file)
      setResult(data.job)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Create Job</h1>
        <p>Manually create a job, paste a description, or upload a PDF</p>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === 'manual' ? 'active' : ''}`} onClick={() => setTab('manual')}>
          ✏️ Manual
        </button>
        <button className={`tab ${tab === 'text' ? 'active' : ''}`} onClick={() => setTab('text')}>
          📝 Paste Text
        </button>
        <button className={`tab ${tab === 'pdf' ? 'active' : ''}`} onClick={() => setTab('pdf')}>
          📎 Upload PDF
        </button>
      </div>

      {error && <div className="alert alert-error">❌ {error}</div>}
      {result && (
        <div className="alert alert-success">
          ✅ <strong>{result.title}</strong> created! (ID: {result.id})
          <div style={{ marginTop: 8 }}>
            <strong>Required Skills:</strong> {result.required_skills?.map(s => <span key={s} className="tag">{s}</span>)}
          </div>
          {result.summary && <div style={{ marginTop: 4 }}><strong>Summary:</strong> {result.summary}</div>}
        </div>
      )}

      {tab === 'manual' && (
        <form onSubmit={handleManual}>
          <div className="card">
            <div className="form-group">
              <label>Job Title</label>
              <input className="form-input" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Python Backend Developer" required />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea className="form-textarea" value={description} onChange={e => setDescription(e.target.value)} placeholder="Job description…" required />
            </div>
            <div className="form-group">
              <label>Required Skills (comma-separated)</label>
              <input className="form-input" value={skills} onChange={e => setSkills(e.target.value)} placeholder="Python, FastAPI, PostgreSQL" required />
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <><div className="spinner" /> Creating…</> : 'Create Job'}
            </button>
          </div>
        </form>
      )}

      {tab === 'text' && (
        <form onSubmit={handleText}>
          <div className="card">
            <div className="form-group">
              <label>Job Description Text</label>
              <textarea className="form-textarea" value={jobText} onChange={e => setJobText(e.target.value)} placeholder="Paste the full job description here…" required />
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading || !jobText.trim()}>
              {loading ? <><div className="spinner" /> Extracting…</> : 'Extract & Create'}
            </button>
          </div>
        </form>
      )}

      {tab === 'pdf' && (
        <form onSubmit={handlePDF}>
          <div className="card">
            <label className="file-drop">
              <input type="file" accept=".pdf" onChange={e => setFile(e.target.files[0])} />
              {file ? <p>📎 {file.name}</p> : <p>📁 Click to select a PDF file</p>}
            </label>
            <button type="submit" className="btn btn-primary" disabled={loading || !file} style={{ marginTop: 16 }}>
              {loading ? <><div className="spinner" /> Extracting…</> : 'Extract & Create'}
            </button>
          </div>
        </form>
      )}
    </>
  )
}
