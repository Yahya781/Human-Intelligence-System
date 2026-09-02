import { useEffect, useState } from 'react'
import { getCandidates, getJobs } from '../api'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [candidates, setCandidates] = useState([])
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getCandidates(), getJobs()])
      .then(([c, j]) => {
        setCandidates(c.candidates || [])
        setJobs(j.jobs || [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading"><div className="spinner" /> Loading dashboard…</div>

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Overview of your HR Management System</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">👥 Candidates</div>
          <p style={{ fontSize: 36, fontWeight: 700 }}>{candidates.length}</p>
          <Link to="/candidates" className="btn btn-secondary" style={{ marginTop: 12 }}>
            View all →
          </Link>
        </div>

        <div className="card">
          <div className="card-title">💼 Jobs</div>
          <p style={{ fontSize: 36, fontWeight: 700 }}>{jobs.length}</p>
          <Link to="/jobs" className="btn btn-secondary" style={{ marginTop: 12 }}>
            View all →
          </Link>
        </div>
      </div>

      <div className="card">
        <div className="card-title">⚡ Quick Actions</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Link to="/upload-cv" className="btn btn-primary">📄 Upload CV</Link>
          <Link to="/create-job" className="btn btn-primary">💼 Create Job</Link>
          <Link to="/matches" className="btn btn-primary">🎯 View Matches</Link>
        </div>
      </div>
    </>
  )
}
