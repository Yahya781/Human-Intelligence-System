import { useState } from 'react'
import { uploadCVText, uploadCVPDF } from '../api'

export default function UploadCV() {
  const [tab, setTab] = useState('text')
  const [cvText, setCvText] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleTextSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await uploadCVText(cvText)
      setResult(data.candidate)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handlePDFSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await uploadCVPDF(file)
      setResult(data.candidate)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Upload CV</h1>
        <p>Paste CV text or upload a PDF — AI will extract skills, experience, and summary</p>
      </div>

      <div className="tabs">
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
          ✅ <strong>{result.name}</strong> saved successfully!
          <div style={{ marginTop: 8 }}>
            <strong>Skills:</strong> {result.skills?.map(s => <span key={s} className="tag">{s}</span>)}
          </div>
          <div style={{ marginTop: 4 }}><strong>Experience:</strong> {result.experience_years} years</div>
          <div style={{ marginTop: 4 }}><strong>Summary:</strong> {result.summary}</div>
        </div>
      )}

      {tab === 'text' ? (
        <form onSubmit={handleTextSubmit}>
          <div className="card">
            <div className="form-group">
              <label>CV Text</label>
              <textarea
                className="form-textarea"
                value={cvText}
                onChange={(e) => setCvText(e.target.value)}
                placeholder="Paste the full CV text here…"
                required
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading || !cvText.trim()}>
              {loading ? <><div className="spinner" /> Extracting…</> : 'Extract & Save'}
            </button>
          </div>
        </form>
      ) : (
        <form onSubmit={handlePDFSubmit}>
          <div className="card">
            <label className="file-drop">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files[0])}
              />
              {file ? (
                <p>📎 {file.name} ({(file.size / 1024).toFixed(1)} KB)</p>
              ) : (
                <p>📁 Click to select a PDF file</p>
              )}
            </label>
            <button type="submit" className="btn btn-primary" disabled={loading || !file} style={{ marginTop: 16 }}>
              {loading ? <><div className="spinner" /> Extracting…</> : 'Extract & Save'}
            </button>
          </div>
        </form>
      )}
    </>
  )
}
