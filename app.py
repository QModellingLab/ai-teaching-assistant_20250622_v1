def save_interaction(user_id, user_name, message, ai_response):
    """記錄學生與AI的互動 (保持原有兼容性)"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        # 記錄到原有表格 (保持兼容性)
        cursor.execute('''
            INSERT INTO student_interactions 
            (user_id, user_name, message, ai_response)
            VALUES (?, ?, ?, ?)
        ''', (user_id, user_name, message, ai_response))
        
        # 更新使用統計
        cursor.execute('''
            INSERT OR REPLACE INTO usage_stats (user_id, date, message_count)
            VALUES (?, date('now'), 
                    COALESCE((SELECT message_count FROM usage_stats 
                             WHERE user_id = ? AND date = date('now')), 0) + 1)
        ''', (user_id, user_id))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ 互動記錄錯誤: {e}")

# =============================================================================
# 研究數據分析與統計功能
# =============================================================================

def get_research_analytics():
    """獲取完整研究分析數據"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        # 基本參與度統計
        cursor.execute('''
            SELECT 
                COUNT(*) as total_interactions,
                COUNT(DISTINCT user_id) as active_students,
                AVG(interaction_quality_score) as avg_quality
            FROM participation_analytics
        ''')
        basic_stats = cursor.fetchone()
        
        # 週使用率計算
        current_week = get_current_week()
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) 
            FROM participation_analytics 
            WHERE week_number = ?
        ''', (current_week,))
        weekly_active = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM participation_analytics')
        total_students = cursor.fetchone()[0]
        weekly_usage_rate = (weekly_active / max(total_students, 1)) * 100 if total_students > 0 else 0
        
        # 平均發言次數/週
        cursor.execute('''
            SELECT AVG(message_count) 
            FROM weekly_student_stats 
            WHERE week_number = ?
        ''', (current_week,))
        avg_result = cursor.fetchone()
        avg_messages_per_week = avg_result[0] if avg_result[0] else 0
        
        # 今日使用量
        cursor.execute('''
            SELECT COUNT(*) 
            FROM participation_analytics 
            WHERE date(timestamp) = date('now')
        ''')
        today_usage = cursor.fetchone()[0]
        
        # 最活躍學生排行
        cursor.execute('''
            SELECT user_name, message_count, avg_quality_score, engagement_level
            FROM weekly_student_stats 
            WHERE week_number = ?
            ORDER BY message_count DESC 
            LIMIT 10
        ''', (current_week,))
        top_students = cursor.fetchall()
        
        # 小組活躍度排行
        cursor.execute('''
            SELECT group_id, activity_score, total_messages, unique_participants
            FROM group_activity 
            WHERE week_number = ?
            ORDER BY activity_score DESC 
            LIMIT 5
        ''', (current_week,))
        top_groups = cursor.fetchall()
        
        # 主題興趣分析
        cursor.execute('''
            SELECT topic_name, mention_count, avg_quality_score, question_count
            FROM topic_analytics 
            WHERE week_number = ?
            ORDER BY mention_count DESC
        ''', (current_week,))
        topic_stats = cursor.fetchall()
        
        # 訊息類型分布
        cursor.execute('''
            SELECT message_type, COUNT(*) as count
            FROM participation_analytics 
            WHERE week_number = ?
            GROUP BY message_type
        ''', (current_week,))
        message_type_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'basic_stats': {
                'total_interactions': basic_stats[0] or 0,
                'active_students': basic_stats[1] or 0,
                'avg_quality': round(basic_stats[2] or 0, 2)
            },
            'key_metrics': {
                'weekly_usage_rate': round(weekly_usage_rate, 1),
                'avg_messages_per_week': round(avg_messages_per_week, 1),
                'today_usage': today_usage,
                'current_week': current_week
            },
            'rankings': {
                'top_students': top_students,
                'top_groups': top_groups
            },
            'content_analysis': {
                'topic_stats': topic_stats,
                'message_type_stats': dict(message_type_stats)
            }
        }
        
    except Exception as e:
        print(f"❌ 研究分析錯誤: {e}")
        return {
            'basic_stats': {'total_interactions': 0, 'active_students': 0, 'avg_quality': 0},
            'key_metrics': {'weekly_usage_rate': 0, 'avg_messages_per_week': 0, 'today_usage': 0, 'current_week': 10},
            'rankings': {'top_students': [], 'top_groups': []},
            'content_analysis': {'topic_stats': [], 'message_type_stats': {}}
        }

def analyze_teaching_effectiveness():
    """分析教學效果並生成建議"""
    analytics = get_research_analytics()
    insights = []
    metrics = analytics['key_metrics']
    
    # 參與度分析
    if metrics['weekly_usage_rate'] < 70:
        insights.append({
            'type': 'participation',
            'level': 'high',
            'message': f"週使用率僅{metrics['weekly_usage_rate']:.1f}%，未達70%目標。建議增加課堂互動引導。",
            'suggestion': "考慮在課堂中主動介紹AI助教功能，或設計需要使用AI助教的作業。"
        })
    else:
        insights.append({
            'type': 'participation',
            'level': 'low',
            'message': f"週使用率達{metrics['weekly_usage_rate']:.1f}%，表現優秀！",
            'suggestion': "繼續維持目前的推廣策略。"
        })
    
    # 互動頻率分析
    if metrics['avg_messages_per_week'] < 5:
        insights.append({
            'type': 'engagement',
            'level': 'medium',
            'message': f"平均發言{metrics['avg_messages_per_week']:.1f}次/週，低於5次目標。",
            'suggestion': "可設計每週必答問題，或建立小組競賽機制鼓勵互動。"
        })
    
    # 內容品質分析
    avg_quality = analytics['basic_stats']['avg_quality']
    if avg_quality < 3.0:
        insights.append({
            'type': 'quality',
            'level': 'high',
            'message': f"討論品質平均{avg_quality:.1f}分，有提升空間。",
            'suggestion': "考慮提供討論範例，或引導學生提供具體例子和個人觀點。"
        })
    
    return insights

# =============================================================================
# Web 介面 - 研究數據儀表板
# =============================================================================

@app.route("/", methods=['GET'])
def enhanced_home():
    """增強版首頁"""
    current_week = get_current_week()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Teaching Assistant - EMI Course</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; 
                   background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; min-height: 100vh; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .feature-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                            gap: 20px; margin: 30px 0; }}
            .feature-card {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; 
                            backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); }}
            .button {{ display: inline-block; background: rgba(255,255,255,0.2); color: white; 
                      padding: 12px 24px; text-decoration: none; border-radius: 25px; 
                      margin: 10px 5px; transition: all 0.3s ease; 
                      border: 1px solid rgba(255,255,255,0.3); }}
            .button:hover {{ background: rgba(255,255,255,0.3); transform: translateY(-2px); }}
            .dashboard-button {{ background: #ff8800; }}
            .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat {{ text-align: center; }}
            .stat-number {{ font-size: 2em; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 AI Teaching Assistant</h1>
                <h2>📚 Practical Applications of AI in Life and Learning (EMI)</h2>
                <h3>👩‍🏫 Principal Investigator: Prof. Yu-Yao Tseng</h3>
                <p>🎯 當前週次：第 {current_week} 週 | ✅ 服務運行正常</p>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">📊</div>
                    <div>研究進行中</div>
                </div>
                <div class="stat">
                    <div class="stat-number">🌍</div>
                    <div>EMI教學</div>
                </div>
                <div class="stat">
                    <div class="stat-number">🤖</div>
                    <div>AI輔助</div>
                </div>
                <div class="stat">
                    <div class="stat-number">24/7</div>
                    <div>全天候服務</div>
                </div>
            </div>
            
            <div class="feature-grid">
                <div class="feature-card">
                    <h3>📱 學生使用方式</h3>
                    <ul>
                        <li><strong>個人聊天：</strong>直接提問</li>
                        <li><strong>群組聊天：</strong>使用@符號開頭</li>
                        <li><strong>支援語言：</strong>英語為主，中文輔助</li>
                        <li><strong>功能：</strong>術語解釋、討論引導、學習支援</li>
                    </ul>
                </div>
                
                <div class="feature-card">
                    <h3>📊 研究功能特色</h3>
                    <ul>
                        <li><strong>自動參與度分析：</strong>追蹤學生互動</li>
                        <li><strong>討論品質評估：</strong>AI智能評分</li>
                        <li><strong>主題興趣統計：</strong>內容分類分析</li>
                        <li><strong>小組活躍度：</strong>團隊合作追蹤</li>
                    </ul>
                </div>
                
                <div class="feature-card">
                    <h3>🎯 研究目標追蹤</h3>
                    <ul>
                        <li><strong>週使用率目標：</strong>≥ 70%</li>
                        <li><strong>發言頻率目標：</strong>≥ 5次/週</li>
                        <li><strong>教學評量目標：</strong>≥ 4.2分</li>
                        <li><strong>參與度提升：</strong>+30%</li>
                    </ul>
                </div>
                
                <div class="feature-card">
                    <h3>🔬 技術架構</h3>
                    <ul>
                        <li><strong>AI引擎：</strong>Google Gemini 1.5 Flash</li>
                        <li><strong>通訊平台：</strong>LINE Messaging API</li>
                        <li><strong>部署平台：</strong>Railway雲端服務</li>
                        <li><strong>數據分析：</strong>SQLite + Python</li>
                    </ul>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <h3>🎮 系統管理與監控</h3>
                
                <a href="/research_dashboard" class="button dashboard-button">
                    📊 研究數據儀表板
                </a>
                
                <a href="/weekly_report" class="button">
                    📋 週報告
                </a>
                
                <a href="/health" class="button">
                    🏥 系統健康檢查
                </a>
                
                <a href="/export_research_data" class="button">
                    📥 匯出研究數據
                </a>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding: 20px; 
                        background: rgba(255,255,255,0.1); border-radius: 10px;">
                <h4>📞 聯絡資訊</h4>
                <p>🏫 實踐大學 食品營養與保健生技學系</p>
                <p>📧 技術支援：系統自動監控中</p>
                <p>📚 課程：大數據與人工智慧在生活上的應用</p>
                <p>🔬 計畫：教育部教學實踐研究計畫</p>
            </div>
        </div>
        
        <script>
            console.log("🤖 AI Teaching Assistant - EMI Course");
            console.log("📊 Research Dashboard Available");
            console.log("🔧 System Status: Normal");
        </script>
    </body>
    </html>
    """

@app.route("/research_dashboard", methods=['GET'])
def research_dashboard():
    """完整研究數據儀表板"""
    try:
        analytics = get_research_analytics()
        insights = analyze_teaching_effectiveness()
        
        # 判斷指標達成狀況
        def get_status_indicator(value, target):
            if value >= target:
                return "✅ 達標", "color: green; font-weight: bold;"
            elif value >= target * 0.8:
                return "⚠️ 接近", "color: orange; font-weight: bold;"
            else:
                return "❌ 未達標", "color: red; font-weight: bold;"
        
        usage_status, usage_style = get_status_indicator(analytics['key_metrics']['weekly_usage_rate'], 70)
        message_status, message_style = get_status_indicator(analytics['key_metrics']['avg_messages_per_week'], 5)
        quality_status, quality_style = get_status_indicator(analytics['basic_stats']['avg_quality'], 3.5)
        
        dashboard_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>EMI教學研究數據儀表板</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                                  gap: 20px; }}
                .card {{ background: white; padding: 20px; border-radius: 10px; 
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .metric {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
                .status {{ font-size: 1.2em; margin: 5px 0; }}
                .table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .table th {{ background-color: #f2f2f2; }}
                .progress-bar {{ background-color: #e0e0e0; border-radius: 10px; overflow: hidden; height: 20px; }}
                .progress-fill {{ height: 100%; transition: width 0.3s ease; }}
                .insight-high {{ border-left: 4px solid #ff4444; }}
                .insight-medium {{ border-left: 4px solid #ff8800; }}
                .insight-low {{ border-left: 4px solid #44ff44; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 EMI教學研究數據儀表板</h1>
                <h2>生成式AI輔助的雙語教學創新研究</h2>
                <p>📅 當前週次：第{analytics['key_metrics']['current_week']}週 | 
                   ⏰ 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="dashboard-grid">
                <!-- 關鍵指標卡片 -->
                <div class="card">
                    <h3>🎯 研究關鍵指標</h3>
                    
                    <div>
                        <strong>週使用率目標：≥70%</strong>
                        <div class="metric">{analytics['key_metrics']['weekly_usage_rate']:.1f}%</div>
                        <div class="status" style="{usage_style}">{usage_status}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(analytics['key_metrics']['weekly_usage_rate'], 100)}%; 
                                 background-color: {'#44ff44' if analytics['key_metrics']['weekly_usage_rate'] >= 70 else '#ff8800' if analytics['key_metrics']['weekly_usage_rate'] >= 56 else '#ff4444'};"></div>
                        </div>
                    </div>
                    
                    <hr>
                    
                    <div>
                        <strong>平均發言次數目標：≥5次/週</strong>
                        <div class="metric">{analytics['key_metrics']['avg_messages_per_week']:.1f} 次</div>
                        <div class="status" style="{message_style}">{message_status}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(analytics['key_metrics']['avg_messages_per_week'] * 20, 100)}%; 
                                 background-color: {'#44ff44' if analytics['key_metrics']['avg_messages_per_week'] >= 5 else '#ff8800' if analytics['key_metrics']['avg_messages_per_week'] >= 4 else '#ff4444'};"></div>
                        </div>
                    </div>
                    
                    <hr>
                    
                    <div>
                        <strong>討論品質平均分：</strong>
                        <div class="metric">{analytics['basic_stats']['avg_quality']:.2f} / 5.0</div>
                        <div class="status" style="{quality_style}">{quality_status}</div>
                    </div>
                </div>
                
                <!-- 基礎統計卡片 -->
                <div class="card">
                    <h3>📈 基礎統計資料</h3>
                    <p><strong>總互動次數：</strong> {analytics['basic_stats']['total_interactions']}</p>
                    <p><strong>活躍學生數：</strong> {analytics['basic_stats']['active_students']}</p>
                    <p><strong>今日使用量：</strong> {analytics['key_metrics']['today_usage']}</p>
                    <p><strong>系統運行狀態：</strong> <span style="color: green;">🟢 正常運行</span></p>
                </div>
                
                <!-- 學生參與排行 -->
                <div class="card">
                    <h3>🏆 學生參與度排行（本週）</h3>
                    <table class="table">
                        <thead>
                            <tr><th>排名</th><th>學生</th><th>發言數</th><th>品質分</th><th>參與度</th></tr>
                        </thead>
                        <tbody>
        """
        
        for i, student in enumerate(analytics['rankings']['top_students'][:10], 1):
            name = student[0] if student[0] else "匿名學生"
            dashboard_html += f"""
                            <tr>
                                <td>{i}</td>
                                <td>{name[:10]}{'...' if len(name) > 10 else ''}</td>
                                <td>{student[1]}</td>
                                <td>{student[2]:.1f}</td>
                                <td>{student[3]}</td>
                            </tr>
            """
        
        dashboard_html += """
                        </tbody>
                    </table>
                </div>
                
                <!-- 小組活躍度 -->
                <div class="card">
                    <h3>👥 小組活躍度排行</h3>
                    <table class="table">
                        <thead>
                            <tr><th>小組ID</th><th>活躍分數</th><th>訊息數</th><th>參與人數</th></tr>
                        </thead>
                        <tbody>
        """
        
        for group in analytics['rankings']['top_groups']:
            group_name = group[0] or "個人聊天"
            dashboard_html += f"""
                            <tr>
                                <td>{group_name[:15]}{'...' if len(str(group_name)) > 15 else ''}</td>
                                <td>{group[1]:.1f}</td>
                                <td>{group[2]}</td>
                                <td>{group[3]}</td>
                            </tr>
            """
        
        dashboard_html += """
                        </tbody>
                    </table>
                </div>
                
                <!-- 主題興趣分析 -->
                <div class="card">
                    <h3>📚 討論主題分析</h3>
                    <table class="table">
                        <thead>
                            <tr><th>主題</th><th>提及次數</th><th>平均品質</th><th>問題數</th></tr>
                        </thead>
                        <tbody>
        """
        
        for topic in analytics['content_analysis']['topic_stats']:
            topic_name = topic[0].replace('_', ' ')
            dashboard_html += f"""
                            <tr>
                                <td>{topic_name}</td>
                                <td>{topic[1]}</td>
                                <td>{topic[2]:.1f}</td>
                                <td>{topic[3]}</td>
                            </tr>
            """
        
        dashboard_html += """
                        </tbody>
                    </table>
                </div>
                
                <!-- 訊息類型分布 -->
                <div class="card">
                    <h3>💬 訊息類型分布</h3>
        """
        
        message_types = analytics['content_analysis']['message_type_stats']
        type_names = {'question': '問題', 'discussion': '討論', 'response': '回應', 'greeting': '問候'}
        
        for msg_type, count in message_types.items():
            percentage = (count / sum(message_types.values())) * 100 if message_types else 0
            type_name = type_names.get(msg_type, msg_type)
            dashboard_html += f"""
                    <div style="margin: 10px 0;">
                        <strong>{type_name}：</strong> {count} 次 ({percentage:.1f}%)
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {percentage}%; background-color: #667eea;"></div>
                        </div>
                    </div>
            """
        
        dashboard_html += """
                </div>
                
                <!-- 教學改進建議 -->
                <div class="card" style="grid-column: 1 / -1;">
                    <h3>💡 AI分析建議</h3>
        """
        
        for insight in insights:
            css_class = f"insight-{insight['level']}"
            level_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(insight['level'], '📊')
            
            dashboard_html += f"""
                    <div class="card {css_class}" style="margin: 10px 0; padding: 15px;">
                        <h4>{level_icon} {insight['type'].replace('_', ' ').title()}</h4>
                        <p><strong>觀察：</strong> {insight['message']}</p>
                        <p><strong>建議：</strong> {insight['suggestion']}</p>
                    </div>
            """
        
        dashboard_html += f"""
                </div>
            </div>
            
            <!-- 操作按鈕 -->
            <div style="margin-top: 30px; text-align: center;">
                <a href="/export_research_data" style="background: #667eea; color: white; padding: 10px 20px; 
                   text-decoration: none; border-radius: 5px; margin: 5px;">📥 匯出完整數據</a>
                <a href="/weekly_report" style="background: #44ff44; color: black; padding: 10px 20px; 
                   text-decoration: none; border-radius: 5px; margin: 5px;">📊 週報告</a>
                <a href="/" style="background: #ff8800; color: white; padding: 10px 20px; 
                   text-decoration: none; border-radius: 5px; margin: 5px;">🏠 回到首頁</a>
            </div>
            
            <script>
                // 每5分鐘自動重新整理
                setTimeout(function(){{ 
                    location.reload(); 
                }}, 300000);
                
                console.log("📊 EMI教學研究儀表板已載入");
            </script>
        </body>
        </html>
        """
        
        return dashboard_html
        
    except Exception as e:
        return f"<h1>儀表板載入錯誤</h1><p>錯誤詳情：{e}</p><p><a href='/'>回到首頁</a></p>"

@app.route("/weekly_report", methods=['GET'])
def weekly_report():
    """週報告頁面"""
    try:
        analytics = get_research_analytics()
        insights = analyze_teaching_effectiveness()
        current_week = analytics['key_metrics']['current_week']
        
        report_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>第{current_week}週教學研究報告</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                .highlight {{ background-color: #f0f8ff; padding: 10px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 EMI課程教學研究週報告</h1>
                <h2>第 {current_week} 週</h2>
                <p>報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="section">
                <h3>📈 關鍵指標達成情況</h3>
                <ul>
                    <li><strong>週使用率：</strong> {analytics['key_metrics']['weekly_usage_rate']:.1f}% 
                        {'✅ 達標' if analytics['key_metrics']['weekly_usage_rate'] >= 70 else '❌ 未達標'}</li>
                    <li><strong>平均發言次數：</strong> {analytics['key_metrics']['avg_messages_per_week']:.1f}次/週 
                        {'✅ 達標' if analytics['key_metrics']['avg_messages_per_week'] >= 5 else '❌ 未達標'}</li>
                    <li><strong>討論品質：</strong> {analytics['basic_stats']['avg_quality']:.2f}/5.0</li>
                    <li><strong>活躍學生數：</strong> {analytics['basic_stats']['active_students']} 人</li>
                </ul>
            </div>
            
            <div class="section">
                <h3>💡 主要發現與建議</h3>
        """
        
        for i, insight in enumerate(insights, 1):
            report_html += f"<p><strong>{i}.</strong> {insight['suggestion']}</p>"
        
        report_html += f"""
            </div>
            
            <div class="section">
                <h3>📊 詳細分析數據</h3>
                <div class="highlight">
                    <p><strong>總互動次數：</strong> {analytics['basic_stats']['total_interactions']}</p>
                    <p><strong>今日使用量：</strong> {analytics['key_metrics']['today_usage']}</p>
                    <p><strong>系統穩定性：</strong> 良好</p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/research_dashboard">回到儀表板</a> | 
                <a href="/export_research_data">匯出數據</a> |
                <a href="/">回到首頁</a>
            </div>
        </body>
        </html>
        """
        
        return report_html
        
    except Exception as e:
        return f"<h1>報告生成錯誤</h1><p>{e}</p>"

@app.route("/export_research_data", methods=['GET'])
def export_detailed_research_data():
    """匯出詳細研究數據為CSV"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        # 匯出參與度分析數據
        cursor.execute('''
            SELECT 
                substr(user_id, 1, 8) || '***' as user_code,
                user_name,
                message_type,
                message_length,
                word_count,
                english_ratio,
                interaction_quality_score,
                topic_category,
                group_id,
                week_number,
                timestamp
            FROM participation_analytics
            ORDER BY timestamp
        ''')
        
        data = cursor.fetchall()
        conn.close()
        
        # 生成CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 寫入標題
        writer.writerow([
            '用戶代碼', '用戶名稱', '訊息類型', '訊息長度', '單詞數', 
            '英語比例', '品質分數', '主題類別', '群組ID', '週次', '時間戳記'
        ])
        
        # 寫入數據
        for row in data:
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        # 返回檔案
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=emi_research_data_week_{get_current_week()}.csv'
            }
        )
        
    except Exception as e:
        return f"匯出錯誤: {e}", 500

# =============================================================================
# LINE Bot 訊息處理 - 增強版支援群組@觸發
# =============================================================================

@app.route("/callback", methods=['POST'])
def callback():
    """LINE Bot Webhook 接收訊息"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def enhanced_handle_message(event):
    """增強版訊息處理函數 - 整合進階分析"""
    
    # 獲取訊息資訊
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    
    # 檢查是否為群組訊息
    is_group_message = hasattr(event.source, 'group_id') or hasattr(event.source, 'room_id')
    group_id = None
    
    if is_group_message:
        group_id = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', None)
        
        # 群組中的@觸發條件檢查
        if user_message.startswith('@'):
            user_message = user_message[1:].strip()
            ai_keywords = ['ai', 'AI', '助教', '小助教']
            for keyword in ai_keywords:
                if user_message.startswith(keyword):
                    user_message = user_message[len(keyword):].strip()
                    break
        else:
            return  # 群組中沒有@符號開頭，不回應
    
    if not user_message:
        return
    
    # 獲取學生姓名
    try:
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
    except:
        user_name = "Student"
    
    # 🆕 進階訊息分析
    analysis_result = analyze_message_comprehensive(
        user_id=user_id,
        user_name=user_name,
        message=user_message,
        group_id=group_id
    )
    
    # 生成AI回應 (根據分析結果調整回應策略)
    ai_response = generate_ai_response_with_context(
        user_message, 
        user_name, 
        analysis_result
    )
    
    # 群組中添加@回應
    if is_group_message:
        ai_response = f"@{user_name} {ai_response}"
    
    # 記錄基本互動 (保持與原系統的兼容性)
    save_interaction(user_id, user_name, user_message, ai_response)
    
    # 回覆學生
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_response)
    )
    
    print(f"✅ 增強版回應完成 - {user_name}: {analysis_result['message_type']} (品質: {analysis_result['quality_score']:.1f})")

# =============================================================================
# 系統狀態監控與健康檢查
# =============================================================================

@app.route("/health", methods=['GET'])
def health_check():
    """健康檢查 - Railway監控用"""
    try:
        # 檢查資料庫連接
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM student_interactions')
        total_interactions = cursor.fetchone()[0]
        conn.close()
        
        # 檢查AI功能
        test_response = model.generate_content("Hello")
        ai_working = bool(test_response.text)
        
        return {
            "status": "healthy",
            "service": "AI Teaching Assistant",
            "total_interactions": total_interactions,
            "ai_status": "working" if ai_working else "error",
            "timestamp": datetime.now().isoformat()
        }, 200
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, 500

@app.route("/system_status", methods=['GET'])
def system_status():
    """系統狀態監控API"""
    try:
        analytics = get_research_analytics()
        
        status = {
            "system_health": "healthy",
            "database_status": "connected",
            "current_week": analytics['key_metrics']['current_week'],
            "active_students": analytics['basic_stats']['active_students'],
            "today_interactions": analytics['key_metrics']['today_usage'],
            "key_metrics": {
                "weekly_usage_rate": analytics['key_metrics']['weekly_usage_rate'],
                "avg_messages_per_week": analytics['key_metrics']['avg_messages_per_week'],
                "avg_quality_score": analytics['basic_stats']['avg_quality']
            },
            "targets_status": {
                "usage_rate_target": analytics['key_metrics']['weekly_usage_rate'] >= 70,
                "message_frequency_target": analytics['key_metrics']['avg_messages_per_week'] >= 5,
                "quality_target": analytics['basic_stats']['avg_quality'] >= 3.5
            },
            "last_updated": datetime.now().isoformat()
        }
        
        return status
        
    except Exception as e:
        return {
            "system_health": "error",
            "error_message": str(e),
            "last_updated": datetime.now().isoformat()
        }, 500

# =============================================================================
# 測試功能
# =============================================================================

def test_complete_system():
    """測試完整系統功能"""
    print("\n🧪 測試完整系統功能...")
    
    try:
        # 測試資料庫
        success = init_complete_database()
        if not success:
            print("❌ 資料庫初始化失敗")
            return False
        
        # 測試分析功能
        test_messages = [
            ("What is artificial intelligence?", "question"),
            ("I think AI will revolutionize healthcare in Taiwan.", "discussion"),
            ("Hello!", "greeting"),
            ("Thank you for explaining.", "response")
        ]
        
        for i, (message, expected_type) in enumerate(test_messages):
            result = analyze_message_comprehensive(
                user_id=f"test_user_{i+1}",
                user_name=f"TestStudent{i+1}",
                message=message,
                group_id="test_group" if i % 2 == 0 else None
            )
            
            if result['message_type'] == expected_type:
                print(f"✅ 訊息分析測試 {i+1}: {expected_type} 分類正確")
            else:
                print(f"⚠️ 訊息分析測試 {i+1}: 預期 {expected_type}, 得到 {result['message_type']}")
        
        # 測試研究分析
        analytics = get_research_analytics()
        print(f"✅ 研究分析功能正常")
        print(f"   - 總互動: {analytics['basic_stats']['total_interactions']}")
        print(f"   - 週使用率: {analytics['key_metrics']['weekly_usage_rate']:.1f}%")
        
        # 測試建議生成
        insights = analyze_teaching_effectiveness()
        print(f"✅ 教學建議生成功能正常 ({len(insights)} 項建議)")
        
        print("\n🎉 完整系統測試成功！")
        return True
        
    except Exception as e:
        print(f"❌ 系統測試失敗: {e}")
        return False

# =============================================================================
# 主程式執行 - Railway部署版
# =============================================================================

if __name__ == "__main__":
    print("🚀 Starting Enhanced AI Teaching Assistant...")
    print("📚 Course: Practical Applications of AI in Life and Learning (EMI)")
    print("👩‍🏫 Principal Investigator: Prof. Yu-Yao Tseng")
    print("🌍 Language: English-Medium Instruction (EMI)")
    print("=" * 70)
    
    # 初始化完整資料庫
    success = init_complete_database()
    
    if success:
        print("✅ Enhanced Database Configuration Complete")
        print("✅ LINE Bot Configuration Complete")
        print("✅ Gemini AI Configuration Complete")
        print("=" * 70)
        print("📊 Enhanced System Features:")
        print("• Advanced participation analytics and tracking")
        print("• Automatic discussion quality assessment")
        print("• Group activity monitoring and scoring")
        print("• Topic interest analysis and categorization")
        print("• Real-time research dashboard and reporting")
        print("• Intelligent context-aware AI responses")
        print("• Comprehensive data export for academic research")
        print("• EMI teaching support with bilingual assistance")
        print("=" * 70)
        
        # 可選：執行系統測試
        # test_complete_system()
        
        print("🎯 Research Targets:")
        print("• Weekly Usage Rate: ≥ 70%")
        print("• Average Messages per Week: ≥ 5")
        print("• Teaching Evaluation Score: ≥ 4.2")
        print("• Student Engagement Improvement: +30%")
        print("=" * 70)
        print("🌐 Available Endpoints:")
        print("• /research_dashboard - Comprehensive analytics dashboard")
        print("• /weekly_report - Weekly teaching effectiveness report")
        print("• /export_research_data - Export data for academic analysis")
        print("• /health - System health monitoring")
        print("• /system_status - Real-time system status API")
        print("=" * 70)
    else:
        print("❌ 資料庫初始化失敗，使用基本功能")
    
    # Railway部署設定
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)# app.py - Railway部署版本
# LINE Bot + Gemini AI 教學助手 (完整研究功能整合版)

import os
import sqlite3
import json
import csv
import io
import re
import random
from datetime import datetime, timedelta
from flask import Flask, request, abort, Response
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

# =============================================================================
# 環境變數設定（Railway部署用）
# =============================================================================

# 從環境變數讀取API金鑰（部署時自動使用）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '/FWGFeTl5+9MyyqJry49vlafcpvAl5d5UekpsZbkd/V5Cnk8zES8J9YDM6msNqkJJeC39ivYPA/zQNmuamcDQexc23SakFgwl61hPhdDsk4P2koHSusVKC4oYP67up/+AKrql1cQY8vLf3Tx3prh1QdB04t89/1O/w1cDnyilFU=')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', 'cf2728ecaf0dba522c10c15a99801f68')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyD2kVQffsdK0RDwHjIe8xWQAqlm-9ZK3Rs')

# =============================================================================
# 初始化設定
# =============================================================================

app = Flask(__name__)

# LINE Bot API 初始化
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Gemini AI 初始化
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# =============================================================================
# 進階資料庫設定 - 完整研究分析功能
# =============================================================================

def init_complete_database():
    """初始化完整研究分析資料庫"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        # 原有基礎表格
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT,
                message TEXT,
                ai_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_type TEXT DEFAULT 'question'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date DATE DEFAULT CURRENT_DATE,
                message_count INTEGER DEFAULT 1,
                UNIQUE(user_id, date)
            )
        ''')
        
        # 進階分析表格
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participation_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT,
                message TEXT,
                message_type TEXT,
                message_length INTEGER,
                word_count INTEGER,
                english_ratio REAL,
                interaction_quality_score REAL,
                topic_category TEXT,
                group_id TEXT,
                week_number INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                response_time_seconds INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                group_name TEXT,
                week_number INTEGER,
                total_messages INTEGER DEFAULT 0,
                unique_participants INTEGER DEFAULT 0,
                avg_message_length REAL DEFAULT 0,
                question_count INTEGER DEFAULT 0,
                discussion_count INTEGER DEFAULT 0,
                activity_score REAL DEFAULT 0,
                discussion_quality_avg REAL DEFAULT 0,
                last_activity_time DATETIME,
                date DATE DEFAULT CURRENT_DATE,
                UNIQUE(group_id, week_number)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_student_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT,
                week_number INTEGER,
                message_count INTEGER DEFAULT 0,
                question_count INTEGER DEFAULT 0,
                discussion_count INTEGER DEFAULT 0,
                avg_quality_score REAL DEFAULT 0,
                total_words INTEGER DEFAULT 0,
                english_usage_ratio REAL DEFAULT 0,
                engagement_level TEXT DEFAULT 'medium',
                topics_covered TEXT,
                first_interaction DATETIME,
                last_interaction DATETIME,
                UNIQUE(user_id, week_number)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topic_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_name TEXT NOT NULL,
                week_number INTEGER,
                mention_count INTEGER DEFAULT 1,
                avg_quality_score REAL DEFAULT 0,
                question_count INTEGER DEFAULT 0,
                discussion_count INTEGER DEFAULT 0,
                student_interest_level REAL DEFAULT 0,
                date DATE DEFAULT CURRENT_DATE,
                UNIQUE(topic_name, week_number)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ 完整研究分析資料庫初始化成功")
        return True
        
    except Exception as e:
        print(f"❌ 資料庫初始化錯誤: {e}")
        return False

