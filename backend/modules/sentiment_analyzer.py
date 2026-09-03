"""
==============================================================================
[Module Overview]
- 파일명: backend/modules/sentiment_analyzer.py
- 프로젝트: Financial Multi-Risk Guardian
- 주요 역할:
    1. HuggingFace Hub의 사전학습된 금융 특화 언어모델(KR-FinBERT-SC) 로드 및 가중치 관리
    2. DART 공시 보고서명 및 금융 뉴스 텍스트의 감성 레이블(Positive / Neutral / Negative) 및 확률값 도출
    3. [모델 보강: Rule-based Override Guardrail]
       일반 언어모델이 '유상증자', '감자', '사채 리픽싱' 등을 중립/긍정으로 오분류하는 한계를 극복하기 위해
       치명적 공시 악재 키워드 감지 시 강제로 'negative' 레이블을 부여하는 규칙 보정 계층 운용
    4. 배치 추론(Batch Inference) 및 인메모리 캐싱을 통한 1-Pass 병렬 텐서 연산 최적화
==============================================================================
"""

import os
import torch
import torch.nn.functional as F
from typing import List, Dict, Any
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForSequenceClassification

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN", None)
MODEL_NAME = "snunlp/KR-FinBERT-SC"


class FinancialSentimentAnalyzer:
    """
    KR-FinBERT 기반 금융 텍스트 감성 분석 엔진 (규칙 보정 가드레일 및 배치 추론 적용)
    """

    def __init__(self, model_name: str = MODEL_NAME):
        """
        [함수 역할]
        KR-FinBERT 모델 및 토크나이저를 메모리에 로드하고, 강제 악재 오버라이드 키워드 세트를 초기화합니다.

        Args:
            model_name (str): HuggingFace 모델 리포지토리 식별자
        """
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() 
            else ("mps" if torch.backends.mps.is_available() else "cpu")
        )

        self.tokenizer = None
        self.model = None
        self._cache: Dict[str, Dict[str, Any]] = {}

        # [Rule 보정 가드레일] BERT 모델이 중립으로 오판하기 쉬운 치명적 공시 지뢰 키워드 세트
        self.critical_negative_keywords = [
            "감자결정", "무상감자", "유상감자", "전환가액의조정", "리픽싱", "최대주주변경을수반하는주식담보",
            "담보제공계약", "반대매매", "불성실공시", "벌점", "소송등의제기", "회생절차", "파산",
            "감사의견거절", "감사의견한정", "영업정지", "주권매매거래정지", "투자경고", "투자위험"
        ]

        # 호재로 명확히 인정되는 공시 키워드 세트
        self.critical_positive_keywords = [
            "단일판매ㆍ공급계약체결", "수주", "무상증자결정", "자기주식취득", "자기주식소각", "흑자전환", "배당결정"
        ]

        try:
            token_kwargs = {"token": HF_TOKEN} if HF_TOKEN else {}
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, **token_kwargs)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name, **token_kwargs
            ).to(self.device)
            self.model.eval()
            print(f"[SentimentAnalyzer] '{model_name}' 모델 로드 완료 (Device: {self.device})")
        except Exception as e:
            print(f"[SentimentAnalyzer 경고] 로컬 모델 로드 실패, 휴리스틱 모드로 전환: {e}")
            self.model = None

    def analyze_sentiments(self, texts: List[str]) -> Dict[str, Any]:
        """
        [함수 역할]
        입력된 다수의 공시/뉴스 텍스트 리스트를 배치 추론한 후,
        규칙 보정 가드레일을 적용하여 긍정/부정/중립 비율과 여론 점수를 산출합니다.

        Args:
            texts (List[str]): 공시 제목 또는 뉴스 헤드라인 문자열 목록

        Returns:
            Dict[str, Any]: 감성 지표 통계 및 세부 예측 리스트
        """
        valid_texts = [t.strip() for t in texts if t and t.strip()]
        if not valid_texts:
            return self._get_empty_result()

        if self.model is None or self.tokenizer is None:
            return self._fallback_rule_based(valid_texts)

        uncached_texts = []
        uncached_indices = []
        results: List[Dict[str, Any]] = [None] * len(valid_texts)

        for idx, text in enumerate(valid_texts):
            if text in self._cache:
                results[idx] = self._cache[text]
            else:
                uncached_texts.append(text)
                uncached_indices.append(idx)

        # 미캐싱 텍스트 일괄 뱃치 추론
        if uncached_texts:
            batch_predictions = self._infer_batch(uncached_texts)
            for orig_idx, pred, raw_text in zip(uncached_indices, batch_predictions, uncached_texts):
                # [Rule 보정 적용] 딥러닝 추론 결과에 금융 도메인 가드레일 결합
                calibrated_pred = self._apply_rule_guardrail(pred)
                results[orig_idx] = calibrated_pred
                if len(self._cache) < 1000:
                    self._cache[raw_text] = calibrated_pred

        # 통계 집계
        pos_count = sum(1 for r in results if r["label"] == "positive")
        neg_count = sum(1 for r in results if r["label"] == "negative")
        neu_count = sum(1 for r in results if r["label"] == "neutral")
        total = len(results)

        pos_pct = round((pos_count / total) * 100, 1)
        neg_pct = round((neg_count / total) * 100, 1)
        neu_pct = round(100.0 - (pos_pct + neg_pct), 1)

        raw_diff = (pos_pct - neg_pct)
        sentiment_score = int(max(0, min(100, 50 + (raw_diff * 0.5))))

        if sentiment_score >= 60:
            status = "긍정적 여론 우세"
        elif sentiment_score <= 40:
            status = "부정적 악재 경계"
        else:
            status = "중립적 관망세"

        return {
            "positive_pct": pos_pct,
            "negative_pct": neg_pct,
            "neutral_pct": neu_pct,
            "sentiment_score": sentiment_score,
            "sentiment_status": status,
            "breakdown": results
        }

    def _apply_rule_guardrail(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        [함수 역할 - Rule 보정 핵심]
        딥러닝 추론 결과가 치명적 공시 악재/호재 키워드와 충돌할 경우 강제로 레이블을 교정(Override)합니다.

        Args:
            prediction (Dict[str, Any]): {'text': ..., 'label': ..., 'score': ...}

        Returns:
            Dict[str, Any]: 교정된 예측 딕셔너리
        """
        text = prediction["text"]
        
        # 1. 치명적 악재 키워드 우선 검사 (중립/긍정 오판 방지)
        for neg_k in self.critical_negative_keywords:
            if neg_k in text:
                return {
                    "text": text,
                    "label": "negative",
                    "score": 0.99,
                    "override": True,
                    "reason": f"공시 악재 키워드 '{neg_k}' 감지"
                }

        # 2. 명확한 호재 키워드 검사
        for pos_k in self.critical_positive_keywords:
            if pos_k in text:
                return {
                    "text": text,
                    "label": "positive",
                    "score": 0.95,
                    "override": True,
                    "reason": f"공시 호재 키워드 '{pos_k}' 감지"
                }

        return prediction

    def _infer_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """N개 텍스트 배치 텐서화 및 1-Pass 추론"""
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**encoded)
            probabilities = F.softmax(outputs.logits, dim=-1).cpu()

        predictions = []
        for text, probs in zip(texts, probabilities):
            pred_idx = int(torch.argmax(probs).item())
            confidence = float(probs[pred_idx].item())
            
            label_raw = self.model.config.id2label.get(pred_idx, str(pred_idx)).lower()
            if "pos" in label_raw:
                mapped_label = "positive"
            elif "neg" in label_raw:
                mapped_label = "negative"
            else:
                mapped_label = "neutral"

            predictions.append({
                "text": text,
                "label": mapped_label,
                "score": round(confidence, 4)
            })

        return predictions

    def _fallback_rule_based(self, texts: List[str]) -> Dict[str, Any]:
        """휴리스틱 사전 기반 폴백 분석기"""
        results = []
        for text in texts:
            base_pred = {"text": text, "label": "neutral", "score": 0.70}
            results.append(self._apply_rule_guardrail(base_pred))

        pos_count = sum(1 for r in results if r["label"] == "positive")
        neg_count = sum(1 for r in results if r["label"] == "negative")
        neu_count = sum(1 for r in results if r["label"] == "neutral")
        total = len(results)

        pos_pct = round((pos_count / total) * 100, 1)
        neg_pct = round((neg_count / total) * 100, 1)
        neu_pct = round(100.0 - (pos_pct + neg_pct), 1)

        sentiment_score = int(max(0, min(100, 50 + ((pos_pct - neg_pct) * 0.5))))

        return {
            "positive_pct": pos_pct,
            "negative_pct": neg_pct,
            "neutral_pct": neu_pct,
            "sentiment_score": sentiment_score,
            "sentiment_status": "규칙 기반 분석 완료",
            "breakdown": results
        }

    def _get_empty_result(self) -> Dict[str, Any]:
        return {
            "positive_pct": 0.0,
            "negative_pct": 0.0,
            "neutral_pct": 100.0,
            "sentiment_score": 50,
            "sentiment_status": "수집된 공시 없음",
            "breakdown": []
        }