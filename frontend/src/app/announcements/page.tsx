'use client';

import React, { useState, useEffect } from 'react';
import { apiGet, apiPost } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { 
  Bell, 
  CheckCircle2, 
  Clock, 
  Calendar, 
  Users, 
  Filter, 
  ChevronRight,
  X,
  Building
} from 'lucide-react';

interface AnnouncementItem {
  id: string;
  unitId: string;
  unitName?: string;
  title: string;
  body: string;
  audience: {
    scope: 'SCHOOL' | 'UNIT';
    unit_ids: string[];
    cohorts: string[];
    majors: string[];
  };
  status: string;
  publishAt: string;
  createdAt: string;
  isRead: boolean;
}

export default function AnnouncementsPage() {
  const { user } = useAuth();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [selectedAnn, setSelectedAnn] = useState<AnnouncementItem | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAnnouncements = async () => {
    setLoading(true);
    try {
      const res = await apiGet<{ items: AnnouncementItem[]; total: number }>(
        `/announcements?unread=${unreadOnly}&page=1&size=20`
      );
      setAnnouncements(res.items || []);
    } catch {
      // Demo mock data
      setAnnouncements([
        {
          id: 'a1',
          unitId: 'u1',
          unitName: 'Phòng Đào tạo',
          title: 'Kế hoạch đăng ký học phần học kỳ 2 năm học 2025-2026',
          body: 'Phòng Đào tạo thông báo kế hoạch đăng ký học phần cho sinh viên toàn trường:\n\n1. Thời gian đăng ký thử nghiệm: từ ngày 10/12/2025 đến ngày 12/12/2025.\n2. Đợt đăng ký chính thức: từ 08h00 ngày 15/12/2025 đến 17h00 ngày 22/12/2025.\n3. Đề nghị sinh viên hoàn thành khảo sát môn học và thanh toán các khoản công nợ học phí trước khi mở cổng đăng ký.',
          audience: { scope: 'SCHOOL', unit_ids: [], cohorts: [], majors: [] },
          status: 'PUBLISHED',
          publishAt: new Date(Date.now() - 86400000).toISOString(),
          createdAt: new Date().toISOString(),
          isRead: false,
        },
        {
          id: 'a2',
          unitId: 'u2',
          unitName: 'Khoa Công nghệ Thông tin',
          title: 'Hội thảo Khoa học Sinh viên CNTT và Công nghệ AI 2026',
          body: 'Khoa CNTT trân trọng kính mời sinh viên K65 và K66 tham gia Hội thảo Khoa học thường niên về Trợ lý số ứng dụng và Generative AI. Sinh viên tham dự đầy đủ sẽ được cộng điểm rèn luyện theo quy chế.',
          audience: { scope: 'UNIT', unit_ids: [], cohorts: ['K65', 'K66'], majors: ['Khoa học Máy tính'] },
          status: 'PUBLISHED',
          publishAt: new Date(Date.now() - 86400000 * 2).toISOString(),
          createdAt: new Date().toISOString(),
          isRead: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnnouncements();
  }, [unreadOnly, user]);

  const handleOpenDetail = async (ann: AnnouncementItem) => {
    setSelectedAnn(ann);
    if (!ann.isRead) {
      try {
        await apiPost(`/announcements/${ann.id}/read`);
        setAnnouncements((prev) =>
          prev.map((a) => (a.id === ann.id ? { ...a, isRead: true } : a))
        );
      } catch {}
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">
            Bảng tin & Thông báo
          </span>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">Thông báo dành cho bạn</h1>
          <p className="text-xs text-gray-500">
            Lọc chính xác theo đối tượng cá nhân ({user?.cohort || 'Khóa chung'} - {user?.major || 'Toàn trường'}) tuân thủ chuẩn BR04.
          </p>
        </div>

        {/* Filter Unread */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setUnreadOnly(false)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
              !unreadOnly ? 'bg-indigo-600 text-white shadow-xs' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Tất cả
          </button>
          <button
            onClick={() => setUnreadOnly(true)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
              unreadOnly ? 'bg-indigo-600 text-white shadow-xs' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Chưa đọc
          </button>
        </div>
      </div>

      {/* Announcements List */}
      <div className="space-y-3">
        {announcements.map((ann) => (
          <div
            key={ann.id}
            onClick={() => handleOpenDetail(ann)}
            className={`p-5 rounded-2xl border transition cursor-pointer flex items-center justify-between space-x-4 ${
              !ann.isRead
                ? 'bg-white border-indigo-200 hover:border-indigo-400 shadow-xs'
                : 'bg-white/70 border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-start space-x-3.5">
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5 ${
                  !ann.isRead ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-400'
                }`}
              >
                <Bell className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                    {ann.audience.scope === 'SCHOOL' ? 'Toàn trường' : 'Cấp khoa/viện'}
                  </span>
                  {!ann.isRead && (
                    <span className="w-2 h-2 rounded-full bg-indigo-600" title="Chưa đọc" />
                  )}
                  <span className="text-xs text-gray-400">
                    {new Date(ann.publishAt || ann.createdAt).toLocaleDateString('vi-VN')}
                  </span>
                </div>
                <h3 className={`text-sm sm:text-base ${!ann.isRead ? 'font-bold text-gray-900' : 'font-medium text-gray-700'}`}>
                  {ann.title}
                </h3>
                <p className="text-xs text-gray-500 line-clamp-1">{ann.body}</p>
              </div>
            </div>

            <ChevronRight className="w-5 h-5 text-gray-400 shrink-0" />
          </div>
        ))}

        {announcements.length === 0 && !loading && (
          <div className="text-center py-12 bg-white rounded-2xl border border-dashed border-gray-300 p-8">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-2" />
            <h4 className="font-bold text-gray-800 text-sm">Tuyệt vời, bạn đã đọc hết mọi thông báo!</h4>
            <p className="text-xs text-gray-400 mt-1">Không có thông báo mới nào chưa đọc vào lúc này.</p>
          </div>
        )}
      </div>

      {/* Modal Detail Announcement */}
      {selectedAnn && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto border border-gray-200">
            <div className="p-5 border-b border-gray-200 flex items-center justify-between bg-slate-50">
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                  {selectedAnn.audience.scope === 'SCHOOL' ? 'Thông báo toàn trường' : 'Thông báo khoa'}
                </span>
                <h3 className="font-bold text-base text-gray-900">{selectedAnn.title}</h3>
              </div>
              <button
                onClick={() => setSelectedAnn(null)}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {selectedAnn.body}
            </div>

            <div className="p-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
              <span>Đã đánh dấu đã đọc</span>
              <button
                onClick={() => setSelectedAnn(null)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

