# templates.py - 簡化版 HTML 模板

HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>個人化學習分析系統</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .nav-links { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .nav-btn { background: #007bff; color: white; padding: 15px; text-decoration: none; border-radius: 5px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 個人化學習分析系統</h1>
            <p>EMI 課程學生參與度追蹤與 AI 輔助分析</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ total_students }}</div>
                <div>註冊學生</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_messages }}</div>
                <div>總訊息數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_questions }}</div>
                <div>學生提問</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ active_today }}</div>
                <div>今日活躍</div>
            </div>
        </div>
        
        <div class="nav-links">
            <a href="/students" class="nav-btn">👥 學生列表</a>
            <a href="/analysis" class="nav-btn">📊 分析報告</a>
            <a href="/insights" class="nav-btn">💡 AI 洞察</a>
            <a href="/dashboard" class="nav-btn">📈 儀表板</a>
            <a href="/export?format=csv&type=students" class="nav-btn">📄 匯出數據</a>
        </div>
    </div>
</body>
</html>
'''

STUDENTS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>學生列表</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .back-btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
        .students-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .student-card { background: white; padding: 20px; border-radius: 10px; position: relative; }
        .student-card.demo { border: 2px dashed #28a745; background: #f8fff8; }
        .demo-badge { position: absolute; top: 10px; right: 10px; background: #28a745; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7em; font-weight: bold; }
        .student-header { display: flex; align-items: center; margin-bottom: 15px; }
        .student-avatar { width: 50px; height: 50px; border-radius: 50%; background: #007bff; color: white; display: flex; align-items: center; justify-content: center; margin-right: 15px; font-weight: bold; }
        .student-avatar.demo { background: #28a745; }
        .student-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
        .stat-item { text-align: center; padding: 10px; background: #f8f9fa; border-radius: 5px; }
        .detail-btn { background: #007bff; color: white; padding: 10px; text-decoration: none; border-radius: 5px; text-align: center; display: block; }
        .filter-info { background: #e9ecef; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .legend { display: flex; gap: 20px; margin: 10px 0; }
        .legend-item { display: flex; align-items: center; gap: 8px; }
        .legend-box { width: 20px; height: 20px; border-radius: 4px; }
        .legend-real { background: white; border: 2px solid #007bff; }
        .legend-demo { background: #f8fff8; border: 2px dashed #28a745; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← 返回首頁</a>
            <h1>👥 學生列表</h1>
            <div class="filter-info">
                <p><strong>學生總數：{{ students|length }}</strong></p>
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-box legend-real"></div>
                        <span>真實學生</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-box legend-demo"></div>
                        <span>演示資料</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="students-grid">
            {% for student in students %}
            <div class="student-card {{ 'demo' if student.name.startswith('[DEMO]') else '' }}">
                {% if student.name.startswith('[DEMO]') %}
                <div class="demo-badge">演示</div>
                {% endif %}
                
                <div class="student-header">
                    <div class="student-avatar {{ 'demo' if student.name.startswith('[DEMO]') else '' }}">
                        {{ student.name.replace('[DEMO] ', '')[0] if student.name else '?' }}
                    </div>
                    <div>
                        <h3>{{ student.name.replace('[DEMO] ', '') if student.name.startswith('[DEMO]') else (student.name or '未知用戶') }}</h3>
                        {% if student.name.startswith('[DEMO]') %}
                            <small style="color: #28a745; font-weight: bold;">🎭 系統演示資料</small>
                        {% else %}
                            <span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;">
                                {{ '活躍' if student.is_active else '不活躍' }}
                            </span>
                        {% endif %}
                    </div>
                </div>
                
                <div class="student-stats">
                    <div class="stat-item">
                        <div style="font-size: 1.5em; font-weight: bold; color: #007bff;">{{ student.message_count }}</div>
                        <div>總發言</div>
                    </div>
                    <div class="stat-item">
                        <div style="font-size: 1.5em; font-weight: bold; color: #007bff;">{{ student.question_count }}</div>
                        <div>提問數</div>
                    </div>
                </div>
                
                <a href="/student/{{ student.id }}" class="detail-btn">
                    {% if student.name.startswith('[DEMO]') %}
                        🎭 查看演示分析
                    {% else %}
                        📊 查看詳細分析
                    {% endif %}
                </a>
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
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .back-btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
        .profile { display: flex; align-items: center; margin: 20px 0; }
        .avatar { width: 80px; height: 80px; border-radius: 50%; background: #007bff; color: white; display: flex; align-items: center; justify-content: center; font-size: 2em; margin-right: 20px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 10px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .section { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .question-item { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/students" class="back-btn">← 返回學生列表</a>
            <div class="profile">
                <div class="avatar">{{ student.name[0] if student.name else '?' }}</div>
                <div>
                    <h1>{{ student.name or '未知用戶' }}</h1>
                    <p>註冊時間：{{ student.created_at.strftime('%Y-%m-%d') }}</p>
                </div>
            </div>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{{ student.message_count }}</div>
                <div>總發言數</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ student.question_count }}</div>
                <div>提問次數</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.1f"|format(student.participation_rate) }}%</div>
                <div>參與度</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.1f"|format(student.question_rate) }}%</div>
                <div>提問率</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📝 近期提問記錄</h2>
            {% if recent_questions %}
                {% for question in recent_questions %}
                <div class="question-item">
                    <div>{{ question.content }}</div>
                    <small style="color: #666;">{{ question.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
                </div>
                {% endfor %}
            {% else %}
                <p>尚無提問記錄</p>
            {% endif %}
        </div>
        
        {% if ai_analysis %}
        <div class="section">
            <h2>🤖 AI 分析洞察</h2>
            <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; border-left: 4px solid #2196f3;">
                {{ ai_analysis.content }}
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
    <title>分析報告</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .back-btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
        .section { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .chart-placeholder { background: #f8f9fa; padding: 40px; text-align: center; border-radius: 10px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← 返回首頁</a>
            <h1>📊 班級分析報告</h1>
        </div>
        
        <div class="section">
            <h2>參與度趨勢</h2>
            <div class="chart-placeholder">
                📈 參與度趨勢圖<br>
                (可整合圖表庫)
            </div>
        </div>
        
        <div class="section">
            <h2>整體統計</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{{ stats.avg_participation or 0 }}%</div>
                    <div>平均參與度</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.total_questions or 0 }}</div>
                    <div>總提問數</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.active_students or 0 }}</div>
                    <div>活躍學生</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.avg_questions_per_student or 0 }}</div>
                    <div>人均提問</div>
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
    <title>AI 洞察</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .back-btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
        .insight-card { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .insight-header { display: flex; align-items: center; margin-bottom: 15px; }
        .insight-icon { width: 40px; height: 40px; background: #007bff; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px; }
        .insight-content { line-height: 1.6; }
        .no-insights { text-align: center; padding: 40px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← 返回首頁</a>
            <h1>💡 AI 洞察報告</h1>
        </div>
        
        {% if insights %}
            {% for insight in insights %}
            <div class="insight-card">
                <div class="insight-header">
                    <div class="insight-icon">🤖</div>
                    <div>
                        <h3>{{ insight.title or '學習分析' }}</h3>
                        <small>{{ insight.created_at.strftime('%Y-%m-%d %H:%M') }}</small>
                    </div>
                </div>
                <div class="insight-content">{{ insight.content }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div
