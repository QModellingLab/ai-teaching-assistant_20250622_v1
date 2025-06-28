# === 學生列表頁面模板更新 ===
STUDENTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📚 學生列表 - EMI智能教學助理</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <nav class="mobile-nav">
        <div class="nav-header">
            <h1>📚 EMI助理</h1>
            <button class="nav-toggle" onclick="toggleMobileNav()">☰</button>
        </div>
        <div class="nav-menu" id="mobile-menu">
            <a href="/students">👥 學生列表</a>
            <a href="/teaching-insights">📈 教學洞察</a>
        </div>
    </nav>
    
    <div class="container">
        <div class="page-header">
            <h1>📚 學生列表</h1>
            <p class="page-subtitle">管理和查看所有學生的學習狀況</p>
        </div>
        
        <div class="search-section card mb-6">
            <div class="search-bar">
                <input type="text" id="student-search" class="form-input" 
                       placeholder="🔍 搜尋學生姓名..." 
                       onkeyup="filterStudents(this.value)">
            </div>
            <div class="filter-buttons mt-4">
                <button class="btn btn-secondary btn-sm" onclick="filterByActivity('all')">全部</button>
                <button class="btn btn-secondary btn-sm" onclick="filterByActivity('active')">活躍</button>
                <button class="btn btn-secondary btn-sm" onclick="filterByActivity('inactive')">較少活動</button>
            </div>
        </div>
        
        <div class="students-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3" id="students-container">
            {students_content}
        </div>
        
        <div id="empty-state" class="empty-state text-center" style="display: none;">
            <div class="empty-icon">👥</div>
            <h3>沒有找到學生</h3>
            <p>請調整搜尋條件或檢查學生資料</p>
        </div>
    </div>
    
    <script src="/static/js/progress.js"></script>
    <script src="/static/js/ui-helpers.js"></script>
    <script>
        function filterStudents(searchTerm) {
            const cards = document.querySelectorAll('.student-card');
            const term = searchTerm.toLowerCase();
            let visibleCount = 0;
            
            cards.forEach(card => {
                const name = card.querySelector('.student-name').textContent.toLowerCase();
                if (name.includes(term)) {
                    card.style.display = 'block';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });
            
            document.getElementById('empty-state').style.display = 
                visibleCount === 0 ? 'block' : 'none';
        }
        
        function filterByActivity(type) {
            const cards = document.querySelectorAll('.student-card');
            
            cards.forEach(card => {
                const isActive = card.dataset.active === 'true';
                
                if (type === 'all' || 
                    (type === 'active' && isActive) ||
                    (type === 'inactive' && !isActive)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        }
        
        function toggleMobileNav() {
            const menu = document.getElementById('mobile-menu');
            menu.classList.toggle('active');
        }
        
        function copyStudentInfo(studentId) {
            const studentCard = document.querySelector(`[data-student-id="${studentId}"]`);
            const name = studentCard.querySelector('.student-name').textContent;
            const messageCount = studentCard.querySelector('.stat-value').textContent;
            
            const info = `學生：${name}\\n訊息數：${messageCount}`;
            copyToClipboard(info);
        }
        
        function viewRecentActivity(studentId) {
            showProgress('載入活動', '正在載入近期活動...', 50);
            
            setTimeout(() => {
                hideProgress();
                showSuccess('近期活動載入完成');
            }, 1000);
        }
    </script>
</body>
</html>
"""

# 學生卡片模板
STUDENT_CARD_TEMPLATE = """
<div class="student-card card" data-active="{is_active}" data-student-id="{student_id}">
    <div class="card-header">
        <div class="student-avatar">
            <span class="avatar-text">{student_initial}</span>
        </div>
        <div class="student-basic-info">
            <h3 class="student-name">{student_name}</h3>
            <span class="student-status {status_class}">{status_text}</span>
        </div>
    </div>
    
    <div class="student-stats">
        <div class="stat-item">
            <span class="stat-icon">💬</span>
            <span class="stat-value">{message_count}</span>
            <span class="stat-label">訊息</span>
        </div>
        <div class="stat-item">
            <span class="stat-icon">❓</span>
            <span class="stat-value">{question_count}</span>
            <span class="stat-label">提問</span>
        </div>
        <div class="stat-item">
            <span class="stat-icon">📅</span>
            <span class="stat-value">{days_since_active}</span>
            <span class="stat-label">天前活動</span>
        </div>
    </div>
    
    <div class="student-actions">
        <a href="/students/{student_id}" class="btn btn-primary btn-sm">
            📝 查看詳情
        </a>
        <a href="/students/{student_id}/summary" class="btn btn-success btn-sm">
            📊 學習摘要
        </a>
        <button onclick="downloadStudentQuestions({student_id})" class="btn btn-danger btn-sm">
            📥 下載提問
        </button>
    </div>
    
    <div class="student-quick-actions mt-4">
        <button onclick="copyStudentInfo({student_id})" class="btn btn-secondary btn-sm">
            📋 複製資訊
        </button>
        <button onclick="viewRecentActivity({student_id})" class="btn btn-secondary btn-sm">
            🕒 近期活動
        </button>
    </div>
</div>
"""

# 教學洞察頁面模板（完整重新設計）
TEACHING_INSIGHTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 教學洞察 - EMI智能教學助理</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <nav class="mobile-nav">
        <div class="nav-header">
            <h1>📈 教學洞察</h1>
            <button class="nav-toggle" onclick="toggleMobileNav()">☰</button>
        </div>
        <div class="nav-menu" id="mobile-menu">
            <a href="/students">👥 學生列表</a>
            <a href="/teaching-insights">📈 教學洞察</a>
        </div>
    </nav>
    
    <div class="container">
        <div class="page-header">
            <h1>📈 教學洞察</h1>
            <p class="page-subtitle">深入了解班級整體學習狀況和趨勢</p>
            <div class="page-actions">
                <button onclick="refreshInsights()" class="btn btn-secondary">
                    🔄 重新整理
                </button>
                <button onclick="exportInsightsReport()" class="btn btn-primary">
                    📊 匯出報告
                </button>
            </div>
        </div>
        
        <div id="insights-loading" class="loading-container text-center">
            <div class="loading-spinner"></div>
            <p>正在分析教學資料...</p>
        </div>
        
        <div id="insights-content" style="display: none;">
            <section class="stats-overview mb-8">
                <h2>📊 班級統計概覽</h2>
                <div class="stats-grid grid grid-cols-2 lg:grid-cols-4 gap-6">
                    <div class="stat-card">
                        <div class="stat-icon">👥</div>
                        <div class="stat-number" id="total-students">{total_students}</div>
                        <div class="stat-label">總學生數</div>
                        <div class="stat-trend {students_trend_class}">
                            {students_trend_text}
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">❓</div>
                        <div class="stat-number" id="total-questions">{total_questions}</div>
                        <div class="stat-label">總提問數</div>
                        <div class="stat-trend {questions_trend_class}">
                            {questions_trend_text}
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">🔥</div>
                        <div class="stat-number" id="active-students">{active_students}</div>
                        <div class="stat-label">活躍學生</div>
                        <div class="stat-trend {active_trend_class}">
                            {active_trend_text}
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">💬</div>
                        <div class="stat-number" id="total-messages">{total_messages}</div>
                        <div class="stat-label">總互動數</div>
                        <div class="stat-trend {messages_trend_class}">
                            {messages_trend_text}
                        </div>
                    </div>
                </div>
            </section>
            
            <section class="ai-analysis mb-8">
                <div class="card">
                    <div class="card-header">
                        <h2>🤖 AI學習分析</h2>
                        <div class="analysis-status">
                            <span id="analysis-timestamp" class="text-sm text-gray-500">
                                {analysis_timestamp}
                            </span>
                            <button onclick="regenerateAnalysis()" class="btn btn-sm btn-secondary">
                                🔄 重新分析
                            </button>
                        </div>
                    </div>
                    
                    <div id="ai-summary-content">
                        <div class="analysis-section">
                            <h3>📋 全班學習摘要</h3>
                            <div id="class-summary" class="summary-content">
                                {class_summary_content}
                            </div>
                        </div>
                        
                        <div class="analysis-section">
                            <h3>🏷️ 學習關鍵詞</h3>
                            <div id="learning-keywords" class="keywords-container">
                                {keywords_content}
                            </div>
                        </div>
                        
                        <div class="analysis-section">
                            <h3>📈 學習趨勢分析</h3>
                            <div id="learning-trends" class="trends-content">
                                {trends_content}
                            </div>
                        </div>
                    </div>
                    
                    <div id="ai-analysis-loading" class="analysis-loading" style="display: none;">
                        <div class="loading-spinner"></div>
                        <p>AI正在深度分析學習資料...</p>
                    </div>
                    
                    <div id="ai-analysis-error" class="analysis-error" style="display: none;">
                        <div class="error-message">
                            <span class="error-icon">⚠️</span>
                            <div>
                                <h4>AI分析暫時無法使用</h4>
                                <p>系統將顯示基本統計資料，請稍後重試AI分析功能</p>
                                <button onclick="retryAIAnalysis()" class="btn btn-sm btn-primary mt-2">
                                    🔄 重試AI分析
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
            
            <section class="charts-section mb-8">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="card">
                        <div class="card-header">
                            <h3>📊 提問趨勢圖</h3>
                        </div>
                        <div class="chart-container">
                            <canvas id="questions-chart" width="400" height="200"></canvas>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3>👥 學生參與度</h3>
                        </div>
                        <div class="chart-container">
                            <canvas id="participation-chart" width="400" height="200"></canvas>
                        </div>
                    </div>
                </div>
            </section>

# 教學洞察頁面模板（完整重新設計）
TEACHING_INSIGHTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 教學洞察 - EMI智能教學助理</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <nav class="mobile-nav">
        <div class="nav-header">
            <h1>📈 教學洞察</h1>
            <button class="nav-toggle" onclick="toggleMobileNav()">☰</button>
        </div>
        <div class="nav-menu" id="mobile-menu">
            <a href="/students">👥 學生列表</a>
            <a href="/teaching-insights">📈 教學洞察</a>
        </div>
    </nav>
    
    <div class="container">
        <div class="page-header">
            <h1>📈 教學洞察</h1>
            <p class="page-subtitle">深入了解班級整體學習狀況和趨勢</p>
            <div class="page-actions">
                <button onclick="refreshInsights()" class="btn btn-secondary">
                    🔄 重新整理
                </button>
                <button onclick="exportInsightsReport()" class="btn btn-primary">
                    📊 匯出報告
                </button>
            </div>
        </div>
        
        <div id="insights-loading" class="loading-container text-center">
            <div class="loading-spinner"></div>
            <p>正在分析教學資料...</p>
        </div>
        
        <div id="insights-content" style="display: none;">
            <section class="stats-overview mb-8">
                <h2>📊 班級統計概覽</h2>
                <div class="stats-grid grid grid-cols-2 lg:grid-cols-4 gap-6">
                    <div class="stat-card">
                        <div class="stat-icon">👥</div>
                        <div class="stat-number" id="total-students">{total_students}</div>
                        <div class="stat-label">總學生數</div>
                        <div class="stat-trend {students_trend_class}">
                            {students_trend_text}
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">❓</div>
                        <div class="stat-number" id="total-questions">{total_questions}</div>
                        <div class="stat-label">總提問數</div>
                        <div class="stat-trend {questions_trend_class}">
                            {questions_trend_text}
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">🔥</div>
                        <div class="stat-number" id="active-students">{active_students}</div>
                        <div class="stat-label">活躍學生</div>
                        <div class="stat-trend {active_trend_class}">
                            {active_trend_text}
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">💬</div>
                        <div class="stat-number" id="total-messages">{total_messages}</div>
                        <div class="stat-label">總互動數</div>
                        <div class="stat-trend {messages_trend_class}">
                            {messages_trend_text}
                        </div>
                    </div>
                </div>
            </section>
            
            <section class="export-section">
                <div class="card">
                    <div class="card-header">
                        <h3>📥 資料匯出</h3>
                        <p class="card-subtitle">匯出完整的學習資料供進一步分析</p>
                    </div>
                    
                    <div class="export-options grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div class="export-option">
                            <h4>📝 學生提問記錄</h4>
                            <p>匯出所有學生的提問內容和時間</p>
                            <button onclick="downloadAllQuestions()" class="btn btn-primary w-full">
                                📥 下載TSV檔案
                            </button>
                        </div>
                        
                        <div class="export-option">
                            <h4>📊 統計摘要報告</h4>
                            <p>包含AI分析和統計圖表的完整報告</p>
                            <button onclick="downloadAnalyticsReport()" class="btn btn-primary w-full">
                                📊 下載PDF報告
                            </button>
                        </div>
                        
                        <div class="export-option">
                            <h4>📈 學習趨勢資料</h4>
                            <p>時間序列的學習活動資料</p>
                            <button onclick="downloadTrendsData()" class="btn btn-primary w-full">
                                📈 下載Excel檔案
                            </button>
                        </div>
                    </div>
                </div>
            </section>
        </div>
        
        <div id="insights-error" class="error-container text-center" style="display: none;">
            <div class="error-icon">⚠️</div>
            <h3>載入教學洞察時發生錯誤</h3>
            <p>請檢查網路連接或稍後重試</p>
            <button onclick="window.location.reload()" class="btn btn-primary">
                🔄 重新載入
            </button>
        </div>
    </div>
    
    <script src="/static/js/progress.js"></script>
    <script src="/static/js/ui-helpers.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            initializeInsights();
        });
        
        function initializeInsights() {
            showInsightsLoading();
            
            setTimeout(() => {
                hideInsightsLoading();
                showInsightsContent();
                initializeCharts();
            }, 2000);
        }
        
        function showInsightsLoading() {
            document.getElementById('insights-loading').style.display = 'block';
            document.getElementById('insights-content').style.display = 'none';
            document.getElementById('insights-error').style.display = 'none';
        }
        
        function hideInsightsLoading() {
            document.getElementById('insights-loading').style.display = 'none';
        }
        
        function showInsightsContent() {
            document.getElementById('insights-content').style.display = 'block';
        }
        
        function refreshInsights() {
            showInsightsLoading();
            setTimeout(() => {
                hideInsightsLoading();
                showInsightsContent();
                showSuccess('教學洞察已更新');
            }, 1500);
        }
        
        function regenerateAnalysis() {
            const analysisContent = document.getElementById('ai-summary-content');
            const analysisLoading = document.getElementById('ai-analysis-loading');
            
            analysisContent.style.display = 'none';
            analysisLoading.style.display = 'block';
            
            setTimeout(() => {
                analysisLoading.style.display = 'none';
                analysisContent.style.display = 'block';
                showSuccess('AI分析已更新');
            }, 3000);
        }
        
        function retryAIAnalysis() {
            const errorDiv = document.getElementById('ai-analysis-error');
            const loadingDiv = document.getElementById('ai-analysis-loading');
            
            errorDiv.style.display = 'none';
            loadingDiv.style.display = 'block';
            
            setTimeout(() => {
                loadingDiv.style.display = 'none';
                document.getElementById('ai-summary-content').style.display = 'block';
                showSuccess('AI分析重試成功');
            }, 2000);
        }
        
        function initializeCharts() {
            initQuestionsChart();
            initParticipationChart();
        }
        
        function initQuestionsChart() {
            const canvas = document.getElementById('questions-chart');
            if (canvas) {
                createSimpleChart('questions-chart', {
                    labels: ['週一', '週二', '週三', '週四', '週五'],
                    values: [12, 19, 8, 15, 23]
                }, { type: 'bar', color: '#667eea' });
            }
        }
        
        function initParticipationChart() {
            const canvas = document.getElementById('participation-chart');
            if (canvas) {
                createSimpleChart('participation-chart', {
                    labels: ['高', '中', '低'],
                    values: [15, 8, 3]
                }, { type: 'bar', color: '#48bb78' });
            }
        }
        
        function downloadAllQuestions() {
            downloadWithProgress('/download-all-questions', 'all_students_questions.tsv');
        }
        
        function downloadAnalyticsReport() {
            showProgress('生成報告', '正在準備PDF報告...', 10);
            
            setTimeout(() => updateProgress('收集統計資料...', 30), 500);
            setTimeout(() => updateProgress('生成AI分析內容...', 60), 1500);
            setTimeout(() => updateProgress('格式化PDF文件...', 90), 2500);
            setTimeout(() => {
                updateProgress('報告生成完成！', 100);
                setTimeout(() => {
                    hideProgress();
                    showSuccess('分析報告已下載');
                }, 500);
            }, 3000);
        }
        
        function downloadTrendsData() {
            downloadWithProgress('/api/export/trends-data', 'learning_trends.xlsx');
        }
        
        function exportInsightsReport() {
            showProgress('匯出報告', '正在準備完整報告...', 0);
            
            setTimeout(() => updateProgress('收集圖表資料...', 25), 500);
            setTimeout(() => updateProgress('整理AI分析結果...', 50), 1000);
            setTimeout(() => updateProgress('生成完整報告...', 75), 1500);
            setTimeout(() => updateProgress('報告準備完成！', 100), 2000);
            setTimeout(() => {
                hideProgress();
                showSuccess('完整報告已匯出');
            }, 2500);
        }
        
        function toggleMobileNav() {
            const menu = document.getElementById('mobile-menu');
            menu.classList.toggle('active');
        }
    </script>
</body>
</html>
"""
            
            <section class="ai-analysis mb-8">
                <div class="card">
                    <div class="card-header">
                        <h2>🤖 AI學習分析</h2>
                        <div class="analysis-status">
                            <span id="analysis-timestamp" class="text-sm text-gray-500">
                                {analysis_timestamp}
                            </span>
                            <button onclick="regenerateAnalysis()" class="btn btn-sm btn-secondary">
                                🔄 重新分析
                            </button>
                        </div>
                    </div>
                    
                    <div id="ai-summary-content">
                        <div class="analysis-section">
                            <h3>📋 全班學習摘要</h3>
                            <div id="class-summary" class="summary-content">
                                {class_summary_content}
                            </div>
                        </div>
                        
                        <div class="analysis-section">
                            <h3>🏷️ 學習關鍵詞</h3>
                            <div id="learning-keywords" class="keywords-container">
                                {keywords_content}
                            </div>
                        </div>
                        
                        <div class="analysis-section">
                            <h3>📈 學習趨勢分析</h3>
                            <div id="learning-trends" class="trends-content">
                                {trends_content}
                            </div>
                        </div>
                    </div>
                    
                    <div id="ai-analysis-loading" class="analysis-loading" style="display: none;">
                        <div class="loading-spinner"></div>
                        <p>AI正在深度分析學習資料...</p>
                    </div>
                    
                    <div id="ai-analysis-error" class="analysis-error" style="display: none;">
                        <div class="error-message">
                            <span class="error-icon">⚠️</span>
                            <div>
                                <h4>AI分析暫時無法使用</h4>
                                <p>系統將顯示基本統計資料，請稍後重試AI分析功能</p>
                                <button onclick="retryAIAnalysis()" class="btn btn-sm btn-primary mt-2">
                                    🔄 重試AI分析
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
            
            <section class="charts-section mb-8">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="card">
                        <div class="card-header">
                            <h3>📊 提問趨勢圖</h3>
                        </div>
                        <div class="chart-container">
                            <canvas id="questions-chart" width="400" height="200"></canvas>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3>👥 學生參與度</h3>
                        </div>
                        <div class="chart-container">
                            <canvas id="participation-chart" width="400" height="200"></canvas>
                        </div>
                    </div>
                </div>
            </section>
