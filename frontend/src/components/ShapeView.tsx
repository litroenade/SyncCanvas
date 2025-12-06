import React from 'react';
import { Rect, Ellipse, Line, Text, Arrow, Image as KonvaImage } from 'react-konva';
import useImage from 'use-image';
import { Shape, ToolType } from '../stores/useCanvasStore';

// URLImage sub-component for Image shape
const URLImage = ({ src, ...props }: any) => {
    const [image] = useImage(src);
    return <KonvaImage image={image} {...props} />;
};

interface ShapeViewProps {
    shape: Shape;
    isSelected?: boolean;
    isGuest?: boolean;
    currentTool?: ToolType;
    isPreview?: boolean; // If true, renders as a temporary drawing shape (no interactions, lower opacity)

    // Event Handlers
    onShapeClick?: (id: string, e: any) => void;
    onDragStart?: (id: string) => void;
    onDragMove?: (id: string, e: any) => void;
    onDragEnd?: (id: string, e: any) => void;
    onTextDblClick?: (id: string, text: string) => void;
    shapeRef?: (node: any) => void;
}

export const ShapeView: React.FC<ShapeViewProps> = ({
    shape,
    isGuest = false,
    currentTool = 'select',
    isPreview = false,
    onShapeClick,
    onDragStart,
    onDragMove,
    onDragEnd,
    onTextDblClick,
    shapeRef
}) => {

    // Base props shared by all shapes
    const commonProps: any = {
        id: shape.id,
        x: shape.x,
        y: shape.y,
        rotation: shape.rotation || 0,
        opacity: isPreview ? 0.8 : (shape.opacity ?? 1),
        stroke: shape.strokeColor || '#1e1e1e',
        strokeWidth: shape.strokeWidth || 2,
    };

    // If it's a preview shape, it shouldn't listen to events
    if (isPreview) {
        commonProps.listening = false;
    } else {
        // Interactive props
        commonProps.ref = (node: any) => {
            if (shapeRef) shapeRef(node);
        };
        commonProps.draggable = !isGuest && currentTool === 'select';
        commonProps.onClick = (e: any) => onShapeClick?.(shape.id, e);
        commonProps.onTap = (e: any) => onShapeClick?.(shape.id, e);
        commonProps.onDragStart = () => onDragStart?.(shape.id);
        commonProps.onDragMove = (e: any) => onDragMove?.(shape.id, e);
        commonProps.onDragEnd = (e: any) => onDragEnd?.(shape.id, e);
    }

    // Individual Shape Rendering
    switch (shape.type) {
        case 'rect':
            return (
                <Rect
                    {...commonProps}
                    width={shape.width}
                    height={shape.height}
                    fill={shape.fill}
                    cornerRadius={shape.cornerRadius || 0}
                />
            );

        case 'circle':
            // Ellipse x,y is center, shape.x,y is top-left
            const w = shape.width || 100;
            const h = shape.height || 100;
            return (
                <Ellipse
                    {...commonProps}
                    x={shape.x + w / 2}
                    y={shape.y + h / 2}
                    radiusX={w / 2}
                    radiusY={h / 2}
                    fill={shape.fill}
                />
            );

        case 'diamond':
            const dw = shape.width || 100;
            const dh = shape.height || 100;
            return (
                <Line
                    {...commonProps}
                    points={[dw / 2, 0, dw, dh / 2, dw / 2, dh, 0, dh / 2]}
                    closed
                    fill={shape.fill}
                />
            );

        case 'text':
            return (
                <Text
                    {...commonProps}
                    text={shape.text}
                    fontSize={24}
                    fill={shape.fill || shape.strokeColor}
                    onDblClick={() => !isPreview && onTextDblClick?.(shape.id, shape.text || '')}
                    onDblTap={() => !isPreview && onTextDblClick?.(shape.id, shape.text || '')}
                />
            );

        case 'arrow':
            // Arrow/Line/Freedraw use absolute points, so we override x/y to 0
            // We must exclude x/y from commonProps to avoid JSX duplicate attribute error
            const { x: _x1, y: _y1, ...arrowProps } = commonProps;
            return (
                <Arrow
                    {...arrowProps}
                    x={0}
                    y={0}
                    points={shape.points || [0, 0, 0, 0]}
                    pointerLength={12}
                    pointerWidth={12}
                    fill={shape.strokeColor || '#1e1e1e'}
                />
            );

        case 'line':
            const { x: _x2, y: _y2, ...lineProps } = commonProps;
            return (
                <Line
                    {...lineProps}
                    x={0}
                    y={0}
                    points={shape.points || [0, 0, 0, 0]}
                />
            );

        case 'freedraw':
            const { x: _x3, y: _y3, ...freedrawProps } = commonProps;
            return (
                <Line
                    {...freedrawProps}
                    x={0}
                    y={0}
                    points={shape.points || []}
                    tension={0.5}
                    lineCap="round"
                    lineJoin="round"
                    globalCompositeOperation="source-over"
                />
            );

        case 'image':
            if (!shape.imageUrl) return null;
            return (
                <URLImage
                    {...commonProps}
                    src={shape.imageUrl}
                    width={shape.width}
                    height={shape.height}
                />
            );

        default:
            return null;
    }
};
