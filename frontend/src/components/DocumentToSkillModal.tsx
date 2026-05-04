import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Upload, FileText, FileCode, AlertCircle, FileType } from 'lucide-react';

interface DocumentToSkillModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (description: string, files: File[]) => void;
}

export function DocumentToSkillModal({ isOpen, onClose, onCreate }: DocumentToSkillModalProps) {
  const [description, setDescription] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = () => {
    if (!description.trim()) {
      setError('Please enter a skill description');
      return;
    }
    setError(null);
    onCreate(description, files);
    onClose();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files).slice(0, 3));
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-slate-950/60 backdrop-blur-xl"
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative bg-[#1a1a1a] border border-white/5 rounded-[2rem] shadow-2xl w-full max-w-md overflow-hidden flex flex-col"
          >
            {/* Background Glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-48 bg-indigo-500/10 blur-[80px] -z-10 rounded-full" />

            {/* Content Container */}
            <div className="p-8 flex flex-col items-center">
              {/* Document Visuals */}
              <div className="relative w-40 h-32 mb-6 flex items-center justify-center">
                {/* Back Documents */}
                <div className="absolute w-24 h-32 bg-slate-800/40 border border-white/5 rounded-xl translate-x-[-15px] translate-y-[-5px] rotate-[-5deg]" />
                <div className="absolute w-24 h-32 bg-slate-800/60 border border-white/5 rounded-xl translate-x-[-5px] translate-y-[-2px] rotate-[-2deg]" />
                
                {/* Main Document */}
                <div className="relative w-24 h-32 bg-[#2a2a2a] border border-white/10 rounded-xl shadow-2xl flex flex-col p-3 overflow-hidden">
                   <div className="w-full h-1 bg-white/5 mb-2 rounded-full" />
                   <div className="w-4/5 h-1 bg-white/5 mb-2 rounded-full" />
                   <div className="w-3/5 h-1 bg-white/5 mb-4 rounded-full" />
                   
                   <div className="mt-auto flex justify-center">
                     <FileCode className="w-8 h-8 text-indigo-400 opacity-80" />
                   </div>
                   
                   {/* Bottom Detail */}
                   <div className="absolute bottom-2 left-2 right-2 h-4 bg-white/5 rounded-md" />
                </div>

                {/* Floating Elements */}
                <div className="absolute -right-2 top-2 w-10 h-10 bg-[#e53e3e] rounded-full shadow-lg flex items-center justify-center border-4 border-[#1a1a1a]">
                  <FileType className="w-5 h-5 text-white" />
                </div>
                
                <div className="absolute -left-6 bottom-4 w-8 h-8 bg-slate-800 border border-white/10 rounded-lg flex items-center justify-center shadow-lg">
                   <div className="w-4 h-4 border-2 border-slate-600 rounded-sm" />
                </div>

                <div className="absolute right-[-20px] bottom-8 w-8 h-8 bg-slate-800 border border-white/10 rounded-lg flex flex-col gap-1 p-2 shadow-lg">
                   <div className="w-full h-[2px] bg-indigo-500/50 rounded-full" />
                   <div className="w-full h-[2px] bg-indigo-500/50 rounded-full" />
                </div>
              </div>

              {/* Text Header */}
              <h3 className="text-xl font-bold text-white mb-2">Document to skills</h3>
              <p className="text-slate-400 text-sm text-center mb-8 px-4">
                Replicate styles easily by turning documents into skills.
              </p>

              {/* Drop Zone */}
              <div className="w-full relative group">
                <input 
                  type="file" 
                  multiple 
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                />
                <div className="w-full border-2 border-dashed border-white/10 rounded-2xl py-10 flex flex-col items-center justify-center bg-white/5 hover:bg-white/[0.07] transition-all group-hover:border-white/20">
                  <div className="p-3 bg-white/5 rounded-xl mb-4">
                    <Upload className="w-6 h-6 text-slate-400" />
                  </div>
                  <p className="text-sm font-medium text-slate-200 mb-1">
                    Drop files here or click to upload
                  </p>
                  <p className="text-xs text-slate-500 text-center px-6">
                    Docx, xlsx, pdf, pptx or their screenshots.<br />
                    Max 3 files, 100 MB each.
                  </p>
                </div>
              </div>

              {/* Description Input */}
              <div className="w-full mt-6 space-y-2">
                <label className="text-sm font-bold text-slate-300">Describe your skill</label>
                <div className={`relative rounded-xl transition-all ${error ? 'ring-1 ring-rose-500/50 border-rose-500/50' : 'border-white/5'}`}>
                  <textarea
                    value={description}
                    onChange={(e) => {
                      setDescription(e.target.value);
                      if (error) setError(null);
                    }}
                    placeholder="Replicate the style and layout of this document..."
                    className={`w-full bg-[#242424] border ${error ? 'border-rose-500/50' : 'border-white/5'} rounded-xl p-4 text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-all placeholder:text-slate-600 resize-none h-20`}
                  />
                </div>
                {error && (
                  <div className="flex items-center gap-2 text-rose-500 text-xs mt-1 animate-in fade-in slide-in-from-top-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{error}</span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="w-full mt-8 flex gap-3">
                <button
                  onClick={onClose}
                  className="flex-1 px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-sm transition-all active:scale-95"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  className={`flex-1 px-6 py-3 rounded-xl font-bold text-sm transition-all active:scale-95 ${
                    description.trim() 
                      ? 'bg-slate-800 text-white hover:bg-slate-700' 
                      : 'bg-slate-800/50 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  Create skill
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
