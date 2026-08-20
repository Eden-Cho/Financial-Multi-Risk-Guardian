"use client";

import React, { useState } from "react";
import axios from "axios";
import Link from "next/link";
import { 
  ShieldAlert, 
  Search, 
  X, 
  Plus, 
  Trash2, 
  RefreshCw, 
  Eye, 
  Lock, 
  User,
  ShieldCheck,
  Users,
  MessageSquareQuote,
  Send,
  Sparkles,
  BellRing
} from "lucide-react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer
} from "recharts";

const API_BASE = "http://127.0.0.1:8000/api";

interface WatchItem {
  id: number;
  stock_name: string;
  memo: string;
  created_at: string;
}

export default function Home() {
  // --- 상태 관리 ---
  const [currentUser, setCurrentUser] = useState<string>("");
  const [currentNickname, setCurrentNickname] = useState<string>("");
  const [userRole, setUserRole] = useState<string>("user");
  const [isAuthOpen, setIsAuthOpen] = useState<boolean>(false);
  
  // 로그인 폼 상태
  const [authId, setAuthId] = useState("");
  const [authPw, setAuthPw] = useState("");
  const [authMsg, setAuthMsg] = useState("");

  // 소셜 온보딩 상태
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [socialProvider, setSocialProvider] = useState<"kakao" | "naver" | "google">("kakao");
  const [socialTempUsername, setSocialTempUsername] = useState("");
  const [socialNickname, setSocialNickname] = useState("");
  const [socialEmail, setSocialEmail] = useState("");
  const [socialExp, setSocialExp] = useState("beginner");
  const [agreePrivacyAlert, setAgreePrivacyAlert] = useState(true);
  const [agreeMarketing, setAgreeMarketing] = useState(false);

  // 약관 모달 상태
  const [modalType, setModalType] = useState<"terms" | "privacy" | null>(null);

  // 탭 상태: analyze(진단), watchlist(관심종목), inquiry(문의하기), admin(관리자)
  const [activeTab, setActiveTab] = useState<"analyze" | "watchlist" | "inquiry" | "admin">("analyze");

  // 단일 종목 분석 상태
  const [searchStock, setSearchStock] = useState("모아데이타");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  // 관심 종목 상태
  const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  const [newStockName, setNewStockName] = useState("");
  const [newStockMemo, setNewStockMemo] = useState("");
  const [batchResults, setBatchResults] = useState<any[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);

  // 문의하기 상태
  const [inqCategory, setInqCategory] = useState("기능 문의");
  const [inqContent, setInqContent] = useState("");
  const [inqSuccess, setInqSuccess] = useState("");

  // 관리자 전용 데이터 상태
  const [adminUsers, setAdminUsers] = useState<any[]>([]);
  const [adminInquiries, setAdminInquiries] = useState<any[]>([]);

  // --- 일반 로그인 ---
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthMsg("");
    try {
      const res = await axios.post(`${API_BASE}/auth/login`, {
        username: authId,
        password: authPw
      });
      if (res.data.success) {
        setCurrentUser(authId);
        setCurrentNickname(res.data.nickname || authId);
        setUserRole(res.data.role || "user");
        setIsAuthOpen(false);
        setAuthId("");
        setAuthPw("");
        fetchWatchlist(authId);
      }
    } catch (err: any) {
      setAuthMsg(err.response?.data?.detail || "아이디 또는 비밀번호가 올바르지 않습니다.");
    }
  };

  // --- 간편 소셜 로그인 시도 ---
  const handleSocialTrigger = async (provider: "kakao" | "naver" | "google") => {
    setSocialProvider(provider);
    setAuthMsg("");
    
    const demoSocialId = "user_01"; 
    
    try {
      const res = await axios.post(`${API_BASE}/auth/social-check`, {
        social_id: demoSocialId,
        provider: provider
      });

      if (res.data.is_new) {
        setSocialTempUsername(res.data.suggested_username);
        setSocialEmail(res.data.suggested_email || "");
        setSocialNickname("");
        setIsOnboarding(true);
      } else {
        const user = res.data.user;
        setCurrentUser(user.username);
        setCurrentNickname(user.nickname || user.username);
        setUserRole(user.role || "user");
        setIsAuthOpen(false);
        fetchWatchlist(user.username);
      }
    } catch (err) {
      setAuthMsg("간편 로그인 처리 중 오류가 발생했습니다.");
    }
  };

  // --- 소셜 온보딩 완료 제출 ---
  const handleCompleteOnboarding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreePrivacyAlert) {
      alert("개인정보 수집 및 긴급 공시 알림 제공에 동의해 주세요.");
      return;
    }

    try {
      const res = await axios.post(`${API_BASE}/auth/social-onboarding`, {
        username: socialTempUsername,
        nickname: socialNickname || `투자자_${socialTempUsername.slice(-4)}`,
        email: socialEmail || `${socialTempUsername}@${socialProvider}.com`,
        provider: socialProvider,
        experience: socialExp,
        marketing_agree: agreeMarketing
      });

      if (res.data.success) {
        setCurrentUser(socialTempUsername);
        setCurrentNickname(res.data.user.nickname);
        setUserRole("user");
        setIsOnboarding(false);
        setIsAuthOpen(false);
        fetchWatchlist(socialTempUsername);
      }
    } catch (err: any) {
      setAuthMsg(err.response?.data?.detail || "온보딩 처리 실패");
    }
  };

  const handleLogout = () => {
    setCurrentUser("");
    setCurrentNickname("");
    setUserRole("user");
    setWatchlist([]);
    setBatchResults([]);
    setActiveTab("analyze");
  };

  // --- 분석 및 포트폴리오 ---
  const handleAnalyze = async () => {
    if (!searchStock.trim()) return;
    setAnalyzing(true);
    try {
      const res = await axios.get(`${API_BASE}/analyze/${encodeURIComponent(searchStock)}`);
      setAnalysisResult(res.data);
    } catch (err) {
      alert("종목 분석 중 오류가 발생했습니다.");
    } finally {
      setAnalyzing(false);
    }
  };

  const fetchWatchlist = async (username: string) => {
    try {
      const res = await axios.get(`${API_BASE}/watchlist/${username}`);
      setWatchlist(res.data.watchlist);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddWatchlist = async () => {
    if (!currentUser) {
      setIsAuthOpen(true);
      return;
    }
    if (!newStockName.trim()) return;
    try {
      await axios.post(`${API_BASE}/watchlist/add`, {
        username: currentUser,
        stock_name: newStockName,
        memo: newStockMemo || "관심 종목"
      });
      setNewStockName("");
      setNewStockMemo("");
      fetchWatchlist(currentUser);
    } catch (err: any) {
      alert(err.response?.data?.detail || "등록 실패");
    }
  };

  const handleDeleteWatchlist = async (stockName: string) => {
    try {
      await axios.delete(`${API_BASE}/watchlist/delete`, {
        data: { username: currentUser, stock_name: stockName }
      });
      fetchWatchlist(currentUser);
    } catch (err: any) {
      alert(err.response?.data?.detail || "삭제 실패");
    }
  };

  const handleBatchScan = async () => {
    if (watchlist.length === 0) return;
    setBatchLoading(true);
    try {
      const promises = watchlist.map(item => axios.get(`${API_BASE}/analyze/${encodeURIComponent(item.stock_name)}`));
      const responses = await Promise.all(promises);
      const results = responses.map((res, idx) => ({
        stock_name: watchlist[idx].stock_name,
        memo: watchlist[idx].memo,
        score: res.data.score_info.score,
        status: res.data.score_info.status
      }));
      setBatchResults(results);
    } catch (err) {
      alert("일괄 점검 중 오류가 발생했습니다.");
    } finally {
      setBatchLoading(false);
    }
  };

  // --- 문의하기 핸들러 ---
  const handleInquirySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) {
      setIsAuthOpen(true);
      return;
    }
    if (!inqContent.trim()) return;
    try {
      await axios.post(`${API_BASE}/inquiry/create`, {
        username: `${currentNickname}(${currentUser})`,
        category: inqCategory,
        content: inqContent
      });
      setInqSuccess("소중한 의견이 정상 접수되었습니다. 관리자가 신속히 검토하겠습니다.");
      setInqContent("");
    } catch (err) {
      alert("문의 접수 실패");
    }
  };

  // --- 관리자 데이터 조회 ---
  const fetchAdminData = async () => {
    try {
      const [uRes, iRes] = await Promise.all([
        axios.get(`${API_BASE}/admin/users`),
        axios.get(`${API_BASE}/admin/inquiries`)
      ]);
      setAdminUsers(uRes.data.users);
      setAdminInquiries(iRes.data.inquiries);
    } catch (err) {
      console.error(err);
    }
  };

  const isElevatedUser = userRole === "master" || userRole === "admin";

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* 1. 상단 내비게이션 바 */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-500 text-white p-2 rounded-xl shadow-sm">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 leading-tight">Financial Multi-Risk Guardian</h1>
            <p className="text-xs text-slate-500">주린이를 위한 다차원 지뢰 탐지 & 뇌동매매 방지 비서</p>
          </div>
        </div>

        <div>
          {currentUser ? (
            <div className="flex items-center gap-3 bg-slate-100 py-1.5 px-3 rounded-full text-sm">
              <span className="text-slate-700 font-medium flex items-center gap-1.5">
                {isElevatedUser ? (
                  <ShieldCheck className="w-4 h-4 text-purple-600" />
                ) : (
                  <User className="w-4 h-4 text-emerald-600" />
                )}
                <b>{currentNickname}</b>님 <span className="text-xs text-slate-400">({userRole})</span>
              </span>
              <button 
                onClick={handleLogout}
                className="text-xs text-slate-400 hover:text-rose-500 font-semibold transition cursor-pointer"
              >
                로그아웃
              </button>
            </div>
          ) : (
            <button
              onClick={() => {
                setIsOnboarding(false);
                setIsAuthOpen(true);
              }}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold px-4 py-2 rounded-lg shadow-sm transition cursor-pointer"
            >
              로그인 / 회원가입
            </button>
          )}
        </div>
      </header>

      {/* 2. 메인 컨텐츠 영역 */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6">
        <div className="flex gap-2 border-b border-slate-200 mb-6">
          <button
            onClick={() => setActiveTab("analyze")}
            className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
              activeTab === "analyze"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-400 hover:text-slate-700"
            }`}
          >
            🔍 단일 종목 정밀 진단
          </button>
          <button
            onClick={() => setActiveTab("watchlist")}
            className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
              activeTab === "watchlist"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-400 hover:text-slate-700"
            }`}
          >
            ⭐ 관심 종목 가디언 {watchlist.length > 0 && `(${watchlist.length})`}
          </button>
          <button
            onClick={() => setActiveTab("inquiry")}
            className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
              activeTab === "inquiry"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-400 hover:text-slate-700"
            }`}
          >
            💬 의견 및 문의
          </button>

          {isElevatedUser && (
            <button
              onClick={() => {
                setActiveTab("admin");
                fetchAdminData();
              }}
              className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
                activeTab === "admin"
                  ? "border-purple-600 text-purple-600"
                  : "border-transparent text-slate-400 hover:text-purple-600"
              }`}
            >
              ⚙️ 관리자 센터
            </button>
          )}
        </div>

        {/* [탭 1: 단일 종목 정밀 진단] */}
        {activeTab === "analyze" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col gap-4">
              <h2 className="text-base font-bold text-slate-800">종목 리스크 스캔</h2>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchStock}
                  onChange={(e) => setSearchStock(e.target.value)}
                  placeholder="예: 모아데이타, 삼성전자"
                  className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                />
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white px-4 py-2 rounded-lg font-medium text-sm transition flex items-center gap-1.5 cursor-pointer"
                >
                  {analyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  스캔
                </button>
              </div>

              <div className="bg-slate-50 p-4 rounded-xl text-xs text-slate-600 space-y-2 border border-slate-100">
                <p className="font-bold text-slate-700">💡 이런 위험을 중점 진단합니다:</p>
                <p>• <b>CB/BW 오버행:</b> 주식으로 전환될 대규모 잠재 물량</p>
                <p>• <b>유상증자 / 감자:</b> 주주가치 희석 및 자본 건전성</p>
                <p>• <b>관리종목 / 상폐 위험:</b> DART 부실 징후 공시</p>
              </div>
            </div>

            <div className="md:col-span-2 space-y-6">
              {analysisResult ? (
                <>
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
                    <div>
                      <span className="text-xs font-semibold px-2.5 py-1 bg-emerald-50 text-emerald-600 rounded-full">
                        {analysisResult.score_info.status}
                      </span>
                      <h3 className="text-2xl font-black text-slate-900 mt-2">
                        {analysisResult.stock_name}
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        공시 {analysisResult.score_info.dart_count || 0}건 · 뉴스 {analysisResult.score_info.news_count || 0}건 종합 분석
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-400 font-medium">Safety Score</p>
                      <p className={`text-4xl font-extrabold ${
                        analysisResult.score_info.score >= 70 ? "text-emerald-500" :
                        analysisResult.score_info.score >= 50 ? "text-amber-500" : "text-rose-500"
                      }`}>
                        {analysisResult.score_info.score}<span className="text-lg font-normal text-slate-400">/100</span>
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center">
                      <h4 className="text-xs font-bold text-slate-500 mb-2">다차원 리스크 지형도</h4>
                      <div className="w-full h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart data={analysisResult.radar_data}>
                            <PolarGrid stroke="#e2e8f0" />
                            <PolarAngleAxis dataKey="theta" tick={{ fill: "#64748b", fontSize: 11 }} />
                            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                            <Radar name="위험도" dataKey="r" stroke="#ef4444" fill="#ef4444" fillOpacity={0.4} />
                          </RadarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
                      <h4 className="text-xs font-bold text-slate-500 mb-3">AI 진단 소견서</h4>
                      <div className="flex-1 overflow-y-auto text-sm text-slate-700 whitespace-pre-line leading-relaxed">
                        {analysisResult.report_text}
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="bg-white p-12 rounded-2xl border border-dashed border-slate-200 text-center text-slate-400">
                  <Search className="w-10 h-10 mx-auto mb-3 text-slate-300" />
                  <p>종목명을 입력하고 스캔 버튼을 누르면 AI 정밀 진단이 시작됩니다.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* [탭 2: 내 관심종목 가디언] */}
        {activeTab === "watchlist" && (
          <div className="space-y-6">
            {!currentUser ? (
              <div className="bg-white p-12 rounded-2xl border border-slate-200 shadow-sm text-center">
                <Lock className="w-10 h-10 mx-auto text-emerald-600 mb-3" />
                <h3 className="text-lg font-bold text-slate-800 mb-1">로그인이 필요한 기능입니다</h3>
                <p className="text-sm text-slate-500 mb-6">관심 종목을 등록하고 지뢰 공시를 한눈에 일괄 점검하세요.</p>
                <button
                  onClick={() => {
                    setIsOnboarding(false);
                    setIsAuthOpen(true);
                  }}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold px-6 py-2.5 rounded-lg shadow-sm transition cursor-pointer"
                >
                  로그인하고 시작하기
                </button>
              </div>
            ) : (
              <>
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                  <h3 className="text-sm font-bold text-slate-800 mb-3">⭐ '살까 말까' 고민 중인 종목 간편 등록</h3>
                  <div className="flex flex-col md:flex-row gap-3">
                    <input
                      type="text"
                      value={newStockName}
                      onChange={(e) => setNewStockName(e.target.value)}
                      placeholder="종목명 (예: 모아데이타)"
                      className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 md:w-1/4"
                    />
                    <input
                      type="text"
                      value={newStockMemo}
                      onChange={(e) => setNewStockMemo(e.target.value)}
                      placeholder="담아둔 이유 / 메모 (예: 유튜브 추천, 실적 기대)"
                      className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 flex-1"
                    />
                    <button
                      onClick={handleAddWatchlist}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold px-5 py-2 rounded-lg transition flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Plus className="w-4 h-4" /> 등록
                    </button>
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                    <h4 className="font-bold text-slate-800 text-sm">담아둔 관심 종목 목록</h4>
                    <button
                      onClick={handleBatchScan}
                      disabled={batchLoading || watchlist.length === 0}
                      className="bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white text-xs font-semibold px-4 py-2 rounded-lg transition flex items-center gap-1.5 cursor-pointer"
                    >
                      {batchLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                      전체 일괄 지뢰 탐지
                    </button>
                  </div>

                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-medium">
                      <tr>
                        <th className="px-6 py-3">종목명</th>
                        <th className="px-6 py-3">투자 메모</th>
                        <th className="px-6 py-3">등록일</th>
                        <th className="px-6 py-3 text-right">삭제</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {watchlist.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-50/50">
                          <td className="px-6 py-4 font-bold text-slate-900">{item.stock_name}</td>
                          <td className="px-6 py-4 text-slate-600">{item.memo}</td>
                          <td className="px-6 py-4 text-slate-400 text-xs">{item.created_at.slice(0, 10)}</td>
                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={() => handleDeleteWatchlist(item.stock_name)}
                              className="text-slate-300 hover:text-rose-500 transition cursor-pointer"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                      {watchlist.length === 0 && (
                        <tr>
                          <td colSpan={4} className="text-center py-8 text-slate-400 text-sm">
                            등록된 관심 종목이 없습니다.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {batchResults.length > 0 && (
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                    <h4 className="font-bold text-slate-800 text-sm">⚡ 관심 종목 일괄 안전도 점검 결과</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {batchResults.map((res, idx) => (
                        <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 flex flex-col justify-between">
                          <div>
                            <div className="flex justify-between items-center mb-2">
                              <h5 className="font-bold text-slate-900">{res.stock_name}</h5>
                              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                                res.score >= 70 ? "bg-emerald-100 text-emerald-700" :
                                res.score >= 50 ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"
                              }`}>
                                {res.score}점 ({res.status})
                              </span>
                            </div>
                            <p className="text-xs text-slate-500">{res.memo}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* [탭 3: 의견 및 문의] */}
        {activeTab === "inquiry" && (
          <div className="max-w-2xl mx-auto bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center gap-3 mb-6">
              <MessageSquareQuote className="w-6 h-6 text-emerald-600" />
              <div>
                <h3 className="text-lg font-bold text-slate-800">사용자 피드백 및 기능 문의</h3>
                <p className="text-xs text-slate-500">서비스 이용 중 불편한 점이나 제안하고 싶은 기능을 남겨주세요.</p>
              </div>
            </div>

            <form onSubmit={handleInquirySubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">문의 유형</label>
                <select
                  value={inqCategory}
                  onChange={(e) => setInqCategory(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                >
                  <option value="기능 문의">기능 문의</option>
                  <option value="오류 신고">공시/뉴스 분석 오류 신고</option>
                  <option value="개선 제안">새로운 기능 제안</option>
                  <option value="기타">기타</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">내용</label>
                <textarea
                  rows={5}
                  value={inqContent}
                  onChange={(e) => setInqContent(e.target.value)}
                  placeholder="의견을 자유롭게 작성해 주세요."
                  className="w-full border border-slate-300 rounded-lg p-3 text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              {inqSuccess && (
                <p className="text-xs text-emerald-600 font-medium">{inqSuccess}</p>
              )}

              <button
                type="submit"
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm py-2.5 rounded-lg transition flex items-center justify-center gap-2 cursor-pointer"
              >
                <Send className="w-4 h-4" /> 문의사항 접수하기
              </button>
            </form>
          </div>
        )}

        {/* [탭 4: 관리자 센터] */}
        {activeTab === "admin" && isElevatedUser && (
          <div className="space-y-8">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-purple-600" />
                  <h4 className="font-bold text-slate-800 text-sm">전체 등록 회원 현황 ({adminUsers.length}명)</h4>
                </div>
                <button
                  onClick={fetchAdminData}
                  className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 font-medium cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> 새로고침
                </button>
              </div>

              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-medium">
                  <tr>
                    <th className="px-6 py-3">ID</th>
                    <th className="px-6 py-3">닉네임 (아이디)</th>
                    <th className="px-6 py-3">이메일</th>
                    <th className="px-6 py-3">가입경로</th>
                    <th className="px-6 py-3">투자경험</th>
                    <th className="px-6 py-3">마케팅동의</th>
                    <th className="px-6 py-3">권한</th>
                    <th className="px-6 py-3">관심종목 수</th>
                    <th className="px-6 py-3">가입일시</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {adminUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/50">
                      <td className="px-6 py-3 text-slate-400 text-xs">{u.id}</td>
                      <td className="px-6 py-3 font-bold text-slate-900">
                        {u.nickname} <span className="text-xs text-slate-400 font-normal">({u.username})</span>
                      </td>
                      <td className="px-6 py-3 text-xs text-slate-600">{u.email || "-"}</td>
                      <td className="px-6 py-3 text-xs text-slate-600 font-medium capitalize">{u.provider}</td>
                      <td className="px-6 py-3 text-xs text-slate-600 font-medium capitalize">{u.experience}</td>
                      <td className="px-6 py-3 text-xs">
                        {u.marketing_agree === 1 ? (
                          <span className="text-emerald-600 font-bold">동의</span>
                        ) : (
                          <span className="text-slate-400">미동의</span>
                        )}
                      </td>
                      <td className="px-6 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                          u.role === "master" ? "bg-purple-100 text-purple-700" :
                          u.role === "admin" ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600"
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-slate-600">{u.watchlist_count}개</td>
                      <td className="px-6 py-3 text-slate-400 text-xs">{u.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-slate-100 flex items-center gap-2">
                <MessageSquareQuote className="w-5 h-5 text-purple-600" />
                <h4 className="font-bold text-slate-800 text-sm">접수된 피드백 & 문의사항 목록 ({adminInquiries.length}건)</h4>
              </div>

              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-medium">
                  <tr>
                    <th className="px-6 py-3">작성자</th>
                    <th className="px-6 py-3">구분</th>
                    <th className="px-6 py-3">내용</th>
                    <th className="px-6 py-3">상태</th>
                    <th className="px-6 py-3">접수일</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {adminInquiries.map((inq) => (
                    <tr key={inq.id} className="hover:bg-slate-50/50">
                      <td className="px-6 py-3 font-semibold text-slate-800">{inq.username}</td>
                      <td className="px-6 py-3 text-slate-600 text-xs">{inq.category}</td>
                      <td className="px-6 py-3 text-slate-700">{inq.content}</td>
                      <td className="px-6 py-3">
                        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold">
                          {inq.status}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-slate-400 text-xs">{inq.created_at}</td>
                    </tr>
                  ))}
                  {adminInquiries.length === 0 && (
                    <tr>
                      <td colSpan={5} className="text-center py-6 text-slate-400 text-xs">
                        접수된 문의사항이 없습니다.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* 3. 로그인 모달 & 소셜 온보딩 통합 팝업 */}
      {isAuthOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-sm rounded-3xl p-8 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={() => setIsAuthOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            {/* 신규 소셜 유저 온보딩 폼 */}
            {isOnboarding ? (
              <div>
                <div className="text-center mb-5">
                  <div className="inline-flex p-2.5 rounded-2xl bg-emerald-50 text-emerald-600 mb-2">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-black text-slate-900">추가 정보 입력</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    맞춤형 지뢰 진단 및 알림을 위해 정보를 확인해 주세요
                  </p>
                </div>

                <form onSubmit={handleCompleteOnboarding} className="space-y-3.5">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      활동 닉네임 <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={socialNickname}
                      onChange={(e) => setSocialNickname(e.target.value)}
                      placeholder="예: 텐배거라이언"
                      className="w-full border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1 flex items-center justify-between">
                      <span>알림 수신 이메일 <span className="text-rose-500">*</span></span>
                      <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-0.5">
                        <BellRing className="w-3 h-3" /> 지뢰공시 알림용
                      </span>
                    </label>
                    <input
                      type="email"
                      value={socialEmail}
                      onChange={(e) => setSocialEmail(e.target.value)}
                      placeholder="name@example.com"
                      className="w-full border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      투자 경험 (맞춤형 진단 필터)
                    </label>
                    <select
                      value={socialExp}
                      onChange={(e) => setSocialExp(e.target.value)}
                      className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500 bg-white"
                    >
                      <option value="beginner">🌱 이제 막 시작한 주린이 (1년 미만)</option>
                      <option value="intermediate">📈 매매 경험 1~3년 차</option>
                      <option value="advanced">👑 3년 이상 숙련 투자자</option>
                    </select>
                  </div>

                  {/* 약관 체크박스 */}
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <label className="flex items-start gap-2 cursor-pointer flex-1">
                        <input
                          type="checkbox"
                          checked={agreePrivacyAlert}
                          onChange={(e) => setAgreePrivacyAlert(e.target.checked)}
                          className="rounded text-emerald-600 focus:ring-emerald-500 w-3.5 h-3.5 mt-0.5 shrink-0"
                        />
                        <span className="text-slate-700 leading-tight">
                          <b className="text-emerald-700">[필수]</b> 개인정보(공시알림) 수집 동의
                        </span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setModalType("privacy")}
                        className="text-[10px] text-slate-400 hover:text-emerald-600 underline shrink-0 ml-2"
                      >
                        전문보기
                      </button>
                    </div>

                    <div className="flex items-center justify-between">
                      <label className="flex items-start gap-2 cursor-pointer flex-1">
                        <input
                          type="checkbox"
                          checked={agreeMarketing}
                          onChange={(e) => setAgreeMarketing(e.target.checked)}
                          className="rounded text-emerald-600 focus:ring-emerald-500 w-3.5 h-3.5 mt-0.5 shrink-0"
                        />
                        <span className="text-slate-500 leading-tight">
                          [선택] 정기 리포트 수신 동의
                        </span>
                      </label>
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm py-2.5 rounded-xl transition shadow-sm cursor-pointer mt-1"
                  >
                    가디언 시작하기
                  </button>
                </form>
              </div>
            ) : (
              <div>
                <div className="text-center mb-6">
                  <h3 className="text-xl font-black text-slate-900">로그인</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    로그인하고 투자 리스크 인사이트를 확인하세요
                  </p>
                </div>

                <button
                  onClick={() => handleSocialTrigger("kakao")}
                  className="w-full bg-[#FEE500] hover:bg-[#FADA0A] text-[#191919] font-bold text-sm py-3 rounded-xl flex items-center justify-center gap-2 shadow-xs transition mb-3 cursor-pointer"
                >
                  <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                    <path d="M12 3C6.5 3 2 6.6 2 11c0 2.8 1.9 5.3 4.8 6.7-.2.8-.8 3.1-.9 3.6 0 .1 0 .2.1.3.1.1.2.1.3.1.2 0 2.8-1.9 4-2.7.6.1 1.1.1 1.7.1 5.5 0 10-3.6 10-8s-4.5-8-10-8z"/>
                  </svg>
                  카카오로 시작하기
                </button>

                <div className="grid grid-cols-2 gap-2 mb-4">
                  <button 
                    onClick={() => handleSocialTrigger("naver")}
                    className="w-full py-2.5 rounded-xl bg-[#03C75A] text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-xs hover:opacity-95 transition cursor-pointer"
                  >
                    <span className="font-black text-sm">N</span> 네이버
                  </button>
                  <button 
                    onClick={() => handleSocialTrigger("google")}
                    className="w-full py-2.5 rounded-xl bg-white border border-slate-200 text-slate-700 font-bold text-xs flex items-center justify-center gap-1.5 shadow-xs hover:bg-slate-50 transition cursor-pointer"
                  >
                    <span className="font-black text-sm text-blue-500">G</span> 구글
                  </button>
                </div>

                <div className="flex items-center my-4">
                  <div className="flex-1 border-t border-slate-200"></div>
                  <span className="px-3 text-xs text-slate-400 font-medium">또는 아이디 로그인</span>
                  <div className="flex-1 border-t border-slate-200"></div>
                </div>

                <form onSubmit={handleLoginSubmit} className="space-y-3">
                  <input
                    type="text"
                    placeholder="아이디를 입력해 주세요"
                    value={authId}
                    onChange={(e) => setAuthId(e.target.value)}
                    className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                    required
                  />
                  <input
                    type="password"
                    placeholder="비밀번호를 입력해 주세요"
                    value={authPw}
                    onChange={(e) => setAuthPw(e.target.value)}
                    className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                    required
                  />
                  
                  {authMsg && (
                    <p className="text-xs text-rose-500 text-center">{authMsg}</p>
                  )}

                  <button
                    type="submit"
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm py-3 rounded-xl transition shadow-sm cursor-pointer"
                  >
                    로그인
                  </button>
                </form>

                <div className="mt-5 text-center">
                  <p className="text-xs text-slate-500">
                    아직 계정이 없으신가요?{" "}
                    <Link
                      href="/register"
                      onClick={() => setIsAuthOpen(false)}
                      className="text-emerald-600 font-bold hover:underline"
                    >
                      일반 회원가입
                    </Link>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 약관 전문 모달 팝업 */}
      {modalType && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-3xl p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200 max-h-[85vh] flex flex-col">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-900 text-base">
                {modalType === "terms" ? "서비스 이용약관 및 투자 유의사항" : "개인정보 수집 및 이용 동의"}
              </h3>
              <button
                onClick={() => setModalType(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="my-4 p-4 bg-slate-50 rounded-2xl overflow-y-auto text-xs text-slate-600 leading-relaxed whitespace-pre-line flex-1 border border-slate-100 font-sans">
              <p className="text-amber-600 font-semibold mb-3">
                ※ 본 문서는 대회 심사 및 데모 시연을 위해 작성된 예시 약관입니다.
              </p>
              {modalType === "terms" ? (
                `제1조 (목적 및 서비스의 성격)
본 서비스(Financial Multi-Risk Guardian)는 DART 전자공시 및 공공 뉴스 데이터를 기반으로 기업의 잠재적 리스크 요인을 탐지·가공하여 요약 정보를 제공하는 보조 도구입니다.

제2조 (투자 판단에 관한 면책 조항)
1. 본 서비스가 제공하는 모든 점수(Safety Score), 리스크 지표 및 AI 생성 리포트는 단순 정보 제공 및 투자 참고용 자료이며, 특정 종목의 매수·매도를 추천하거나 보증하지 않습니다.
2. 금융투자상품의 가치 변동 및 최종 투자 결정에 따른 모든 책임과 손실은 투자자 본인에게 귀속되며, 본 서비스 및 개발진은 이에 대해 어떠한 법적 책임도 부담하지 않습니다.

제3조 (서비스의 변경 및 중단)
공공 데이터 제공처(DART 등)의 시스템 장애나 API 정책 변경에 따라 서비스의 일부 또는 전부가 사전 고지 없이 일시 중단될 수 있습니다.`
              ) : (
                `1. 수집 항목: 사용자 아이디, 활동 닉네임, 이메일 주소, 투자 경험 정보

2. 수집 및 이용 목적:
   - 회원 식별 및 계정 관리
   - 사용자가 등록한 관심 종목에 대한 긴급 공시(CB/BW 발행, 유상증자 등) 감지 시 실시간 이메일 알림 발송
   - 맞춤형 리스크 필터링 기준 제공

3. 보유 및 이용 기간: 회원 탈퇴 시까지 (회원 탈퇴 즉시 지체 없이 영구 파기)

4. 동의 거부권 안내:
귀하는 개인정보 수집·이용에 대한 동의를 거부할 권리가 있으나, 필수 항목 동의 거부 시 회원가입 및 공시 알림 서비스 이용이 제한됩니다.`
              )}
            </div>

            <button
              onClick={() => {
                if (modalType === "privacy") setAgreePrivacyAlert(true);
                setModalType(null);
              }}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm py-2.5 rounded-xl transition cursor-pointer"
            >
              내용을 확인하였으며 동의합니다
            </button>
          </div>
        </div>
      )}
    </div>
  );
}