'use client';

import React, { useState, useEffect, useRef } from 'react';
import { readSSEStream, ChatDoneResponse, CitationItem } from '@/lib/sse';
import { useAuth } from '@/lib/auth';
import { CitationDrawer } from '@/components/CitationDrawer';
import { 
  Send, 
  Bot, 
  User, 
  ThumbsUp, 
  ThumbsDown, 
  AlertTriangle, 
  BookOpen, 
  HelpCircle, 
  ShieldAlert, 
  Sparkles,
  Info
} from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  confidence?: number;
  citations?: CitationItem[];
  fallback?: {
    reason: string;
    suggestedUnit: string;
    contactEmail: string;
    message: string;
  } | null;
  feedbackGiven?: 'HELPFUL' | 'UNHELPFUL' | 'REPORTED';
}

export const ChatWindow: React.FC = () => {
  const { token, user } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Khởi tạo hoặc lấy sessionId
  useEffect(() => {
    const initSession = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/v1/chat/sessions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ title: 'Hỏi đáp quy chế đại học' }),
        });
        if (res.ok) {
          const data = await res.json();
          setSessionId(data.sessionId);
        }
      } catch (err) {
        // Fallback local UUID
        setSessionId('sess-' + Date.now());
      }
    };
    initSession();
  }, [token]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputValue;
    if (!text.trim() || isSubmitting) return;

    if (!textToSend) {
      setInputValue('');
    }

    const currentSessId = sessionId || 'sess-default';

    // Thêm câu hỏi của user
    const userMsgId = 'u-' + Date.now();
    const botMsgId = 'b-' + Date.now();

    const newMessages: ChatMessage[] = [
      ...messages,
      { id: userMsgId, role: 'user', content: text },
      { id: botMsgId, role: 'assistant', content: '', isStreaming: true },
    ];
    setMessages(newMessages);
    setIsSubmitting(true);

    const streamUrl = `http://localhost:8000/api/v1/chat/sessions/${currentSessId}/messages`;

    await readSSEStream(
      streamUrl,
      { content: text },
      token,
      // onToken: stream từng chữ
      (tokenText) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMsgId
              ? { ...m, content: m.content + tokenText }
              : m
          )
        );
      },
      // onDone: nhận trích dẫn, điểm tin cậy và fallback
      (doneData: ChatDoneResponse) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMsgId
              ? {
                  ...m,
                  id: doneData.messageId,
                  content: doneData.answer,
                  isStreaming: false,
                  confidence: doneData.confidence,
                  citations: doneData.citations,
                  fallback: doneData.fallback,
                }
              : m
          )
        );
        setIsSubmitting(false);
      },
      // onError
      (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMsgId
              ? {
                  ...m,
                  content: 'Hệ thống chưa kết nối được máy chủ RAG hoặc có lỗi xử lý. Bạn vui lòng kiểm tra lại dịch vụ Backend.',
                  isStreaming: false,
                  confidence: 0.1,
                  fallback: {
                    reason: 'SERVER_ERROR',
                    suggestedUnit: 'Phòng Đào tạo',
                    contactEmail: 'daotao@uni.edu.vn',
                    message: 'Hiện tại hệ thống RAG đang ngoại tuyến.',
                  },
                }
              : m
          )
        );
        setIsSubmitting(false);
      }
    );
  };

  const handleFeedback = async (messageId: string, rating: 'HELPFUL' | 'UNHELPFUL', isReport: boolean = false) => {
    try {
      await fetch(`http://localhost:8000/api/v1/chat/messages/${messageId}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          rating,
          comment: isReport ? 'Báo sai nội dung câu trả lời' : null,
          isReportedWrong: isReport,
        }),
      });

      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? { ...m, feedbackGiven: isReport ? 'REPORTED' : rating }
            : m
        )
      );
    } catch {}
  };

  const renderContentWithCitations = (content: string, citations?: CitationItem[]) => {
    if (!citations || citations.length === 0) {
      return <span className="whitespace-pre-wrap">{content}</span>;
    }

    // Tách các thẻ [1], [2], v.v.
    const parts = content.split(/(\[\d+\])/g);
    return (
      <span className="whitespace-pre-wrap">
        {parts.map((part, i) => {
          const match = part.match(/\[(\d+)\]/);
          if (match) {
            const refNum = parseInt(match[1]);
            const cite = citations.find((c) => c.ref === refNum);
            if (cite) {
              return (
                <button
                  key={i}
                  onClick={() => setSelectedCitation(cite)}
                  className="inline-flex items-center mx-1 px-1.5 py-0.5 rounded text-[11px] font-bold bg-indigo-100 text-indigo-700 hover:bg-indigo-200 transition cursor-pointer border border-indigo-200 shadow-xs"
                  title={`${cite.documentTitle} - ${cite.article || ''} (Trang ${cite.page})`}
                >
                  [{refNum}]
                </button>
              );
            }
          }
          return part;
        })}
      </span>
    );
  };

  const sampleQuestions = [
    'Em học kỳ 2 năm nhất, muốn xin bảo lưu vì lý do cá nhân thì cần điều kiện gì?',
    'Bị cảnh báo học tập mức 1 thì được đăng ký tối đa bao nhiêu tín chỉ?',
    'CPA 3.45 nhưng học lại 8/130 tín chỉ thì có được bằng Giỏi không?',
    'Cho em hỏi theo quy chế cũ năm 2021 thì điều kiện CPA để bảo lưu là bao nhiêu?',
    'Chiều nay từ 14h đến 16h ở tòa A2 có phòng học nào trống không?',
    'Mất thẻ sinh viên thì làm thủ tục cấp lại ở phòng nào?',
  ];

  return (
    <div className="flex flex-col h-[750px] bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden relative">
      {/* Chat Header */}
      <div className="p-4 bg-gradient-to-r from-indigo-700 via-indigo-600 to-primary-600 text-white flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-white/20 backdrop-blur-md flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-sm sm:text-base flex items-center space-x-2">
              <span>Trợ lý Quy chế & Học vụ CampusMate</span>
              <span className="text-[10px] bg-emerald-400 text-slate-900 font-extrabold px-2 py-0.5 rounded-full uppercase">
                RAG v2
              </span>
            </h2>
            <p className="text-xs text-indigo-100">
              Tra cứu quy chế đào tạo, chuẩn đầu ra, điểm rèn luyện & thời khóa biểu
            </p>
          </div>
        </div>

        <div className="text-right hidden sm:block">
          <span className="text-[11px] bg-white/10 px-2.5 py-1 rounded-full text-indigo-100 flex items-center space-x-1">
            <Sparkles className="w-3 h-3 text-amber-300" />
            <span>Xác thực trích dẫn & Khử PII</span>
          </span>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-5 bg-slate-50/50">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-inner">
              <Bot className="w-8 h-8" />
            </div>
            <div>
              <h3 className="font-bold text-gray-800 text-base">Chào bạn, mình có thể hỗ trợ gì cho bạn hôm nay?</h3>
              <p className="text-xs text-gray-500 max-w-md mt-1">
                Mọi thông tin quy chế đều được trích dẫn chính xác từ văn bản ban hành chính thức của nhà trường.
              </p>
            </div>

            {/* Quick Prompts */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full pt-2">
              {sampleQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(q)}
                  className="text-left p-3 rounded-xl bg-white hover:bg-indigo-50/70 border border-gray-200 hover:border-indigo-200 text-xs text-gray-700 transition flex items-center justify-between group shadow-2xs"
                >
                  <span>{q}</span>
                  <HelpCircle className="w-3.5 h-3.5 text-gray-400 group-hover:text-indigo-600 transition shrink-0 ml-2" />
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start space-x-3 ${msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
          >
            {/* Avatar */}
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gradient-to-tr from-indigo-500 to-primary-600 text-white shadow-xs'
              }`}
            >
              {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Message Bubble */}
            <div className={`max-w-[85%] sm:max-w-[75%] space-y-2`}>
              <div
                className={`p-4 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-xs shadow-xs'
                    : 'bg-white text-gray-800 border border-gray-200/80 rounded-tl-xs shadow-xs'
                }`}
              >
                {/* Fallback Box nếu AI từ chối có kiểm soát (BR02) */}
                {msg.fallback ? (
                  <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 space-y-2">
                    <div className="flex items-center space-x-2 font-semibold text-xs">
                      <ShieldAlert className="w-4 h-4 text-amber-600" />
                      <span>{msg.fallback.message}</span>
                    </div>
                    <div className="text-xs bg-white/80 p-2.5 rounded-lg border border-amber-100 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Phòng ban phụ trách:</span>
                        <span className="font-bold text-gray-800">{msg.fallback.suggestedUnit}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Email liên hệ:</span>
                        <a href={`mailto:${msg.fallback.contactEmail}`} className="text-indigo-600 hover:underline font-medium">
                          {msg.fallback.contactEmail}
                        </a>
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    {renderContentWithCitations(msg.content, msg.citations)}
                    {msg.isStreaming && (
                      <span className="inline-block w-2 h-4 bg-indigo-600 animate-pulse ml-1 align-middle" />
                    )}
                  </>
                )}

                {/* Trích dẫn đính kèm */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[11px] font-semibold text-gray-400 mr-1 flex items-center">
                      <BookOpen className="w-3 h-3 mr-1" />
                      Căn cứ:
                    </span>
                    {msg.citations.map((c) => (
                      <button
                        key={c.ref}
                        onClick={() => setSelectedCitation(c)}
                        className="text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-gray-700 px-2 py-0.5 rounded-md border border-gray-200 transition"
                      >
                        [{c.ref}] {c.documentTitle} ({c.article || `Trang ${c.page}`})
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Bot Meta & Actions */}
              {msg.role === 'assistant' && !msg.isStreaming && (
                <div className="flex items-center justify-between px-1 text-[11px] text-gray-400">
                  {/* Cảnh báo tham khảo cố định (BR03) */}
                  <div className="flex items-center space-x-1 italic text-gray-500 max-w-[70%]">
                    <Info className="w-3 h-3 text-gray-400 shrink-0" />
                    <span className="truncate">Câu trả lời chỉ mang tính tham khảo; văn bản gốc là căn cứ chính thức.</span>
                  </div>

                  {/* Feedback Buttons (FR04) */}
                  <div className="flex items-center space-x-1 shrink-0">
                    <button
                      onClick={() => handleFeedback(msg.id, 'HELPFUL')}
                      disabled={!!msg.feedbackGiven}
                      className={`p-1 rounded hover:bg-gray-100 transition ${
                        msg.feedbackGiven === 'HELPFUL' ? 'text-emerald-600 font-bold' : 'text-gray-400'
                      }`}
                      title="Hữu ích"
                    >
                      <ThumbsUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleFeedback(msg.id, 'UNHELPFUL')}
                      disabled={!!msg.feedbackGiven}
                      className={`p-1 rounded hover:bg-gray-100 transition ${
                        msg.feedbackGiven === 'UNHELPFUL' ? 'text-amber-600 font-bold' : 'text-gray-400'
                      }`}
                      title="Không hữu ích"
                    >
                      <ThumbsDown className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleFeedback(msg.id, 'UNHELPFUL', true)}
                      disabled={!!msg.feedbackGiven}
                      className={`p-1 rounded hover:bg-gray-100 transition ${
                        msg.feedbackGiven === 'REPORTED' ? 'text-rose-600 font-bold' : 'text-gray-400'
                      }`}
                      title="Báo sai nội dung quy chế"
                    >
                      <AlertTriangle className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-3 sm:p-4 bg-white border-t border-gray-200">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center space-x-2"
        >
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Hỏi về quy chế đào tạo, bảo lưu, lịch học, phòng trống..."
            disabled={isSubmitting}
            className="flex-1 px-4 py-3 rounded-xl border border-gray-300 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 text-sm transition"
          />
          <button
            type="submit"
            disabled={isSubmitting || !inputValue.trim()}
            className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-medium text-sm flex items-center justify-center transition shadow-xs"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
        <div className="flex items-center justify-between mt-2 px-1 text-[11px] text-gray-400">
          <span>Tự động khử dữ liệu định danh cá nhân (MSSV, SĐT, Email) theo chuẩn BR08</span>
          <span className="hidden sm:inline">Phím Enter để gửi câu hỏi</span>
        </div>
      </div>

      {/* Citation Drawer Slider */}
      <CitationDrawer citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
    </div>
  );
};

