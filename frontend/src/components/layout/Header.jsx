import React from 'react';
import { useLocation } from 'react-router-dom';

const titles = {
  '/': 'Dashboard',
  '/entities': 'Entities',
  '/assets': 'Assets',
  '/ownerships': 'Ownerships',
  '/distributions': 'Distributions',
  '/reports': 'Reports',
};

export default function Header() {
  const location = useLocation();
  const title = titles[location.pathname] || 'Financial Accounting';
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
        <p className="text-sm text-gray-500">{today}</p>
      </div>
    </header>
  );
}
