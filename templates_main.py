# templates_main.py - 主要頁面模板

# =========================================
# 首頁模板
# =========================================

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EMI 智能教學助理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .header h1 {
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .navigation {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
        }
        .nav-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        .nav-item {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-decoration: none;
            text-align: center;
            transition: transform 0.3s ease;
        }
        .nav-item:hover {
            transform: translateY(-5px);
            text-decoration: none;
            color: white;
        }
        .nav-icon {
            font-size: 2em;
            margin-bottom: 10px;
            display: block;
        }
        .recent-activity {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
        }
        .activity-item {
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .activity-item:last-child {
            border-bottom: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 EMI 智能教學助理</h1>
            <p>生成式AI輔助的雙語教學創新平台</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_students or 0 }}</div>
                <div class="stat-label">總學生數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.real_students or 0 }}</div>
                <div class="stat-label">真實學生</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_messages or 0 }}</div>
                <div class="stat-label">總訊息數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.avg_participation or 0 }}%</div>
                <div class="stat-label">平均參與度</div>
            </div>
        </div>

        <div class="navigation">
            <h3 style="margin-bottom: 20px; color: #2c3e50;">🎯 功能導航</h3>
            <div class="nav-grid">
                <a href="/teaching-insights" class="nav-item">
                    <span class="nav-icon">📊</span>
                    <strong>教師分析後台</strong>
                    <div>視覺化問題分類統計</div>
                </a>
                <a href="/conversation-summaries" class="nav-item">
                    <span class="nav-icon">💬</span>
                    <strong>智能對話摘要</strong>
                    <div>教學重點提取</div>
                </a>
                <a href="/learning-recommendations" class="nav-item">
                    <span class="nav-icon">🎯</span>
                    <strong>個人化學習建議</strong>
                    <div>基於分析的學習指導</div>
                </a>
                <a href="/storage-management" class="nav-item">
                    <span class="nav-icon">💾</span>
                    <strong>儲存監控</strong>
                    <div>空間使用量管理</div>
                </a>
                <a href="/data-export" class="nav-item">
                    <span class="nav-icon">📤</span>
                    <strong>資料匯出</strong>
                    <div>教學研究資料下載</div>
                </a>
                <a href="/students" class="nav-item">
                    <span class="nav-icon">👥</span>
                    <strong>學生管理</strong>
                    <div>學生列表與詳細分析</div>
                </a>
            </div>
        </div>

        <div class="recent-activity">
            <h3 style="margin-bottom: 15px; color: #2c3e50;">📈 最近活動</h3>
            {% for message in recent_messages %}
            <div class="activity-item">
                <strong>{{ message.student.name if message.student else '未知學生' }}</strong>
                <span style="color: #666;">{{ message.timestamp.strftime('%m-%d %H:%M') }}</span>
                <div style="color: #888; font-size: 0.9em;">
                    {{ message.message_type }}: {{ message.content[:50] }}...
                </div>
            </div>
            {% else %}
            <div style="text-align: center; color: #666; padding: 20px;">
                暫無最近活動
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

# =========================================
# 學生列表模板
# =========================================

STUDENTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>學生管理 - EMI 教學助理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .students-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .student-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        .student-card:hover {
            transform: translateY(-5px);
        }
        .demo-student {
            border: 2px dashed #28a745;
            background: rgba(40, 167, 69, 0.05);
        }
        .demo-badge {
            background: #28a745;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-left: 10px;
        }
        .student-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        .student-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(45deg, #84fab0, #8fd3f4);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2em;
            font-weight: bold;
            margin-right: 15px;
        }
        .student-info h3 {
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .student-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        .stat-item {
            text-align: center;
            padding: 10px;
            background: rgba(132, 250, 176, 0.2);
            border-radius: 8px;
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #84fab0;
        }
        .stat-label {
            font-size: 0.8em;
            color: #666;
        }
        .view-btn {
            width: 100%;
            padding: 10px;
            background: linear-gradient(45deg, #84fab0, #8fd3f4);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        .view-btn:hover {
            transform: translateY(-2px);
            text-decoration: none;
            color: white;
        }
        .legend {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 25px;
            display: flex;
            gap: 30px;
            align-items: center;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .legend-box {
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }
        .legend-real {
            background: rgba(132, 250, 176, 0.3);
            border: 2px solid #84fab0;
        }
        .legend-demo {
            background: rgba(40, 167, 69, 0.05);
            border: 2px dashed #28a745;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👥 學生管理</h1>
            <p>查看所有學生的學習狀況和分析報告</p>
        </div>

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

        <div class="students-grid">
            {% for student in students %}
            <div class="student-card {% if student.name.startswith('[DEMO]') %}demo-student{% endif %}">
                <div class="student-header">
                    <div class="student-avatar">
                        {{ student.name[0] }}
                    </div>
                    <div class="student-info">
                        <h3>
                            {{ student.name }}
                            {% if student.name.startswith('[DEMO]') %}
                                <span class="demo-badge">演示</span>
                            {% endif %}
                        </h3>
                        <div style="color: #666; font-size: 0.9em;">
                            最後活動: {{ student.last_active.strftime('%m-%d %H:%M') if student.last_active else '無記錄' }}
                        </div>
                    </div>
                </div>

                <div class="student-stats">
                    <div class="stat-item">
                        <div class="stat-value">{{ student.participation_rate }}%</div>
                        <div class="stat-label">參與度</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{{ student.question_count }}</div>
                        <div class="stat-label">提問數</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{{ student.message_count }}</div>
                        <div class="stat-label">總訊息</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{{ student.active_days }}</div>
                        <div class="stat-label">活躍天數</div>
                    </div>
                </div>

                <a href="/student/{{ student.id }}" class="view-btn">
                    📋 查看詳細分析
                </a>
            </div>
            {% else %}
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <h3>🎓 準備開始</h3>
                <p>目前沒有學生資料。當學生開始使用系統後，這裡將顯示他們的學習分析。</p>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

# =========================================
# 學生詳細頁面模板
# =========================================

STUDENT_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ student.name }} - 學習分析</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .student-profile {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
        }
        .profile-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(45deg, #fbc2eb, #a6c1ee);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2em;
            font-weight: bold;
        }
        .profile-info h1 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        .demo-warning {
            background: rgba(40, 167, 69, 0.1);
            border: 1px solid #28a745;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            color: #155724;
        }
        .analysis-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
        }
        .analysis-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .card-title {
            font-size: 1.2em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .messages-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .message-item {
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .message-item:last-child {
            border-bottom: none;
        }
        .message-meta {
            font-size: 0.8em;
            color: #666;
            margin-bottom: 5px;
        }
        .back-btn {
            background: linear-gradient(45deg, #fbc2eb, #a6c1ee);
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            text-decoration: none;
            display: inline-block;
            margin-bottom: 20px;
            transition: transform 0.3s ease;
        }
        .back-btn:hover {
            transform: translateY(-2px);
            text-decoration: none;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/students" class="back-btn">← 返回學生列表</a>

        <div class="header">
            <div class="student-profile">
                <div class="profile-avatar">
                    {{ student.name[0] }}
                </div>
                <div class="profile-info">
                    <h1>{{ student.name }}</h1>
                    <p>參與度: {{ student.participation_rate }}% | 提問數: {{ student.question_count }} | 總訊息: {{ student.message_count }}</p>
                </div>
            </div>

            {% if student.name.startswith('[DEMO]') %}
            <div class="demo-warning">
                <strong>⚠️ 演示資料說明</strong><br>
                這是系統演示用的虛擬學生資料，用於展示平台功能。真實學生的資料會有更豐富的學習分析內容。
            </div>
            {% endif %}
        </div>

        <div class="analysis-grid">
            <div class="analysis-card">
                <div class="card-title">
                    <span>📊</span>
                    學習統計
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                    <div style="text-align: center; padding: 15px; background: rgba(251, 194, 235, 0.2); border-radius: 8px;">
                        <div style="font-size: 1.8em; font-weight: bold; color: #fbc2eb;">{{ student.participation_rate }}%</div>
                        <div style="color: #666;">參與度</div>
                    </div>
                    <div style="text-align: center; padding: 15px; background: rgba(166, 193, 238, 0.2); border-radius: 8px;">
                        <div style="font-size: 1.8em; font-weight: bold; color: #a6c1ee;">{{ student.question_rate or 0 }}%</div>
                        <div style="color: #666;">提問率</div>
                    </div>
                </div>
            </div>

            <div class="analysis-card">
                <div class="card-title">
                    <span>🤖</span>
                    AI 學習分析
                </div>
                <div style="line-height: 1.6;">
                    {% if analysis %}
                        {{ analysis }}
                    {% else %}
                        <p style="color: #666;">正在分析學生學習模式，請稍後查看詳細分析結果...</p>
                    {% endif %}
                </div>
            </div>

            <div class="analysis-card">
                <div class="card-title">
                    <span>💬</span>
                    對話摘要
                </div>
                <div style="line-height: 1.6;">
                    {% if conversation_summary %}
                        {{ conversation_summary }}
                    {% else %}
                        <p style="color: #666;">需要更多對話資料來生成摘要...</p>
                    {% endif %}
                </div>
            </div>

            <div class="analysis-card">
                <div class="card-title">
                    <span>📝</span>
                    最近訊息
                </div>
                <div class="messages-list">
                    {% for message in messages %}
                    <div class="message-item">
                        <div class="message-meta">
                            {{ message.timestamp.strftime('%m-%d %H:%M') }} - {{ message.message_type }}
                        </div>
                        <div>{{ message.content[:100] }}{% if message.content|length > 100 %}...{% endif %}</div>
                    </div>
                    {% else %}
                    <div style="text-align: center; color: #666; padding: 20px;">
                        暫無訊息記錄
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