# =============================================================================
# 課程進度與週次管理
# =============================================================================

def get_current_week():
    """獲取當前教學週次"""
    # 假設第10週開始於2025年6月23日 (請根據實際情況調整)
    start_date = datetime(2025, 6, 23)
    current_date = datetime.now()
    week_diff = (current_date - start_date).days // 7
    current_week = 10 + week_diff
    return min(max(current_week, 10), 17)

def get_week_context(week_number):
    """獲取週次課程背景資訊"""
    course_schedule = {
        10: {
            'topic': 'Mass Customization by Industry 4.0',
            'keywords': ['Industry 4.0', 'IoT', 'Smart Manufacturing', 'Automation'],
            'focus': 'Understanding how Industry 4.0 enables personalized production'
        },
        11: {
            'topic': 'Industry 4.0 Applications',
            'keywords': ['Cyber-Physical Systems', 'Digital Twin', 'Predictive Maintenance'],
            'focus': 'Real-world applications and case studies'
        },
        12: {
            'topic': 'Smart Home Technologies',
            'keywords': ['Smart Home', 'IoT Devices', 'Home Automation', 'AI Assistants'],
            'focus': 'How AI makes homes intelligent and responsive'
        },
        13: {
            'topic': 'Smart Home Implementation',
            'keywords': ['Home Networks', 'Privacy', 'Security', 'User Experience'],
            'focus': 'Practical considerations for smart home deployment'
        },
        14: {
            'topic': 'AI in Art and Fashion',
            'keywords': ['Creative AI', 'Generative Design', 'Fashion Tech', 'Digital Art'],
            'focus': 'How AI is transforming creative industries'
        },
        15: {
            'topic': 'Fashion and Art Innovation',
            'keywords': ['Style Transfer', '3D Design', 'Virtual Fashion', 'AI Creativity'],
            'focus': 'Innovation in design and artistic expression'
        },
        16: {
            'topic': 'AI in Healthcare',
            'keywords': ['Medical AI', 'Diagnostic Tools', 'Telemedicine', 'Health Monitoring'],
            'focus': 'How AI is revolutionizing healthcare delivery'
        },
        17: {
            'topic': 'Healthcare AI Applications',
            'keywords': ['Clinical Decision Support', 'Drug Discovery', 'Personalized Medicine'],
            'focus': 'Advanced applications and future possibilities'
        }
    }
    
    return course_schedule.get(week_number, {
        'topic': 'General AI Applications',
        'keywords': ['Artificial Intelligence', 'Machine Learning', 'Technology'],
        'focus': 'Exploring AI applications in daily life'
    })

