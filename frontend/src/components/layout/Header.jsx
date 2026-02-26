import React from 'react';
import { useLocation } from 'react-router-dom';
import { Bars3Icon } from '@heroicons/react/24/outline';

const titles = {
  '/': 'Dashboard',
  '/entities': 'Entities',
  '/assets': 'Assets',
  '/ownerships': 'Ownerships',
  '/distributions': 'Distributions',
  '/reports': 'Reports',
};

export default function Header({ onMenuToggle }) {
  const location = useLocation();
  const title = titles[location.pathname] || 'Financial Accounting';
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <header className="bg-white border-b border-gray-200 px-4 sm:px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-1.5 -ml-1.5 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
        >
          <Bars3Icon className="h-6 w-6" />
        </button>
        <div>
          <h1 className="text-lg sm:text-xl font-semibold text-gray-900">{title}</h1>
          <p className="text-xs sm:text-sm text-gray-500 hidden sm:block">{today}</p>
        </div>
      </div>
    </header>
  );
}
