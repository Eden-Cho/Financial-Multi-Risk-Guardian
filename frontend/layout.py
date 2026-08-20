import gradio as gr
import plotly.express as px

def create_ui(risk_analyzer):
    
    def handle_analyze(stock_name):
        # 백엔드 호출
        score_info, radar_df, report_text = risk_analyzer.analyze(stock_name)
        
        # Plotly 차트 생성
        fig = px.line_polar(radar_df, r='r', theta='theta', line_close=True)
        fig.update_traces(fill='toself', line_color='#E63946')
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        # HTML Score 카드
        score_html = f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #2a9d8f; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="margin:0; color:#264653; font-size: 22px;">🛡️ Safety Score: <span style="color:#2a9d8f; font-weight:bold;">{score_info['score']} / 100</span> ({score_info['status']})</h2>
            <p style="margin:8px 0 0 0; color:#6c757d; font-size: 13px;">🔒 Security-First Anonymizer Layer 가공 완료 | 실시간 SLM 진단 결과</p>
        </div>
        """
        return score_html, fig, report_text

    # Gradio Blocks UI 구성 (Gradio 6.0+ 최신 규격 반영)
    with gr.Blocks(title="Financial Multi-Risk Guardian") as demo:
        gr.Markdown(
            """
            # 🛡️ Financial Multi-Risk Guardian
            ### 개인투자자 보호를 위한 AI 기반 주식 다차원 위험 진단 & 뇌동매매 방지 비서
            ---
            """
        )
        with gr.Row():
            with gr.Column(scale=1):
                stock_input = gr.Textbox(label="종목명 또는 종목코드", placeholder="예: 삼성전자, 카카오, 005930", value="삼성전자")
                btn = gr.Button("🔍 AI 멀티 리스크 스캔 시작", variant="primary", size="lg")
                gr.Markdown("#### 💡 서비스 안내\n* **소비자 보호:** 자산 보호 및 위험 요소 경고 목적\n* **보안 강화:** 개인정보 비식별화(Masking) 적용")
            
            with gr.Column(scale=2):
                score_output = gr.HTML(label="Safety Score")
                with gr.Row():
                    # PlotlyPlot -> Plot으로 수정
                    chart_output = gr.Plot(label="다차원 리스크 지형도")
                    report_output = gr.Textbox(label="SLM AI 모델 상세 진단 리포트", lines=9)

        btn.click(fn=handle_analyze, inputs=[stock_input], outputs=[score_output, chart_output, report_output])
        
    return demo