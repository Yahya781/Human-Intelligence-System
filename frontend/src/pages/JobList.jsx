import { useEffect, useState } from 'react'
import { getJobs } from '../api'
import { Link } from 'react-router-dom'

export default function JobList() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getJobs()
      .then(data => setJobs(data.jobs || []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading"><div className="spinner" /> Loading jobs…</div>

  return (
    <>
      <div className="page-header">
        <h1>Jobs</h1>
        <p>All posted jobs in the system</p>
      </div>

      {error && <div className="alert alert-error">❌ {error}</div>}

      {jobs.length === 0 ? (
        <div className="alert alert-info">No jobs yet. <Link to="/create-job">Create a job</Link> to get started.</div>
      ) : (
        jobs.map(job => (
          <div key={job.id} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="card-title">{job.title}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 8 }}>
                  Job ID: {job.id}
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Required Skills:</strong>{' '}
                  {job.required_skills?.map(s => <span key={s} className="tag">{s}</span>)}
                </div>
                {job.summary && (
                  <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>{job.summary}</div>
                )}
                {job.description && (
                  <div style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 4 }}>{job.description}</div>
                )}
              </div>
              <Link to="/matches" className="btn btn-secondary">View Matches →</Link>
            </div>
          </div>
        ))
      )}
    </>
  )
}
