'use client';

import React, { useState, useEffect } from 'react';
import { apiGet, apiPost } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { 
  FileCheck2, 
  Upload, 
  Sparkles, 
  FileText, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  ExternalLink,
  RefreshCw,
  FolderPlus
} from 'lucide-react';

interface DocumentVersion {
  id: string;
  documentId: string;
  versionNo: string;
  effectiveFrom: string;
  effectiveTo?: string;
  status: 'DRAFT' | 'ACTIVE' | 'EXPIRED';
  fileUrl: string;
  indexedAt?: string;
}

interface DocumentItem {
  id: string;
  title: string;
  issuerUnitId: string;
  status: string;
  createdAt: string;
  activeVersion?: DocumentVersion;
  versions: DocumentVersion[];
}

export default function AdminDocumentsPage() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [reindexingVerId, setReindexingVerId] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<{ text: string; error?: boolean } | null>(null);

  // Form upload version
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [versionNo, setVersionNo] = useState('2026');
  const [effectiveFrom, setEffectiveFrom] = useState(new Date().toISOString().split('T')[0]);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const data = await apiGet<DocumentItem[]>('/admin/documents');
      setDocuments(data || []);
    } catch {
      // Mock data
      setDocuments([
        {
          id: 'doc-1',
          title: 'Quy chế đào tạo đại học chính quy theo hệ thống tín chỉ',
          issuerUnitId: 'u1',
          status: 'ACTIVE',
          createdAt: new Date().toISOString(),
          versions: [
            {
              id: 'v-2025',
              documentId: 'doc-1',
              versionNo: '2025',
              effectiveFrom: '2025-01-01',
              status: 'ACTIVE',
              fileUrl: '/api/v1/storage/quy_che_dao_tao_2025.pdf',
              indexedAt: new Date().toISOString(),
            },
            {
              id: 'v-2026-draft',
              documentId: 'doc-1',
              versionNo: '2026',
              effectiveFrom: '2026-09-01',
              status: 'DRAFT',
              fileUrl: '/api/v1/storage/quy_che_dao_tao_2026_draft.pdf',
            },
          ],
        },
        {
          id: 'doc-2',
          title: 'Quy định đánh giá điểm rèn luyện và xét cấp học bổng khuyến khích',
          issuerUnitId: 'u2',
          status: 'ACTIVE',
          createdAt: new Date().toISOString(),
          versions: [
            {
              id: 'v-2024',
              documentId: 'doc-2',
              versionNo: '2024',
              effectiveFrom: '2024-09-01',
              status: 'ACTIVE',
              fileUrl: '/api/v1/storage/quy_dinh_hoc_bong_2024.pdf',
              indexedAt: new Date().toISOString(),
            },
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleReindex = async (docId: string, versionId: string) => {
    setReindexingVerId(versionId);
    setActionMsg(null);
    try {
      const res = await apiPost<any>(`/admin/documents/${docId}/reindex`, { versionId });
      setActionMsg({ text: res.message || 'Lập chỉ mục vector thành công.' });
      await fetchDocuments();
    } catch (err: any) {
      setActionMsg({ text: err.message || 'Lỗi khi kích hoạt lập chỉ mục.', error: true });
    } finally {
      setReindexingVerId(null);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !selectedDocId) {
      alert('Vui lòng chọn văn bản và tệp PDF/DOCX.');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('versionNo', versionNo);
      formData.append('effectiveFrom', effectiveFrom);
      formData.append('file', file);

      await apiPost(`/admin/documents/${selectedDocId}/versions`, formData);
      setActionMsg({ text: 'Đã tải lên phiên bản mới ở trạng thái DRAFT. Vui lòng bấm kích hoạt hiệu lực để AI lập chỉ mục (BR07).' });
      setShowUploadModal(false);
      setFile(null);
      await fetchDocuments();
    } catch (err: any) {
      setActionMsg({ text: err.message || 'Lỗi tải lên tệp.', error: true });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2.5 py-1 rounded-full">
            Kho tri thức số
          </span>
          <h1 className="text-2xl font-bold text-gray-900 mt-1 flex items-center space-x-2">
            <FileCheck2 className="w-6 h-6 text-purple-600" />
            <span>Quản lý kho văn bản quy chế & Lập chỉ mục AI (BR07)</span>
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Phiên bản mới ban đầu ở trạng thái DRAFT. Chỉ khi bấm "Xác nhận hiệu lực", tiến trình cắt đoạn theo cấu trúc pháp lý (Chương/Điều/Khoản) và sinh vector BGE-M3 mới được kích hoạt.
          </p>
        </div>

        <button
          onClick={() => {
            if (documents.length > 0) setSelectedDocId(documents[0].id);
            setShowUploadModal(true);
          }}
          className="inline-flex items-center px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs sm:text-sm font-semibold shadow-xs transition"
        >
          <Upload className="w-4 h-4 mr-1.5" />
          Tải lên phiên bản mới
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

      {/* Documents List */}
      <div className="space-y-4">
        {documents.map((doc) => (
          <div key={doc.id} className="bg-white rounded-2xl border border-gray-200 shadow-xs p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-gray-100 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                  Văn bản quy chế chính thức
                </span>
                <h3 className="text-lg font-bold text-gray-900 mt-1">{doc.title}</h3>
              </div>
            </div>

            {/* Versions Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs sm:text-sm">
                <thead className="bg-slate-50 text-gray-500 uppercase text-[10px] tracking-wider font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Số phiên bản</th>
                    <th className="py-2.5 px-3">Hiệu lực từ ngày</th>
                    <th className="py-2.5 px-3">Trạng thái (BR07)</th>
                    <th className="py-2.5 px-3">Lập chỉ mục AI</th>
                    <th className="py-2.5 px-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {doc.versions?.map((ver) => {
                    const isReindexing = reindexingVerId === ver.id;
                    return (
                      <tr key={ver.id} className="hover:bg-slate-50/60 transition">
                        <td className="py-3 px-3 font-bold text-gray-900 flex items-center space-x-1.5">
                          <FileText className="w-4 h-4 text-gray-400" />
                          <span>Phiên bản {ver.versionNo}</span>
                        </td>
                        <td className="py-3 px-3 text-gray-600">
                          {new Date(ver.effectiveFrom).toLocaleDateString('vi-VN')}
                        </td>
                        <td className="py-3 px-3">
                          {ver.status === 'ACTIVE' ? (
                            <span className="bg-emerald-100 text-emerald-800 text-[11px] font-bold px-2 py-0.5 rounded-full">
                              Còn hiệu lực (ACTIVE)
                            </span>
                          ) : ver.status === 'DRAFT' ? (
                            <span className="bg-amber-100 text-amber-800 text-[11px] font-bold px-2 py-0.5 rounded-full">
                              Bản nháp (DRAFT)
                            </span>
                          ) : (
                            <span className="bg-gray-100 text-gray-600 text-[11px] font-bold px-2 py-0.5 rounded-full">
                              Hết hiệu lực (EXPIRED)
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-xs text-gray-500">
                          {ver.indexedAt ? (
                            <span className="text-emerald-600 font-medium flex items-center">
                              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                              Đã đánh chỉ mục
                            </span>
                          ) : (
                            <span className="text-gray-400">Chưa đưa vào kho AI</span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-right space-x-2">
                          <button
                            onClick={() => handleReindex(doc.id, ver.id)}
                            disabled={isReindexing}
                            className={`inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition ${
                              ver.status === 'ACTIVE'
                                ? 'bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200'
                                : 'bg-purple-600 hover:bg-purple-700 text-white'
                            }`}
                          >
                            <Sparkles className="w-3.5 h-3.5 mr-1" />
                            {isReindexing
                              ? 'Đang cắt đoạn & sinh vector...'
                              : ver.status === 'ACTIVE'
                              ? 'Tái lập chỉ mục'
                              : 'Xác nhận hiệu lực & Đánh chỉ mục AI'}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      {/* Modal Upload */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full border border-gray-200 p-6 space-y-4">
            <h3 className="font-bold text-base text-gray-900 flex items-center space-x-2">
              <Upload className="w-5 h-5 text-purple-600" />
              <span>Tải lên phiên bản văn bản mới</span>
            </h3>

            <form onSubmit={handleUploadSubmit} className="space-y-3 text-xs sm:text-sm">
              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">Văn bản quy chế *</label>
                <select
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-purple-500 bg-white"
                >
                  {documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Số phiên bản *</label>
                  <input
                    type="text"
                    value={versionNo}
                    onChange={(e) => setVersionNo(e.target.value)}
                    placeholder="VD: 2026 hoặc v2.1"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-purple-500"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Hiệu lực từ ngày *</label>
                  <input
                    type="date"
                    value={effectiveFrom}
                    onChange={(e) => setEffectiveFrom(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-purple-500"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">Tệp văn bản gốc (PDF hoặc DOCX) *</label>
                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-gray-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
                  required
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-semibold transition"
                >
                  {uploading ? 'Đang tải lên...' : 'Lưu bản DRAFT'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

