'use client';

import React, { useState, useEffect } from 'react';
import { apiGet, apiPost } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { AnnouncementEditor } from '@/components/AnnouncementEditor';
import { 
  Bell, 
  Plus, 
  CheckCircle, 
  RotateCcw, 
  Clock, 
  AlertTriangle, 
  Send,
  Eye,
  ShieldAlert
} from 'lucide-react';

interface AnnouncementItem {
  id: string;
  unitId: string;
  title: string;
  body: string;
  audience: {
    scope: 'SCHOOL' | 'UNIT';
    unit_ids: string[];
    cohorts: string[];
    majors: string[];
  };
  status: 'DRAFT' | 'PENDING_APPROVAL' | 'SCHEDULED' | 'PUBLISHED' | 'REVOKED';
  publishAt?: string;
  createdAt: string;
}

export default function AdminAnnouncementsPage() {
  const { user, role } = useAuth();
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<{ text: string; error?: boolean } | null>(null);

  const fetchAnnouncements = async () => {
    setLoading(true);
    try {
      const res = await apiGet<{ items: AnnouncementItem[] }>('/announcements?page=1&size=50');
      setAnnouncements(res.items || []);
    } catch {
      // Mock data
      setAnnouncements([
        {
          id: 'a-draft',
          unitId: 'u1',
          title: 'Dự thảo quy định xét miễn giảm học phí cho sinh viên khó khăn năm 2026',
          body: 'Nội dung dự thảo đang được Phòng Đào tạo và Phòng CTSV lấy ý kiến...',
          audience: { scope: 'SCHOOL', unit_ids: [], cohorts: [], majors: [] },
          status: 'PENDING_APPROVAL',
          createdAt: new Date().toISOString(),
        },
        {
          id: 'a-pub',
          unitId: 'u1',
          title: 'Kế hoạch đăng ký học phần học kỳ 2 năm học 2025-2026',
          body: 'Phòng Đào tạo thông báo kế hoạch đăng ký học phần...',
          audience: { scope: 'SCHOOL', unit_ids: [], cohorts: [], majors: [] },
          status: 'PUBLISHED',
          publishAt: new Date(Date.now() - 86400000).toISOString(),
          createdAt: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnnouncements();
  }, [user]);

  const handlePublish = async (id: string) => {
    try {
      await apiPost(`/admin/announcements/${id}/publish`);
      setActionMsg({ text: 'Đã phê duyệt và đăng thông báo thành công!' });
      await fetchAnnouncements();
    } catch (err: any) {
      setActionMsg({ text: err.message || 'Không thể đăng thông báo.', error: true });
    }
  };

  const handleRevoke = async (id: string) => {
    const reason = window.prompt('Nhập lý do thu hồi thông báo:');
    if (!reason) return;

    try {
      await apiPost(`/admin/announcements/${id}/revoke`, { reason });
      setActionMsg({ text: 'Đã thu hồi thông báo và lưu vết kiểm toán (BR05).' });
      await fetchAnnouncements();
    } catch (err: any) {
      setActionMsg({ text: err.message || 'Lỗi khi thu hồi.', error: true });
    }
  };

  const statusBadge = (status: AnnouncementItem['status']) => {
    switch (status) {
      case 'DRAFT':
        return <span className="bg-gray-100 text-gray-700 px-2.5 py-0.5 rounded-full text-xs font-semibold">Nháp (DRAFT)</span>;
      case 'PENDING_APPROVAL':
        return <span className="bg-amber-100 text-amber-800 px-2.5 py-0.5 rounded-full text-xs font-semibold">Chờ duyệt (PENDING)</span>;
      case 'SCHEDULED':
        return <span className="bg-blue-100 text-blue-800 px-2.5 py-0.5 rounded-full text-xs font-semibold">Hẹn giờ đăng</span>;
      case 'PUBLISHED':
        return <span className="bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded-full text-xs font-semibold">Đã đăng (PUBLISHED)</span>;
      case 'REVOKED':
        return <span className="bg-rose-100 text-rose-800 px-2.5 py-0.5 rounded-full text-xs font-semibold">Đã thu hồi (REVOKED)</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2.5 py-1 rounded-full">
            Cổng Cán bộ & Quản trị
          </span>
          <h1 className="text-2xl font-bold text-gray-900 mt-1 flex items-center space-x-2">
            <Bell className="w-6 h-6 text-purple-600" />
            <span>Quản trị quy trình thông báo (FSM BR05)</span>
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Máy trạng thái kiểm soát luồng duyệt cấp Khoa và cấp Toàn trường. Không xóa cứng, lưu vết kiểm toán.
          </p>
        </div>

        <button
          onClick={() => setIsEditorOpen(true)}
          className="inline-flex items-center px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs sm:text-sm font-semibold shadow-xs transition"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          Soạn thông báo mới
        </button>
      </div>

      {actionMsg && (
        <div
          className={`p-4 rounded-xl text-xs font-medium border flex items-center justify-between ${
            actionMsg.error ? 'bg-rose-50 text-rose-800 border-rose-200' : 'bg-emerald-50 text-emerald-800 border-emerald-200'
          }`}
        >
          <span>{actionMsg.text}</span>
          <button onClick={() => setActionMsg(null)} className="text-gray-400 hover:text-gray-600">×</button>
        </div>
      )}

      {/* Announcements Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-slate-50 border-b border-gray-200 text-gray-500 uppercase text-[11px] tracking-wider font-semibold">
              <tr>
                <th className="py-3.5 px-4">Tiêu đề thông báo</th>
                <th className="py-3.5 px-4">Phạm vi (Scope)</th>
                <th className="py-3.5 px-4">Trạng thái (FSM)</th>
                <th className="py-3.5 px-4">Ngày tạo</th>
                <th className="py-3.5 px-4 text-right">Thao tác duyệt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {announcements.map((ann) => (
                <tr key={ann.id} className="hover:bg-slate-50/70 transition">
                  <td className="py-3.5 px-4 font-semibold text-gray-900 max-w-xs sm:max-w-md truncate">
                    {ann.title}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="text-[11px] font-bold uppercase text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                      {ann.audience.scope}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">{statusBadge(ann.status)}</td>
                  <td className="py-3.5 px-4 text-gray-500 text-xs">
                    {new Date(ann.createdAt).toLocaleDateString('vi-VN')}
                  </td>
                  <td className="py-3.5 px-4 text-right space-x-2">
                    {ann.status !== 'PUBLISHED' && ann.status !== 'REVOKED' && (
                      <button
                        onClick={() => handlePublish(ann.id)}
                        className="inline-flex items-center px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium transition"
                      >
                        <CheckCircle className="w-3.5 h-3.5 mr-1" />
                        Duyệt & Đăng
                      </button>
                    )}

                    {ann.status === 'PUBLISHED' && (
                      <button
                        onClick={() => handleRevoke(ann.id)}
                        className="inline-flex items-center px-3 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg text-xs font-medium transition"
                        title="Thu hồi thông báo theo chuẩn BR05"
                      >
                        <RotateCcw className="w-3.5 h-3.5 mr-1" />
                        Thu hồi
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {isEditorOpen && (
        <AnnouncementEditor
          onClose={() => setIsEditorOpen(false)}
          onSuccess={() => {
            setActionMsg({ text: 'Đã tạo thông báo mới theo quy trình FSM thành công.' });
            fetchAnnouncements();
          }}
        />
      )}
    </div>
  );
}

