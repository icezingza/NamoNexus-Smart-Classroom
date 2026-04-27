import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Circle, MicOff } from 'lucide-react';
import type { NamoStatus } from '../hooks/useNamoSocket';

interface AIStatusIndicatorProps {
  status: NamoStatus;
  isMuted?: boolean;
}

export function AIStatusIndicator({ status, isMuted = false }: AIStatusIndicatorProps) {
  const getStatusConfig = () => {
    if (isMuted) {
      return {
        icon: MicOff,
        text: 'Microphone Muted',
        color: 'text-rose-500',
        glow: 'shadow-[0_0_20px_-5px_rgba(244,63,94,0.5)]',
        accent: 'bg-rose-500/10',
        borderColor: 'border-rose-500/30',
        bg: 'bg-rose-500/5',
        label: 'Press unmute to resume'
      };
    }

    switch (status) {
      case 'connecting':
        return {
          icon: Circle,
          text: 'Establishing Secure Link...',
          color: 'text-indigo-400',
          glow: 'shadow-[0_0_20px_-5px_rgba(129,140,248,0.5)]',
          accent: 'bg-indigo-500/10',
          borderColor: 'border-indigo-500/30',
          bg: 'bg-indigo-500/5',
          label: 'Verifying Namo Core v4.4.0'
        };
      case 'connected':
        return {
          icon: Brain,
          text: 'Namo: Online',
          color: 'text-cyan-400',
          glow: 'shadow-[0_0_25px_-5px_rgba(34,211,238,0.4)]',
          accent: 'bg-cyan-500/10',
          borderColor: 'border-cyan-500/30',
          bg: 'bg-cyan-500/5',
          label: 'Ready for classroom command'
        };
      case 'error':
        return {
          icon: MicOff,
          text: 'Connection Lost',
          color: 'text-amber-500',
          glow: 'shadow-[0_0_20px_-5px_rgba(245,158,11,0.5)]',
          accent: 'bg-amber-500/10',
          borderColor: 'border-amber-500/30',
          bg: 'bg-amber-500/5',
          label: 'Attempting reconnection...'
        };
      default:
        return {
          icon: Brain,
          text: 'In standby',
          color: 'text-slate-400',
          glow: 'shadow-none',
          accent: 'bg-slate-700/10',
          borderColor: 'border-slate-700/30',
          bg: 'bg-slate-700/5',
          label: 'Awaiting connection'
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <div className="flex flex-col items-center justify-center py-8">
      {/* Central Neural Hub */}
      <div className="relative group">
        {/* Animated Rings (Wow Factor) */}
        <AnimatePresence>
          {status === 'connected' && !isMuted && (
            <>
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1.4, opacity: [0.1, 0.3, 0.1] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                className="absolute inset-0 rounded-full bg-cyan-500/20 blur-xl"
              />
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1.8, opacity: [0.05, 0.15, 0.05] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                className="absolute inset-0 rounded-full bg-indigo-500/10 blur-2xl"
              />
            </>
          )}
        </AnimatePresence>

        {/* Main Indicator Circle */}
        <motion.div
          animate={{
            scale: status === 'connecting' ? [1, 1.05, 1] : 1,
          }}
          transition={{ duration: 2, repeat: Infinity }}
          className={`
            relative z-10 w-28 h-28 rounded-full 
            flex items-center justify-center
            border-2 ${config.borderColor} ${config.bg} ${config.glow}
            transition-all duration-500
          `}
        >
          <Icon 
            className={`w-12 h-12 ${config.color} transition-colors duration-500`} 
          />
        </motion.div>

        {/* Status Data Tag */}
        <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 z-20">
          <div className="px-3 py-1 rounded-full glass border border-white/10 text-[10px] font-bold tracking-widest uppercase text-white/70">
            {status}
          </div>
        </div>
      </div>

      {/* Labeling Section */}
      <div className="mt-8 text-center space-y-1">
        <motion.h2 
          key={config.text}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className={`text-xl font-bold tracking-tight ${config.color}`}
        >
          {config.text}
        </motion.h2>
        <p className="text-slate-500 text-sm font-medium italic">
          {config.label}
        </p>
      </div>
    </div>
  );
}
