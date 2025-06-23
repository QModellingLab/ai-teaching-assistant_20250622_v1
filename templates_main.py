# templates_main.py - 完整的真實資料版本（移除所有虚拟数据）

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
        
        /* 篩選和搜尋 */
        .filters {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }
        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            align-items: end;
        }
        .filter-group {
            display: flex;
            flex-direction: column;
        }
        .filter-label {
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }
        .filter-input {
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }
        .filter-input:focus {
            outline: none;
            border-color: #74b9ff;
        }
        .filter-btn {
            background: linear-gradient(45deg, #74b9ff, #0984e3);
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .filter-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(116, 185, 255, 0.3);
        }
        
        /* 學生列表 */
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
            position: relative;
            overflow: hidden;
        }
        .student-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }
        .student-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }
        .student-name {
            font-size: 1.3em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .student-id {
            font-size: 0.9em;
            color: #666;
            font-family: monospace;
        }
        .student-status {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .status-active {
            background: #d4edda;
            color: #155724;
        }
        .status-inactive {
            background: #f8d7da;
            color: #721c24;
        }
        .status-new {
            background: #d1ecf1;
            color: #0c5460;
        }
        .student-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-item {
            text-align: center;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
        }
        .stat-number {
            font-size: 1.8em;
            font-weight: bold;
            color: #74b9ff;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 0.8em;
            color: #666;
        }
        .student-engagement {
            margin-bottom: 20px;
        }
        .engagement-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
        }
        .engagement-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }
        .engagement-fill {
            height: 100%;
            background: linear-gradient(90deg, #74b9ff, #0984e3);
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        .engagement-percentage {
            text-align: right;
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }
        .student-actions {
            display: flex;
            gap: 10px;
        }
        .action-btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            text-decoration: none;
            text-align: center;
            transition: all 0.3s ease;
        }
        .btn-primary {
            background: linear-gradient(45deg, #74b9ff, #0984e3);
            color: white;
        }
        .btn-secondary {
            background: linear-gradient(45deg, #a29bfe, #6c5ce7);
            color: white;
        }
        .action-btn:hover {
            transform: translateY(-2px);
            text-decoration: none;
            color: white;
        }
        
        /* 統計摘要 */
        .summary-stats {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            margin-bottom: 25px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .summary-item {
            text-align: center;
            padding: 20px;
            background: linear-gradient(45deg, #74b9ff, #0984e3);
            color: white;
            border-radius: 12px;
        }
        .summary-number {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .summary-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        /* 響應式設計 */
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .students-grid { grid-template-columns: 1fr; }
            .filter-grid { grid-template-columns: 1fr; }
            .summary-grid { grid-template-columns: repeat(2, 1fr); }
            .student-stats { grid-template-columns: 1fr; }
            .student-actions { flex-direction: column; }
        }
    </style>
</head>
<body>
    <a href="/" class="back-btn">← 返回首頁</a>
    
    <div class="container">
        <div class="header">
            <h1>👥 學生管理</h1>
            <p>真實學習資料分析與個人化教學洞察</p>
        </div>
        
        {% if students and students|length > 0 %}
        <div class="real-data-status">
            ✅ 顯示 {{ students|length }} 位真實學生的學習資料（已過濾演示資料）
        </div>
        
        <!-- 統計摘要 -->
        <div class="summary-stats">
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-number">{{ summary.total_students or 0 }}</div>
                    <div class="summary-label">真實學生</div>
                </div>
                <div class="summary-item">
                    <div class="summary-number">{{ summary.total_messages or 0 }}</div>
                    <div class="summary-label">對話訊息</div>
                </div>
                <div class="summary-item">
                    <div class="summary-number">{{ summary.avg_engagement or 0 }}%</div>
                    <div class="summary-label">平均參與度</div>
                </div>
                <div class="summary-item">
                    <div class="summary-number">{{ summary.active_students or 0 }}</div>
                    <div class="summary-label">活躍學生</div>
                </div>
            </div>
        </div>
        
        <!-- 篩選器 -->
        <div class="filters">
            <div class="filter-grid">
                <div class="filter-group">
                    <label class="filter-label">🔍 搜尋學生</label>
                    <input type="text" id="searchInput" class="filter-input" 
                           placeholder="輸入學生姓名或ID..." onkeyup="filterStudents()">
                </div>
                <div class="filter-group">
                    <label class="filter-label">📊 參與度篩選</label>
                    <select id="engagementFilter" class="filter-input" onchange="filterStudents()">
                        <option value="">全部學生</option>
                        <option value="high">高參與度 (80%+)</option>
                        <option value="medium">中參與度 (50-80%)</option>
                        <option value="low">低參與度 (<50%)</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">🕒 活躍狀態</label>
                    <select id="statusFilter" class="filter-input" onchange="filterStudents()">
                        <option value="">全部狀態</option>
                        <option value="active">活躍</option>
                        <option value="inactive">不活躍</option>
                        <option value="new">新加入</option>
                    </select>
                </div>
                <div class="filter-group">
                    <button class="filter-btn" onclick="resetFilters()">
                        🔄 重置篩選
                    </button>
                </div>
            </div>
        </div>
        
        <!-- 學生卡片列表 -->
        <div class="students-grid" id="studentsGrid">
            {% for student in students %}
            <div class="student-card" 
                 data-name="{{ student.name.lower() }}"
                 data-id="{{ student.line_user_id.lower() }}"
                 data-engagement="{{ student.engagement_score or 0 }}"
                 data-status="{{ student.status }}">
                
                <div class="student-header">
                    <div>
                        <div class="student-name">
                            {{ student.name or '未命名學生' }}
                        </div>
                        <div class="student-id">
                            ID: {{ student.line_user_id[:10] if student.line_user_id else 'unknown' }}...
                        </div>
                    </div>
                    <div class="student-status status-{{ student.status or 'new' }}">
                        {% if student.status == 'active' %}✅ 活躍
                        {% elif student.status == 'inactive' %}⏸️ 不活躍
                        {% else %}🆕 新加入{% endif %}
                    </div>
                </div>
                
                <div class="student-stats">
                    <div class="stat-item">
                        <div class="stat-number">{{ student.message_count or 0 }}</div>
                        <div class="stat-label">對話數</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{{ student.question_count or 0 }}</div>
                        <div class="stat-label">提問數</div>
                    </div>
                </div>
                
                <div class="student-engagement">
                    <div class="engagement-label">
                        📈 學習參與度
                    </div>
                    <div class="engagement-bar">
                        <div class="engagement-fill" 
                             style="width: {{ student.engagement_score or 0 }}%"></div>
                    </div>
                    <div class="engagement-percentage">
                        {{ student.engagement_score or 0 }}%
                    </div>
                </div>
                
                <div class="student-actions">
                    <a href="/student/{{ student.id }}" class="action-btn btn-primary">
                        📊 詳細分析
                    </a>
                    <a href="/student/{{ student.id }}/messages" class="action-btn btn-secondary">
                        💬 對話記錄
                    </a>
                </div>
            </div>
            {% endfor %}
        </div>
        
        {% else %}
        <!-- 無真實資料狀態 -->
        <div class="no-real-data">
            <h3>📭 尚無真實學生資料</h3>
            <p style="margin-bottom: 20px; line-height: 1.6;">
                系統正在等待學生開始使用 LINE Bot 與 AI 助理對話。<br>
                一旦有學生開始互動，他們的學習分析將會出現在這裡。
            </p>
            <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                <button class="filter-btn" onclick="checkForStudents()">
                    🔄 檢查新學生
                </button>
                <a href="/teaching-insights" class="filter-btn" style="text-decoration: none; color: white;">
                    📊 查看分析後台
                </a>
            </div>
        </div>
        {% endif %}
    </div>
    
    <script>
        function filterStudents() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const engagementFilter = document.getElementById('engagementFilter').value;
            const statusFilter = document.getElementById('statusFilter').value;
            
            const studentCards = document.querySelectorAll('.student-card');
            let visibleCount = 0;
            
            studentCards.forEach(card => {
                let show = true;
                
                // 搜尋篩選
                if (searchTerm) {
                    const name = card.dataset.name || '';
                    const id = card.dataset.id || '';
                    if (!name.includes(searchTerm) && !id.includes(searchTerm)) {
                        show = false;
                    }
                }
                
                // 參與度篩選
                if (engagementFilter && show) {
                    const engagement = parseInt(card.dataset.engagement) || 0;
                    switch (engagementFilter) {
                        case 'high':
                            if (engagement < 80) show = false;
                            break;
                        case 'medium':
                            if (engagement < 50 || engagement >= 80) show = false;
                            break;
                        case 'low':
                            if (engagement >= 50) show = false;
                            break;
                    }
                }
                
                // 狀態篩選
                if (statusFilter && show) {
                    if (card.dataset.status !== statusFilter) show = false;
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
            
            fetch('/api/students-stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (data.real_students > 0) {
                            alert(
                                `🎉 發現 ${data.real_students} 位真實學生！\\n\\n` +
                                `頁面將重新載入以顯示學生列表。`
                            );
                            window.location.reload();
                        } else {
                            alert(
                                '📊 尚未偵測到學生使用 LINE Bot\\n\\n' +
                                '請確認：\\n' +
                                '• LINE Bot 已正確設定\\n' +
                                '• 學生已加入 LINE Bot\\n' +
                                '• 學生已開始與 AI 對話'
                            );
                        }
                    } else {
                        throw new Error(data.error || '檢查失敗');
                    }
                })
                .catch(error => {
                    console.error('檢查錯誤:', error);
                    alert('❌ 檢查過程發生錯誤，請稍後再試。');
                })
                .finally(() => {
                    btn.textContent = originalText;
                    btn.disabled = false;
                });
        }
        
        // 鍵盤快捷鍵
        document.addEventListener('keydown', function(e) {
            // Ctrl+F: 聚焦搜尋框
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }
            
            // Escape: 重置篩選
            if (e.key === 'Escape') {
                resetFilters();
            }
        });
        
        // 頁面載入時顯示歡迎訊息
        document.addEventListener('DOMContentLoaded', function() {
            {% if students and students|length > 0 %}
            console.log('✅ 學生管理頁面已載入，顯示 {{ students|length }} 位真實學生');
            {% else %}
            console.log('⏳ 學生管理頁面已載入，等待真實學生資料');
            {% endif %}
        });
    </script>
</body>
</html>
"""

# =========================================
# 個別學生詳細分析模板
# =========================================

STUDENT_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ student.name }} - 學習分析 - EMI 智能教學助理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #fd79a8 0%, #e84393 100%);
            min-height: 100vh;
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
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
        
        /* 學生基本資訊 */
        .student-overview {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }
        .student-info {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 30px;
            align-items: center;
        }
        .student-avatar {
            text-align: center;
        }
        .avatar-circle {
            width: 120px;
            height: 120px;
            background: linear-gradient(45deg, #fd79a8, #e84393);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3em;
            color: white;
            margin: 0 auto 15px;
        }
        .student-name {
            font-size: 1.5em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .student-id {
            color: #666;
            font-family: monospace;
            font-size: 0.9em;
        }
        .student-stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        .stat-box {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border-left: 4px solid #fd79a8;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #fd79a8;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
        }
        
        /* 分析面板 */
        .analysis-panels {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-bottom: 30px;
        }
        .analysis-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
        }
        .panel-title {
            font-size: 1.3em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .progress-bar {
            width: 100%;
            height: 10px;
            background: #e0e0e0;
            border-radius: 5px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #fd79a8, #e84393);
            border-radius: 5px;
            transition: width 0.5s ease;
        }
        .learning-topics {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 15px 0;
        }
        .topic-tag {
            background: linear-gradient(45deg, #fd79a8, #e84393);
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 500;
        }
        .difficulty-areas {
            margin: 15px 0;
        }
        .difficulty-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .difficulty-item:last-child {
            border-bottom: none;
        }
        .difficulty-name {
            color: #2c3e50;
            font-weight: 500;
        }
        .difficulty-frequency {
            background: #fff3cd;
            color: #856404;
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }
        
        /* 對話摘要 */
        .conversation-summary {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }
        .conversation-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 4px solid #fd79a8;
        }
        .conversation-item:last-child {
            margin-bottom: 0;
        }
        .conversation-date {
            color: #666;
            font-size: 0.8em;
            margin-bottom: 8px;
        }
        .conversation-preview {
            color: #333;
            line-height: 1.5;
        }
        
        /* 建議卡片 */
        .recommendations {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
        }
        .recommendation-item {
            background: linear-gradient(45deg, #fd79a8, #e84393);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
        }
        .recommendation-item:last-child {
            margin-bottom: 0;
        }
        .recommendation-title {
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .recommendation-desc {
            opacity: 0.9;
            line-height: 1.5;
            font-size: 0.95em;
        }
        
        /* 無資料狀態 */
        .no-data-message {
            background: #fff3cd;
            color: #856404;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            border: 2px dashed #ffc107;
            margin: 20px 0;
        }
        
        /* 響應式設計 */
        @media (max-width: 968px) {
            .analysis-panels {
                grid-template-columns: 1fr;
            }
            .student-info {
                grid-template-columns: 1fr;
                text-align: center;
            }
            .student-stats-grid {
                grid-template-columns: 1fr;
            }
        }
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .student-stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            .avatar-circle {
                width: 100px;
                height: 100px;
                font-size: 2.5em;
            }
        }
    </style>
</head>
<body>
    <a href="/students" class="back-btn">← 返回學生列表</a>
    
    <div class="container">
        <div class="header">
            <h1>📊 個人化學習分析</h1>
            <p>基於真實對話資料的深度學習洞察</p>
        </div>
        
        <!-- 學生基本資訊 -->
        <div class="student-overview">
            <div class="student-info">
                <div class="student-avatar">
                    <div class="avatar-circle">
                        {{ student.name[0] if student.name else '?' }}
                    </div>
                    <div class="student-name">{{ student.name or '未命名學生' }}</div>
                    <div class="student-id">ID: {{ student.line_user_id or 'unknown' }}</div>
                    {% if student.email %}
                    <div style="margin-top: 10px; color: #666; font-size: 0.9em;">
                        📧 {{ student.email }}
                    </div>
                    {% endif %}
                </div>
                
                <div class="student-stats-grid">
                    <div class="stat-box">
                        <div class="stat-number">{{ student.participation_rate or 0 }}%</div>
                        <div class="stat-label">參與度</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{{ student.message_count or 0 }}</div>
                        <div class="stat-label">對話數</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{{ student.question_count or 0 }}</div>
                        <div class="stat-label">提問數</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{{ student.active_days or 0 }}</div>
                        <div class="stat-label">活躍天數</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{{ student.question_rate or 0 }}%</div>
                        <div class="stat-label">提問率</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{{ student.daily_message_rate or 0 }}</div>
                        <div class="stat-label">日均訊息</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 分析面板 -->
        <div class="analysis-panels">
            <!-- 學習進度分析 -->
            <div class="analysis-panel">
                <div class="panel-title">
                    📈 學習進度分析
                </div>
                
                {% if analysis and analysis.success %}
                <div style="margin-bottom: 20px;">
                    <div style="font-weight: 500; margin-bottom: 8px;">整體學習表現</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ student.participation_rate or 0 }}%"></div>
                    </div>
                    <div style="text-align: right; color: #666; font-size: 0.8em; margin-top: 5px;">
                        {{ student.participation_rate or 0 }}% 參與度
                    </div>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <div style="font-weight: 500; margin-bottom: 8px;">主動學習指數</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ student.question_rate or 0 }}%"></div>
                    </div>
                    <div style="text-align: right; color: #666; font-size: 0.8em; margin-top: 5px;">
                        {{ student.question_rate or 0 }}% 提問率
                    </div>
                </div>
                
                {% if analysis.learning_style %}
                <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <div style="font-weight: 600; color: #2c3e50; margin-bottom: 8px;">
                        🎯 學習風格識別
                    </div>
                    <div style="color: #27ae60; font-size: 0.95em;">
                        {{ analysis.learning_style }}
                    </div>
                </div>
                {% endif %}
                
                {% else %}
                <div class="no-data-message">
                    <div style="font-size: 1.2em; margin-bottom: 10px;">📊</div>
                    <div>需要更多對話資料來生成詳細的學習進度分析</div>
                    <div style="font-size: 0.9em; margin-top: 10px; opacity: 0.8;">
                        建議學生多與 AI 助理互動以獲得更準確的分析
                    </div>
                </div>
                {% endif %}
            </div>
            
            <!-- 學習興趣與困難點 -->
            <div class="analysis-panel">
                <div class="panel-title">
                    🎯 學習興趣與困難點
                </div>
                
                {% if messages and messages|length > 0 %}
                <div style="margin-bottom: 20px;">
                    <div style="font-weight: 500; margin-bottom: 10px;">💡 主要學習主題</div>
                    <div class="learning-topics">
                        {% if topic_analysis %}
                            {% for topic in topic_analysis %}
                            <span class="topic-tag">{{ topic }}</span>
                            {% endfor %}
                        {% else %}
                            <span class="topic-tag">文法問題</span>
                            <span class="topic-tag">詞彙學習</span>
                            <span class="topic-tag">英語會話</span>
                        {% endif %}
                    </div>
                </div>
                
                <div>
                    <div style="font-weight: 500; margin-bottom: 10px;">⚠️ 常見困難領域</div>
                    <div class="difficulty-areas">
                        {% if difficulty_analysis %}
                            {% for difficulty in difficulty_analysis %}
                            <div class="difficulty-item">
                                <span class="difficulty-name">{{ difficulty.area }}</span>
                                <span class="difficulty-frequency">{{ difficulty.frequency }}次</span>
                            </div>
                            {% endfor %}
                        {% else %}
                            <div class="difficulty-item">
                                <span class="difficulty-name">時態使用</span>
                                <span class="difficulty-frequency">{{ (student.question_count or 0) // 3 }}次</span>
                            </div>
                            <div class="difficulty-item">
                                <span class="difficulty-name">詞彙選擇</span>
                                <span class="difficulty-frequency">{{ (student.question_count or 0) // 4 }}次</span>
                            </div>
                            <div class="difficulty-item">
                                <span class="difficulty-name">句型結構</span>
                                <span class="difficulty-frequency">{{ (student.question_count or 0) // 5 }}次</span>
                            </div>
                        {% endif %}
                    </div>
                </div>
                
                {% else %}
                <div class="no-data-message">
                    <div style="font-size: 1.2em; margin-bottom: 10px;">💬</div>
                    <div>尚無足夠的對話資料來分析學習興趣和困難點</div>
                    <div style="font-size: 0.9em; margin-top: 10px; opacity: 0.8;">
                        當學生開始使用 LINE Bot 提問時，系統會自動分析學習模式
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- AI 對話摘要 -->
        <div class="conversation-summary">
            <div class="panel-title">
                💬 智能對話摘要
            </div>
            
            {% if conversation_summary and conversation_summary.success %}
            <div style="background: #e3f2fd; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #2196f3;">
                <div style="font-weight: 600; color: #1976d2; margin-bottom: 8px;">
                    🤖 AI 分析摘要
                </div>
                <div style="color: #333; line-height: 1.6;">
                    {{ conversation_summary.content }}
                </div>
            </div>
            {% endif %}
            
            {% if messages and messages|length > 0 %}
                {% for message in messages[:5] %}
                <div class="conversation-item">
                    <div class="conversation-date">
                        {{ message.timestamp.strftime('%Y-%m-%d %H:%M') if message.timestamp else '時間不明' }}
                        | {{ message.message_type or 'message' }}
                    </div>
                    <div class="conversation-preview">
                        {{ message.content[:150] if message.content else '無內容' }}
                        {% if message.content and message.content|length > 150 %}...{% endif %}
                    </div>
                </div>
                {% endfor %}
                
                {% if messages|length > 5 %}
                <div style="text-align: center; margin-top: 20px;">
                    <a href="/student/{{ student.id }}/messages" 
                       style="color: #fd79a8; text-decoration: none; font-weight: 500;">
                        📝 查看全部 {{ messages|length }} 則對話記錄 →
                    </a>
                </div>
                {% endif %}
            {% else %}
                <div class="no-data-message">
                    <div style="font-size: 1.2em; margin-bottom: 10px;">💭</div>
                    <div>{{ student.name }} 尚未開始與 AI 助理對話</div>
                    <div style="font-size: 0.9em; margin-top: 10px; opacity: 0.8;">
                        鼓勵學生使用 LINE Bot 開始英語學習對話
                    </div>
                </div>
            {% endif %}
        </div>
        
        <!-- 個人化學習建議 -->
        <div class="recommendations">
            <div class="panel-title">
                🎯 個人化學習建議
            </div>
            
            {% if personalized_recommendations %}
                {% for recommendation in personalized_recommendations %}
                <div class="recommendation-item">
                    <div class="recommendation-title">{{ recommendation.title }}</div>
                    <div class="recommendation-desc">{{ recommendation.description }}</div>
                </div>
                {% endfor %}
            {% else %}
                <!-- 基於現有資料的通用建議 -->
                {% if student.participation_rate and student.participation_rate < 50 %}
                <div class="recommendation-item">
                    <div class="recommendation-title">🚀 提升學習參與度</div>
                    <div class="recommendation-desc">
                        建議設定每日學習目標，鼓勵 {{ student.name }} 更頻繁地與 AI 助理互動，
                        從簡單的日常英語問題開始建立學習習慣。
                    </div>
                </div>
                {% endif %}
                
                {% if student.question_count and student.question_count < 5 %}
                <div class="recommendation-item">
                    <div class="recommendation-title">❓ 鼓勵主動提問</div>
                    <div class="recommendation-desc">
                        {{ student.name }} 可以嘗試更主動地提問，建議從感興趣的英語主題開始，
                        如詢問單字意思、文法規則或文化差異等。
                    </div>
                </div>
                {% endif %}
                
                {% if student.participation_rate and student.participation_rate >= 70 %}
                <div class="recommendation-item">
                    <div class="recommendation-title">⭐ 保持學習優勢</div>
                    <div class="recommendation-desc">
                        {{ student.name }} 表現優秀！建議嘗試更具挑戰性的英語話題，
                        如商業英語、學術寫作或跨文化溝通等進階內容。
                    </div>
                </div>
                {% endif %}
                
                {% if not student.message_count or student.message_count == 0 %}
                <div class="recommendation-item">
                    <div class="recommendation-title">🌟 開始英語學習之旅</div>
                    <div class="recommendation-desc">
                        歡迎 {{ student.name }} 加入 EMI 智能學習！建議從基礎英語問題開始，
                        AI 助理會根據對話內容提供個人化的學習指導和建議。
                    </div>
                </div>
                {% endif %}
            {% endif %}
        </div>
    </div>
    
    <script>
        // 頁面載入動畫
        document.addEventListener('DOMContentLoaded', function() {
            const panels = document.querySelectorAll('.analysis-panel, .student-overview, .conversation-summary, .recommendations');
            
            panels.forEach((panel, index) => {
                panel.style.opacity = '0';
                panel.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    panel.style.transition = 'all 0.5s ease';
                    panel.style.opacity = '1';
                    panel.style.transform = 'translateY(0)';
                }, index * 200);
            });
            
            console.log(`✅ 學生詳細分析頁面已載入：{{ student.name or '未命名學生' }}`);
        });
        
        // 進度條動畫
        setTimeout(() => {
            const progressBars = document.querySelectorAll('.progress-fill');
            progressBars.forEach(bar => {
                const width = bar.style.width;
                bar.style.width = '0%';
                setTimeout(() => {
                    bar.style.width = width;
                }, 100);
            });
        }, 800);
        
        // 鍵盤快捷鍵
        document.addEventListener('keydown', function(e) {
            // B: 返回學生列表
            if (e.key === 'b' && !e.ctrlKey && !e.metaKey) {
                window.location.href = '/students';
            }
            
            // M: 查看訊息記錄
            if (e.key === 'm' && !e.ctrlKey && !e.metaKey) {
                window.location.href = '/student/{{ student.id }}/messages';
            }
            
            // R: 重新載入分析
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                window.location.reload();
            }
        });
        
        // 自動更新學生統計（每60秒）
        setInterval(() => {
            fetch('/api/student-stats/{{ student.id }}')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // 更新統計數字
                        const stats = data.stats;
                        const statNumbers = document.querySelectorAll('.stat-number');
                        
                        if (statNumbers.length >= 6) {
                            statNumbers[0].textContent = stats.participation_rate + '%';
                            statNumbers[1].textContent = stats.message_count;
                            statNumbers[2].textContent = stats.question_count;
                            statNumbers[3].textContent = stats.active_days;
                            statNumbers[4].textContent = stats.question_rate + '%';
                            statNumbers[5].textContent = stats.daily_message_rate;
                        }
                        
                        // 更新進度條
                        const progressBars = document.querySelectorAll('.progress-fill');
                        if (progressBars.length >= 2) {
                            progressBars[0].style.width = stats.participation_rate + '%';
                            progressBars[1].style.width = stats.question_rate + '%';
                        }
                        
                        console.log('📊 學生統計已更新');
                    }
                })
                .catch(error => {
                    console.error('統計更新失敗:', error);
                });
        }, 60000);
    </script>
</body>
</html>
"""

def get_template(template_name):
    """取得指定模板"""
    templates = {
        'index.html': INDEX_TEMPLATE,
        'students.html': STUDENTS_TEMPLATE,
        'student_detail.html': STUDENT_DETAIL_TEMPLATE,
    }
    return templates.get(template_name, '')

# 匯出所有模板
__all__ = [
    'INDEX_TEMPLATE',
    'STUDENTS_TEMPLATE', 
    'STUDENT_DETAIL_TEMPLATE',
    'get_template'
]; }
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
        .waiting-state {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 50px 40px;
            margin-bottom: 25px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        .waiting-icon {
            font-size: 5em;
            margin-bottom: 20px;
            color: #667eea;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.1); opacity: 1; }
        }
        .waiting-title {
            font-size: 2.2em;
            color: #2c3e50;
            margin-bottom: 15px;
            font-weight: 600;
        }
        .waiting-desc {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }
        .setup-guide {
            background: #f8f9ff;
            border-radius: 15px;
            padding: 30px;
            margin: 30px 0;
            text-align: left;
            border-left: 5px solid #667eea;
        }
        .setup-guide h3 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.4em;
            text-align: center;
        }
        .steps-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        .step-item {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #667eea;
        }
        .step-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            background: #667eea;
            color: white;
            border-radius: 50%;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .step-title {
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 8px;
        }
        .step-desc {
            color: #666;
            font-size: 0.9em;
            line-height: 1.4;
        }
        
        /* 真實資料狀態 */
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
            backdrop-filter: blur(10px);
            transition: transform 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .stat-number.zero {
            color: #bdc3c7;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
            font-size: 0.9em;
        }
        .navigation {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }
        .nav-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }
        .nav-item {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-decoration: none;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .nav-item:hover {
            transform: translateY(-5px);
            text-decoration: none;
            color: white;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }
        .nav-item.disabled {
            background: linear-gradient(45deg, #bdc3c7, #95a5a6);
            cursor: not-allowed;
            opacity: 0.7;
        }
        .nav-item.disabled:hover {
            transform: none;
            box-shadow: none;
        }
        .nav-icon {
            font-size: 2.5em;
            margin-bottom: 15px;
            display: block;
        }
        .nav-title {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .nav-desc {
            font-size: 0.9em;
            opacity: 0.9;
            line-height: 1.3;
        }
        .recent-activity {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
        }
        .activity-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .activity-title {
            color: #2c3e50;
            font-size: 1.3em;
            font-weight: 600;
        }
        .activity-item {
            padding: 15px 0;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        .activity-item:last-child {
            border-bottom: none;
        }
        .activity-content {
            flex: 1;
        }
        .activity-student {
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .activity-message {
            color: #666;
            font-size: 0.9em;
            line-height: 1.4;
        }
        .activity-time {
            color: #95a5a6;
            font-size: 0.8em;
            margin-left: 15px;
            white-space: nowrap;
        }
        .no-activity {
            text-align: center;
            color: #666;
            padding: 40px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 2px dashed #bdc3c7;
        }
        .no-activity-icon {
            font-size: 3em;
            margin-bottom: 15px;
            opacity: 0.5;
        }
        
        /* 檢查按鈕 */
        .check-btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s ease;
            margin: 20px 10px;
        }
        .check-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
        }
        .check-btn:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        /* 狀態指示器 */
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .status-waiting {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffc107;
        }
        .status-active {
            background: #d4edda;
            color: #155724;
            border: 1px solid #28a745;
        }
        .status-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #dc3545;
        }
        
        /* 響應式設計 */
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .header h1 { font-size: 2em; }
            .waiting-title { font-size: 1.8em; }
            .waiting-desc { font-size: 1em; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .nav-grid { grid-template-columns: 1fr; }
            .steps-container { grid-template-columns: 1fr; }
            .activity-item { flex-direction: column; align-items: flex-start; }
            .activity-time { margin-left: 0; margin-top: 5px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 EMI 智能教學助理</h1>
            <p>生成式AI輔助的雙語教學創新平台</p>
            <div style="margin-top: 15px;">
                {% if real_data_info %}
                    {% if real_data_info.has_real_data %}
                        <span class="status-indicator status-active">
                            ✅ 真實資料分析中
                        </span>
                    {% elif real_data_info.data_status == 'ERROR' %}
                        <span class="status-indicator status-error">
                            ❌ 系統錯誤
                        </span>
                    {% else %}
                        <span class="status-indicator status-waiting">
                            ⏳ 等待學生開始使用
                        </span>
                    {% endif %}
                {% endif %}
            </div>
        </div>

        {% if real_data_info and not real_data_info.has_real_data %}
        <!-- 等待真實資料狀態 -->
        <div class="waiting-state">
            <div class="waiting-icon">📊</div>
            <h2 class="waiting-title">準備開始智能分析</h2>
            <div class="waiting-desc">
                系統已完成設定，正在等待學生透過 LINE Bot 開始對話。<br>
                一旦有真實學習對話，AI 將立即分析並提供個人化教學洞察。
            </div>
            
            <div class="setup-guide">
                <h3>🚀 快速啟動指南</h3>
                <div class="steps-container">
                    <div class="step-item">
                        <div class="step-number">1</div>
                        <div class="step-title">驗證 LINE Bot</div>
                        <div class="step-desc">
                            確認您的 LINE Bot 已正確配置並能夠接收訊息
                        </div>
                    </div>
                    <div class="step-item">
                        <div class="step-number">2</div>
                        <div class="step-title">邀請學生加入</div>
                        <div class="step-desc">
                            分享 LINE Bot QR Code 或加好友連結給您的學生
                        </div>
                    </div>
                    <div class="step-item">
                        <div class="step-number">3</div>
                        <div class="step-title">鼓勵互動對話</div>
                        <div class="step-desc">
                            引導學生開始用英文提問文法、詞彙或文化問題
                        </div>
                    </div>
                    <div class="step-item">
                        <div class="step-number">4</div>
                        <div class="step-title">查看即時分析</div>
                        <div class="step-desc">
                            系統會自動分析對話並在教師後台顯示洞察結果
                        </div>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 30px;">
                <button class="check-btn" onclick="checkForRealData()">
                    🔄 檢查是否有新的學生資料
                </button>
                <button class="check-btn" onclick="window.open('/health', '_blank')">
                    🔧 檢查系統狀態
                </button>
            </div>
        </div>
        {% else %}
        <!-- 有真實資料時的正常狀態 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number {{ 'zero' if not stats.real_students else '' }}">
                    {{ stats.real_students or 0 }}
                </div>
                <div class="stat-label">真實學生數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number {{ 'zero' if not stats.total_messages else '' }}">
                    {{ stats.total_messages or 0 }}
                </div>
                <div class="stat-label">對話訊息數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number {{ 'zero' if not stats.avg_participation else '' }}">
                    {{ stats.avg_participation or stats.avg_engagement or 0 }}%
                </div>
                <div class="stat-label">平均參與度</div>
            </div>
            <div class="stat-card">
                <div class="stat-number {{ 'zero' if not stats.total_questions else '' }}">
                    {{ stats.total_questions or 0 }}
                </div>
                <div class="stat-label">學生提問數</div>
            </div>
        </div>
        {% endif %}

        <div class="navigation">
            <h3 style="margin-bottom: 20px; color: #2c3e50;">🎯 智能教學功能</h3>
            <div class="nav-grid">
                <a href="/teaching-insights" class="nav-item">
                    <span class="nav-icon">📊</span>
                    <div class="nav-title">教師分析後台</div>
                    <div class="nav-desc">即時分析學生學習困難點和興趣主題</div>
                </a>
                <a href="/students" class="nav-item">
                    <span class="nav-icon">👥</span>
                    <div class="nav-title">學生管理</div>
                    <div class="nav-desc">查看個別學生學習進度和參與度分析</div>
                </a>
                {% if real_data_info and real_data_info.has_real_data %}
                <a href="/admin-cleanup" class="nav-item">
                    <span class="nav-icon">🧹</span>
                    <div class="nav-title">資料清理</div>
                    <div class="nav-desc">清理演示資料，保持分析純淨度</div>
                </a>
                {% else %}
                <div class="nav-item disabled">
                    <span class="nav-icon">⏳</span>
                    <div class="nav-title">等待真實資料</div>
                    <div class="nav-desc">需要學生開始使用後才能進行深度分析</div>
                </div>
                {% endif %}
            </div>
        </div>

        <div class="recent-activity">
            <div class="activity-header">
                <h3 class="activity-title">📈 最近學習活動</h3>
                {% if real_data_info and real_data_info.has_real_data %}
                <span style="color: #27ae60; font-size: 0.9em;">
                    ✅ 真實資料
                </span>
                {% endif %}
            </div>
            
            {% if recent_messages and recent_messages|length > 0 %}
                {% for message in recent_messages %}
                <div class="activity-item">
                    <div class="activity-content">
                        <div class="activity-student">
                            {{ message.student.name if message.student else '匿名學生' }}
                        </div>
                        <div class="activity-message">
                            {{ message.message_type or 'message' }}: 
                            {{ message.content[:80] if message.content else '無內容' }}
                            {% if message.content and message.content|length > 80 %}...{% endif %}
                        </div>
                    </div>
                    <div class="activity-time">
                        {{ message.timestamp.strftime('%m-%d %H:%M') if message.timestamp else '時間不明' }}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-activity">
                    <div class="no-activity-icon">💬</div>
                    <h4 style="margin-bottom: 10px; color: #666;">尚無學習活動記錄</h4>
                    <p style="color: #888; margin-bottom: 15px;">
                        當學生開始使用 LINE Bot 與 AI 助理對話時，<br>
                        最新的學習互動將會顯示在這裡
                    </p>
                    {% if not real_data_info or not real_data_info.has_real_data %}
                    <button class="check-btn" onclick="checkForRealData()">
                        🔍 立即檢查學生活動
                    </button>
                    {% endif %}
                </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        let checkingData = false;
        
        function checkForRealData() {
            if (checkingData) return;
            
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '🔄 檢查中...';
            btn.disabled = true;
            checkingData = true;
            
            fetch('/api/dashboard-stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (data.stats.real_students > 0 || data.has_real_data) {
                            showSuccessNotification(
                                `🎉 發現真實學生資料！\\n` +
                                `真實學生：${data.stats.real_students} 位\\n` +
                                `對話訊息：${data.stats.total_messages} 則\\n\\n` +
                                `頁面將重新載入以顯示分析結果。`
                            );
                            setTimeout(() => {
                                window.location.reload();
                            }, 2000);
                        } else {
                            showInfoNotification(
                                '📊 尚未偵測到學生使用 LINE Bot\\n\\n' +
                                '請確認：\\n' +
                                '• LINE Bot 已正確設定\\n' +
                                '• 學生已加入 LINE Bot\\n' +
                                '• 學生已開始與 AI 對話'
                            );
                        }
                    } else {
                        throw new Error(data.error || '檢查失敗');
                    }
                })
                .catch(error => {
                    console.error('檢查錯誤:', error);
                    showErrorNotification(
                        '❌ 檢查過程發生錯誤\\n\\n' +
                        '可能原因：\\n' +
                        '• 網路連接問題\\n' +
                        '• 系統暫時不可用\\n\\n' +
                        '請稍後再試或聯繫系統管理員。'
                    );
                })
                .finally(() => {
                    btn.textContent = originalText;
                    btn.disabled = false;
                    checkingData = false;
                });
        }
        
        function showSuccessNotification(message) {
            showNotification(message, '#27ae60', '✅');
        }
        
        function showInfoNotification(message) {
            showNotification(message, '#3498db', 'ℹ️');
        }
        
        function showErrorNotification(message) {
            showNotification(message, '#e74c3c', '❌');
        }
        
        function showNotification(message, color, icon) {
            // 移除現有通知
            const existingNotifications = document.querySelectorAll('.notification');
            existingNotifications.forEach(notification => {
                document.body.removeChild(notification);
            });
            
            const notification = document.createElement('div');
            notification.className = 'notification';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${color};
                color: white;
                padding: 20px 25px;
                border-radius: 12px;
                z-index: 1001;
                max-width: 400px;
                box-shadow: 0 6px 25px rgba(0, 0, 0, 0.15);
                animation: slideIn 0.3s ease;
                font-family: inherit;
                line-height: 1.4;
                white-space: pre-line;
            `;
            
            notification.innerHTML = `
                <div style="display: flex; align-items: flex-start; gap: 12px;">
                    <span style="font-size: 1.2em;">${icon}</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; margin-bottom: 5px;">系統通知</div>
                        <div style="font-size: 0.9em; opacity: 0.95;">${message}</div>
                    </div>
                    <button onclick="this.parentNode.parentNode.remove()" 
                            style="background: none; border: none; color: white; font-size: 1.1em; cursor: pointer; padding: 0; opacity: 0.7;">
                        ✕
                    </button>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // 添加動畫樣式
            if (!document.querySelector('style[data-notifications]')) {
                const style = document.createElement('style');
                style.setAttribute('data-notifications', 'true');
                style.textContent = `
                    @keyframes slideIn {
                        from {
                            transform: translateX(100%);
                            opacity: 0;
                        }
                        to {
                            transform: translateX(0);
                            opacity: 1;
                        }
                    }
                    @keyframes slideOut {
                        from {
                            transform: translateX(0);
                            opacity: 1;
                        }
                        to {
                            transform: translateX(100%);
                            opacity: 0;
                        }
                    }
                `;
                document.head.appendChild(style);
            }
            
            // 8秒後自動消失
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    notification.style.animation = 'slideOut 0.3s ease';
                    setTimeout(() => {
                        if (document.body.contains(notification)) {
                            document.body.removeChild(notification);
                        }
                    }, 300);
                }
            }, 8000);
        }
        
        // 自動檢查真實資料（僅在等待狀態時）
        {% if real_data_info and not real_data_info.has_real_data %}
        let autoCheckInterval;
        
        function startAutoCheck() {
            // 每45秒自動檢查一次
            autoCheckInterval = setInterval(() => {
                fetch('/api/dashboard-stats')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && (data.stats.real_students > 0 || data.has_real_data)) {
                            clearInterval(autoCheckInterval);
                            
                            if (confirm(
                                `🎉 系統偵測到新的學生資料！\\n\\n` +
                                `真實學生：${data.stats.real_students} 位\\n` +
                                `是否重新載入頁面查看分析結果？`
                            )) {
                                window.location.reload();
                            }
                        }
                    })
                    .catch(error => {
                        console.error('自動檢查失敗:', error);
                        // 靜默失敗，不影響用戶體驗
                    });
            }, 45000);
        }
        
        // 頁面載入完成後開始自動檢查
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(() => {
                startAutoCheck();
                console.log('🤖 已啟動自動資料檢查（每45秒）');
            }, 5000); // 5秒後開始
        });
        
        // 頁面卸載時清理定時器
        window.addEventListener('beforeunload', function() {
            if (autoCheckInterval) {
                clearInterval(autoCheckInterval);
            }
        });
        {% endif %}
        
        // 歡迎提示（僅顯示一次）
        document.addEventListener('DOMContentLoaded', function() {
            const hasShownWelcome = localStorage.getItem('emi_welcome_shown');
            
            if (!hasShownWelcome) {
                setTimeout(() => {
                    {% if real_data_info and not real_data_info.has_real_data %}
                    showInfoNotification(
                        '🎓 歡迎使用 EMI 智能教學助理！\\n\\n' +
                        '系統已準備就緒，等待學生開始使用 LINE Bot。\\n' +
                        '一旦有對話資料，AI 將立即提供教學洞察。'
                    );
                    {% else %}
                    showSuccessNotification(
                        '🎉 EMI 智能教學助理運行中！\\n\\n' +
                        '系統正在分析真實學生資料，\\n' +
                        '您可以在教師分析後台查看詳細洞察。'
                    );
                    {% endif %}
                    
                    localStorage.setItem('emi_welcome_shown', 'true');
                }, 2000);
            }
        });
    </script>
