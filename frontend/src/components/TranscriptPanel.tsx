import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { NamoData } from '../hooks/useNamoSocket';

interface TranscriptPanelProps {
  data: NamoData | null;
}

export function TranscriptPanel({ data }: TranscriptPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new transcripts
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [data?.transcript?.text]);

  // Mock initial transcripts for 'wow' factor if empty
  const transcripts = data?.transcript ? [data.transcript] : [
    { text: "Namo Core v5.0.0 is ready. How can I assist your lesson today?", speaker: "namo" as const, is_final: true }
  ];

  return (
    <div className="flex-1 flex flex-col min-h-0 relative">
      {/* Top Fade Gradient */}
      <div className="absolute top-0 inset-x-0 h-12 bg-gradient-to-b from-slate-950 to-transparent z-10 pointer-events-none" />

      {/* Scrollable Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-1 py-8 space-y-6 scroll-smooth"
      >
        <AnimatePresence mode="popLayout">
          {transcripts.map((t, idx) => (
            <motion.div
              key={idx + (t.text)}
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className={`flex ${t.speaker === 'namo' ? 'justify-start' : 'justify-end'}`}
            >
              <div 
                className={`
                  max-w-[85%] px-5 py-3.5 rounded-2xl text-sm leading-relaxed
                  ${t.speaker === 'namo' 
                    ? 'glass border-cyan-500/10 text-cyan-50/90 rounded-bl-none' 
                    : 'bg-indigo-600/90 text-white shadow-lg shadow-indigo-500/20 rounded-br-none'
                  }
                `}
              >
                <p>{t.text}</p>
                {!t.is_final && t.speaker === 'user' && (
                  <motion.span 
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1, repeat: Infinity }}
                    className="inline-block w-1.5 h-4 ml-1 bg-white/50 align-middle"
                  />
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Bottom Fade Gradient */}
      <div className="absolute bottom-0 inset-x-0 h-8 bg-gradient-to-t from-slate-950 to-transparent z-10 pointer-events-none" />
    </div>
  );
}
