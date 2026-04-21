import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Server, Shield, Globe, Save, RotateCcw } from 'lucide-react';
import type { NamoSettings } from '../hooks/useNamoSettings';
import { DEFAULT_SETTINGS } from '../hooks/useNamoSettings';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: NamoSettings;
  onSave: (settings: NamoSettings) => void;
}

export function SettingsModal({ isOpen, onClose, settings, onSave }: SettingsModalProps) {
  const [cfg, setCfg] = useState<NamoSettings>(settings);

  const handleUpdate = (key: keyof NamoSettings, val: string) => {
    setCfg((prev: NamoSettings) => ({ ...prev, [key]: val }));
  };

  const handleSave = () => {
    onSave(cfg);
    onClose();
  };

  const handleReset = () => {
    setCfg(DEFAULT_SETTINGS);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-slate-950/60 backdrop-blur-xl"
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="relative bg-slate-900 border border-white/10 rounded-[2.5rem] shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]"
          >
            {/* Modal Header */}
            <div className="px-8 pt-8 pb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <Server className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white tracking-tight">Core Configuration</h3>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Namo Sovereign v5.0.0</p>
                </div>
              </div>
              <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full text-slate-500 hover:text-white transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto px-8 py-4 space-y-6">
              {/* Mode Selection */}
              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5" />
                  Connectivity Mode
                </label>
                <div className="grid grid-cols-2 gap-3 p-1 rounded-2xl bg-slate-950/50 border border-white/5">
                  <ModeTab 
                    active={cfg.mode === 'local'} 
                    label="Local Server" 
                    onClick={() => handleUpdate('mode', 'local')} 
                  />
                  <ModeTab 
                    active={cfg.mode === 'tunnel'} 
                    label="Cloud Tunnel" 
                    onClick={() => handleUpdate('mode', 'tunnel')} 
                  />
                </div>
              </div>

              {/* Dynamic Fields */}
              <div className="grid grid-cols-1 gap-6">
                {cfg.mode === 'local' ? (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="col-span-2">
                      <Field label="Server Host" value={cfg.localIp} onChange={(v: string) => handleUpdate('localIp', v)} placeholder="192.168.1.102" />
                    </div>
                    <div>
                      <Field label="Port" value={cfg.localPort} onChange={(v: string) => handleUpdate('localPort', v)} placeholder="8000" type="number" />
                    </div>
                  </div>
                ) : (
                  <Field label="Tunnel Endpoint" value={cfg.tunnelUrl} onChange={(v: string) => handleUpdate('tunnelUrl', v)} placeholder="https://api.namonexus.com" />
                ) }

                <Field 
                  label="Security Token (Access Key)" 
                  value={cfg.token} 
                  onChange={(v: string) => handleUpdate('token', v)} 
                  placeholder="••••••••••••" 
                  type="password" 
                  icon={<Shield className="w-3.5 h-3.5" />}
                />
              </div>

              {/* Connection Preview */}
              <div className="p-4 rounded-2xl bg-slate-950/50 border border-indigo-500/10 space-y-2">
                <p className="text-[10px] text-slate-600 uppercase font-black tracking-widest">Protocol Metadata</p>
                <code className="text-[11px] text-cyan-400/80 block break-all font-mono">
                  {cfg.mode === 'local' ? `ws://${cfg.localIp}:${cfg.localPort}/ws` : `${cfg.tunnelUrl}/ws`}
                </code>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-8 pt-4 flex gap-3">
              <button 
                onClick={handleReset}
                className="flex items-center gap-2 px-5 py-3 rounded-2xl text-slate-400 hover:text-white hover:bg-white/5 transition-all text-sm font-bold active:scale-95"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
              <button 
                onClick={handleSave}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-xl shadow-indigo-600/20 transition-all font-bold active:scale-95 text-sm"
              >
                <Save className="w-4 h-4" />
                Apply Configuration
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

function ModeTab({ active, label, onClick }: { active: boolean, label: string, onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`
        px-4 py-2 rounded-xl text-xs font-bold transition-all
        ${active ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-500 hover:text-slate-300'}
      `}
    >
      {label}
    </button>
  );
}

function Field({ label, value, onChange, placeholder, type = "text", icon }: any) {
  return (
    <div className="space-y-2">
      <label className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
        {icon}
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-slate-950/50 border border-white/5 focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 rounded-xl px-4 py-3 text-sm text-white transition-all outline-none"
      />
    </div>
  );
}
