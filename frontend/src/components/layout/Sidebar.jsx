import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  HomeIcon,
  BuildingOfficeIcon,
  CubeIcon,
  LinkIcon,
  BanknotesIcon,
  ChartBarIcon,
  XMarkIcon,
  CalculatorIcon,
  BuildingLibraryIcon,
} from '@heroicons/react/24/outline';

const navItems = [
  { path: '/', label: 'Dashboard', icon: HomeIcon },
  { path: '/entities', label: 'Entities', icon: BuildingOfficeIcon },
  { path: '/assets', label: 'Assets', icon: CubeIcon },
  { path: '/ownerships', label: 'Ownerships', icon: LinkIcon },
  { path: '/distributions', label: 'Distributions', icon: BanknotesIcon },
  { path: '/budgets', label: 'Budgets', icon: CalculatorIcon },
  { path: '/accounts', label: 'Accounts', icon: BuildingLibraryIcon },
  { path: '/reports', label: 'Reports', icon: ChartBarIcon },
];

export default function Sidebar({ isOpen, onClose }) {
  return (
    <aside
      className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-[#0F172A] flex flex-col
        transform transition-transform duration-200 ease-in-out
        lg:relative lg:translate-x-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}
    >
      <div className="px-6 py-6 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <BanknotesIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-white font-semibold text-sm">FinAccounting</p>
            <p className="text-gray-400 text-xs">Portfolio Tracker</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="lg:hidden text-gray-400 hover:text-white transition-colors"
        >
          <XMarkIcon className="h-5 w-5" />
        </button>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <Icon className="h-5 w-5 flex-shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-4 border-t border-white/10">
        <p className="text-gray-500 text-xs text-center">v1.0.0</p>
      </div>
    </aside>
  );
}
