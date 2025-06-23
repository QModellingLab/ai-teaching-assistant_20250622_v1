# templates_main.py - 完整的真實資料版本（第一部分）

# =========================================
# 首頁模板 - 完全專注真實資料
# =========================================

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EMI 智能教學助理 - 真實學習分析</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            min-height: 100vh;
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        .header h1 {
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .back-btn {
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            padding: 12px 20px;
            border-radius: 25px;
            text-decoration: none;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        .back-btn:hover {
            background: white;
            transform: translateY(-2px);
            text-decoration: none;
            color: #333;
        }
        
        /* 真實資料狀態 */
        .real-data-status {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 25px;
            text-align: center;
            border: 1px solid #c3e6cb;
        }
        .no-real-data {
            background: #fff3cd;
            color: #856404;
            padding: 40px;
            border-radius: 15px;
            margin-bottom: 25px;
            text-align: center;
            border: 2px dashed #ffc107;
        }
        .no-real-data h3 {
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        
        /* 統計卡片 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            text-align: center;
            transition: transform 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-icon {
            font-size: 2.5em;
            margin-bottom: 15px;
        }
        .stat-number {
            font-size: 2.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #7f8c8d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* 最近活動 */
        .activity-section {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        .activity-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }
        .activity-item {
            display: flex;
            align-items: center;
            padding: 15px;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #3498db;
        }
        .activity-icon {
            font-size: 1.5em;
            margin-right: 15px;
            width: 40px;
            text-align: center;
        }
        .activity-content {
            flex: 1;
        }
        .activity-student {
            font-weight: bold;
            color: #2c3e50;
        }
        .activity-message {
            color: #7f8c8d;
            margin: 5px 0;
        }
        .activity-time {
            font-size: 0.8em;
            color: #95a5a6;
        }
        
        /* 等待狀態動畫 */
        .waiting-animation {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* 響應式設計 */
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .header { padding: 20px; }
            .header h1 { font-size: 2em; }
            .stats-grid { grid-template-columns: 1fr; }
            .activity-header { flex-direction: column; gap: 15px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 EMI 智能教學助理</h1>
            <p>專為真實教學情境設計的 AI 學習分析平台</p>
        </div>

        <!-- 真實資料狀態檢查 -->
        {% if stats.real_students > 0 %}
        <div class="real-data-status">
            ✅ 系統已有 {{ stats.real_students }} 位真實學生資料，分析結果基於實際互動
        </div>
        {% else %}
        <div class="no-real-data">
            <h3>⏳ 等待真實學生資料</h3>
            <p>系統已準備就緒，等待學生通過 LINE Bot 開始互動</p>
            <p>一旦有學生開始使用，這裡將顯示真實的學習分析</p>
            <div class="waiting-animation"></div>
        </div>
        {% endif %}

        <!-- 統計數據 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">👥</div>
                <div class="stat-number">{{ stats.real_students }}</div>
                <div class="stat-label">真實學生</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">💬</div>
                <div class="stat-number">{{ stats.total_messages }}</div>
                <div class="stat-label">總互動次數</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🔥</div>
                <div class="stat-number">{{ stats.active_conversations }}</div>
                <div class="stat-label">活躍對話</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-number">{{ "%.1f"|format(stats.avg_engagement) }}%</div>
                <div class="stat-label">平均參與度</div>
            </div>
        </div>

        <!-- 最近活動 -->
        <div class="activity-section">
            <div class="activity-header">
                <h2>📈 最近學習活動</h2>
                <a href="/students" class="btn" style="text-decoration: none; background: #3498db; color: white; padding: 10px 20px; border-radius: 25px;">查看所有學生</a>
            </div>
            
            {% if recent_messages %}
                {% for message in recent_messages %}
                <div class="activity-item">
                    <div class="activity-icon">
                        {% if message.message_type == '問題' %}💡
                        {% elif message.message_type == '回答' %}💭
                        {% else %}📝{% endif %}
                    </div>
                    <div class="activity-content">
                        <div class="activity-student">{{ message.student.name }}</div>
                        <div class="activity-message">{{ message.content[:80] }}{% if message.content|length > 80 %}...{% endif %}</div>
                        <div class="activity-time">{{ message.timestamp.strftime('%m/%d %H:%M') }}</div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div style="text-align: center; color: #7f8c8d; padding: 40px;">
                    <h3>🎯 等待學生互動</h3>
                    <p>當學生開始使用 LINE Bot 時，最新的學習活動將在這裡顯示</p>
                </div>
            {% endif %}
        </div>

        <!-- 快速功能導航 -->
        <div class="stats-grid">
            <a href="/students" class="stat-card" style="text-decoration: none; color: inherit;">
                <div class="stat-icon">👥</div>
                <div style="font-size: 1.2em; margin-top: 10px;">學生管理</div>
            </a>
            <a href="/teaching-insights" class="stat-card" style="text-decoration: none; color: inherit;">
                <div class="stat-icon">📊</div>
                <div style="font-size: 1.2em; margin-top: 10px;">教學洞察</div>
            </a>
            <a href="/conversation-summaries" class="stat-card" style="text-decoration: none; color: inherit;">
                <div class="stat-icon">💬</div>
                <div style="font-size: 1.2em; margin-top: 10px;">對話摘要</div>
            </a>
            <a href="/learning-recommendations" class="stat-card" style="text-decoration: none; color: inherit;">
                <div class="stat-icon">🎯</div>
                <div style="font-size: 1.2em; margin-top: 10px;">學習建議</div>
            </a>
        </div>
    </div>

    <script>
        // 自動刷新真實資料
        setInterval(() => {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    if (data.real_students > 0) {
                        location.reload(); // 有真實資料時重新載入頁面
                    }
                })
                .catch(error => console.log('統計更新失敗:', error));
        }, 30000); // 每30秒檢查一次
    </script>
</body>
</html>
"""

# templates_main.py - 第二部分：學生列表模板

# =========================================
# 學生列表模板 - 真實資料版本
# =========================================

STUDENTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>學生管理 - EMI 智能教學助理</title>
    <style>
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
            backdrop-filter: blur(10px);
        }
        .header h1 {
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* 等待真實資料狀態 */
        .waiting-for-data {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 40px;
            margin-bottom: 25px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            border: 2px dashed #ffc107;
        }
        .waiting-for-data h3 {
            color: #856404;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        .waiting-for-data p {
            color: #856404;
            margin-bottom: 10px;
        }
        
        /* 返回按鈕 */
        .back-btn {
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            padding: 12px 20px;
            border-radius: 25px;
            text-decoration: none;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        .back-btn:hover {
            background: white;
            transform: translateY(-2px);
            text-decoration: none;
            color: #333;
        }
        
        /* 搜尋和篩選 */
        .search-filters {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        .filter-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr auto;
            gap: 15px;
            align-items: center;
        }
        .filter-input {
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        .filter-input:focus {
            outline: none;
            border-color: #667eea;
        }
        .filter-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s ease;
        }
        .filter-btn:hover {
            background: #5a6fd8;
        }
        
        /* 學生卡片網格 */
        .students-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        .student-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .student-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }
        
        /* 學生資訊 */
        .student-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        .student-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(45deg, #667eea, #764ba2);
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
            font-size: 1.2em;
        }
        .student-status {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }
        .status-active { background: #d4edda; color: #155724; }
        .status-moderate { background: #fff3cd; color: #856404; }
        .status-inactive { background: #f8d7da; color: #721c24; }
        
        /* 統計數據 */
        .student-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 15px 0;
        }
        .stat-item {
            text-align: center;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .stat-number {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }
        .stat-label {
            font-size: 0.8em;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* 進度條 */
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        /* 最後活動時間 */
        .last-active {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e0e0e0;
            font-size: 0.9em;
            color: #7f8c8d;
        }
        
        /* 載入動畫 */
        .loading {
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
        }
        .spinner {
            display: inline-block;
            width: 30px;
            height: 30px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 15px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* 響應式設計 */
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .filter-row {
                grid-template-columns: 1fr;
                gap: 10px;
            }
            .students-grid {
                grid-template-columns: 1fr;
                gap: 15px;
            }
            .student-stats {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <a href="/" class="back-btn">← 返回首頁</a>
    
    <div class="container">
        <div class="header">
            <h1>👥 學生管理</h1>
            <p>查看和管理所有真實學生的學習狀況</p>
        </div>

        {% if not students or students|length == 0 %}
        <!-- 等待真實學生資料 -->
        <div class="waiting-for-data">
            <h3>⏳ 等待學生註冊</h3>
            <p>目前還沒有學生通過 LINE Bot 註冊</p>
            <p>當學生開始使用系統時，他們的資料將會在這裡顯示</p>
            <div class="spinner"></div>
            <button onclick="checkForStudents()" class="filter-btn" style="margin-top: 15px;">
                🔄 檢查新學生
            </button>
        </div>
        {% else %}
        
        <!-- 搜尋和篩選功能 -->
        <div class="search-filters">
            <div class="filter-row">
                <input type="text" id="searchInput" class="filter-input" placeholder="🔍 搜尋學生姓名或郵件..." onkeyup="filterStudents()">
                <select id="engagementFilter" class="filter-input" onchange="filterStudents()">
                    <option value="">所有參與度</option>
                    <option value="high">高參與 (80%+)</option>
                    <option value="medium">中參與 (50-79%)</option>
                    <option value="low">低參與 (<50%)</option>
                </select>
                <select id="statusFilter" class="filter-input" onchange="filterStudents()">
                    <option value="">所有狀態</option>
                    <option value="active">活躍</option>
                    <option value="moderate">一般</option>
                    <option value="inactive">不活躍</option>
                </select>
                <button onclick="resetFilters()" class="filter-btn">清除篩選</button>
            </div>
        </div>

        <!-- 學生卡片網格 -->
        <div class="students-grid" id="studentsGrid">
            {% for student in students %}
            <div class="student-card" onclick="location.href='/student/{{ student.id }}'" 
                 data-name="{{ student.name.lower() }}" 
                 data-email="{{ student.email.lower() if student.email else '' }}"
                 data-engagement="{{ student.engagement_score }}"
                 data-status="{{ student.status }}">
                
                <div class="student-header">
                    <div class="student-avatar">
                        {{ student.name[0].upper() }}
                    </div>
                    <div class="student-info">
                        <h3>{{ student.name }}</h3>
                        <span class="student-status status-{{ student.status }}">
                            {% if student.status == 'active' %}🟢 活躍
                            {% elif student.status == 'moderate' %}🟡 一般
                            {% else %}🔴 不活躍{% endif %}
                        </span>
                    </div>
                </div>

                <div class="student-stats">
                    <div class="stat-item">
                        <span class="stat-number">{{ student.total_messages }}</span>
                        <span class="stat-label">總訊息數</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">{{ "%.1f"|format(student.engagement_score) }}%</span>
                        <span class="stat-label">參與度</span>
                    </div>
                </div>

                <div class="progress-bar">
                    <div class="progress-fill" style="width: {{ student.engagement_score }}%"></div>
                </div>

                <div class="last-active">
                    <span>📅 最後活動</span>
                    <span>{{ student.last_active.strftime('%m/%d %H:%M') if student.last_active else '未知' }}</span>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>

    <script>
        function filterStudents() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const engagementFilter = document.getElementById('engagementFilter').value;
            const statusFilter = document.getElementById('statusFilter').value;
            const cards = document.querySelectorAll('.student-card');
            
            let visibleCount = 0;
            
            cards.forEach(card => {
                const name = card.dataset.name;
                const email = card.dataset.email;
                const engagement = parseFloat(card.dataset.engagement);
                const status = card.dataset.status;
                
                let show = true;
                
                // 搜尋篩選
                if (searchTerm && !name.includes(searchTerm) && !email.includes(searchTerm)) {
                    show = false;
                }
                
                // 參與度篩選
                if (engagementFilter) {
                    if (engagementFilter === 'high' && engagement < 80) show = false;
                    if (engagementFilter === 'medium' && (engagement < 50 || engagement >= 80)) show = false;
                    if (engagementFilter === 'low' && engagement >= 50) show = false;
                }
                
                // 狀態篩選
                if (statusFilter && status !== statusFilter) {
                    show = false;
                }
                
                card.style.display = show ? 'block' : 'none';
                if (show) visibleCount++;
            });
            
            // 顯示篩選結果
            updateFilterResults(visibleCount);
        }
        
        function resetFilters() {
            document.getElementById('searchInput').value = '';
            document.getElementById('engagementFilter').value = '';
            document.getElementById('statusFilter').value = '';
            filterStudents();
        }
        
        function updateFilterResults(count) {
            // 移除現有的結果提示
            const existingResult = document.querySelector('.filter-result');
            if (existingResult) {
                existingResult.remove();
            }
            
            // 添加新的結果提示
            if (count !== document.querySelectorAll('.student-card').length) {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'filter-result';
                resultDiv.style.cssText = `
                    background: #e3f2fd;
                    color: #1976d2;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    text-align: center;
                    border: 1px solid #bbdefb;
                `;
                resultDiv.innerHTML = `📊 篩選結果：顯示 ${count} 位學生`;
                
                const grid = document.getElementById('studentsGrid');
                grid.parentNode.insertBefore(resultDiv, grid);
            }
        }
        
        function checkForStudents() {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '🔄 檢查中...';
            btn.disabled = true;
            
            fetch('/api/students')
                .then(response => response.json())
                .then(data => {
                    if (data.students && data.students.length > 0) {
                        location.reload();
                    } else {
                        btn.textContent = '📭 暫無新學生';
                        setTimeout(() => {
                            btn.textContent = originalText;
                            btn.disabled = false;
                        }, 2000);
                    }
                })
                .catch(error => {
                    console.error('檢查失敗:', error);
                    btn.textContent = '❌ 檢查失敗';
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }, 2000);
                });
        }
        
        // 自動檢查新學生（每2分鐘）
        setInterval(() => {
            if (document.querySelector('.waiting-for-data')) {
                fetch('/api/students')
                    .then(response => response.json())
                    .then(data => {
                        if (data.students && data.students.length > 0) {
                            location.reload();
                        }
                    })
                    .catch(error => console.log('自動檢查失敗:', error));
            }
        }, 120000);
    </script>
</body>
</html>
"""

# templates_main.py - 第三部分：學生詳細資料模板

# =========================================
# 學生詳細資料模板 - 真實資料版本
# =========================================

STUDENT_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ student.name }} - 學生詳情 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
            margin: 0;
            padding: 20px;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        
        /* 返回按鈕 */
        .back-btn {
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            padding: 12px 20px;
            border-radius: 25px;
            text-decoration: none;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            z-index: 1000;
        }
        .back-btn:hover {
            background: white;
            transform: translateY(-2px);
            text-decoration: none;
            color: #333;
        }
        
        /* 學生資訊卡片 */
        .student-header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            display: flex;
            align-items: center;
            gap: 30px;
        }
        .student-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(45deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2em;
            font-weight: bold;
        }
        .student-info h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .student-meta {
            display: flex;
            gap: 20px;
            align-items: center;
            flex-wrap: wrap;
        }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
            text-transform: uppercase;
        }
        .status-active { background: #d4edda; color: #155724; }
        .status-moderate { background: #fff3cd; color: #856404; }
        .status-inactive { background: #f8d7da; color: #721c24; }
        
        /* 統計網格 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            text-align: center;
        }
        .stat-icon {
            font-size: 2.5em;
            margin-bottom: 15px;
        }
        .stat-number {
            font-size: 2.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #7f8c8d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .progress-ring {
            margin: 15px 0;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        /* 內容區塊 */
        .content-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        .content-section {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        .section-title {
            color: #2c3e50;
            font-size: 1.5em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* 對話記錄 */
        .conversation-item {
            display: flex;
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 10px;
            background: #f8f9fa;
        }
        .message-time {
            font-size: 0.8em;
            color: #95a5a6;
            margin-bottom: 5px;
        }
        .message-content {
            color: #2c3e50;
            line-height: 1.5;
        }
        .message-type {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.7em;
            font-weight: bold;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .type-question { background: #e3f2fd; color: #1976d2; }
        .type-answer { background: #e8f5e8; color: #2e7d32; }
        .type-feedback { background: #fff3e0; color: #f57c00; }
        
        /* 學習分析 */
        .analysis-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        .analysis-item:last-child {
            border-bottom: none;
        }
        .analysis-label {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        .analysis-value {
            color: #2c3e50;
            font-weight: bold;
        }
        
        /* 學習建議 */
        .recommendation {
            background: #e8f5e8;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 0 8px 8px 0;
        }
        .recommendation-title {
            font-weight: bold;
            color: #2e7d32;
            margin-bottom: 8px;
        }
        .recommendation-content {
            color: #1b5e20;
            line-height: 1.5;
        }
        
        /* 等待資料狀態 */
        .no-data {
            text-align: center;
            color: #7f8c8d;
            padding: 40px;
        }
        .no-data h3 {
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        /* 響應式設計 */
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .student-header {
                flex-direction: column;
                text-align: center;
                gap: 20px;
            }
            .student-meta {
                justify-content: center;
            }
            .stats-grid { grid-template-columns: 1fr; }
            .content-grid { 
                grid-template-columns: 1fr;
                gap: 20px;
            }
        }
    </style>
</head>
<body>
    <a href="/students" class="back-btn">← 返回學生列表</a>
    
    <div class="container">
        <!-- 學生資訊標題 -->
        <div class="student-header">
            <div class="student-avatar">
                {{ student.name[0].upper() }}
            </div>
            <div class="student-info">
                <h1>{{ student.name }}</h1>
                <div class="student-meta">
                    <span class="status-badge status-{{ student.status }}">
                        {% if student.status == 'active' %}🟢 活躍學生
                        {% elif student.status == 'moderate' %}🟡 一般活躍
                        {% else %}🔴 較不活躍{% endif %}
                    </span>
                    {% if student.email %}
                    <span style="color: #7f8c8d;">📧 {{ student.email }}</span>
                    {% endif %}
                    <span style="color: #7f8c8d;">📅 加入於 {{ student.created_at.strftime('%Y/%m/%d') if student.created_at else '未知' }}</span>
                </div>
            </div>
        </div>

        <!-- 統計數據 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">💬</div>
                <div class="stat-number">{{ student.total_messages }}</div>
                <div class="stat-label">總訊息數</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">❓</div>
                <div class="stat-number">{{ student.question_count or 0 }}</div>
                <div class="stat-label">提問次數</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-number">{{ "%.1f"|format(student.engagement_score) }}%</div>
                <div class="stat-label">參與度分數</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {{ student.engagement_score }}%"></div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📈</div>
                <div class="stat-number">{{ student.active_days or 0 }}</div>
                <div class="stat-label">活躍天數</div>
            </div>
        </div>

        <!-- 主要內容區域 -->
        <div class="content-grid">
            <!-- 對話記錄 -->
            <div class="content-section">
                <h2 class="section-title">
                    💬 最近對話記錄
                </h2>
                
                {% if conversations and conversations|length > 0 %}
                <div id="conversationList">
                    {% for conv in conversations[:10] %}
                    <div class="conversation-item">
                        <div style="flex: 1;">
                            <div class="message-time">{{ conv.timestamp.strftime('%m/%d %H:%M') }}</div>
                            <div class="message-type type-{{ conv.message_type.lower() }}">
                                {% if conv.message_type == 'question' %}❓ 問題
                                {% elif conv.message_type == 'answer' %}💭 回答
                                {% else %}📝 回饋{% endif %}
                            </div>
                            <div class="message-content">{{ conv.content }}</div>
                            {% if conv.ai_response %}
                            <div style="margin-top: 10px; padding: 10px; background: #e3f2fd; border-radius: 6px; font-size: 0.9em;">
                                <strong>🤖 AI 回覆：</strong>{{ conv.ai_response[:100] }}{% if conv.ai_response|length > 100 %}...{% endif %}
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                
                {% if conversations|length > 10 %}
                <div style="text-align: center; margin-top: 20px;">
                    <button onclick="loadMoreConversations()" class="filter-btn" style="background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer;">
                        載入更多對話
                    </button>
                </div>
                {% endif %}
                
                {% else %}
                <div class="no-data">
                    <h3>📝 尚無對話記錄</h3>
                    <p>當學生開始與 AI 助理互動時，對話記錄將會顯示在這裡</p>
                </div>
                {% endif %}
            </div>

            <!-- 學習分析 -->
            <div class="content-section">
                <h2 class="section-title">
                    📊 學習分析
                </h2>
                
                <div class="analysis-item">
                    <span class="analysis-label">平均每日訊息數</span>
                    <span class="analysis-value">{{ "%.1f"|format(student.daily_message_rate) if student.daily_message_rate else '0.0' }}</span>
                </div>
                <div class="analysis-item">
                    <span class="analysis-label">問題比例</span>
                    <span class="analysis-value">{{ "%.1f"|format(student.question_rate) if student.question_rate else '0.0' }}%</span>
                </div>
                <div class="analysis-item">
                    <span class="analysis-label">最後活動時間</span>
                    <span class="analysis-value">{{ student.last_active.strftime('%m/%d %H:%M') if student.last_active else '未知' }}</span>
                </div>
                <div class="analysis-item">
                    <span class="analysis-label">連續活躍天數</span>
                    <span class="analysis-value">{{ student.streak_days or 0 }} 天</span>
                </div>
                
                <!-- 學習建議 -->
                <h3 style="color: #2c3e50; margin: 25px 0 15px 0;">🎯 個人化建議</h3>
                
                {% if recommendations and recommendations|length > 0 %}
                    {% for rec in recommendations %}
                    <div class="recommendation">
                        <div class="recommendation-title">{{ rec.title }}</div>
                        <div class="recommendation-content">{{ rec.content }}</div>
                    </div>
                    {% endfor %}
                {% else %}
                    {% if student.engagement_score < 50 %}
                    <div class="recommendation">
                        <div class="recommendation-title">📈 提升參與度</div>
                        <div class="recommendation-content">建議主動聯絡此學生，了解學習困難並提供個別輔導</div>
                    </div>
                    {% elif student.engagement_score < 80 %}
                    <div class="recommendation">
                        <div class="recommendation-title">🎯 維持學習動力</div>
                        <div class="recommendation-content">學生表現良好，可提供更多挑戰性的學習內容</div>
                    </div>
                    {% else %}
                    <div class="recommendation">
                        <div class="recommendation-title">⭐ 優秀學生</div>
                        <div class="recommendation-content">表現優異！可考慮讓此學生協助其他同學學習</div>
                    </div>
                    {% endif %}
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        let conversationOffset = 10;
        
        function loadMoreConversations() {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '載入中...';
            btn.disabled = true;
            
            fetch(`/api/student/{{ student.id }}/conversations?offset=${conversationOffset}&limit=10`)
                .then(response => response.json())
                .then(data => {
                    if (data.conversations && data.conversations.length > 0) {
                        const conversationList = document.getElementById('conversationList');
                        data.conversations.forEach(conv => {
                            const convDiv = document.createElement('div');
                            convDiv.className = 'conversation-item';
                            convDiv.innerHTML = `
                                <div style="flex: 1;">
                                    <div class="message-time">${new Date(conv.timestamp).toLocaleDateString('zh-TW', {month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'})}</div>
                                    <div class="message-type type-${conv.message_type.toLowerCase()}">
                                        ${conv.message_type === 'question' ? '❓ 問題' : conv.message_type === 'answer' ? '💭 回答' : '📝 回饋'}
                                    </div>
                                    <div class="message-content">${conv.content}</div>
                                    ${conv.ai_response ? `<div style="margin-top: 10px; padding: 10px; background: #e3f2fd; border-radius: 6px; font-size: 0.9em;"><strong>🤖 AI 回覆：</strong>${conv.ai_response.substring(0, 100)}${conv.ai_response.length > 100 ? '...' : ''}</div>` : ''}
                                </div>
                            `;
                            conversationList.appendChild(convDiv);
                        });
                        conversationOffset += 10;
                        
                        if (data.conversations.length < 10) {
                            btn.style.display = 'none';
                        } else {
                            btn.textContent = originalText;
                            btn.disabled = false;
                        }
                    } else {
                        btn.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('載入失敗:', error);
                    btn.textContent = '載入失敗';
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }, 2000);
                });
        }
        
        // 定期更新學生統計
        setInterval(() => {
            fetch(`/api/student/{{ student.id }}/stats`)
                .then(response => response.json())

# templates_main.py - 第四部分：完成學生詳細模板並添加模板函數

# 完成第三部分的 JavaScript 和 HTML 結束標籤
STUDENT_DETAIL_TEMPLATE += """
                .then(data => {
                    if (data.success) {
                        // 更新統計數字
                        const stats = data.stats;
                        const statNumbers = document.querySelectorAll('.stat-number');
                        
                        if (statNumbers.length >= 4) {
                            statNumbers[0].textContent = stats.message_count;
                            statNumbers[1].textContent = stats.question_count;
                            statNumbers[2].textContent = stats.participation_rate + '%';
                            statNumbers[3].textContent = stats.active_days;
                        }
                        
                        // 更新進度條
                        const progressBars = document.querySelectorAll('.progress-fill');
                        if (progressBars.length >= 1) {
                            progressBars[0].style.width = stats.participation_rate + '%';
                        }
                        
                        console.log('📊 學生統計已更新');
                    }
                })
                .catch(error => {
                    console.error('統計更新失敗:', error);
                });
        }, 60000); // 每分鐘更新一次
    </script>
</body>
</html>
"""

# =========================================
# 模板函數和工具
# =========================================

def get_template(template_name):
    """
    取得指定模板
    
    Args:
        template_name (str): 模板名稱，支援以下選項：
            - 'index.html': 首頁模板
            - 'students.html': 學生列表模板  
            - 'student_detail.html': 學生詳細資料模板
    
    Returns:
        str: 對應的 HTML 模板字串，如果找不到則返回空字串
    """
    templates = {
        'index.html': INDEX_TEMPLATE,
        'students.html': STUDENTS_TEMPLATE,
        'student_detail.html': STUDENT_DETAIL_TEMPLATE,
    }
    
    template = templates.get(template_name, '')
    if not template:
        print(f"⚠️  警告：找不到模板 '{template_name}'")
    
    return template

def validate_template(template_name):
    """
    驗證模板是否存在且有效
    
    Args:
        template_name (str): 模板名稱
        
    Returns:
        bool: True 如果模板存在且有效，否則 False
    """
    template = get_template(template_name)
    return bool(template and len(template.strip()) > 0)

def get_available_templates():
    """
    取得所有可用的模板列表
    
    Returns:
        list: 可用模板名稱列表
    """
    return ['index.html', 'students.html', 'student_detail.html']

def template_info():
    """
    取得模板系統資訊
    
    Returns:
        dict: 包含模板統計資訊的字典
    """
    templates = get_available_templates()
    valid_templates = [t for t in templates if validate_template(t)]
    
    return {
        'total_templates': len(templates),
        'valid_templates': len(valid_templates),
        'available_templates': templates,
        'template_sizes': {
            name: len(get_template(name)) for name in templates
        }
    }

def debug_templates():
    """
    除錯函數：檢查所有模板的狀態
    """
    info = template_info()
    print("=== Templates Main 模板系統資訊 ===")
    print(f"總模板數量: {info['total_templates']}")
    print(f"有效模板數量: {info['valid_templates']}")
    print(f"可用模板: {', '.join(info['available_templates'])}")
    
    print("\n=== 各模板大小 ===")
    for name, size in info['template_sizes'].items():
        status = "✅" if size > 0 else "❌"
        print(f"{name}: {size:,} 字元 {status}")
    
    # 檢查關鍵 CSS 和 JavaScript
    print("\n=== 模板內容檢查 ===")
    for template_name in info['available_templates']:
        template = get_template(template_name)
        if template:
            has_css = '<style>' in template and '</style>' in template
            has_js = '<script>' in template and '</script>' in template
            has_responsive = '@media' in template
            print(f"{template_name}:")
            print(f"  CSS: {'✅' if has_css else '❌'}")
            print(f"  JavaScript: {'✅' if has_js else '❌'}")
            print(f"  響應式設計: {'✅' if has_responsive else '❌'}")

# =========================================
# 模板常數和設定
# =========================================

# 模板版本資訊
TEMPLATE_VERSION = "2.0.0"
TEMPLATE_DESCRIPTION = "EMI 智能教學助理 - 真實資料專用模板系統"

# 支援的模板類型
SUPPORTED_TEMPLATES = {
    'index.html': {
        'name': '首頁',
        'description': '系統首頁，顯示整體統計和最近活動',
        'features': ['真實資料檢測', '統計儀表板', '最近活動', '快速導航']
    },
    'students.html': {
        'name': '學生管理',
        'description': '學生列表頁面，支援搜尋和篩選功能',
        'features': ['學生卡片顯示', '即時搜尋', '參與度篩選', '狀態管理']
    },
    'student_detail.html': {
        'name': '學生詳情',
        'description': '個別學生的詳細資料和學習分析',
        'features': ['詳細統計', '對話記錄', '學習分析', '個人化建議']
    }
}

# CSS 主題設定
THEME_COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2', 
    'success': '#4caf50',
    'warning': '#ffc107',
    'danger': '#f44336',
    'info': '#2196f3',
    'light': '#f8f9fa',
    'dark': '#2c3e50'
}

# JavaScript 功能設定
JS_FEATURES = {
    'auto_refresh': True,          # 自動刷新資料
    'real_time_updates': True,     # 即時更新
    'responsive_design': True,     # 響應式設計
    'search_filter': True,         # 搜尋篩選
    'lazy_loading': True,          # 懶加載
    'error_handling': True         # 錯誤處理
}

# =========================================
# 匯出所有公開介面
# =========================================

# 主要模板
__all__ = [
    # 模板常數
    'INDEX_TEMPLATE',
    'STUDENTS_TEMPLATE', 
    'STUDENT_DETAIL_TEMPLATE',
    
    # 工具函數
    'get_template',
    'validate_template',
    'get_available_templates',
    'template_info',
    'debug_templates',
    
    # 系統資訊
    'TEMPLATE_VERSION',
    'TEMPLATE_DESCRIPTION',
    'SUPPORTED_TEMPLATES',
    'THEME_COLORS',
    'JS_FEATURES'
]

# =========================================
# 向後相容性支援
# =========================================

def get_main_template(template_name):
    """
    向後相容函數：為了支援舊版本的模板工具
    
    Args:
        template_name (str): 模板名稱
        
    Returns:
        str: 模板內容
    """
    return get_template(template_name)

def check_template_integrity():
    """
    檢查模板完整性
    
    Returns:
        dict: 完整性檢查結果
    """
    results = {
        'status': 'ok',
        'errors': [],
        'warnings': [],
        'summary': {}
    }
    
    # 檢查每個模板
    for template_name in get_available_templates():
        template = get_template(template_name)
        template_results = {
            'exists': bool(template),
            'size': len(template) if template else 0,
            'has_doctype': '<!DOCTYPE html>' in template if template else False,
            'has_closing_tags': '</html>' in template if template else False,
            'has_meta_charset': 'charset="UTF-8"' in template if template else False,
            'has_viewport': 'viewport' in template if template else False,
            'has_styles': '<style>' in template and '</style>' in template if template else False,
            'has_scripts': '<script>' in template and '</script>' in template if template else False
        }
        
        # 檢查錯誤
        if not template_results['exists']:
            results['errors'].append(f"模板 {template_name} 不存在或為空")
        elif template_results['size'] < 1000:
            results['warnings'].append(f"模板 {template_name} 內容過短 ({template_results['size']} 字元)")
        
        if template and not template_results['has_doctype']:
            results['warnings'].append(f"模板 {template_name} 缺少 DOCTYPE")
        
        if template and not template_results['has_closing_tags']:
            results['errors'].append(f"模板 {template_name} 缺少結束標籤")
        
        results['summary'][template_name] = template_results
    
    # 設定整體狀態
    if results['errors']:
        results['status'] = 'error'
    elif results['warnings']:
        results['status'] = 'warning'
    
    return results

def generate_template_report():
    """
    生成模板系統報告
    
    Returns:
        str: 格式化的報告內容
    """
    info = template_info()
    integrity = check_template_integrity()
    
    report = []
    report.append("=" * 50)
    report.append("EMI 智能教學助理 - 模板系統報告")
    report.append("=" * 50)
    report.append(f"版本: {TEMPLATE_VERSION}")
    report.append(f"描述: {TEMPLATE_DESCRIPTION}")
    report.append("")
    
    # 基本統計
    report.append("📊 基本統計:")
    report.append(f"  總模板數: {info['total_templates']}")
    report.append(f"  有效模板數: {info['valid_templates']}")
    report.append(f"  完整性狀態: {integrity['status'].upper()}")
    report.append("")
    
    # 模板詳情
    report.append("📋 模板詳情:")
    for name in info['available_templates']:
        template_info_detail = SUPPORTED_TEMPLATES.get(name, {})
        size = info['template_sizes'].get(name, 0)
        status = "✅" if size > 0 else "❌"
        
        report.append(f"  {name} {status}")
        report.append(f"    名稱: {template_info_detail.get('name', '未知')}")
        report.append(f"    大小: {size:,} 字元")
        report.append(f"    功能: {', '.join(template_info_detail.get('features', []))}")
        report.append("")
    
    # 錯誤和警告
    if integrity['errors']:
        report.append("❌ 錯誤:")
        for error in integrity['errors']:
            report.append(f"  - {error}")
        report.append("")
    
    if integrity['warnings']:
        report.append("⚠️  警告:")
        for warning in integrity['warnings']:
            report.append(f"  - {warning}")
        report.append("")
    
    # 功能支援
    report.append("🔧 JavaScript 功能:")
    for feature, enabled in JS_FEATURES.items():
        status = "✅" if enabled else "❌"
        report.append(f"  {feature}: {status}")
    report.append("")
    
    # 主題色彩
    report.append("🎨 主題配色:")
    for color_name, color_value in THEME_COLORS.items():
        report.append(f"  {color_name}: {color_value}")
    
    report.append("=" * 50)
    
    return "\n".join(report)

# =========================================
# 測試和開發工具
# =========================================

def test_all_templates():
    """
    測試所有模板的基本功能
    
    Returns:
        dict: 測試結果
    """
    results = {
        'passed': 0,
        'failed': 0,
        'details': {}
    }
    
    test_data = {
        'student': {
            'id': 1,
            'name': '測試學生',
            'email': 'test@example.com',
            'total_messages': 50,
            'engagement_score': 85.5,
            'status': 'active',
            'created_at': None,
            'last_active': None,
            'question_count': 25,
            'active_days': 15,
            'daily_message_rate': 3.3,
            'question_rate': 50.0,
            'streak_days': 7
        },
        'stats': {
            'real_students': 1,
            'total_messages': 100,
            'active_conversations': 5,
            'avg_engagement': 78.5
        },
        'students': [
            {
                'id': 1,
                'name': '測試學生1',
                'email': 'test1@example.com',
                'total_messages': 30,
                'engagement_score': 75.0,
                'status': 'active'
            }
        ],
        'conversations': [],
        'recent_messages': [],
        'recommendations': []
    }
    
    for template_name in get_available_templates():
        try:
            template = get_template(template_name)
            if template:
                # 簡單的模板渲染測試（不實際渲染，只檢查基本結構）
                basic_checks = [
                    'DOCTYPE' in template,
                    '<html' in template,
                    '</html>' in template,
                    '<head>' in template,
                    '</head>' in template,
                    '<body>' in template,
                    '</body>' in template
                ]
                
                if all(basic_checks):
                    results['passed'] += 1
                    results['details'][template_name] = {'status': 'passed', 'message': '基本結構檢查通過'}
                else:
                    results['failed'] += 1
                    results['details'][template_name] = {'status': 'failed', 'message': '基本結構檢查失敗'}
            else:
                results['failed'] += 1
                results['details'][template_name] = {'status': 'failed', 'message': '模板為空或不存在'}
                
        except Exception as e:
            results['failed'] += 1
            results['details'][template_name] = {'status': 'error', 'message': f'測試異常: {str(e)}'}
    
    return results

if __name__ == "__main__":
    # 當直接執行此模組時，進行自檢
    print("🔍 執行模板系統自檢...")
    print(generate_template_report())
    
    print("\n🧪 執行模板測試...")
    test_results = test_all_templates()
    print(f"測試結果: {test_results['passed']} 通過, {test_results['failed']} 失敗")
    
    for template_name, result in test_results['details'].items():
        status_emoji = "✅" if result['status'] == 'passed' else "❌"
        print(f"  {template_name}: {status_emoji} {result['message']}")

# 模組初始化完成提示
print(f"✅ templates_main.py 模組已載入 (版本 {TEMPLATE_VERSION})")
