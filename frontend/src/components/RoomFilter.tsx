'use client';

import React, { useState, useEffect } from 'react';
import { apiGet } from '@/lib/api';
import { Search, DoorOpen, Users, Clock, CheckCircle2, SlidersHorizontal } from 'lucide-react';

interface RoomItem {
  id: string;
  code: string;
  building: string;
  capacity: number;
  roomType: string;
  equipment: string[];
  openingHours: string;
}

export const RoomFilter: React.FC = () => {
  const todayStr = new Date().toISOString().split('T')[0];

  const [date, setDate] = useState(todayStr);
  const [start, setStart] = useState('08:00');
  const [end, setEnd] = useState('10:00');
  const [building, setBuilding] = useState('');
  const [capacity, setCapacity] = useState('30');
  const [rooms, setRooms] = useState<RoomItem[]>([]);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const fetchRooms = async () => {
    setLoading(true);
    setSearched(true);
    try {
      let query = `/rooms/available?date=${date}&start=${start}&end=${end}`;
      if (building) query += `&building=${building}`;
      if (capacity) query += `&capacity=${capacity}`;

      const data = await apiGet<{ lastSyncedAt: string; rooms: RoomItem[] }>(query);
      setRooms(data.rooms || []);
      setLastSyncedAt(data.lastSyncedAt);
    } catch {
      // Demo fallback mock data
      setRooms([
        {
          id: 'r1',
          code: 'A1-101',
          building: 'A1',
          capacity: 60,
          roomType: 'CLASSROOM',
          equipment: ['PROJECTOR', 'AC', 'MIC'],
          openingHours: '07:00 - 21:00',
        },
        {
          id: 'r4',
          code: 'D3-Lib01',
          building: 'D3',
          capacity: 80,
          roomType: 'SELF_STUDY',
          equipment: ['WIFI', 'AC', 'POWER_OUTLET'],
          openingHours: '07:00 - 22:00',
        },
      ]);
      setLastSyncedAt(new Date().toISOString());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRooms();
  }, []);

  return (
    <div className="space-y-6">
      {/* Filter Form */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs space-y-4">
        <div className="flex items-center space-x-2 text-indigo-700 font-semibold text-sm">
          <SlidersHorizontal className="w-4 h-4" />
          <span>Bộ lọc tìm kiếm phòng trống (Tuân thủ BR06)</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Ngày tra cứu</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Giờ bắt đầu</label>
            <input
              type="time"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Giờ kết thúc</label>
            <input
              type="time"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Tòa nhà</label>
            <select
              value={building}
              onChange={(e) => setBuilding(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-indigo-500 bg-white"
            >
              <option value="">Tất cả các tòa</option>
              <option value="A1">Tòa A1</option>
              <option value="B1">Tòa B1</option>
              <option value="D3">Tòa D3 (Thư viện)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Sức chứa tối thiểu</label>
            <input
              type="number"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              placeholder="VD: 40"
              className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={fetchRooms}
            disabled={loading}
            className="inline-flex items-center px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs sm:text-sm rounded-xl transition shadow-xs disabled:opacity-50"
          >
            <Search className="w-4 h-4 mr-2" />
            {loading ? 'Đang kiểm tra phòng...' : 'Tìm phòng trống'}
          </button>
        </div>
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs text-gray-500 px-1">
        <span>
          Tìm thấy <strong className="text-gray-900">{rooms.length}</strong> phòng trống khả dụng
        </span>
        {lastSyncedAt && (
          <span>
            Dữ liệu đồng bộ lúc: {new Date(lastSyncedAt).toLocaleTimeString('vi-VN')} {new Date(lastSyncedAt).toLocaleDateString('vi-VN')}
          </span>
        )}
      </div>

      {/* Rooms Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {rooms.map((r) => (
          <div
            key={r.id}
            className="bg-white p-5 rounded-2xl border border-gray-200 hover:border-indigo-300 hover:shadow-md transition space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-50 text-indigo-700">
                Tòa {r.building}
              </span>
              <span className="text-xs text-emerald-600 font-semibold flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                Sẵn sàng
              </span>
            </div>

            <div>
              <h4 className="text-lg font-bold text-gray-900 flex items-center space-x-1.5">
                <DoorOpen className="w-5 h-5 text-indigo-600" />
                <span>Phòng {r.code}</span>
              </h4>
              <p className="text-xs text-gray-500 mt-0.5">
                Loại phòng: {r.roomType === 'CLASSROOM' ? 'Giảng đường' : r.roomType === 'LAB' ? 'Phòng máy tính' : 'Không gian tự học'}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y border-gray-100 text-gray-600">
              <div className="flex items-center space-x-1">
                <Users className="w-3.5 h-3.5 text-gray-400" />
                <span>Sức chứa: <strong>{r.capacity} chỗ</strong></span>
              </div>
              <div className="flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-gray-400" />
                <span>{r.openingHours}</span>
              </div>
            </div>

            {/* Equipment Tags */}
            <div className="flex flex-wrap gap-1">
              {r.equipment?.map((eq, i) => (
                <span
                  key={i}
                  className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium"
                >
                  {eq}
                </span>
              ))}
            </div>
          </div>
        ))}

        {rooms.length === 0 && searched && (
          <div className="col-span-full text-center py-12 bg-white rounded-2xl border border-dashed border-gray-300 p-8">
            <DoorOpen className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <h4 className="font-semibold text-gray-800 text-sm">Không có phòng trống trong khung giờ này</h4>
            <p className="text-xs text-gray-500 mt-1">
              Vui lòng thử điều chỉnh lại ngày, giờ bắt đầu/kết thúc hoặc giảm bớt tiêu chí lọc.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

