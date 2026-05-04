import { useState } from 'react';
import { Header } from '../components/Header';
import { AIStatusIndicator } from '../components/AIStatusIndicator';
import { TranscriptPanel } from '../components/TranscriptPanel';
import { ControlBar } from '../components/ControlBar';
import { SettingsModal } from '../components/SettingsModal';
import { NotebookDashboard } from '../components/NotebookDashboard';
import { DocumentToSkillModal } from '../components/DocumentToSkillModal';
import { useNamoSettings } from '../hooks/useNamoSettings';
import { useNamoSocket } from '../hooks/useNamoSocket';
import { Book, Sparkles } from 'lucide-react';

export function TeacherView() {
  const { settings, saveSettings, wsUrl, httpUrl, fetchWithAuth } = useNamoSettings();
  const { data, status, connect, disconnect } = useNamoSocket(!wsUrl ? null : wsUrl);
  
  const [isMuted, setIsMuted] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isNotebookOpen, setIsNotebookOpen] = useState(false);
  const [isSkillModalOpen, setIsSkillModalOpen] = useState(false);

  const handleClearChat = () => {
    console.log("Clearing chat context...");
  };

  const handleCreateSkill = (description: string, files: File[]) => {
    console.log("Creating skill with description:", description, "and files:", files);
    // Future implementation: API call to create skill
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col overflow-hidden font-sans selection:bg-cyan-500/30">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-cyan-600/5 blur-[120px] rounded-full" />
      </div>

      <Header 
        status={status} 
        httpUrl={httpUrl}
        onSettingsClick={() => setIsSettingsOpen(true)} 
      />

      <main className="flex-1 flex flex-col min-w-0 container max-w-4xl mx-auto px-4">
        <div className="flex-shrink-0 pt-4 flex items-center justify-end gap-3">
          <AIStatusIndicator status={status} isMuted={isMuted} />
          
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setIsSkillModalOpen(true)}
              className="flex items-center gap-2 bg-slate-900/50 hover:bg-indigo-500/10 border border-slate-800 hover:border-indigo-500/50 px-4 py-2 rounded-xl transition-all group"
            >
              <Sparkles className="w-5 h-5 text-slate-400 group-hover:text-indigo-400" />
              <span className="text-sm font-bold text-slate-300 group-hover:text-white uppercase tracking-tighter">Skill Sync</span>
            </button>

            <button 
              onClick={() => setIsNotebookOpen(true)}
              className="flex items-center gap-2 bg-slate-900/50 hover:bg-cyan-500/10 border border-slate-800 hover:border-cyan-500/50 px-4 py-2 rounded-xl transition-all group"
            >
              <Book className="w-5 h-5 text-slate-400 group-hover:text-cyan-400" />
              <span className="text-sm font-bold text-slate-300 group-hover:text-white">สมุดบันทึกนะโม</span>
            </button>
          </div>
        </div>

        <div className="flex-1 min-h-0 flex flex-col">
          <TranscriptPanel data={data} />
        </div>
      </main>

      <ControlBar 
        status={status}
        isMuted={isMuted}
        onConnect={() => connect()}
        onDisconnect={disconnect}
        onToggleMute={() => setIsMuted(!isMuted)}
        onClear={handleClearChat}
      />

      <SettingsModal 
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={settings}
        onSave={saveSettings}
      />

      <NotebookDashboard 
        isOpen={isNotebookOpen}
        onClose={() => setIsNotebookOpen(false)}
        httpUrl={httpUrl}
        wsUrl={wsUrl}
        fetchWithAuth={fetchWithAuth}
        aiStatus={status}
        isMuted={isMuted}
      />

      <DocumentToSkillModal
        isOpen={isSkillModalOpen}
        onClose={() => setIsSkillModalOpen(false)}
        onCreate={handleCreateSkill}
      />
    </div>
  );
}
