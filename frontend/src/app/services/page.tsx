'use client';

import React, { useState, useEffect } from 'react';
import { apiGet } from '@/lib/api';
import { 
  FileText, 
  Search, 
  Clock, 
  Phone, 
  Download, 
  Building2, 
  ExternalLink,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface ServiceItem {
  id: string;
  unitId: string;
  unitName?: string;
  name: string;
  procedure: string;
  formUrls: { label: string; url: string }[];
  openingHours: string;
  contact: string;
}

export default function ServicesPage() {
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchServices = async (q?: string) => {
    setLoading(true);
    try {
      const endpoint = q ? `/services?q=${encodeURIComponent(q)}` : '/services';
      const res = await apiGet<{ services: ServiceItem[] }>(endpoint);
      setServices(res.services || []);
      if (res.services && res.services.length > 0 && !expandedId) {
        setExpandedId(res.services[0].id);
      }
    } catch {
      // Demo mock data
      setServices([
        {
          id: 's1',
          unitId: 'u1',
          unitName: 'Phòng Đào tạo',
          name: 'Cấp bảng điểm và giấy xác nhận học vụ',
          procedure: '1. Sinh viên điền thông tin vào phiếu đề nghị cấp bảng điểm hoặc giấy xác nhận học vụ.\n2. Nộp đơn trực tuyến hoặc nộp trực tiếp tại Bộ phận Một cửa Phòng Đào tạo (Nhà C1-101).\n3. Thời gian xử lý: 02 ngày làm việc kể từ khi nhận đủ hồ sơ hợp lệ.\n4. Sinh viên xuất trình thẻ sinh viên hoặc CCCD để nhận kết quả.',
          formUrls: [
            { label: 'Đơn xin cấp bảng điểm (PDF)', url: '/forms/don_cap_bang_diem.pdf' },
            { label: 'Giấy xác nhận đang là sinh viên (DOCX)', url: '/forms/giay_xac_nhan_sv.docx' },
          ],
          openingHours: 'Sáng 08:00 - 11:30, Chiều 13:30 - 17:00 (Thứ 2 - Thứ 6)',
          contact: 'Nhà C1, Phòng 101 | Email: daotao@uni.edu.vn | Hotline: 024-3869-2345',
        },
        {
          id: 's2',
          unitId: 'u2',
          unitName: 'Phòng Công tác Sinh viên',
          name: 'Cấp lại thẻ sinh viên tích hợp ngân hàng',
          procedure: '1. Khai báo thông tin mất thẻ trên cổng thông tin sinh viên hoặc liên hệ trực tiếp phòng CTSV.\n2. Nộp lệ phí phát hành lại thẻ: 50.000 VNĐ.\n3. Thời gian nhận thẻ mới: 05 ngày làm việc.\n4. Thẻ sinh viên tích hợp mã vé xe buýt và tài khoản thanh toán nội bộ.',
          formUrls: [
            { label: 'Tờ khai cấp lại thẻ sinh viên (PDF)', url: '/forms/cap_lai_the_sv.pdf' },
          ],
          openingHours: '08:00 - 16:30 các ngày làm việc trong tuần',
          contact: 'Nhà C1, Phòng 102 | Email: ctsv@uni.edu.vn | Hotline: 024-3869-3456',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServices();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchServices(searchQuery);
  };

  return (
    <div className="space-y-6">
      {/* Header & Search */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs space-y-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">
            Dịch vụ & Thủ tục hành chính
          </span>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">Danh bạ dịch vụ sinh viên</h1>
          <p className="text-xs text-gray-500">
            Tra cứu quy trình thủ tục giấy tờ, thời gian tiếp nhận, giờ làm việc và tải biểu mẫu hành chính chính thức.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm thủ tục (ví dụ: cấp bảng điểm, cấp lại thẻ, vay vốn, hoãn thi)..."
              className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-300 rounded-xl focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs sm:text-sm font-semibold transition shadow-xs"
          >
            Tìm kiếm
          </button>
        </form>
      </div>

      {/* Services Accordion List */}
      <div className="space-y-4">
        {services.map((item) => {
          const isExpanded = expandedId === item.id;
          return (
            <div
              key={item.id}
              className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden transition"
            >
              <div
                onClick={() => setExpandedId(isExpanded ? null : item.id)}
                className="p-5 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition"
              >
                <div className="flex items-center space-x-3.5">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                      {item.unitName || 'Phòng ban trường'}
                    </span>
                    <h3 className="text-base font-bold text-gray-900 mt-0.5">{item.name}</h3>
                  </div>
                </div>

                <div className="flex items-center space-x-2 text-gray-400">
                  <span className="text-xs hidden sm:inline">{isExpanded ? 'Thu gọn' : 'Xem quy trình'}</span>
                  {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </div>
              </div>

              {isExpanded && (
                <div className="p-6 bg-slate-50/60 border-t border-gray-100 space-y-4 text-xs sm:text-sm">
                  {/* Procedure */}
                  <div>
                    <h4 className="font-bold text-gray-900 mb-1.5 flex items-center space-x-1.5">
                      <span>Các bước thực hiện</span>
                    </h4>
                    <div className="p-4 bg-white rounded-xl border border-gray-200 text-gray-700 whitespace-pre-wrap leading-relaxed">
                      {item.procedure}
                    </div>
                  </div>

                  {/* Contact & Hours */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-700">
                    <div className="p-3 bg-white rounded-xl border border-gray-200 flex items-center space-x-2.5">
                      <Clock className="w-4 h-4 text-indigo-600 shrink-0" />
                      <div>
                        <span className="font-semibold block text-gray-500 text-[10px] uppercase">Giờ tiếp nhận</span>
                        <span>{item.openingHours}</span>
                      </div>
                    </div>

                    <div className="p-3 bg-white rounded-xl border border-gray-200 flex items-center space-x-2.5">
                      <Phone className="w-4 h-4 text-indigo-600 shrink-0" />
                      <div>
                        <span className="font-semibold block text-gray-500 text-[10px] uppercase">Liên hệ trực tiếp</span>
                        <span>{item.contact}</span>
                      </div>
                    </div>
                  </div>

                  {/* Form URLs */}
                  {item.formUrls && item.formUrls.length > 0 && (
                    <div>
                      <h4 className="font-bold text-gray-900 mb-1.5 text-xs">Biểu mẫu tải về đính kèm:</h4>
                      <div className="flex flex-wrap gap-2">
                        {item.formUrls.map((f, i) => (
                          <a
                            key={i}
                            href={f.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center px-3 py-1.5 rounded-lg bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-50 text-xs font-medium transition shadow-2xs"
                          >
                            <Download className="w-3.5 h-3.5 mr-1.5" />
                            {f.label}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {services.length === 0 && !loading && (
          <div className="text-center py-12 bg-white rounded-2xl border border-dashed border-gray-300 p-8">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-2" />
            <h4 className="font-bold text-gray-800 text-sm">Không tìm thấy thủ tục phù hợp</h4>
            <p className="text-xs text-gray-400 mt-1">Vui lòng thử lại với từ khóa khác hoặc liên hệ bộ phận Một cửa.</p>
          </div>
        )}
      </div>
    </div>
  );
}

