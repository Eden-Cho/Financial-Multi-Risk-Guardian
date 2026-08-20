import gradio as gr
import plotly.express as px
import pandas as pd


def create_ui(risk_analyzer, db_manager):
    
    # ------------------- 헬퍼 함수 -------------------
    
    def get_watchlist_df(username):
        if not username:
            return pd.DataFrame(columns=["종목명", "메모 / 담아둔 이유", "등록일"])
        items = db_manager.get_user_portfolio(username)
        if not items:
            return pd.DataFrame(columns=["종목명", "메모 / 담아둔 이유", "등록일"])
        
        data = []
        for it in items:
            data.append({
                "종목명": it["stock_name"],
                "메모 / 담아둔 이유": it["memo"] or "관심 종목",
                "등록일": str(it["created_at"])[:10]
            })
        return pd.DataFrame(data)

    # ------------------- 뷰 전환 & 인증 핸들러 -------------------

    def go_to_auth():
        # 메인 숨김 -> 인증 화면 표시
        return gr.update(visible=False), gr.update(visible=True), ""

    def go_to_main():
        # 인증 화면 숨김 -> 메인 표시
        return gr.update(visible=True), gr.update(visible=False)

    def handle_auth_submit(auth_mode, username, password):
        if not username or not password:
            return (
                "⚠️ 아이디와 비밀번호를 모두 입력해 주세요.",
                "",
                gr.update(visible=False),  # main_view
                gr.update(visible=True),   # auth_view
                gr.update(visible=True),   # unauth_box
                gr.update(visible=False),  # auth_box
                "",
                get_watchlist_df("")
            )
        
        if auth_mode == "로그인":
            if db_manager.verify_user(username, password):
                df = get_watchlist_df(username)
                welcome_text = f"👤 **{username}**님 환영합니다"
                # 로그인 성공 시 메인 화면으로 복귀
                return (
                    "",
                    username,
                    gr.update(visible=True),   # main_view 열기
                    gr.update(visible=False),  # auth_view 닫기
                    gr.update(visible=False),  # unauth_box 숨김
                    gr.update(visible=True),   # auth_box 표시
                    welcome_text,
                    df
                )
            else:
                return (
                    "❌ 아이디 또는 비밀번호가 올바르지 않습니다.",
                    "",
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    "",
                    get_watchlist_df("")
                )
        else:  # 회원가입
            ok, res_msg = db_manager.register_user(username, password)
            if ok:
                return (
                    f"🎉 {res_msg} (로그인 탭으로 전환하여 로그인해 주세요)",
                    "",
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    "",
                    get_watchlist_df("")
                )
            else:
                return (
                    f"❌ {res_msg}",
                    "",
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    "",
                    get_watchlist_df("")
                )

    def handle_logout():
        # 로그아웃 처리
        return (
            "",
            gr.update(visible=True),   # unauth_box 표시
            gr.update(visible=False),  # auth_box 숨김
            "",
            get_watchlist_df("")
        )

    # ------------------- 분석 & 포트폴리오 핸들러 -------------------

    def handle_analyze(stock_name):
        if not stock_name:
            return "종목명을 입력하세요.", None, ""
        
        score_info, radar_df, report_text = risk_analyzer.analyze(stock_name)
        
        fig = px.line_polar(radar_df, r='r', theta='theta', line_close=True)
        fig.update_traces(fill='toself', line_color='#E63946')
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        score = score_info['score']
        if score >= 80:
            color = "#2a9d8f"
        elif score >= 60:
            color = "#e9c46a"
        elif score >= 40:
            color = "#f4a261"
        else:
            color = "#e76f51"
        
        score_html = f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid {color}; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="margin:0; color:#264653; font-size: 22px;">🛡️ Safety Score: <span style="color:{color}; font-weight:bold;">{score} / 100</span> ({score_info['status']})</h2>
            <p style="margin:8px 0 0 0; color:#6c757d; font-size: 13px;">🔒 Security-First Anonymizer Layer 가공 완료 | DART 공시 {score_info.get('dart_count', 0)}건 · 실시간 뉴스 {score_info.get('news_count', 0)}건 분석</p>
        </div>
        """
        return score_html, fig, report_text

    def handle_add_stock(current_user, stock_name, memo):
        if not current_user:
            return gr.update(value="⚠️ 먼저 우측 상단에서 로그인을 진행해 주세요."), get_watchlist_df("")
        if not stock_name:
            return gr.update(value="⚠️ 등록할 종목명을 입력해 주세요."), get_watchlist_df(current_user)
        
        ok, msg = db_manager.add_portfolio_item(
            username=current_user,
            stock_name=stock_name,
            memo=memo or "관심 종목"
        )
        df = get_watchlist_df(current_user)
        return gr.update(value=f"✅ {msg}"), df

    def handle_remove_stock(current_user, stock_name):
        if not current_user:
            return gr.update(value="⚠️ 먼저 우측 상단에서 로그인을 진행해 주세요."), get_watchlist_df("")
        if not stock_name:
            return gr.update(value="⚠️ 삭제할 종목명을 입력해 주세요."), get_watchlist_df(current_user)
        
        ok, msg = db_manager.remove_portfolio_item(current_user, stock_name)
        df = get_watchlist_df(current_user)
        return gr.update(value=f"🗑️ {msg}"), df

    def handle_scan_watchlist(current_user):
        if not current_user:
            return gr.update(value="⚠️ 로그인이 필요합니다."), pd.DataFrame()
        
        items = db_manager.get_user_portfolio(current_user)
        if not items:
            return gr.update(value="등록된 관심 종목이 없습니다. 종목을 먼저 등록해 주세요."), pd.DataFrame()
        
        results = []
        for it in items:
            name = it["stock_name"]
            score_info, _, _ = risk_analyzer.analyze(name)
            
            status = score_info["status"]
            advice = "🟢 안전 - 매수 검토 가능" if score_info['score'] >= 70 else "🟡 주의 - 공시 확인 필수" if score_info['score'] >= 50 else "🚨 위험 - 뇌동매매 주의 (지뢰 공시)"

            results.append({
                "종목명": name,
                "안전 점수": f"{score_info['score']}점",
                "위험 등급": status,
                "가디언 조언": advice,
                "메모": it["memo"] or "-"
            })
        
        res_df = pd.DataFrame(results)
        summary_msg = f"📊 **[{current_user}]** 님이 담아둔 총 {len(items)}개 종목의 리스크 일괄 점검이 완료되었습니다."
        return gr.update(value=summary_msg), res_df

    # ------------------- Gradio Blocks Layout -------------------
    
    with gr.Blocks(title="Financial Multi-Risk Guardian") as demo:
        current_user_state = gr.State("")

        # ==========================================
        # [PAGE 1] 메인 대시보드 뷰
        # ==========================================
        with gr.Column(visible=True) as main_view:
            # 1. 상단 내비게이션 바
            with gr.Row(variant="panel"):
                with gr.Column(scale=3):
                    gr.Markdown(
                        """
                        # 🛡️ Financial Multi-Risk Guardian
                        <p style="margin: 0; color: #6c757d; font-size: 14px;">
                            주린이를 위한 주식 다차원 지뢰(CB/유증/오버행) 진단 & 뇌동매매 방지 비서
                        </p>
                        """
                    )
                
                with gr.Column(scale=1, min_width=160):
                    # 비로그인 상태 UI
                    with gr.Group(visible=True) as unauth_header_box:
                        login_page_btn = gr.Button("🔐 로그인 / 회원가입", variant="primary")

                    # 로그인 완료 상태 UI
                    with gr.Group(visible=False) as auth_header_box:
                        header_welcome_display = gr.Markdown("")
                        logout_btn = gr.Button("로그아웃", variant="secondary", size="sm")

            gr.Markdown("")

            # 2. 메인 탭 영역
            with gr.Tabs():
                
                # [탭 1: 단일 종목 실시간 정밀 스캔]
                with gr.Tab("🔍 종목 1개 정밀 진단"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            stock_input = gr.Textbox(
                                label="종목명 또는 종목코드", 
                                placeholder="예: 모아데이타, 카카오, 삼성전자", 
                                value="모아데이타"
                            )
                            scan_btn = gr.Button("🔍 실시간 리스크 스캔", variant="primary", size="lg")
                            gr.Markdown(
                                """
                                #### 💡 이런 숨은 위험을 찾아냅니다
                                * **CB/BW 오버행:** 주식으로 전환되어 쏟아질 빚
                                * **유상증자 / 감자:** 주주 가치 희석 및 자본 잠식
                                * **관리종목 / 상장폐지 우려:** 부실 징후 공시
                                """
                            )
                        
                        with gr.Column(scale=2):
                            score_output = gr.HTML(label="Safety Score")
                            with gr.Row():
                                chart_output = gr.Plot(label="다차원 리스크 지형도")
                            report_output = gr.Markdown(label="SLM AI 모델 상세 진단 리포트")

                # [탭 2: 내 관심종목(장바구니) 일괄 점검]
                with gr.Tab("⭐ 내 관심 종목 (사기 전 점검)"):
                    gr.Markdown("#### 📋 '살까 말까' 고민 중인 종목 간편 등록")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            w_stock_name = gr.Textbox(label="종목명", placeholder="예: 모아데이타")
                            w_memo = gr.Textbox(label="담아둔 이유 / 메모", placeholder="예: 유튜브 추천, 친구 추천, 실적 기대")
                            
                            with gr.Row():
                                add_btn = gr.Button("➕ 관심종목 등록", variant="primary")
                                del_btn = gr.Button("🗑️ 종목 삭제", variant="stop")
                            
                            crud_status = gr.Markdown("")

                        with gr.Column(scale=2):
                            watchlist_table = gr.DataFrame(
                                headers=["종목명", "메모 / 담아둔 이유", "등록일"],
                                datatype=["str", "str", "str"],
                                label="내가 담아둔 관심 종목 목록"
                            )
                    
                    gr.Markdown("---")
                    gr.Markdown("#### ⚡ 담아둔 종목 전체 리스크 일괄 점검")
                    batch_scan_btn = gr.Button("🚀 매수 전 지뢰 탐지 (일괄 점검)", variant="primary", size="lg")
                    batch_status = gr.Markdown("")
                    batch_result_table = gr.DataFrame(label="관심 종목 종합 안전도 진단표")

        # ==========================================
        # [PAGE 2] 로그인 / 회원가입 전용 페이지 뷰
        # ==========================================
        with gr.Column(visible=False) as auth_view:
            with gr.Row():
                with gr.Column(scale=1):
                    pass
                with gr.Column(scale=2):
                    gr.Markdown(
                        """
                        <div style="text-align: center; margin-top: 30px; margin-bottom: 20px;">
                            <h2>🔐 Financial Multi-Risk Guardian 계정 관리</h2>
                            <p style="color: #6c757d;">로그인하여 관심 종목을 안전하게 보관하고 실시간으로 지뢰 공시를 감시하세요.</p>
                        </div>
                        """
                    )
                    with gr.Group():
                        auth_tab_mode = gr.Radio(["로그인", "회원가입"], label="이용 목적", value="로그인")
                        auth_user_id = gr.Textbox(label="아이디", placeholder="아이디를 입력하세요")
                        auth_user_pw = gr.Textbox(label="비밀번호", placeholder="비밀번호를 입력하세요", type="password")
                        auth_submit_btn = gr.Button("확인 및 계속하기", variant="primary", size="lg")
                        auth_msg_display = gr.Markdown("")
                    
                    back_to_main_btn = gr.Button("⬅️ 메인 대시보드로 돌아가기", variant="secondary")
                with gr.Column(scale=1):
                    pass

        # ------------------- 이벤트 바인딩 -------------------

        # 1. 화면 전환 버튼
        login_page_btn.click(
            fn=go_to_auth,
            inputs=[],
            outputs=[main_view, auth_view, auth_msg_display]
        )
        back_to_main_btn.click(
            fn=go_to_main,
            inputs=[],
            outputs=[main_view, auth_view]
        )

        # 2. 인증 제출 처리
        auth_submit_btn.click(
            fn=handle_auth_submit,
            inputs=[auth_tab_mode, auth_user_id, auth_user_pw],
            outputs=[
                auth_msg_display,
                current_user_state,
                main_view,
                auth_view,
                unauth_header_box,
                auth_header_box,
                header_welcome_display,
                watchlist_table
            ]
        )

        # 3. 로그아웃 처리
        logout_btn.click(
            fn=handle_logout,
            inputs=[],
            outputs=[
                current_user_state,
                unauth_header_box,
                auth_header_box,
                header_welcome_display,
                watchlist_table
            ]
        )

        # 4. 분석 & CRUD 이벤트
        scan_btn.click(
            fn=handle_analyze,
            inputs=[stock_input],
            outputs=[score_output, chart_output, report_output]
        )
        add_btn.click(
            fn=handle_add_stock,
            inputs=[current_user_state, w_stock_name, w_memo],
            outputs=[crud_status, watchlist_table]
        )
        del_btn.click(
            fn=handle_remove_stock,
            inputs=[current_user_state, w_stock_name],
            outputs=[crud_status, watchlist_table]
        )
        batch_scan_btn.click(
            fn=handle_scan_watchlist,
            inputs=[current_user_state],
            outputs=[batch_status, batch_result_table]
        )

    return demo