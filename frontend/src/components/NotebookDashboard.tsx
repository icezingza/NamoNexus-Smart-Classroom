import React, { useState, useEffect } from 'react';
import { Book, Save, Plus, FileText, HelpCircle, Mic, CreditCard, Send, Loader2, Search } from 'lucide-react';

interface SourceItem {
  title: string;
  text: string;
  source: string;
}

interface NotebookDashboardProps {
  isOpen: boolean;
  onClose: () => void;
  httpUrl: string;
  wsUrl: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  aiStatus: string;
  isMuted: boolean;
}

const DHAMMA_QUOTES = [
  "ผู้ให้ย่อมผูกมิตรไว้ได้ (สังยุตตนิกาย)",
  "แสงสว่างเสมอด้วยปัญญาไม่มี (สังยุตตนิกาย)",
  "การฝึกจิตเป็นความดี จิตที่ฝึกดีแล้วนำสุขมาให้ (ขุททกนิกาย)",
  "ปัญญาประเสริฐกว่าทรัพย์ (มัชฌิมนิกาย)",
  "บุคคลย่อมบริสุทธิ์ด้วยปัญญา (ขุททกนิกาย)",
  "สติเป็นเครื่องตื่นในโลก (สังยุตตนิกาย)"
];

export const NotebookDashboard: React.FC<NotebookDashboardProps> = ({
  isOpen,
  onClose,
  httpUrl,
  wsUrl,
  fetchWithAuth,
  aiStatus,
  isMuted
}) => {
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [query, setQuery] = useState("");
  const [instruction, setInstruction] = useState("");
  const [mode, setMode] = useState("briefing");
  const [result, setResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<SourceItem[]>([]);

  const [searchError, setSearchError] = useState<string>('');

  const [quoteIndex, setQuoteIndex] = useState(0);

  useEffect(() => {
    let interval: any;
    if (isLoading) {
      interval = setInterval(() => {
        setQuoteIndex(prev => (prev + 1) % DHAMMA_QUOTES.length);
      }, 3500);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  if (!isOpen) return null;

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearchError('');
    setSuggestions([]);
    try {
      const url = `${httpUrl}/notebook/suggest-sources?q=${encodeURIComponent(query)}`;
      console.log('[NamoNotebook] Searching:', url);
      const resp = await fetchWithAuth(url);
      if (!resp.ok) {
        setSearchError(`ค้นหาไม่สำเร็จ (HTTP ${resp.status})`);
        return;
      }
      const data = await resp.json();
      const items = data.suggestions || [];
      console.log('[NamoNotebook] Got suggestions:', items.length);
      if (items.length === 0) {
        setSearchError('ไม่พบคัมภีร์ที่ตรงกับคำค้นหา ลองคำอื่นดูครับ');
      }
      setSuggestions(items);
    } catch (err) {
      console.error('[NamoNotebook] Search failed:', err);
      setSearchError('เชื่อมต่อ Backend ไม่ได้ กรุณาตรวจสอบการเชื่อมต่อ');
    }
  };

  const addSource = (src: SourceItem) => {
    if (!sources.find(s => s.text === src.text)) {
      setSources([...sources, src]);
    }
    setSuggestions([]);
    setQuery("");
  };

  const handleGenerate = async () => {
    if (sources.length === 0) return;
    setIsLoading(true);
    setResult(null);
    setQuoteIndex(0);

    try {
      const resp = await fetchWithAuth(`${httpUrl}/notebook/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sources, mode, instruction })
      });
      const data = await resp.json();

      if (data.job_id) {
        // Attempt WebSocket connection for Real-Time Event-Driven Updates
        let wsConnected = false;
        try {
          const wsEndpoint = wsUrl.split('?')[0].replace('/ws', `/notebook/ws/${data.job_id}`);
          // Include token in query string if needed, assuming wsEndpoint handled it
          const wsTokenParams = wsUrl.includes('?') ? `?${wsUrl.split('?')[1]}` : '';
          const ws = new WebSocket(`${wsEndpoint}${wsTokenParams}`);
          let pingInterval: ReturnType<typeof setInterval>;

          ws.onopen = () => {
            wsConnected = true;
            // Heartbeat: ส่ง Ping ทุกๆ 30 วินาที เพื่อป้องกันท่อ WebSocket หลุด (The Long-Run Test)
            pingInterval = setInterval(() => {
              if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "ping" }));
              }
            }, 30000);
          };
          ws.onmessage = (event) => {
            const payload = JSON.parse(event.data);
            if (payload.status === "completed" || payload.status === "failed") {
              setResult(payload);
              setIsLoading(false);
              clearInterval(pingInterval);
              ws.close();
            }
          };
          ws.onerror = () => {
            clearInterval(pingInterval);
            ws.close();
          };
          ws.onclose = () => {
            clearInterval(pingInterval);
            // Fallback: If disconnected and still loading, start HTTP Polling
            if (isLoading && wsConnected) {
              console.warn("WebSocket dropped, falling back to HTTP polling...");
              startHttpPolling(data.job_id);
            } else if (isLoading && !wsConnected) {
              startHttpPolling(data.job_id);
            }
          };
        } catch (e) {
          startHttpPolling(data.job_id);
        }
      } else {
        setResult(data);
        setIsLoading(false);
      }
    } catch (err) {
      console.error("Generation failed", err);
      setIsLoading(false);
    }
  };

  const startHttpPolling = (jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const resp = await fetchWithAuth(`${httpUrl}/notebook/job/${jobId}`);
        const data = await resp.json();
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(pollInterval);
          setResult(data);
          setIsLoading(false);
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 3000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-2 md:p-4 animate-in fade-in duration-300">
      <div className="bg-slate-950 border border-slate-800 w-full max-w-7xl h-[95vh] md:h-[85vh] rounded-3xl shadow-2xl flex flex-col overflow-hidden">

        {/* Mobile-Friendly Header */}
        <div className="flex items-center justify-between px-4 md:px-8 py-4 md:py-6 border-b border-slate-800 bg-slate-900/40">
          <div className="flex items-center gap-4 md:gap-8">
            <div className="flex items-center gap-3">
              <div className="bg-cyan-500/20 p-2.5 rounded-2xl shadow-inner">
                <Book className="text-cyan-400 w-6 h-6 md:w-7 md:h-7" />
              </div>
              <div>
                <h2 className="text-lg md:text-2xl font-black text-white tracking-tight">Namo Notebook</h2>
                <p className="hidden md:block text-[10px] text-slate-500 uppercase tracking-[0.2em] font-bold">Wisdom Synthesis Engine</p>
              </div>
            </div>

            {/* Smart Status Bar - Tablet Optimized */}
            <div className="flex items-center gap-3 md:gap-4 px-3 md:px-5 py-2 bg-slate-900/80 rounded-2xl border border-slate-800/50">
              <div className="flex items-center gap-2 border-r border-slate-800 pr-3 md:pr-4">
                <div className={`w-2.5 h-2.5 rounded-full ${aiStatus === 'connected' ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.6)]' : 'bg-rose-500'}`} />
                <span className="text-[10px] md:text-xs font-black text-slate-300 uppercase">AI</span>
              </div>

              <div className="flex items-center gap-2" title="สถานะการเชื่อมต่อ AI (ไม่ใช่ไมโครโฟน)">
                <Mic className={`w-4 h-4 ${isMuted ? 'text-rose-500' : 'text-cyan-400'}`} />
                <div className="flex items-center gap-1">
                  {[0.4, 0.7, 0.3, 0.9, 0.5].map((h, i) => (
                    <div
                      key={i}
                      className="w-1 bg-cyan-500/40 rounded-full transition-all duration-300"
                      style={{
                        height: aiStatus === 'connected' && !isMuted ? `${h * 14}px` : '3px',
                        opacity: isMuted ? 0.2 : 1
                      }}
                    />
                  ))}
                </div>
                <span className="text-[9px] font-bold text-slate-600 uppercase tracking-tight hidden md:block">AI Signal</span>
              </div>
            </div>
          </div>

          <button onClick={onClose} className="bg-slate-800/50 text-slate-400 hover:text-white p-3 md:p-4 hover:bg-slate-800 rounded-2xl transition-all active:scale-90">
            <Plus className="w-6 h-6 md:w-7 md:h-7 rotate-45" />
          </button>
        </div>

        <div className="flex-1 flex overflow-hidden flex-col md:flex-row">

          {/* Sidebar - Sources (Scrollable on Tablet) */}
          <div className="w-full md:w-[350px] border-b md:border-b-0 md:border-r border-slate-800 p-4 md:p-6 flex flex-col gap-4 md:gap-6 bg-slate-900/20 overflow-y-auto md:overflow-visible h-1/3 md:h-auto">
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="text-[10px] md:text-xs font-black text-slate-500 uppercase tracking-widest">1. ค้นหาคัมภีร์อ้างอิง</label>
                <span className="text-[9px] font-black uppercase tracking-tight text-amber-500/80 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-lg">พิมพ์เท่านั้น</span>
              </div>
              <div className="relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="เช่น มงคลสูตร, ศีล 5..."
                  className="w-full bg-slate-900 border-2 border-slate-800 rounded-2xl px-5 py-3 md:py-4 pr-12 text-sm md:text-base focus:ring-4 focus:ring-cyan-500/10 focus:border-cyan-500/50 outline-none transition-all placeholder:text-slate-600"
                />
                <button onClick={handleSearch} className="absolute right-3 top-1/2 -translate-y-1/2 bg-cyan-500/10 p-2 rounded-xl text-cyan-400 hover:bg-cyan-500 hover:text-white transition-all">
                  <Search className="w-5 h-5 md:w-6 md:h-6" />
                </button>
              </div>

              {/* Suggestions - Touch Optimized */}
              {suggestions.length > 0 && (
                <div className="mt-3 bg-slate-900 border-2 border-slate-800 rounded-2xl max-h-60 overflow-y-auto shadow-2xl z-30 relative divide-y divide-slate-800/50">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => addSource(s)}
                      className="w-full text-left p-4 hover:bg-slate-800 transition-colors active:bg-cyan-500/10 group"
                    >
                      <div className="font-bold text-cyan-400 group-hover:text-cyan-300 text-sm md:text-base mb-1">{s.title || s.text?.slice(0, 40) || '(ไม่มีชื่อ)'}</div>
                      <div className="text-slate-500 line-clamp-1 text-[10px] md:text-xs">{s.text?.slice(0, 80)}</div>
                    </button>
                  ))}
                </div>
              )}
              {searchError && (
                <p className="mt-2 text-xs text-rose-400 px-1">{searchError}</p>
              )}
            </div>

            <div className="flex-1 flex flex-col min-h-0">
              <label className="text-[10px] md:text-xs font-black text-slate-500 uppercase tracking-widest mb-3 block flex items-center justify-between">
                2. คัมภีร์ที่คัดเลือก
                <span className="bg-cyan-500/20 text-cyan-400 px-2.5 py-0.5 rounded-lg">{sources.length}</span>
              </label>
              <div className="flex-1 overflow-y-auto space-y-3 pr-1 custom-scrollbar">
                {sources.map((s, i) => (
                  <div key={i} className="bg-slate-900 border-2 border-slate-800/50 p-4 rounded-2xl relative group hover:border-cyan-500/30 transition-all active:scale-[0.98]">
                    <div className="text-[9px] font-black text-cyan-500/50 uppercase tracking-tighter mb-1">{s.source}</div>
                    <div className="text-xs md:text-sm font-bold text-slate-200 line-clamp-2 leading-relaxed">{s.title}</div>
                    <button
                      onClick={() => setSources(sources.filter((_, idx) => idx !== i))}
                      className="absolute top-3 right-3 p-2 bg-slate-800 hover:bg-red-500/20 text-slate-500 hover:text-red-400 rounded-xl transition-all"
                    >
                      <Plus className="w-4 h-4 rotate-45" />
                    </button>
                  </div>
                ))}
                {sources.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-32 md:h-40 border-2 border-dashed border-slate-800/50 rounded-3xl text-slate-700 bg-slate-900/10">
                    <Plus className="w-10 h-10 mb-2 opacity-10" />
                    <span className="text-[10px] font-bold uppercase tracking-widest">เพิ่มแหล่งข้อมูล</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Main Content - Generation (Large Hit Targets for Tablet) */}
          <div className="flex-1 p-4 md:p-10 flex flex-col gap-6 md:gap-10 overflow-y-auto custom-scrollbar bg-slate-950">

            <div className="grid grid-cols-3 md:grid-cols-5 gap-3 md:gap-4">
              {[
                { id: 'briefing', label: 'สรุปเตรียมสอน', icon: FileText, color: 'text-indigo-400', bg: 'bg-indigo-500/10', badge: null },
                { id: 'faq', label: 'คู่มือ & FAQ', icon: HelpCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10', badge: null },
                { id: 'audio', label: 'บทละครเสียง', icon: Mic, color: 'text-rose-400', bg: 'bg-rose-500/10', badge: 'บทความ' },
                { id: 'flashcard', label: 'บัตรคำ', icon: CreditCard, color: 'text-amber-400', bg: 'bg-amber-500/10', badge: null },
                { id: 'quiz', label: 'ควิซวัดผล', icon: Save, color: 'text-cyan-400', bg: 'bg-cyan-500/10', badge: null },
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  className={`relative flex flex-col items-center justify-center gap-3 p-4 md:p-6 rounded-[2.5rem] border-2 transition-all active:scale-95 ${mode === m.id
                      ? `border-cyan-500 ${m.bg} shadow-[0_20px_40px_-15px_rgba(6,182,212,0.15)]`
                      : 'border-slate-800/50 bg-slate-900/20 hover:border-slate-700 hover:bg-slate-900/40'
                    }`}
                >
                  {m.badge && (
                    <span className="absolute -top-2 left-1/2 -translate-x-1/2 text-[8px] font-black uppercase tracking-tight text-rose-400 bg-rose-500/10 border border-rose-500/30 px-1.5 py-0.5 rounded-md whitespace-nowrap">{m.badge}</span>
                  )}
                  <div className={`p-3 md:p-4 rounded-2xl ${mode === m.id ? 'bg-cyan-500 text-white' : `${m.bg} ${m.color}`}`}>
                    <m.icon className="w-6 h-6 md:w-8 md:h-8" />
                  </div>
                  <span className={`text-[10px] md:text-xs font-black uppercase tracking-widest ${mode === m.id ? 'text-cyan-400' : 'text-slate-500'}`}>
                    {m.label}
                  </span>
                </button>
              ))}
            </div>

            <div className="space-y-4">
              <label className="text-[10px] md:text-xs font-black text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
                3. คำสั่งพิเศษถึงนะโม (Instruction)
                <span className="h-1 flex-1 bg-slate-800/50 rounded-full" />
              </label>
              <textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="เช่น 'เน้นศัพท์ภาษาบาลี', 'สรุปให้เด็กอนุบาลเข้าใจง่ายๆ'..."
                className="w-full h-32 md:h-40 bg-slate-900 border-2 border-slate-800/50 rounded-[2rem] p-6 md:p-8 text-sm md:text-lg focus:ring-8 focus:ring-cyan-500/5 focus:border-cyan-500/5 focus:border-cyan-500/50 outline-none resize-none transition-all placeholder:text-slate-700 leading-relaxed font-medium"
              />
            </div>

            <button
              onClick={handleGenerate}
              disabled={isLoading || sources.length === 0}
              className={`relative w-full py-5 md:py-8 rounded-[2rem] font-black text-sm md:text-xl uppercase tracking-[0.3em] flex items-center justify-center gap-4 transition-all active:scale-[0.97] overflow-hidden ${isLoading || sources.length === 0
                  ? 'bg-slate-900 text-slate-700 border-2 border-slate-800'
                  : 'bg-gradient-to-br from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-2xl shadow-cyan-500/20'
                }`}
            >
              {isLoading && (
                <div className="absolute inset-0 bg-slate-900/95 backdrop-blur-md flex flex-col items-center justify-center gap-2 animate-in fade-in z-10 text-cyan-400">
                  <div className="flex items-center gap-3">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span className="text-xs font-bold tracking-[0.2em]">Saturating Wisdom...</span>
                  </div>
                  <span className="text-[10px] md:text-xs text-slate-400 normal-case tracking-normal animate-pulse font-medium text-center px-4">
                    "{DHAMMA_QUOTES[quoteIndex]}"
                  </span>
                </div>
              )}
              <Send className="w-6 h-6" />
              Saturate Wisdom
            </button>

            {/* Result Area - Extra Clean for Tablet */}
            {result && (
              <div className="mt-4 pb-20 animate-in slide-in-from-bottom-10 duration-700 ease-out">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-1.5 h-8 bg-cyan-500 rounded-full shadow-[0_0_15px_rgba(6,182,212,0.5)]" />
                    <h3 className="text-xl md:text-3xl font-black text-white tracking-tight">
                      {result.title}
                    </h3>
                  </div>
                  <button className="bg-slate-800 hover:bg-cyan-500 text-slate-300 hover:text-white px-6 py-3 rounded-2xl font-bold text-xs md:text-sm transition-all active:scale-90">
                    Copy Wisdom
                  </button>
                </div>
                <div className="bg-slate-900/50 border-2 border-slate-800/50 rounded-[2.5rem] p-8 md:p-14 text-slate-200 leading-[1.8] whitespace-pre-wrap font-serif text-lg md:text-2xl shadow-2xl backdrop-blur-sm">
                  {result.content}
                </div>
              </div>
            )}
          </div>

        </div>

        {/* Mini Webcam Preview - Movable Placeholder for Tablet */}
        <div className="absolute bottom-6 right-6 w-32 md:w-56 h-24 md:h-36 bg-slate-900 border-2 border-slate-800 rounded-3xl shadow-2xl overflow-hidden group active:scale-95 transition-transform cursor-pointer">
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent z-10" />
          <div className="absolute top-3 left-3 z-20 flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-rose-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(244,63,94,0.8)]" />
            <span className="text-[10px] md:text-xs font-black text-white uppercase tracking-tighter">Room 01</span>
          </div>

          <div className="w-full h-full flex items-center justify-center">
            <img
              src="https://images.unsplash.com/photo-1577891772227-d263f5e3c973?auto=format&fit=crop&q=80&w=400"
              alt="Classroom"
              className="w-full h-full object-cover opacity-40 group-hover:opacity-100 transition-opacity duration-500 scale-110"
            />
          </div>

          <div className="absolute bottom-3 left-3 z-20">
            <p className="text-[9px] md:text-[11px] text-cyan-400 font-black uppercase tracking-widest">Classroom Live</p>
          </div>
        </div>

      </div>
    </div>
  );
};
