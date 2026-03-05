import React, { useState, useEffect, useRef } from 'react';

export default function Mascot() {
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
    const svgRef = useRef(null);

    useEffect(() => {
        const handleMouseMove = (e) => {
            setMousePos({ x: e.clientX, y: e.clientY });
        };
        window.addEventListener('mousemove', handleMouseMove);
        return () => window.removeEventListener('mousemove', handleMouseMove);
    }, []);

    const getPupilOffset = (cx, cy) => {
        if (!svgRef.current) return { x: 0, y: 0 };
        const rect = svgRef.current.getBoundingClientRect();

        // Approximate the absolute pixel position of the eye center
        // The SVG is 200x200, so scale accordingly
        const scaleX = rect.width / 200;
        const scaleY = rect.height / 200;

        const absoluteCx = rect.left + cx * scaleX;
        const absoluteCy = rect.top + cy * scaleY;

        const dx = mousePos.x - absoluteCx;
        const dy = mousePos.y - absoluteCy;
        const dist = Math.sqrt(dx * dx + dy * dy);

        const maxOffset = 3; // Modest eye movement limits

        if (dist === 0) return { x: 0, y: 0 };
        return {
            x: (dx / dist) * Math.min(maxOffset, dist * 0.05),
            y: (dy / dist) * Math.min(maxOffset, dist * 0.05)
        };
    };

    const leftPupil = getPupilOffset(80, 85);
    const rightPupil = getPupilOffset(120, 85);

    return (
        <svg
            ref={svgRef}
            viewBox="0 0 200 200"
            width="180"
            height="180"
            style={{ dropShadow: '0 10px 15px rgba(0,0,0,0.5)' }}
            xmlns="http://www.w3.org/2000/svg"
        >
            <defs>
                <linearGradient id="skinGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f5d0b5" />
                    <stop offset="100%" stopColor="#d2a679" />
                </linearGradient>
            </defs>

            {/* Neck */}
            <rect x="85" y="125" width="30" height="40" fill="#d2a679" />

            {/* Shoulders (Mas alto para menos cuello) */}
            <path d="M 25 200 Q 100 110 175 200 Z" fill="#90caf9" />

            {/* Rosario (Collar de cuentas y Cruz) */}
            <path d="M 75 130 Q 100 180 125 130" fill="none" stroke="#5D4037" strokeWidth="2.5" strokeDasharray="3 3" />
            <g transform="translate(100, 163)">
                <line x1="0" y1="0" x2="0" y2="16" stroke="#FFC107" strokeWidth="3" strokeLinecap="round" />
                <line x1="-5" y1="5" x2="5" y2="5" stroke="#FFC107" strokeWidth="3" strokeLinecap="round" />
            </g>

            {/* Head Silhouette */}
            <ellipse cx="100" cy="90" rx="45" ry="55" fill="url(#skinGrad)" />

            {/* Ears */}
            <ellipse cx="53" cy="95" rx="5" ry="12" fill="#d2a679" />
            <ellipse cx="147" cy="95" rx="5" ry="12" fill="#d2a679" />

            {/* Headphones (Band) */}
            <path d="M 45 95 C 45 20, 155 20, 155 95" fill="none" stroke="#212121" strokeWidth="8" strokeLinecap="round" />

            {/* Headphones (Earpieces) */}
            <rect x="40" y="75" width="12" height="40" rx="6" fill="#111" />
            <rect x="148" y="75" width="12" height="40" rx="6" fill="#111" />

            {/* Eyebrows */}
            <path d="M 68 72 Q 80 68 88 72" fill="none" stroke="#6d4c41" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M 132 72 Q 120 68 112 72" fill="none" stroke="#6d4c41" strokeWidth="2.5" strokeLinecap="round" />

            {/* Eyes (Whites) */}
            <ellipse cx="80" cy="85" rx="8" ry="5" fill="#FFF" />
            <ellipse cx="120" cy="85" rx="8" ry="5" fill="#FFF" />

            {/* Pupils */}
            <circle cx={80 + leftPupil.x} cy={85 + leftPupil.y} r="2.5" fill="#3e2723" />
            <circle cx={120 + rightPupil.x} cy={85 + rightPupil.y} r="2.5" fill="#3e2723" />

            {/* Glasses (Frames) */}
            <rect x="65" y="78" width="30" height="14" rx="3" fill="none" stroke="#607d8b" strokeWidth="1.5" />
            <rect x="105" y="78" width="30" height="14" rx="3" fill="none" stroke="#607d8b" strokeWidth="1.5" />
            <line x1="95" y1="83" x2="105" y2="83" stroke="#607d8b" strokeWidth="1.5" />
            <line x1="53" y1="83" x2="65" y2="83" stroke="#607d8b" strokeWidth="1.5" />
            <line x1="135" y1="83" x2="147" y2="83" stroke="#607d8b" strokeWidth="1.5" />

            {/* KN95 Mask */}
            <path d="M 60 105 L 100 90 L 140 105 L 125 145 L 75 145 Z" fill="#F8F9FA" stroke="#CFD8DC" strokeWidth="1" />

            {/* Mask Detail Lines (Center fold) */}
            <line x1="100" y1="90" x2="100" y2="145" stroke="#CFD8DC" strokeWidth="1.5" />
            <path d="M 60 105 Q 80 115 100 115 Q 120 115 140 105" fill="none" stroke="#CFD8DC" strokeWidth="1" />

            {/* Mask Straps */}
            <line x1="60" y1="105" x2="53" y2="95" stroke="#FFF" strokeWidth="1.5" />
            <line x1="75" y1="140" x2="53" y2="105" stroke="#FFF" strokeWidth="1.5" />
            <line x1="140" y1="105" x2="147" y2="95" stroke="#FFF" strokeWidth="1.5" />
            <line x1="125" y1="140" x2="147" y2="105" stroke="#FFF" strokeWidth="1.5" />
        </svg>
    );
}
