import { useEffect } from 'react';
import { AIStatusIndicator } from '../components/AIStatusIndicator';
import { TranscriptPanel } from '../components/TranscriptPanel';
import { useNamoSettings } from '../hooks/useNamoSettings';
import { useNamoSocket } from '../hooks/useNamoSocket';

export function DisplayView() {
  const { wsUrl } = useNamoSettings();
  const { data, status, connect } = useNamoSocket(!wsUrl ? null : wsUrl);

  useEffect(() => {
    // Auto-connect on display view
    connect();
  }, [connect]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col overflow-hidden font-sans selection:bg-cyan-500/30">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-cyan-600/5 blur-[120px] rounded-full" />
      </div>

      <main className="flex-1 flex flex-col min-w-0 container max-w-6xl mx-auto px-8 py-12">
        <div className="flex-shrink-0 pb-8 flex items-center justify-center">
          <AIStatusIndicator status={status} isMuted={false} />
        </div>

        <div className="flex-1 min-h-0 flex flex-col">
          {/* TranscriptPanel is designed to show big text */}
          <TranscriptPanel data={data} />
        </div>
      </main>
    </div>
  );
}
