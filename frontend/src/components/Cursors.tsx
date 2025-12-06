import React from 'react';
import { useCanvasStore } from '../stores/useCanvasStore';

interface CursorProps {
    x: number;
    y: number;
    color: string;
    name: string;
    showName: boolean;
}

const Cursor: React.FC<CursorProps> = ({ x, y, color, name, showName }) => {
    return (
        <div
            className="absolute pointer-events-none z-50 transition-all duration-100 ease-linear"
            style={{
                left: x,
                top: y,
                transform: 'translate(-50%, -50%)'
            }}
        >
            <svg width="24" height="36" viewBox="0 0 24 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5.65376 12.3673H5.46026L5.31717 12.4976L0.500002 16.8829L0.500002 1.19841L11.7841 12.3673H5.65376Z" fill={color} stroke="white" />
            </svg>
            {showName && (
                <div
                    className="absolute left-4 top-4 px-2 py-1 rounded text-xs font-medium text-white whitespace-nowrap shadow-sm"
                    style={{ backgroundColor: color }}
                >
                    {name}
                </div>
            )}
        </div>
    );
};

export const Cursors: React.FC<{ cursors: Record<string, any> }> = ({ cursors }) => {
    const { showCursorNames } = useCanvasStore();

    return (
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
            {Object.entries(cursors).map(([clientId, cursor]) => (
                <Cursor
                    key={clientId}
                    x={cursor.x}
                    y={cursor.y}
                    color={cursor.color}
                    name={cursor.name}
                    showName={showCursorNames}
                />
            ))}
        </div>
    );
};

