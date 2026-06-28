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

export function DashboardCharts({ report }: Props) {
  const { theme } = useApp();
  const isDark = theme === "dark";

  // 언어 비중(라인 수)을 파이 차트에 매핑
  const langData = report.languages.map((l) => ({
    name: l.name,
    value: l.lines,
  }));

  // 건강도를 기반으로 임의의 레이더 차트 수치 계산 (실제 서비스에서는 백엔드에서 제공하는게 바람직함)
  const baseHealth = report.health_score;
  const radarData = [
    { subject: "보안(Security)", A: Math.min(100, baseHealth + 10), fullMark: 100 },
    { subject: "모듈화(Modularity)", A: Math.max(0, baseHealth - 5), fullMark: 100 },
    { subject: "코드품질(Quality)", A: baseHealth, fullMark: 100 },
    { subject: "테스트(Test)", A: Math.max(0, baseHealth - 20), fullMark: 100 },
    { subject: "복잡도(Complexity)", A: Math.min(100, baseHealth + 5), fullMark: 100 },
  ];

  return (
    <div className={`mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>
      <div className={`p-4 rounded-xl border ${isDark ? "bg-zinc-900/50 border-zinc-800" : "bg-white border-zinc-200 shadow-sm"}`}>
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

      <div className={`p-4 rounded-xl border ${isDark ? "bg-zinc-900/50 border-zinc-800" : "bg-white border-zinc-200 shadow-sm"}`}>
        <h3 className="text-sm font-semibold mb-2">건강도 다차원 분석</h3>
        <p className="text-[10px] text-zinc-500 mb-4">종합 품질 점수(Health Score) 기반 평가</p>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius={65} data={radarData}>
              <PolarGrid stroke={isDark ? "#3f3f46" : "#e4e4e7"} />
              <PolarAngleAxis dataKey="subject" tick={{ fill: isDark ? "#a1a1aa" : "#71717a", fontSize: 10 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
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
