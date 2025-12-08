import React from 'react';
import { X, Sun, Moon } from 'lucide-react';
import { useThemeStore } from '../../stores/useThemeStore';
import { cn } from '../../lib/utils';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
    const { theme, setTheme } = useThemeStore();

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
            <div
                className={cn(
                    "rounded-2xl shadow-2xl w-96 p-6 relative animate-in zoom-in-95 duration-200 border",
                    theme === 'dark'
                        ? "bg-slate-900/90 border-slate-700 text-slate-100"
                        : "bg-white/90 border-white/20 text-slate-800"
                )}
                style={{ backdropFilter: 'blur(20px)' }}
            >
                <button
                    onClick={onClose}
                    className={cn(
                        "absolute top-4 right-4 transition-colors",
                        theme === 'dark' ? "text-slate-500 hover:text-slate-300" : "text-slate-400 hover:text-slate-600"
                    )}
                >
                    <X size={20} />
                </button>

                <h2 className="text-xl font-semibold mb-6">设置</h2>

                <div className="space-y-8">
                    {/* Theme Selection */}
                    <div className="space-y-3">
                        <label className={cn("text-sm font-medium", theme === 'dark' ? "text-slate-400" : "text-slate-500")}>
                            外观
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                onClick={() => setTheme('light')}
                                className={cn(
                                    "flex items-center justify-center gap-2 p-3 rounded-xl border transition-all",
                                    theme === 'light'
                                        ? "bg-blue-50 border-blue-200 text-blue-600 ring-1 ring-blue-500"
                                        : "border-transparent hover:bg-slate-100 text-slate-600 dark:hover:bg-slate-800 dark:text-slate-400"
                                )}
                            >
                                <Sun size={18} />
                                <span className="text-sm font-medium">亮色</span>
                            </button>
                            <button
                                onClick={() => setTheme('dark')}
                                className={cn(
                                    "flex items-center justify-center gap-2 p-3 rounded-xl border transition-all",
                                    theme === 'dark'
                                        ? "bg-blue-900/30 border-blue-800 text-blue-400 ring-1 ring-blue-500"
                                        : "border-transparent hover:bg-slate-100 text-slate-600 dark:hover:bg-slate-800 dark:text-slate-400"
                                )}
                            >
                                <Moon size={18} />
                                <span className="text-sm font-medium">暗色</span>
                            </button>
                        </div>
                    </div>

                    <div className={cn("pt-6 border-t", theme === 'dark' ? "border-slate-800" : "border-slate-100")}>
                        <p className={cn("text-xs text-center", theme === 'dark' ? "text-slate-600" : "text-slate-400")}>
                            SyncCanvas v0.2.0
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};