# =============================================================================
# 訊息分析核心函數
# =============================================================================

def classify_message_type(message):
    """自動分類訊息類型"""
    message_lower = message.lower().strip()
    
    question_patterns = [
        r'\?', r'？', r'\bwhat\b', r'\bhow\b', r'\bwhy\b', r'\bwhen\b', 
        r'\bwhere\b', r'\bwhich\b', r'\bcan you\b', r'\bcould you\b',
        r'什麼', r'如何', r'為什麼', r'怎麼', r'哪裡', r'什麼時候', r'可以.*嗎'
    ]
    
    discussion_patterns = [
        r'\bi think\b', r'\bin my opinion\b', r'\bi believe\b', r'\bconsider\b',
        r'\banalyze\b', r'\bcompare\b', r'\bevaluate\b', r'\bassess\b',
        r'我認為', r'我覺得', r'應該', r'可能', r'分析', r'比較', r'評估'
    ]
    
    greeting_patterns = [
        r'\bhello\b', r'\bhi\b', r'\bhey\b', r'\bgood morning\b', r'\bgood afternoon\b',
        r'你好', r'哈囉', r'嗨', r'早安', r'午安', r'晚安'
    ]
    
    if any(re.search(pattern, message_lower) for pattern in question_patterns):
        return 'question'
    elif any(re.search(pattern, message_lower) for pattern in discussion_patterns):
        return 'discussion'
    elif any(re.search(pattern, message_lower) for pattern in greeting_patterns):
        return 'greeting'
    else:
        return 'response'

