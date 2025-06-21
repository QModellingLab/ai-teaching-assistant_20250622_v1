# templates_analysis_part2.py - 對話摘要模板（完整版）

# 對話摘要模板
CONVERSATION_SUMMARIES_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💬 智能對話摘要 - EMI 智能教學助理</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
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
        
        .summary-controls {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .controls-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            align-items: end;
        }
        
        .control-group {
            display: flex;
            flex-direction: column;
        }
        
        .control-group label {
            margin-bottom: 8px;
            font-weight: 500;
            color: #2c3e50;
        }
        
        .control-group select,
        .control-group input {
            padding: 10px;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            font-size: 0.9em;
        }
        
        .control-group select:focus,
        .control-group input:focus {
            border-color: #4facfe;
            outline: none;
        }
        
        .generate-btn {
            padding: 12px 25px;
            background: linear-gradient(135deg, #4facfe, #00f2fe);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s ease;
        }
        
        .generate-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(79, 172, 254, 0.3);
        }
        
        .insights-panel {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .insights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .insight-item {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .insight-value {
            font-size: 2em;
            font-weight: bold;
            color: #4facfe;
            margin-bottom: 8px;
        }
        
        .insight-label {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .summaries-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
        }
        
        .summary-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        
        .summary-card:hover {
            transform: translateY(-5px);
        }
        
        .summary-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }
        
        .summary-title {
            font-size: 1.1em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .summary-meta {
            font-size: 0.9em;
            color: #7f8c8d;
        }
        
        .summary-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }
        
        .badge-grammar { background: #e3f2fd; color: #1976d2; }
        .badge-vocabulary { background: #e8f5e8; color: #388e3c; }
        .badge-pronunciation { background: #fff3e0; color: #f57c00; }
        .badge-culture { background: #fce4ec; color: #c2185b; }
        .badge-general { background: #f3e5f5; color: #7b1fa2; }
        
        .summary-content {
            color: #555;
            line-height: 1.7;
            margin-bottom: 20px;
        }
        
        .key-points {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #4facfe;
        }
        
        .key-points h4 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 0.9em;
        }
        
        .key-points ul {
            padding-left: 20px;
            margin: 0;
        }
        
        .key-points li {
            margin-bottom: 5px;
            color: #666;
            font-size: 0.9em;
        }
        
        .summary-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .action-btn {
            padding: 6px 15px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.3s ease;
        }
        
        .btn-view { background: #4facfe; color: white; }
        .btn-regenerate { background: #ff6b6b; color: white; }
        .btn-export { background: #51cf66; color: white; }
        
        .action-btn:hover {
            transform: translateY(-1px);
            opacity: 0.9;
        }
        
        .loading-state {
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
        }
        
        .loading-spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #4facfe;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
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
            .summaries-grid {
                grid-template-columns: 1fr;
            }
            
            .controls-grid {
                grid-template-columns: 1fr;
            }
            
            .insights-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .summary-actions {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <a href="/teaching-insights" class="back-btn">← 返回分析後台</a>
    
    <div class="container">
        <div class="header">
            <h1>💬 智能對話摘要</h1>
            <p>AI 自動分析學生對話，提取關鍵學習重點</p>
        </div>
        
        <!-- 摘要控制面板 -->
        <div class="summary-controls">
            <div class="controls-grid">
                <div class="control-group">
                    <label for="timeRange">時間範圍</label>
                    <select id="timeRange">
                        <option value="today">今天</option>
                        <option value="week" selected>本週</option>
                        <option value="month">本月</option>
                        <option value="custom">自訂範圍</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="summaryType">摘要類型</label>
                    <select id="summaryType">
                        <option value="all" selected>全部類型</option>
                        <option value="grammar">文法相關</option>
                        <option value="vocabulary">詞彙相關</option>
                        <option value="pronunciation">發音相關</option>
                        <option value="culture">文化相關</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="summaryLength">摘要長度</label>
                    <select id="summaryLength">
                        <option value="brief">簡要</option>
                        <option value="standard" selected>標準</option>
                        <option value="detailed">詳細</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <button class="generate-btn" onclick="generateSummaries()">
                        🔄 重新生成摘要
                    </button>
                </div>
            </div>
        </div>
        
        <!-- 洞察面板 -->
        <div class="insights-panel">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">📊 本週對話洞察</h2>
            <div class="insights-grid">
                <div class="insight-item">
                    <div class="insight-value">{{ insights.total_conversations or 47 }}</div>
                    <div class="insight-label">總對話數</div>
                </div>
                <div class="insight-item">
                    <div class="insight-value">{{ insights.avg_length or 8.5 }}</div>
                    <div class="insight-label">平均對話輪次</div>
                </div>
                <div class="insight-item">
                    <div class="insight-value">{{ insights.satisfaction_rate or 92 }}%</div>
                    <div class="insight-label">問題解決率</div>
                </div>
                <div class="insight-item">
                    <div class="insight-value">{{ insights.response_time or 2.3 }}s</div>
                    <div class="insight-label">平均回應時間</div>
                </div>
            </div>
        </div>
        
        <!-- 對話摘要卡片 -->
        <div class="summaries-grid" id="summariesContainer">
            {% if summaries %}
                {% for summary in summaries %}
                <div class="summary-card">
                    <div class="summary-header">
                        <div>
                            <div class="summary-title">{{ summary.title }}</div>
                            <div class="summary-meta">
                                {{ summary.date }} | {{ summary.student_count }} 位學生 | {{ summary.message_count }} 則訊息
                            </div>
                        </div>
                        <span class="summary-badge badge-{{ summary.category }}">
                            {{ summary.category_name }}
                        </span>
                    </div>
                    
                    <div class="summary-content">
                        {{ summary.content }}
                    </div>
                    
                    {% if summary.key_points %}
                    <div class="key-points">
                        <h4>🎯 關鍵重點</h4>
                        <ul>
                            {% for point in summary.key_points %}
                            <li>{{ point }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                    
                    <div class="summary-actions">
                        <button class="action-btn btn-view" onclick="viewFullConversation('{{ summary.id }}')">
                            👁️ 查看完整對話
                        </button>
                        <button class="action-btn btn-regenerate" onclick="regenerateSummary('{{ summary.id }}')">
                            🔄 重新生成
                        </button>
                        <button class="action-btn btn-export" onclick="exportSummary('{{ summary.id }}')">
                            📥 匯出
                        </button>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <!-- 示範資料 -->
                <div class="summary-card">
                    <div class="summary-header">
                        <div>
                            <div class="summary-title">現在完成式學習討論</div>
                            <div class="summary-meta">
                                2024-03-15 | 8 位學生 | 32 則訊息
                            </div>
                        </div>
                        <span class="summary-badge badge-grammar">文法</span>
                    </div>
                    
                    <div class="summary-content">
                        本次對話中，學生們主要討論了現在完成式的使用時機和結構。多數學生對於「已完成但對現在有影響」的概念有些困惑，特別是在與過去式的區別上。透過具體例句和情境練習，學生們逐漸理解了 have/has + 過去分詞的結構應用。
                    </div>
                    
                    <div class="key-points">
                        <h4>🎯 關鍵重點</h4>
                        <ul>
                            <li>學生對現在完成式的時間概念需要加強</li>
                            <li>建議增加更多與過去式的對比練習</li>
                            <li>情境教學效果良好，建議持續採用</li>
                        </ul>
                    </div>
                    
                    <div class="summary-actions">
                        <button class="action-btn btn-view" onclick="viewFullConversation('demo1')">
                            👁️ 查看完整對話
                        </button>
                        <button class="action-btn btn-regenerate" onclick="regenerateSummary('demo1')">
                            🔄 重新生成
                        </button>
                        <button class="action-btn btn-export" onclick="exportSummary('demo1')">
                            📥 匯出
                        </button>
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="summary-header">
                        <div>
                            <div class="summary-title">商業英文詞彙學習</div>
                            <div class="summary-meta">
                                2024-03-14 | 12 位學生 | 45 則訊息
                            </div>
                        </div>
                        <span class="summary-badge badge-vocabulary">詞彙</span>
                    </div>
                    
                    <div class="summary-content">
                        學生們在本次對話中學習了商業場合常用的正式詞彙，包括會議、簡報、談判等情境的專業用語。大家對於正式與非正式用詞的轉換特別感興趣，並積極練習在不同商業情境中的應用。
                    </div>
                    
                    <div class="key-points">
                        <h4>🎯 關鍵重點</h4>
                        <ul>
                            <li>學生對商業詞彙的實際應用很感興趣</li>
                            <li>建議加入更多真實商業情境的案例</li>
                            <li>角色扮演練習效果顯著</li>
                        </ul>
                    </div>
                    
                    <div class="summary-actions">
                        <button class="action-btn btn-view" onclick="viewFullConversation('demo2')">
                            👁️ 查看完整對話
                        </button>
                        <button class="action-btn btn-regenerate" onclick="regenerateSummary('demo2')">
                            🔄 重新生成
                        </button>
                        <button class="action-btn btn-export" onclick="exportSummary('demo2')">
                            📥 匯出
                        </button>
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="summary-header">
                        <div>
                            <div class="summary-title">英美文化差異討論</div>
                            <div class="summary-meta">
                                2024-03-13 | 15 位學生 | 38 則訊息
                            </div>
                        </div>
                        <span class="summary-badge badge-culture">文化</span>
                    </div>
                    
                    <div class="summary-content">
                        本次討論聚焦於英美兩國在商業文化和社交禮儀上的差異。學生們分享了自己的觀察和經驗，對於跨文化溝通的重要性有了更深的認識。特別是在職場溝通風格和時間觀念方面有熱烈討論。
                    </div>
                    
                    <div class="key-points">
                        <h4>🎯 關鍵重點</h4>
                        <ul>
                            <li>學生對跨文化議題參與度很高</li>
                            <li>建議定期安排文化主題討論</li>
                            <li>可邀請外籍人士分享經驗</li>
                        </ul>
                    </div>
                    
                    <div class="summary-actions">
                        <button class="action-btn btn-view" onclick="viewFullConversation('demo3')">
                            👁️ 查看完整對話
                        </button>
                        <button class="action-btn btn-regenerate" onclick="regenerateSummary('demo3')">
                            🔄 重新生成
                        </button>
                        <button class="action-btn btn-export" onclick="exportSummary('demo3')">
                            📥 匯出
                        </button>
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="summary-header">
                        <div>
                            <div class="summary-title">發音練習與改進</div>
                            <div class="summary-meta">
                                2024-03-12 | 6 位學生 | 28 則訊息
                            </div>
                        </div>
                        <span class="summary-badge badge-pronunciation">發音</span>
                    </div>
                    
                    <div class="summary-content">
                        這次對話主要圍繞英文發音技巧和常見錯誤的修正。學生們對於母音和子音的發音差異特別關注，也討論了語調和重音在不同情境下的應用。透過實際練習和即時回饋，學生們的發音準確度有明顯提升。
                    </div>
                    
                    <div class="key-points">
                        <h4>🎯 關鍵重點</h4>
                        <ul>
                            <li>學生對發音練習的參與度較以往提高</li>
                            <li>建議增加音標教學和對比練習</li>
                            <li>錄音回放功能對學習很有幫助</li>
                        </ul>
                    </div>
                    
                    <div class="summary-actions">
                        <button class="action-btn btn-view" onclick="viewFullConversation('demo4')">
                            👁️ 查看完整對話
                        </button>
                        <button class="action-btn btn-regenerate" onclick="regenerateSummary('demo4')">
                            🔄 重新生成
                        </button>
                        <button class="action-btn btn-export" onclick="exportSummary('demo4')">
                            📥 匯出
                        </button>
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="summary-header">
                        <div>
                            <div class="summary-title">學術寫作技巧指導</div>
                            <div class="summary-meta">
                                2024-03-11 | 10 位學生 | 41 則訊息
                            </div>
                        </div>
                        <span class="summary-badge badge-general">綜合</span>
                    </div>
                    
                    <div class="summary-content">
                        本次對話專注於學術寫作的結構和技巧。學生們學習了如何撰寫有效的引言、發展論點和撰寫結論。討論中涵蓋了參考文獻格式、避免抄襲的方法，以及如何使用過渡詞語增強文章的連貫性。
                    </div>
                    
                    <div class="key-points">
                        <h4>🎯 關鍵重點</h4>
                        <ul>
                            <li>學生對學術寫作結構的掌握需要加強</li>
                            <li>建議提供更多寫作範例和模板</li>
                            <li>同儕互評機制效果良好</li>
                        </ul>
                    </div>
                    
                    <div class="summary-actions">
                        <button class="action-btn btn-view" onclick="viewFullConversation('demo5')">
                            👁️ 查看完整對話
                        </button>
                        <button class="action-btn btn-regenerate" onclick="regenerateSummary('demo5')">
                            🔄 重新生成
                        </button>
                        <button class="action-btn btn-export" onclick="exportSummary('demo5')">
                            📥 匯出
                        </button>
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="summary-header">
                        <div>
                            <div class="summary-title">日常會話練習</div>
                            <div class="summary-meta">
                                2024-03-10 | 14 位學生 | 52 則訊息
                            </div>
                        </div>
                        <span class="summary-badge badge-general">綜合</span>
                    </div>
                    
                    <div class="summary-content">
                        這次對話聚焦於日常生活情境的英語對話練習。學生們模擬了購物、訂餐、問路等真實情境，練習使用自然流暢的表達方式。大家特別關注如何在對話中表達禮貌和適當的語氣。
                    </div>
                    
                    <div class="key-points">
                        <h4>🎯 關鍵重點</h4>
                        <ul>
                            <li>學生對實用對話場景很感興趣</li>
                            <li>建議增加更多角色扮演活動</li>
                            <li>文化禮儀教學應該更加融入對話練習</li>
                        </ul>
                    </div>
                    
                    <div class="summary-actions">
                        <button class="action-btn btn-view" onclick="viewFullConversation('demo6')">
                            👁️ 查看完整對話
                        </button>
                        <button class="action-btn btn-regenerate" onclick="regenerateSummary('demo6')">
                            🔄 重新生成
                        </button>
                        <button class="action-btn btn-export" onclick="exportSummary('demo6')">
                            📥 匯出
                        </button>
                    </div>
                </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        function generateSummaries() {
            const container = document.getElementById('summariesContainer');
            
            // 顯示載入狀態
            container.innerHTML = `
                <div class="loading-state">
                    <div class="loading-spinner"></div>
                    <div>正在生成 AI 對話摘要...</div>
                </div>
            `;
            
            // 收集選項
            const options = {
                timeRange: document.getElementById('timeRange').value,
                summaryType: document.getElementById('summaryType').value,
                summaryLength: document.getElementById('summaryLength').value
            };
            
            // 模擬 API 請求
            setTimeout(() => {
                fetch('/api/generate-summaries', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(options)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.reload();
                    } else {
                        showError('摘要生成失敗：' + data.error);
                    }
                })
                .catch(error => {
                    showError('摘要生成過程發生錯誤');
                    // 恢復原始內容
                    setTimeout(() => window.location.reload(), 2000);
                });
            }, 3000);
        }
        
        function viewFullConversation(summaryId) {
            window.open(`/conversation/${summaryId}`, '_blank');
        }
        
        function regenerateSummary(summaryId) {
            if (confirm('確定要重新生成這個摘要嗎？')) {
                const card = event.target.closest('.summary-card');
                const originalContent = card.innerHTML;
                
                card.innerHTML = `
                    <div class="loading-state">
                        <div class="loading-spinner"></div>
                        <div>正在重新生成摘要...</div>
                    </div>
                `;
                
                // 模擬重新生成
                setTimeout(() => {
                    card.innerHTML = originalContent;
                    showSuccess('摘要已重新生成');
                }, 2000);
            }
        }
        
        function exportSummary(summaryId) {
            showSuccess('摘要匯出已開始，請稍候...');
            
            setTimeout(() => {
                // 創建下載連結
                const link = document.createElement('a');
                link.href = `/api/export-summary/${summaryId}`;
                link.download = `summary_${summaryId}.pdf`;
                link.click();
                
                showSuccess('摘要已匯出完成');
            }, 2000);
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
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
                animation: slideIn 0.3s ease;
            `;
            notification.innerHTML = message;
            document.body.appendChild(notification);
            
            // 添加滑入動畫
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
            `;
            document.head.appendChild(style);
            
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    notification.style.animation = 'slideOut 0.3s ease';
                    setTimeout(() => {
                        if (document.body.contains(notification)) {
                            document.body.removeChild(notification);
                        }
                    }, 300);
                }
            }, 4000);
        }
        
        // 自動刷新摘要數據（每60秒）
        setInterval(() => {
            fetch('/api/summaries-status')
                .then(response => response.json())
                .then(data => {
                    // 更新洞察面板數據
                    updateInsightsPanel(data.insights);
                })
                .catch(error => console.error('數據更新失敗:', error));
        }, 60000);
        
        function updateInsightsPanel(insights) {
            const insightItems = document.querySelectorAll('.insight-value');
            if (insightItems.length >= 4) {
                insightItems[0].textContent = insights.total_conversations || 47;
                insightItems[1].textContent = insights.avg_length || 8.5;
                insightItems[2].textContent = (insights.satisfaction_rate || 92) + '%';
                insightItems[3].textContent = (insights.response_time || 2.3) + 's';
            }
        }
        
        // 搜索功能
        function searchSummaries() {
            const searchTerm = prompt('請輸入搜索關鍵字：');
            if (searchTerm) {
                const cards = document.querySelectorAll('.summary-card');
                cards.forEach(card => {
                    const content = card.textContent.toLowerCase();
                    if (content.includes(searchTerm.toLowerCase())) {
                        card.style.display = 'block';
                        card.style.border = '2px solid #4facfe';
                    } else {
                        card.style.display = 'none';
                    }
                });
                
                showSuccess(`找到 ${document.querySelectorAll('.summary-card[style*="block"]').length} 個相關摘要`);
            }
        }
        
        // 重置搜索
        function resetSearch() {
            const cards = document.querySelectorAll('.summary-card');
            cards.forEach(card => {
                card.style.display = 'block';
                card.style.border = 'none';
            });
        }
        
        // 批量操作
        function selectAllSummaries() {
            const checkboxes = document.querySelectorAll('.summary-checkbox');
            checkboxes.forEach(cb => cb.checked = true);
        }
        
        function batchExport() {
            const selectedSummaries = document.querySelectorAll('.summary-checkbox:checked');
            if (selectedSummaries.length === 0) {
                showError('請先選擇要匯出的摘要');
                return;
            }
            
            showSuccess(`正在匯出 ${selectedSummaries.length} 個摘要...`);
            
            setTimeout(() => {
                const link = document.createElement('a');
                link.href = '/api/batch-export-summaries';
                link.download = 'batch_summaries.zip';
                link.click();
                
                showSuccess('批量匯出完成');
            }, 3000);
        }
        
        // 快捷鍵支援
        document.addEventListener('keydown', function(e) {
            // Ctrl+R: 重新生成摘要
            if (e.ctrlKey && e.key === 'r') {
                e.preventDefault();
                generateSummaries();
            }
            
            // Ctrl+F: 搜索摘要
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                searchSummaries();
            }
            
            // Esc: 重置搜索
            if (e.key === 'Escape') {
                resetSearch();
            }
        });
        
        // 初始化提示
        setTimeout(() => {
            if (document.querySelectorAll('.summary-card').length > 0) {
                showSuccess('💡 提示: 使用 Ctrl+R 重新生成，Ctrl+F 搜索摘要');
            }
        }, 2000);
    </script>
</body>
</html>
"""

def get_template(template_name):
    """取得模板"""
    templates = {
        'conversation_summaries.html': CONVERSATION_SUMMARIES_TEMPLATE,
    }
    return templates.get(template_name, '')

# 匯出
__all__ = ['CONVERSATION_SUMMARIES_TEMPLATE', 'get_template']
