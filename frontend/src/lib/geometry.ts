import { Shape } from '../stores/useCanvasStore';

export const isShapeIntersecting = (shape: Shape, p1: { x: number, y: number }, p2: { x: number, y: number }, threshold = 5): boolean => {
    // 简单的矩形包围盒检测 MVP
    // 更精确的检测可以使用线段与图形的相交算法
    const minX = Math.min(p1.x, p2.x) - threshold;
    const maxX = Math.max(p1.x, p2.x) + threshold;
    const minY = Math.min(p1.y, p2.y) - threshold;
    const maxY = Math.max(p1.y, p2.y) + threshold;

    const shapeX = shape.x;
    const shapeY = shape.y;
    const shapeW = shape.width || 0;
    const shapeH = shape.height || 0;

    // 对于 rect, image, text 等 Simple Bounding Box
    if (shape.type !== 'freedraw' && shape.type !== 'line' && shape.type !== 'arrow') {
        return !(shapeX + shapeW < minX || shapeX > maxX || shapeY + shapeH < minY || shapeY > maxY);
    }

    // 对于 freedraw, line, arrow，需要更细致的检测
    // 这里简化为：先检测包围盒，如果相交，再认为相交 (优化空间：检测具体点)
    if (shape.type === 'freedraw') {
        // 计算 freedraw 的 bounding box
        const points = shape.points || [];
        if (points.length < 2) return false;
        let fxMin = points[0], fxMax = points[0], fyMin = points[1], fyMax = points[1];
        for (let i = 0; i < points.length; i += 2) {
            fxMin = Math.min(fxMin, points[i]);
            fxMax = Math.max(fxMax, points[i]);
            fyMin = Math.min(fyMin, points[i + 1]);
            fyMax = Math.max(fyMax, points[i + 1]);
        }
        // 加上线宽造成的扩展
        const stroke = (shape.strokeWidth || 2) / 2;
        fxMin -= stroke; fxMax += stroke; fyMin -= stroke; fyMax += stroke;

        return !(fxMax < minX || fxMin > maxX || fyMax < minY || fyMin > maxY);
    }

    // Line / Arrow 类似
    if (shape.type === 'line' || shape.type === 'arrow') {
        const points = shape.points || [];
        if (points.length < 4) return false;
        // 简化处理：使用首尾点的 bounding box (不准确，应该计算所有点)
        return !(Math.max(points[0], points[2]) < minX || Math.min(points[0], points[2]) > maxX ||
            Math.max(points[1], points[3]) < minY || Math.min(points[1], points[3]) > maxY);
    }

    return false;
};

/**
 * 获取鼠标在画布世界坐标系中的位置
 * @param stage - Konva Stage 实例
 * @returns 世界坐标点 {x, y} 或 null
 */
export const getWorldPos = (stage: any): { x: number; y: number } | null => {
    const pointer = stage.getPointerPosition();
    if (!pointer) return null;
    const transform = stage.getAbsoluteTransform().copy();
    transform.invert();
    return transform.point(pointer);
};
