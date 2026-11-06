'use client';

import React, { useState } from 'react';
import { apiPost } from '@/lib/api';
import { X, Send, Save, BellRing, Users } from 'lucide-react';

interface AnnouncementEditorProps {
  onClose: () => void;
  onSuccess: () => void;
}

export const AnnouncementEditor: React.FC<AnnouncementEditorProps> = ({ onClose, onSuccess }) => {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [scope, setScope] = useState<'SCHOOL' | 'UNIT'>('SCHOOL');
  const [cohorts, setCohorts] = useState('');
  const [majors, setMajors] = useState('');
  const [publishAt, setPublishAt] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !body.trim()) {
      setErrorMsg('Vui lòng điền đầy đủ tiêu đề và nội dung thông báo.');
      return;
    }

    setSubmitting(true);
    setErrorMsg('');

    try {
      const audiencePayload = {
        scope,
        unit_ids: [],
        cohorts: cohorts ? cohorts.split(',').map((c) => c.trim()) : [],
        majors: majors ? majors.split(',').map((m) => m.trim()) : [],
      };

      await apiPost('/admin/announcements', {
        title,
        body,
        audience: audiencePayload,
        publishAt: publishAt ? new Date(publishAt).toISOString() : null,
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Có lỗi xảy ra khi lưu thông báo.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-gray-200">
        <div className="p-5 border-b border-gray-200 flex items-center justify-between bg-purple-50/50">
          <div className="flex items-center space-x-2 text-purple-700">
            <BellRing className="w-5 h-5" />
            <h3 className="font-bold text-base">Soạn thông báo mới (Tuân thủ BR05)</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-gray-700 block mb-1">Tiêu đề thông báo *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="VD: Kế hoạch đăng ký học phần học kỳ 2..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-purple-500"
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-700 block mb-1">Phạm vi phát hành (Audience Scope) *</label>
            <div className="grid grid-cols-2 gap-3">
              <label
                className={`p-3 rounded-xl border cursor-pointer text-xs flex items-center space-x-2 transition ${
                  scope === 'SCHOOL'
                    ? 'border-purple-600 bg-purple-50/70 text-purple-900 font-semibold'
                    : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <input
                  type="radio"
                  name="scope"
                  checked={scope === 'SCHOOL'}
                  onChange={() => setScope('SCHOOL')}
                  className="hidden"
                />
                <Users className="w-4 h-4 text-purple-600 shrink-0" />
                <div>
                  <span className="block font-medium">Toàn trường (SCHOOL)</span>
                  <span className="text-[10px] text-gray-500 font-normal">Cần duyệt bởi Trưởng đơn vị / Admin</span>
                </div>
              </label>

              <label
                className={`p-3 rounded-xl border cursor-pointer text-xs flex items-center space-x-2 transition ${
                  scope === 'UNIT'
                    ? 'border-purple-600 bg-purple-50/70 text-purple-900 font-semibold'
                    : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <input
                  type="radio"
                  name="scope"
                  checked={scope === 'UNIT'}
                  onChange={() => setScope('UNIT')}
                  className="hidden"
                />
                <Users className="w-4 h-4 text-purple-600 shrink-0" />
                <div>
                  <span className="block font-medium">Nội bộ Đơn vị / Khoa (UNIT)</span>
                  <span className="text-[10px] text-gray-500 font-normal">Được đăng trực tiếp bởi Cán bộ khoa</span>
                </div>
              </label>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-700 block mb-1">Khóa sinh viên (Cách nhau bởi dấu phẩy)</label>
              <input
                type="text"
                value={cohorts}
                onChange={(e) => setCohorts(e.target.value)}
                placeholder="VD: K65, K66"
                className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-700 block mb-1">Ngành học</label>
              <input
                type="text"
                value={majors}
                onChange={(e) => setMajors(e.target.value)}
                placeholder="VD: Khoa học Máy tính, Kỹ thuật Phần mềm"
                className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-purple-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-700 block mb-1">Hẹn giờ đăng (Để trống nếu đăng ngay)</label>
            <input
              type="datetime-local"
              value={publishAt}
              onChange={(e) => setPublishAt(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-purple-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-700 block mb-1">Nội dung chi tiết *</label>
            <textarea
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Nhập nội dung văn bản thông báo..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-purple-500"
              required
            />
          </div>

          <div className="flex justify-end space-x-2 pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-xl text-xs sm:text-sm text-gray-700 hover:bg-gray-50 transition"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs sm:text-sm font-semibold transition flex items-center shadow-xs disabled:opacity-50"
            >
              <Send className="w-4 h-4 mr-1.5" />
              {submitting ? 'Đang lưu...' : 'Lưu & Khởi tạo (FSM)'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