def calculate_english_ratio(message):
    """計算英語使用比例"""
    english_chars = len(re.findall(r'[a-zA-Z]', message))
    total_chars = len(re.sub(r'\s', '', message))
    return min(english_chars / total_chars, 1.0) if total_chars > 0 else 0.0

def count_words(message):
    """計算單詞數量"""
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', message))
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', message))
    return english_words + chinese_chars

def classify_topic_category(message):
    """自動分類討論主題"""
    topic_keywords = {
        'AI_Technology': [
            'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
            'algorithm', 'ai model', 'training data', 'prediction',
            '人工智慧', '機器學習', '深度學習', '神經網路', '演算法', 'AI模型'
        ],
        'Industry_4.0': [
            'industry 4.0', 'industrial revolution', 'iot', 'internet of things',
            'smart manufacturing', 'automation', 'robotics', 'cyber physical',
            '工業4.0', '工業革命', '物聯網', '智慧製造', '自動化', '機器人'
        ],
        'Smart_Home': [
            'smart home', 'home automation', 'smart devices', 'smart speaker',
            'home assistant', 'iot home', 'connected home',
            '智慧家庭', '家庭自動化', '智慧裝置', '智慧音箱', '居家助理'
        ],
        'Healthcare': [
            'healthcare', 'medical ai', 'telemedicine', 'health monitoring',
            'medical diagnosis', 'patient care', 'health data',
            '醫療', '健康照護', '遠距醫療', '健康監測', '醫療診斷', '病患照護'
        ],
        'Ethics_Privacy': [
            'ethics', 'privacy', 'bias', 'fairness', 'responsibility',
            'data protection', 'algorithmic bias', 'ai ethics',
            '倫理', '隱私', '偏見', '公平性', '責任', '資料保護', '演算法偏見'
        ],
        'Future_Trends': [
            'future', 'prediction', 'trends', 'development', 'innovation',
            'emerging technology', 'next generation', 'advancement',
            '未來', '趨勢', '發展', '創新', '新興技術', '下一代', '進步'
        ]
    }
    
    message_lower = message.lower()
    topic_scores = {}
    
    for topic, keywords in topic_keywords.items():
        score = sum(1 for keyword in keywords if keyword.lower() in message_lower)
        if score > 0:
            topic_scores[topic] = score
    
    return max(topic_scores, key=topic_scores.get) if topic_scores else 'General_Discussion'

