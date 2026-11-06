'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ChatWindow } from '@/components/ChatWindow';
import { apiGet } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { 
  Calendar, 
  Bell, 
  Clock, 
  ArrowRight, 
  Sparkles, 
  BookCheck, 
  DoorOpen, 
  FileSpreadsheet
} from 'lucide-react';

export default function HomePage() {
  const { user, role } = useAuth();
  const [todaySchedule, setTodaySchedule] = useState<any[]>([]);
  const [recentAnnouncements, setRecentAnnouncements] = useState<any[]>([]);
  const [loadingWidgets, setLoadingWidgets] = useState(true);

  useEffect(() => {
    const fetchWidgets = async () => {
      try {
        const todayStr = new Date().toISOString().split('T')[0];
        const [schedData, annData] = await Promise.allSettled([
          apiGet<any>(`/schedule?from=${todayStr}&to=${todayStr}`),
          apiGet<any>(`/announcements?unread=true&size=3`),
        ]);

        if (schedData.status === 'fulfilled') {
          setTodaySchedule(schedData.value.entries || []);
        }
        if (annData.status === 'fulfilled') {
          setRecentAnnouncements(annData.value.items || []);
        }
      } catch {
        // Mock default for demo
        setTodaySchedule([
          {
            id: 'demo-s1',
            courseCode: 'IT3010',
            courseName: 'Cấu trúc dữ liệu và giải thuật',
            roomCode: 'A1-101',
            building: 'A1',
            entryType: 'CLASS',
            startTime: '08:00',
            endTime: '10:00',
          },
        ]);
        setRecentAnnouncements([
          {
            id: 'demo-a1',
            title: 'Kế hoạch đăng ký học phần học kỳ 2 năm học 2025-2026',
            publishAt: new Date().toISOString(),
          },
        ]);
      } finally {
        setLoadingWidgets(false);
      }
    };

    fetchWidgets();
  }, [user]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Cột chính: Khung Chat AI (8 cột) */}
      <div className="lg:col-span-8">
        <ChatWindow />
      </div>

      {/* Cột phụ: Tóm tắt thông tin hôm nay (4 cột) */}
      <div className="lg:col-span-4 space-y-5">
        {/* Lịch học / thi hôm nay */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-gray-100 pb-2.5">
            <div className="flex items-center space-x-2 text-indigo-700 font-semibold text-sm">
              <Calendar className="w-4 h-4" />
              <span>Lịch của bạn hôm nay</span>
            </div>
            <Link href="/schedule" className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center">
              Xem hết <ArrowRight className="w-3 h-3 ml-0.5" />
            </Link>
          </div>

          <div className="space-y-2">
            {todaySchedule.length > 0 ? (
              todaySchedule.map((entry, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-start justify-between space-x-2"
                >
                  <div className="space-y-0.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded">
                      {entry.entryType === 'EXAM' ? 'Lịch thi' : 'Lịch học'}
                    </span>
                    <h4 className="font-semibold text-xs text-gray-900 mt-1">{entry.courseName}</h4>
                    <p className="text-[11px] text-gray-500">
                      Phòng <strong>{entry.roomCode}</strong> (Tòa {entry.building})
                    </p>
                  </div>
                  <div className="text-right text-xs font-semibold text-gray-700 shrink-0">
                    <Clock className="w-3.5 h-3.5 inline mr-1 text-gray-400" />
                    {entry.startTime} - {entry.endTime}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-6 text-gray-400 text-xs">
                Hôm nay bạn không có lịch học hoặc lịch thi nào.
              </div>
            )}
          </div>
        </div>

        {/* Thông báo chưa đọc */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-gray-100 pb-2.5">
            <div className="flex items-center space-x-2 text-indigo-700 font-semibold text-sm">
              <Bell className="w-4 h-4" />
              <span>Thông báo mới nhất</span>
            </div>
            <Link href="/announcements" className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center">
              Xem tất cả <ArrowRight className="w-3 h-3 ml-0.5" />
            </Link>
          </div>

          <div className="space-y-2">
            {recentAnnouncements.length > 0 ? (
              recentAnnouncements.map((ann, idx) => (
                <Link
                  key={idx}
                  href="/announcements"
                  className="block p-3 rounded-xl hover:bg-indigo-50/50 border border-transparent hover:border-indigo-100 transition"
                >
                  <h4 className="font-semibold text-xs text-gray-900 line-clamp-2">{ann.title}</h4>
                  <span className="text-[10px] text-gray-400 mt-1 block">
                    {new Date(ann.publishAt || Date.now()).toLocaleDateString('vi-VN')}
                  </span>
                </Link>
              ))
            ) : (
              <div className="text-center py-4 text-gray-400 text-xs">
                Không có thông báo mới chưa đọc.
              </div>
            )}
          </div>
        </div>

        {/* Lối tắt tra cứu tiện ích */}
        <div className="bg-gradient-to-br from-indigo-500 to-primary-600 text-white p-5 rounded-2xl shadow-sm space-y-3">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-amber-300" />
            <h3 className="font-bold text-sm">Tiện ích nhanh cho {role === 'STUDENT' ? 'Sinh viên' : 'Giảng viên'}</h3>
          </div>
          <p className="text-xs text-indigo-100">
            Truy cập nhanh các dịch vụ học vụ và không gian học tập tại trường.
          </p>
          <div className="grid grid-cols-2 gap-2 pt-1">
            <Link
              href="/rooms"
              className="p-2.5 rounded-xl bg-white/10 hover:bg-white/20 transition flex flex-col items-center text-center text-xs"
            >
              <DoorOpen className="w-4 h-4 mb-1" />
              <span>Tìm phòng trống</span>
            </Link>
            <Link
              href="/services"
              className="p-2.5 rounded-xl bg-white/10 hover:bg-white/20 transition flex flex-col items-center text-center text-xs"
            >
              <FileSpreadsheet className="w-4 h-4 mb-1" />
              <span>Biểu mẫu dịch vụ</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

