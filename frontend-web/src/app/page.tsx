"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
import Link from "next/link";
import { 
  ShieldAlert, 
  Search, 
  X, 
  Plus, 
  Trash2, 
  RefreshCw, 
  Lock, 
  User, 
  ShieldCheck, 
  Users, 
  MessageSquareQuote, 
  Send, 
  Sparkles, 
  BellRing,
  AlertTriangle,
  Building2,
  CalendarClock,
  ExternalLink,
  FileText,
  Bot,
  Coins,
  Scale,
  TrendingDown,
  TrendingUp,
  Compass,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Camera,
  Upload,
  Check,
  Smile,
  Frown,
  Crown,
  CheckCircle2,
  ChevronRight,
  ArrowRightLeft,
  Clock,
  KeyRound
} from "lucide-react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer
} from "recharts";

const API_BASE = typeof window !== "undefined" ? "/api" : "http://localhost:8000/api";

// JWT Access Token 자동 주입 인터셉터
if (typeof window !== "undefined") {
  axios.interceptors.request.use((config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });
}

interface WatchItem {
  stock_name: string;
  score: number;
  status: string;
  current_price: string;
  change_str: string;
}

interface ToastInfo {
  message: string;
  type: "success" | "error" | "info";
}

export default function Home() {
  const [currentUser, setCurrentUser] = useState<string>("");
  const [currentNickname, setCurrentNickname] = useState<string>("");
  const [userRole, setUserRole] = useState<string>("user");
  const [isAuthOpen, setIsAuthOpen] = useState<boolean>(false);
  
  const [authId, setAuthId] = useState("");
  const [authPw, setAuthPw] = useState("");
  const [authMsg, setAuthMsg] = useState("");

  // 계정 찾기 모달 상태
  const [isAccountRecoveryOpen, setIsAccountRecoveryOpen] = useState(false);
  const [recoveryTab, setRecoveryTab] = useState<"findId" | "resetPw">("findId");
  const [recoveryEmail, setRecoveryEmail] = useState("");
  const [recoveryId, setRecoveryId] = useState("");
  const [recoveryNewPw, setRecoveryNewPw] = useState("");
  const [recoveryResultMsg, setRecoveryResultMsg] = useState<{ text: string; isError: boolean } | null>(null);

  const [isOnboarding, setIsOnboarding] = useState(false);
  const [socialProvider, setSocialProvider] = useState<"kakao" | "naver" | "google">("kakao");
  const [socialTempUsername, setSocialTempUsername] = useState("");
  const [socialNickname, setSocialNickname] = useState("");
  const [socialEmail, setSocialEmail] = useState("");
  const [socialExp, setSocialExp] = useState("beginner");
  const [agreePrivacyAlert, setAgreePrivacyAlert] = useState(true);
  const [agreeMarketing, setAgreeMarketing] = useState(false);

  const [modalType, setModalType] = useState<"terms" | "privacy" | null>(null);
  const [summaryModal, setSummaryModal] = useState<any>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [showDeepDive, setShowDeepDive] = useState<boolean>(false);

  const [isOcrModalOpen, setIsOcrModalOpen] = useState<boolean>(false);
  const [ocrLoading, setOcrLoading] = useState<boolean>(false);
  const [detectedStocks, setDetectedStocks] = useState<string[]>([]);
  const [selectedStocks, setSelectedStocks] = useState<string[]>([]);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<"analyze" | "watchlist" | "inquiry" | "admin">("analyze");

  const [searchStock, setSearchStock] = useState("삼성전자");
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [newStockName, setNewStockName] = useState("");
  const [addingStock, setAddingStock] = useState(false);

  const [toast, setToast] = useState<ToastInfo | null>(null);

  const showToast = (message: string, type: "success" | "error" | "info" = "info") => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 3000);
  };

  const [inqCategory, setInqCategory] = useState("기능 문의");
  const [inqContent, setInqContent] = useState("");
  const [inqSuccess, setInqSuccess] = useState("");

  const [adminUsers, setAdminUsers] = useState<any[]>([]);
  const [adminInquiries, setAdminInquiries] = useState<any[]>([]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("recent_searches");
      if (saved) {
        setRecentSearches(JSON.parse(saved));
      }
    } catch (e) {}
  }, []);

  useEffect(() => {
    if (currentUser) {
      fetchWatchlist(currentUser);
    } else {
      setWatchlist([]);
    }
  }, [currentUser]);

  const saveRecentSearch = (stock: string) => {
    const updated = [stock, ...recentSearches.filter(s => s !== stock)].slice(0, 5);
    setRecentSearches(updated);
    try {
      localStorage.setItem("recent_searches", JSON.stringify(updated));
    } catch (e) {}
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthMsg("");
    try {
      const res = await axios.post(`${API_BASE}/auth/login`, {
        username: authId,
        password: authPw
      });
      if (res.data.success) {
        if (res.data.token) {
          localStorage.setItem("access_token", res.data.token);
        }
        setCurrentUser(authId);
        setCurrentNickname(res.data.nickname || authId);
        setUserRole(res.data.role || "user");
        setIsAuthOpen(false);
        setAuthId("");
        setAuthPw("");
        showToast(`${res.data.nickname || authId}님 환영합니다!`, "success");
        fetchWatchlist(authId);
      }
    } catch (err: any) {
      setAuthMsg(err.response?.data?.detail || "아이디 또는 비밀번호가 올바르지 않습니다.");
    }
  };

  // 아이디 찾기 요청
  const handleFindId = async (e: React.FormEvent) => {
    e.preventDefault();
    setRecoveryResultMsg(null);
    try {
      const res = await axios.post(`${API_BASE}/auth/find-id`, { email: recoveryEmail });
      if (res.data.success) {
        setRecoveryResultMsg({
          text: `가입된 계정 아이디: ${res.data.masked_id}`,
          isError: false
        });
      } else {
        setRecoveryResultMsg({ text: res.data.message, isError: true });
      }
    } catch (err: any) {
      setRecoveryResultMsg({ text: "아이디 조회 중 오류가 발생했습니다.", isError: true });
    }
  };

  // 비밀번호 재설정 요청
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setRecoveryResultMsg(null);
    try {
      const res = await axios.post(`${API_BASE}/auth/reset-pw`, {
        username: recoveryId,
        email: recoveryEmail,
        new_password: recoveryNewPw
      });
      if (res.data.success) {
        setRecoveryResultMsg({ text: res.data.message, isError: false });
        setRecoveryNewPw("");
      } else {
        setRecoveryResultMsg({ text: res.data.message, isError: true });
      }
    } catch (err: any) {
      setRecoveryResultMsg({ text: "비밀번호 재설정 중 오류가 발생했습니다.", isError: true });
    }
  };

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
        if (res.data.token) {
          localStorage.setItem("access_token", res.data.token);
        }
        setCurrentUser(user.username);
        setCurrentNickname(user.nickname || user.username);
        setUserRole(user.role || "user");
        setIsAuthOpen(false);
        showToast(`${user.nickname || user.username}님 환영합니다!`, "success");
        fetchWatchlist(user.username);
      }
    } catch (err) {
      setAuthMsg("간편 로그인 처리 중 오류가 발생했습니다.");
    }
  };

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
        if (res.data.token) {
          localStorage.setItem("access_token", res.data.token);
        }
        setCurrentUser(socialTempUsername);
        setCurrentNickname(res.data.user.nickname);
        setUserRole("user");
        setIsOnboarding(false);
        setIsAuthOpen(false);
        showToast("회원 정보가 성공적으로 등록되었습니다.", "success");
        fetchWatchlist(socialTempUsername);
      }
    } catch (err: any) {
      setAuthMsg(err.response?.data?.detail || "온보딩 처리 실패");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    setCurrentUser("");
    setCurrentNickname("");
    setUserRole("user");
    setWatchlist([]);
    setActiveTab("analyze");
    showToast("로그아웃되었습니다. 검색 기능만 이용하실 수 있습니다.", "info");
  };

  const executeAnalysis = async (targetStock: string) => {
    if (!targetStock.trim()) return;
    setAnalyzing(true);
    try {
      const res = await axios.get(`${API_BASE}/analyze/${encodeURIComponent(targetStock.trim())}`);
      setAnalysisResult(res.data);
      setShowDeepDive(false);
      setSearchStock(targetStock.trim());
      saveRecentSearch(targetStock.trim());
      setActiveTab("analyze");
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.response?.data?.error || "종목 분석 중 오류가 발생했습니다.";
      showToast(errMsg, "error");
      setAnalysisResult(null);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAnalyze = () => {
    executeAnalysis(searchStock);
  };

  const fetchWatchlist = async (username: string) => {
    if (!username) {
      setWatchlist([]);
      return;
    }
    setWatchlistLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/watchlist?user_id=${encodeURIComponent(username)}`);
      setWatchlist(res.data.items || []);
    } catch (err) {
      console.error("관심 종목 로드 실패:", err);
    } finally {
      setWatchlistLoading(false);
    }
  };

  const handleAddWatchlist = async () => {
    if (!currentUser) {
      showToast("관심 종목 등록은 로그인이 필요합니다.", "info");
      setIsAuthOpen(true);
      return;
    }
    const cleanStock = newStockName.trim();
    if (!cleanStock) return;

    if (watchlist.some(item => item.stock_name.toLowerCase() === cleanStock.toLowerCase())) {
      showToast(`'${cleanStock}'은(는) 이미 등록된 관심 종목입니다.`, "info");
      return;
    }

    setAddingStock(true);
    try {
      const res = await axios.post(`${API_BASE}/watchlist/add`, {
        user_id: currentUser,
        stock_name: cleanStock
      });
      if (res.data.status === "SUCCESS" || res.data.success) {
        setNewStockName("");
        showToast(`'${cleanStock}'이(가) 관심 목록에 등록되었습니다.`, "success");
        await fetchWatchlist(currentUser);
      } else {
        showToast(res.data.message || "등록 실패", "error");
      }
    } catch (err: any) {
      showToast(err.response?.data?.message || "등록 중 오류가 발생했습니다.", "error");
    } finally {
      setAddingStock(false);
    }
  };

  const handleDeleteWatchlist = async (stockName: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!currentUser) return;

    try {
      await axios.post(`${API_BASE}/watchlist/remove`, {
        user_id: currentUser,
        stock_name: stockName
      });
      setWatchlist(prev => prev.filter(item => item.stock_name !== stockName));
      showToast(`'${stockName}'이(가) 삭제되었습니다.`, "info");
    } catch (err: any) {
      showToast(err.response?.data?.message || "삭제 실패", "error");
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => setPreviewImage(reader.result as string);
    reader.readAsDataURL(file);

    const formData = new FormData();
    formData.append("file", file);

    setOcrLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/watchlist/upload-screenshot`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      const stocks = res.data.detected_stocks || [];
      setDetectedStocks(stocks);
      setSelectedStocks(stocks);
    } catch (err) {
      showToast("이미지에서 종목을 인식하는 중 오류가 발생했습니다.", "error");
    } finally {
      setOcrLoading(false);
    }
  };

  const handleConfirmOcrBulkRegister = async () => {
    if (!currentUser) {
      setIsOcrModalOpen(false);
      setIsAuthOpen(true);
      showToast("종목 등록은 로그인이 필요합니다.", "info");
      return;
    }

    if (selectedStocks.length === 0) {
      showToast("등록할 종목을 1개 이상 선택해 주세요.", "info");
      return;
    }

    try {
      for (const s of selectedStocks) {
        await axios.post(`${API_BASE}/watchlist/add`, {
          user_id: currentUser,
          stock_name: s
        });
      }
      showToast(`${selectedStocks.length}개 종목이 성공적으로 등록되었습니다.`, "success");
      setIsOcrModalOpen(false);
      setDetectedStocks([]);
      setSelectedStocks([]);
      setPreviewImage(null);
      fetchWatchlist(currentUser);
    } catch (err) {
      showToast("일괄 등록 처리 중 오류가 발생했습니다.", "error");
    }
  };

  const handleOpenDisclosureSummary = async (disclosure: any) => {
    setSummaryLoading(true);
    setSummaryModal({
      report_nm: disclosure.report_nm,
      rcept_dt: disclosure.rcept_dt,
      url: disclosure.url,
      summary: null
    });
    try {
      const res = await axios.get(`${API_BASE}/disclosure/summary`, {
        params: {
          report_nm: disclosure.report_nm,
          rcept_no: disclosure.rcept_no || ""
        }
      });
      setSummaryModal((prev: any) => ({ ...prev, summary: res.data.summary || res.data }));
    } catch (err) {
      showToast("공시 요약 중 오류가 발생했습니다.", "error");
    } finally {
      setSummaryLoading(false);
    }
  };

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
      showToast("문의가 정상 접수되었습니다.", "success");
    } catch (err) {
      showToast("문의 접수 실패", "error");
    }
  };

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

  const getRiskScore = (key: string) => {
    if (!analysisResult || !analysisResult.radar_data) return 0;
    const item = analysisResult.radar_data.find((d: any) => d.theta === key);
    return item ? item.r : 0;
  };

  const safeCount = watchlist.filter(item => item.score >= 75).length;
  const cautionCount = watchlist.filter(item => item.score >= 45 && item.score < 75).length;
  const dangerCount = watchlist.filter(item => item.score < 45).length;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 relative">
      {/* 🔔 플로팅 토스트 알림 */}
      {toast && (
        <div className="fixed top-20 right-6 z-50 animate-in fade-in slide-in-from-top-3 duration-300">
          <div className={`px-4 py-3 rounded-2xl shadow-xl flex items-center gap-2.5 text-xs font-bold border backdrop-blur-md ${
            toast.type === "success" ? "bg-emerald-500/95 text-white border-emerald-400" :
            toast.type === "error" ? "bg-rose-500/95 text-white border-rose-400" :
            "bg-slate-800/95 text-white border-slate-700"
          }`}>
            {toast.type === "success" && <Check className="w-4 h-4" />}
            {toast.type === "error" && <AlertCircle className="w-4 h-4" />}
            {toast.type === "info" && <BellRing className="w-4 h-4" />}
            <span>{toast.message}</span>
          </div>
        </div>
      )}

      {/* 1. 상단 내비게이션 바 */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-500 text-white p-2 rounded-xl shadow-sm">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 leading-tight">Financial Multi-Risk Guardian</h1>
            <p className="text-xs text-slate-500">실시간 주가 · 스마트 캐시 하이브리드 진단 · DART 공시 지뢰 탐지</p>
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
            🔍 단일 종목 다차원 정밀 진단
          </button>
          <button
            onClick={() => {
              setActiveTab("watchlist");
              if (currentUser) fetchWatchlist(currentUser);
            }}
            className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
              activeTab === "watchlist"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-400 hover:text-slate-700"
            }`}
          >
            ⭐ 관심 종목 가디언 {currentUser && watchlist.length > 0 && `(${watchlist.length})`}
          </button>
          <button
            onClick={() => setActiveTab("inquiry")}
            className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
              activeTab === "inquiry"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-400 hover:text-slate-700"
            }`}
          >
            💬 사용자 피드백 & 문의
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

        {/* [탭 1: 단일 종목 다차원 정밀 진단] */}
        {activeTab === "analyze" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col gap-4">
                <h2 className="text-base font-bold text-slate-800">종목 리스크 스캔</h2>
                
                {/* 종목 검색창 */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={searchStock}
                    onChange={(e) => setSearchStock(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !analyzing) {
                        handleAnalyze();
                      }
                    }}
                    placeholder="예: 노루페인트, 한화, 카카오"
                    disabled={analyzing}
                    className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 disabled:bg-slate-100"
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

                {/* ⚡ 심사위원 원클릭 빠른 시연 프리셋 바 */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
                  <span className="text-[11px] text-slate-400 font-bold">⚡ 시연 프리셋:</span>
                  <button
                    type="button"
                    onClick={() => { setSearchStock("파두"); executeAnalysis("파두"); }}
                    disabled={analyzing}
                    className="px-2 py-0.5 rounded-md bg-rose-50 hover:bg-rose-100 text-rose-600 font-bold border border-rose-200 transition cursor-pointer text-[11px]"
                  >
                    🔴 고위험 (파두)
                  </button>
                  <button
                    type="button"
                    onClick={() => { setSearchStock("삼성전자"); executeAnalysis("삼성전자"); }}
                    disabled={analyzing}
                    className="px-2 py-0.5 rounded-md bg-emerald-50 hover:bg-emerald-100 text-emerald-600 font-bold border border-emerald-200 transition cursor-pointer text-[11px]"
                  >
                    🟢 클린 (삼성전자)
                  </button>
                  <button
                    type="button"
                    onClick={() => { setSearchStock("카카오"); executeAnalysis("카카오"); }}
                    disabled={analyzing}
                    className="px-2 py-0.5 rounded-md bg-amber-50 hover:bg-amber-100 text-amber-600 font-bold border border-amber-200 transition cursor-pointer text-[11px]"
                  >
                    🟡 주의 (카카오)
                  </button>
                </div>

                {recentSearches.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap pt-1">
                    <span className="text-[10px] text-slate-400 font-semibold flex items-center gap-0.5">
                      <Clock className="w-3 h-3" /> 최근:
                    </span>
                    {recentSearches.map((s, idx) => (
                      <button
                        key={idx}
                        onClick={() => executeAnalysis(s)}
                        disabled={analyzing}
                        className="text-[11px] bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium px-2 py-0.5 rounded-md transition cursor-pointer"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}

                <div className="bg-slate-50 p-4 rounded-xl text-xs text-slate-600 space-y-2 border border-slate-100">
                  <p className="font-bold text-slate-700">💡 3초 만에 끝내는 투자 판단:</p>
                  <p>• <b>스마트 캐시:</b> 공유 DB 캐시로 0.01초 초고속 조회</p>
                  <p>• <b>HF KR-FinBERT:</b> 공시·뉴스 감성 지표 분석</p>
                  <p>• <b>시나리오 예측:</b> Gemini AI 기반 3~6개월 전망</p>
                </div>
              </div>

              {analysisResult && (
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center animate-in fade-in duration-300">
                  <div className="w-full flex items-center justify-between mb-1">
                    <h4 className="text-xs font-bold text-slate-700">다차원 리스크 지형도 (Radar Map)</h4>
                    <span className="text-[10px] text-slate-400">외곽일수록 위험</span>
                  </div>
                  
                  <div className="w-full h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart 
                        data={analysisResult.radar_data} 
                        cx="50%" 
                        cy="50%" 
                        outerRadius="50%"
                        margin={{ top: 15, right: 45, bottom: 15, left: 45 }}
                      >
                        <PolarGrid stroke="#e2e8f0" />
                        <PolarAngleAxis 
                          dataKey="theta" 
                          tick={{ fill: "#334155", fontSize: 11, fontWeight: 700 }} 
                        />
                        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                        <Radar 
                          name="위험도" 
                          dataKey="r" 
                          stroke="#ef4444" 
                          fill="#ef4444" 
                          fillOpacity={0.35} 
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>

                  <p className="text-[11px] text-slate-400 text-center leading-tight">
                    5대 리스크 축의 수치가 중심(0)에 가까울수록 안전합니다.
                  </p>
                </div>
              )}
            </div>

            <div className="md:col-span-2 space-y-6">
              {analysisResult ? (
                <>
                  {analysisResult.forecast_scenario && (
                    <div className={`p-6 rounded-2xl border shadow-sm transition ${
                      analysisResult.forecast_scenario.traffic_light === "RED" ? "bg-rose-50/70 border-rose-200" :
                      analysisResult.forecast_scenario.traffic_light === "YELLOW" ? "bg-amber-50/70 border-amber-200" : "bg-emerald-50/70 border-emerald-200"
                    }`}>
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-4 border-b border-black/5">
                        <div className="flex items-start gap-3">
                          <span className={`text-sm font-black px-3.5 py-1.5 rounded-xl shadow-xs shrink-0 mt-0.5 ${
                            analysisResult.forecast_scenario.traffic_light === "RED" ? "bg-rose-600 text-white" :
                            analysisResult.forecast_scenario.traffic_light === "YELLOW" ? "bg-amber-500 text-white" : "bg-emerald-600 text-white"
                          }`}>
                            {analysisResult.forecast_scenario.verdict_badge}
                          </span>
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <h3 className="text-xl font-black text-slate-900">
                                {analysisResult.price_info?.display_name || analysisResult.stock_name}
                              </h3>
                              <span className="text-[11px] font-mono bg-slate-200/80 text-slate-700 px-2 py-0.5 rounded-md font-bold">
                                {analysisResult.price_info?.code || "KRX"}
                              </span>
                              {analysisResult.price_info?.has_preferred_family && (
                                <span className="text-[10px] font-bold bg-purple-100 text-purple-700 px-2 py-0.5 rounded-md flex items-center gap-0.5">
                                  <Crown className="w-3 h-3 text-purple-600" /> 우선주 패밀리 보유사
                                </span>
                              )}
                            </div>

                            {analysisResult.price_info?.has_price && (
                              <div className="flex items-center gap-2 mt-1.5 text-xs">
                                <span className="font-extrabold text-base text-slate-900">
                                  {analysisResult.price_info.current_price}
                                </span>
                                <span className={`font-bold flex items-center gap-0.5 ${
                                  analysisResult.price_info.is_up ? "text-rose-600" :
                                  analysisResult.price_info.is_down ? "text-blue-600" : "text-slate-600"
                                }`}>
                                  {analysisResult.price_info.is_up ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                                  {analysisResult.price_info.change_str}
                                </span>
                                <span className="text-[10px] text-slate-400">({analysisResult.price_info.market_status})</span>
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className="text-[11px] text-slate-500 block font-medium">안전도 점수</span>
                          <span className={`text-3xl font-black ${
                            analysisResult.score_info.score >= 75 ? "text-emerald-600" :
                            analysisResult.score_info.score >= 45 ? "text-amber-600" : "text-rose-600"
                          }`}>
                            {analysisResult.score_info.score}<span className="text-sm font-normal text-slate-400">/100</span>
                          </span>
                        </div>
                      </div>

                      <div className="space-y-2 text-sm text-slate-800 leading-relaxed font-medium">
                        <p className="flex items-start gap-2">
                          <AlertCircle className={`w-4 h-4 shrink-0 mt-1 ${
                            analysisResult.forecast_scenario.traffic_light === "RED" ? "text-rose-600" :
                            analysisResult.forecast_scenario.traffic_light === "YELLOW" ? "text-amber-600" : "text-emerald-600"
                          }`} />
                          <span><b>현 상황 요약:</b> {analysisResult.forecast_scenario.verdict_summary}</span>
                        </p>
                        <p className="flex items-start gap-2 bg-white/80 p-3 rounded-xl border border-black/5">
                          <Compass className="w-4 h-4 shrink-0 mt-0.5 text-slate-700" />
                          <span><b>👉 행동 지침:</b> {analysisResult.forecast_scenario.action_call}</span>
                        </p>
                      </div>
                    </div>
                  )}

                  {/* 우선주 비교 캐러셀 */}
                  {analysisResult.price_info?.has_preferred_family && analysisResult.price_info?.related_pref_stocks?.length > 0 && (
                    <div className="bg-gradient-to-br from-indigo-50/90 via-purple-50/70 to-slate-50 border border-purple-200 p-6 rounded-2xl shadow-sm space-y-4 animate-in fade-in duration-300">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-purple-100">
                        <div className="flex items-center gap-2.5">
                          <div className="p-2 bg-purple-600 text-white rounded-xl shadow-xs">
                            <Crown className="w-4 h-4" />
                          </div>
                          <div>
                            <h4 className="text-sm font-black text-slate-900">
                              👑 {analysisResult.price_info.common_name} 우선주 패밀리 실시간 비교
                            </h4>
                            <p className="text-[11px] text-purple-700">
                              보통주 기준가 <b>{analysisResult.price_info.common_price}</b> 대비 우선주별 가격 및 할인율(괴리율)
                            </p>
                          </div>
                        </div>

                        <span className="text-[11px] font-bold bg-purple-100 text-purple-800 px-2.5 py-1 rounded-full self-start sm:self-auto flex items-center gap-1">
                          <ArrowRightLeft className="w-3 h-3" /> 총 {analysisResult.price_info.related_pref_stocks.length}개 우선주 발행
                        </span>
                      </div>

                      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-purple-200 scrollbar-track-transparent">
                        {analysisResult.price_info.related_pref_stocks.map((p: any, idx: number) => (
                          <div 
                            key={idx} 
                            className="min-w-[280px] max-w-[320px] bg-white p-4 rounded-2xl border border-purple-100 shadow-xs flex flex-col justify-between hover:border-purple-300 transition shrink-0"
                          >
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-xs font-black text-slate-900">{p.name}</span>
                                  <span className="text-[10px] font-mono text-slate-400">({p.code})</span>
                                </div>
                                <span className="text-[10px] font-bold bg-purple-50 text-purple-700 px-2 py-0.5 rounded-md border border-purple-100">
                                  {p.type}
                                </span>
                              </div>

                              <div className="flex items-baseline justify-between mb-3 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                                <div>
                                  <span className="text-[10px] text-slate-400 block font-medium">우선주 시세</span>
                                  <span className="text-base font-extrabold text-slate-900">{p.price}</span>
                                </div>
                                <span className={`text-xs font-bold ${p.is_up ? "text-rose-600" : p.is_down ? "text-blue-600" : "text-slate-500"}`}>
                                  {p.change_str}
                                </span>
                              </div>
                            </div>

                            <div className="pt-2 border-t border-slate-100 space-y-2">
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-slate-500 font-medium">보통주 대비 할인율:</span>
                                <span className="font-extrabold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md border border-purple-200">
                                  {p.discount_rate_str}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-500 flex items-center gap-1">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                                <span>{p.dividend_benefit}</span>
                              </p>

                              <button
                                onClick={() => executeAnalysis(p.name)}
                                className="w-full bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-bold py-2 rounded-xl transition flex items-center justify-center gap-1 mt-1 cursor-pointer"
                              >
                                <span>{p.name} 정밀 진단하기</span>
                                <ChevronRight className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="text-[11px] text-slate-500 bg-white/80 p-3 rounded-xl border border-purple-100 flex items-center justify-between">
                        <span>💡 우선주는 의결권이 없는 대신 <b>높은 배당수익률과 가격 할인 혜택</b>이 주어집니다.</span>
                        <span className="text-purple-600 font-bold hidden sm:inline">장기 배당 투자에 유리</span>
                      </div>
                    </div>
                  )}

                  {/* 감성 분석 카드 */}
                  {analysisResult.sentiment_data && (
                    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-base">🤗</span>
                          <h4 className="font-bold text-xs text-slate-900">
                            KR-FinBERT 공시·뉴스 여론 감성 지표
                          </h4>
                        </div>
                        <span className="text-xs font-bold text-slate-700">
                          {analysisResult.sentiment_data.sentiment_status}
                        </span>
                      </div>

                      <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden flex mb-3">
                        <div 
                          style={{ width: `${analysisResult.sentiment_data.positive_pct}%` }} 
                          className="bg-emerald-500 transition-all duration-500" 
                          title={`긍정 ${analysisResult.sentiment_data.positive_pct}%`}
                        />
                        <div 
                          style={{ width: `${analysisResult.sentiment_data.neutral_pct}%` }} 
                          className="bg-slate-300 transition-all duration-500" 
                          title={`중립 ${analysisResult.sentiment_data.neutral_pct}%`}
                        />
                        <div 
                          style={{ width: `${analysisResult.sentiment_data.negative_pct}%` }} 
                          className="bg-rose-500 transition-all duration-500" 
                          title={`부정 ${analysisResult.sentiment_data.negative_pct}%`}
                        />
                      </div>

                      <div className="flex justify-between items-center text-xs font-semibold text-slate-600">
                        <span className="flex items-center gap-1 text-emerald-600">
                          <Smile className="w-3.5 h-3.5" /> 긍정 {analysisResult.sentiment_data.positive_pct}%
                        </span>
                        <span className="text-slate-400">
                          중립 {analysisResult.sentiment_data.neutral_pct}%
                        </span>
                        <span className="flex items-center gap-1 text-rose-500">
                          <Frown className="w-3.5 h-3.5" /> 부정 {analysisResult.sentiment_data.negative_pct}%
                        </span>
                      </div>
                    </div>
                  )}

                  {/* 시나리오 카드 */}
                  {analysisResult.forecast_scenario?.scenarios && (
                    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <TrendingDown className="w-5 h-5 text-indigo-600" />
                          <h4 className="font-bold text-sm text-slate-900">향후 3~6개월 주가 리스크 시나리오 예측</h4>
                        </div>
                        <span className="text-xs text-slate-400 font-medium">D-Day 일정 및 재무 실적 연동</span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {analysisResult.forecast_scenario.scenarios.map((sc: any, idx: number) => (
                          <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 flex flex-col justify-between">
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-[11px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md">
                                  {sc.period}
                                </span>
                                <span className="text-[10px] text-slate-400 font-mono">발생확률 {sc.prob}</span>
                              </div>
                              <h5 className="font-bold text-xs text-slate-900 mb-2">{sc.trend}</h5>
                              <p className="text-xs text-slate-600 leading-relaxed">{sc.desc}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 3대 리스크 카드 */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className={`w-4 h-4 ${getRiskScore("상장유지 위험") > 0 ? "text-rose-500" : "text-emerald-500"}`} />
                        <h5 className="font-bold text-xs text-slate-800">상장유지 적격성</h5>
                      </div>
                      <div className="space-y-1">
                        <p className={`text-lg font-black ${getRiskScore("상장유지 위험") > 0 ? "text-rose-600" : "text-emerald-600"}`}>
                          {getRiskScore("상장유지 위험") > 0 ? "주의 필요" : "정상 (적격)"}
                        </p>
                        <p className="text-[11px] text-slate-500 leading-tight">
                          {getRiskScore("상장유지 위험") > 0 ? "감사의견·자본잠식 징후 탐지" : "감사의견 적정 및 관리종목 요건 없음"}
                        </p>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
                      <div className="flex items-center gap-2 mb-2">
                        <Building2 className={`w-4 h-4 ${getRiskScore("내부자 지분변동") > 0 ? "text-amber-500" : "text-emerald-500"}`} />
                        <h5 className="font-bold text-xs text-slate-800">지배구조 및 내부자 지분</h5>
                      </div>
                      <div className="space-y-1">
                        <p className={`text-lg font-black ${getRiskScore("내부자 지분변동") > 0 ? "text-amber-600" : "text-emerald-600"}`}>
                          {getRiskScore("내부자 지분변동") > 0 ? "지분 변동 감지" : "지분 안정적"}
                        </p>
                        <p className="text-[11px] text-slate-500 leading-tight">
                          {getRiskScore("내부자 지분변동") > 0 ? "최대주주·임원 매도/경영권 변동 이력" : "주요 경영진 지분 이탈 없음"}
                        </p>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
                      <div className="flex items-center gap-2 mb-2">
                        <CalendarClock className={`w-4 h-4 ${getRiskScore("잠재물량 부담") > 0 ? "text-rose-500" : "text-emerald-500"}`} />
                        <h5 className="font-bold text-xs text-slate-800">잠재 출회물량 (오버행)</h5>
                      </div>
                      <div className="space-y-1">
                        <p className={`text-lg font-black ${getRiskScore("잠재물량 부담") > 0 ? "text-rose-600" : "text-emerald-600"}`}>
                          {getRiskScore("잠재물량 부담") > 0 ? "출회 부담 존재" : "부담 미미"}
                        </p>
                        <p className="text-[11px] text-slate-500 leading-tight">
                          {getRiskScore("잠재물량 부담") > 0 ? "전환사채(CB) 및 보호예수 일정" : "단기 대규모 신주 전환 일정 없음"}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* 심층 분석 아코디언 */}
                  <div className="pt-2">
                    <button
                      onClick={() => setShowDeepDive(!showDeepDive)}
                      className="w-full bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 font-bold text-xs py-3 px-4 rounded-2xl transition flex items-center justify-center gap-2 shadow-xs cursor-pointer"
                    >
                      {showDeepDive ? (
                        <>
                          <span>심층 분석 데이터 및 DART 공시 접기</span>
                          <ChevronUp className="w-4 h-4 text-slate-500" />
                        </>
                      ) : (
                        <>
                          <span>🔍 3개년 재무표 · 미상환 사채 잔액 · AI 소견서 및 DART 공시 원문 자세히 보기</span>
                          <ChevronDown className="w-4 h-4 text-emerald-600" />
                        </>
                      )}
                    </button>
                  </div>

                  {showDeepDive && (
                    <div className="space-y-6 pt-2 animate-in fade-in slide-in-from-top-4 duration-200">
                      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                        <h4 className="text-xs font-bold text-slate-500 mb-3">AI 정밀 금융 리스크 소견서</h4>
                        <div className="text-sm text-slate-700 whitespace-pre-line leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100 font-sans">
                          {analysisResult.report_text}
                        </div>
                      </div>

                      {analysisResult.cb_dilution && (
                        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                              <Scale className="w-5 h-5 text-purple-600" />
                              <h4 className="font-bold text-sm text-slate-900">미상환 사채(CB/BW) 잔액 및 시총 대비 잠재 희석률</h4>
                            </div>
                            <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                              analysisResult.cb_dilution.dilution_ratio >= 15 ? "bg-rose-100 text-rose-700" :
                              analysisResult.cb_dilution.dilution_ratio > 0 ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
                            }`}>
                              {analysisResult.cb_dilution.dilution_ratio_str}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                              <span className="text-[10px] text-slate-400 block font-medium">미상환 권면총액</span>
                              <span className="text-xs font-black text-slate-800">{analysisResult.cb_dilution.total_unredeemed_amount}</span>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                              <span className="text-[10px] text-slate-400 block font-medium">시가총액 대비 비중</span>
                              <span className={`text-xs font-black ${
                                analysisResult.cb_dilution.dilution_ratio >= 15 ? "text-rose-600" : "text-slate-800"
                              }`}>
                                {analysisResult.cb_dilution.market_cap}
                              </span>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                              <span className="text-[10px] text-slate-400 block font-medium">전환가능 주식 수</span>
                              <span className="text-xs font-black text-slate-800">{analysisResult.cb_dilution.total_potential_shares}</span>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                              <span className="text-[10px] text-slate-400 block font-medium">발행주식 대비 잠재비율</span>
                              <span className={`text-xs font-black ${
                                analysisResult.cb_dilution.dilution_ratio >= 15 ? "text-rose-600" : "text-emerald-600"
                              }`}>
                                {analysisResult.cb_dilution.shares_ratio}
                              </span>
                            </div>
                          </div>
                        </div>
                      )}

                      {analysisResult.financial_health && (
                        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                              <Coins className="w-5 h-5 text-emerald-600" />
                              <h4 className="font-bold text-sm text-slate-900">3개년 재무 생존력 & 자본잠식 진단</h4>
                            </div>
                            <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                              analysisResult.financial_health.is_impaired || analysisResult.financial_health.consecutive_loss_years >= 2
                                ? "bg-rose-100 text-rose-700"
                                : "bg-emerald-100 text-emerald-700"
                            }`}>
                              {analysisResult.financial_health.impairment_ratio_str}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                              <span className="text-[10px] text-slate-400 block font-medium">자본금</span>
                              <span className="text-xs font-black text-slate-800">{analysisResult.financial_health.capital}</span>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                              <span className="text-[10px] text-slate-400 block font-medium">자본총계</span>
                              <span className="text-xs font-black text-slate-800">{analysisResult.financial_health.total_equity}</span>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                              <span className="text-[10px] text-slate-400 block font-medium">자본잠식률</span>
                              <span className={`text-xs font-black ${
                                analysisResult.financial_health.impairment_ratio >= 50 ? "text-rose-600" :
                                analysisResult.financial_health.impairment_ratio > 0 ? "text-amber-600" : "text-emerald-600"
                              }`}>
                                {analysisResult.financial_health.impairment_ratio}%
                              </span>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                              <span className="text-[10px] text-slate-400 block font-medium">연속 영업손실</span>
                              <span className={`text-xs font-black ${
                                analysisResult.financial_health.consecutive_loss_years >= 2 ? "text-rose-600" : "text-emerald-600"
                              }`}>
                                {analysisResult.financial_health.consecutive_loss_years}년 연속 적자
                              </span>
                            </div>
                          </div>
                        </div>
                      )}

                      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-emerald-600" />
                            <h4 className="font-bold text-sm text-slate-900">DART 실시간 전자공시 원문 목록</h4>
                          </div>
                          <span className="text-xs text-slate-400 font-medium">
                            최근 수집 {analysisResult.raw_disclosures?.length || 0}건
                          </span>
                        </div>

                        <table className="w-full text-left text-sm">
                          <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-medium">
                            <tr>
                              <th className="px-6 py-3">공시 보고서명</th>
                              <th className="px-6 py-3">제출인</th>
                              <th className="px-6 py-3">접수일자</th>
                              <th className="px-6 py-3 text-right">AI 해설 / 원문</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 text-xs">
                            {analysisResult.raw_disclosures && analysisResult.raw_disclosures.length > 0 ? (
                              analysisResult.raw_disclosures.map((d: any, idx: number) => (
                                <tr key={idx} className="hover:bg-slate-50/50">
                                  <td className="px-6 py-3 font-semibold text-slate-900">
                                    {d.report_nm}
                                  </td>
                                  <td className="px-6 py-3 text-slate-500">{d.flr_nm || "-"}</td>
                                  <td className="px-6 py-3 text-slate-400 font-mono">{d.rcept_dt}</td>
                                  <td className="px-6 py-3 text-right space-x-2">
                                    <button
                                      onClick={() => handleOpenDisclosureSummary(d)}
                                      className="inline-flex items-center gap-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-bold px-2.5 py-1 rounded-md transition text-[11px] cursor-pointer"
                                    >
                                      <Bot className="w-3 h-3" /> AI 요약
                                    </button>
                                    <a
                                      href={d.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-0.5 text-slate-400 hover:text-slate-700 font-semibold text-[11px] hover:underline"
                                    >
                                      원문 <ExternalLink className="w-3.5 h-3.5" />
                                    </a>
                                  </td>
                                </tr>
                              ))
                            ) : (
                              <tr>
                                <td colSpan={4} className="text-center py-6 text-slate-400 text-xs">
                                  최근 접수된 공시 내역이 없습니다.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="bg-white p-12 rounded-2xl border border-dashed border-slate-200 text-center text-slate-400">
                  <Search className="w-10 h-10 mx-auto mb-3 text-slate-300" />
                  <p>종목명을 입력하고 스캔 버튼을 누르거나 위의 시연 프리셋을 클릭하세요.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* [탭 2: 관심 종목 가디언] */}
        {activeTab === "watchlist" && (
          <div className="space-y-6">
            {!currentUser ? (
              <div className="bg-white p-16 rounded-3xl border border-slate-200 shadow-sm text-center max-w-xl mx-auto my-8">
                <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Lock className="w-8 h-8" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-2">로그인이 필요한 서비스입니다</h3>
                <p className="text-sm text-slate-500 mb-6 leading-relaxed">
                  로그인하시면 나만의 관심/보유 종목을 등록하고<br />
                  상장폐지, 지배구조 변동, 메자닌 사채 희석 리스크를 실시간 관제할 수 있습니다.
                </p>
                <button
                  onClick={() => {
                    setIsOnboarding(false);
                    setIsAuthOpen(true);
                  }}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold px-8 py-3 rounded-xl shadow-sm transition cursor-pointer"
                >
                  로그인 / 간편가입
                </button>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                  <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-400">총 보유/관심 종목</p>
                      <p className="text-2xl font-black text-slate-800 mt-1">{watchlist.length}개</p>
                    </div>
                    <div className="p-3 bg-slate-100 rounded-xl text-slate-600">
                      <Coins className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="bg-emerald-50/60 border border-emerald-200 rounded-2xl p-4 shadow-sm flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-emerald-600">정상 / 안전 (75점↑)</p>
                      <p className="text-2xl font-black text-emerald-700 mt-1">{safeCount}개</p>
                    </div>
                    <div className="p-3 bg-emerald-100 rounded-xl text-emerald-600">
                      <ShieldCheck className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="bg-amber-50/60 border border-amber-200 rounded-2xl p-4 shadow-sm flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-amber-600">주의 관찰 (45~74점)</p>
                      <p className="text-2xl font-black text-amber-700 mt-1">{cautionCount}개</p>
                    </div>
                    <div className="p-3 bg-amber-100 rounded-xl text-amber-600">
                      <AlertCircle className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="bg-rose-50/60 border border-rose-200 rounded-2xl p-4 shadow-sm flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-rose-600">고위험 경보 (45점↓)</p>
                      <p className="text-2xl font-black text-rose-700 mt-1">{dangerCount}개</p>
                    </div>
                    <div className="p-3 bg-rose-100 rounded-xl text-rose-600">
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-800">포트폴리오 리스크 관제 센터</h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      등록된 종목은 공시 변동이 없는 한 로컬 SQLite 캐시로 <b>0.01초</b> 만에 안전도를 출력합니다.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 w-full md:w-auto">
                    <input
                      type="text"
                      placeholder="종목명 (예: 카카오, 셀트리온)"
                      value={newStockName}
                      onChange={(e) => setNewStockName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !addingStock) {
                          handleAddWatchlist();
                        }
                      }}
                      className="px-3 py-2 text-sm border border-slate-300 rounded-xl focus:outline-none focus:border-emerald-500 w-full sm:w-56"
                    />
                    <button
                      onClick={handleAddWatchlist}
                      disabled={addingStock || !newStockName.trim()}
                      className="bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition flex items-center gap-1 shrink-0 cursor-pointer"
                    >
                      <Plus className="w-4 h-4" /> {addingStock ? "등록 중..." : "종목 추가"}
                    </button>
                    <button
                      onClick={() => setIsOcrModalOpen(true)}
                      className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold px-3 py-2.5 rounded-xl transition flex items-center gap-1 shrink-0 cursor-pointer"
                      title="MTS 캡처 이미지로 종목 일괄 추가"
                    >
                      <Camera className="w-4 h-4 text-emerald-600" /> 스크린샷 OCR
                    </button>
                    <button
                      onClick={() => fetchWatchlist(currentUser)}
                      disabled={watchlistLoading}
                      className="p-2.5 text-slate-400 hover:text-slate-700 rounded-xl hover:bg-slate-100 transition cursor-pointer"
                      title="새로고침"
                    >
                      <RefreshCw className={`w-4 h-4 ${watchlistLoading ? "animate-spin text-emerald-600" : ""}`} />
                    </button>
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                    <h4 className="font-bold text-slate-800 text-sm">
                      내 관심 종목 ({watchlist.length}개)
                    </h4>
                    <span className="text-xs text-slate-400">
                      종목을 클릭하면 정밀 진단 탭으로 즉시 이동합니다.
                    </span>
                  </div>

                  {watchlistLoading ? (
                    <div className="py-16 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
                      <RefreshCw className="w-5 h-5 animate-spin text-emerald-600" />
                      <span>포트폴리오 리스크를 진단하고 있습니다...</span>
                    </div>
                  ) : watchlist.length === 0 ? (
                    <div className="py-16 text-center text-slate-400 text-sm">
                      등록된 관심 종목이 없습니다. 상단에서 관심 있는 기업을 추가해 보세요.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-medium">
                          <tr>
                            <th className="px-6 py-3.5">종목명</th>
                            <th className="px-6 py-3.5">현재가 (등락률)</th>
                            <th className="px-6 py-3.5">안전 점수</th>
                            <th className="px-6 py-3.5 text-center">리스크 상태</th>
                            <th className="px-6 py-3.5 text-right">관리</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-xs">
                          {watchlist.map((item) => (
                            <tr
                              key={item.stock_name}
                              onClick={() => executeAnalysis(item.stock_name)}
                              className="hover:bg-slate-50/70 transition cursor-pointer group"
                            >
                              <td className="px-6 py-4 font-black text-slate-900 text-sm flex items-center gap-2">
                                <span>{item.stock_name}</span>
                                <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-emerald-600 transition" />
                              </td>
                              <td className="px-6 py-4 font-mono font-bold text-slate-800">
                                <span>{item.current_price}</span>
                                {item.change_str && (
                                  <span className={`ml-2 text-[11px] ${
                                    item.change_str.includes("+")
                                      ? "text-rose-600 font-bold"
                                      : item.change_str.includes("-")
                                      ? "text-blue-600 font-bold"
                                      : "text-slate-400"
                                  }`}>
                                    {item.change_str}
                                  </span>
                                )}
                              </td>
                              <td className="px-6 py-4">
                                <div className="flex items-center gap-3">
                                  <div className="w-28 bg-slate-100 h-2 rounded-full overflow-hidden">
                                    <div
                                      className={`h-full rounded-full transition-all duration-500 ${
                                        item.score >= 75
                                          ? "bg-emerald-500"
                                          : item.score >= 45
                                          ? "bg-amber-500"
                                          : "bg-rose-500"
                                      }`}
                                      style={{ width: `${Math.min(100, Math.max(0, item.score))}%` }}
                                    />
                                  </div>
                                  <span className="font-black text-slate-700 text-xs">{item.score}점</span>
                                </div>
                              </td>
                              <td className="px-6 py-4 text-center">
                                <span className={`px-2.5 py-1 text-xs font-bold rounded-full ${
                                  item.score >= 75
                                    ? "bg-emerald-100 text-emerald-700"
                                    : item.score >= 45
                                    ? "bg-amber-100 text-amber-700"
                                    : "bg-rose-100 text-rose-700 animate-pulse"
                                }`}>
                                  {item.status || (item.score >= 75 ? "정상" : item.score >= 45 ? "주의" : "위험")}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-right">
                                <button
                                  onClick={(e) => handleDeleteWatchlist(item.stock_name, e)}
                                  className="text-slate-300 hover:text-rose-500 transition p-1 cursor-pointer"
                                  title="관심 종목 삭제"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
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

      {/* 📸 OCR 모달 */}
      {isOcrModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-3xl p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={() => {
                setIsOcrModalOpen(false);
                setDetectedStocks([]);
                setSelectedStocks([]);
                setPreviewImage(null);
              }}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-2.5 rounded-2xl bg-emerald-50 text-emerald-600">
                <Camera className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">증권사 스크린샷 OCR 자동 등록</h3>
                <p className="text-xs text-slate-500">MTS 잔고나 관심종목 화면 캡처 이미지를 올려주세요.</p>
              </div>
            </div>

            <div className="mb-4">
              <label className="border-2 border-dashed border-slate-200 hover:border-emerald-500 bg-slate-50/50 hover:bg-emerald-50/30 transition rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer block text-center">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden"
                />
                <Upload className="w-7 h-7 text-emerald-600 mb-2" />
                <span className="text-xs font-bold text-slate-700 block">
                  {previewImage ? "다른 이미지로 변경하기" : "스크린샷 이미지 파일 선택 또는 드래그"}
                </span>
                <span className="text-[10px] text-slate-400 mt-0.5">JPG, PNG 파일 지원</span>
              </label>
            </div>

            {ocrLoading && (
              <div className="py-8 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                <RefreshCw className="w-6 h-6 animate-spin text-emerald-600" />
                <span className="font-bold">AI가 이미지 속 종목명을 읽고 DART 상장사를 검증 중입니다...</span>
              </div>
            )}

            {!ocrLoading && detectedStocks.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-800">
                    인식 완료: <b className="text-emerald-600">{detectedStocks.length}개</b> 종목 탐지
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      if (selectedStocks.length === detectedStocks.length) setSelectedStocks([]);
                      else setSelectedStocks(detectedStocks);
                    }}
                    className="text-[11px] text-slate-500 hover:text-emerald-600 font-semibold cursor-pointer"
                  >
                    {selectedStocks.length === detectedStocks.length ? "전체 해제" : "전체 선택"}
                  </button>
                </div>

                <div className="max-h-48 overflow-y-auto bg-slate-50 p-3 rounded-2xl border border-slate-100 grid grid-cols-2 gap-2 text-xs">
                  {detectedStocks.map((stock, idx) => (
                    <label
                      key={idx}
                      className={`flex items-center gap-2 p-2 rounded-xl border transition cursor-pointer ${
                        selectedStocks.includes(stock)
                          ? "bg-emerald-50 border-emerald-300 text-emerald-900 font-bold"
                          : "bg-white border-slate-200 text-slate-600"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedStocks.includes(stock)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedStocks([...selectedStocks, stock]);
                          else setSelectedStocks(selectedStocks.filter(s => s !== stock));
                        }}
                        className="rounded text-emerald-600 focus:ring-emerald-500 w-3.5 h-3.5"
                      />
                      <span className="truncate">{stock}</span>
                    </label>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={handleConfirmOcrBulkRegister}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm py-3 rounded-xl transition shadow-sm flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Check className="w-4 h-4" /> 선택한 {selectedStocks.length}개 종목 일괄 등록하기
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. 로그인 모달 */}
      {isAuthOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-sm rounded-3xl p-8 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={() => setIsAuthOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            {isOnboarding ? (
              <div>
                <div className="text-center mb-5">
                  <div className="inline-flex p-2.5 rounded-2xl bg-emerald-50 text-emerald-600 mb-2">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-black text-slate-900">추가 정보 입력</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    맞춤형 공시 리스크 진단 및 알림을 위해 정보를 확인해 주세요
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
                        <BellRing className="w-3 h-3" /> 주요 공시 알림용
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
                          <b className="text-emerald-700">[필수]</b> 개인정보 수집 및 긴급 공시 알림 제공 동의
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

                {/* 🔗 [신규] 아이디/비밀번호 찾기 & 회원가입 버튼 영역 */}
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                  <button
                    type="button"
                    onClick={() => {
                      setIsAuthOpen(false);
                      setRecoveryResultMsg(null);
                      setIsAccountRecoveryOpen(true);
                    }}
                    className="hover:text-slate-800 transition cursor-pointer flex items-center gap-1"
                  >
                    <KeyRound className="w-3.5 h-3.5 text-slate-400" />
                    아이디 / 비밀번호 찾기
                  </button>
                  <Link
                    href="/register"
                    onClick={() => setIsAuthOpen(false)}
                    className="text-emerald-600 font-bold hover:underline"
                  >
                    일반 회원가입
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 🔑 [신규] 아이디 / 비밀번호 찾기 모달 */}
      {isAccountRecoveryOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-sm rounded-3xl p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={() => {
                setIsAccountRecoveryOpen(false);
                setRecoveryResultMsg(null);
              }}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 rounded-xl bg-slate-100 text-slate-700">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">계정 정보 찾기</h3>
                <p className="text-xs text-slate-500">가입 시 등록한 정보로 확인합니다.</p>
              </div>
            </div>

            {/* 탭 버튼 */}
            <div className="flex border-b border-slate-200 mb-4 text-xs font-bold">
              <button
                type="button"
                onClick={() => {
                  setRecoveryTab("findId");
                  setRecoveryResultMsg(null);
                }}
                className={`flex-1 py-2 text-center border-b-2 transition ${
                  recoveryTab === "findId"
                    ? "border-emerald-600 text-emerald-600"
                    : "border-transparent text-slate-400 hover:text-slate-600"
                }`}
              >
                아이디 찾기
              </button>
              <button
                type="button"
                onClick={() => {
                  setRecoveryTab("resetPw");
                  setRecoveryResultMsg(null);
                }}
                className={`flex-1 py-2 text-center border-b-2 transition ${
                  recoveryTab === "resetPw"
                    ? "border-emerald-600 text-emerald-600"
                    : "border-transparent text-slate-400 hover:text-slate-600"
                }`}
              >
                비밀번호 재설정
              </button>
            </div>

            {recoveryTab === "findId" ? (
              <form onSubmit={handleFindId} className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    가입 이메일 주소
                  </label>
                  <input
                    type="email"
                    value={recoveryEmail}
                    onChange={(e) => setRecoveryEmail(e.target.value)}
                    placeholder="example@domain.com"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs py-2.5 rounded-xl transition cursor-pointer"
                >
                  아이디 확인
                </button>
              </form>
            ) : (
              <form onSubmit={handleResetPassword} className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    아이디
                  </label>
                  <input
                    type="text"
                    value={recoveryId}
                    onChange={(e) => setRecoveryId(e.target.value)}
                    placeholder="가입한 아이디 입력"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    가입 이메일 주소
                  </label>
                  <input
                    type="email"
                    value={recoveryEmail}
                    onChange={(e) => setRecoveryEmail(e.target.value)}
                    placeholder="example@domain.com"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    새 비밀번호
                  </label>
                  <input
                    type="password"
                    value={recoveryNewPw}
                    onChange={(e) => setRecoveryNewPw(e.target.value)}
                    placeholder="새로운 비밀번호 입력"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs py-2.5 rounded-xl transition cursor-pointer"
                >
                  비밀번호 변경하기
                </button>
              </form>
            )}

            {recoveryResultMsg && (
              <div className={`mt-3 p-3 rounded-xl text-xs text-center font-medium ${
                recoveryResultMsg.isError ? "bg-rose-50 text-rose-600 border border-rose-100" : "bg-emerald-50 text-emerald-700 border border-emerald-100"
              }`}>
                {recoveryResultMsg.text}
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-slate-100 text-center">
              <button
                type="button"
                onClick={() => {
                  setIsAccountRecoveryOpen(false);
                  setIsAuthOpen(true);
                }}
                className="text-xs text-slate-500 hover:text-slate-800 underline cursor-pointer"
              >
                로그인 화면으로 돌아가기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. DART 공시 AI 요약 팝업 */}
      {summaryModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-3xl p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={() => setSummaryModal(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2.5 mb-3">
              <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[11px] font-bold text-emerald-600">AI 공시 돋보기</span>
                <h3 className="font-bold text-slate-900 text-sm leading-snug">
                  {summaryModal.report_nm}
                </h3>
              </div>
            </div>

            {summaryLoading ? (
              <div className="py-12 text-center text-slate-400 text-xs flex flex-col items-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-emerald-500" />
                <span>공시 원문을 정밀 분석하고 요약 중입니다...</span>
              </div>
            ) : summaryModal.summary ? (
              <div className="space-y-4 mt-4">
                <div className="flex items-center justify-between bg-slate-50 p-3 rounded-xl border border-slate-100 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[10px]">공시 분류</span>
                    <span className="font-bold text-slate-800">{summaryModal.summary.category}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-slate-400 block text-[10px]">주가 위험도 등급</span>
                    <span className="font-bold text-rose-600">{summaryModal.summary.risk_level}</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <h5 className="font-bold text-xs text-slate-700">📌 핵심 내용 3줄 요약</h5>
                  <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 space-y-2 text-xs text-slate-600">
                    {summaryModal.summary.key_points?.map((pt: string, idx: number) => (
                      <p key={idx} className="leading-relaxed">
                        • {pt}
                      </p>
                    ))}
                  </div>
                </div>

                <div className="bg-emerald-50/70 border border-emerald-100 p-3 rounded-xl text-xs text-emerald-800 font-medium">
                  {summaryModal.summary.action_guide}
                </div>

                <div className="flex gap-2 pt-1">
                  <a
                    href={summaryModal.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-center font-bold text-xs py-2.5 rounded-xl transition flex items-center justify-center gap-1"
                  >
                    DART 전자공시 원문 전체보기 <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                  <button
                    onClick={() => setSummaryModal(null)}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs py-2.5 rounded-xl transition cursor-pointer"
                  >
                    확인 완료
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* 6. 약관 모달 */}
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
본 서비스(Financial Multi-Risk Guardian)는 DART 전자공시 및 공공 뉴스 데이터를 기반으로 기업의 잠재적 리스크 요인을 탐지·가공하여 요약 정보를 제공하는 보조 도구입니다.`
              ) : (
                `1. 수집 항목: 사용자 아이디, 활동 닉네임, 이메일 주소, 투자 경험 정보`
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