"use client";

import { useApp } from "@/common/contexts/AppContext";
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

const mockContributorData = [
  { name: "gabriel", commits: 45, value: 45 },
  { name: "alice", commits: 25, value: 25 },
  { name: "bob", commits: 20, value: 20 },
];

const COLORS = ["#818cf8", "#34d399", "#fbbf24", "#f87171"];

const mockHealthData = [
  { subject: "보안(Security)", A: 80, fullMark: 100 },
  { subject: "모듈화(Modularity)", A: 65, fullMark: 100 },
  { subject: "코드품질(Quality)", A: 90, fullMark: 100 },
  { subject: "테스트(Test)", A: 40, fullMark: 100 },
  { subject: "복잡도(Complexity)", A: 75, fullMark: 100 },
];

export function DashboardCharts() {
  const { theme } = useApp();
  const isDark = theme === "dark";

  return (
    <div className={`mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>
      <div className={`p-4 rounded-xl border ${isDark ? "bg-zinc-900/50 border-zinc-800" : "bg-white border-zinc-200 shadow-sm"}`}>
        <h3 className="text-sm font-semibold mb-2">기여도 현황 (Mock)</h3>
        <p className="text-[10px] text-zinc-500 mb-4">Git 커밋 비중</p>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={mockContributorData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={70}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
              >
                {mockContributorData.map((entry, index) => (
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
        <h3 className="text-sm font-semibold mb-2">건강도 다차원 분석 (Mock)</h3>
        <p className="text-[10px] text-zinc-500 mb-4">분석 항목별 레이더 차트 (이슈 논의 후 산식 적용 예정)</p>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius={65} data={mockHealthData}>
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
