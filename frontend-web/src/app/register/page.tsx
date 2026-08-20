"use client";

import React, { useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ShieldAlert, ArrowLeft, CheckCircle2, AlertCircle, BellRing, X } from "lucide-react";

const API_BASE = "http://127.0.0.1:8000/api";

export default function RegisterPage() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [experience, setExperience] = useState("beginner");
  
  // 법적 동의 체크박스 상태
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [agreePrivacyAlert, setAgreePrivacyAlert] = useState(false);
  const [agreeMarketing, setAgreeMarketing] = useState(false);

  // 약관 모달 상태
  const [modalType, setModalType] = useState<"terms" | "privacy" | null>(null);

  const [errorMsg, setErrorMsg] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!username.trim() || !password.trim() || !email.trim()) {
      setErrorMsg("아이디, 이메일, 비밀번호를 모두 입력해 주세요.");
      return;
    }
    if (password !== passwordConfirm) {
      setErrorMsg("비밀번호가 일치하지 않습니다.");
      return;
    }
    if (password.length < 4) {
      setErrorMsg("비밀번호는 최소 4자 이상이어야 합니다.");
      return;
    }
    if (!agreeTerms || !agreePrivacyAlert) {
      setErrorMsg("필수 약관 및 개인정보(공시 알림) 수집에 동의해 주세요.");
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/auth/register`, {
        username: username.trim(),
        nickname: nickname.trim() || username.trim(),
        email: email.trim(),
        password: password.trim(),
        experience: experience,
        marketing_agree: agreeMarketing
      });

      if (res.data.success) {
        setIsSuccess(true);
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "회원가입 처리 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md px-4 mb-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
        >
          <ArrowLeft className="w-4 h-4" /> 메인 대시보드로 돌아가기
        </Link>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center mb-2">
          <div className="bg-emerald-500 text-white p-3 rounded-2xl shadow-sm">
            <ShieldAlert className="w-8 h-8" />
          </div>
        </div>
        <h2 className="text-center text-2xl font-black text-slate-900">
          가디언 계정 만들기
        </h2>
        <p className="mt-1 text-center text-xs text-slate-500">
          지뢰 공시 실시간 이메일 알림과 뇌동매매 방지를 시작하세요
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-white py-8 px-6 shadow-xl shadow-slate-200/50 rounded-3xl border border-slate-100 sm:px-10">
          {isSuccess ? (
            <div className="text-center py-4 space-y-4">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
              <div>
                <h3 className="text-lg font-bold text-slate-900">회원가입이 완료되었습니다!</h3>
                <p className="text-xs text-slate-500 mt-1">
                  <b>[{nickname || username}]</b> 님, 등록하신 <b>{email}</b>(으)로 긴급 지뢰 공시가 감지되면 즉시 브리핑을 보내드립니다.
                </p>
              </div>
              <button
                onClick={() => router.push("/")}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition text-sm cursor-pointer"
              >
                메인으로 가서 로그인하기
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  아이디 <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="로그인용 아이디"
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  활동 닉네임 <span className="text-slate-400 font-normal">(미입력시 아이디 자동적용)</span>
                </label>
                <input
                  type="text"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  placeholder="예: 성투하는라이언"
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 flex items-center justify-between">
                  <span>이메일 주소 <span className="text-rose-500">*</span></span>
                  <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-0.5">
                    <BellRing className="w-3 h-3" /> 지뢰공시 알림용
                  </span>
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  비밀번호 <span className="text-rose-500">*</span>
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="4자리 이상 비밀번호"
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  비밀번호 확인 <span className="text-rose-500">*</span>
                </label>
                <input
                  type="password"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  placeholder="비밀번호 재확인"
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  투자 경험 (맞춤 진단용)
                </label>
                <select
                  value={experience}
                  onChange={(e) => setExperience(e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500 bg-white"
                >
                  <option value="beginner">🌱 이제 막 시작한 주린이 (1년 미만)</option>
                  <option value="intermediate">📈 매매 경험 1~3년 차</option>
                  <option value="advanced">👑 3년 이상 숙련 투자자</option>
                </select>
              </div>

              {/* 약관 및 알림 동의 체크박스 영역 */}
              <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-100 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <label className="flex items-start gap-2 cursor-pointer flex-1">
                    <input
                      type="checkbox"
                      checked={agreeTerms}
                      onChange={(e) => setAgreeTerms(e.target.checked)}
                      className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4 mt-0.5 shrink-0"
                    />
                    <span className="text-slate-700 leading-tight">
                      <b className="text-emerald-700">[필수]</b> 이용약관 & 투자유의사항 동의
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setModalType("terms")}
                    className="text-[11px] text-slate-400 hover:text-emerald-600 underline shrink-0 ml-2"
                  >
                    전문보기
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <label className="flex items-start gap-2 cursor-pointer flex-1">
                    <input
                      type="checkbox"
                      checked={agreePrivacyAlert}
                      onChange={(e) => setAgreePrivacyAlert(e.target.checked)}
                      className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4 mt-0.5 shrink-0"
                    />
                    <span className="text-slate-700 leading-tight">
                      <b className="text-emerald-700">[필수]</b> 개인정보 수집(공시알림) 동의
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setModalType("privacy")}
                    className="text-[11px] text-slate-400 hover:text-emerald-600 underline shrink-0 ml-2"
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
                      className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4 mt-0.5 shrink-0"
                    />
                    <span className="text-slate-500 leading-tight">
                      [선택] 주간 리스크 브리핑 수신 동의
                    </span>
                  </label>
                </div>
              </div>

              {errorMsg && (
                <div className="flex items-center gap-2 bg-rose-50 text-rose-600 p-3 rounded-xl text-xs font-medium border border-rose-100">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-bold py-3 rounded-xl transition shadow-sm text-sm mt-2 cursor-pointer"
              >
                {loading ? "가입 처리 중..." : "가디언 시작하기 (회원가입)"}
              </button>

              <div className="text-center pt-2">
                <p className="text-xs text-slate-500">
                  이미 계정이 있으신가요?{" "}
                  <Link href="/" className="text-emerald-600 font-bold hover:underline">
                    로그인하기
                  </Link>
                </p>
              </div>
            </form>
          )}
        </div>
      </div>

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
                if (modalType === "terms") setAgreeTerms(true);
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