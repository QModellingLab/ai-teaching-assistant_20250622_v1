return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>{analysis['user_name']} - 個人學習分析</title>
        <style>
            body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .header {{ text-align: center; margin-bottom: 30px; color: #333; }}
            .section {{ margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
            .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
            .value {{ font-weight: bold; color: #007bff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{analysis['user_name']} 個人學習分析</h1>
                <p>分析日期：{analysis['analysis_date']} | 學習期間：{analysis['study_period_days']} 天</p>
                <p><strong>綜合表現：{analysis['overall_assessment']['performance_level']} ({analysis['overall_assessment']['overall_score']}/10)</strong></p>
            </div>
            
            <div class="section">
                <h3>參與度分析</h3>
                <div class="metric">
                    <span>總互動次數</span>
                    <span class="value">{analysis['participation']['total_interactions']}</span>
                </div>
                <div class="metric">
                    <span>活躍天數</span>
                    <span class="value">{analysis['participation']['active_days']} 天</span>
                </div>
                <div class="metric">
                    <span>參與度等級</span>
                    <span class="value" style="color: {analysis['participation']['level_color']};">{analysis['participation']['participation_level']}</span>
                </div>
            </div>
            
            <div class="section">
                <h3>討論品質分析</h3>
                <div class="metric">
                    <span>平均品質分數</span>
                    <span class="value">{analysis['quality']['avg_quality']}/5.0</span>
                </div>
                <div class="metric">
                    <span>高品質討論次數</span>
                    <span class="value">{analysis['quality']['high_quality_count']} 次</span>
                </div>
                <div class="metric">
                    <span>品質趨勢</span>
                    <span class="value">{analysis['quality']['quality_trend']}</span>
                </div>
            </div>
            
            <div class="section">
                <h3>英語使用分析</h3>
                <div class="metric">
                    <span>平均英語使用比例</span>
                    <span class="value">{analysis['english_usage']['avg_english_ratio']:.1%}</span>
                </div>
                <div class="metric">
                    <span>雙語能力評估</span>
                    <span class="value">{analysis['english_usage']['bilingual_ability']}</span>
                </div>
            </div>
            
            <div class="section">
                <h3>提問行為分析</h3>
                <div class="metric">
                    <span>總提問次數</span>
                    <span class="value">{analysis['questioning']['total_questions']}</span>
                </div>
                <div class="metric">
                    <span>提問比例</span>
                    <span class="value">{analysis['questioning']['question_ratio']:.1%}</span>
                </div>
                <div class="metric">
                    <span>提問模式</span>
                    <span class="value">{analysis['questioning']['questioning_pattern']}</span>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/student_list" style="color: #007bff; margin: 0 10px;">返回學生列表</a>
                <a href="/admin" style="color: #007bff; margin: 0 10px;">管理首頁</a>
                <a href="/" style="color: #007bff; margin: 0 10px;">回到首頁</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/class_analysis")
def class_analysis():
    """班級分析頁面"""
    try:
        if not ensure_db_exists():
            return '''
            <div style="text-align: center; padding: 50px; font-family: Microsoft JhengHei;">
                <h2>資料庫錯誤</h2>
                <p>資料庫初始化失敗</p>
                <a href="/" style="color: #007bff;">回到首頁</a>
            </div>
            '''
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT u.user_id) as total_students,
                   COUNT(DISTINCT CASE WHEN i.id IS NOT NULL THEN u.user_id END) as active_students,
                   AVG(i.quality_score) as avg_quality,
                   AVG(i.english_ratio) as avg_english,
                   COUNT(i.id) as total_interactions
            FROM users u
            LEFT JOIN interactions i ON u.user_id = i.user_id
        ''')
        
        stats = cursor.fetchone()
        
        cursor.execute('''
            SELECT u.user_name, COUNT(i.id) as interactions,
                   AVG(i.quality_score) as avg_quality,
                   AVG(i.english_ratio) as avg_english
            FROM users u
            LEFT JOIN interactions i ON u.user_id = i.user_id
            GROUP BY u.user_id, u.user_name
            ORDER BY interactions DESC
            LIMIT 10
        ''')
        
        rankings = cursor.fetchall()
        conn.close()
        
        total_students, active_students, avg_quality, avg_english, total_interactions = stats
        participation_rate = (active_students / total_students * 100) if total_students > 0 else 0
        
        ranking_html = ""
        for i, (name, interactions, quality, english) in enumerate(rankings, 1):
            rank_color = "#ffd700" if i <= 3 else "#c0c0c0"
            ranking_html += f'''
                <tr>
                    <td style="background: {rank_color}; color: white; font-weight: bold; text-align: center;">{i}</td>
                    <td><strong>{name}</strong></td>
                    <td>{interactions or 0}</td>
                    <td>{quality:.2f if quality else 0}</td>
                    <td>{english:.1%} if english else 0%</td>
                </tr>
            '''
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>班級整體分析報告</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
                .stat-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 12px; border: 1px solid #ddd; text-align: left; }}
                th {{ background: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>AI實務應用課程 - 班級整體分析</h1>
                <p>分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{total_students or 0}</div>
                        <div>班級總人數</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{active_students or 0}</div>
                        <div>活躍學生數</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{participation_rate:.1f}%</div>
                        <div>參與率</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{avg_quality:.2f if avg_quality else 0}</div>
                        <div>平均討論品質</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{avg_english:.1%} if avg_english else 0%</div>
                        <div>平均英語使用</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{total_interactions or 0}</div>
                        <div>總互動次數</div>
                    </div>
                </div>
                
                <h2>學生表現排行榜</h2>
                <table>
                    <tr>
                        <th>排名</th>
                        <th>學生姓名</th>
                        <th>互動次數</th>
                        <th>平均品質</th>
                        <th>英語使用比例</th>
                    </tr>
                    {ranking_html}
                </table>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/admin" style="color: #007bff; margin: 0 10px;">返回管理首頁</a>
                    <a href="/" style="color: #007bff; margin: 0 10px;">回到首頁</a>
                    <a href="/student_list" style="color: #007bff; margin: 0 10px;">學生列表</a>
                </div>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f"班級分析錯誤: {e}"

@app.route("/research_dashboard")
def research_dashboard():
    """研究儀表板"""
    try:
        if not ensure_db_exists():
            return '''
            <div style="text-align: center; padding: 50px; font-family: Microsoft JhengHei;">
                <h2>資料庫錯誤</h2>
                <p>資料庫初始化失敗</p>
                <a href="/" style="color: #007bff;">回到首頁</a>
            </div>
            '''
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM interactions')
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM interactions')
        active_students = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE date(created_at) = date("now")')
        today_usage = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(quality_score) FROM interactions WHERE quality_score > 0')
        avg_quality = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(english_ratio) FROM interactions WHERE english_ratio IS NOT NULL')
        avg_english = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>EMI教學研究數據儀表板</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
                .metric-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 15px; text-align: center; }}
                .metric-value {{ font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }}
                .metric-label {{ font-size: 1.1em; opacity: 0.9; }}
                .research-section {{ margin: 40px 0; padding: 30px; background: #f8f9fa; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>EMI教學研究數據儀表板</h1>
                <p>AI在生活與學習上的實務應用 - 教學實踐研究</p>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{total_interactions}</div>
                        <div class="metric-label">總互動次數</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{active_students}</div>
                        <div class="metric-label">活躍學生數</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{today_usage}</div>
                        <div class="metric-label">今日使用量</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{avg_quality:.1f}/5.0</div>
                        <div class="metric-label">討論品質平均分</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{avg_english:.1%}</div>
                        <div class="metric-label">英語使用比例</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">第{get_current_week()}週</div>
                        <div class="metric-label">當前課程進度</div>
                    </div>
                </div>
                
                <div class="research-section">
                    <h2>114年度教學實踐研究計畫</h2>
                    <h3>生成式AI輔助的雙語教學創新：提升EMI課程學生參與度與跨文化能力</h3>
                    <p>量化分析學生參與度、討論品質統計，支援教學實踐研究報告撰寫</p>
                </div>
                
                <div style="text-align: center; margin-top: 40px;">
                    <a href="/export_research_data" style="padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">匯出完整數據 (CSV)</a>
                    <a href="/student_list" style="padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">個人分析報告</a>
                    <a href="/class_analysis" style="padding: 12px 24px; background: #17a2b8; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">班級整體報告</a>
                    <a href="/admin" style="padding: 12px 24px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">返回管理首頁</a>
                </div>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f"研究儀表板錯誤: {e}"

@app.route("/export_research_data")
def export_research_data():
    """匯出研究數據"""
    try:
        if not ensure_db_exists():
            return "資料庫錯誤：無法匯出數據"
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_name, i.created_at, i.content, i.message_type,
                   i.quality_score, i.english_ratio, i.contains_keywords, i.group_id
            FROM users u
            JOIN interactions i ON u.user_id = i.user_id
            ORDER BY i.created_at
        ''')
        
        data = cursor.fetchall()
        conn.close()
        
        csv_content = "學生姓名,時間,內容,訊息類型,品質分數,英語比例,包含關鍵詞,群組互動\n"
        for row in data:
            content_preview = row[2][:50].replace('"', '""') if row[2] else ""
            csv_content += f'"{row[0]}","{row[1]}","{content_preview}...","{row[3]}",{row[4] or 0},{row[5] or 0},{row[6] or 0},"{row[7] or ""}"\n'
        
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=ai_course_research_data.csv"}
        )
        
    except Exception as e:
        return f"匯出錯誤: {e}"

@app.route("/health")
def health_check():
    """健康檢查"""
    db_status = ensure_db_exists()
    
    return jsonify({
        "status": "healthy" if db_status else "database_error",
        "timestamp": datetime.now().isoformat(),
        "system": "AI課程分析系統 v2.0",
        "line_bot_configured": line_bot_api is not None,
        "database_status": "connected" if db_status else "failed"
    })

@app.route("/test_db")
def test_db():
    """測試資料庫連接"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM interactions")
        interaction_count = cursor.fetchone()[0]
        
        conn.close()
        
        return f'''
        <div style="font-family: Microsoft JhengHei; margin: 20px; padding: 20px; background: white; border-radius: 10px;">
            <h2>資料庫連接測試</h2>
            <p><strong>狀態:</strong> 連接成功</p>
            <p><strong>表格:</strong> {[table[0] for table in tables]}</p>
            <p><strong>用戶數量:</strong> {user_count}</p>
            <p><strong>互動記錄:</strong> {interaction_count}</p>
            <a href="/admin" style="color: #007bff;">返回管理首頁</a>
        </div>
        '''
        
    except Exception as e:
        return f'''
        <div style="font-family: Microsoft JhengHei; margin: 20px; padding: 20px; background: white; border-radius: 10px;">
            <h2>資料庫連接測試</h2>
            <p><strong>狀態:</strong> 連接失敗</p>
            <p><strong>錯誤:</strong> {e}</p>
            <a href="/admin" style="color: #007bff;">返回管理首頁</a>
        </div>
        '''

@app.route("/init_db_manually")
def init_db_manually():
    """手動初始化資料庫"""
    success = init_db()
    
    if success:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #d4edda; margin: 20px; border-radius: 10px;">
            <h2>✅ 資料庫手動初始化成功！</h2>
            <p>資料庫已重新建立，包含示範數據</p>
            <p><a href="/test_db" style="color: #28a745; font-weight: bold;">測試資料庫連接</a></p>
            <p><a href="/admin" style="color: #007bff;">返回管理首頁</a></p>
        </div>
        '''
    else:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #f8d7da; margin: 20px; border-radius: 10px;">
            <h2>❌ 資料庫初始化失敗</h2>
            <p>請檢查系統權限和儲存空間</p>
            <p><a href="/admin" style="color: #007bff;">返回管理首頁</a></p>
        </div>
        '''

@app.route("/setup_guide")
def setup_guide():
    """設定指南"""
    return '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>LINE Bot 設定指南</title>
        <style>
            body { font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .step { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>LINE Bot 設定指南</h1>
            
            <div class="step">
                <h3>步驟 1: 建立 LINE Bot</h3>
                <p>1. 前往 LINE Developers (https://developers.line.biz/)</p>
                <p>2. 建立新的 Channel（Messaging API）</p>
                <p>3. 取得 Channel Access Token 和 Channel Secret</p>
            </div>
            
            <div class="step">
                <h3>步驟 2: 設定 Railway 環境變數</h3>
                <p>在 Railway 專案的 Variables 頁面設定：</p>
                <p>CHANNEL_ACCESS_TOKEN = 您的 Channel Access Token</p>
                <p>CHANNEL_SECRET = 您的 Channel Secret</p>
            </div>
            
            <div class="step">
                <h3>步驟 3: 設定 Webhook URL</h3>
                <p>在 LINE Developers Console 設定 Webhook URL：</p>
                <p>https://web-production-5a0e.up.railway.app/callback</p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/admin" style="color: #007bff;">返回管理首頁</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.errorhandler(404)
def not_found(error):
    return '''
    <div style="text-align: center; padding: 50px; font-family: Microsoft JhengHei;">
        <h2>頁面未找到</h2>
        <p>您要查找的頁面不存在</p>
        <a href="/" style="color: #007bff;">回到首頁</a>
    </div>
    ''', 404

@app.errorhandler(500)
def internal_error(error):
    return '''
    <div style="text-align: center; padding: 50px; font-family: Microsoft JhengHei;">
        <h2>系統錯誤</h2>
        <p>系統發生內部錯誤，請稍後再試</p>
        <a href="/" style="color: #007bff;">回到首頁</a>
    </div>
    ''', 500

# 應用啟動
if __name__ == "__main__":
    print("=== AI課程分析系統啟動 ===")
    print("正在初始化資料庫...")
    
    # 確保資料庫和基本數據存在
    if ensure_db_exists():
        print("✅ 資料庫初始化完成")
    else:
        print("❌ 資料庫初始化失敗")
    
    # 檢查LINE Bot狀態
    if line_bot_api:
        print("✅ LINE Bot 已配置")
    else:
        print("⚠️ LINE Bot 未配置 - 請設定環境變數")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 啟動應用於 port {port}")
    print("📋 可用功能:")
    print("   - 🏠 管理首頁 (/admin)")
    print("   - 📊 個人學習分析")
    print("   - 📈 班級整體分析") 
    print("   - 🔬 研究數據儀表板")
    print("   - 🔄 謹慎重設系統")
    print("   - 📅 學期週數管理")
    print("   - 📱 LINE Bot 互動記錄")
    print("=== 系統準備就緒 ===")
    
    app.run(host='0.0.0.0', port=port, debug=False)

# WSGI 應用入口點
application = app; background: #d1ecf1; margin: 20px; border-radius: 10px;">
            <h2>✅ 週次自動設定成功！</h2>
            <p>已自動設定為第 {auto_week} 週</p>
            <p><strong>本週主題：</strong>{COURSE_SCHEDULE_18_WEEKS.get(auto_week, {}).get('chinese', '')}</p>
            <p><a href="/semester_settings" style="color: #0c5460; font-weight: bold;">返回學期設定</a></p>
        </div>
        '''
    else:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #f8d7da; margin: 20px; border-radius: 10px;">
            <h2>❌ 自動設定失敗</h2>
            <p><a href="/semester_settings" style="color: #007bff;">返回設定頁面</a></p>
        </div>
        '''

@app.route("/admin_panel")
def admin_panel():
    """管理面板"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 統計資料
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id LIKE "demo_%"')
        demo_students = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id NOT LIKE "demo_%"')
        real_students = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id LIKE "demo_%"')
        demo_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id NOT LIKE "demo_%"')
        real_interactions = cursor.fetchone()[0]
        
        conn.close()
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>系統管理面板</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
                .demo-card {{ background: #e3f2fd; border: 2px solid #2196f3; }}
                .real-card {{ background: #e8f5e8; border: 2px solid #4caf50; }}
                .action-card {{ background: #fff3e0; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800; }}
                .btn {{ display: inline-block; padding: 12px 24px; margin: 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .btn-danger {{ background: #dc3545; color: white; }}
                .btn-warning {{ background: #ffc107; color: #333; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 學生分析系統 - 管理面板</h1>
                
                <div class="stats-grid">
                    <div class="stat-card demo-card">
                        <h3>🤖 虛擬學生</h3>
                        <p><strong>{demo_students}</strong> 位虛擬學生</p>
                        <p><strong>{demo_interactions}</strong> 筆示範互動</p>
                        <small>【虛擬】標示的測試數據</small>
                    </div>
                    <div class="stat-card real-card">
                        <h3>👨‍🎓 真實學生</h3>
                        <p><strong>{real_students}</strong> 位真實學生</p>
                        <p><strong>{real_interactions}</strong> 筆真實互動</p>
                        <small>LINE Bot 實際記錄</small>
                    </div>
                </div>
                
                <div class="action-card">
                    <h3>🔄 謹慎重設系統</h3>
                    <div class="warning">
                        <strong>⚠️ 重要：</strong>重設前請務必查看完整備份預覽！
                    </div>
                    
                    <a href="/backup_preview" class="btn btn-primary">
                        📋 查看完整備份預覽
                    </a>
                    <small>（重設前必看：檢視所有數據、下載備份檔案）</small><br>
                </div>
                
                <div class="action-card">
                    <h3>📅 學期管理</h3>
                    <a href="/semester_settings" class="btn btn-success">📅 學期設定與週數管理</a>
                    <small>（設定學期開始日期、調整當前週次）</small>
                </div>
                
                <div class="action-card">
                    <h3>📊 快速操作</h3>
                    <a href="/student_list" class="btn btn-success">查看學生列表</a>
                    <a href="/research_dashboard" class="btn btn-success">研究儀表板</a>
                    <a href="/export_research_data" class="btn btn-success">匯出數據</a>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/admin" style="color: #007bff;">← 返回管理首頁</a>
                    <a href="/" style="color: #007bff; margin-left: 20px;">回到首頁</a>
                </div>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f"管理面板錯誤: {e}"

@app.route("/backup_preview")
def backup_preview():
    """備份預覽頁面"""
    backup_data = export_complete_backup()
    
    if not backup_data:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #f8d7da; margin: 20px; border-radius: 10px;">
            <h2>❌ 無法產生備份</h2>
            <p>資料庫連接失敗</p>
            <p><a href="/admin_panel" style="color: #007bff;">返回管理面板</a></p>
        </div>
        '''
    
    stats = backup_data['statistics']
    config = backup_data['semester_config']
    
    # 生成用戶預覽
    users_preview = ""
    for i, user in enumerate(backup_data['users'][:10]):
        user_type = "🤖 虛擬" if user['user_id'].startswith('demo_') else "👨‍🎓 真實"
        users_preview += f"<tr><td>{user_type}</td><td>{user['user_name']}</td><td>{user['user_id']}</td></tr>"
    
    if len(backup_data['users']) > 10:
        users_preview += f"<tr><td colspan='3' style='text-align: center; color: #666;'>... 還有 {len(backup_data['users']) - 10} 位學生</td></tr>"
    
    # 生成互動預覽
    interactions_preview = ""
    for i, interaction in enumerate(backup_data['interactions'][-10:]):
        content_preview = interaction['content'][:30] + "..." if len(interaction['content']) > 30 else interaction['content']
        interactions_preview += f'''
        <tr>
            <td>{interaction['user_name']}</td>
            <td>{content_preview}</td>
            <td>{interaction['quality_score']:.1f}</td>
            <td>{interaction['created_at']}</td>
        </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>系統備份預覽</title>
        <style>
            body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
            .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
            .warning-card {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th, td {{ padding: 8px 12px; border: 1px solid #ddd; text-align: left; }}
            th {{ background: #f8f9fa; font-weight: bold; }}
            .btn {{ display: inline-block; padding: 12px 24px; margin: 10px 5px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
            .btn-success {{ background: #28a745; color: white; }}
            .btn-danger {{ background: #dc3545; color: white; }}
            .btn-primary {{ background: #007bff; color: white; }}
        </style>
        <script>
            function confirmReset(type) {{
                const messages = {{
                    'all': '⚠️ 重要警告！\\n\\n這將永久刪除所有數據：\\n• {stats["total_students"]} 位學生\\n• {stats["total_interactions"]} 筆互動記錄\\n• 所有分析結果\\n\\n此操作無法復原！\\n\\n確定要繼續嗎？',
                    'real': '確定要刪除所有 {stats["real_students"]} 位真實學生的數據嗎？\\n\\n將保留 {stats["demo_students"]} 位虛擬學生供測試使用。',
                    'demo': '確定要重新建立虛擬學生數據嗎？\\n\\n現有的 {stats["demo_students"]} 位虛擬學生數據將被重置。'
                }};
                return confirm(messages[type]);
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>📋 系統完整備份預覽</h1>
            <p>備份時間：{backup_data['backup_timestamp']}</p>
            
            <div class="warning-card">
                <h3>⚠️ 重設前請詳細檢查</h3>
                <p>以下是即將被影響的完整數據，請仔細確認後再進行重設操作！</p>
            </div>
            
            <h2>📊 系統統計</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h4>🤖 虛擬學生</h4>
                    <div style="font-size: 1.5em; color: #2196f3;">{stats['demo_students']}</div>
                    <small>{stats['demo_interactions']} 筆互動</small>
                </div>
                <div class="stat-card">
                    <h4>👨‍🎓 真實學生</h4>
                    <div style="font-size: 1.5em; color: #4caf50;">{stats['real_students']}</div>
                    <small>{stats['real_interactions']} 筆互動</small>
                </div>
                <div class="stat-card">
                    <h4>📅 學期設定</h4>
                    <div style="font-size: 1.2em;">第 {config['current_week']} 週</div>
                    <small>共 {config['total_weeks']} 週</small>
                </div>
                <div class="stat-card">
                    <h4>💾 總計</h4>
                    <div style="font-size: 1.5em; color: #ff9800;">{stats['total_interactions']}</div>
                    <small>筆完整記錄</small>
                </div>
            </div>
            
            <h2>👥 學生列表預覽</h2>
            <table>
                <tr><th>類型</th><th>姓名</th><th>ID</th></tr>
                {users_preview}
            </table>
            
            <h2>💬 最近互動預覽</h2>
            <table>
                <tr><th>學生</th><th>內容</th><th>品質</th><th>時間</th></tr>
                {interactions_preview}
            </table>
            
            <div class="warning-card">
                <h3>🔄 重設選項</h3>
                <p><strong>請選擇適當的重設方式：</strong></p>
                
                <a href="/download_backup" class="btn btn-success">💾 下載完整備份 (JSON)</a>
                <a href="/export_research_data" class="btn btn-success">📊 下載研究數據 (CSV)</a><br><br>
                
                <a href="/execute_reset_demo" onclick="return confirmReset('demo')" class="btn btn-primary">
                    🔄 重置虛擬學生數據
                </a>
                <small>（重新產生測試數據，不影響真實學生）</small><br>
                
                <a href="/execute_reset_real" onclick="return confirmReset('real')" class="btn btn-danger">
                    🧹 清除真實學生數據
                </a>
                <small>（刪除真實學生，保留虛擬學生）</small><br>
                
                <a href="/execute_reset_all" onclick="return confirmReset('all')" class="btn btn-danger">
                    💥 完全重設系統
                </a>
                <small>（刪除所有數據，重建空白系統）</small>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/admin" style="color: #007bff;">← 返回管理首頁</a>
                <a href="/admin_panel" style="color: #007bff; margin-left: 20px;">管理面板</a>
                <a href="/" style="color: #007bff; margin-left: 20px;">回到首頁</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/download_backup")
def download_backup():
    """下載完整備份檔案"""
    backup_data = export_complete_backup()
    
    if not backup_data:
        return "備份失敗：無法讀取資料庫"
    
    # 生成檔案名稱
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ai_course_backup_{timestamp}.json"
    
    # 轉換為JSON字符串
    json_content = json.dumps(backup_data, ensure_ascii=False, indent=2, default=str)
    
    return Response(
        json_content,
        mimetype="application/json",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

@app.route("/execute_reset_demo")
def execute_reset_demo():
    """執行虛擬學生數據重設"""
    success = reset_demo_data()
    
    if success:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #d1ecf1; margin: 20px; border-radius: 10px;">
            <h2>✅ 虛擬學生數據重建成功！</h2>
            <p>已重新建立8位虛擬學生和豐富的測試互動數據</p>
            <p>所有虛擬學生都有【虛擬】標示，方便區分</p>
            <p><a href="/student_list" style="color: #0c5460; font-weight: bold;">查看更新後的學生列表</a></p>
            <p><a href="/admin" style="color: #007bff;">返回管理首頁</a></p>
        </div>
        '''
    else:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #f8d7da; margin: 20px; border-radius: 10px;">
            <h2>❌ 虛擬學生數據重建失敗</h2>
            <p><a href="/admin" style="color: #007bff;">返回管理首頁</a></p>
        </div>
        '''

@app.route("/execute_reset_real")
def execute_reset_real():
    """執行真實學生數據清除"""
    success = clear_real_students_only()
    
    if success:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #fff3cd; margin: 20px; border-radius: 10px;">
            <h2>✅ 真實學生數據已清除！</h2>
            <p>已刪除所有真實學生的互動記錄</p>
            <p>虛擬學生數據已保留供測試使用</p>
            <p><a href="/student_list" style="color: #856404; font-weight: bold;">查看目前學生列表</a></p>
            <p><a href="/admin" style="color: #007bff;">返回管理首頁</a></p>
        </div>
        '''
    else:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #f8d7da; margin: 20px; border-radius: 10px;">
            <h2>❌ 清除失敗</h2>
            <p><a href="/admin" style="color: #007bff;">返回管理首頁</a></p>
        </div>
        '''

@app.route("/execute_reset_all")
def execute_reset_all():
    """執行完全系統重設"""
    success = reset_all_data()
    
    if success:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #d4edda; margin: 20px; border-radius: 10px;">
            <h2>✅ 系統完全重設成功！</h2>
            <p>所有數據已清除，並重新建立8位虛擬學生測試數據</p>
            <p><a href="/student_list" style="color: #28a745; font-weight: bold;">查看重設後的學生列表</a></p>
            <p><a href="/admin" style="color: #007bff;">返回管理首頁</a></p>
        </div>
        '''
    else:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #f8d7da; margin: 20px; border-radius: 10px;">
            <h2>❌ 系統重設失敗</h2>
            <p><a href="/admin" style="color: #007bff;">返回管理首頁</a></p>
        </div>
        '''

@app.route("/simulate_interaction", methods=['GET', 'POST'])
def simulate_interaction():
    """模擬LINE Bot互動"""
    if request.method == 'POST':
        user_name = request.form.get('user_name', 'Demo User')
        user_id = request.form.get('user_id', 'demo_user')
        message = request.form.get('message', '')
        is_group = request.form.get('is_group') == 'on'
        
        if message:
            ai_response = generate_ai_response(message, user_name)
            success = log_interaction(user_id, user_name, message, ai_response, is_group)
            
            status = "成功" if success else "失敗"
            
            return f'''
            <div style="font-family: Microsoft JhengHei; margin: 20px; padding: 20px; background: #f0f8ff; border-radius: 10px;">
                <h3>互動記錄：{status}</h3>
                <p><strong>學生:</strong> {user_name}</p>
                <p><strong>訊息:</strong> {message}</p>
                <p><strong>AI回應:</strong> {ai_response}</p>
                <p><strong>群組互動:</strong> {'是' if is_group else '否'}</p>
                <a href="/simulate_interaction" style="color: #007bff;">繼續測試</a> |
                <a href="/research_dashboard" style="color: #007bff;">查看數據</a>
            </div>
            '''
    
    return '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>LINE Bot 互動模擬器</title>
        <style>
            body { font-family: Microsoft JhengHei; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>LINE Bot 互動模擬器</h1>
            
            <form method="POST">
                <div class="form-group">
                    <label>學生姓名:</label>
                    <input type="text" name="user_name" value="York Chen" required>
                </div>
                
                <div class="form-group">
                    <label>學生ID:</label>
                    <input type="text" name="user_id" value="student001" required>
                </div>
                
                <div class="form-group">
                    <label>訊息內容:</label>
                    <textarea name="message" rows="4" placeholder="例如: What is machine learning?" required></textarea>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="is_group"> 群組互動 (模擬@AI呼叫)
                    </label>
                </div>
                
                <button type="submit">模擬互動</button>
            </form>
            
            <div style="margin-top: 30px; text-align: center;">
                <a href="/admin" style="color: #007bff; margin: 0 10px;">返回管理首頁</a>
                <a href="/" style="color: #007bff; margin: 0 10px;">回到首頁</a>
                <a href="/research_dashboard" style="color: #007bff; margin: 0 10px;">查看數據</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/student_list")
def student_list():
    """學生列表"""
    try:
        if not ensure_db_exists():
            return '''
            <div style="text-align: center; padding: 50px; font-family: Microsoft JhengHei;">
                <h2>資料庫錯誤</h2>
                <p>資料庫初始化失敗</p>
                <a href="/" style="color: #007bff;">回到首頁</a>
            </div>
            '''
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_id, u.user_name, COUNT(i.id) as total_interactions,
                   AVG(i.quality_score) as avg_quality, MAX(i.created_at) as last_activity
            FROM users u
            LEFT JOIN interactions i ON u.user_id = i.user_id
            GROUP BY u.user_id, u.user_name
            ORDER BY total_interactions DESC
        ''')
        
        students = cursor.fetchall()
        conn.close()
        
        student_rows = ""
        for student in students:
            user_id, user_name, interactions, quality, last_activity = student
            interactions = interactions or 0
            quality = quality or 0
            
            if interactions >= 5:
                status = "活躍"
                status_color = "#28a745"
            elif interactions >= 1:
                status = "正常"
                status_color = "#ffc107"
            else:
                status = "無互動"
                status_color = "#dc3545"
            
            last_date = "今日" if last_activity else "無記錄"
            
            student_rows += f'''
                <tr>
                    <td><strong>{user_name}</strong></td>
                    <td>{interactions}</td>
                    <td>{quality:.2f}</td>
                    <td>{last_date}</td>
                    <td><span style="background: {status_color}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8em;">{status}</span></td>
                    <td><a href="/student_analysis/{user_id}" style="padding: 6px 12px; background: #007bff; color: white; text-decoration: none; border-radius: 3px;">詳細分析</a></td>
                </tr>
            '''
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>學生個人分析列表</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 12px; border: 1px solid #ddd; text-align: left; }}
                th {{ background: #f8f9fa; font-weight: bold; }}
                tr:hover {{ background: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>學生個人分析系統</h1>
                <p>AI在生活與學習上的實務應用課程</p>
                
                <table>
                    <tr>
                        <th>學生姓名</th>
                        <th>互動次數</th>
                        <th>平均品質</th>
                        <th>最後活動</th>
                        <th>狀態</th>
                        <th>操作</th>
                    </tr>
                    {student_rows}
                </table>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/admin" style="color: #007bff; margin: 0 10px;">返回管理首頁</a>
                    <a href="/" style="color: #007bff; margin: 0 10px;">回到首頁</a>
                    <a href="/class_analysis" style="color: #007bff; margin: 0 10px;">班級分析</a>
                </div>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f"學生列表錯誤: {e}"

@app.route("/student_analysis/<user_id>")
def student_analysis(user_id):
    """個人分析頁面"""
    analysis = get_individual_student_analysis(user_id)
    
    if not analysis or not analysis.get('analysis_available'):
        return '''
        <div style="text-align: center; padding: 50px; font-family: Microsoft JhengHei;">
            <h2>個人學習分析</h2>
            <p>此學生暫無足夠的互動數據進行分析</p>
            <a href="/student_list" style="color: #007bff;">返回學生列表</a>
        </div>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    from flask import Flask, request, abort, jsonify, Response
import os
import sqlite3
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re
import csv
import io

app = Flask(__name__)

# LINE Bot 設定 - 兼容兩種環境變數名稱
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN') or os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET') or os.environ.get('CHANNEL_SECRET')

line_bot_api = None
handler = None

if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
    try:
        from linebot import LineBotApi, WebhookHandler
        from linebot.exceptions import InvalidSignatureError
        from linebot.models import MessageEvent, TextMessage, TextSendMessage
        
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(CHANNEL_SECRET)
        print("LINE Bot initialized successfully")
    except Exception as e:
        print(f"LINE Bot initialization failed: {e}")
        line_bot_api = None
        handler = None
else:
    print("LINE Bot environment variables not set")

# 18週課程設定
COURSE_SCHEDULE_18_WEEKS = {
    1: {"topic": "Course Introduction and AI Era Overview", "chinese": "課程介紹,人工智慧如何改變我們的生活?"},
    2: {"topic": "Generative AI Technologies", "chinese": "生成式AI技術 (ChatGPT, Claude等)"},
    3: {"topic": "Student Presentations 1", "chinese": "學生專題分享週(1)"},
    4: {"topic": "AI Applications in Learning", "chinese": "AI在學習上的應用"},
    5: {"topic": "Student Presentations 2", "chinese": "學生專題分享週(2)"},
    6: {"topic": "AI in Creative and Professional Fields", "chinese": "AI在創意與職場的應用"},
    7: {"topic": "Student Presentations 3", "chinese": "學生專題分享週(3)"},
    8: {"topic": "AI Tool Development and Customization", "chinese": "AI工具開發與客製化"},
    9: {"topic": "Student Presentations 4", "chinese": "學生專題分享週(4)"},
    10: {"topic": "AI Ethics and Responsible Use", "chinese": "AI倫理與責任使用"},
    11: {"topic": "AI in Research and Academic Writing", "chinese": "AI在研究與學術寫作的應用"},
    12: {"topic": "Student Presentations 5", "chinese": "學生專題分享週(5)"},
    13: {"topic": "Industry 4.0 and Smart Manufacturing", "chinese": "工業4.0與智慧製造"},
    14: {"topic": "Student Presentations 6", "chinese": "學生專題分享週(6)"},
    15: {"topic": "AI in Home and Daily Life", "chinese": "AI在居家與日常生活的應用"},
    16: {"topic": "Student Presentations 7", "chinese": "學生專題分享週(7)"},
    17: {"topic": "Future Trends and Career Preparation", "chinese": "未來趨勢與職涯準備"},
    18: {"topic": "Final Review and Course Reflection", "chinese": "期末回顧與課程反思"}
}

# 資料庫相關函數
def get_db_connection():
    """建立資料庫連接"""
    db_path = os.path.join(os.getcwd(), 'course_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_db_exists():
    """確保資料庫存在"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 檢查主要表格
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            conn.close()
            return init_db()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interactions'")
        if not cursor.fetchone():
            conn.close()
            return init_db()
        
        # 確保學期設定表格存在
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semester_config (
                id INTEGER PRIMARY KEY,
                semester_start DATE,
                current_week INTEGER DEFAULT 1,
                total_weeks INTEGER DEFAULT 18,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Database check failed: {e}")
        return init_db()

def init_db():
    """初始化資料庫"""
    try:
        print("Starting database initialization...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DROP TABLE IF EXISTS interactions')
        cursor.execute('DROP TABLE IF EXISTS users')
        cursor.execute('DROP TABLE IF EXISTS semester_config')
        
        cursor.execute('''
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL,
                is_demo INTEGER DEFAULT 0,
                first_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_name TEXT,
                content TEXT,
                ai_response TEXT,
                message_type TEXT,
                quality_score REAL,
                english_ratio REAL,
                contains_keywords INTEGER,
                group_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE semester_config (
                id INTEGER PRIMARY KEY,
                semester_start DATE,
                current_week INTEGER DEFAULT 1,
                total_weeks INTEGER DEFAULT 18,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 初始化學期設定
        default_start = datetime(2025, 2, 17).date()
        cursor.execute('''
            INSERT INTO semester_config (semester_start, current_week, total_weeks) 
            VALUES (?, 1, 18)
        ''', (default_start,))
        
        conn.commit()
        conn.close()
        print("Database initialization completed")
        
        create_demo_data()
        return True
        
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

def create_demo_data():
    """創建示範數據 - 加強版虛擬學生標示"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id LIKE "demo_%"')
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # 虛擬學生資料 - 明確標示
        demo_students = [
            ('demo_student001', '【虛擬】陳建宏 York Chen'),
            ('demo_student002', '【虛擬】王雅琳 Alice Wang'),
            ('demo_student003', '【虛擬】林志明 Bob Lin'),
            ('demo_student004', '【虛擬】劉詩涵 Catherine Liu'),
            ('demo_student005', '【虛擬】張大衛 David Chang'),
            ('demo_student006', '【虛擬】黃美玲 Emma Huang'),
            ('demo_student007', '【虛擬】李俊傑 Frank Lee'),
            ('demo_student008', '【虛擬】吳佩君 Grace Wu')
        ]
        
        for user_id, user_name in demo_students:
            cursor.execute('INSERT INTO users (user_id, user_name, is_demo) VALUES (?, ?, 1)', (user_id, user_name))
        
        # 豐富的示範互動數據
        demo_interactions = [
            # 高活躍學生 - York Chen
            ('demo_student001', '【虛擬】陳建宏 York Chen', 'What is artificial intelligence and how does it impact our daily life?', 'AI response...', 'question', 4.5, 0.9, 1, None),
            ('demo_student001', '【虛擬】陳建宏 York Chen', 'AI在教育領域的應用非常廣泛，特別是個人化學習', 'AI response...', 'discussion', 4.2, 0.6, 1, 'group'),
            ('demo_student001', '【虛擬】陳建宏 York Chen', 'How can we ensure AI ethics in machine learning algorithms?', 'AI response...', 'question', 4.7, 0.95, 1, None),
            ('demo_student001', '【虛擬】陳建宏 York Chen', 'Industry 4.0 requires integration of AI and IoT technologies', 'AI response...', 'discussion', 4.3, 0.85, 1, 'group'),
            ('demo_student001', '【虛擬】陳建宏 York Chen', 'Can you explain the difference between supervised and unsupervised learning?', 'AI response...', 'question', 4.6, 0.92, 1, None),
            
            # 中等活躍學生 - Alice Wang
            ('demo_student002', '【虛擬】王雅琳 Alice Wang', 'How does machine learning work in recommendation systems?', 'AI response...', 'question', 4.1, 0.88, 1, None),
            ('demo_student002', '【虛擬】王雅琳 Alice Wang', '我認為生成式AI對創意產業影響很大', 'AI response...', 'discussion', 3.8, 0.4, 1, 'group'),
            ('demo_student002', '【虛擬】王雅琳 Alice Wang', 'What are the limitations of current AI technology?', 'AI response...', 'question', 4.0, 0.82, 1, None),
            
            # 英語學習者 - Bob Lin
            ('demo_student003', '【虛擬】林志明 Bob Lin', 'AI applications in smart manufacturing很有趣', 'AI response...', 'discussion', 3.5, 0.7, 1, 'group'),
            ('demo_student003', '【虛擬】林志明 Bob Lin', '請問machine learning和deep learning有什麼不同？', 'AI response...', 'question', 3.2, 0.3, 1, None),
            ('demo_student003', '【虛擬】林志明 Bob Lin', 'IoT devices can collect data for AI analysis', 'AI response...', 'response', 3.6, 0.75, 1, 'group'),
            
            # 較少參與學生 - Catherine Liu
            ('demo_student004', '【虛擬】劉詩涵 Catherine Liu', '生成式AI的應用很廣泛，但需要注意倫理問題', 'AI response...', 'response', 3.0, 0.2, 1, None),
            ('demo_student004', '【虛擬】劉詩涵 Catherine Liu', 'AI工具可以幫助提升學習效率', 'AI response...', 'discussion', 2.8, 0.15, 1, 'group'),
            
            # 新加入學生 - David Chang
            ('demo_student005', '【虛擬】張大衛 David Chang', 'What is ChatGPT?', 'AI response...', 'question', 3.5, 0.8, 1, None),
            
            # 積極英語使用者 - Emma Huang
            ('demo_student006', '【虛擬】黃美玲 Emma Huang', 'How can AI help in language learning and cross-cultural communication?', 'AI response...', 'question', 4.4, 0.95, 1, None),
            ('demo_student006', '【虛擬】黃美玲 Emma Huang', 'The ethical implications of AI in education are significant', 'AI response...', 'discussion', 4.2, 0.92, 1, 'group'),
            
            # 技術探討者 - Frank Lee
            ('demo_student007', '【虛擬】李俊傑 Frank Lee', 'Neural networks和傳統programming有什麼差別？', 'AI response...', 'question', 3.8, 0.5, 1, None),
            ('demo_student007', '【虛擬】李俊傑 Frank Lee', 'AI在healthcare方面的應用需要更嚴格的regulation', 'AI response...', 'discussion', 4.0, 0.6, 1, 'group'),
            
            # 觀察型學習者 - Grace Wu
            ('demo_student008', '【虛擬】吳佩君 Grace Wu', '謝謝老師的說明，我對AI有更深的了解了', 'AI response...', 'response', 2.5, 0.1, 1, None)
        ]
        
        for interaction in demo_interactions:
            cursor.execute('''
                INSERT INTO interactions 
                (user_id, user_name, content, ai_response, message_type, quality_score, 
                 english_ratio, contains_keywords, group_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', interaction)
        
        conn.commit()
        conn.close()
        print("Enhanced demo data with virtual student labels created successfully")
        
    except Exception as e:
        print(f"Demo data creation failed: {e}")

# 學期設定相關函數
def get_semester_config():
    """取得學期設定"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM semester_config ORDER BY id DESC LIMIT 1')
        config = cursor.fetchone()
        
        if not config:
            # 預設設定：2025年春季學期
            default_start = datetime(2025, 2, 17).date()
            cursor.execute('''
                INSERT INTO semester_config (semester_start, current_week, total_weeks) 
                VALUES (?, 1, 18)
            ''', (default_start,))
            conn.commit()
            config = (1, default_start, 1, 18, datetime.now())
        
        conn.close()
        return {
            'semester_start': config[1] if isinstance(config[1], str) else config[1],
            'current_week': config[2],
            'total_weeks': config[3],
            'updated_at': config[4]
        }
    except Exception as e:
        print(f"Semester config error: {e}")
        return {
            'semester_start': datetime(2025, 2, 17).date(),
            'current_week': 1,
            'total_weeks': 18,
            'updated_at': datetime.now()
        }

def update_semester_config(semester_start, current_week):
    """更新學期設定"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO semester_config (semester_start, current_week, total_weeks) 
            VALUES (?, ?, 18)
        ''', (semester_start, current_week))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Update semester config error: {e}")
        return False

def calculate_current_week_from_date():
    """根據日期自動計算當前週次"""
    config = get_semester_config()
    
    if isinstance(config['semester_start'], str):
        semester_start = datetime.strptime(config['semester_start'], '%Y-%m-%d').date()
    else:
        semester_start = config['semester_start']
    
    current_date = datetime.now().date()
    days_passed = (current_date - semester_start).days
    week = min(max(1, (days_passed // 7) + 1), 18)
    return week

def get_current_week():
    """取得當前課程週次"""
    config = get_semester_config()
    return config['current_week']

# 備份相關函數
def export_complete_backup():
    """匯出完整的系統備份"""
    try:
        if not ensure_db_exists():
            return None
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 匯出所有用戶
        cursor.execute('SELECT * FROM users')
        users_data = [dict(row) for row in cursor.fetchall()]
        
        # 匯出所有互動
        cursor.execute('SELECT * FROM interactions ORDER BY created_at')
        interactions_data = [dict(row) for row in cursor.fetchall()]
        
        # 匯出學期設定
        config = get_semester_config()
        
        # 統計資料
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id LIKE "demo_%"')
        demo_students_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id NOT LIKE "demo_%"')
        real_students_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id LIKE "demo_%"')
        demo_interactions_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id NOT LIKE "demo_%"')
        real_interactions_count = cursor.fetchone()[0]
        
        conn.close()
        
        backup_data = {
            'backup_timestamp': datetime.now().isoformat(),
            'semester_config': config,
            'statistics': {
                'demo_students': demo_students_count,
                'real_students': real_students_count,
                'demo_interactions': demo_interactions_count,
                'real_interactions': real_interactions_count,
                'total_students': demo_students_count + real_students_count,
                'total_interactions': demo_interactions_count + real_interactions_count
            },
            'users': users_data,
            'interactions': interactions_data
        }
        
        return backup_data
        
    except Exception as e:
        print(f"Backup export error: {e}")
        return None

# 重設相關函數
def reset_all_data():
    """完全重設所有數據"""
    try:
        print("Starting complete data reset...")
        return init_db()
    except Exception as e:
        print(f"Data reset failed: {e}")
        return False

def clear_real_students_only():
    """僅清除真實學生數據，保留虛擬學生"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 刪除非demo的互動記錄
        cursor.execute('DELETE FROM interactions WHERE user_id NOT LIKE "demo_%"')
        
        # 刪除非demo的用戶
        cursor.execute('DELETE FROM users WHERE user_id NOT LIKE "demo_%"')
        
        conn.commit()
        conn.close()
        
        print("Real student data cleared, demo data preserved")
        return True
        
    except Exception as e:
        print(f"Real student data clearing failed: {e}")
        return False

def reset_demo_data():
    """重新建立虛擬學生數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM interactions WHERE user_id LIKE "demo_%"')
        cursor.execute('DELETE FROM users WHERE user_id LIKE "demo_%"')
        
        conn.commit()
        conn.close()
        
        # 重新建立虛擬學生數據
        create_demo_data()
        return True
        
    except Exception as e:
        print(f"Demo data reset failed: {e}")
        return False

# 分析相關函數
def calculate_quality_score(content):
    """計算討論品質分數"""
    score = 1.0
    content_lower = content.lower()
    
    if len(content) > 50: score += 0.5
    if len(content) > 100: score += 0.5
    if len(content) > 200: score += 0.5
    
    academic_keywords = ['analysis', 'research', 'theory', 'methodology', 'evaluation']
    if any(keyword in content_lower for keyword in academic_keywords):
        score += 1.0
    
    if any(keyword in content_lower for keyword in ['ai', 'artificial intelligence', 'machine learning']):
        score += 0.5
    
    if any(char in content for char in ['?', '？']):
        score += 0.5
    
    return min(score, 5.0)

def calculate_english_ratio(content):
    """計算英語使用比例"""
    english_chars = sum(1 for c in content if c.isalpha() and ord(c) < 128)
    total_chars = len(content.replace(' ', ''))
    return english_chars / max(total_chars, 1) if total_chars > 0 else 0

def detect_message_type(content):
    """檢測訊息類型"""
    content_lower = content.lower()
    if any(char in content for char in ['?', '？']):
        return 'question'
    elif any(word in content_lower for word in ['i think', 'analysis', '我覺得', '分析']):
        return 'discussion'
    else:
        return 'response'

def log_interaction(user_id, user_name, content, ai_response, is_group=False):
    """記錄互動到資料庫"""
    try:
        if not ensure_db_exists():
            return False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('INSERT OR IGNORE INTO users (user_id, user_name, is_demo) VALUES (?, ?, 0)', (user_id, user_name))
        
        quality_score = calculate_quality_score(content)
        english_ratio = calculate_english_ratio(content)
        message_type = detect_message_type(content)
        contains_keywords = 1
        group_id = "group" if is_group else None
        
        cursor.execute('''
            INSERT INTO interactions 
            (user_id, user_name, content, ai_response, message_type, quality_score, 
             english_ratio, contains_keywords, group_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, content, ai_response, message_type, quality_score, 
              english_ratio, contains_keywords, group_id))
        
        conn.commit()
        conn.close()
        print(f"Interaction logged: {user_name}")
        return True
        
    except Exception as e:
        print(f"Failed to log interaction: {e}")
        return False

def generate_ai_response(message, user_name):
    """生成AI回應"""
    current_week = get_current_week()
    week_info = COURSE_SCHEDULE_18_WEEKS.get(current_week, {})
    
    responses = [
        f"Hi {user_name}! 這週我們討論「{week_info.get('chinese', '課程內容')}」。",
        f"很好的問題！關於{message[:20]}...",
        f"根據第{current_week}週的課程內容，我建議...",
        f"這個觀點很有趣！在AI應用方面..."
    ]
    
    import random
    return random.choice(responses)

def is_group_message(event):
    """檢查是否為群組訊息"""
    try:
        return hasattr(event.source, 'group_id') and event.source.group_id is not None
    except:
        return False

def get_individual_student_analysis(user_id):
    """獲取個別學生分析"""
    try:
        if not ensure_db_exists():
            return None
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_name FROM users WHERE user_id = ?', (user_id,))
        user_info = cursor.fetchone()
        if not user_info:
            conn.close()
            return None
        
        cursor.execute('''
            SELECT created_at, message_type, content, quality_score, 
                   contains_keywords, english_ratio, group_id
            FROM interactions 
            WHERE user_id = ?
            ORDER BY created_at
        ''', (user_id,))
        
        interactions = cursor.fetchall()
        conn.close()
        
        if not interactions:
            return {'user_name': user_info[0], 'analysis_available': False}
        
        return analyze_individual_performance(interactions, user_info[0], user_id)
        
    except Exception as e:
        print(f"Individual analysis error: {e}")
        return None

def analyze_individual_performance(interactions, user_name, user_id):
    """分析個人表現"""
    total_interactions = len(interactions)
    dates = [datetime.fromisoformat(row[0]).date() for row in interactions]
    
    active_days = len(set(dates))
    study_period = (max(dates) - min(dates)).days + 1 if len(dates) > 1 else 1
    
    qualities = [row[3] for row in interactions if row[3] > 0]
    avg_quality = sum(qualities) / len(qualities) if qualities else 0
    
    english_ratios = [row[5] for row in interactions if row[5] is not None]
    avg_english = sum(english_ratios) / len(english_ratios) if english_ratios else 0
    
    questions = [row for row in interactions if row[1] == 'question']
    
    # 參與度等級
    if total_interactions >= 15:
        participation_level = "高度活躍"
        level_color = "#28a745"
    elif total_interactions >= 8:
        participation_level = "中度活躍"
        level_color = "#ffc107"
    elif total_interactions >= 3:
        participation_level = "偶爾參與"
        level_color = "#fd7e14"
    else:
        participation_level = "較少參與"
        level_color = "#dc3545"
    
    # 品質趨勢
    if len(qualities) >= 3:
        recent = sum(qualities[-3:]) / 3
        early = sum(qualities[:3]) / 3
        if recent > early + 0.5:
            quality_trend = "明顯進步"
        elif recent > early + 0.2:
            quality_trend = "穩定進步"
        else:
            quality_trend = "穩定維持"
    else:
        quality_trend = "數據不足"
    
    # 雙語能力
    if avg_english >= 0.8:
        bilingual_ability = "優秀雙語使用者"
    elif avg_english >= 0.6:
        bilingual_ability = "良好雙語能力"
    elif avg_english >= 0.4:
        bilingual_ability = "中等雙語能力"
    else:
        bilingual_ability = "主要使用中文"
    
    # 提問模式
    question_ratio = len(questions) / total_interactions if total_interactions > 0 else 0
    if question_ratio >= 0.4:
        questioning_pattern = "積極提問者"
    elif question_ratio >= 0.2:
        questioning_pattern = "適度提問"
    else:
        questioning_pattern = "較少提問"
    
    # 綜合評估
    scores = []
    if total_interactions >= 15:
        scores.append(9)
    elif total_interactions >= 8:
        scores.append(7)
    else:
        scores.append(5)
    
    scores.append(min(avg_quality * 2, 10))
    scores.append(min(avg_english * 10, 10))
    
    overall_score = sum(scores) / len(scores)
    
    if overall_score >= 8:
        performance_level = "優秀"
    elif overall_score >= 6:
        performance_level = "良好"
    else:
        performance_level = "需改進"
    
    return {
        'user_name': user_name,
        'user_id': user_id,
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'study_period_days': study_period,
        'analysis_available': True,
        'participation': {
            'total_interactions': total_interactions,
            'active_days': active_days,
            'avg_weekly_activity': round(total_interactions / max(study_period/7, 1), 1),
            'participation_level': participation_level,
            'level_color': level_color,
            'consistency_score': round(active_days / study_period * 100, 1)
        },
        'quality': {
            'avg_quality': round(avg_quality, 2),
            'high_quality_count': sum(1 for q in qualities if q >= 4.0),
            'quality_trend': quality_trend
        },
        'english_usage': {
            'avg_english_ratio': avg_english,
            'bilingual_ability': bilingual_ability
        },
        'questioning': {
            'total_questions': len(questions),
            'question_ratio': question_ratio,
            'questioning_pattern': questioning_pattern
        },
        'overall_assessment': {
            'overall_score': round(overall_score, 1),
            'performance_level': performance_level,
            'learning_style': "穩健學習者",
            'strengths': ["持續努力中"],
            'improvement_suggestions': ["建議保持學習節奏"]
        }
    }

# LINE Bot 路由
if line_bot_api and handler:
    @app.route("/callback", methods=['POST'])
    def callback():
        signature = request.headers['X-Line-Signature']
        body = request.get_data(as_text=True)
        
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)
        
        return 'OK'

    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        try:
            user_message = event.message.text
            user_id = event.source.user_id
            
            try:
                profile = line_bot_api.get_profile(user_id)
                user_name = profile.display_name
            except:
                user_name = f"User{user_id[:8]}"
            
            is_group = is_group_message(event)
            if is_group:
                if not user_message.strip().startswith('@AI'):
                    return
                user_message = user_message.replace('@AI', '').strip()
                if not user_message:
                    user_message = "Hi"
            
            ai_response = generate_ai_response(user_message, user_name)
            log_interaction(user_id, user_name, user_message, ai_response, is_group)
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=ai_response)
            )
            
        except Exception as e:
            print(f"Message handling error: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，處理訊息時發生錯誤。")
            )
else:
    @app.route("/callback", methods=['POST'])
    def callback():
        return jsonify({"error": "LINE Bot not configured"})

# 網頁路由
@app.route("/")
def home():
    """一般首頁 - 加入管理入口"""
    line_bot_status = "已配置" if line_bot_api else "未配置"
    db_status = "正常" if ensure_db_exists() else "異常"
    
    config = get_semester_config()
    current_week = config['current_week']
    week_info = COURSE_SCHEDULE_18_WEEKS.get(current_week, {})
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>AI實務應用課程分析系統</title>
        <style>
            body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .header {{ text-align: center; margin-bottom: 40px; color: #333; }}
            .week-banner {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center; }}
            .week-number {{ font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }}
            .status {{ background: #28a745; color: white; padding: 8px 16px; border-radius: 20px; margin: 10px; }}
            .warning {{ background: #ffc107; color: #333; padding: 8px 16px; border-radius: 20px; margin: 10px; }}
            .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            .card {{ background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
            .admin-btn {{ background: #dc3545; }}
            .teacher-btn {{ background: #28a745; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AI在生活與學習上的實務應用</h1>
                <p>通識教育中心 | 授課教師：曾郁堯</p>
                <span class="{'status' if line_bot_api else 'warning'}">LINE Bot狀態: {line_bot_status}</span>
                <span class="{'status' if db_status == '正常' else 'warning'}">資料庫狀態: {db_status}</span>
            </div>
            
            <div class="week-banner">
                <div class="week-number">第 {current_week} 週</div>
                <div style="font-size: 1.2em; margin-bottom: 5px;">{week_info.get('chinese', '課程內容')}</div>
                <div style="font-size: 1em; opacity: 0.9;">{week_info.get('topic', '')}</div>
                <div style="margin-top: 10px;">
                    <a href="/semester_settings" style="color: white; text-decoration: underline;">📅 管理學期設定</a>
                </div>
            </div>
            
            <!-- 教師專區 -->
            <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center;">
                <h2>🎓 教師專區</h2>
                <p>完整的課程管理和分析工具</p>
                <a href="/admin" class="btn teacher-btn" style="background: white; color: #28a745; font-weight: bold; margin: 10px;">
                    🏠 進入教師管理首頁
                </a>
            </div>
            
            <div class="cards">
                <div class="card">
                    <h3>個人學習分析</h3>
                    <p>查看每位學生的詳細學習報告和進步軌跡</p>
                    <a href="/student_list" class="btn">學生列表</a>
                </div>
                <div class="card">
                    <h3>班級整體分析</h3>
                    <p>全班學習狀況統計和教學成效評估</p>
                    <a href="/class_analysis" class="btn">班級分析</a>
                </div>
                <div class="card">
                    <h3>研究數據儀表板</h3>
                    <p>EMI教學實踐研究數據追蹤</p>
                    <a href="/research_dashboard" class="btn">研究儀表板</a>
                </div>
                <div class="card">
                    <h3>互動模擬器</h3>
                    <p>模擬LINE Bot互動，測試數據記錄功能</p>
                    <a href="/simulate_interaction" class="btn">開始模擬</a>
                </div>
                <div class="card">
                    <h3>數據匯出</h3>
                    <p>匯出完整的學習數據，支援研究分析</p>
                    <a href="/export_research_data" class="btn">匯出數據</a>
                </div>
                <div class="card">
                    <h3>系統管理</h3>
                    <p>重設系統、備份數據、學期設定</p>
                    <a href="/admin_panel" class="btn admin-btn">管理面板</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/admin")
def admin_homepage():
    """管理首頁 - 教師專用管理介面"""
    try:
        # 取得系統狀態
        db_status = ensure_db_exists()
        line_bot_status = line_bot_api is not None
        config = get_semester_config()
        current_week = config['current_week']
        week_info = COURSE_SCHEDULE_18_WEEKS.get(current_week, {})
        
        # 取得統計數據
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id LIKE "demo_%"')
        demo_students = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id NOT LIKE "demo_%"')
        real_students = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id LIKE "demo_%"')
        demo_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id NOT LIKE "demo_%"')
        real_interactions = cursor.fetchone()[0]
        
        # 今日活動
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE date(created_at) = date("now")')
        today_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM interactions WHERE date(created_at) = date("now")')
        today_active_users = cursor.fetchone()[0]
        
        # 最近活動
        cursor.execute('''
            SELECT user_name, content, created_at, quality_score
            FROM interactions 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        recent_activities = cursor.fetchall()
        
        # 本週統計
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE created_at >= date('now', '-7 days')
        ''')
        week_interactions = cursor.fetchone()[0]
        
        conn.close()
        
        # 生成最近活動HTML
        recent_html = ""
        for activity in recent_activities:
            user_name, content, created_at, quality = activity
            content_preview = content[:40] + "..." if len(content) > 40 else content
            time_str = datetime.fromisoformat(created_at).strftime('%m/%d %H:%M')
            recent_html += f'''
            <div style="padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 5px; border-left: 3px solid #007bff;">
                <div style="font-weight: bold; color: #333;">{user_name}</div>
                <div style="color: #666; font-size: 0.9em;">{content_preview}</div>
                <div style="color: #999; font-size: 0.8em;">品質: {quality:.1f} | {time_str}</div>
            </div>
            '''
        
        if not recent_html:
            recent_html = '<p style="color: #666; text-align: center;">尚無互動記錄</p>'
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>教師管理首頁 - AI課程分析系統</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 0; background: #f5f7fa; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }}
                .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
                .dashboard-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 30px; }}
                .main-content {{ display: grid; grid-template-rows: auto auto 1fr; gap: 20px; }}
                .sidebar {{ display: grid; grid-template-rows: auto auto 1fr; gap: 20px; }}
                
                .status-banner {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .week-info {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
                .week-number {{ font-size: 2em; font-weight: bold; margin-bottom: 10px; }}
                
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
                .stat-value {{ font-size: 2em; font-weight: bold; margin-bottom: 5px; }}
                .demo-value {{ color: #2196f3; }}
                .real-value {{ color: #4caf50; }}
                .today-value {{ color: #ff9800; }}
                .week-value {{ color: #9c27b0; }}
                
                .management-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
                .management-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .management-card h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                
                .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 5px; font-weight: bold; transition: all 0.3s; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .btn-warning {{ background: #ffc107; color: #333; }}
                .btn-danger {{ background: #dc3545; color: white; }}
                .btn-info {{ background: #17a2b8; color: white; }}
                .btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }}
                
                .recent-activities {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .status-indicator {{ padding: 5px 10px; border-radius: 15px; font-size: 0.8em; font-weight: bold; }}
                .status-ok {{ background: #d4edda; color: #155724; }}
                .status-warning {{ background: #fff3cd; color: #856404; }}
                .status-error {{ background: #f8d7da; color: #721c24; }}
                
                .quick-stats {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="container">
                    <h1>🎓 教師管理首頁</h1>
                    <p>AI在生活與學習上的實務應用 | 授課教師：曾郁堯</p>
                </div>
            </div>
            
            <div class="container">
                <div class="dashboard-grid">
                    <div class="main-content">
                        <!-- 系統狀態橫幅 -->
                        <div class="status-banner">
                            <h2>📊 系統狀態總覽</h2>
                            <div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap;">
                                <span class="status-indicator {'status-ok' if db_status else 'status-error'}">
                                    資料庫: {'正常' if db_status else '異常'}
                                </span>
                                <span class="status-indicator {'status-ok' if line_bot_status else 'status-warning'}">
                                    LINE Bot: {'已配置' if line_bot_status else '未配置'}
                                </span>
                                <span class="status-indicator status-ok">
                                    學生總數: {demo_students + real_students} 位
                                </span>
                                <span class="status-indicator status-ok">
                                    互動總數: {demo_interactions + real_interactions} 筆
                                </span>
                            </div>
                        </div>
                        
                        <!-- 統計數據 -->
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-value demo-value">{demo_students}</div>
                                <div>🤖 虛擬學生</div>
                                <small>{demo_interactions} 筆互動</small>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value real-value">{real_students}</div>
                                <div>👨‍🎓 真實學生</div>
                                <small>{real_interactions} 筆互動</small>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value today-value">{today_interactions}</div>
                                <div>📅 今日互動</div>
                                <small>{today_active_users} 位活躍學生</small>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value week-value">{week_interactions}</div>
                                <div>📈 本週互動</div>
                                <small>最近7天統計</small>
                            </div>
                        </div>
                        
                        <!-- 管理功能 -->
                        <div class="management-grid">
                            <div class="management-card">
                                <h3>📚 教學分析</h3>
                                <a href="/student_list" class="btn btn-primary">👥 學生列表</a>
                                <a href="/class_analysis" class="btn btn-success">📊 班級分析</a>
                                <a href="/research_dashboard" class="btn btn-info">🔬 研究儀表板</a>
                                <a href="/export_research_data" class="btn btn-warning">📄 匯出數據</a>
                            </div>
                            
                            <div class="management-card">
                                <h3>⚙️ 系統管理</h3>
                                <a href="/backup_preview" class="btn btn-primary">💾 備份與重設</a>
                                <a href="/semester_settings" class="btn btn-success">📅 學期設定</a>
                                <a href="/simulate_interaction" class="btn btn-info">🧪 互動測試</a>
                                <a href="/setup_guide" class="btn btn-warning">📋 設定指南</a>
                            </div>
                            
                            <div class="management-card">
                                <h3>🔧 系統工具</h3>
                                <a href="/health" class="btn btn-success">💚 健康檢查</a>
                                <a href="/test_db" class="btn btn-info">🗃️ 資料庫測試</a>
                                <a href="/init_db_manually" class="btn btn-warning">🔄 手動初始化</a>
                                <a href="/download_backup" class="btn btn-danger">⬇️ 下載備份</a>
                            </div>
                        </div>
                    </div>
                    
                    <div class="sidebar">
                        <!-- 當前課程週次 -->
                        <div class="week-info">
                            <div class="week-number">第 {current_week} 週</div>
                            <div style="margin-bottom: 10px;">{week_info.get('chinese', '課程內容')}</div>
                            <div style="font-size: 0.9em; opacity: 0.9;">{week_info.get('topic', '')}</div>
                            <div style="margin-top: 15px;">
                                <a href="/semester_settings" style="color: white; text-decoration: underline;">
                                    📅 調整週次設定
                                </a>
                            </div>
                        </div>
                        
                        <!-- 快速統計 -->
                        <div class="quick-stats">
                            <h3>📈 快速統計</h3>
                            <div style="margin: 10px 0;">
                                <strong>學期設定：</strong><br>
                                開始日期：{config['semester_start']}<br>
                                總週數：{config['total_weeks']} 週
                            </div>
                            <div style="margin: 10px 0;">
                                <strong>參與率：</strong><br>
                                {((real_students / max(real_students + demo_students, 1)) * 100):.1f}% 真實學生
                            </div>
                            <div style="margin: 10px 0;">
                                <strong>系統版本：</strong><br>
                                AI課程分析系統 v2.0
                            </div>
                        </div>
                        
                        <!-- 最近活動 -->
                        <div class="recent-activities">
                            <h3>🕒 最近活動</h3>
                            {recent_html}
                            <div style="text-align: center; margin-top: 15px;">
                                <a href="/student_list" style="color: #007bff; font-size: 0.9em;">查看所有活動 →</a>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 底部導航 -->
                <div style="text-align: center; margin-top: 30px; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <a href="/" class="btn btn-primary">🏠 回到一般首頁</a>
                    <a href="/admin_panel" class="btn btn-info">🔧 舊版管理面板</a>
                    <a href="https://docs.anthropic.com" class="btn btn-success" target="_blank">📚 Claude文件</a>
                </div>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f'''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #f8d7da; margin: 20px; border-radius: 10px;">
            <h2>❌ 管理首頁載入錯誤</h2>
            <p>錯誤：{e}</p>
            <p><a href="/" style="color: #007bff;">回到首頁</a></p>
        </div>
        '''

@app.route("/semester_settings")
def semester_settings():
    """學期設定頁面"""
    config = get_semester_config()
    auto_week = calculate_current_week_from_date()
    
    # 格式化日期
    if isinstance(config['semester_start'], str):
        semester_start_str = config['semester_start']
    else:
        semester_start_str = config['semester_start'].strftime('%Y-%m-%d')
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>學期設定與週數管理</title>
        <style>
            body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .info-card {{ background: #e3f2fd; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #2196f3; }}
            .form-group {{ margin: 15px 0; }}
            .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            .form-group input, .form-group select {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
            .btn {{ display: inline-block; padding: 12px 24px; margin: 10px 5px; text-decoration: none; border-radius: 5px; font-weight: bold; cursor: pointer; border: none; }}
            .btn-primary {{ background: #007bff; color: white; }}
            .btn-success {{ background: #28a745; color: white; }}
            .week-display {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; text-align: center; }}
            .current-week {{ font-size: 2em; color: #007bff; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📅 學期設定與週數管理</h1>
            
            <div class="info-card">
                <h3>目前學期狀態</h3>
                <p><strong>學期開始日期：</strong>{semester_start_str}</p>
                <p><strong>目前設定週次：</strong>第 {config['current_week']} 週</p>
                <p><strong>總週數：</strong>{config['total_weeks']} 週</p>
                <p><strong>上次更新：</strong>{config['updated_at']}</p>
            </div>
            
            <div class="week-display">
                <div>根據日期自動計算</div>
                <div class="current-week">第 {auto_week} 週</div>
                <div>{COURSE_SCHEDULE_18_WEEKS.get(auto_week, {}).get('chinese', '課程內容')}</div>
                <div style="color: #666; font-size: 0.9em;">{COURSE_SCHEDULE_18_WEEKS.get(auto_week, {}).get('topic', '')}</div>
            </div>
            
            <form method="POST" action="/update_semester_config">
                <div class="form-group">
                    <label>學期開始日期：</label>
                    <input type="date" name="semester_start" value="{semester_start_str}" required>
                </div>
                
                <div class="form-group">
                    <label>當前週次：</label>
                    <select name="current_week" required>
                        {''.join([f'<option value="{i}" {"selected" if i == config["current_week"] else ""}>第 {i} 週 - {COURSE_SCHEDULE_18_WEEKS.get(i, {}).get("chinese", "")}</option>' for i in range(1, 19)])}
                    </select>
                </div>
                
                <button type="submit" class="btn btn-primary">💾 更新學期設定</button>
                <a href="/auto_set_week" class="btn btn-success">🔄 自動設定為第 {auto_week} 週</a>
            </form>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/admin" style="color: #007bff;">← 返回管理首頁</a>
                <a href="/admin_panel" style="color: #007bff; margin-left: 20px;">管理面板</a>
                <a href="/" style="color: #007bff; margin-left: 20px;">回到首頁</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/update_semester_config", methods=['POST'])
def update_semester_config_route():
    """更新學期設定"""
    semester_start = request.form.get('semester_start')
    current_week = int(request.form.get('current_week'))
    
    success = update_semester_config(semester_start, current_week)
    
    if success:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #d4edda; margin: 20px; border-radius: 10px;">
            <h2>✅ 學期設定更新成功！</h2>
            <p>新的學期設定已儲存</p>
            <p><a href="/semester_settings" style="color: #28a745; font-weight: bold;">返回學期設定</a></p>
        </div>
        '''
    else:
        return '''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px; background: #f8d7da; margin: 20px; border-radius: 10px;">
            <h2>❌ 設定更新失敗</h2>
            <p><a href="/semester_settings" style="color: #007bff;">返回設定頁面</a></p>
        </div>
        '''

@app.route("/auto_set_week")
def auto_set_week():
    """自動設定當前週次"""
    config = get_semester_config()
    auto_week = calculate_current_week_from_date()
    
    success = update_semester_config(config['semester_start'], auto_week)
    
    if success:
        return f'''
        <div style="font-family: Microsoft JhengHei; text-align: center; padding: 50px