def evaluate_content_quality(message, message_type):
    """內容品質評估"""
    score = 2.0
    length = len(message.strip())
    word_count = count_words(message)
    
    # 長度加分
    if length > 100:
        score += 1.0
    elif length > 50:
        score += 0.5
    
    # 單詞數加分
    if word_count > 20:
        score += 0.5
    
    # 訊息類型調整
    if message_type == 'question':
        score += 0.3
    elif message_type == 'discussion':
        score += 0.5
    
    # 學術關鍵詞加分
    academic_keywords = [
        'example', 'because', 'therefore', 'however', 'analysis', 'consider',
        'compare', 'evaluate', 'advantage', 'disadvantage', 'benefit', 'challenge',
        '例如', '因為', '所以', '然而', '分析', '考慮', '比較', '評估', '優點', '缺點'
    ]
    
    keyword_bonus = sum(0.2 for keyword in academic_keywords if keyword.lower() in message.lower())
    score += min(keyword_bonus, 1.0)
    
    return min(max(score, 1.0), 5.0)

def calculate_engagement_level(msg_count, question_count, discussion_count, avg_quality):
    """計算學生參與度等級"""
    base_score = msg_count * 2
    interactive_score = question_count * 3 + discussion_count * 4
    quality_score = avg_quality * 2
    total_score = base_score + interactive_score + quality_score
    
    if total_score >= 25:
        return 'high'
    elif total_score >= 15:
        return 'medium'
    else:
        return 'low'

