# templates_analysis_part1.py - 教師分析後台模板（更新版）

# 教師分析後台模板（整合匯出功能）
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
        
        .difficulty-tag {
            background: #ff9800;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-left: 10px;
        }
        
        .interest-tag {
            background: #4caf50;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-left: 5px;
        }
        
        .insight-item {
            background: #fff3e0;
            padding: 12px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 3px solid #ff9800;
        }
        
        .progress-bar {
            background: #e0e0e0;
            border-radius: 10px;
            height: 8px;
            margin: 10px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            background: linear-gradient(90deg, #667eea, #764ba2);
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
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
        
        .filter-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .tab {
            padding: 8px 16px;
            background: #e0e0e0;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .tab.active {
            background: #667eea;
            color: white;
        }
        
        .timestamp {
            color: #999;
            font-size: 0.8em;
        }
        
        /* 匯出彈窗樣式 */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal-content {
            background: white;
            padding: 0;
            border-radius: 15px;
            max-width: 800px;
            width: 95%;
            max-height: 85vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        .modal-header {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-header h3 {
            margin: 0;
            font-size: 1.3em;
        }
        
        .close-btn {
            background: none;
            border: none;
            color: white;
            font-size: 1.5em;
            cursor: pointer;
            padding: 5px;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .close-btn:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .export-tabs {
            display: flex;
            background: #f5f5f5;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .export-tab {
            flex: 1;
            padding: 15px 20px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 0.95em;
            color: #666;
            transition: all 0.3s ease;
        }
        
        .export-tab.active {
            background: white;
            color: #667eea;
            border-bottom: 3px solid #667eea;
        }
        
        .export-tab:hover {
            background: #f0f0f0;
        }
        
        .tab-content {
            display: none;
            padding: 30px;
            overflow-y: auto;
            flex: 1;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .export-section {
            margin-bottom: 0;
            padding: 0;
            background: none;
            border-radius: 0;
        }
        
        .export-section h4 {
            color: #333;
            margin-bottom: 8px;
            font-size: 1.2em;
        }
        
        .section-desc {
            color: #666;
            margin-bottom: 25px;
            font-size: 0.95em;
            line-height: 1.4;
        }
        
        .option-group {
            margin-bottom: 25px;
            padding: 20px;
            background: #f8f9ff;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        
        .group-title {
            display: block;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
            font-size: 1em;
        }
        
        .format-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
        }
        
        .format-option {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }
        
        .format-option:hover {
            border-color: #667eea;
            transform: translateY(-1px);
        }
        
        .format-option input:checked + .format-icon {
            color: #667eea;
        }
        
        .format-icon {
            font-size: 1.2em;
        }
        
        .content-options, .analysis-options, .filter-options, .file-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }
        
        .content-options label, .analysis-options label, .filter-options label, .file-options label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            padding: 8px;
            border-radius: 6px;
            transition: background 0.3s ease;
        }
        
        .content-options label:hover, .analysis-options label:hover, .filter-options label:hover, .file-options label:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        
        .date-range {
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
            background: white;
            padding: 15px;
            border-radius: 8px;
        }
        
        .date-range input {
            padding: 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 0.95em;
            transition: border-color 0.3s ease;
        }
        
        .date-range input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .export-progress {
            background: #e8f5e8;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #4caf50;
        }
        
        .modal-buttons {
            display: flex;
            gap: 15px;
            justify-content: flex-end;
            padding: 20px 30px;
            background: #f9f9f9;
            border-top: 1px solid #e0e0e0;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #e0e0e0;
            color: #333;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s ease;
        }
        
        .btn-secondary:hover {
            background: #d0d0d0;
        }
        
        /* 響應式設計 */
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
            
            .modal-content {
                width: 95%;
                max-height: 90vh;
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
        
        <div class="dashboard-grid">
            <div class="card">
                <h2>🎯 學習困難點分析</h2>
                <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                    📊 AI即時分析學生對話訊息，動態識別學習困難點
                </p>
                
                <div class="insight-item">
                    <strong>現在完成式概念混淆</strong>
                    <p>🔍 從近期5位學生的12則訊息中識別出此困難點</p>
                    <p><em>「什麼時候用現在完成式？」「I have been 和 I went 有什麼不同？」</em></p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 65%"></div>
                    </div>
                    <small>🔄 隨新訊息持續更新 - 需要加強練習</small>
                </div>
                
                <div class="insight-item">
                    <strong>被動語態應用場景</strong>
                    <p>🔍 從8則學生訊息中發現：理解語法但不知道使用時機</p>
                    <p><em>「為什麼這裡要用被動語態？」「什麼情況下用被動比較好？」</em></p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 40%"></div>
                    </div>
                    <small>🔄 建議增加情境練習</small>
                </div>
                
                <div class="insight-item">
                    <strong>商業英文禮貌用語</strong>
                    <p>🔍 從3位學生的6則訊息中識別：對正式與非正式語境區別不清</p>
                    <p><em>「商務郵件為什麼要這樣寫？」「跟朋友聊天可以這樣說嗎？」</em></p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 30%"></div>
                    </div>
                    <small>🔄 需要文化背景說明</small>
                </div>
            </div>
            
            <div class="card">
                <h2>⭐ 學生興趣主題</h2>
                <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                    📈 AI分析學生主動提問內容，即時更新興趣排行
                </p>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">12</div>
                        <div>旅遊英文</div>
                        <small style="opacity: 0.8;">↗ 本週新增</small>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">8</div>
                        <div>科技話題</div>
                        <small style="opacity: 0.8;">📱 持續熱門</small>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">6</div>
                        <div>文化差異</div>
                        <small style="opacity: 0.8;">🌍 深度討論</small>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">4</div>
                        <div>職場溝通</div>
                        <small style="opacity: 0.8;">💼 實用導向</small>
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <h4>📊 AI分析發現</h4>
                    <p>🔍 從學生主動提問分析：實際應用場景的問題增加了 <strong style="color: #4caf50;">35%</strong></p>
                    <p>🔍 文化背景相關討論提升了 <strong style="color: #4caf50;">28%</strong></p>
                    <p style="font-size: 0.9em; color: #666; margin-top: 10px;">
                        💡 數據每次學生發送訊息後自動更新
                    </p>
                </div>
            </div>
        </div>
        
        <div class="card conversation-log">
            <h2>💬 學生對話紀錄與分析</h2>
            
            <div class="filter-tabs">
                <button class="tab active">全部對話</button>
                <button class="tab">困難點</button>
                <button class="tab">興趣主題</button>
                <button class="tab">進步軌跡</button>
            </div>
            
            <div class="conversation-item">
                <div class="conversation-meta">
                    <span><strong>學生 A</strong></span>
                    <span class="timestamp">2025-06-23 14:30</span>
                    <span class="difficulty-tag">困難</span>
                    <span class="interest-tag">高興趣</span>
                </div>
                
                <div class="student-message">
                    <strong>學生:</strong> 我想問一下，"I have been to Japan" 和 "I went to Japan" 有什麼不同？我總是搞不清楚什麼時候要用現在完成式。
                </div>
                
                <div class="ai-analysis">
                    <strong>AI分析:</strong> 
                    <ul>
                        <li><strong>困難點:</strong> 現在完成式與過去式的時間概念區別</li>
                        <li><strong>理解程度:</strong> 知道兩種形式存在，但不清楚使用時機</li>
                        <li><strong>學習興趣:</strong> 主動提問，顯示學習動機強</li>
                        <li><strong>建議:</strong> 需要更多時間軸概念的視覺化說明</li>
                    </ul>
                </div>
            </div>
            
            <div class="conversation-item">
                <div class="conversation-meta">
                    <span><strong>學生 B</strong></span>
                    <span class="timestamp">2025-06-23 15:15</span>
                    <span class="interest-tag">文化興趣</span>
                </div>
                
                <div class="student-message">
                    <strong>學生:</strong> 在商務郵件中，為什麼外國人總是說 "I hope this email finds you well"？這樣說有什麼特別的意思嗎？
                </div>
                
                <div class="ai-analysis">
                    <strong>AI分析:</strong>
                    <ul>
                        <li><strong>興趣點:</strong> 對商務文化和禮貌用語的好奇</li>
                        <li><strong>學習層次:</strong> 從語言形式深入到文化理解</li>
                        <li><strong>思考深度:</strong> 不只學習用法，更想了解背後原因</li>
                        <li><strong>建議:</strong> 可以擴展到更多商務文化話題</li>
                    </ul>
                </div>
            </div>
            
            <div class="conversation-item">
                <div class="conversation-meta">
                    <span><strong>學生 C</strong></span>
                    <span class="timestamp">2025-06-23 16:20</span>
                    <span class="difficulty-tag">進步中</span>
                </div>
                
                <div class="student-message">
                    <strong>學生:</strong> 上次你教我的被動語態，我今天在讀新聞時看到 "The bridge was built in 1990"，我現在知道為什麼要用被動了！是因為重點在橋樑，不在建造的人對吧？
                </div>
                
                <div class="ai-analysis">
                    <strong>AI分析:</strong>
                    <ul>
                        <li><strong>進步指標:</strong> 能夠在實際情境中應用所學概念</li>
                        <li><strong>理解深度:</strong> 掌握了被動語態的使用邏輯</li>
                        <li><strong>學習遷移:</strong> 主動將課堂所學應用到課外閱讀</li>
                        <li><strong>建議:</strong> 可以給予更多類似的實際應用練習</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- 匯出選項彈窗 -->
        <div id="exportModal" class="modal" style="display: none;">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>📊 資料匯出中心</h3>
                    <button class="close-btn" onclick="closeModal()">✕</button>
                </div>
                
                <div class="export-tabs">
                    <button class="export-tab active" onclick="switchTab('conversations')">💬 對話記錄</button>
                    <button class="export-tab" onclick="switchTab('analysis')">📊 分析報告</button>
                    <button class="export-tab" onclick="switchTab('advanced')">⚙️ 進階選項</button>
                </div>
                
                <!-- 對話記錄匯出 -->
                <div id="conversations-tab" class="tab-content active">
                    <div class="export-section">
                        <h4>📥 學生對話記錄匯出</h4>
                        <p class="section-desc">匯出所有學生與AI的對話歷史和互動記錄</p>
                        
                        <div class="option-group">
                            <label class="group-title">📄 匯出格式：</label>
                            <div class="format-options">
                                <label class="format-option">
                                    <input type="checkbox" name="conv-format" value="excel" checked>
                                    <span class="format-icon">📊</span> Excel (.xlsx)
                                </label>
                                <label class="format-option">
                                    <input type="checkbox" name="conv-format" value="csv" checked>
                                    <span class="format-icon">📋</span> CSV
                                </label>
                                <label class="format-option">
                                    <input type="checkbox" name="conv-format" value="pdf">
                                    <span class="format-icon">📄</span> PDF
                                </label>
                                <label class="format-option">
                                    <input type="checkbox" name="conv-format" value="json">
                                    <span class="format-icon">⚡</span> JSON
                                </label>
                            </div>
                        </div>
                        
                        <div class="option-group">
                            <label class="group-title">📅 時間範圍：</label>
                            <div class="date-range">
                                <input type="date" id="conv-start" value="2025-06-01">
                                <span>至</span>
                                <input type="date" id="conv-end" value="2025-06-23">
                            </div>
                        </div>
                        
                        <div class="option-group">
                            <label class="group-title">🎯 包含內容：</label>
                            <div class="content-options">
                                <label><input type="checkbox" checked> 學生訊息</label>
                                <label><input type="checkbox" checked> AI回應</label>
                                <label><input type="checkbox" checked> 時間戳記</label>
                                <label><input type="checkbox"> 對話元資料</label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 分析報告匯出 -->
                <div id="analysis-tab" class="tab-content">
                    <div class="export-section">
                        <h4>📊 AI學習分析報告</h4>
                        <p class="section-desc">匯出學生學習進度、困難點和興趣主題分析</p>
                        
                        <div class="option-group">
                            <label class="group-title">📄 報告格式：</label>
                            <div class="format-options">
                                <label class="format-option">
                                    <input type="checkbox" name="analysis-format" value="pdf" checked>
                                    <span class="format-icon">📄</span> PDF 報告
                                </label>
                                <label class="format-option">
                                    <input type="checkbox" name="analysis-format" value="excel" checked>
                                    <span class="format-icon">📊</span> Excel 數據
                                </label>
                                <label class="format-option">
                                    <input type="checkbox" name="analysis-format" value="ppt">
                                    <span class="format-icon">📽️</span> PowerPoint
                                </label>
                            </div>
                        </div>
                        
                        <div class="option-group">
                            <label class="group-title">📋 分析內容：</label>
                            <div class="analysis-options">
                                <label><input type="checkbox" checked> 🎯 學習困難點分析</label>
                                <label><input type="checkbox" checked> ⭐ 學生興趣主題</label>
                                <label><input type="checkbox" checked> 📈 學習進步軌跡</label>
                                <label><input type="checkbox" checked> 💡 教學建議</label>
                                <label><input type="checkbox"> 💬 代表性對話範例</label>
                                <label><input type="checkbox"> 📊 統計圖表</label>
                            </div>
                        </div>
                        
                        <div class="option-group">
                            <label class="group-title">📅 分析期間：</label>
                            <div class="date-range">
                                <input type="date" id="analysis-start" value="2025-06-01">
                                <span>至</span>
                                <input type="date" id="analysis-end" value="2025-06-23">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 進階選項 -->
                <div id="advanced-tab" class="tab-content">
                    <div class="export-section">
                        <h4>⚙️ 進階匯出選項</h4>
                        
                        <div class="option-group">
                            <label class="group-title">🔍 資料篩選：</label>
                            <div class="filter-options">
                                <label><input type="checkbox" checked> 僅包含活躍學生</label>
                                <label><input type="checkbox"> 僅包含標記困難的對話</label>
                                <label><input type="checkbox"> 僅包含高興趣主題</label>
                                <label><input type="checkbox"> 排除測試對話</label>
                            </div>
                        </div>
                        
                        <div class="option-group">
                            <label class="group-title">📦 檔案選項：</label>
                            <div class="file-options">
                                <label><input type="checkbox" checked> 壓縮為ZIP檔案</label>
                                <label><input type="checkbox" checked> 包含匯出說明文件</label>
                                <label><input type="checkbox"> 密碼保護檔案</label>
                            </div>
                        </div>
                        
                        <div class="export-progress" id="exportProgress" style="display: none;">
                            <h4>🔄 匯出進度</h4>
                            <div class="progress-bar">
                                <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                            </div>
                            <p id="progressText">準備中...</p>
                        </div>
                    </div>
                </div>
                
                <div class="modal-buttons">
                    <button class="btn-primary" onclick="startExport()">
                        🚀 開始匯出
                    </button>
                    <button class="btn-secondary" onclick="closeModal()">
                        取消
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 對話記錄標籤切換功能
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                // 這裡可以加入篩選邏輯
            });
        });
        
        // 匯出彈窗標籤切換
        function switchTab(tabName) {
            // 移除所有標籤的活躍狀態
            document.querySelectorAll('.export-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // 啟用選中的標籤
            event.target.classList.add('active');
            document.getElementById(tabName + '-tab').classList.add('active');
        }
        
        // 快速匯出功能
        function exportConversations() {
            showExportOptions();
            // 自動切換到對話記錄標籤
            setTimeout(() => {
                document.querySelector('[onclick*="conversations"]').click();
            }, 100);
        }
        
        function exportAnalysis() {
            showExportOptions();
            // 自動切換到分析報告標籤
            setTimeout(() => {
                document.querySelector('[onclick*="analysis"]').click();
            }, 100);
        }
        
        function showExportOptions() {
            document.getElementById('exportModal').style.display = 'flex';
        }
        
        function closeModal() {
            document.getElementById('exportModal').style.display = 'none';
            // 重置進度顯示
            document.getElementById('exportProgress').style.display = 'none';
            // 重新顯示標籤
            document.querySelectorAll('.export-tab').forEach(tab => {
                tab.style.display = 'block';
            });
        }
        
        function startExport() {
            const activeTab = document.querySelector('.export-tab.active');
            const tabType = activeTab ? activeTab.textContent : '匯出';
            
            // 收集選中的格式
            const selectedFormats = [];
            document.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
                const parent = cb.closest('.format-option');
                if (parent) {
                    selectedFormats.push(parent.textContent.trim());
                }
            });
            
            // 顯示進度
            showExportProgress();
            
            // 模擬匯出過程
            simulateExport(tabType, selectedFormats);
        }
        
        function showExportProgress() {
            document.getElementById('exportProgress').style.display = 'block';
            
            // 隱藏其他標籤，只顯示進階選項標籤
            document.querySelectorAll('.export-tab').forEach(tab => {
                tab.style.display = 'none';
            });
            document.querySelector('.export-tab[onclick*="advanced"]').style.display = 'block';
            document.querySelector('.export-tab[onclick*="advanced"]').click();
        }
        
        function simulateExport(tabType, formats) {
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            
            let progress = 0;
            const steps = [
                '📊 分析資料結構...',
                '🔍 篩選符合條件的記錄...',
                '📝 生成報告內容...',
                '📄 格式化輸出檔案...',
                '📦 壓縮和打包檔案...',
                '✅ 匯出完成！'
            ];
            
            const interval = setInterval(() => {
                progress += 100 / steps.length;
                progressFill.style.width = Math.min(progress, 100) + '%';
                
                const stepIndex = Math.floor(progress / (100 / steps.length));
                if (stepIndex < steps.length) {
                    progressText.textContent = steps[stepIndex];
                }
                
                if (progress >= 100) {
                    clearInterval(interval);
                    setTimeout(() => {
                        showExportComplete(tabType, formats);
                    }, 1000);
                }
            }, 800);
        }
        
        function showExportComplete(tabType, formats) {
            const progressText = document.getElementById('progressText');
            progressText.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <h4 style="color: #4caf50; margin-bottom: 15px;">🎉 匯出成功完成！</h4>
                    <p><strong>匯出類型：</strong>${tabType}</p>
                    <p><strong>檔案格式：</strong>${formats.length > 0 ? formats.join(', ') : 'Excel, PDF'}</p>
                    <p><strong>檔案大小：</strong>2.3 MB</p>
                    <p style="margin-top: 15px;">
                        <button class="btn-primary" onclick="downloadFiles()" style="margin-right: 10px;">
                            📥 下載檔案
                        </button>
                        <button class="btn-secondary" onclick="closeModal()">
                            關閉
                        </button>
                    </p>
                </div>
            `;
        }
        
        function downloadFiles() {
            alert('📁 檔案下載開始...\\n\\n檔案將保存到您的下載資料夾\\n包含：學生對話記錄、AI分析報告、匯出說明文件');
            closeModal();
        }
        
        // 點擊彈窗外部關閉
        document.getElementById('exportModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });
        
        // 設定預設日期
        document.addEventListener('DOMContentLoaded', function() {
            const today = new Date().toISOString().split('T')[0];
            const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
            
            document.getElementById('conv-end').value = today;
            document.getElementById('analysis-end').value = today;
            document.getElementById('conv-start').value = monthAgo;
            document.getElementById('analysis-start').value = monthAgo;
        });
    </script>
</body>
</html>
"""
