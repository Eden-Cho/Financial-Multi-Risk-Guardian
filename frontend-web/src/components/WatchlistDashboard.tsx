"use client";

import React, { useState, useEffect } from "react";

interface WatchlistItem {
  stock_name: string;
  score: number;
  status: "정상" | "주의" | "경고" | "위험" | string;
  current_price: string;
  change_str: string;
}

interface WatchlistDashboardProps {
  userId?: string;
  onSelectStock: (stockName: string) => void;
}

export default function WatchlistDashboard({
  userId = "default_user",
  onSelectStock,
}: WatchlistDashboardProps) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [newStock, setNewStock] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // 백엔드 API로부터 사용자 관심 종목 및 일괄 안전도 조회
  const fetchWatchlist = async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/watchlist?user_id=${userId}`);
      if (!res.ok) throw new Error("관심 종목을 불러오지 못했습니다.");
      const data = await res.json();
      setWatchlist(data.items || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, [userId]);

  // 관심 종목 추가
  const handleAddStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStock.trim()) return;

    setSubmitting(true);
    try {
      const res = await fetch("http://localhost:8000/api/watchlist/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId, stockName: newStock.trim() }),
      });
      if (res.ok) {
        setNewStock("");
        await fetchWatchlist();
      }
    } catch (err) {
      console.error("추가 실패:", err);
    } finally {
      setSubmitting(false);
    }
  };

  // 관심 종목 삭제
  const handleRemoveStock = async (stockName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await fetch("http://localhost:8000/api/watchlist/remove", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId, stockName }),
      });
      if (res.ok) {
        setWatchlist((prev) => prev.filter((item) => item.stock_name !== stockName));
      }
    } catch (err) {
      console.error("삭제 실패:", err);
    }
  };

  // 통계 계산
  const safeCount = watchlist.filter((item) => item.score >= 70).length;
  const cautionCount = watchlist.filter((item) => item.score >= 50 && item.score < 70).length;
  const dangerCount = watchlist.filter((item) => item.score < 50).length;

  const getStatusBadge = (score: number) => {
    if (score >= 70) {
      return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-700">정상</span>;
    } else if (score >= 50) {
      return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-700">주의</span>;
    } else {
      return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-100 text-rose-700 animate-pulse">위험</span>;
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-6 space-y-6">
      {/* 1. 상단 통계 카드 바 */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
          <p className="text-sm font-medium text-slate-500">총 보유/관심 종목</p>
          <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1">{watchlist.length}개</p>
        </div>
        <div className="bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 rounded-xl p-4 shadow-sm">
          <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">정상 / 안전</p>
          <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-300 mt-1">{safeCount}개</p>
        </div>
        <div className="bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/50 rounded-xl p-4 shadow-sm">
          <p className="text-sm font-medium text-amber-600 dark:text-amber-400">주의 관찰</p>
          <p className="text-2xl font-bold text-amber-700 dark:text-amber-300 mt-1">{cautionCount}개</p>
        </div>
        <div className="bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-xl p-4 shadow-sm">
          <p className="text-sm font-medium text-rose-600 dark:text-rose-400">고위험 경보</p>
          <p className="text-2xl font-bold text-rose-700 dark:text-rose-300 mt-1">{dangerCount}개</p>
        </div>
      </div>

      {/* 2. 빠른 추가 폼 */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">내 포트폴리오 리스크 관제</h3>
          <p className="text-xs text-slate-500 mt-0.5">등록된 종목은 매일 백그라운드에서 공시 및 재무 변동을 1회씩 자동 동기화합니다.</p>
        </div>
        <form onSubmit={handleAddStock} className="flex items-center gap-2 w-full sm:w-auto">
          <input
            type="text"
            placeholder="기업명 입력 (예: 노루페인트, 한화)"
            value={newStock}
            onChange={(e) => setNewStock(e.target.value)}
            className="px-3.5 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full sm:w-64"
          />
          <button
            type="submit"
            disabled={submitting || !newStock.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg transition-colors whitespace-nowrap"
          >
            {submitting ? "등록 중..." : "종목 추가"}
          </button>
        </form>
      </div>

      {/* 3. 관심 종목 테이블 */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-sm text-slate-400">
            포트폴리오 리스크를 진단하고 있습니다...
          </div>
        ) : watchlist.length === 0 ? (
          <div className="py-16 text-center text-sm text-slate-400">
            등록된 관심 종목이 없습니다. 상단에서 보유 종목을 추가해 보세요.
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 text-xs uppercase tracking-wider">
                <th className="py-3.5 px-4 font-semibold">종목명</th>
                <th className="py-3.5 px-4 font-semibold">현재가 (등락)</th>
                <th className="py-3.5 px-4 font-semibold">종합 안전 점수</th>
                <th className="py-3.5 px-4 font-semibold text-center">위험도 상태</th>
                <th className="py-3.5 px-4 font-semibold text-right">관리</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {watchlist.map((item) => (
                <tr
                  key={item.stock_name}
                  onClick={() => onSelectStock(item.stock_name)}
                  className="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition-colors"
                >
                  <td className="py-3.5 px-4 font-bold text-slate-800 dark:text-slate-100">
                    {item.stock_name}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="font-medium text-slate-900 dark:text-slate-100">{item.current_price}원</span>
                    <span
                      className={`ml-2 text-xs font-semibold ${
                        item.change_str.includes("+")
                          ? "text-red-500"
                          : item.change_str.includes("-")
                          ? "text-blue-500"
                          : "text-slate-400"
                      }`}
                    >
                      {item.change_str}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-3">
                      <div className="w-24 bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            item.score >= 70
                              ? "bg-emerald-500"
                              : item.score >= 50
                              ? "bg-amber-500"
                              : "bg-rose-500"
                          }`}
                          style={{ width: `${item.score}%` }}
                        />
                      </div>
                      <span className="font-semibold text-slate-700 dark:text-slate-200">{item.score}점</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-center">{getStatusBadge(item.score)}</td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={(e) => handleRemoveStock(item.stock_name, e)}
                      className="text-xs text-slate-400 hover:text-rose-600 px-2 py-1 rounded transition-colors"
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}