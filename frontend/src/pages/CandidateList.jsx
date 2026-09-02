import { useEffect, useState } from 'react'
import { getCandidates } from '../api'

export default function CandidateList() {
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getCandidates()
      .then(data => setCandidates(data.candidates || []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading"><div className="spinner" /> Loading candidates…</div>

  return (
    <>
      <div className="page-header">
        <h1>Candidates</h1>
        <p>All stored candidates in the system</p>
      </div>

      {error && <div className="alert alert-error">❌ {error}</div>}

      {candidates.length === 0 ? (
        <div className="alert alert-info">No candidates yet. Upload a CV to get started.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Skills</th>
                <th>Experience</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map(c => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td><strong>{c.name}</strong></td>
                  <td>{c.skills?.map(s => <span key={s} className="tag">{s}</span>)}</td>
                  <td>{c.experience_years} yrs</td>
                  <td style={{ maxWidth: 300, color: 'var(--text-muted)' }}>{c.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