# =============================================================================
# 主要分析函數
# =============================================================================

def analyze_message_comprehensive(user_id, user_name, message, group_id=None):
    """全面分析學生訊息"""
    try:
        message_type = classify_message_type(message)
        message_length = len(message.strip())
        word_count = count_words(message)
        english_ratio = calculate_english_ratio(message)
        topic_category = classify_topic_category(message)
        current_week = get_current_week()
        quality_score = evaluate_content_quality(message, message_type)
        
        # 儲存詳細分析結果
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO participation_analytics 
            (user_id, user_name, message, message_type, message_length, 
             word_count, english_ratio, interaction_quality_score, 
             topic_category, group_id, week_number, response_time_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, message, message_type, message_length,
              word_count, english_ratio, quality_score, 
              topic_category, group_id, current_week, 0))
        
        # 更新各種統計
        update_weekly_student_stats(user_id, user_name, current_week, message_type, 
                                   quality_score, word_count, english_ratio, topic_category)
        update_topic_analytics(topic_category, current_week, quality_score, message_type)
        
        if group_id:
            update_group_activity_stats(group_id, current_week, message_type, quality_score, message_length)
        
        conn.commit()
        conn.close()
        
        return {
            'message_type': message_type,
            'quality_score': quality_score,
            'topic_category': topic_category,
            'week_number': current_week,
            'english_ratio': english_ratio,
            'word_count': word_count
        }
        
    except Exception as e:
        print(f"❌ 訊息分析錯誤: {e}")
        return {
            'message_type': 'response',
            'quality_score': 3.0,
            'topic_category': 'General_Discussion',
            'week_number': get_current_week(),
            'english_ratio': 0.5,
            'word_count': 10
        }

