import React, { useRef, useEffect, useState, useCallback } from 'react';
import html2canvas from 'html2canvas';

type RouteStyle = 'horiz' | 'vert' | 'bottom-bus' | 'top-bus';

interface Conn {
  from: string;
  to: string;
  color?: string;
  dashed?: boolean;
  label?: string;
  route?: RouteStyle;
  fromXOffset?: number;  // px offset on the exit x-point, used to spread parallel lines
}

interface Line {
  id: string;
  path: string;
  color: string;
  dashed: boolean;
  label?: string;
  lx?: number;
  ly?: number;
}

const CONNS: Conn[] = [
  { from: 'candidate', to: 'api',     color: '#374151', route: 'horiz', label: 'Request flow' },
  { from: 'recruiter', to: 'api',     color: '#374151', route: 'horiz', label: 'Request flow' },
  { from: 'api',       to: 'backend', color: '#374151', route: 'horiz' },
  { from: 'backend',   to: 'kg',      color: '#5b21b6', route: 'horiz', label: 'Graph / ML' },
  { from: 'backend',   to: 'llm',     color: '#be185d', route: 'horiz', label: 'LLM' },
  { from: 'kg',        to: 'embed',   color: '#5b21b6', dashed: true, label: 'similarity', route: 'vert' },
  { from: 'recruiter', to: 'kg',      color: '#dc2626', dashed: true, label: 'feedback loop', route: 'top-bus' },
  { from: 'backend',   to: 'db',      color: '#374151', route: 'vert', fromXOffset: -22, label: 'Request flow' },
  { from: 'backend',   to: 'latex',   color: '#92400e', route: 'vert', fromXOffset:  22, label: 'PDF generation' },
];

const ALL_COLORS = CONNS.map(c => c.color || '#374151').filter((v, i, a) => a.indexOf(v) === i);

function makePath(
  from: HTMLElement,
  to: HTMLElement,
  cr: DOMRect,
  style: RouteStyle,
  fromXOffset: number = 0,
): { path: string; lx: number; ly: number } {
  const fr = from.getBoundingClientRect();
  const tr = to.getBoundingClientRect();

  const fL  = fr.left   - cr.left;
  const fR  = fr.right  - cr.left;
  const fT  = fr.top    - cr.top;
  const fB  = fr.bottom - cr.top;
  const fCx = fL + fr.width  / 2;
  const fCy = fT + fr.height / 2;

  const tL  = tr.left   - cr.left;
  const tT  = tr.top    - cr.top;
  const tB  = tr.bottom - cr.top;
  const tCx = tL + tr.width  / 2;
  const tCy = tT + tr.height / 2;

  if (style === 'vert') {
    const sx = fCx + fromXOffset;
    const sy = fB;
    const tx = tCx;
    const ty = tT;
    // drop straight down to a bus level that's 80% of the way to the target (well below all boxes in between)
    // then go horizontal, then drop into target
    const midY = sy + (ty - sy) * 0.80;
    const labelY = midY - 10;  // label sits just above the horizontal bus segment
    return { path: `M${sx} ${sy} V${midY} H${tx} V${ty}`, lx: (sx + tx) / 2, ly: labelY };
  }

  if (style === 'bottom-bus') {
    const busY = cr.height - 14;
    const sx   = fCx;
    const sy   = fB;
    const tx   = tCx;
    const ty   = tB;
    return {
      path: `M${sx} ${sy} V${busY} H${tx} V${ty}`,
      lx: (sx + tx) / 2,
      ly: busY,
    };
  }

  if (style === 'top-bus') {
    // Route above all content: API and Backend are single-item centered boxes
    // so their tops are lower than the first boxes in multi-item columns.
    // busY sits 18px above the topmost of the two endpoints, clearing all boxes in between.
    const busY = Math.min(fT, tT) - 18;
    const sx   = fCx;
    const sy   = fT;
    const tx   = tCx;
    const ty   = tT;
    return {
      path: `M${sx} ${sy} V${busY} H${tx} V${ty}`,
      lx: (sx + tx) / 2,
      ly: busY,
    };
  }

  // horiz: strict orthogonal elbow through divider gap
  const sx   = fR;
  const sy   = fCy;
  const tx   = tL;
  const ty   = tCy;
  const midX = (sx + tx) / 2;
  return {
    path: `M${sx} ${sy} H${midX} V${ty} H${tx}`,
    lx: midX,
    ly: (sy + ty) / 2,  // centered on the vertical run in the divider gap
  };
}

interface NodeProps {
  id: string;
  title: string;
  sub?: string;
  accent?: string;
  reg: (id: string, el: HTMLDivElement | null) => void;
}

