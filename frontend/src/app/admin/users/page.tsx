'use client';

import React, { useState, useEffect } from 'react';
import { apiGet, apiPost } from '@/lib/api';
import { useAuth, UserRole } from '@/lib/auth';
import { Users, Shield, CheckCircle2, UserCheck, RefreshCw } from 'lucide-react';

interface UserItem {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  unitId?: string;
  cohort?: string;
  major?: string;
  isActive: boolean;
}

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await apiGet<UserItem[]>('/admin/users');
      setUsers(data || []);
    } catch {
      // Mock data
      setUsers([
        {
          id: 'u-1',
          email: 'demo.student@uni.edu.vn',
          fullName: 'Nguyễn Văn An',
          role: 'STUDENT',
          cohort: 'K65',
          major: 'Khoa học Máy tính',
          isActive: true,
        },
        {
          id: 'u-2',
          email: 'demo.lecturer@uni.edu.vn',
          fullName: 'TS. Trần Văn Bình',
          role: 'LECTURER',
          isActive: true,
        },
        {
          id: 'u-3',
          email: 'demo.staff@uni.edu.vn',
          fullName: 'ThS. Lê Thị Cúc',
          role: 'STAFF',
          isActive: true,
        },
        {
          id: 'u-4',
          email: 'demo.admin@uni.edu.vn',
          fullName: 'Quản trị viên Hệ thống',
          role: 'ADMIN',
          isActive: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleRoleChange = async (userId: string, newRole: UserRole) => {
    setUpdatingId(userId);
    try {
      await apiPost(`/admin/users/${userId}/role`, { role: newRole });
      setMsg(`Đã cập nhật vai trò người dùng thành ${newRole} và lưu vết AuditLog.`);
      await fetchUsers();
    } catch (err: any) {
      setMsg(err.message || 'Lỗi khi cập nhật vai trò.');
    } finally {
      setUpdatingId(null);
    }
  };

  const roles = [
    { value: 'STUDENT', label: 'Sinh viên' },
    { value: 'LECTURER', label: 'Giảng viên' },
    { value: 'STAFF', label: 'Cán bộ phòng ban' },
    { value: 'ADMIN', label: 'Quản trị viên' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2.5 py-1 rounded-full">
            Quản trị định danh & RBAC
          </span>
          <h1 className="text-2xl font-bold text-gray-900 mt-1 flex items-center space-x-2">
            <Users className="w-6 h-6 text-purple-600" />
            <span>Danh sách người dùng & Phân quyền</span>
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Quản lý vai trò (STUDENT, LECTURER, STAFF, ADMIN). Mọi thay đổi quyền hạn đều được ghi vết vào Audit Log.
          </p>
        </div>

        <button
          onClick={fetchUsers}
          className="p-2.5 rounded-xl border border-gray-200 hover:bg-gray-50 text-gray-600 transition"
          title="Tải lại danh sách"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {msg && (
        <div className="p-3.5 rounded-xl bg-purple-50 text-purple-900 border border-purple-200 text-xs flex items-center justify-between">
          <span>{msg}</span>
          <button onClick={() => setMsg(null)} className="text-purple-400 hover:text-purple-700">×</button>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-slate-50 text-gray-500 uppercase text-[10px] tracking-wider font-semibold border-b border-gray-200">
              <tr>
                <th className="py-3 px-4">Họ và tên</th>
                <th className="py-3 px-4">Email đăng nhập</th>
                <th className="py-3 px-4">Khóa / Ngành</th>
                <th className="py-3 px-4">Trạng thái</th>
                <th className="py-3 px-4">Vai trò (RBAC)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/70 transition">
                  <td className="py-3.5 px-4 font-bold text-gray-900 flex items-center space-x-2">
                    <UserCheck className="w-4 h-4 text-gray-400" />
                    <span>{u.fullName}</span>
                  </td>
                  <td className="py-3.5 px-4 text-gray-600">{u.email}</td>
                  <td className="py-3.5 px-4 text-gray-500 text-xs">
                    {u.cohort ? `${u.cohort} - ${u.major}` : 'Cán bộ'}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                      Hoạt động
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <select
                      value={u.role}
                      disabled={updatingId === u.id}
                      onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                      className="px-2.5 py-1 text-xs font-semibold rounded-lg border border-gray-300 bg-white focus:ring-1 focus:ring-purple-500"
                    >
                      {roles.map((r) => (
                        <option key={r.value} value={r.value}>
                          {r.label} ({r.value})
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

