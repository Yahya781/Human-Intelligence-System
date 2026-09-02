import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import UploadCV from './pages/UploadCV.jsx'
import CreateJob from './pages/CreateJob.jsx'
import ViewMatches from './pages/ViewMatches.jsx'
import CandidateList from './pages/CandidateList.jsx'
import JobList from './pages/JobList.jsx'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/upload-cv" element={<UploadCV />} />
        <Route path="/create-job" element={<CreateJob />} />
        <Route path="/matches" element={<ViewMatches />} />
        <Route path="/candidates" element={<CandidateList />} />
        <Route path="/jobs" element={<JobList />} />
      </Routes>
    </Layout>
  )
}
