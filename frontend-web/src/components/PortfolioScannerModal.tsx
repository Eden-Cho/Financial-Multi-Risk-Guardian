"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  X,
  Plus,
  Loader2,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

interface StockCard {
  stock_name: string;
  stock_code: string;
  score: number;
  status: "SAFE" | "CAUTION" | "DANGER";
  badge_color: string;
  highlight_flags: string[];
  major_risks: string[];
}

interface TopWarning {
  severity: "CRITICAL" | "WARNING";
  target_stock: string;
  title: string;
  description: string;
}

interface DiagnosisResult {
  status: string;
  portfolio_summary: {
    overall_score: number;
    grade: string;
    risk_level: string;
    risk_level_kr: string;
    summary_comment: string;
    distribution: {
      safe_count: number;
      caution_count: number;
      danger_count: number;
      total_count: number;
    };
  };
  radar_composite: Array<{
    category: string;
    score: number;
    full_mark: number;
  }>;
  stock_cards: StockCard[];
  top_warnings: TopWarning[];
}

interface PortfolioScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId?: string;
}

export default function PortfolioScannerModal({
  isOpen,
  onClose,
  userId = "user_demo",
}: PortfolioScannerModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  
  const [detectedStocks, setDetectedStocks] = useState<string[]>([]);
  const [newStockInput, setNewStockInput] = useState("");
  const [diagnosisData, setDiagnosisData] = useState<DiagnosisResult | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileSelect = (selectedFile: File) => {
    if (!selectedFile.type.startsWith("image/")) {
      alert("이미지 파일(PNG, JPG 등)만 업로드할 수 있습니다.");
      return;
    }
    setFile(selectedFile);
    setPreviewUrl(URL.createObjectURL(selectedFile));
    setDiagnosisData(null);
    setDetectedStocks([]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  // 1단계: OCR 실행
  const runOcrScan = async () => {
    if (!file) return;

    setIsScanning(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("user_id", userId);

    try {
      const res = await fetch("http://localhost:8000/api/watchlist/upload-screenshot", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("OCR 추출 실패");

      const data = await res.json();
      const stocks: string[] = data.detected_stocks || [];
      setDetectedStocks(stocks);

      // 백엔드에서 동시에 내려준 진단 데이터가 있을 경우 바로 세팅
      if (data.diagnosis && data.diagnosis.status === "success") {
        setDiagnosisData(data.diagnosis);
      }
    } catch (err: any) {
      alert(`스캔 중 오류 발생: ${err.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  // 2단계: 태그 수정 후 정밀 재진단 요청
  const runReDiagnosis = async (stocks: string[]) => {
    if (stocks.length === 0) {
      setDiagnosisData(null);
      return;
    }
    setIsDiagnosing(true);
    try {
      const res = await fetch("http://localhost:8000/api/portfolio/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stock_names: stocks }),
      });
      if (!res.ok) throw new Error("포트폴리오 진단 실패");
      const data = await res.json();
      setDiagnosisData(data);
    } catch (err: any) {
      alert(`진단 오류: ${err.message}`);
    } finally {
      setIsDiagnosing(false);
    }
  };

  const removeStock = (target: string) => {
    const updated = detectedStocks.filter((s) => s !== target);
    setDetectedStocks(updated);
    if (updated.length > 0) runReDiagnosis(updated);
    else setDiagnosisData(null);
  };

  const addStock = () => {
    const clean = newStockInput.trim();
    if (!clean || detectedStocks.includes(clean)) return;
    const updated = [...detectedStocks, clean];
    setDetectedStocks(updated);
    setNewStockInput("");
    runReDiagnosis(updated);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-indigo-400" />
              MTS 잔고 스크린샷 원스톱 정밀 진단
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              스크린샷을 업로드하면 상장 종목 추출부터 9각 다차원 리스크 요약까지 즉시 분석합니다.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 본문 영역 */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-200">
          {/* 업로드 & 미리보기 */}
          {!diagnosisData && (
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              className={`border-2 border-dashed rounded-xl p-8 text-center flex flex-col items-center justify-center transition ${
                previewUrl
                  ? "border-indigo-500/50 bg-indigo-500/5"
                  : "border-slate-700 bg-slate-800/30 hover:border-slate-500"
              }`}
            >
              {previewUrl ? (
                <div className="flex flex-col items-center gap-4">
                  <img
                    src={previewUrl}
                    alt="MTS 잔고 캡처"
                    className="max-h-56 rounded-lg shadow-md border border-slate-700 object-contain"
                  />
                  <div className="flex gap-3">
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                    >
                      다른 이미지 선택
                    </button>
                    <button
                      disabled={isScanning}
                      onClick={runOcrScan}
                      className="px-5 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center gap-2 transition disabled:opacity-50"
                    >
                      {isScanning ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          EasyOCR 판독 중...
                        </>
                      ) : (
                        <>
                          종목 자동 추출 시작
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="cursor-pointer flex flex-col items-center"
                >
                  <UploadCloud className="w-12 h-12 text-slate-500 mb-3" />
                  <p className="text-sm font-semibold text-slate-300">
                    증권사 잔고/보유종목 캡처 이미지를 드래그하거나 클릭하여 선택
                  </p>
                  <p className="text-xs text-slate-500 mt-1">PNG, JPG, JPEG 지원</p>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              />
            </div>
          )}

          {/* 인식된 종목 칩 태그 바 */}
          {detectedStocks.length > 0 && (
            <div className="bg-slate-800/60 border border-slate-700/60 p-4 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  인식된 보유 종목 ({detectedStocks.length}개)
                </span>
                {isDiagnosing && (
                  <span className="text-xs text-indigo-400 flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" /> 리스크 재계산 중...
                  </span>
                )}
              </div>

              <div className="flex flex-wrap gap-2 items-center">
                {detectedStocks.map((stock) => (
                  <span
                    key={stock}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-700/80 border border-slate-600 text-sm font-medium text-slate-200 rounded-lg"
                  >
                    {stock}
                    <button
                      onClick={() => removeStock(stock)}
                      className="hover:text-red-400 transition"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}

                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    value={newStockInput}
                    placeholder="종목 직접 추가"
                    onChange={(e) => setNewStockInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addStock()}
                    className="bg-slate-900 border border-slate-700 text-xs px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-indigo-500 text-slate-200 w-28"
                  />
                  <button
                    onClick={addStock}
                    className="p-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-300"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 종합 진단 리포트 대시보드 */}
          {diagnosisData && (
            <div className="space-y-6 animate-fadeIn">
              {/* 긴급 알림 배너 */}
              {diagnosisData.top_warnings.length > 0 && (
                <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-red-400 font-bold text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    포트폴리오 긴급 위험 경보
                  </div>
                  <div className="grid gap-2 text-xs">
                    {diagnosisData.top_warnings.map((warn, idx) => (
                      <div key={idx} className="bg-red-950/40 p-2.5 rounded-lg border border-red-900/40">
                        <span className="font-semibold text-red-300 mr-2">[{warn.target_stock}]</span>
                        <span className="text-slate-300">{warn.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 상단 요약 카드 + 9각 레이더 차트 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* 종합 점수 카드 */}
                <div className="bg-slate-800/40 border border-slate-800 p-5 rounded-xl flex flex-col justify-between">
                  <div>
                    <span className="text-xs text-slate-400 font-medium">통합 헬스케어 점수</span>
                    <div className="flex items-baseline gap-3 mt-1">
                      <span className="text-4xl font-extrabold text-white">
                        {diagnosisData.portfolio_summary.overall_score}
                      </span>
                      <span className="text-sm font-bold text-slate-400">/ 100점</span>
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-bold ml-auto ${
                          diagnosisData.portfolio_summary.risk_level === "SAFE"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : diagnosisData.portfolio_summary.risk_level === "CAUTION"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        {diagnosisData.portfolio_summary.risk_level_kr}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 mt-4 leading-relaxed bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
                      {diagnosisData.portfolio_summary.summary_comment}
                    </p>
                  </div>

                  {/* 안전도 분포 바 */}
                  <div className="mt-4 pt-4 border-t border-slate-800 flex justify-around text-center text-xs">
                    <div>
                      <div className="text-emerald-400 font-bold text-lg">
                        {diagnosisData.portfolio_summary.distribution.safe_count}
                      </div>
                      <div className="text-slate-400 text-[11px]">안전</div>
                    </div>
                    <div className="border-r border-slate-800" />
                    <div>
                      <div className="text-amber-400 font-bold text-lg">
                        {diagnosisData.portfolio_summary.distribution.caution_count}
                      </div>
                      <div className="text-slate-400 text-[11px]">주의</div>
                    </div>
                    <div className="border-r border-slate-800" />
                    <div>
                      <div className="text-rose-400 font-bold text-lg">
                        {diagnosisData.portfolio_summary.distribution.danger_count}
                      </div>
                      <div className="text-slate-400 text-[11px]">고위험</div>
                    </div>
                  </div>
                </div>

                {/* 9각 레이더 차트 */}
                <div className="bg-slate-800/40 border border-slate-800 p-4 rounded-xl flex flex-col items-center justify-center">
                  <span className="text-xs text-slate-400 font-medium mb-1 self-start">
                    포트폴리오 9각 리스크 노출도
                  </span>
                  <div className="w-full h-52">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={diagnosisData.radar_composite}>
                        <PolarGrid stroke="#334155" />
                        <PolarAngleAxis dataKey="category" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                        <PolarRadiusAxis domain={[0, 100]} stroke="#475569" tick={false} />
                        <Radar
                          name="리스크 노출도"
                          dataKey="score"
                          stroke="#818cf8"
                          fill="#6366f1"
                          fillOpacity={0.4}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* 개별 종목 신호등 카드 리스트 */}
              <div className="space-y-3">
                <span className="text-xs font-bold text-slate-400 tracking-wider uppercase">
                  종목별 세부 판정 리스트
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {diagnosisData.stock_cards.map((card) => (
                    <div
                      key={card.stock_name}
                      className="bg-slate-800/30 border border-slate-800 p-3.5 rounded-xl hover:border-slate-700 transition space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="font-bold text-white text-sm mr-2">{card.stock_name}</span>
                          <span className="text-xs text-slate-500">{card.stock_code}</span>
                        </div>
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-bold ${
                            card.status === "SAFE"
                              ? "bg-emerald-500/10 text-emerald-400"
                              : card.status === "CAUTION"
                              ? "bg-amber-500/10 text-amber-400"
                              : "bg-rose-500/10 text-rose-400"
                          }`}
                        >
                          {card.score}점
                        </span>
                      </div>

                      {/* 리스크/플래그 태그 */}
                      <div className="flex flex-wrap gap-1 text-[11px]">
                        {card.highlight_flags.map((flag, i) => (
                          <span key={i} className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
                            {flag}
                          </span>
                        ))}
                        {card.major_risks.map((risk, i) => (
                          <span key={i} className="bg-rose-950/40 text-rose-300 px-2 py-0.5 rounded border border-rose-900/30">
                            {risk}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-5 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            확인 완료
          </button>
        </div>
      </div>
    </div>
  );
}