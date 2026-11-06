'use client';

import React from 'react';
import { AnalyticsCharts } from '@/components/AnalyticsCharts';
import { BarChart3 } from 'lucide-react';

export default function AdminAnalyticsPage() {
  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs">
        <span className="text-xs font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2.5 py-1 rounded-full">
          Phân tích & Tình báo Học vụ
        </span>
        <h1 className="text-2xl font-bold text-gray-900 mt-1 flex items-center space-x-2">
          <BarChart3 className="w-6 h-6 text-purple-600" />
          <span>Thống kê câu hỏi & Khoảng trống tri thức (UC12 / FR13)</span>
        </h1>
        <p className="text-xs text-gray-500 mt-1 max-w-3xl">
          Thuật toán K-Means / HDBSCAN tự động gom cụm câu hỏi người dùng (đã khử PII) và tách riêng nhóm câu hỏi AI chưa trả lời được để chỉ ra cho nhà trường những nội dung còn thiếu văn bản quy định.
        </p>
      </div>

      <AnalyticsCharts />
    </div>
  );
}

