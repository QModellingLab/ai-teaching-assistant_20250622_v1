# templates_management.py - 管理功能模板

# 儲存空間管理模板
STORAGE_MANAGEMENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💾 儲存空間管理 - EMI 智能教學助理</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            text-align: center;
        }
        
        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.2em;
        }
        
        .storage-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .used { color: #e74c3c; }
        .available { color: #27ae60; }
        .total { color: #3498db; }
        .growth { color: #f39c12; }
        
        .progress-bar {
            background: #ecf0f1;
            border-radius: 10px;
            height: 20px;
            margin: 15px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
        }
        
        .storage-breakdown {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
        }
        
        .data-categories {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .category-item {
            display: flex;
            align-items: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid;
            transition: transform 0.2s ease;
        }
        
        .category-item:hover {
            transform: translateX(5px);
        }
        
        .conversations { border-left-color: #3498db; }
        .analysis { border-left-color: #e74c3c; }
        .cache { border-left-color: #f39c12; }
        .exports { border-left-color: #9b59b6; }
        .logs { border-left-color: #2ecc71; }
        
        .category-icon {
            font-size: 1.5em;
            margin-right: 15px;
        }
        
        .category-info h4 {
            margin-bottom: 5px;
            color: #2c3e50;
        }
        
        .category-size {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .management-actions {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .action-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .action-card {
            padding: 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            border: none;
        }
        
        .action-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
        }
        
        .action-card h3 {
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .action-card p {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .cleanup-safe { background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); }
        .cleanup-aggressive { background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); }
        .export-data { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); }
        .optimize { background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); }
        
        .alerts {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .alert {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 4px solid;
        }
        
        .alert-warning {
            background: #fff3cd;
            border-left-color: #ffc107;
            color: #856404;
        }
        
        .alert-danger {
            background: #f8d7da;
            border-left-color: #dc3545;
            color: #721c24;
        }
        
        .alert-info {
            background: #d1ecf1;
            border-left-color: #17a2b8;
            color: #0c5460;
        }
        
        .recommendations {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .recommendation-item {
            display: flex;
            align-items: flex-start;
            padding: 20px;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #3498db;
        }
        
        .recommendation-icon {
            font-size: 1.5em;
            margin-right: 15px;
            color: #3498db;
        }
        
        .recommendation-content h4 {
            margin-bottom: 8px;
            color: #2c3e50;
        }
        
        .recommendation-content p {
            color: #7f8c8d;
            margin-bottom: 10px;
        }
        
        .recommendation-action {
            background: #3498db;
            color: white;
            padding: 8px 15px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background 0.3s ease;
        }
        
        .recommendation-action:hover {
            background: #2980b9;
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
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        }
    </style>
</head>
<body>
    <a href="/teaching-insights" class="back-btn">← 返回分析後台</a>
    
    <div class="container">
        <div class="header">
            <h1>💾 儲存空間管理</h1>
            <p>監控系統儲存使用狀況，優化空間配置</p>
        </div>
        
        <!-- 儲存統計概覽 -->
        <div class="storage-stats">
            <div class="stat-card">
                <div class="stat-value used">{{ storage_stats.used_gb }}GB</div>
                <div>已使用空間</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {{ storage_stats.usage_percentage }}%; background: linear-gradient(90deg, #e74c3c, #c0392b);"></div>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value available">{{ storage_stats.available_gb }}GB</div>
                <div>可用空間</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {{ 100 - storage_stats.usage_percentage }}%; background: linear-gradient(90deg, #27ae60, #2ecc71);"></div>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value total">{{ storage_stats.total_gb }}GB</div>
                <div>總容量</div>
                <div style="font-size: 0.9em; color: #7f8c8d; margin-top: 10px;">
                    使用率：{{ storage_stats.usage_percentage }}%
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value growth">+{{ storage_stats.daily_growth_mb }}MB</div>
                <div>日均增長</div>
                <div style="font-size: 0.9em; color: #7f8c8d; margin-top: 10px;">
                    預估 {{ storage_stats.days_until_full }} 天後滿載
                </div>
            </div>
        </div>
        
        <!-- 空間分布圖表 -->
        <div class="storage-breakdown">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">📊 儲存空間分布</h2>
            <div class="chart-container">
                <canvas id="storageChart"></canvas>
            </div>
            
            <!-- 資料分類詳情 -->
            <div class="data-categories">
                <div class="category-item conversations">
                    <div class="category-icon">💬</div>
                    <div class="category-info">
                        <h4>對話記錄</h4>
                        <div class="category-size">{{ data_breakdown.conversations.size }} ({{ data_breakdown.conversations.percentage }}%)</div>
                    </div>
                </div>
                
                <div class="category-item analysis">
                    <div class="category-icon">📈</div>
                    <div class="category-info">
                        <h4>分析結果</h4>
                        <div class="category-size">{{ data_breakdown.analysis.size }} ({{ data_breakdown.analysis.percentage }}%)</div>
                    </div>
                </div>
                
                <div class="category-item cache">
                    <div class="category-icon">⚡</div>
                    <div class="category-info">
                        <h4>快取資料</h4>
                        <div class="category-size">{{ data_breakdown.cache.size }} ({{ data_breakdown.cache.percentage }}%)</div>
                    </div>
                </div>
                
                <div class="category-item exports">
                    <div class="category-icon">📁</div>
                    <div class="category-info">
                        <h4>匯出檔案</h4>
                        <div class="category-size">{{ data_breakdown.exports.size }} ({{ data_breakdown.exports.percentage }}%)</div>
                    </div>
                </div>
                
                <div class="category-item logs">
                    <div class="category-icon">📝</div>
                    <div class="category-info">
                        <h4>系統記錄</h4>
                        <div class="category-size">{{ data_breakdown.logs.size }} ({{ data_breakdown.logs.percentage }}%)</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 管理操作 -->
        <div class="management-actions">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">🛠️ 管理操作</h2>
            <div class="action-grid">
                <button class="action-card cleanup-safe" onclick="safeCleanup()">
                    <h3>🧹 安全清理</h3>
                    <p>清理臨時檔案和過期快取<br>預計釋放：{{ cleanup_estimates.safe }}MB</p>
                </button>
                
                <button class="action-card cleanup-aggressive" onclick="aggressiveCleanup()">
                    <h3>🔥 深度清理</h3>
                    <p>清理舊對話和分析結果<br>預計釋放：{{ cleanup_estimates.aggressive }}MB</p>
                </button>
                
                <button class="action-card export-data" onclick="exportAndArchive()">
                    <h3>📦 匯出存檔</h3>
                    <p>匯出重要資料後清理<br>預計釋放：{{ cleanup_estimates.archive }}MB</p>
                </button>
                
                <button class="action-card optimize" onclick="optimizeStorage()">
                    <h3>⚡ 優化儲存</h3>
                    <p>壓縮和重組資料庫<br>預計優化：{{ cleanup_estimates.optimize }}MB</p>
                </button>
            </div>
        </div>
        
        <!-- 警告和提醒 -->
        {% if alerts %}
        <div class="alerts">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">⚠️ 系統提醒</h2>
            {% for alert in alerts %}
            <div class="alert alert-{{ alert.type }}">
                <strong>{{ alert.title }}</strong><br>
                {{ alert.message }}
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <!-- 優化建議 -->
        <div class="recommendations">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">💡 優化建議</h2>
            
            <div class="recommendation-item">
                <div class="recommendation-icon">🔄</div>
                <div class="recommendation-content">
                    <h4>定期清理快取</h4>
                    <p>建議每週清理一次系統快取，可釋放約 {{ recommendations.cache_cleanup }}MB 空間</p>
                    <button class="recommendation-action" onclick="scheduleCleanup()">設定自動清理</button>
                </div>
            </div>
            
            <div class="recommendation-item">
                <div class="recommendation-icon">📚</div>
                <div class="recommendation-content">
                    <h4>存檔舊對話</h4>
                    <p>將 30 天前的對話記錄存檔，保留重要學習資料同時節省空間</p>
                    <button class="recommendation-action" onclick="archiveOldConversations()">開始存檔</button>
                </div>
            </div>
            
            <div class="recommendation-item">
                <div class="recommendation-icon">⚙️</div>
                <div class="recommendation-content">
                    <h4>調整儲存策略</h4>
                    <p>優化資料儲存方式，提升系統效能並減少空間佔用</p>
                    <button class="recommendation-action" onclick="optimizeStrategy()">查看設定</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 儲存空間分布圖表
        const ctx = document.getElementById('storageChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['對話記錄', '分析結果', '快取資料', '匯出檔案', '系統記錄'],
                datasets: [{
                    data: [
                        {{ data_breakdown.conversations.percentage }},
                        {{ data_breakdown.analysis.percentage }},
                        {{ data_breakdown.cache.percentage }},
                        {{ data_breakdown.exports.percentage }},
                        {{ data_breakdown.logs.percentage }}
                    ],
                    backgroundColor: [
                        '#3498db',
                        '#e74c3c',
                        '#f39c12',
                        '#9b59b6',
                        '#2ecc71'
                    ],
                    borderWidth: 3,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
        
        // 管理操作函數
        function safeCleanup() {
            if (confirm('確定要進行安全清理嗎？這將清理臨時檔案和過期快取。')) {
                showProgress('正在進行安全清理...', 'cleanup/safe');
            }
        }
        
        function aggressiveCleanup() {
            if (confirm('警告：深度清理將刪除舊的對話記錄和分析結果，此操作不可恢復。確定繼續嗎？')) {
                showProgress('正在進行深度清理...', 'cleanup/aggressive');
            }
        }
        
        function exportAndArchive() {
            showProgress('正在匯出並存檔資料...', 'export/archive');
        }
        
        function optimizeStorage() {
            showProgress('正在優化儲存結構...', 'optimize/storage');
        }
        
        function scheduleCleanup() {
            showProgress('正在設定自動清理排程...', 'schedule/cleanup');
        }
        
        function archiveOldConversations() {
            showProgress('正在存檔舊對話記錄...', 'archive/conversations');
        }
        
        function optimizeStrategy() {
            window.location.href = '/storage-settings';
        }
        
        function showProgress(message, endpoint) {
            // 顯示進度提示
            const progressDiv = document.createElement('div');
            progressDiv.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                z-index: 1000;
            `;
            progressDiv.innerHTML = `
                <div style="font-size: 1.2em; margin-bottom: 20px;">${message}</div>
                <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.3); border-radius: 2px;">
                    <div style="width: 0%; height: 100%; background: #3498db; border-radius: 2px; transition: width 3s ease;" id="progressBar"></div>
                </div>
            `;
            document.body.appendChild(progressDiv);
            
            // 模擬進度
            setTimeout(() => {
                document.getElementById('progressBar').style.width = '100%';
            }, 100);
            
            // 3秒後移除並重新載入
            setTimeout(() => {
                document.body.removeChild(progressDiv);
                window.location.reload();
            }, 3000);
        }
        
        // 即時更新儲存狀態（每30秒）
        setInterval(() => {
            fetch('/api/storage-status')
                .then(response => response.json())
                .then(data => {
                    // 更新顯示的數據
                    console.log('儲存狀態已更新', data);
                })
                .catch(error => console.error('更新失敗:', error));
        }, 30000);
    </script>
</body>
</html>
"""

# 資料匯出模板
DATA_EXPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 資料匯出中心 - EMI 智能教學助理</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            text-align: center;
        }
        
        .header h1 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 2.5em;
        }
        
        .export-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .export-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        
        .export-card:hover {
            transform: translateY(-5px);
        }
        
        .export-card h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.4em;
            display: flex;
            align-items: center;
        }
        
        .export-card h3::before {
            content: attr(data-icon);
            margin-right: 10px;
            font-size: 1.2em;
        }
        
        .format-options {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 20px 0;
        }
        
        .format-btn {
            padding: 8px 15px;
            border: 2px solid #3498db;
            background: transparent;
            color: #3498db;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9em;
        }
        
        .format-btn:hover {
            background: #3498db;
            color: white;
        }
        
        .format-btn.selected {
            background: #3498db;
            color: white;
        }
        
        .date-range {
            margin: 20px 0;
        }
        
        .date-inputs {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .date-inputs input {
            padding: 10px;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            font-size: 0.9em;
        }
        
        .date-inputs input:focus {
            border-color: #3498db;
            outline: none;
        }
        
        .export-btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
        }
        
        .export-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(52, 152, 219, 0.3);
        }
        
        .progress-section {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .progress-item {
            display: flex;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #3498db;
        }
        
        .progress-icon {
            font-size: 1.5em;
            margin-right: 15px;
        }
        
        .progress-info {
            flex: 1;
        }
        
        .progress-bar {
            background: #ecf0f1;
            border-radius: 10px;
            height: 8px;
            margin: 8px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3498db, #2980b9);
            border-radius: 10px;
            transition: width 0.5s ease;
        }
        
        .status-complete { border-left-color: #27ae60; }
        .status-processing { border-left-color: #f39c12; }
        .status-pending { border-left-color: #95a5a6; }
        .status-error { border-left-color: #e74c3c; }
        
        .download-link {
            background: #27ae60;
            color: white;
            padding: 8px 15px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.9em;
            transition: background 0.3s ease;
        }
        
        .download-link:hover {
            background: #2ecc71;
        }
        
        .history-section {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .history-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 10px;
            transition: background 0.3s ease;
        }
        
        .history-item:hover {
            background: #e9ecef;
        }
        
        .history-info h4 {
            margin-bottom: 5px;
            color: #2c3e50;
        }
        
        .history-meta {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .history-actions {
            display: flex;
            gap: 10px;
        }
        
        .action-btn {
            padding: 6px 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.3s ease;
        }
        
        .btn-download {
            background: #3498db;
            color: white;
        }
        
        .btn-delete {
            background: #e74c3c;
            color: white;
        }
        
        .btn-share {
            background: #f39c12;
            color: white;
        }
        
        .action-btn:hover {
            transform: translateY(-1px);
            opacity: 0.9;
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
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        }
        
        .advanced-options {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .option-group {
            margin-bottom: 20px;
        }
        
        .option-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #2c3e50;
        }
        
        .checkbox-group {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }
        
        .checkbox-item {
            display: flex;
            align-items: center;
        }
        
        .checkbox-item input {
            margin-right: 8px;
        }
    </style>
</head>
<body>
    <a href="/teaching-insights" class="back-btn">← 返回分析後台</a>
    
    <div class="container">
        <div class="header">
            <h1>📊 資料匯出中心</h1>
            <p>匯出教學資料，支援多種格式和自訂選項</p>
        </div>
        
        <!-- 匯出選項 -->
        <div class="export-options">
            <!-- 學生對話記錄 -->
            <div class="export-card">
                <h3 data-icon="💬">學生對話記錄</h3>
                <p>匯出所有學生的對話歷史和互動記錄</p>
                
                <div class="format-options">
                    <button class="format-btn selected" data-format="csv">CSV</button>
                    <button class="format-btn" data-format="excel">Excel</button>
                    <button class="format-btn" data-format="json">JSON</button>
                    <button class="format-btn" data-format="pdf">PDF</button>
                </div>
                
                <div class="date-range">
                    <label>日期範圍：</label>
                    <div class="date-inputs">
                        <input type="date" id="conversations-start" value="{{ default_dates.month_ago }}">
                        <span>至</span>
                        <input type="date" id="conversations-end" value="{{ default_dates.today }}">
                    </div>
                </div>
                
                <button class="export-btn" onclick="exportData('conversations')">
                    匯出對話記錄
                </button>
            </div>
            
            <!-- 學習分析報告 -->
            <div class="export-card">
                <h3 data-icon="📈">學習分析報告</h3>
                <p>匯出學生學習進度和參與度分析</p>
                
                <div class="format-options">
                    <button class="format-btn selected" data-format="pdf">PDF</button>
                    <button class="format-btn" data-format="excel">Excel</button>
                    <button class="format-btn" data-format="pptx">PowerPoint</button>
                </div>
                
                <div class="date-range">
                    <label>分析期間：</label>
                    <div class="date-inputs">
                        <input type="date" id="analysis-start" value="{{ default_dates.semester_start }}">
                        <span>至</span>
                        <input type="date" id="analysis-end" value="{{ default_dates.today }}">
                    </div>
                </div>
                
                <button class="export-btn" onclick="exportData('analysis')">
                    匯出分析報告
                </button>
            </div>
            
            <!-- 教學成效統計 -->
            <div class="export-card">
                <h3 data-icon="🎯">教學成效統計</h3>
                <p>匯出課程整體成效和改進建議</p>
                
                <div class="format-options">
                    <button class="format-btn selected" data-format="excel">Excel</button>
                    <button class="format-btn" data-format="csv">CSV</button>
                    <button class="format-btn" data-format="json">JSON</button>
                </div>
                
                <div class="date-range">
                    <label>統計期間：</label>
                    <div class="date-inputs">
                        <input type="date" id="effectiveness-start" value="{{ default_dates.semester_start }}">
                        <span>至</span>
                        <input type="date" id="effectiveness-end" value="{{ default_dates.today }}">
                    </div>
                </div>
                
                <button class="export-btn" onclick="exportData('effectiveness')">
                    匯出成效統計
                </button>
            </div>
            
            <!-- 完整資料備份 -->
            <div class="export-card">
                <h3 data-icon="💾">完整資料備份</h3>
                <p>匯出系統所有資料作為完整備份</p>
                
                <div class="format-options">
                    <button class="format-btn selected" data-format="zip">ZIP 壓縮檔</button>
                    <button class="format-btn" data-format="sql">SQL 備份</button>
                </div>
                
                <div style="margin: 20px 0; padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 5px;">
                    <strong>注意：</strong>完整備份可能需要較長時間，建議在系統閒置時進行。
                </div>
                
                <button class="export-btn" onclick="exportData('full_backup')">
                    開始完整備份
                </button>
            </div>
        </div>
        
        <!-- 進階選項 -->
        <div class="advanced-options">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">⚙️ 進階匯出選項</h2>
            
            <div class="option-group">
                <label>資料篩選：</label>
                <div class="checkbox-group">
                    <div class="checkbox-item">
                        <input type="checkbox" id="filter-active" checked>
                        <label for="filter-active">僅活躍學生</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="filter-complete" checked>
                        <label for="filter-complete">完整對話記錄</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="filter-analysis">
                        <label for="filter-analysis">包含 AI 分析</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="filter-metadata">
                        <label for="filter-metadata">包含元資料</label>
                    </div>
                </div>
            </div>
            
            <div class="option-group">
                <label>匯出格式設定：</label>
                <div class="checkbox-group">
                    <div class="checkbox-item">
                        <input type="checkbox" id="format-timestamps" checked>
                        <label for="format-timestamps">包含時間戳記</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="format-charts">
                        <label for="format-charts">包含圖表</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="format-summary" checked>
                        <label for="format-summary">包含摘要</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="format-compress">
                        <label for="format-compress">壓縮檔案</label>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 匯出進度 -->
        <div class="progress-section">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">🔄 匯出進度</h2>
            
            {% if export_jobs %}
            {% for job in export_jobs %}
            <div class="progress-item status-{{ job.status }}">
                <div class="progress-icon">
                    {% if job.status == 'complete' %}✅
                    {% elif job.status == 'processing' %}⏳
                    {% elif job.status == 'error' %}❌
                    {% else %}⏸️{% endif %}
                </div>
                <div class="progress-info">
                    <h4>{{ job.name }}</h4>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ job.progress }}%;"></div>
                    </div>
                    <div style="font-size: 0.9em; color: #7f8c8d;">
                        {{ job.description }} - {{ job.progress }}%
                    </div>
                </div>
                {% if job.status == 'complete' %}
                <a href="{{ job.download_url }}" class="download-link">下載</a>
                {% endif %}
            </div>
            {% endfor %}
            {% else %}
            <div style="text-align: center; color: #7f8c8d; padding: 40px;">
                目前沒有進行中的匯出作業
            </div>
            {% endif %}
        </div>
        
        <!-- 匯出歷史 -->
        <div class="history-section">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">📚 匯出歷史</h2>
            
            {% if export_history %}
            {% for item in export_history %}
            <div class="history-item">
                <div class="history-info">
                    <h4>{{ item.name }}</h4>
                    <div class="history-meta">
                        {{ item.created_at.strftime('%Y-%m-%d %H:%M') }} | 
                        {{ item.file_size }} | 
                        {{ item.format.upper() }}
                    </div>
                </div>
                <div class="history-actions">
                    {% if item.available %}
                    <button class="action-btn btn-download" onclick="downloadFile('{{ item.file_path }}')">
                        下載
                    </button>
                    <button class="action-btn btn-share" onclick="shareFile('{{ item.id }}')">
                        分享
                    </button>
                    {% endif %}
                    <button class="action-btn btn-delete" onclick="deleteFile('{{ item.id }}')">
                        刪除
                    </button>
                </div>
            </div>
            {% endfor %}
            {% else %}
            <div style="text-align: center; color: #7f8c8d; padding: 40px;">
                尚未有匯出記錄
            </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        // 格式選擇
        document.querySelectorAll('.format-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                // 移除同組其他按鈕的選中狀態
                this.parentNode.querySelectorAll('.format-btn').forEach(b => b.classList.remove('selected'));
                // 選中當前按鈕
                this.classList.add('selected');
            });
        });
        
        // 匯出資料
        function exportData(type) {
            const card = event.target.closest('.export-card');
            const format = card.querySelector('.format-btn.selected').dataset.format;
            const startDate = card.querySelector('input[type="date"]:first-of-type').value;
            const endDate = card.querySelector('input[type="date"]:last-of-type').value;
            
            // 收集進階選項
            const filters = {
                active_only: document.getElementById('filter-active').checked,
                complete_only: document.getElementById('filter-complete').checked,
                include_analysis: document.getElementById('filter-analysis').checked,
                include_metadata: document.getElementById('filter-metadata').checked,
                include_timestamps: document.getElementById('format-timestamps').checked,
                include_charts: document.getElementById('format-charts').checked,
                include_summary: document.getElementById('format-summary').checked,
                compress: document.getElementById('format-compress').checked
            };
            
            // 顯示進度提示
            showExportProgress(`正在準備 ${getTypeName(type)} 匯出...`);
            
            // 發送匯出請求
            fetch('/api/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: type,
                    format: format,
                    start_date: startDate,
                    end_date: endDate,
                    filters: filters
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showSuccess(`${getTypeName(type)} 匯出已開始，請在進度區域查看狀態`);
                    // 重新載入頁面以更新進度
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    showError(`匯出失敗：${data.error}`);
                }
            })
            .catch(error => {
                showError(`匯出過程發生錯誤：${error.message}`);
            });
        }
        
        function getTypeName(type) {
            const names = {
                'conversations': '對話記錄',
                'analysis': '分析報告',
                'effectiveness': '成效統計',
                'full_backup': '完整備份'
            };
            return names[type] || type;
        }
        
        function showExportProgress(message) {
            const progressDiv = document.createElement('div');
            progressDiv.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                z-index: 1000;
            `;
            progressDiv.innerHTML = `
                <div style="font-size: 1.2em; margin-bottom: 20px;">${message}</div>
                <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.3); border-radius: 2px;">
                    <div style="width: 0%; height: 100%; background: #f093fb; border-radius: 2px; animation: loading 2s ease-in-out infinite;" id="exportProgressBar"></div>
                </div>
                <style>
                @keyframes loading {
                    0%, 100% { width: 0%; }
                    50% { width: 100%; }
                }
                </style>
            `;
            document.body.appendChild(progressDiv);
            
            // 2秒後移除
            setTimeout(() => {
                if (document.body.contains(progressDiv)) {
                    document.body.removeChild(progressDiv);
                }
            }, 2000);
        }
        
        function showSuccess(message) {
            showNotification(message, 'success');
        }
        
        function showError(message) {
            showNotification(message, 'error');
        }
        
        function showNotification(message, type) {
            const notification = document.createElement('div');
            const color = type === 'success' ? '#27ae60' : '#e74c3c';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${color};
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                z-index: 1001;
                max-width: 300px;
                animation: slideIn 0.3s ease;
            `;
            notification.innerHTML = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 4000);
        }
        
        function downloadFile(filePath) {
            window.open(`/api/download/${encodeURIComponent(filePath)}`, '_blank');
        }
        
        function shareFile(fileId) {
            // 生成分享連結
            const shareUrl = `${window.location.origin}/api/share/${fileId}`;
            navigator.clipboard.writeText(shareUrl).then(() => {
                showSuccess('分享連結已複製到剪貼簿');
            }).catch(() => {
                prompt('分享連結：', shareUrl);
            });
        }
        
        function deleteFile(fileId) {
            if (confirm('確定要刪除這個檔案嗎？此操作無法復原。')) {
                fetch(`/api/export/${fileId}`, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showSuccess('檔案已刪除');
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        showError('刪除失敗：' + data.error);
                    }
                })
                .catch(error => {
                    showError('刪除過程發生錯誤');
                });
            }
        }
        
        // 定期更新進度
        setInterval(() => {
            fetch('/api/export-status')
                .then(response => response.json())
                .then(data => {
                    // 更新進度條
                    data.jobs.forEach(job => {
                        const progressBar = document.querySelector(`[data-job-id="${job.id}"] .progress-fill`);
                        if (progressBar) {
                            progressBar.style.width = `${job.progress}%`;
                        }
                    });
                })
                .catch(error => console.error('更新進度失敗:', error));
        }, 5000);
    </script>
</body>
</html>
"""

# 模板管理工具函數
def get_template(template_name):
    """取得指定模板"""
    templates = {
        'storage_management.html': STORAGE_MANAGEMENT_TEMPLATE,
        'data_export.html': DATA_EXPORT_TEMPLATE,
    }
    return templates.get(template_name, '<h1>模板未找到</h1>')

# 匯出所有模板
__all__ = [
    'STORAGE_MANAGEMENT_TEMPLATE',
    'DATA_EXPORT_TEMPLATE',
    'get_template'
]