const Node: React.FC<NodeProps> = ({ id, title, sub, accent = '#374151', reg }) => (
  <div
    ref={el => reg(id, el)}
    style={{
      borderTop: `2px solid ${accent}`,
      borderRight: `1px solid ${accent}33`,
      borderBottom: `1px solid ${accent}33`,
      borderLeft: `4px solid ${accent}`,
      borderRadius: 4,
      padding: 'clamp(10px, 1.8vh, 20px) clamp(10px, 1.4vw, 18px)',
      background: '#ffffff',
      marginBottom: 'clamp(24px, 4.2vh, 48px)',
    }}
  >
    <div style={{
      fontSize: 'clamp(0.82rem, 1.3vw, 1.1rem)',
      fontWeight: 700,
      color: accent,
      letterSpacing: '0.01em',
      marginBottom: sub ? 'clamp(5px, 0.8vh, 9px)' : 0,
    }}>
      {title}
    </div>
    {sub && (
      <div style={{
        fontSize: 'clamp(0.68rem, 0.95vw, 0.85rem)',
        color: '#6b7280',
        lineHeight: 1.65,
      }}>
        {sub}
      </div>
    )}
  </div>
);

interface ColProps {
  label: string;
  color: string;
  children: React.ReactNode;
  flex?: number;
}