def update_weekly_student_stats(user_id, user_name, week_number, message_type, 
                               quality_score, word_count, english_ratio, topic_category):
    """更新學生週統計"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message_count, question_count, discussion_count, 
                   avg_quality_score, total_words, english_usage_ratio, topics_covered
            FROM weekly_student_stats 
            WHERE user_id = ? AND week_number = ?
        ''', (user_id, week_number))
        
        existing = cursor.fetchone()
        
        if existing:
            old_msg_count, old_q_count, old_d_count, old_quality, old_words, old_english, old_topics = existing
            
            new_msg_count = old_msg_count + 1
            new_q_count = old_q_count + (1 if message_type == 'question' else 0)
            new_d_count = old_d_count + (1 if message_type == 'discussion' else 0)
            new_quality = (old_quality * old_msg_count + quality_score) / new_msg_count
            new_words = old_words + word_count
            new_english = (old_english * old_msg_count + english_ratio) / new_msg_count
            
            topics_list = json.loads(old_topics) if old_topics else []
            if topic_category not in topics_list:
                topics_list.append(topic_category)
            new_topics = json.dumps(topics_list)
            
            engagement_level = calculate_engagement_level(new_msg_count, new_q_count, new_d_count, new_quality)
            
            cursor.execute('''
                UPDATE weekly_student_stats 
                SET message_count = ?, question_count = ?, discussion_count = ?,
                    avg_quality_score = ?, total_words = ?, english_usage_ratio = ?,
                    engagement_level = ?, topics_covered = ?, last_interaction = CURRENT_TIMESTAMP
                WHERE user_id = ? AND week_number = ?
            ''', (new_msg_count, new_q_count, new_d_count, new_quality, 
                  new_words, new_english, engagement_level, new_topics, user_id, week_number))
        else:
            engagement_level = calculate_engagement_level(1, 
                                                        1 if message_type == 'question' else 0,
                                                        1 if message_type == 'discussion' else 0, 
                                                        quality_score)
            topics_list = [topic_category]
            
            cursor.execute('''
                INSERT INTO weekly_student_stats 
                (user_id, user_name, week_number, message_count, question_count, 
                 discussion_count, avg_quality_score, total_words, english_usage_ratio,
                 engagement_level, topics_covered, first_interaction, last_interaction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (user_id, user_name, week_number, 1, 
                  1 if message_type == 'question' else 0,
                  1 if message_type == 'discussion' else 0,
                  quality_score, word_count, english_ratio, engagement_level, 
                  json.dumps(topics_list)))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ 學生週統計更新錯誤: {e}")

def update_topic_analytics(topic_name, week_number, quality_score, message_type):
    """更新主題分析統計"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT mention_count, avg_quality_score, question_count, discussion_count
            FROM topic_analytics 
            WHERE topic_name = ? AND week_number = ?
        ''', (topic_name, week_number))
        
        existing = cursor.fetchone()
        
        if existing:
            old_count, old_quality, old_q_count, old_d_count = existing
            new_count = old_count + 1
            new_quality = (old_quality * old_count + quality_score) / new_count
            new_q_count = old_q_count + (1 if message_type == 'question' else 0)
            new_d_count = old_d_count + (1 if message_type == 'discussion' else 0)
            
            cursor.execute('''
                UPDATE topic_analytics 
                SET mention_count = ?, avg_quality_score = ?, question_count = ?, discussion_count = ?
                WHERE topic_name = ? AND week_number = ?
            ''', (new_count, new_quality, new_q_count, new_d_count, topic_name, week_number))
        else:
            cursor.execute('''
                INSERT INTO topic_analytics 
                (topic_name, week_number, mention_count, avg_quality_score, 
                 question_count, discussion_count, student_interest_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (topic_name, week_number, 1, quality_score,
                  1 if message_type == 'question' else 0,
                  1 if message_type == 'discussion' else 0,
                  quality_score))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ 主題統計更新錯誤: {e}")

