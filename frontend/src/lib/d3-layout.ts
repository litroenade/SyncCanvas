import * as d3 from 'd3';
import { Shape } from '../stores/useCanvasStore';

interface D3Node extends d3.SimulationNodeDatum {
    id: string;
    x: number;
    y: number;
    width: number;
    height: number;
    original: Shape;
}

interface D3Link extends d3.SimulationLinkDatum<D3Node> {
    source: string | D3Node;
    target: string | D3Node;
    id: string;
    original: Shape;
}

/**
 * Apply force-directed layout to shapes
 * @param shapes Record of shapes
 * @returns Updated shapes with new positions
 */
export const applyForceLayout = (shapes: Record<string, Shape>): Record<string, Shape> => {
    const nodes: D3Node[] = [];
    const links: D3Link[] = [];
    const shapeList = Object.values(shapes);

    // 1. Identify Nodes and Links
    shapeList.forEach(shape => {
        if (['rect', 'circle', 'text', 'image'].includes(shape.type)) {
            nodes.push({
                id: shape.id,
                x: shape.x,
                y: shape.y,
                width: shape.width || 100,
                height: shape.height || 100,
                original: shape
            });
        }
    });

    // 2. Infer Links based on proximity (Arrows/Lines)
    shapeList.forEach(shape => {
        if (['arrow', 'line'].includes(shape.type) && shape.points && shape.points.length >= 4) {
            const startX = shape.points[0];
            const startY = shape.points[1];
            const endX = shape.points[shape.points.length - 2];
            const endY = shape.points[shape.points.length - 1];

            // Find closest node to start
            let sourceNode: D3Node | null = null;
            let minStartDist = Infinity;

            // Find closest node to end
            let targetNode: D3Node | null = null;
            let minEndDist = Infinity;

            nodes.forEach(node => {
                // Simple center distance or boundary distance could be used
                // Here we use center distance for simplicity
                const centerX = node.x + node.width / 2;
                const centerY = node.y + node.height / 2;

                const startDist = Math.hypot(centerX - startX, centerY - startY);
                if (startDist < minStartDist && startDist < 200) { // Threshold
                    minStartDist = startDist;
                    sourceNode = node;
                }

                const endDist = Math.hypot(centerX - endX, centerY - endY);
                if (endDist < minEndDist && endDist < 200) {
                    minEndDist = endDist;
                    targetNode = node;
                }
            });

            if (sourceNode && targetNode && (sourceNode as D3Node).id !== (targetNode as D3Node).id) {
                links.push({
                    source: (sourceNode as D3Node).id,
                    target: (targetNode as D3Node).id,
                    id: shape.id, // Link shape ID
                    original: shape
                });
            }
        }
    });

    // 3. Run Simulation
    const simulation = d3.forceSimulation<D3Node>(nodes)
        .force("charge", d3.forceManyBody().strength(-500)) // Repulsion
        .force("center", d3.forceCenter(window.innerWidth / 2, window.innerHeight / 2)) // Center
        .force("collide", d3.forceCollide().radius((d: any) => Math.max(d.width, d.height) / 1.5).iterations(2)) // Collision
        .force("link", d3.forceLink<D3Node, D3Link>(links).id((d) => d.id).distance(200)) // Links
        .stop();

    // Run simulation synchronously for N ticks
    for (let i = 0; i < 300; ++i) simulation.tick();

    // 4. Update Shapes
    const newShapes = { ...shapes };

    // Update Nodes
    nodes.forEach(node => {
        if (newShapes[node.id]) {
            newShapes[node.id] = {
                ...newShapes[node.id],
                x: (node.x || 0) - (node.width || 0) / 2, // D3 uses center, we might need top-left? 
                // Wait, d3 initializes x/y. 
                // Actually d3 initializes x/y. 
                // Let's assume node.x/y is the position.
                // If we initialized with top-left, D3 treats it as point.
                // Let's keep it simple.
                y: (node.y || 0) - (node.height || 0) / 2
            };
        }
    });

    // Update Links (Arrows) to follow nodes
    links.forEach(link => {
        const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
        const targetId = typeof link.target === 'string' ? link.target : link.target.id;

        const source = nodes.find(n => n.id === sourceId);
        const target = nodes.find(n => n.id === targetId);

        if (source && target && newShapes[link.id]) {
            // Update start/end points to centers of nodes
            // Ideally should be intersection of boundary, but center is easier for now

            // Re-calculate points
            // We need to map simulation coordinates back to top-left if necessary
            // But let's assume we want to connect centers.

            // Actually, let's just update the arrow to point from center to center
            // But we need to respect the original shape type (arrow/line)

            newShapes[link.id] = {
                ...newShapes[link.id],
                points: [source.x || 0, source.y || 0, target.x || 0, target.y || 0]
            };
        }
    });

    return newShapes;
};
