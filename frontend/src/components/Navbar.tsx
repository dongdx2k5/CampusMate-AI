'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth, UserRole } from '@/lib/auth';
import { 
  Bot, 
  Calendar, 
  Bell, 
  DoorOpen, 
  FileText, 
  Settings, 
  BarChart3, 
  Users, 
  ShieldCheck, 
  ChevronDown, 
  Menu, 
  X,
  FileCheck2
} from 'lucide-react';

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const { user, role, switchRole } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);

  const isStaffOrAdmin = role === 'STAFF' || role === 'ADMIN';

  const portalLinks = [
    { href: '/', label: 'Trợ lý AI', icon: Bot },
    { href: '/schedule', label: 'Lịch cá nhân', icon: Calendar },
    { href: '/announcements', label: 'Thông báo', icon: Bell },
    { href: '/rooms', label: 'Tìm phòng trống', icon: DoorOpen },
    { href: '/services', label: 'Dịch vụ sinh viên', icon: FileText },
  ];

  const adminLinks = [
    { href: '/admin/announcements', label: 'Duyệt thông báo', icon: Bell },
    { href: '/admin/documents', label: 'Kho quy chế & AI', icon: FileCheck2 },
    { href: '/admin/analytics', label: 'Phân tích & Khoảng trống', icon: BarChart3 },
    { href: '/admin/users', label: 'Người dùng', icon: Users },
    { href: '/admin/audit-logs', label: 'Kiểm toán', icon: ShieldCheck },
  ];

  const rolesList: { id: UserRole; label: string; badge: string }[] = [
    { id: 'STUDENT', label: 'Sinh viên', badge: 'bg-blue-100 text-blue-800' },
    { id: 'LECTURER', label: 'Giảng viên', badge: 'bg-green-100 text-green-800' },
    { id: 'STAFF', label: 'Cán bộ phòng ban', badge: 'bg-amber-100 text-amber-800' },
    { id: 'ADMIN', label: 'Quản trị viên', badge: 'bg-purple-100 text-purple-800' },
  ];

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-primary-500 flex items-center justify-center text-white shadow-md">
                <Bot className="w-6 h-6" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-lg text-gray-900 leading-tight">CampusMate AI</span>
                <span className="text-xs text-gray-500">Trợ lý số đại học</span>
              </div>
            </Link>

            {/* Desktop Navigation Links */}
            <div className="hidden md:flex ml-6 space-x-1">
              {portalLinks.map((link) => {
                const Icon = link.icon;
                const active = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`inline-flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      active
                        ? 'bg-indigo-50 text-indigo-700 font-semibold'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="w-4 h-4 mr-1.5" />
                    {link.label}
                  </Link>
                );
              })}

              {isStaffOrAdmin && (
                <div className="h-6 w-px bg-gray-200 mx-2 self-center" />
              )}

              {isStaffOrAdmin &&
                adminLinks.map((link) => {
                  const Icon = link.icon;
                  const active = pathname.startsWith(link.href);
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`inline-flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        active
                          ? 'bg-purple-50 text-purple-700 font-semibold'
                          : 'text-gray-600 hover:text-purple-700 hover:bg-purple-50/50'
                      }`}
                    >
                      <Icon className="w-4 h-4 mr-1.5" />
                      {link.label}
                    </Link>
                  );
                })}
            </div>
          </div>

          {/* Right: Role Switcher & User Profile */}
          <div className="flex items-center space-x-3">
            {/* Quick Demo Role Switcher */}
            <div className="relative">
              <button
                onClick={() => setRoleMenuOpen(!roleMenuOpen)}
                className="flex items-center space-x-2 text-xs font-medium px-3 py-1.5 rounded-full border border-gray-300 hover:border-gray-400 bg-gray-50 transition"
              >
                <span className="text-gray-500 hidden sm:inline">Chuyển vai trò:</span>
                <span className="font-semibold text-gray-900">
                  {rolesList.find((r) => r.id === role)?.label}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
              </button>

              {roleMenuOpen && (
                <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-lg border border-gray-100 py-1.5 z-50">
                  <div className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Thử nghiệm vai trò (RBAC)
                  </div>
                  {rolesList.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => {
                        switchRole(r.id);
                        setRoleMenuOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-gray-50 ${
                        role === r.id ? 'bg-indigo-50/70 font-semibold text-indigo-700' : 'text-gray-700'
                      }`}
                    >
                      <span>{r.label}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] ${r.badge}`}>
                        {r.id}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* User display */}
            <div className="hidden sm:flex flex-col text-right">
              <span className="text-xs font-semibold text-gray-900 truncate max-w-[130px]">
                {user?.fullName || 'Người dùng'}
              </span>
              <span className="text-[10px] text-gray-500">
                {user?.cohort ? `${user.cohort} - ${user.major}` : user?.email}
              </span>
            </div>

            {/* Mobile menu toggle */}
            <div className="flex md:hidden">
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="p-2 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200 px-4 pt-2 pb-4 space-y-1 bg-white">
          <div className="text-xs font-semibold text-gray-400 px-3 py-1 uppercase">Cổng Sinh viên & Giảng viên</div>
          {portalLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-gray-100"
            >
              <link.icon className="w-4 h-4 mr-2" />
              {link.label}
            </Link>
          ))}

          {isStaffOrAdmin && (
            <>
              <div className="text-xs font-semibold text-purple-600 px-3 pt-3 py-1 uppercase">Cổng Cán bộ & Quản trị</div>
              {adminLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-purple-50"
                >
                  <link.icon className="w-4 h-4 mr-2 text-purple-600" />
                  {link.label}
                </Link>
              ))}
            </>
          )}
        </div>
      )}
    </nav>
  );
};

