# templates.py - HTML 模板

HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>個人化學習分析系統</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        .header {
            background: white;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        h1 { 
            color: #1f2937; 
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .subtitle { 
            color: #6b7280; 
            font-size: 1.1em;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-number {
            font-size: 3em;
            font-weight: bold;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 10px 0;
        }
        
        .stat-label {
            color: #6b7280;
            font-size: 1.1em;
        }
        
        .nav-buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .nav-btn {
            background: white;
            color: #6366f1;
            text-decoration: none;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            font-weight: bold;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }
        
        .nav-btn:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        }
        
        .recent-activity {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-top: 30px;
        }
        
        .activity-item {
            padding: 15px 0;
            border-bottom: 1px solid #f3f4f6;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .activity-item:last-child {
            border-bottom: none;
        }
        
        .activity-text {
            color: #374151;
        }
        
        .activity-time {
            color: #9ca3af;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 個人化學習分析系統</h1>
            <p class="subtitle">EMI 課程學生參與度追蹤與 AI 輔助分析</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_students }}</div>
                <div class="stat-label">註冊學生</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_messages }}</div>
                <div class="stat-label">總訊息數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_questions }}</div>
                <div class="stat-label">學生提問</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ active_today }}</div>
                <div class="stat-label">今日活躍</div>
            </div>
        </div>
        
        <div class="nav-buttons">
            <a href="/students" class="nav-btn">👥 學生列表</a>
            <a href="/analysis" class="nav-btn">📊 分析報告</a>
            <a href="/insights" class="nav-btn">💡 AI 洞察</a>
            <a href="/export" class="nav-btn">📄 匯出數據</a>
        </div>
        
        <div class="recent-activity">
            <h3 style="margin-bottom: 20px; color: #374151;">📈 近期活動</h3>
            {% for activity in recent_activities %}
            <div class="activity-item">
                <div class="activity-text">{{ activity.text }}</div>
                <div class="activity-time">{{ activity.time }}</div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

