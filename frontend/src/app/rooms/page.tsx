'use client';

import React from 'react';
import { RoomFilter } from '@/components/RoomFilter';
import { DoorOpen } from 'lucide-react';

export default function RoomsPage() {
  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs">
        <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">
          Không gian học tập & Nghiên cứu
        </span>
        <h1 className="text-2xl font-bold text-gray-900 mt-1 flex items-center space-x-2">
          <DoorOpen className="w-6 h-6 text-indigo-600" />
          <span>Tra cứu & Tìm phòng học trống</span>
        </h1>
        <p className="text-xs text-gray-500 mt-1 max-w-2xl">
          Hệ thống kiểm tra tự động xung đột lịch học, lịch thi và lịch đặt phòng theo thời gian thực (Quy tắc BR06).
        </p>
      </div>

      <RoomFilter />
    </div>
  );
}

