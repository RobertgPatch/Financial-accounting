import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Entities from './pages/Entities';
import EntityDetail from './pages/EntityDetail';
import Assets from './pages/Assets';
import AssetDetail from './pages/AssetDetail';
import Ownerships from './pages/Ownerships';
import Distributions from './pages/Distributions';
import Budgets from './pages/Budgets';
import Reports from './pages/Reports';
import Accounts from './pages/Accounts';
import K1Upload from './pages/K1Upload';
import K1Review from './pages/K1Review';
import K1Documents from './pages/K1Documents';

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/+$/, '')}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="entities" element={<Entities />} />
            <Route path="entities/:id" element={<EntityDetail />} />
            <Route path="assets" element={<Assets />} />
            <Route path="assets/:id" element={<AssetDetail />} />
            <Route path="ownerships" element={<Ownerships />} />
            <Route path="distributions" element={<Distributions />} />
            <Route path="budgets" element={<Budgets />} />
            <Route path="accounts" element={<Accounts />} />
            <Route path="reports" element={<Reports />} />
            <Route path="k1" element={<K1Documents />} />
            <Route path="k1/upload" element={<K1Upload />} />
            <Route path="k1/:id/review" element={<K1Review />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