STUDENTS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>學生列表 - 學習分析系統</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        .header {
            background: white;
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .back-btn {
            background: #6366f1;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            text-decoration: none;
            margin-bottom: 20px;
            display: inline-block;
        }
        
        .students-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        
        .student-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        
        .student-card:hover {
            transform: translateY(-5px);
        }
        
        .student-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .student-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.2em;
            margin-right: 15px;
        }
        
        .student-info h3 {
            color: #1f2937;
            margin-bottom: 5px;
        }
        
        .student-status {
            background: #10b981;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }
        
        .student-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-item {
            text-align: center;
            padding: 15px;
            background: #f9fafb;
            border-radius: 10px;
        }
        
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #6366f1;
        }
        
        .stat-title {
            color: #6b7280;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .detail-btn {
            background: #6366f1;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            text-decoration: none;
            display: block;
            text-align: center;
            transition: background 0.3s;
        }
        
        .detail-btn:hover {
            background: #5b57e0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← 返回首頁</a>
            <h1>👥 學生列表</h1>
            <p>共 {{ students|length }} 位學生</p>
        </div>
        
        <div class="students-grid">
            {% for student in students %}
            <div class="student-card">
                <div class="student-header">
                    <div class="student-avatar">{{ student.name[0] }}</div>
                    <div class="student-info">
                        <h3>{{ student.name }}</h3>
                        <span class="student-status">活躍</span>
                    </div>
                </div>
                
                <div class="student-stats">
                    <div class="stat-item">
                        <div class="stat-value">{{ student.message_count }}</div>
                        <div class="stat-title">總發言</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{{ student.question_count }}</div>
                        <div class="stat-title">提問數</div>
                    </div>
                </div>
                
                <a href="/student/{{ student.id }}" class="detail-btn">查看詳細分析</a>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

STUDENT_DETAIL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ student.name }} - 學習分析</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        .header {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .back-btn {
            background: #6366f1;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            text-decoration: none;
            margin-bottom: 20px;
            display: inline-block;
        }
        
        .student-profile {
            display: flex;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .profile-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 2em;
            margin-right: 20px;
        }
        
        .profile-info h1 {
            color: #1f2937;
            margin-bottom: 10px;
        }
        
        .profile-meta {
            color: #6b7280;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .metric-label {
            color: #6b7280;
            font-size: 1.1em;
        }
        
        .analysis-section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .section-title {
            color: #1f2937;
            font-size: 1.5em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }
        
        .section-title::before {
            content: '📊';
            margin-right: 10px;
        }
        
        .question-list {
            background: #f9fafb;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .question-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #6366f1;
        }
        
        .question-item:last-child {
            margin-bottom: 0;
        }
        
        .question-text {
            color: #374151;
            margin-bottom: 5px;
        }
        
        .question-time {
            color: #9ca3af;
            font-size: 0.9em;
        }
        
        .ai-insight {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #0ea5e9;
        }
        
        .insight-text {
            color: #0c4a6e;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/students" class="back-btn">← 返回學生列表</a>
            
            <div class="student-profile">
                <div class="profile-avatar">{{ student.name[0] }}</div>
                <div class="profile-info">
                    <h1>{{ student.name }}</h1>
                    <div class="profile-meta">
                        註冊時間：{{ student.created_at.strftime('%Y-%m-%d') }} | 
                        最後活動：{{ student.last_active.strftime('%Y-%m-%d %H:%M') if student.last_active else '無' }}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{{ student.message_count }}</div>
                <div class="metric-label">總發言數</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ student.question_count }}</div>
                <div class="metric-label">提問次數</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.1f"|format(student.participation_rate) }}%</div>
                <div class="metric-label">參與度</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.1f"|format(student.question_rate) }}%</div>
                <div class="metric-label">提問率</div>
            </div>
        </div>
        
        <div class="analysis-section">
            <h2 class="section-title">近期提問記錄</h2>
            <div class="question-list">
                {% for question in recent_questions %}
                <div class="question-item">
                    <div class="question-text">{{ question.content }}</div>
                    <div class="question-time">{{ question.timestamp.strftime('%Y-%m-%d %H:%M') }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        {% if ai_analysis %}
        <div class="analysis-section">
            <h2 class="section-title">💡 AI 分析洞察</h2>
            <div class="ai-insight">
                <div class="insight-text">{{ ai_analysis.content }}</div>
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

ANALYSIS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>分析報告 - 學習分析系統</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        .header {
            background: white;
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .back-btn {
            background: #6366f1;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            text-decoration: none;
            margin-bottom: 20px;
            display: inline-block;
        }
        
        .report-section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .section-title {
            color: #1f2937;
            font-size: 1.5em;
            margin-bottom: 20px;
            border-bottom: 2px solid #6366f1;
            padding-bottom: 10px;
        }
        
        .chart-placeholder {
            background: #f9fafb;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            color: #6b7280;
            font-size: 1.1em;
            margin-bottom: 20px;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .summary-card {
            background: #f8fafc;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        
        .summary-number {
            font-size: 2em;
            font-weight: bold;
            color: #6366f1;
            margin-bottom: 10px;
        }
        
        .summary-label {
            color: #64748b;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← 返回首頁</a>
            <h1>📊 班級分析報告</h1>
            <p>整體學習參與度分析</p>
        </div>
        
        <div class="report-section">
            <h2 class="section-title">參與度趨勢</h2>
            <div class="chart-placeholder">
                📈 參與度趨勢圖<br>
                (可整合 Chart.js 或其他圖表庫)
            </div>
        </div>
        
        <div class="report-section">
            <h2 class="section-title">整體統計</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="summary-number">{{ stats.avg_participation }}%</div>
                    <div class="summary-label">平均參與度</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number">{{ stats.total_questions }}</div>
                    <div class="summary-label">總提問數</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number">{{ stats.active_students }}</div>
                    <div class="summary-label">活躍學生</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number">{{ stats.avg_questions_per_student }}</div>
                    <div class="summary-label">人均提問</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

INSIGHTS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI 洞察 - 學習分析系統</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        .header {
            background: white;
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .back-btn {
            background: #6366f1;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            text-decoration: none;
            margin-bottom: 20px;
            display: inline-block;
        }
        
        .insight-card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }
        
        .insight-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .insight-icon {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.5em;
            margin-right: 15px;
        }
        
        .insight-meta {
            flex: 1;
        }
        
        .insight-title {
            color: #1f2937;
            font-size: 1.3em;
            margin-bottom: 5px;
        }
        
        .insight-time {
            color: #6b7280;
            font-size: 0.9em;
        }
        
        .insight-content {
            color: #374151;
            line-height: 1.6;
            font-size: 1.1em;
        }
        
        .insight-type {
            background: #ddd6fe;
            color: #7c3aed;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .no-insights {
            text-align: center;
            color: #6b7280;
            font-size: 1.1em;
            padding: 40px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← 返回首頁</a>
            <h1>💡 AI 洞察報告</h1>
            <p>智能分析學習模式與建議</p>
        </div>
        
        {% if insights %}
            {% for insight in insights %}
            <div class="insight-card">
                <div class="insight-header">
                    <div class="insight-icon">🤖</div>
                    <div class="insight-meta">
                        <div class="insight-title">{{ insight.title }}</div>
                        <div class="insight-time">
                            {{ insight.created_at.strftime('%Y-%m-%d %H:%M') }}
                            <span class="insight-type">{{ insight.analysis_type }}</span>
                        </div>
                    </div>
                </div>
                <div class="insight-content">{{ insight.content }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="insight-card">
                <div class="no-insights">
                    🔍 尚無 AI 洞察報告<br>
                    系統會在收集足夠數據後自動生成分析
                </div>
            </div>
        {% endif %}
    </div>
</body>
</html>
'''
