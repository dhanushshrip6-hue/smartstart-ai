import { useEffect, useState, type ReactNode } from "react";
import { Bar, Doughnut, Line, PolarArea, Radar } from "react-chartjs-2";
import { ArcElement, BarElement, CategoryScale, Chart, Filler, Legend, LineElement, LinearScale, PointElement, RadialLinearScale, Tooltip } from "chart.js";
import { MapContainer, TileLayer, Circle, CircleMarker, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Basis } from "../types";

Chart.register(ArcElement, BarElement, CategoryScale, Filler, Legend, LineElement, LinearScale, PointElement, RadialLinearScale, Tooltip);
Chart.defaults.font.family = '"Schibsted Grotesk", system-ui, sans-serif';
Chart.defaults.color = "#5c6b75";
export const C = { orange: "#d9480f", blue: "#1f5fa8", green: "#1c7c54", amber: "#c78a0a", purple: "#7a3aa8", ink: "#17232d", grey: "#9aa8a1" };
export const SEG_COLORS = [C.blue, C.green, C.amber, C.purple, "#0e8a9a", "#b0446b"];

const cls: Record<Basis, string> = { "Retrieved fact": "fact", "User assumption": "assumption", "Calculated estimate": "estimate", "AI interpretation": "ai" };
export const Tag = ({ kind }: { kind: Basis }) => <span className={`tag ${cls[kind]}`}>{kind}</span>;

export function Card({ title, tag, children, className = "" }: { title?: string; tag?: Basis; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || tag) && <header><h3>{title}</h3>{tag && <Tag kind={tag} />}</header>}
      {children}
    </section>
  );
}
export const Stat = ({ label, value, sub, tag }: { label: string; value: ReactNode; sub?: string; tag?: Basis }) => (
  <div className="card stat"><div className="l">{label}</div><div className="v">{value}</div>{sub && <div className="small muted">{sub}</div>}{tag && <div style={{ marginTop: 8 }}><Tag kind={tag} /></div>}</div>
);
export const PageHead = ({ title, intro, children }: { title: string; intro: string; children?: ReactNode }) => (
  <div className="page-head fade"><div><h2>{title}</h2><p>{intro}</p></div>{children}</div>
);
export const Meter = ({ value, max = 100, color = C.blue }: { value: number; max?: number; color?: string }) => (
  <div className="bar" role="meter" aria-valuenow={value} aria-valuemax={max}><i style={{ width: `${Math.min(100, (value / max) * 100)}%`, ["--c" as any]: color }} /></div>
);
export const Banner = ({ kind, children }: { kind: "err" | "warn" | "info"; children: ReactNode }) => <div className={`banner ${kind}`} role={kind === "err" ? "alert" : "status"}>{children}</div>;

export function ScoreRing({ score, color, size = 170 }: { score: number; color: string; size?: number }) {
  const [v, setV] = useState(0);
  useEffect(() => { const t = setTimeout(() => setV(score), 80); return () => clearTimeout(t); }, [score]);
  const r = 70, c = 2 * Math.PI * r;
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg viewBox="0 0 170 170" width={size} height={size}><circle cx="85" cy="85" r={r} fill="none" stroke="#e6ebe7" strokeWidth="14" />
        <circle cx="85" cy="85" r={r} fill="none" stroke={color} strokeWidth="14" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} style={{ transition: "stroke-dashoffset 1.1s cubic-bezier(.2,.8,.2,1)" }} /></svg>
      <div className="c"><b>{score.toFixed(0)}</b><span className="small muted">of 100</span></div>
    </div>
  );
}

const base = { responsive: true, maintainAspectRatio: false } as const;
export const BarChart = ({ data, options, tall }: { data: any; options?: any; tall?: boolean }) => <div className={`chart ${tall ? "tall" : ""}`}><Bar data={data} options={{ ...base, ...options }} /></div>;
export const LineChart = ({ data, options }: { data: any; options?: any }) => <div className="chart"><Line data={data} options={{ ...base, ...options }} /></div>;
export const DonutChart = ({ data, options }: { data: any; options?: any }) => <div className="chart short"><Doughnut data={data} options={{ ...base, cutout: "62%", plugins: { legend: { position: "right" } }, ...options }} /></div>;
export const RadarChart = ({ data }: { data: any }) => <div className="chart tall"><Radar data={data} options={{ ...base, scales: { r: { min: 0, max: 100, ticks: { stepSize: 25, backdropColor: "transparent" } } }, plugins: { legend: { display: false } } }} /></div>;
export const PolarChart = ({ data }: { data: any }) => <div className="chart tall"><PolarArea data={data} options={{ ...base, plugins: { legend: { position: "bottom" } } }} /></div>;

export interface Pt { lat: number; lon: number; color: string; label: string; radius?: number }
function Fit({ center, radiusM }: { center: [number, number]; radiusM: number }) {
  const map = useMap();
  useEffect(() => { map.fitBounds(L.latLng(center[0], center[1]).toBounds(radiusM * 2), { padding: [10, 10] }); }, [center[0], center[1], radiusM]);
  return null;
}
const homeIcon = L.divIcon({ className: "", html: '<div class="pulse"></div>', iconSize: [18, 18], iconAnchor: [9, 9] });
export function MapView({ center, radiusM, points = [], rings = [], label = "Selected location" }: { center: [number, number]; radiusM: number; points?: Pt[]; rings?: number[]; label?: string }) {
  return (
    <div className="map">
      <MapContainer center={center} zoom={13} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Fit center={center} radiusM={radiusM} />
        <Circle center={center} radius={radiusM} pathOptions={{ color: C.ink, weight: 1.5, fillOpacity: 0.04, dashArray: "6 6" }} />
        {rings.map((r) => <Circle key={r} center={center} radius={r} pathOptions={{ color: C.grey, weight: 1, fill: false }} />)}
        {points.map((p, i) => (
          <CircleMarker key={i} center={[p.lat, p.lon]} radius={p.radius ?? 5} pathOptions={{ color: "#fff", weight: 1, fillColor: p.color, fillOpacity: 0.9 }}>
            <Popup>{p.label}</Popup>
          </CircleMarker>
        ))}
        <Marker position={center} icon={homeIcon}><Popup>{label}</Popup></Marker>
      </MapContainer>
    </div>
  );
}
export const Legend2 = ({ items }: { items: [string, string][] }) => <div className="legend">{items.map(([l, c]) => <span key={l} style={{ ["--c" as any]: c }}>{l}</span>)}</div>;
