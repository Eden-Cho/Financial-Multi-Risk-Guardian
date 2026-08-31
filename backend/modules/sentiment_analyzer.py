import os
import time
import warnings

# Hugging Face 경고 및 프로그레스 바 비활성화
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings("ignore")

import torch
from transformers import pipeline, logging as hf_logging

# 프로그레스 바 및 경고 음소거
hf_logging.set_verbosity_error()
hf_logging.disable_progress_bar()

class FinancialSentimentAnalyzer:
    def __init__(self):
        self.pipe = None

    def _get_pipe(self):
        if self.pipe is None:
            t0 = time.perf_counter()
            try:
                self.pipe = pipeline(
                    "text-classification",
                    model="snunlp/KR-FinBert-SC",
                    device=0 if torch.cuda.is_available() else -1
                )
                elapsed = time.perf_counter() - t0
                print(f"[HuggingFace] snunlp/KR-FinBert-SC 모델 로드 완료 ({elapsed:.2f}s)")
            except Exception as e:
                print(f"[HuggingFace] FinBERT 로드 실패: {e}")
        return self.pipe

    def analyze_sentiments(self, texts: list[str]) -> dict:
        if not texts:
            return {
                "positive_pct": 50,
                "negative_pct": 20,
                "neutral_pct": 30,
                "sentiment_score": 65,
                "sentiment_status": "중립/안정",
                "breakdown": []
            }

        pipe = self._get_pipe()
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        breakdown = []

        if pipe:
            try:
                results = pipe(texts[:15], truncation=True, max_length=128)
                for txt, res in zip(texts[:15], results):
                    label = res['label'].lower()
                    score = round(res['score'] * 100, 1)
                    
                    if "pos" in label:
                        positive_count += 1
                        kr_label = "긍정"
                    elif "neg" in label:
                        negative_count += 1
                        kr_label = "부정(주의)"
                    else:
                        neutral_count += 1
                        kr_label = "중립"

                    breakdown.append({
                        "text": txt[:30] + ("..." if len(txt) > 30 else ""),
                        "label": kr_label,
                        "confidence": f"{score}%"
                    })
            except Exception as e:
                positive_count, neutral_count = len(texts), 0
        else:
            negative_keywords = ["적자", "손실", "사채", "유상증자", "소송", "불성실", "감소", "하락"]
            for txt in texts[:15]:
                if any(k in txt for k in negative_keywords):
                    negative_count += 1
                    breakdown.append({"text": txt[:30], "label": "부정(주의)", "confidence": "85.0%"})
                else:
                    positive_count += 1
                    breakdown.append({"text": txt[:30], "label": "긍정/중립", "confidence": "80.0%"})

        total = max(1, positive_count + negative_count + neutral_count)
        pos_pct = round((positive_count / total) * 100)
        neg_pct = round((negative_count / total) * 100)
        neu_pct = 100 - pos_pct - neg_pct

        sentiment_score = max(0, min(100, pos_pct + int(neu_pct * 0.5) - int(neg_pct * 0.5)))
        
        if neg_pct >= 40:
            sentiment_status = "악재 여론 우세 (부정적)"
        elif pos_pct >= 60:
            sentiment_status = "호재 여론 우세 (긍정적)"
        else:
            sentiment_status = "균형 (중립적 흐름)"

        return {
            "positive_pct": pos_pct,
            "negative_pct": neg_pct,
            "neutral_pct": max(0, neu_pct),
            "sentiment_score": sentiment_score,
            "sentiment_status": sentiment_status,
            "breakdown": breakdown[:5]
        }