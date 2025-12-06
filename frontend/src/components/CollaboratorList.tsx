import React, { useEffect, useState } from 'react';
import { yjsManager } from '../lib/yjs';
import { Users } from 'lucide-react';

/**
 * 协作者列表组件
 * 
 * 显示当前房间内的在线用户数量
 */
export const CollaboratorList: React.FC = () => {
    const [onlineCount, setOnlineCount] = useState(0);

    useEffect(() => {
        const updateCount = () => {
            const awareness = yjsManager.getAwareness();
            if (!awareness) return;

            const states = awareness.getStates();
            let count = 0;
            states.forEach((state: any) => {
                if (state.user) count++;
            });
            setOnlineCount(count);
        };

        // 初始更新和轮询
        const checkAndUpdate = () => {
            const awareness = yjsManager.getAwareness();
            if (awareness) {
                updateCount();
                awareness.on('change', updateCount);
            }
        };

        // 延迟检查（等待 Yjs 连接）
        const intervalId = setInterval(() => {
            const awareness = yjsManager.getAwareness();
            if (awareness) {
                clearInterval(intervalId);
                checkAndUpdate();
            }
        }, 500);

        return () => {
            clearInterval(intervalId);
            const awareness = yjsManager.getAwareness();
            if (awareness) {
                awareness.off('change', updateCount);
            }
        };
    }, []);

    if (onlineCount === 0) return null;

    return (
        <div className="fixed top-4 right-20 z-50 flex items-center gap-1.5 bg-white/90 backdrop-blur-md rounded-full px-3 py-1.5 shadow-sm border border-slate-200/60">
            <Users size={14} className="text-slate-500" />
            <span className="text-xs text-slate-600 font-medium">
                {onlineCount} 在线
            </span>
        </div>
    );
};

