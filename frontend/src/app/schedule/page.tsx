'use client';

import React, { useState, useEffect } from 'react';
import { apiGet } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { 
  Calendar as CalendarIcon, 
  Download, 
  Clock, 
  MapPin, 
  BookOpen, 
  GraduationCap, 
  ChevronLeft, 
  ChevronRight,
  Filter
} from 'lucide-react';

interface ScheduleEntry {
  id: string;
  courseCode: string;
  courseName: string;
  roomCode: string;
  building: string;
  entryType: 'CLASS' | 'EXAM' | 'BOOKING';
  date: string;
  startTime: string;
  endTime: string;
}

export default function SchedulePage() {
  const { user, token } = useAuth();
  const [viewMode, setViewMode] = useState<'DAY' | 'WEEK' | 'MONTH'>('WEEK');
  const [entries, setEntries] = useState<ScheduleEntry[]>([]);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchSchedule = async () => {
    setLoading(true);
    try {
      const data = await apiGet<{ lastSyncedAt: string; entries: ScheduleEntry[] }>('/schedule');
      setEntries(data.entries || []);
      setLastSyncedAt(data.lastSyncedAt);
    } catch {
      // Demo mock data
      const today = new Date().toISOString().split('T')[0];
      setEntries([
        {
          id: '1',
          courseCode: 'IT3010',
          courseName: 'Cấu trúc dữ liệu và giải thuật',
          roomCode: 'A1-101',
          building: 'A1',
          entryType: 'CLASS',
          date: today,
          startTime: '08:00',
          endTime: '10:00',
        },
        {
          id: '2',
          courseCode: 'IT3040',
          courseName: 'Kỹ thuật lập trình Web',
          roomCode: 'B1-301',
          building: 'B1',
          entryType: 'CLASS',
          date: today,
          startTime: '10:15',
          endTime: '12:15',
        },
        {
          id: '3',
          courseCode: 'IT3020',
          courseName: 'Toán rời rạc và Lý thuyết đồ thị',
          roomCode: 'A1-205',
          building: 'A1',
          entryType: 'EXAM',
          date: new Date(Date.now() + 86400000 * 3).toISOString().split('T')[0],
          startTime: '13:30',
          endTime: '15:30',
        },
      ]);
      setLastSyncedAt(new Date().toISOString());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, [user]);

  const handleExportIcs = () => {
    const icsUrl = `http://localhost:8000/api/v1/schedule/export.ics?semester=20251`;
    window.open(icsUrl, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">
            Thời khóa biểu & Lịch thi
          </span>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">Lịch học cá nhân</h1>
          <p className="text-xs text-gray-500">
            Dữ liệu cá nhân cô lập theo chuẩn BR04. Đồng bộ từ hệ thống đào tạo (SIS/LMS).
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {/* Switch View Buttons */}
          <div className="flex bg-gray-100 p-1 rounded-xl text-xs font-semibold">
            {(['DAY', 'WEEK', 'MONTH'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`px-3 py-1.5 rounded-lg transition ${
                  viewMode === mode ? 'bg-white text-indigo-700 shadow-xs' : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {mode === 'DAY' ? 'Ngày' : mode === 'WEEK' ? 'Tuần' : 'Tháng'}
              </button>
            ))}
          </div>

          {/* Export iCal Button */}
          <button
            onClick={handleExportIcs}
            className="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-xs transition"
          >
            <Download className="w-4 h-4 mr-1.5" />
            Xuất lịch iCal (.ics)
          </button>
        </div>
      </div>

      {/* Sync Status Banner */}
      {lastSyncedAt && (
        <div className="flex items-center justify-between px-2 text-xs text-gray-500">
          <span>
            Đồng bộ lần cuối lúc:{' '}
            <strong>
              {new Date(lastSyncedAt).toLocaleTimeString('vi-VN')} {new Date(lastSyncedAt).toLocaleDateString('vi-VN')}
            </strong>
          </span>
          <span className="flex items-center space-x-3">
            <span className="flex items-center">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 mr-1.5" /> Lớp học phần
            </span>
            <span className="flex items-center">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-1.5" /> Lịch thi học kỳ
            </span>
          </span>
        </div>
      )}

      {/* Schedule Entries List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {entries.map((entry) => {
          const isExam = entry.entryType === 'EXAM';
          return (
            <div
              key={entry.id}
              className={`p-5 rounded-2xl border transition shadow-xs ${
                isExam
                  ? 'bg-rose-50/40 border-rose-200 hover:border-rose-300'
                  : 'bg-white border-gray-200 hover:border-indigo-300'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span
                  className={`text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-full ${
                    isExam
                      ? 'bg-rose-100 text-rose-800 border border-rose-200'
                      : 'bg-indigo-50 text-indigo-700 border border-indigo-100'
                  }`}
                >
                  {isExam ? 'Lịch thi học kỳ' : 'Lịch học chính khóa'}
                </span>
                <span className="text-xs font-semibold text-gray-600">
                  {new Date(entry.date).toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' })}
                </span>
              </div>

              <h3 className="font-bold text-gray-900 text-base line-clamp-1">{entry.courseName}</h3>
              <p className="text-xs text-gray-500 mb-3">Mã học phần: {entry.courseCode}</p>

              <div className="space-y-1.5 pt-2 border-t border-gray-100 text-xs text-gray-700">
                <div className="flex items-center space-x-2">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  <span>
                    Khung giờ: <strong>{entry.startTime} - {entry.endTime}</strong>
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <MapPin className="w-3.5 h-3.5 text-gray-400" />
                  <span>
                    Địa điểm: <strong>Phòng {entry.roomCode}</strong> (Tòa {entry.building})
                  </span>
                </div>
              </div>
            </div>
          );
        })}

        {entries.length === 0 && !loading && (
          <div className="col-span-full text-center py-12 bg-white rounded-2xl border border-dashed border-gray-200 p-8">
            <CalendarIcon className="w-12 h-12 text-gray-300 mx-auto mb-2" />
            <h4 className="font-bold text-gray-700 text-sm">Không có lịch học hoặc lịch thi trong khoảng thời gian này</h4>
            <p className="text-xs text-gray-400 mt-1">Hệ thống sẽ tự động cập nhật khi phòng Đào tạo công bố thời khóa biểu mới.</p>
          </div>
        )}
      </div>
    </div>
  );
}

