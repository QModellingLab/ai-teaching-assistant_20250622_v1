# templates_analysis_part1.py - 修正版（完全移除假資料）

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
        
        .export-buttons {
            margin-top: 15px;
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .export-btn {
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
        
        .export-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        /* 等待狀態樣式 */
        .waiting-state {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 40px;
            margin-bottom: 25px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .waiting-icon {
            font-size: 4em;
            margin-bottom: 20px;
            color: #667eea;
        }
        
        .waiting-title {
            font-size: 2em;
            color: #2c3e50;
            margin-bottom: 15px;
        }
        
        .waiting-desc {
            font-size: 1.1em;
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        
        .setup-steps {
            background: #f8f9ff;
            border-radius: 10px;
            padding: 25px;
            margin: 20px 0;
            text-align: left;
            border-left: 4px solid #667eea;
        }
        
        .setup-steps h3 {
            color: #2c3e50;
            margin-bottom: 15px;
        }
        
        .setup-steps ol {
            padding-left: 20px;
        }
        
        .setup-steps li {
            margin-bottom: 10px;
            color: #555;
            line-height: 1.5;
        }
        
        .check-btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s ease;
        }
        
        .check-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
        }
        
        /* 真實資料狀態樣式 */
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
        
        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .conversation-log {
                grid-column: span 1;
            }
            
            .export-buttons {
                flex-direction: column;
                align-items: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 教師分析後台</h1>
            <p>學生對話分析與學習洞察</p>
            
            <div class="export-buttons">
                <button class="export-btn" onclick="exportConversations()">
                    📥 匯出對話記錄
                </button>
                <button class="export-btn" onclick="exportAnalysis()">
                    📊 匯出分析報告
                </button>
                <button class="export-btn" onclick="showExportOptions()">
                    ⚙️ 進階匯出
                </button>
            </div>
        </div>
        
        {% if real_data_info and not real_data_info.has_real_data %}
        <!-- 等待真實資料狀態 -->
        <div class="waiting-state">
            <div class="waiting-icon">⏳</div>
            <div class="waiting-title">等待學生開始使用 LINE Bot</div>
            <div class="waiting-desc">
                系統已準備就緒，正在等待學生透過 LINE Bot 開始對話。<br>
                一旦有真實對話資料，AI 將立即開始分析並提供教學洞察。
            </div>
            
            <div class="setup-steps">
                <h3>📋 快速設定指南</h3>
                <ol>
                    <li><strong>分享 LINE Bot：</strong>將您的 LINE Bot QR Code 或連結分享給學生</li>
                    <li><strong>鼓勵互動：</strong>請學生開始用英文提問或討論學習內容</li>
                    <li><strong>即時分析：</strong>每次學生發送訊息，AI 都會自動分析學習模式</li>
                    <li><strong>查看洞察：</strong>回到此頁面查看即時生成的教學分析</li>
                </ol>
            </div>
            
            <button class="check-btn" onclick="checkForRealData()">
                🔄 檢查是否有新的學生資料
            </button>
        </div>
        {% else %}
        <!-- 有真實資料時的分析顯示 -->
        <div class="dashboard-grid">
            <div class="card">
                <h2>🎯 學習困難點分析</h2>
                <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                    📊 基於真實學生對話的 AI 分析結果
                </p>
                
                {% if category_stats and category_stats.total_questions > 0 %}
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{{ category_stats.grammar_questions }}</div>
                            <div>文法問題</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ category_stats.vocabulary_questions }}</div>
                            <div>詞彙問題</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ category_stats.pronunciation_questions }}</div>
                            <div>發音問題</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ category_stats.cultural_questions }}</div>
                            <div>文化問題</div>
                        </div>
                    </div>
                    <p style="margin-top: 15px; color: #666; font-size: 0.9em;">
                        💡 基於 {{ category_stats.total_questions }} 個真實學生問題的分析
                    </p>
                {% else %}
                    <div class="no-data-message">
                        <p>📊 尚無學生問題資料</p>
                        <p>當學生開始提問時，AI 會自動分析困難點</p>
                    </div>
                {% endif %}
            </div>
            
            <div class="card">
                <h2>⭐ 參與度分析</h2>
                <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                    📈 真實學生參與情況統計
                </p>
                
                {% if engagement_analysis and engagement_analysis.total_real_students > 0 %}
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{{ engagement_analysis.total_real_students }}</div>
                            <div>真實學生</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ engagement_analysis.daily_average }}</div>
                            <div>平均參與度</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ engagement_analysis.recent_messages }}</div>
                            <div>本週訊息</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ engagement_analysis.weekly_trend }}%</div>
                            <div>週趨勢</div>
                        </div>
                    </div>
                {% else %}
                    <div class="no-data-message">
                        <p>📈 尚無參與度資料</p>
                        <p>等待學生開始互動以生成參與度分析</p>
                    </div>
                {% endif %}
            </div>
        </div>
        
        <!-- 學生對話記錄 -->
        <div class="card conversation-log">
            <h2>💬 真實學生對話記錄</h2>
            
            {% if students and students|length > 0 %}
                {% for student in students %}
                <div class="conversation-item">
                    <div class="conversation-meta">
                        <span><strong>{{ student.name }}</strong></span>
                        <span>參與度: {{ student.engagement }}% | 問題數: {{ student.questions_count }}</span>
                    </div>
                    
                    <div class="student-message">
                        <strong>學生資料:</strong> 總訊息 {{ student.total_messages }} 則，參與度 {{ student.engagement }}%
                    </div>
                    
                    <div class="ai-analysis">
                        <strong>AI分析:</strong>
                        <ul>
                            <li><strong>表現等級:</strong> {{ student.performance_level }}</li>
                            <li><strong>互動頻率:</strong> {{ student.total_messages }} 則訊息</li>
                            <li><strong>學習狀態:</strong> 
                                {% if student.engagement >= 80 %}積極參與
                                {% elif student.engagement >= 60 %}適度參與
                                {% elif student.engagement >= 40 %}需要鼓勵
                                {% else %}需要關注{% endif %}
                            </li>
                        </ul>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-data-message">
                    <p>💬 尚無學生對話記錄</p>
                    <p>當學生開始使用 LINE Bot 對話時，記錄將出現在這裡</p>
                </div>
            {% endif %}
        </div>
        {% endif %}
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
                        alert('🎉 發現新的學生資料！頁面將重新載入以顯示分析結果。');
                        window.location.reload();
                    } else {
                        alert('📊 尚未偵測到學生使用 LINE Bot。\\n請確認學生已開始與 AI 對話。');
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('檢查錯誤:', error);
                    alert('檢查過程發生錯誤，請稍後再試。');
                    btn.textContent = originalText;
                    btn.disabled = false;
                });
        }
        
        function exportConversations() {
            alert('📥 對話記錄匯出功能開發中...');
        }
        
        function exportAnalysis() {
            alert('📊 分析報告匯出功能開發中...');
        }
        
        function showExportOptions() {
            alert('⚙️ 進階匯出選項開發中...');
        }
        
        // 自動檢查真實資料（每30秒）
        {% if real_data_info and not real_data_info.has_real_data %}
        setInterval(() => {
            fetch('/api/dashboard-stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.stats.real_students > 0) {
                        if (confirm('🎉 偵測到新的學生資料！是否重新載入頁面查看分析結果？')) {
                            window.location.reload();
                        }
                    }
                })
                .catch(error => console.error('自動檢查失敗:', error));
        }, 30000);
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