const Col: React.FC<ColProps> = ({ label, color, children, flex = 1 }) => (
  <div style={{ flex, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
    <div style={{
      fontSize: 'clamp(0.52rem, 0.78vw, 0.7rem)',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.14em',
      color,
      borderBottom: `2px solid ${color}45`,
      paddingBottom: 'clamp(4px, 0.6vh, 7px)',
      marginBottom: 'clamp(10px, 1.5vh, 16px)',
      textAlign: 'center',
    }}>
      {label}
    </div>
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      {children}
    </div>
  </div>
);

const Divider: React.FC = () => (
  <div style={{ width: 1, background: '#e5e7eb', margin: '0 clamp(16px, 2.2vw, 32px)', flexShrink: 0 }} />
);

const ArchitectureDiagram: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const nodeMap = useRef<Map<string, HTMLDivElement>>(new Map());
  const [lines, setLines] = useState<Line[]>([]);

  const reg = useCallback((id: string, el: HTMLDivElement | null) => {
    if (el) nodeMap.current.set(id, el);
    else nodeMap.current.delete(id);
  }, []);

  const recalc = useCallback(() => {
    if (!containerRef.current) return;
    const cr = containerRef.current.getBoundingClientRect();
    const result: Line[] = [];
    CONNS.forEach((c, i) => {
      const f = nodeMap.current.get(c.from);
      const t = nodeMap.current.get(c.to);
      if (!f || !t) return;
      const { path, lx, ly } = makePath(f, t, cr, c.route ?? 'horiz', c.fromXOffset ?? 0);
      result.push({
        id: `l${i}`, path,
        color: c.color ?? '#374151',
        dashed: c.dashed ?? false,
        label: c.label,
        lx, ly,
      });
    });
    setLines(result);
  }, []);

  useEffect(() => {
    const id = requestAnimationFrame(recalc);
    const obs = new ResizeObserver(() => requestAnimationFrame(recalc));
    if (containerRef.current) obs.observe(containerRef.current);
    return () => { cancelAnimationFrame(id); obs.disconnect(); };
  }, [recalc]);

  const exportPng = useCallback(async () => {
    if (!containerRef.current) return;
    const canvas = await html2canvas(containerRef.current, {
      backgroundColor: '#ffffff',
      scale: 3,
      useCORS: true,
      logging: false,
    });
    const link = document.createElement('a');
    link.download = 'hire-lens-architecture.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, []);

  return (
    <div style={{
      background: '#f3f4f6',
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'clamp(6px, 1vw, 14px)',
      fontFamily: "'Sora', 'Inter', sans-serif",
      boxSizing: 'border-box',
      gap: 10,
    }}>
      <div style={{ alignSelf: 'flex-end', marginRight: 4 }}>
        <button
          onClick={exportPng}
          style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '7px 16px',
            background: '#111827',
            color: '#ffffff',
            border: 'none',
            borderRadius: 5,
            fontSize: 'clamp(0.7rem, 1vw, 0.85rem)',
            fontWeight: 700,
            fontFamily: "'Sora', sans-serif",
            letterSpacing: '0.02em',
            cursor: 'pointer',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Export PNG
        </button>
      </div>
      <div
        ref={containerRef}
        style={{
          width: 'min(97vw, calc(96vh * 16 / 9))',
          aspectRatio: '16 / 9',
          background: '#ffffff',
          border: '1px solid #9ca3af',
          borderRadius: 6,
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          overflow: 'hidden',
          boxShadow: '0 2px 20px rgba(0,0,0,0.10)',
        }}
      >
        {/* SVG overlay for lines — z-index 1 so node boxes render on top */}
        <svg style={{
          position: 'absolute', top: 0, left: 0,
          width: '100%', height: '100%',
          pointerEvents: 'none', zIndex: 1,
        }}>
          <defs>
            {ALL_COLORS.map(c => (
              <marker key={c} id={`a-${c.replace('#', '')}`}
                markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                <path d="M0 0 L7 3.5 L0 7 Z" fill={c} opacity="0.85" />
              </marker>
            ))}
          </defs>
          {lines.map(l => (
            <path key={l.id} d={l.path} stroke={l.color} strokeWidth="1.6" fill="none"
              opacity="0.7" strokeDasharray={l.dashed ? '7 4' : undefined}
              strokeLinejoin="round"
              markerEnd={`url(#a-${l.color.replace('#', '')})`} />
          ))}
        </svg>

        {/* SVG overlay for labels — z-index 3 so labels appear above everything */}
        <svg style={{
          position: 'absolute', top: 0, left: 0,
          width: '100%', height: '100%',
          pointerEvents: 'none', zIndex: 3,
        }}>
          {lines.map(l => l.label && l.lx !== undefined && l.ly !== undefined && (
            <g key={`${l.id}-label`}>
              <rect x={l.lx - l.label.length * 3.5} y={l.ly - 9} width={l.label.length * 7} height={13}
                fill="#ffffff" opacity="0.92" rx="2" />
              <text x={l.lx} y={l.ly} textAnchor="middle" dominantBaseline="middle"
                style={{ fontSize: 'clamp(8px, 0.9vw, 11px)' }}
                fill={l.color} opacity="1"
                fontFamily="'Sora', sans-serif" fontStyle="italic" fontWeight="600">
                {l.label}
              </text>
            </g>
          ))}
        </svg>

        {/* Body */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          zIndex: 2,
          position: 'relative',
        }}>
          {/* Main columns */}
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'row',
            padding: 'clamp(10px, 1.8vh, 20px) clamp(14px, 2vw, 28px)',
            paddingBottom: 'clamp(6px, 1vh, 10px)',
            overflow: 'hidden',
          }}>
            <Col label="Client" color="#2563eb" flex={1}>
              <Node id="recruiter" title="Recruiter Portal"
                sub="Job Posting · Application Review · Candidate Shortlisting · AI Interview Question Generation"
                accent="#0891b2" reg={reg} />
              <Node id="candidate" title="Candidate Portal"
                sub="Profile Management · Resume Generation · Job Discovery · Learning Resources · Practice Prep"
                accent="#2563eb" reg={reg} />
            </Col>

            <Divider />

            <Col label="API Gateway" color="#374151" flex={0.9}>
              <Node id="api" title="Django REST Framework"
                sub="JWT Authentication · Role-based Authorization · Stateless API · Token Lifecycle Management"
                accent="#374151" reg={reg} />
            </Col>

            <Divider />

            <Col label="Backend" color="#6366f1" flex={1}>
              <Node id="backend" title="Django Applications"
                sub="User & Auth · Candidate Profiles · Recruiter Workflow · Resume Engine · AI Orchestration"
                accent="#6366f1" reg={reg} />
            </Col>

            <Divider />

            <Col label="Intelligence" color="#5b21b6" flex={1.3}>
              <Node id="kg" title="Knowledge Graph"
                sub="Candidate-Skill-Domain mapping · Weighted competency edges · Partial-credit match scoring"
                accent="#5b21b6" reg={reg} />
              <Node id="embed" title="Sentence Embeddings"
                sub="Dense vector encoding · Cosine similarity ranking · Semantic skill-to-JD alignment"
                accent="#5b21b6" reg={reg} />
              <Node id="llm" title="LLM Service"
                sub="Multi-model Gemini cascade · JD structured extraction · Resume content synthesis · Match reasoning"
                accent="#be185d" reg={reg} />
            </Col>
          </div>

          {/* Infrastructure row — pinned at the bottom, full width */}
          <div style={{
            borderTop: '1.5px solid #e5e7eb',
            padding: 'clamp(8px, 1.2vh, 14px) clamp(14px, 2vw, 28px)',
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            gap: 'clamp(10px, 1.5vw, 18px)',
            flexShrink: 0,
          }}>
            <span style={{
              fontSize: 'clamp(0.52rem, 0.78vw, 0.7rem)',
              fontWeight: 700,
              textTransform: 'uppercase' as const,
              letterSpacing: '0.14em',
              color: '#374151',
              flexShrink: 0,
              paddingRight: 'clamp(8px, 1vw, 14px)',
              borderRight: '2px solid #37415135',
            }}>Infrastructure</span>
            <div style={{ flex: 1 }}>
              <Node id="db" title="Persistent Storage"
                sub="User profiles · Job listings · Applications · Match scores · LLM usage logs"
                accent="#374151" reg={reg} />
            </div>
            <div style={{ flex: 1 }}>
              <Node id="latex" title="Resume PDF Engine"
                sub="LaTeX template rendering · Structured PDF generation"
                accent="#92400e" reg={reg} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ArchitectureDiagram;
