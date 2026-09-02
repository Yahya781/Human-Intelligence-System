import { useEffect, useState } from 'react'
import { getJobs, getMatches } from '../api'

export default function ViewMatches() {
  const [jobs, setJobs] = useState([])
  const [selectedJob, setSelectedJob] = useState(null)
  const [matches, setMatches] = useState([])
  const [loadingJobs, setLoadingJobs] = useState(true)
  const [loadingMatches, setLoadingMatches] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getJobs()
      .then(data => setJobs(data.jobs || []))
      .catch(err => setError(err.message))
      .finally(() => setLoadingJobs(false))
  }, [])

  const handleSelect = async (jobId) => {
    setSelectedJob(jobId)
    setLoadingMatches(true)
    setError(null)
    setMatches([])
    try {
      const data = await getMatches(jobId)
      setMatches(data.matches || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingMatches(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>View Matches</h1>
        <p>Select a job to see semantically ranked candidates</p>
      </div>

      {error && <div className="alert alert-error">❌ {error}</div>}

      <div className="card">
        <div className="card-title">Select a Job</div>
        {loadingJobs ? (
          <div className="loading"><div className="spinner" /> Loading jobs…</div>
        ) : jobs.length === 0 ? (
          <div className="alert alert-info">No jobs yet. Create a job first.</div>
        ) : (
          <select
            className="form-select"
            value={selectedJob || ''}
            onChange={e => handleSelect(Number(e.target.value))}
          >
            <option value="" disabled>Choose a job…</option>
            {jobs.map(job => (
              <option key={job.id} value={job.id}>
                #{job.id} — {job.title}
              </option>
            ))}
          </select>
        )}
      </div>

      {loadingMatches && (
        <div className="loading"><div className="spinner" /> AI is ranking candidates…</div>
      )}

      {!loadingMatches && matches.length > 0 && (
        <div className="card">
          <div className="card-title">Top {matches.length} Candidates — AI Ranked</div>
          {matches.map((match, idx) => {
            const c = match.candidate
            const aiScore = match.ai_fit_score || 0
            const aiExplain = match.ai_explanation || ''
            const semPct = (match.semantic_similarity * 100).toFixed(1)
            return (
              <div key={idx} className="match-card">
                <div className="match-rank">{idx + 1}</div>
                <div className="match-info">
                  <div className="match-name">{c.name}</div>
                  <div className="match-meta">
                    {c.experience_years} years experience
                  </div>
                  <div className="match-meta">
                    <strong>Matching Skills:</strong>{' '}
                    {match.matching_skills?.map(s => <span key={s} className="tag tag-match">{s}</span>)}
                    {(!match.matching_skills || match.matching_skills.length === 0) && (
                      <span style={{ color: 'var(--text-muted)' }}>No exact skill matches (semantic only)</span>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
                    <span className="match-score" style={{ color: 'var(--primary)' }}>
                      AI Fit: {aiScore}/100
                    </span>
                    <span className="match-similarity">
                      Semantic: {semPct}%
                    </span>
                  </div>
                  <div className="score-bar">
                    <div className="score-fill" style={{ width: `${aiScore}%` }} />
                  </div>
                  {aiExplain && (
                    <div style={{
                      marginTop: 10,
                      padding: '10px 14px',
                      background: 'var(--bg)',
                      borderRadius: 8,
                      fontSize: 14,
                      color: 'var(--text)',
                      border: '1px solid var(--border)'
                    }}>
                      <strong style={{ color: 'var(--primary)' }}>💡 AI Analysis:</strong> {aiExplain}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {!loadingMatches && selectedJob && matches.length === 0 && !error && (
        <div className="alert alert-info">No matching candidates found.</div>
      )}
    </>
  )
}
