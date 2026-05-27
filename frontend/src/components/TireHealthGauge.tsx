/**
 * TireHealthGauge — Circular gauge showing health score (0–10).
 * Pure web/Next.js SVG version. No React Native/Expo dependencies.
 */

import React from "react";

interface TireHealthGaugeProps {
  score: number;       // 0 to 10
  size?: number;       // diameter in px
}

const STROKE = 8;

function scoreToColor(score: number): string {
  if (score >= 7.5) return "#3FB950";
  if (score >= 5.0) return "#E3B341";
  if (score >= 3.0) return "#F0883E";
  return "#F85149";
}

function scoreToLabel(score: number): string {
  if (score >= 8) return "Excellent";
  if (score >= 6) return "Good";
  if (score >= 4) return "Fair";
  if (score >= 2) return "Poor";
  return "Critical";
}

export function TireHealthGauge({ score, size = 80 }: TireHealthGaugeProps) {
  const radius = (size - STROKE) / 2;
  const circumference = 2 * Math.PI * radius;
  const safeScore = Math.max(0, Math.min(10, score));
  const progress = safeScore / 10;
  const color = scoreToColor(safeScore);
  const strokeDash = circumference - circumference * progress;

  return (
    <div style={{ width: size, height: size, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <svg width={size} height={size} style={{ position: "absolute", top: 0, left: 0 }}>
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          {/* Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#30363D"
            strokeWidth={STROKE}
            fill="none"
          />
          {/* Progress Arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeWidth={STROKE}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDash}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 1s" }}
          />
        </g>
      </svg>
      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
        <span style={{ fontSize: size * 0.22, fontWeight: 800, color }}>{safeScore.toFixed(1)}</span>
        <span style={{ fontSize: size * 0.12, color: "#8B949E" }}>{scoreToLabel(safeScore)}</span>
      </div>
    </div>
  );
}
