'use client';

import React from 'react';
import { CitationItem } from '@/lib/sse';
import { X, BookOpen, ExternalLink, FileText } from 'lucide-react';

interface CitationDrawerProps {
  citation: CitationItem | null;
  onClose: () => void;
}

export const CitationDrawer: React.FC<CitationDrawerProps> = ({ citation, onClose }) => {
  if (!citation) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-96 bg-white shadow-2xl border-l border-gray-200 flex flex-col transition-transform transform">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-indigo-50/50">
        <div className="flex items-center space-x-2 text-indigo-700">
          <BookOpen className="w-5 h-5" />
          <h3 className="font-semibold text-sm">Trích dẫn nguồn căn cứ [{citation.ref}]</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Body */}
      <div className="p-5 flex-1 overflow-y-auto space-y-4 text-sm">
        <div>
          <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Tên văn bản quy chế</label>
          <p className="font-medium text-gray-900 mt-0.5">{citation.documentTitle}</p>
        </div>

        <div className="grid grid-cols-2 gap-3 bg-gray-50 p-3 rounded-lg border border-gray-100">
          <div>
            <label className="text-xs text-gray-500">Phiên bản / Năm</label>
            <p className="font-semibold text-gray-800">{citation.version}</p>
          </div>
          <div>
            <label className="text-xs text-gray-500">Trang số</label>
            <p className="font-semibold text-gray-800">{citation.page}</p>
          </div>
          {citation.article && (
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Điều khoản</label>
              <p className="font-semibold text-indigo-700">{citation.article}</p>
            </div>
          )}
        </div>

        <div>
          <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Nguyên văn trích dẫn</label>
          <div className="mt-1.5 p-3.5 bg-amber-50/60 border-l-4 border-amber-400 rounded-r-lg text-gray-800 leading-relaxed italic text-xs sm:text-sm">
            "{citation.quote}"
          </div>
        </div>

        <div className="pt-2">
          <a
            href={citation.url}
            target="_blank"
            rel="noreferrer"
            className="w-full inline-flex items-center justify-center px-4 py-2 border border-indigo-200 text-xs font-semibold rounded-lg text-indigo-700 bg-indigo-50 hover:bg-indigo-100 transition"
          >
            <FileText className="w-4 h-4 mr-1.5" />
            Xem văn bản PDF gốc
            <ExternalLink className="w-3.5 h-3.5 ml-1.5" />
          </a>
        </div>
      </div>
    </div>
  );
};

