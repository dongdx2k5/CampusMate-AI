'use client';

import React, { useState, useEffect } from 'react';
import { apiGet } from '@/lib/api';
import { ShieldCheck, Clock, User, Filter, RefreshCw, FileText } from 'lucide-react';

interface AuditLogItem {
  id: string;
  actorId?: string;
  actorName?: string;
  action: string;
  targetType: string;
  targetId: string;
  metadata?: any;
  createdAt: string;
}

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await apiGet<{ items: AuditLogItem[]; total: number }>('/admin/audit-logs?page=1&size=50');
      setLogs(res.items || []);
    } catch {
      // Mock data
      setLogs([
        {
          id: 'log-1',
          actorName: 'Quản trị viên Hệ thống',
          action: 'REINDEX_DOCUMENT',
          targetType: 'DOCUMENT_VERSION',
          targetId: 'v-2025',
          metadata: { chunks_count: 4 },
          createdAt: new Date().toISOString(),
        },
        {
          id: 'log-2',
          actorName: 'ThS. Lê Thị Cúc',
          action: 'PUBLISH_ANNOUNCEMENT',
          targetType: 'ANNOUNCEMENT',
          targetId: 'a-pub',
          metadata: { status: 'PUBLISHED', scope: 'SCHOOL' },
          createdAt: new Date(Date.now() - 3600000).toISOString(),
        },
        {
          id: 'log-3',
          actorName: 'Quản trị viên Hệ thống',
          action: 'UPDATE_USER_ROLE',
          targetType: 'USER',
          targetId: 'u-1',
          metadata: { oldRole: 'STUDENT', newRole: 'STAFF' },
          createdAt: new Date(Date.now() - 7200000).toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2.5 py-1 rounded-full">
            Tuân thủ & An ninh
          </span>
          <h1 className="text-2xl font-bold text-gray-900 mt-1 flex items-center space-x-2">
            <ShieldCheck className="w-6 h-6 text-purple-600" />
            <span>Nhật ký kiểm toán hệ thống (Audit Logs)</span>
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Lưu vết toàn bộ thao tác quan trọng: duyệt văn bản, lập chỉ mục AI, thu hồi thông báo và thay đổi quyền hạn.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="p-2.5 rounded-xl border border-gray-200 hover:bg-gray-50 text-gray-600 transition"
          title="Tải lại"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-slate-50 text-gray-500 uppercase text-[10px] tracking-wider font-semibold border-b border-gray-200">
              <tr>
                <th className="py-3 px-4">Thời gian</th>
                <th className="py-3 px-4">Người thực hiện</th>
                <th className="py-3 px-4">Hành động (Action)</th>
                <th className="py-3 px-4">Đối tượng tác động</th>
                <th className="py-3 px-4">Chi tiết (Metadata)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/70 transition">
                  <td className="py-3 px-4 text-gray-500 text-xs whitespace-nowrap">
                    {new Date(log.createdAt).toLocaleString('vi-VN')}
                  </td>
                  <td className="py-3 px-4 font-semibold text-gray-900 flex items-center space-x-1.5">
                    <User className="w-3.5 h-3.5 text-gray-400" />
                    <span>{log.actorName || 'Hệ thống'}</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-700">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600 text-xs">
                    {log.targetType}: <span className="font-mono">{log.targetId}</span>
                  </td>
                  <td className="py-3 px-4 text-xs font-mono text-gray-500 max-w-xs truncate">
                    {log.metadata ? JSON.stringify(log.metadata) : '-'}
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

