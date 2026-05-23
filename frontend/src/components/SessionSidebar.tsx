"use client";

import { SavedSession } from "@/lib/storage";

interface Props {
  sessions: SavedSession[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export default function SessionSidebar({ sessions, activeId, onSelect, onNew, onDelete }: Props) {
  return (
    <div className="w-56 bg-gray-900 text-gray-200 h-screen flex flex-col shrink-0">
      <div className="p-3 border-b border-gray-700">
        <button
          onClick={onNew}
          className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition"
        >
          + 新建对话
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 && (
          <p className="text-gray-500 text-xs px-2 py-4 text-center">暂无历史对话</p>
        )}
        {sessions
          .sort((a, b) => b.updatedAt - a.updatedAt)
          .map((s) => (
            <div
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`group flex items-center justify-between px-3 py-2 rounded cursor-pointer text-sm transition ${
                s.id === activeId
                  ? "bg-gray-700 text-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
              }`}
            >
              <span className="truncate flex-1">{s.title || "新对话"}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(s.id);
                }}
                className="ml-2 text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition text-xs"
              >
                ✕
              </button>
            </div>
          ))}
      </div>
    </div>
  );
}
