import React, { useEffect, useState } from 'react';
import { yjsManager } from '../lib/yjs';
import { Users } from 'lucide-react';

/**
 * 预设的协作者颜色列表
 * 第一个用户使用深色，后续用户使用彩色
 */
const COLLABORATOR_COLORS = [
    '#1e1e1e', // 第一个用户：黑色
    '#ef4444', // 红色
    '#f97316', // 橙色
    '#10b981', // 绿色
    '#3b82f6', // 蓝色
    '#8b5cf6', // 紫色
    '#f43f5e', // 粉色
    '#06b6d4', // 青色
];

interface Collaborator {
    clientId: number;
    name: string;
    color: string;
}

/**
 * 协作者列表组件
 * 
 * 显示当前房间内的在线用户数量和头像列表
 */
export const CollaboratorList: React.FC = () => {
    const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
    const [myClientId, setMyClientId] = useState<number | null>(null);

    useEffect(() => {
        const updateCollaborators = () => {
            const awareness = yjsManager.getAwareness();
            if (!awareness) return;

            setMyClientId(awareness.clientID);
            const states = awareness.getStates();
            const users: Collaborator[] = [];
            let colorIndex = 0;

            states.forEach((state: any, clientId: number) => {
                if (state.user) {
                    users.push({
                        clientId,
                        name: state.user.name || 'Unknown',
                        color: COLLABORATOR_COLORS[colorIndex % COLLABORATOR_COLORS.length],
                    });
                    colorIndex++;
                }
            });

            setCollaborators(users);
        };

        // 初始更新
        const checkAndUpdate = () => {
            const awareness = yjsManager.getAwareness();
            if (awareness) {
                updateCollaborators();
                awareness.on('change', updateCollaborators);
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
                awareness.off('change', updateCollaborators);
            }
        };
    }, []);

    const onlineCount = collaborators.length;
    const maxDisplay = 4;
    const displayUsers = collaborators.slice(0, maxDisplay);
    const extraCount = Math.max(0, onlineCount - maxDisplay);

    if (onlineCount === 0) return null;

    return (
        <div className="fixed top-4 right-20 z-50 flex items-center gap-2 bg-white/90 backdrop-blur-md rounded-full px-3 py-1.5 shadow-sm border border-slate-200/60">
            <Users size={14} className="text-slate-500" />
            <div className="flex items-center -space-x-2">
                {displayUsers.map((user, index) => (
                    <div
                        key={user.clientId}
                        className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium text-white border-2 border-white relative"
                        style={{ backgroundColor: user.color, zIndex: maxDisplay - index }}
                        title={user.name + (user.clientId === myClientId ? ' (你)' : '')}
                    >
                        {user.name.charAt(0).toUpperCase()}
                    </div>
                ))}
                {extraCount > 0 && (
                    <div
                        className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium text-slate-600 bg-slate-200 border-2 border-white"
                        style={{ zIndex: 0 }}
                    >
                        +{extraCount}
                    </div>
                )}
            </div>
            <span className="text-xs text-slate-600 font-medium ml-1">
                {onlineCount}
            </span>
        </div>
    );
};