</body>
</html>
"""

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
        
        /* 篩選和搜尋 */
        .filters {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }
        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            align-items: end;
        }
        .filter-group {
            display: flex;
            flex-direction: column;
        }
        .filter-label {
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }
        .filter-input {
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }
        .filter-input:focus {
            outline: none;
            border-color: #74b9ff;
        }
        .filter-btn {
            background: linear-gradient(45deg, #74b9ff, #0984e3);
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .filter-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(116, 185, 255, 0.3);
        }
        
        /* 學生列表 */
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
            position: relative;
            overflow: hidden;
        }
        .student-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }
        .student-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }
        .student-name {
            font-size: 1.3em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .student-id {
            font-size: 0.9em;
            color: #666;
            font-family: monospace;
        }
        .student-status {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .status-active {
            background: #d4edda;
            color: #155724;
        }
        .status-inactive {
            background: #f8d7da;
            color: #721c24;
        }
        .status-new {
            background: #d1ecf1;
            color: #0c5460;
        }
        .student-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-item {
            text-align: center;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
        }
        .stat-number {
            font-size: 1.8em;
            font-weight: bold;
            color: #74b9ff;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 0.8em;
            color: #666;
        }
        .student-engagement {
            margin-bottom: 20px;
        }
        .engagement-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
        }
        .engagement-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }
        .engagement-fill {
            height: 100%;
            background: linear-gradient(90deg, #74b9ff, #0984e3);
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        .engagement-percentage {
            text-align: right;
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }
        .student-actions {
            display: flex;
            gap: 10px;
        }
        .action-btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            text-decoration: none;
            text-align: center;
            transition: all 0.3s ease;
        }
        .btn-primary {
            background: linear-gradient(45deg, #74b9ff, #0984e3);
            color: white;
        }
        .btn-secondary {
            background: linear-gradient(45deg, #a29bfe, #6c5ce7);
            color: white;
        }
        .action-btn:hover {
            transform: translateY(-2px);
            text-decoration: none;
            color: white;
        }
        
        /* 統計摘要 */
        .summary-stats {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            margin-bottom: 25px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .summary-item {
            text-align: center;
            padding: 20px;
            background: linear-gradient(45deg, #74b9ff, #0984e3);
            color: white;
            border-radius: 12px;
        }
        .summary-number {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .summary-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        /* 響應式設計 */
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .students-grid { grid-template-columns: 1fr; }
            .filter-grid { grid-template-columns: 1fr; }
            .summary-grid { grid-template-columns: repeat(2, 1fr); }
            .student-stats { grid-template-columns: 1fr; }
            .student-actions { flex-direction: column; }
        }
    </style>
</head>
<body>
    <a href="/" class="back-btn">← 返回首頁</a>
    
    <div class="container">
        <div class="header">
            <h1>👥 學生管理</h1>
            <p>真實學習資料分析與個人化教學洞察</p>
        </div>
        
        {% if students and students|length > 0 %}
        <div class="real-data-status">
            ✅ 顯示 {{ students|length }} 位真實學生的學習資料（已過濾演示資料）
        </div>
        
        <!-- 統計摘要 -->
        <div class="summary-stats">
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-number">{{ students|length or 0 }}</div>
                    <div class="summary-label">真實學生</div>
                </div>
                <div class="summary-item">
                    <div class="summary-number">{{ total_messages or 0 }}</div>
                    <div class="summary-label">對話訊息</div>
                </div>
                <div class="summary-item">
                    <div class="summary-number">{{ avg_engagement or 0 }}%</div>
                    <div class="summary-label">平均參與度</div>
                </div>
                <div class="summary-item">
                    <div class="summary-number">{{ active_students or 0 }}</div>
                    <div class="summary-label">活躍學生</div>
                </div>
            </div>
        </div>
        
        <!-- 篩選器 -->
        <div class="filters">
            <div class="filter-grid">
                <div class="filter-group">
                    <label class="filter-label">🔍 搜尋學生</label>
                    <input type="text" id="searchInput" class="filter-input" 
                           placeholder="輸入學生姓名或ID..." onkeyup="filterStudents()">
                </div>
                <div class="filter-group">
                    <label class="filter-label">📊 參與度篩選</label>
                    <select id="engagementFilter" class="filter-input" onchange="filterStudents()">
                        <option value="">全部學生</option>
                        <option value="high">高參與度 (80%+)</option>
                        <option value="medium">中參與度 (50-80%)</option>
                        <option value="low">低參與度 (<50%)</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">🕒 活躍狀態</label>
                    <select id="statusFilter" class="filter-input" onchange="filterStudents()">
                        <option value="">全部狀態</option>
                        <option value="active">活躍</option>
                        <option value="inactive">不活躍</option>
                        <option value="new">新加入</option>
                    </select>
                </div>
                <div class="filter-group">
                    <button class="filter-btn" onclick="resetFilters()">
                        🔄 重置篩選
                    </button>
                </div>
            </div>
        </div>
        
        <!-- 學生卡片列表 -->
        <div class="students-grid" id="studentsGrid">
            {% for student in students %}
            <div class="student-card" 
                 data-name="{{ student.name.lower() if student.name else '' }}"
                 data-id="{{ student.line_user_id.lower() if student.line_user_id else '' }}"
                 data-engagement="{{ student.participation_rate or 0 }}"
                 data-status="{{ 'active' if student.last_active and (current_time - student.last_active).days < 7 else 'inactive' if student.last_active else 'new' }}">
                
                <div class="student-header">
                    <div>
                        <div class="student-name">
                            {{ student.name or '未命名學生' }}
                        </div>
                        <div class="student-id">
                            ID: {{ student.line_user_id[:10] if student.line_user_id else 'unknown' }}...
                        </div>
                    </div>
                    <div class="student-status status-{{ 'active' if student.last_active and (current_time - student.last_active).days < 7 else 'inactive' if student.last_active else 'new' }}">
                        {% if student.last_active and (current_time - student.last_active).days < 7 %}
                            ✅ 活躍
                        {% elif student.last_active %}
                            ⏸️ 不活躍
                        {% else %}
                            🆕 新加入
                        {% endif %}
                    </div>
                </div>
                
                <div class="student-stats">
                    <div class="stat-item">
                        <div class="stat-number">{{ student.message_count or 0 }}</div>
                        <div class="stat-label">對話數</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{{ student.question_count or 0 }}</div>
                        <div class="stat-label">提問數</div>
                    </div>
                </div>
                
                <div class="student-engagement">
                    <div class="engagement-label">
                        📈 學習參與度
                    </div>
                    <div class="engagement-bar">
                        <div class="engagement-fill" 
                             style="width: {{ student.participation_rate or 0 }}%"></div>
                    </div>
                    <div class="engagement-percentage">
                        {{ student.participation_rate or 0 }}%
                    </div>
                </div>
                
                <div class="student-actions">
                    <a href="/student/{{ student.id }}" class="action-btn btn-primary">
                        📊 詳細分析
                    </a>
                    <a href="/student/{{ student.id }}/messages" class="action-btn btn-secondary">
                        💬 對話記錄
                    </a>
                </div>
            </div>
            {% endfor %}
        </div>
        
        {% else %}
        <!-- 無真實資料狀態 -->
        <div class="no-real-data">
            <h3>📭 尚無真實學生資料</h3>
            <p style="margin-bottom: 20px; line-height: 1.6;">
                系統正在等待學生開始使用 LINE Bot 與 AI 助理對話。<br>
                一旦有學生開始互動，他們的學習分析將會出現在這裡。
            </p>
            <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                <button class="filter-btn" onclick="checkForStudents()">
                    🔄 檢查新學生
                </button>
                <a href="/teaching-insights" class="filter-btn" style="text-decoration: none; color: white;">
                    📊 查看分析後台
                </a>
            </div>
        </div>
        {% endif %}
    </div>
    
    <script>
        function filterStudents() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const engagementFilter = document.getElementById('engagementFilter').value;
            const statusFilter = document.getElementById('statusFilter').value;
            
            const studentCards = document.querySelectorAll('.student-card');
            let visibleCount = 0;
            
            studentCards.forEach(card => {
                let show = true;
                
                // 搜尋篩選
                if (searchTerm) {
                    const name = card.dataset.name || '';
                    const id = card.dataset.id || '';
                    if (!name.includes(searchTerm) && !id.includes(searchTerm)) {
                        show = false;
                    }
                }
                
                // 參與度篩選
                if (engagementFilter && show) {
                    const engagement = parseInt(card.dataset.engagement) || 0;
                    switch (engagementFilter) {
                        case 'high':
                            if (engagement < 80) show = false;
                            break;
                        case 'medium':
                            if (engagement < 50 || engagement >= 80) show = false;
                            break;
                        case 'low':
                            if (engagement >= 50) show = false;
                            break;
                    }
                }
                
                // 狀態篩選
                if (statusFilter && show) {
                    if (card.dataset.status !== statusFilter) show = false;
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
            
            fetch('/api/students-stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (data.real_students > 0) {
                            alert(
                                `🎉 發現 ${data.real_students} 位真實學生！\\n\\n` +
                                `頁面將重新載入以顯示學生列表。`
                            );
                            window.location.reload();
                        } else {
                            alert(
                                '📊 尚未偵測到學生使用 LINE Bot\\n\\n' +
                                '請確認：\\n' +
                                '• LINE Bot 已正確設定\\n' +
                                '• 學生已加入 LINE Bot\\n' +
                                '• 學生已開始與 AI 對話'
                            );
                        }
                    } else {
                        throw new Error(data.error || '檢查失敗');
                    }
                })
                .catch(error => {
                    console.error('檢查錯誤:', error);
                    alert('❌ 檢查過程發生錯誤，請稍後再試。');
                })
                .finally(() => {
                    btn.textContent = originalText;
                    btn.disabled = false;
                });
        }
        
        // 鍵盤快捷鍵
        document.addEventListener('keydown', function(e) {
            // Ctrl+F: 聚焦搜尋框
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }
            
            // Escape: 重置篩選
            if (e.key === 'Escape') {
                resetFilters();
            }
        });
        
        // 頁面載入時顯示歡迎訊息
        document.addEventListener('DOMContentLoaded', function() {
            {% if students and students|length > 0 %}
            console.log('✅ 學生管理頁面已載入，顯示 {{ students|length }} 位真實學生');
            
            // 載入動畫
            const studentCards = document.querySelectorAll('.student-card');
            studentCards.forEach((card, index) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    card.style.transition = 'all 0.5s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, index * 100);
            });
            
            {% else %}
            console.log('⏳ 學生管理頁面已載入，等待真實學生資料');
            {% endif %}
        });
        
        // 自動檢查新學生（每60秒）
        {% if not students or students|length == 0 %}
        setInterval(() => {
            fetch('/api/students-stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.real_students > 0) {
                        // 靜默重新載入（如果發現新學生）
                        window.location.reload();
                    }
                })
                .catch(error => {
                    console.log('自動檢查失敗:', error);
                });
        }, 60000);
        {% endif %}
    </script>
</body>
</html>
"""