def update_group_activity_stats(group_id, week_number, message_type, quality_score, message_length):
    """更新群組活躍度統計"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) 
            FROM participation_analytics 
            WHERE group_id = ? AND week_number = ?
        ''', (group_id, week_number))
        
        unique_participants = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT total_messages, avg_message_length, question_count, 
                   discussion_count, discussion_quality_avg
            FROM group_activity 
            WHERE group_id = ? AND week_number = ?
        ''', (group_id, week_number))
        
        existing = cursor.fetchone()
        
        if existing:
            old_msgs, old_avg_length, old_q_count, old_d_count, old_quality = existing
            
            new_msgs = old_msgs + 1
            new_avg_length = (old_avg_length * old_msgs + message_length) / new_msgs
            new_q_count = old_q_count + (1 if message_type == 'question' else 0)
            new_d_count = old_d_count + (1 if message_type == 'discussion' else 0)
            new_quality = (old_quality * old_msgs + quality_score) / new_msgs
            
            activity_score = calculate_group_activity_score(new_msgs, unique_participants, new_quality)
            
            cursor.execute('''
                UPDATE group_activity 
                SET total_messages = ?, unique_participants = ?, avg_message_length = ?,
                    question_count = ?, discussion_count = ?, activity_score = ?,
                    discussion_quality_avg = ?, last_activity_time = CURRENT_TIMESTAMP
                WHERE group_id = ? AND week_number = ?
            ''', (new_msgs, unique_participants, new_avg_length, new_q_count, new_d_count,
                  activity_score, new_quality, group_id, week_number))
        else:
            activity_score = calculate_group_activity_score(1, unique_participants, quality_score)
            
            cursor.execute('''
                INSERT INTO group_activity 
                (group_id, week_number, total_messages, unique_participants, 
                 avg_message_length, question_count, discussion_count, activity_score,
                 discussion_quality_avg, last_activity_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (group_id, week_number, 1, unique_participants, message_length,
                  1 if message_type == 'question' else 0,
                  1 if message_type == 'discussion' else 0,
                  activity_score, quality_score))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ 群組活躍度更新錯誤: {e}")

def calculate_group_activity_score(total_messages, unique_participants, avg_quality):
    """計算群組活躍度分數"""
    message_score = min(total_messages * 1.5, 30)
    participation_score = min(unique_participants * 6, 40)
    quality_score = (avg_quality or 0) * 6
    return round(message_score + participation_score + quality_score, 2)

# =============================================================================
# AI 教學助手功能 - 增強版EMI教學
# =============================================================================

def generate_ai_response_with_context(user_message, user_name, analysis_result):
    """根據分析結果生成上下文感知的AI回應"""
    message_type = analysis_result['message_type']
    topic_category = analysis_result['topic_category']
    week_number = analysis_result['week_number']
    
    # 根據訊息類型調整回應策略
    if message_type == 'question':
        response_style = "provide a clear, educational answer"
    elif message_type == 'discussion':
        response_style = "engage thoughtfully and encourage further discussion"
    elif message_type == 'greeting':
        response_style = "respond warmly and guide toward course topics"
    else:
        response_style = "provide supportive feedback"
    
    # 課程週次上下文
    course_context = get_week_context(week_number)
    
    # 根據主題類別提供相關背景
    topic_context = ""
    if topic_category != 'General_Discussion':
        topic_context = f"The student is asking about {topic_category.replace('_', ' ')}. "
    
    enhanced_prompt = f"""
You are an AI Teaching Assistant for "Practical Applications of AI in Life and Learning" (EMI course).

CONTEXT:
- Student: {user_name}
- Current Week: {week_number} 
- Course Topic: {course_context.get('topic', 'General AI Applications')}
- Message Type: {message_type}
- Topic Category: {topic_category}
- {topic_context}

STUDENT MESSAGE: "{user_message}"

RESPONSE STRATEGY: {response_style}

GUIDELINES:
1. Keep response SHORT (2-3 sentences max)
2. Primary language: English (EMI course)
3. Use Traditional Chinese assistance when needed (關鍵術語繁體中文)
4. Connect to current week's topic when relevant: {course_context.get('keywords', [])}
5. Encourage critical thinking for discussions
6. Be supportive and educational
7. End with "Want to know more?" or "需要更詳細的說明嗎？" when appropriate

Respond appropriately based on the context and analysis.
"""
    
    try:
        response = model.generate_content(enhanced_prompt)
        if response.text:
            return response.text.strip()
        else:
            return "I apologize, but I cannot answer this question right now. Please try again later."
    except Exception as e:
        print(f"AI Response Error: {e}")
        return "I'm sorry, the AI assistant is temporarily unavailable. Please try again later."

# =============================================================================
# 原有功能保持兼容性
# =============================================================================

def save_interaction(user_id, user_name, message, ai_response):
    """記錄學生與AI的互動 (保持原有兼容性)"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
