"use client";

import { useState, useEffect } from "react";
import { Message } from "@/lib/api";

interface AgentStatus {
  name: string;
  label: string;
  color: string;
  status: "idle" | "thinking" | "done";
  lastAction: string;
}

export default function AgentStatusBar({ latestMessage }: { latestMessage?: Message }) {
  const [agents, setAgents] = useState<AgentStatus[]>([
    { name: "collector", label: "收集员", color: "bg-green-500", status: "idle", lastAction: "" },
    { name: "curator", label: "策展人", color: "bg-purple-500", status: "idle", lastAction: "" },
    { name: "librarian", label: "馆员", color: "bg-blue-500", status: "idle", lastAction: "" },
    { name: "editor", label: "编辑", color: "bg-orange-500", status: "idle", lastAction: "" },
  ]);

  useEffect(() => {
    if (!latestMessage) return;

    setAgents((prev) =>
      prev.map((a) => {
        // 发送消息的 Agent 标记为 done
        if (a.name === latestMessage.from_agent) {
          return { ...a, status: "done" as const, lastAction: latestMessage.msg_type };
        }
        // 接收消息的 Agent 标记为 thinking
        if (a.name === latestMessage.to_agent) {
          return { ...a, status: "thinking" as const, lastAction: "" };
        }
        return a;
      })
    );

    // 3 秒后重置状态
    const timer = setTimeout(() => {
      setAgents((prev) => prev.map((a) => ({ ...a, status: "idle" as const })));
    }, 3000);
    return () => clearTimeout(timer);
  }, [latestMessage]);

  const statusDot = (status: string) => {
    switch (status) {
      case "thinking":
        return <span className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />;
      case "done":
        return <span className="w-2 h-2 bg-green-400 rounded-full" />;
      default:
        return <span className="w-2 h-2 bg-gray-300 rounded-full" />;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-4">
      <div className="flex items-center gap-4 text-xs">
        <span className="text-gray-500 font-medium">Agent 状态</span>
        {agents.map((a) => (
          <div key={a.name} className="flex items-center gap-1.5">
            {statusDot(a.status)}
            <span className="text-gray-600">{a.label}</span>
            {a.lastAction && (
              <span className="text-gray-400">({a.lastAction})</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
