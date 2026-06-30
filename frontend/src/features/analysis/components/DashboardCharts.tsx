"use client";

import { useApp } from "@/common/contexts/AppContext";
import type { WorkspaceReport } from "@/common/types/contracts";
import {
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";

const COLORS = ["#818cf8", "#34d399", "#fbbf24", "#f87171", "#c084fc", "#f472b6", "#a78bfa", "#2dd4bf"];

interface Props {
  report: WorkspaceReport;
}

interface RadarRadiusTickProps {
  x?: number | string;
  y?: number | string;
  payload?: {
    value?: number | string;
  };
}

export function DashboardCharts({ report }: Props) {
  const { theme } = useApp();
  const isDark = theme === "dark";

  // 언어 비중(라인 수)을 파이 차트에 매핑
  const langData = report.languages.map((l) => ({
    name: l.name,
    value: l.lines,
  }));

  const metrics = report.health_metrics;
  const getScore = (val?: number) => val ?? 50;

  const radarData = [
    { subject: "보안(Security)", A: getScore(metrics?.security), fullMark: 100 },
    { subject: "모듈화(Modularity)", A: getScore(metrics?.modularity), fullMark: 100 },
    { subject: "코드품질(Quality)", A: getScore(metrics?.quality), fullMark: 100 },
    { subject: "복잡도(Complexity)", A: getScore(metrics?.complexity), fullMark: 100 },
  ];

  const renderRadarRadiusTick = ({ x, y, payload }: RadarRadiusTickProps) => {
    const tickX = Number(x);
    const tickY = Number(y);
    if (!Number.isFinite(tickX) || !Number.isFinite(tickY)) return null;

    return (
      <text
        x={tickX + 4}
        y={tickY}
        fill={isDark ? "#d4d4d8" : "#52525b"}
        fontSize={8}
        fontWeight={700}
        textAnchor="start"
        dominantBaseline="central"
      >
        {payload?.value}
      </text>
    );
  };

  return (
    <div className={`mt-4 grid grid-cols-[repeat(auto-fit,minmax(min(100%,20rem),1fr))] gap-4 ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>
      <div className={`min-w-0 overflow-hidden p-4 rounded-xl border ${isDark ? "bg-zinc-900/50 border-zinc-800" : "bg-white border-zinc-200 shadow-sm"}`}>
        <h3 className="text-sm font-semibold mb-2">저장소 언어 분포</h3>
        <p className="text-[10px] text-zinc-500 mb-4">소스코드 라인 비중</p>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={langData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={70}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
              >
                {langData.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: isDark ? "#18181b" : "#fff", 
                  border: isDark ? "1px solid #27272a" : "1px solid #e4e4e7",
                  borderRadius: "8px",
                  fontSize: "12px"
                }} 
              />
              <Legend wrapperStyle={{ fontSize: "10px" }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className={`min-w-0 overflow-hidden p-4 rounded-xl border ${isDark ? "bg-zinc-900/50 border-zinc-800" : "bg-white border-zinc-200 shadow-sm"}`}>
        <h3 className="text-sm font-semibold mb-2">건강도 다차원 분석</h3>
        <p className="text-[10px] text-zinc-500 mb-4">종합 품질 점수(Health Score) 기반 평가</p>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius={65} data={radarData}>
              <PolarGrid stroke={isDark ? "#3f3f46" : "#e4e4e7"} />
              <PolarAngleAxis dataKey="subject" radius={78} tick={{ fill: isDark ? "#a1a1aa" : "#71717a", fontSize: 10 }} />
              <PolarRadiusAxis
                angle={90}
                axisLine={false}
                domain={[0, 100]}
                tick={renderRadarRadiusTick}
                tickLine={false}
                ticks={[25, 50, 75, 100]}
              />
              <Radar name="Repository" dataKey="A" stroke="#818cf8" fill="#818cf8" fillOpacity={0.4} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: isDark ? "#18181b" : "#fff", 
                  border: isDark ? "1px solid #27272a" : "1px solid #e4e4e7",
                  borderRadius: "8px",
                  fontSize: "12px"
                }} 
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
