# templates_analysis_part1.py - 移除虛擬資料版本（完全專注真實資料）

TEACHING_INSIGHTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 教師分析後台 - EMI 智能教學助理</title>
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
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            color: #333;
            font-size: 2.2em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        
        .admin-buttons {
            margin-top: 15px;
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .admin-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .admin-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .admin-btn.cleanup {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
        }
        
        /* 等待真實資料狀態樣式 */
        .waiting-state {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 60px 40px;
            margin-bottom: 25px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .waiting-icon {
            font-size: 5em;
            margin-bottom: 20px;
            color: #667eea;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 0.7; }
            50% { opacity: 1; }
        }
        
        .waiting-title {
            font-size: 2.2em;
            color: #2c3e50;
            margin-bottom: 15px;
        }
        
        .waiting-desc {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
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
            text-align: center;
            font-size: 1.3em;
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
        
        .status-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .status-item {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #e74c3c;
        }
        
        .status-item.ready {
            border-left-color: #27ae60;
        }
        
        .status-item.waiting {
            border-left-color: #f39c12;
        }
        
        .status-value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .status-label {
            color: #666;
            font-size: 0.9em;
        }
        
        .check-btn {
            background: linear-gradient(135deg, #27ae60, #2ecc71);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1.1em;
            font-weight: 600;
            transition: all 0.3s ease;
            margin-top: 20px;
        }
        
        .check-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(39, 174, 96, 0.3);
        }
        
        /* 有真實資料時的樣式 */
        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-bottom: 25px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.4em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .real-data-badge {
            background: #27ae60;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.7em;
            font-weight: 600;
            margin-left: 10px;
        }
        
        .conversation-log {
            grid-column: span 2;
        }
        
        .conversation-item {
            background: #f8f9ff;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }
        
        .conversation-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            font-size: 0.9em;
            color: #666;
        }
        
        .student-message {
            background: #e3f2fd;
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #2196f3;
        }
        
        .ai-analysis {
            background: #f3e5f5;
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #9c27b0;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .no-data-message {
            text-align: center;
            color: #666;
            padding: 40px;
            background: #f8f9fa;
            border-radius: 10px;
            margin: 20px 0;
        }
        
        .cleanup-notice {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .cleanup-notice.hidden {
            display: none;
        }
        
        .auto-refresh {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px 15px;
            border-radius: 25px;
            font-size: 0.8em;
            color: #666;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .conversation-log {
                grid-column: span 1;
            }
            
            .admin-buttons {
                flex-direction: column;
                align-items: center;
            }
            
            .waiting-state {
                padding: 40px 20px;
            }
            
            .steps-container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 教師分析後台</h1>
            <p>真實學生對話分析與學習洞察</p>
            
            <div class="admin-buttons">
                <a href="/admin/data-status" class="admin-btn">
                    📋 資料狀態
                </a>
                <a href="/admin/cleanup" class="admin-btn cleanup">
                    🧹 清理演示資料
                </a>
                <button class="admin-btn" onclick="refreshData()">
                    🔄 重新整理
                </button>
            </div>
        </div>
        
        <!-- 檢查是否需要清理演示資料 -->
        {% if cleanup_needed %}
        <div class="cleanup-notice" id="cleanupNotice">
            <span style="font-size: 1.2em;">⚠️</span>
            <div>
                <strong>發現演示資料需要清理</strong><br>
                系統中有 {{ cleanup_info.demo_students }} 個演示學生和 {{ cleanup_info.demo_messages }} 則演示訊息，建議清理以確保分析純度。
            </div>
            <a href="/admin/cleanup" style="background: #ff6b6b; color: white; padding: 8px 15px; border-radius: 5px; text-decoration: none; margin-left: auto;">
                立即清理
            </a>
        </div>
        {% endif %}
        
        {% if real_data_info and not real_data_info.has_real_data %}
        <!-- 等待真實資料狀態 -->
        <div class="waiting-state">
            <div class="waiting-icon">📈</div>
            <h2 class="waiting-title">等待真實學生開始對話</h2>
            <p class="waiting-desc">
                系統已準備就緒，正在等待學生透過 LINE Bot 開始對話。<br>
                一旦有真實對話資料，AI 將立即開始分析並提供教學洞察。
            </p>
            
            <div class="setup-guide">
                <h3>🎯 開始收集真實教學資料</h3>
                <div class="steps-container">
                    <div class="step-item">
                        <div class="step-number">1</div>
                        <div class="step-title">確認 LINE Bot 設定</div>
                        <div class="step-desc">
                            檢查 CHANNEL_ACCESS_TOKEN 和 CHANNEL_SECRET 環境變數是否正確設定
                        </div>
                    </div>
                    
                    <div class="step-item">
                        <div class="step-number">2</div>
                        <div class="step-title">分享給學生</div>
                        <div class="step-desc">
                            將 LINE Bot 的 QR Code 或連結分享給您的學生
                        </div>
                    </div>
                    
                    <div class="step-item">
                        <div class="step-number">3</div>
                        <div class="step-title">鼓勵英文對話</div>
                        <div class="step-desc">
                            引導學生用英文提問文法、詞彙、發音或文化相關問題
                        </div>
                    </div>
                    
                    <div class="step-item">
                        <div class="step-number">4</div>
                        <div class="step-title">自動分析開始</div>
                        <div class="step-desc">
                            系統將即時分析對話，識別學習困難點和興趣主題
                        </div>
                    </div>
                </div>
            </div>
            
            <button class="check-btn" onclick="checkForRealData()">
                🔍 檢查是否有新的學生資料
            </button>
        </div>
        
        <!-- 系統準備狀態 -->
        <div class="status-panel">
            <h2 style="margin-bottom: 20px; color: #2c3e50; text-align: center;">🔧 系統準備狀態</h2>
            <div class="status-grid">
                <div class="status-item ready">
                    <div class="status-value">✅</div>
                    <div class="status-label">資料庫已連接</div>
                </div>
                
                <div class="status-item ready">
                    <div class="status-value">✅</div>
                    <div class="status-label">AI 分析引擎準備</div>
                </div>
                
                <div class="status-item waiting">
                    <div class="status-value">⏳</div>
                    <div class="status-label">等待學生對話</div>
                </div>
                
                <div class="status-item waiting">
                    <div class="status-value">{{ real_data_info.total_real_students or 0 }}</div>
                    <div class="status-label">真實學生數</div>
                </div>
            </div>
        </div>
        
        {% else %}
        <!-- 有真實資料時的分析顯示 -->
        <div class="dashboard-grid">
            <div class="card">
                <h2>🎯 學習困難點分析<span class="real-data-badge">真實資料</span></h2>
                <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                    📊 基於 {{ category_stats.total_questions or 0 }} 個真實學生問題的 AI 分析
                </p>
                
                {% if category_stats and category_stats.total_questions > 0 %}
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{{ category_stats.grammar_questions or 0 }}</div>
                            <div>文法問題</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ category_stats.vocabulary_questions or 0 }}</div>
                            <div>詞彙問題</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ category_stats.pronunciation_questions or 0 }}</div>
                            <div>發音問題</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ category_stats.cultural_questions or 0 }}</div>
                            <div>文化問題</div>
                        </div>
                    </div>
                    <p style="margin-top: 15px; color: #27ae60; font-size: 0.9em; font-weight: 600;">
                        ✅ 基於真實學生互動的精準分析
                    </p>
                {% else %}
                    <div class="no-data-message">
                        <p>📊 學生尚未開始提問</p>
                        <p>當真實學生開始提問時，困難點分析將自動出現</p>
                    </div>
                {% endif %}
            </div>
            
            <div class="card">
                <h2>⭐ 真實參與度分析<span class="real-data-badge">真實資料</span></h2>
                <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                    📈 {{ engagement_analysis.total_real_students or 0 }} 位真實學生的參與情況
                </p>
                
                {% if engagement_analysis and engagement_analysis.total_real_students > 0 %}
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{{ engagement_analysis.total_real_students }}</div>
                            <div>真實學生</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ engagement_analysis.daily_average or 0 }}%</div>
                            <div>平均參與度</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ engagement_analysis.recent_messages or 0 }}</div>
                            <div>本週訊息</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ engagement_analysis.weekly_trend or 0 }}%</div>
                            <div>週趨勢</div>
                        </div>
                    </div>
                    <p style="margin-top: 15px; color: #27ae60; font-size: 0.9em; font-weight: 600;">
                        ✅ 排除演示資料的純淨統計
                    </p>
                {% else %}
                    <div class="no-data-message">
                        <p>📈 等待學生參與數據</p>
                        <p>當學生開始互動時，參與度分析將即時更新</p>
                    </div>
                {% endif %}
            </div>
        </div>
        
        <!-- 真實學生對話記錄 -->
        <div class="card conversation-log">
            <h2>💬 真實學生對話記錄<span class="real-data-badge">真實資料</span></h2>
            
            {% if students and students|length > 0 %}
                {% for student in students %}
                <div class="conversation-item">
                    <div class="conversation-meta">
                        <span><strong>{{ student.name }}</strong> (真實學生)</span>
                        <span>參與度: {{ student.engagement }}% | 問題數: {{ student.questions_count }}</span>
                    </div>
                    
                    <div class="student-message">
                        <strong>學生表現:</strong> 總訊息 {{ student.total_messages }} 則，參與度 {{ student.engagement }}%
                    </div>
                    
                    <div class="ai-analysis">
                        <strong>AI 真實分析:</strong>
                        <ul>
                            <li><strong>表現等級:</strong> {{ student.performance_level or student.performance_text or '分析中' }}</li>
                            <li><strong>互動頻率:</strong> {{ student.total_messages }} 則真實訊息</li>
                            <li><strong>學習狀態:</strong> 
                                {% if student.engagement >= 80 %}積極參與
                                {% elif student.engagement >= 60 %}適度參與
                                {% elif student.engagement >= 40 %}需要鼓勵
                                {% else %}需要關注{% endif %}
                            </li>
                            <li><strong>資料來源:</strong> 100% 真實學生互動</li>
                        </ul>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-data-message">
                    <p>💬 等待真實學生對話</p>
                    <p>當學生開始使用 LINE Bot 對話時，記錄將即時出現在這裡</p>
                    <p style="margin-top: 10px; color: #27ae60; font-weight: 600;">
                        ✅ 系統只會顯示真實學生的對話，確保分析品質
                    </p>
                </div>
            {% endif %}
        </div>
        {% endif %}
    </div>
    
    <!-- 自動重新整理指示器 -->
    <div class="auto-refresh" id="autoRefreshIndicator">
        🔄 每30秒自動檢查新資料
    </div>
    
    <script>
        function checkForRealData() {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '🔄 檢查中...';
            btn.disabled = true;
            
            fetch('/api/dashboard-stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.stats.real_students > 0) {
                        showNotification('🎉 發現真實學生資料！頁面將重新載入以顯示分析結果。', 'success');
                        setTimeout(() => window.location.reload(), 2000);
                    } else {
                        showNotification('📊 尚未偵測到真實學生使用 LINE Bot。<br>請確認學生已開始與 AI 對話。', 'info');
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('檢查錯誤:', error);
                    showNotification('檢查過程發生錯誤，請稍後再試。', 'error');
                    btn.textContent = originalText;
                    btn.disabled = false;
                });
        }
        
        function refreshData() {
            showNotification('🔄 正在重新整理資料...', 'info');
            setTimeout(() => window.location.reload(), 1000);
        }
        
        function showNotification(message, type) {
            const colors = {
                'success': '#27ae60',
                'error': '#e74c3c',
                'info': '#3498db',
                'warning': '#f39c12'
            };
            
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${colors[type] || colors.info};
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                z-index: 1001;
                max-width: 350px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
                animation: slideIn 0.3s ease;
            `;
            notification.innerHTML = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    notification.style.animation = 'slideOut 0.3s ease';
                    setTimeout(() => {
                        if (document.body.contains(notification)) {
                            document.body.removeChild(notification);
                        }
                    }, 300);
                }
            }, 5000);
        }
        
        // 自動檢查真實資料（每30秒）
        {% if real_data_info and not real_data_info.has_real_data %}
        let checkCount = 0;
        const maxChecks = 120; // 最多檢查120次（1小時）
        
        const autoCheck = setInterval(() => {
            checkCount++;
            
            fetch('/api/dashboard-stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.stats.real_students > 0) {
                        clearInterval(autoCheck);
                        showNotification('🎉 偵測到真實學生資料！頁面將自動重新載入。', 'success');
                        setTimeout(() => window.location.reload(), 3000);
                    }
                    
                    // 更新指示器
                    const indicator = document.getElementById('autoRefreshIndicator');
                    if (indicator) {
                        indicator.textContent = `🔄 自動檢查中 (${checkCount}/${maxChecks})`;
                    }
                    
                    if (checkCount >= maxChecks) {
                        clearInterval(autoCheck);
                        const indicator = document.getElementById('autoRefreshIndicator');
                        if (indicator) {
                            indicator.textContent = '⏸️ 自動檢查已停止';
                            indicator.style.background = '#f39c12';
                        }
                    }
                })
                .catch(error => {
                    console.error('自動檢查失敗:', error);
                });
        }, 30000);
        {% endif %}
        
        // 隱藏清理通知
        function dismissCleanupNotice() {
            const notice = document.getElementById('cleanupNotice');
            if (notice) {
                notice.classList.add('hidden');
            }
        }
        
        // 添加動畫樣式
        const style = document.createElement('style');
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
        
        // 歡迎訊息（僅在等待狀態顯示）
        {% if real_data_info and not real_data_info.has_real_data %}
        setTimeout(() => {
            showNotification('💡 系統已準備就緒！分享 LINE Bot 給學生即可開始收集真實教學資料。', 'info');
        }, 2000);
        {% endif %}
    </script>
</body>
</html>
"""

def get_template(template_name):
    """取得模板"""
    templates = {
        'teaching_insights.html': TEACHING_INSIGHTS_TEMPLATE,
    }
    return templates.get(template_name, '')

# 匯出
__all__ = ['TEACHING_INSIGHTS_TEMPLATE', 'get_template']
