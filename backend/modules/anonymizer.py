import re


class Anonymizer:
    def __init__(self):
        # 1. 주민등록번호 패턴 (990101-1234567 또는 9901011234567)
        self.rrn_pattern = re.compile(r"\b\d{6}[-\s]?[1-8]\d{6}\b")
        
        # 2. 휴대전화 및 일반 전화번호 패턴
        self.phone_pattern = re.compile(r"\b(01[016789]|02|0[3-9][0-9])[-\s]?\d{3,4}[-\s]?\d{4}\b")
        
        # 3. 은행 계좌번호 패턴 (숫자-숫자-숫자 형태)
        self.account_pattern = re.compile(r"\b\d{3,6}[-\s]\d{2,6}[-\s]\d{3,6}\b")
        
        # 4. 이메일 주소 패턴
        self.email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

    def mask_name(self, name: str) -> str:
        """이름 마스킹 (예: '한상진' -> '한*진', '홍길동' -> '홍*동', 'John' -> 'J**n')"""
        name = name.strip()
        if not name:
            return ""
        if len(name) == 2:
            return f"{name[0]}*"
        elif len(name) >= 3:
            return f"{name[0]}{'*' * (len(name) - 2)}{name[-1]}"
        return name

    def mask_text(self, text: str) -> str:
        """텍스트 내 모든 민감정보(주민번호, 전화번호, 계좌번호, 이메일) 비식별화"""
        if not text:
            return ""
        
        text = self.rrn_pattern.sub("[주민번호 비식별]", text)
        text = self.phone_pattern.sub("[연락처 비식별]", text)
        text = self.account_pattern.sub("[계좌번호 비식별]", text)
        text = self.email_pattern.sub("[이메일 비식별]", text)
        return text

    def anonymize_disclosures(self, items: list[dict]) -> list[dict]:
        """공시 목록 내 제출인 성명 및 보고서명 마스킹"""
        anonymized = []
        for item in items:
            clean_item = item.copy()
            flr_nm = clean_item.get("flr_nm", "")
            # 법인/기관명이 아닌 개인 성명(2~4자) 형태인 경우 마스킹
            if 2 <= len(flr_nm) <= 4 and not flr_nm.endswith(("회사", "법인", "본부", "거래소", "조합", "펀드")):
                clean_item["flr_nm"] = self.mask_name(flr_nm)
            
            clean_item["report_nm"] = self.mask_text(clean_item.get("report_nm", ""))
            anonymized.append(clean_item)
        return anonymized


if __name__ == "__main__":
    anon = Anonymizer()
    sample_text = "제출인 홍길동 (연락처: 010-1234-5678, 주민번호: 850101-1234567, 계좌: 110-123-456789)"
    print("=== 비식별화 테스트 ===")
    print("원문:", sample_text)
    print("마스킹:", anon.mask_text(sample_text))
    print("이름 마스킹:", anon.mask_name("한상진"))