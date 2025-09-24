import { useState } from 'react'
import {BrowserRouter as Router, Route, Routes} from 'react-router-dom'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'
import './App.css'
import DashboardLayout from './components/DashboardLayout'
import DashboardPage from './components/DashboardPage'
import UploadPage from './components/UploadPage'
import AnalyticsPage from './components/AnalyticsPage'
import DocumentsPage from './components/DocumentsPage'
import HistoryPage from './components/HistoryPage'
import ProfilePage from './components/ProfilePage'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RegisterPage />} />
          <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          </Route>
        </Routes>
      </Router>
    </>
  )
}

export default App
