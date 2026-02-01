import React from 'react'
import { Routes, Route } from 'react-router-dom'
import MainLayout from './components/MainLayout'
import PaperManagement from './pages/PaperManagement'
import GraphVisualization from './pages/GraphVisualization'
import QAAssistant from './pages/QAAssistant'
import EntityBrowser from './pages/EntityBrowser'

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<PaperManagement />} />
        <Route path="papers" element={<PaperManagement />} />
        <Route path="graph" element={<GraphVisualization />} />
        <Route path="qa" element={<QAAssistant />} />
        <Route path="entities" element={<EntityBrowser />} />
      </Route>
    </Routes>
  )
}

export default AppRoutes