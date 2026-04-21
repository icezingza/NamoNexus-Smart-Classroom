import { Settings, ShieldCheck } from 'lucide-react';
import type { NamoStatus } from '../hooks/useNamoSocket';

interface HeaderProps {
  status: NamoStatus;
  httpUrl: string;
  onSettingsClick: () => void;
}

export function Header({ status, httpUrl, onSettingsClick }: HeaderProps) {
  return (
    <header className="flex-shrink-0 glass-header px-6 py-4 flex items-center justify-between z-50">
      {/* Brand Section */}
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <span className="text-white font-bold text-xl tracking-tighter">N</span>
        </div>
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight leading-none">Namo Core</h1>
          <div className="flex items-center gap-1.5 mt-1">
            <ShieldCheck className="w-3 h-3 text-cyan-400" />
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Sovereign v5.0.0</span>
          </div>
        </div>
      </div>

      {/* Connectivity & Actions */}
      <div className="flex items-center gap-6">
        {/* Connection Payload (Investor Wow) */}
        <div className="hidden md:flex flex-col items-end">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-slate-500">{httpUrl}</span>
            <div className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-cyan-500 animate-pulse' : 'bg-slate-600'}`} />
          </div>
          <p className="text-[9px] text-slate-600 uppercase tracking-tighter mt-1 font-bold">Encrypted Pipeline Active</p>
        </div>

        <div className="h-8 w-[1px] bg-white/10" />

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button 
            onClick={onSettingsClick}
            className="p-2.5 rounded-xl hover:bg-white/5 text-slate-400 hover:text-white transition-all active:scale-95 border border-transparent hover:border-white/10"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
