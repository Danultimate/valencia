import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Oportunidades from './pages/Oportunidades'
import Subastas from './pages/Subastas'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/oportunidades" replace />} />
          <Route path="/oportunidades" element={<Oportunidades />} />
          <Route path="/subastas" element={<Subastas />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
