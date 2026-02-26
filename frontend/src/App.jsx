import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Entities from './pages/Entities';
import Assets from './pages/Assets';
import Ownerships from './pages/Ownerships';
import Distributions from './pages/Distributions';
import Budgets from './pages/Budgets';
import Reports from './pages/Reports';

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/+$/, '')}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="entities" element={<Entities />} />
          <Route path="assets" element={<Assets />} />
          <Route path="ownerships" element={<Ownerships />} />
          <Route path="distributions" element={<Distributions />} />
          <Route path="budgets" element={<Budgets />} />
          <Route path="reports" element={<Reports />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
