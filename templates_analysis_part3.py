# templates_analysis_part3.py - 學習建議模板（完整版）

# 學習建議模板
LEARNING_RECOMMENDATIONS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 個人化學習建議 - EMI 智能教學助理</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
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
            font-size: 2.2em;
        }
        
        .filter-panel {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            align-items: end;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
        }
        
        .filter-group label {
            margin-bottom: 8px;
            font-weight: 500;
            color: #2c3e50;
        }
        
        .filter-group select {
            padding: 10px;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            font-size: 0.9em;
        }
        
        .filter-group select:focus {
            border-color: #a8edea;
            outline: none;
        }
        
        .generate-btn {
            padding: 12px 25px;
            background: linear-gradient(135deg, #a8edea, #fed6e3);
            color: #2c3e50;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .generate-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(168, 237, 234, 0.3);
        }
        
        .overview-panel {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .overview-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .overview-item {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 10px;
            border-left: 4px solid #a8edea;
        }
        
        .overview-value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
        }
        
        .overview-label {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .recommendations-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
            gap: 25px;
        }
        
        .recommendation-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
            border-left: 5px solid;
        }
        
        .recommendation-card:hover {
            transform: translateY(-5px);
        }
        
        .card-grammar { border-left-color: #3498db; }
        .card-vocabulary { border-left-color: #27ae60; }
        .card-pronunciation { border-left-color: #f39c12; }
        .card-culture { border-left-color: #e74c3c; }
        .card-general { border-left-color: #9b59b6; }
        
        .recommendation-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }
        
        .recommendation-title {
            font-size: 1.2em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .recommendation-student {
            font-size: 0.9em;
            color: #7f8c8d;
        }
        
        .priority-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }
        
        .priority-high { background: #ffebee; color: #c62828; }
        .priority-medium { background: #fff3e0; color: #ef6c00; }
        .priority-low { background: #e8f5e8; color: #2e7d32; }
        
        .recommendation-content {
            color: #555;
            line-height: 1.7;
            margin-bottom: 20px;
        }
        
        .learning-goals {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #a8edea;
        }
        
        .learning-goals h4 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 0.95em;
        }
        
        .goals-list {
            list-style: none;
            padding: 0;
        }
        
        .goals-list li {
            margin-bottom: 8px;
            color: #666;
            font-size: 0.9em;
            padding-left: 20px;
            position: relative;
        }
        
        .goals-list li::before {
            content: '✓';
            position: absolute;
            left: 0;
            color: #27ae60;
            font-weight: bold;
        }
        
        .action-plan {
            background: linear-gradient(135deg, #e3f2fd, #f3e5f5);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        
        .action-plan h4 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 0.95em;
        }
        
        .action-steps {
            list-style: none;
            padding: 0;
            counter-reset: step-counter;
        }
        
        .action-steps li {
            margin-bottom: 8px;
            color: #666;
            font-size: 0.9em;
            padding-left: 25px;
            position: relative;
        }
        
        .action-steps li::before {
            content: counter(step-counter);
            counter-increment: step-counter;
            position: absolute;
            left: 0;
            background: #3498db;
            color: white;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7em;
            font-weight: bold;
        }
        
        .recommendation-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .action-btn {
            padding: 8px 16px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.3s ease;
        }
        
        .btn-implement { background: #27ae60; color: white; }
        .btn-details { background: #3498db; color: white; }
        .btn-progress { background: #f39c12; color: white; }
        
        .action-btn:hover {
            transform: translateY(-1px);
            opacity: 0.9;
        }
        
        .progress-tracking {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            margin-top: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .progress-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #a8edea;
        }
        
        .progress-info h4 {
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .progress-meta {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .progress-bar {
            width: 200px;
            height: 8px;
            background: #ecf0f1;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #a8edea, #fed6e3);
            border-radius: 4px;
            transition: width 0.5s ease;
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
        
        @media (max-width: 768px) {
            .recommendations-container {
                grid-template-columns: 1fr;
            }
            
            .filter-grid {
                grid-template-columns: 1fr;
            }
            
            .overview-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .progress-item {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .progress-bar {
                width: 100%;
                margin-top: 10px;
            }
        }
    </style>
</head>
<body>
    <a href="/teaching-insights" class="back-btn">← 返回分析後台</a>
    
    <div class="container">
        <div class="header">
            <h1>🎯 個人化學習建議</h1>
            <p>基於 AI 分析為每位學生提供客製化學習路徑</p>
        </div>
        
        <!-- 篩選面板 -->
        <div class="filter-panel">
            <div class="filter-grid">
                <div class="filter-group">
                    <label for="studentFilter">學生篩選</label>
                    <select id="studentFilter">
                        <option value="all" selected>所有學生</option>
                        <option value="high-priority">高優先級</option>
                        <option value="needs-attention">需要關注</option>
                        <option value="progressing">進步中</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <label for="categoryFilter">學習領域</label>
                    <select id="categoryFilter">
                        <option value="all" selected>全部領域</option>
                        <option value="grammar">文法</option>
                        <option value="vocabulary">詞彙</option>
                        <option value="pronunciation">發音</option>
                        <option value="culture">文化</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <label for="priorityFilter">優先級</label>
                    <select id="priorityFilter">
                        <option value="all" selected>所有優先級</option>
                        <option value="high">高</option>
                        <option value="medium">中</option>
                        <option value="low">低</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <button class="generate-btn" onclick="updateRecommendations()">
                        🔄 更新建議
                    </button>
                </div>
            </div>
        </div>
        
        <!-- 總覽面板 -->
        <div class="overview-panel">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">📊 學習建議總覽</h2>
            <div class="overview-grid">
                <div class="overview-item">
                    <div class="overview-value">{{ overview.total_recommendations or 24 }}</div>
                    <div class="overview-label">待實施建議</div>
                </div>
                <div class="overview-item">
                    <div class="overview-value">{{ overview.high_priority or 8 }}</div>
                    <div class="overview-label">高優先級建議</div>
                </div>
                <div class="overview-item">
                    <div class="overview-value">{{ overview.in_progress or 12 }}</div>
                    <div class="overview-label">進行中建議</div>
                </div>
                <div class="overview-item">
                    <div class="overview-value">{{ overview.completed_this_week or 15 }}</div>
                    <div class="overview-label">本週完成</div>
                </div>
            </div>
        </div>
        
        <!-- 學習建議卡片 -->
        <div class="recommendations-container" id="recommendationsContainer">
            <!-- 示範建議卡片 -->
            <div class="recommendation-card card-grammar">
                <div class="recommendation-header">
                    <div>
                        <div class="recommendation-title">強化現在完成式理解</div>
                        <div class="recommendation-student">
                            學生：王小明 | 領域：文法
                        </div>
                    </div>
                    <span class="priority-badge priority-high">高</span>
                </div>
                
                <div class="recommendation-content">
                    根據對話分析，王小明對現在完成式的時間概念理解不夠清晰，經常與過去式混淆。建議透過時間軸視覺化和實際情境練習來加強理解。
                </div>
                
                <div class="learning-goals">
                    <h4>🎯 學習目標</h4>
                    <ul class="goals-list">
                        <li>正確區分現在完成式與過去式的使用時機</li>
                        <li>掌握 have/has + 過去分詞的結構</li>
                        <li>能在實際對話中流暢使用現在完成式</li>
                    </ul>
                </div>
                
                <div class="action-plan">
                    <h4>📋 行動計畫</h4>
                    <ol class="action-steps">
                        <li>提供時間軸圖解說明時態差異</li>
                        <li>設計情境對話練習</li>
                        <li>安排每日5分鐘結構練習</li>
                        <li>進行週末口語應用測試</li>
                    </ol>
                </div>
                
                <div class="recommendation-actions">
                    <button class="action-btn btn-implement" onclick="implementRecommendation('demo1')">
                        ✅ 實施建議
                    </button>
                    <button class="action-btn btn-details" onclick="viewDetails('demo1')">
                        📋 查看詳情
                    </button>
                    <button class="action-btn btn-progress" onclick="trackProgress('demo1')">
                        📈 追蹤進度
                    </button>
                </div>
            </div>
            
            <div class="recommendation-card card-vocabulary">
                <div class="recommendation-header">
                    <div>
                        <div class="recommendation-title">擴展商業詞彙量</div>
                        <div class="recommendation-student">
                            學生：李小華 | 領域：詞彙
                        </div>
                    </div>
                    <span class="priority-badge priority-medium">中</span>
                </div>
                
                <div class="recommendation-content">
                    李小華在商業情境討論中表現積極，但缺乏足夠的專業詞彙支撐。建議系統性地學習商業英文詞彙，並透過實際案例加深印象。
                </div>
                
                <div class="learning-goals">
                    <h4>🎯 學習目標</h4>
                    <ul class="goals-list">
                        <li>掌握100個核心商業詞彙</li>
                        <li>理解正式與非正式商業用語的差異</li>
                        <li>能在模擬商業情境中準確使用詞彙</li>
                    </ul>
                </div>
                
                <div class="action-plan">
                    <h4>📋 行動計畫</h4>
                    <ol class="action-steps">
                        <li>每週學習20個新商業詞彙</li>
                        <li>製作詞彙卡片進行複習</li>
                        <li>參與商業情境角色扮演</li>
                        <li>撰寫商業email練習</li>
                    </ol>
                </div>
                
                <div class="recommendation-actions">
                    <button class="action-btn btn-implement" onclick="implementRecommendation('demo2')">
                        ✅ 實施建議
                    </button>
                    <button class="action-btn btn-details" onclick="viewDetails('demo2')">
                        📋 查看詳情
                    </button>
                    <button class="action-btn btn-progress" onclick="trackProgress('demo2')">
                        📈 追蹤進度
                    </button>
                </div>
            </div>
            
            <div class="recommendation-card card-pronunciation">
                <div class="recommendation-header">
                    <div>
                        <div class="recommendation-title">改善發音清晰度</div>
                        <div class="recommendation-student">
                            學生：張美玲 | 領域：發音
                        </div>
                    </div>
                    <span class="priority-badge priority-high">高</span>
                </div>
                
                <div class="recommendation-content">
                    張美玲在口語表達上較為保守，主要是因為對自己的發音缺乏信心。建議透過系統性的發音訓練和錄音練習來提升發音準確度。
                </div>
                
                <div class="learning-goals">
                    <h4>🎯 學習目標</h4>
                    <ul class="goals-list">
                        <li>掌握英文音標系統</li>
                        <li>改善常見發音錯誤</li>
                        <li>提升口語表達信心</li>
                    </ul>
                </div>
                
                <div class="action-plan">
                    <h4>📋 行動計畫</h4>
                    <ol class="action-steps">
                        <li>進行發音診斷測試</li>
                        <li>每日10分鐘音標練習</li>
                        <li>錄音跟讀標準發音</li>
                        <li>參加小組口語練習</li>
                    </ol>
                </div>
                
                <div class="recommendation-actions">
                    <button class="action-btn btn-implement" onclick="implementRecommendation('demo3')">
                        ✅ 實施建議
                    </button>
                    <button class="action-btn btn-details" onclick="viewDetails('demo3')">
                        📋 查看詳情
                    </button>
                    <button class="action-btn btn-progress" onclick="trackProgress('demo3')">
                        📈 追蹤進度
                    </button>
                </div>
            </div>
        </div>
        
        <!-- 進度追蹤面板 -->
        <div class="progress-tracking">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">📈 實施進度追蹤</h2>
            
            <div class="progress-item">
                <div class="progress-info">
                    <h4>強化現在完成式理解</h4>
                    <div class="progress-meta">
                        王小明 | 開始日期：2024-03-10
                    </div>
                </div>
                <div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 65%;"></div>
                    </div>
                    <div style="text-align: center; margin-top: 5px; font-size: 0.8em; color: #7f8c8d;">
                        65%
                    </div>
                </div>
            </div>
            
            <div class="progress-item">
                <div class="progress-info">
                    <h4>擴展商業詞彙量</h4>
                    <div class="progress-meta">
                        李小華 | 開始日期：2024-03-08
                    </div>
                </div>
                <div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 80%;"></div>
                    </div>
                    <div style="text-align: center; margin-top: 5px; font-size: 0.8em; color: #7f8c8d;">
                        80%
                    </div>
                </div>
            </div>
            
            <div class="progress-item">
                <div class="progress-info">
                    <h4>改善發音清晰度</h4>
                    <div class="progress-meta">
                        張美玲 | 開始日期：2024-03-12
                    </div>
                </div>
                <div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 45%;"></div>
                    </div>
                    <div style="text-align: center; margin-top: 5px; font-size: 0.8em; color: #7f8c8d;">
                        45%
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function updateRecommendations() {
            const container = document.getElementById('recommendationsContainer');
            
            // 顯示載入狀態
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #7f8c8d;">正在更新學習建議...</div>';
            
            // 收集篩選選項
            const filters = {
                student: document.getElementById('studentFilter').value,
                category: document.getElementById('categoryFilter').value,
                priority: document.getElementById('priorityFilter').value
            };
            
            // 模擬 API 請求
            setTimeout(() => {
                fetch('/api/update-recommendations', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(filters)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.reload();
                    } else {
                        showError('更新建議失敗：' + data.error);
                    }
                })
                .catch(error => {
                    showError('更新過程發生錯誤');
                    setTimeout(() => window.location.reload(), 2000);
                });
            }, 2000);
        }
        
        function implementRecommendation(recId) {
            if (confirm('確定要開始實施這個學習建議嗎？')) {
                showSuccess('學習建議已加入實施計畫');
                
                // 模擬實施過程
                setTimeout(() => {
                    fetch(`/api/implement-recommendation/${recId}`, {
                        method: 'POST'
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showSuccess('建議實施成功，已開始追蹤進度');
                        }
                    })
                    .catch(error => {
                        showError('實施過程發生錯誤');
                    });
                }, 1000);
            }
        }
        
        function viewDetails(recId) {
            window.open(`/recommendation/${recId}`, '_blank');
        }
        
        function trackProgress(recId) {
            window.location.href = `/progress/${recId}`;
        }
        
        function showSuccess(message) {
            showNotification(message, '#27ae60');
        }
        
        function showError(message) {
            showNotification(message, '#e74c3c');
        }
        
        function showNotification(message, color) {
            const notification = document.createElement('div');
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
        
        // 定期更新進度
        setInterval(() => {
            fetch('/api/progress-status')
                .then(response => response.json())
                .then(data => {
                    // 更新進度條
                    data.progress.forEach(item => {
                        const progressBar = document.querySelector(`[data-progress-id="${item.id}"] .progress-fill`);
                        if (progressBar) {
                            progressBar.style.width = `${item.progress}%`;
                        }
                    });
                })
                .catch(error => console.error('進度更新失敗:', error));
        }, 30000);
    </script>
</body>
</html>
"""

def get_template(template_name):
    """取得模板"""
    templates = {
        'learning_recommendations.html': LEARNING_RECOMMENDATIONS_TEMPLATE,
    }
    return templates.get(template_name, '')

# 匯出
__all__ = ['LEARNING_RECOMMENDATIONS_TEMPLATE', 'get_template']
