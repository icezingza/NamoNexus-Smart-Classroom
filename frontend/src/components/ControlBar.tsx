import { Power, Mic, MicOff, Trash2, Globe } from 'lucide-react';
import type { NamoStatus } from '../hooks/useNamoSocket';

interface ControlBarProps {
  status: NamoStatus;
  isMuted: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  onToggleMute: () => void;
  onClear: () => void;
}

export function ControlBar({ 
  status, 
  isMuted, 
  onConnect, 
  onDisconnect, 
  onToggleMute, 
  onClear 
}: ControlBarProps) {
  const isConnected = status === 'connected';

  return (
    <footer className="flex-shrink-0 px-6 py-8 pb-10 flex items-center justify-center gap-4 z-50">
      <div className="glass px-6 py-4 rounded-3xl flex items-center gap-3 shadow-2xl border-white/5 glow-indigo">
        
        {/* Main Connect/Power Button */}
        <button
          onClick={isConnected ? onDisconnect : onConnect}
          className={`
            flex items-center gap-2.5 px-6 py-3 rounded-2xl font-bold transition-all active:scale-95
            ${isConnected 
              ? 'bg-rose-600/20 text-rose-500 border border-rose-500/30' 
              : 'bg-cyan-600 text-white shadow-[0_8px_30px_rgb(8,145,178,0.3)]'
            }
          `}
        >
          <Power className="w-5 h-5" />
          <span>{isConnected ? 'Disconnect' : 'Activate Namo'}</span>
        </button>

        <div className="w-[1px] h-8 bg-white/10 mx-2" />

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Mute Toggle */}
          <ControlButton 
            icon={isMuted ? MicOff : Mic} 
            active={isMuted} 
            onClick={onToggleMute}
            label={isMuted ? "Unmute" : "Mute"}
            danger={isMuted}
            disabled={!isConnected}
          />

          {/* Clear Context */}
          <ControlButton 
            icon={Trash2} 
            onClick={onClear}
            label="Clear"
            disabled={!isConnected}
          />
          
          {/* Language / Mode Switch (Mock for now) */}
          <ControlButton 
            icon={Globe} 
            onClick={() => {}}
            label="Thai"
            disabled={!isConnected}
          />
        </div>
      </div>
    </footer>
  );
}

function ControlButton({ 
  icon: Icon, 
  active, 
  onClick, 
  label, 
  danger, 
  disabled 
}: { 
  icon: any, 
  active?: boolean, 
  onClick: () => void, 
  label: string,
  danger?: boolean,
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        group relative flex flex-col items-center justify-center w-14 h-14 rounded-2xl transition-all active:scale-90
        ${disabled ? 'opacity-30 cursor-not-allowed' : 'hover:bg-white/5 cursor-pointer'}
        ${active && danger ? 'text-rose-500 bg-rose-500/10' : 'text-slate-400 hover:text-white'}
      `}
    >
      <Icon className="w-6 h-6" />
      <span className="absolute -top-10 scale-0 group-hover:scale-100 transition-transform bg-slate-800 text-white text-[10px] px-2 py-1 rounded-md pointer-events-none uppercase font-bold">
        {label}
      </span>
    </button>
  );
}
