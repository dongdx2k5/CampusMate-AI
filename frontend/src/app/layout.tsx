import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth';
import { Navbar } from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'CampusMate AI — Cổng thông tin & Trợ lý số đại học',
  description: 'Trợ lý số đại học tích hợp RAG tiếng Việt, tra cứu quy chế, thời khóa biểu, phòng trống và thông báo.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="bg-slate-50 text-gray-900 min-h-screen flex flex-col font-sans antialiased selection:bg-indigo-500 selection:text-white">
        <AuthProvider>
          <Navbar />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {children}
          </main>
          <footer className="bg-white border-t border-gray-200 py-6 text-center text-xs text-gray-500">
            <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
              <p>© 2026 CampusMate AI — Hệ thống Trợ lý số Đại học & RAG tiếng Việt chuẩn hóa.</p>
              <p className="italic text-gray-400">
                Tuân thủ BR01-BR08 | Tiêu chuẩn WCAG 2.1 AA | Bảo mật dữ liệu định danh (PII)
              </p>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}

