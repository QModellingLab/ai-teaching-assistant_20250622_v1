# admin_cleanup_templates.py - 資料清理管理模板

ADMIN_CLEANUP_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧹 資料清理管理 - EMI 智能教學助理</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
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
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 15px;
        }
        
        .warning-notice {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 25px;
            text-align: center;
        }
        
        .warning-notice h3 {
            color: #856404;
            margin-bottom: 10px;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .status-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .status-card h3 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.3em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .stat-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #eee;
        }
        
        .stat-item:last-child {
            border-bottom: none;
        }
        
        .stat-label {
            color: #666;
            font-weight: 500;
        }
        
        .stat-value {
            font-weight: bold;
            color: #2c3e50;
        }
        
        .stat-value.demo {
            color: #e74c3c;
            background: rgba(231, 76, 60, 0.1);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.9em;
        }
        
        .stat-value.real {
            color: #27ae60;
            background: rgba(39, 174, 96, 0.1);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.9em;
        }
        
        .cleanup-section {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            margin-bottom: 25px;
        }
        
        .cleanup-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 25px;
        }
        
        .cleanup-option {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 12px;
            border: 2px solid transparent;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .cleanup-option:hover {
            border-color: #ff6b6b;
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(255, 107, 107, 0.2);
        }
        
        .cleanup-option.selected {
            border-color: #ff6b6b;
            background: #fff5f5;
        }
        
        .cleanup-title {
            font-size: 1.2em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .cleanup-description {
            color: #666;
            margin-bottom: 15px;
            line-height: 1.5;
        }
        
        .cleanup-details {
            background: rgba(255, 107, 107, 0.1);
            padding: 15px;
            border-radius: 8px;
            font-size: 0.9em;
        }
        
        .cleanup-details ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        
        .cleanup-details li {
            margin-bottom: 5px;
            color: #555;
        }
        
        .action-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 30px;
            flex-wrap: wrap;
        }
        
        .action-btn {
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            color: white;
        }
        
        .btn-warning {
            background: linear-gradient(135deg, #f39c12, #e67e22);
            color: white;
        }
        
        .btn-info {
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
        }
        
        .btn-success {
            background: linear-gradient(135deg, #27ae60, #2ecc71);
            color: white;
        }
        
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
        }
        
        .progress-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        
        .progress-content {
            background: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            max-width: 500px;
            width: 90%;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            margin: 20px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #ff6b6b, #ee5a24);
            border-radius: 4px;
            transition: width 0.5s ease;
            width: 0%;
        }
        
        .integrity-check {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .integrity-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        
        .integrity-status {
            font-weight: 600;
        }
        
        .integrity-status.pass {
            color: #27ae60;
        }
        
        .integrity-status.fail {
            color: #e74c3c;
        }
        
        .integrity-status.warning {
            color: #f39c12;
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
            .status-grid,
            .cleanup-options {
                grid-template-columns: 1fr;
            }
            
            .action-buttons {
                flex-direction: column;
                align-items: stretch;
            }
            
            .action-btn {
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <a href="/teaching-insights" class="back-btn">← 返回分析後台</a>
    
    <div class="container">
        <div class="header">
            <h1>🧹 資料清理管理</h1>
            <p>清理演示資料，保持真實學習分析的純淨度</p>
        </div>
        
        <!-- 安全警告 -->
        <div class="warning-notice">
            <h3>⚠️ 重要安全提醒</h3>
            <p>此功能將永久刪除演示資料。真實學生資料不會受到影響。</p>
            <p><strong>建議在執行前先進行資料備份。</strong></p>
        </div>
        
        <!-- 資料狀態總覽 -->
        <div class="status-grid">
            <div class="status-card">
                <h3>📊 資料統計總覽</h3>
                
                <div class="stat-item">
                    <span class="stat-label">真實學生</span>
                    <span class="stat-value real">{{ data_summary.real_students or 0 }}</span>
                </div>
                
                <div class="stat-item">
                    <span class="stat-label">演示學生</span>
                    <span class="stat-value demo">{{ data_summary.demo_students or 0 }}</span>
                </div>
                
                <div class="stat-item">
                    <span class="stat-label">真實訊息</span>
                    <span class="stat-value real">{{ data_summary.real_messages or 0 }}</span>
                </div>
                
                <div class="stat-item">
                    <span class="stat-label">演示訊息</span>
                    <span class="stat-value demo">{{ data_summary.demo_messages or 0 }}</span>
                </div>
            </div>
            
            <div class="status-card">
                <h3>💾 空間使用分析</h3>
                
                <div class="stat-item">
                    <span class="stat-label">總使用空間</span>
                    <span class="stat-value">{{ storage_info.total_size_mb or 0 }} MB</span>
                </div>
                
                <div class="stat-item">
                    <span class="stat-label">演示資料佔用</span>
                    <span class="stat-value demo">{{ storage_info.demo_size_mb or 0 }} MB</span>
                </div>
                
                <div class="stat-item">
                    <span class="stat-label">清理後可節省</span>
                    <span class="stat-value">{{ storage_info.potential_savings_mb or 0 }} MB</span>
                </div>
                
                <div class="stat-item">
                    <span class="stat-label">資料清潔度</span>
                    <span class="stat-value">{{ data_summary.cleanliness_percentage or 100 }}%</span>
                </div>
            </div>
            
            <div class="status-card">
                <h3>🔍 完整性檢查</h3>
                
                <div class="stat-item">
                    <span class="stat-label">孤立記錄檢查</span>
                    <span class="stat-value">{{ integrity_check.orphaned_records or 0 }} 個</span>
                </div>
                
                <div class="stat-item">
                    <span class="stat-label">統計一致性</span>
                    <span class="stat-value">{{ integrity_check.stats_consistency or '正常' }}</span>
                </div>
                
                <div class="stat-item">
                    <span class="stat-label">資料完整性</span>
                    <span class="stat-value">{{ integrity_check.data_integrity_score or 100 }}%</span>
                </div>
                
                <div class="stat-item">
                    <span class="stat-label">最後檢查</span>
                    <span class="stat-value">{{ integrity_check.last_check or '未執行' }}</span>
                </div>
            </div>
        </div>
        
        <!-- 資料完整性檢查 -->
        <div class="integrity-check">
            <h3>🔧 系統完整性檢查</h3>
            <div id="integrityResults">
                {% if integrity_results %}
                    {% for check in integrity_results %}
                    <div class="integrity-item">
                        <div>
                            <strong>{{ check.name }}</strong><br>
                            <small>{{ check.description }}</small>
                        </div>
                        <div class="integrity-status {{ check.status }}">
                            {{ check.result }}
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                <div style="text-align: center; color: #666; padding: 20px;">
                    點擊「執行完整性檢查」來檢測系統狀態
                </div>
                {% endif %}
            </div>
            
            <div style="text-align: center; margin-top: 20px;">
                <button class="action-btn btn-info" onclick="runIntegrityCheck()">
                    🔍 執行完整性檢查
                </button>
            </div>
        </div>
        
        <!-- 清理選項 -->
        <div class="cleanup-section">
            <h3>🗑️ 清理選項選擇</h3>
            <p>選擇適合的清理方式。建議從保守清理開始。</p>
            
            <div class="cleanup-options">
                <div class="cleanup-option" onclick="selectCleanupOption('conservative')">
                    <div class="cleanup-title">
                        🟢 保守清理
                    </div>
                    <div class="cleanup-description">
                        只清理明確標記為演示的資料，最安全的選項
                    </div>
                    <div class="cleanup-details">
                        <strong>將清理：</strong>
                        <ul>
                            <li>名稱以 [DEMO] 開頭的學生</li>
                            <li>line_user_id 以 demo_ 開頭的記錄</li>
                            <li>source_type 為 demo 的訊息</li>
                            <li>相關的分析和回應記錄</li>
                        </ul>
                        <strong>預計節省：</strong> {{ cleanup_estimates.conservative or '1-5' }} MB
                    </div>
                </div>
                
                <div class="cleanup-option" onclick="selectCleanupOption('thorough')">
                    <div class="cleanup-title">
                        🟡 徹底清理
                    </div>
                    <div class="cleanup-description">
                        清理所有演示資料並修復資料完整性問題
                    </div>
                    <div class="cleanup-details">
                        <strong>將清理：</strong>
                        <ul>
                            <li>所有演示資料（保守清理 + 孤立記錄）</li>
                            <li>修復統計不一致問題</li>
                            <li>重新計算所有學生統計</li>
                            <li>優化資料庫索引</li>
                        </ul>
                        <strong>預計節省：</strong> {{ cleanup_estimates.thorough or '5-15' }} MB
                    </div>
                </div>
                
                <div class="cleanup-option" onclick="selectCleanupOption('complete')">
                    <div class="cleanup-title">
                        🔴 完全重置
                    </div>
                    <div class="cleanup-description">
                        清理所有演示資料並重建資料庫結構（慎用）
                    </div>
                    <div class="cleanup-details">
                        <strong>將執行：</strong>
                        <ul>
                            <li>清理所有演示資料</li>
                            <li>重建資料庫索引</li>
                            <li>重新計算所有統計資料</li>
                            <li>重新整理資料庫結構</li>
                        </ul>
                        <strong>預計節省：</strong> {{ cleanup_estimates.complete or '15-50' }} MB
                        <br><strong style="color: #e74c3c;">注意：此操作需要更長時間</strong>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 操作按鈕 -->
        <div class="action-buttons">
            <button class="action-btn btn-danger" onclick="startCleanup()" id="cleanupBtn" disabled>
                🗑️ 開始清理
            </button>
            
            <button class="action-btn btn-warning" onclick="exportBeforeCleanup()">
                📤 清理前匯出備份
            </button>
            
            <button class="action-btn btn-info" onclick="previewCleanup()">
                👁️ 預覽清理效果
            </button>
            
            <button class="action-btn btn-success" onclick="verifyAfterCleanup()">
                ✅ 驗證清理結果
            </button>
        </div>
    </div>
    
    <!-- 進度模態視窗 -->
    <div class="progress-modal" id="progressModal">
        <div class="progress-content">
            <h3 id="progressTitle">🧹 正在清理資料...</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <p id="progressMessage">準備開始清理...</p>
            <div id="progressDetails" style="margin-top: 15px; font-size: 0.9em; color: #666;"></div>
        </div>
    </div>
    
    <script>
        let selectedCleanupOption = null;
        
        function selectCleanupOption(option) {
            // 移除之前的選擇
            document.querySelectorAll('.cleanup-option').forEach(el => {
                el.classList.remove('selected');
            });
            
            // 選擇當前選項
            event.target.closest('.cleanup-option').classList.add('selected');
            selectedCleanupOption = option;
            
            // 啟用清理按鈕
            document.getElementById('cleanupBtn').disabled = false;
            
            console.log('選擇清理選項:', option);
        }
        
        function startCleanup() {
            if (!selectedCleanupOption) {
                alert('請先選擇清理選項');
                return;
            }
            
            const optionNames = {
                'conservative': '保守清理',
                'thorough': '徹底清理', 
                'complete': '完全重置'
            };
            
            const confirmMessage = `確定要執行「${optionNames[selectedCleanupOption]}」嗎？\n\n此操作將永久刪除演示資料，無法復原。\n\n建議在執行前先匯出備份。`;
            
            if (!confirm(confirmMessage)) {
                return;
            }
            
            // 顯示進度模態視窗
            showProgressModal();
            
            // 執行清理
            executeCleanup(selectedCleanupOption);
        }
        
        function showProgressModal() {
            document.getElementById('progressModal').style.display = 'flex';
        }
        
        function hideProgressModal() {
            document.getElementById('progressModal').style.display = 'none';
        }
        
        function executeCleanup(option) {
            const steps = getCleanupSteps(option);
            let currentStep = 0;
            
            function runNextStep() {
                if (currentStep >= steps.length) {
                    // 清理完成
                    document.getElementById('progressTitle').textContent = '✅ 清理完成！';
                    document.getElementById('progressMessage').textContent = '所有演示資料已成功清理';
                    document.getElementById('progressFill').style.width = '100%';
                    
                    setTimeout(() => {
                        hideProgressModal();
                        alert('✅ 資料清理完成！\n頁面將重新載入以顯示最新狀態。');
                        window.location.reload();
                    }, 2000);
                    return;
                }
                
                const step = steps[currentStep];
                const progress = ((currentStep + 1) / steps.length) * 100;
                
                // 更新進度顯示
                document.getElementById('progressMessage').textContent = step.message;
                document.getElementById('progressFill').style.width = progress + '%';
                document.getElementById('progressDetails').textContent = `步驟 ${currentStep + 1}/${steps.length}: ${step.detail}`;
                
                // 模擬步驟執行
                setTimeout(() => {
                    // 實際這裡會調用 API
                    fetch(`/api/cleanup/${option}/step/${currentStep}`, {
                        method: 'POST'
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log(`步驟 ${currentStep + 1} 完成:`, data);
                        currentStep++;
                        runNextStep();
                    })
                    .catch(error => {
                        console.error('清理錯誤:', error);
                        document.getElementById('progressMessage').textContent = '清理過程發生錯誤';
                        setTimeout(() => {
                            hideProgressModal();
                            alert('清理過程發生錯誤，請稍後再試。');
                        }, 2000);
                    });
                }, 1000);
            }
            
            runNextStep();
        }
        
        function getCleanupSteps(option) {
            const baseSteps = [
                {
                    message: '掃描演示資料...',
                    detail: '識別所有需要清理的演示資料記錄'
                },
                {
                    message: '清理演示學生...',
                    detail: '刪除標記為演示的學生記錄'
                },
                {
                    message: '清理演示訊息...',
                    detail: '刪除演示學生的對話記錄'
                },
                {
                    message: '清理分析記錄...',
                    detail: '刪除相關的分析和統計資料'
                }
            ];
            
            if (option === 'thorough') {
                baseSteps.push(
                    {
                        message: '修復資料完整性...',
                        detail: '檢查並修復孤立記錄和統計錯誤'
                    },
                    {
                        message: '重新計算統計...',
                        detail: '更新所有學生的參與度統計'
                    }
                );
            }
            
            if (option === 'complete') {
                baseSteps.push(
                    {
                        message: '重建資料庫索引...',
                        detail: '優化資料庫查詢效能'
                    },
                    {
                        message: '驗證清理結果...',
                        detail: '確認所有演示資料已完全清理'
                    }
                );
            }
            
            return baseSteps;
        }
        
        function exportBeforeCleanup() {
            if (confirm('即將匯出完整資料備份，包含演示資料。確定繼續？')) {
                window.open('/api/export/comprehensive?format=json&include_demo=true', '_blank');
                showNotification('✅ 備份匯出已開始', 'success');
            }
        }
        
        function previewCleanup() {
            if (!selectedCleanupOption) {
                alert('請先選擇清理選項');
                return;
            }
            
            fetch(`/api/cleanup/preview/${selectedCleanupOption}`)
                .then(response => response.json())
                .then(data => {
                    const previewContent = `
                        清理預覽 - ${selectedCleanupOption}
                        
                        將刪除的記錄：
                        • 演示學生：${data.demo_students} 個
                        • 演示訊息：${data.demo_messages} 則
                        • 分析記錄：${data.demo_analyses} 個
                        • AI回應：${data.demo_responses} 個
                        
                        預計節省空間：${data.space_savings} MB
                        
                        保留的真實資料：
                        • 真實學生：${data.real_students} 個
                        • 真實訊息：${data.real_messages} 則
                    `;
                    
                    alert(previewContent);
                })
                .catch(error => {
                    console.error('預覽錯誤:', error);
                    alert('無法生成預覽，請稍後再試。');
                });
        }
        
        function verifyAfterCleanup() {
            fetch('/api/cleanup/verify')
                .then(response => response.json())
                .then(data => {
                    const verifyContent = `
                        清理驗證結果：
                        
                        ✅ 演示資料清理狀態：${data.demo_data_cleared ? '已完全清理' : '仍有殘留'}
                        ✅ 資料完整性：${data.integrity_check ? '正常' : '發現問題'}
                        ✅ 統計一致性：${data.stats_consistent ? '正常' : '需要修復'}
                        
                        當前狀態：
                        • 真實學生：${data.real_students} 個
                        • 演示學生：${data.demo_students} 個
                        • 資料清潔度：${data.cleanliness_percentage}%
                    `;
                    
                    alert(verifyContent);
                    
                    if (data.demo_students === 0) {
                        showNotification('🎉 清理驗證通過！系統現在只包含真實資料。', 'success');
                    }
                })
                .catch(error => {
                    console.error('驗證錯誤:', error);
                    alert('驗證過程發生錯誤，請稍後再試。');
                });
        }
        
        function runIntegrityCheck() {
            const resultsDiv = document.getElementById('integrityResults');
            resultsDiv.innerHTML = '<div style="text-align: center; padding: 20px;">🔍 正在檢查系統完整性...</div>';
            
            fetch('/api/integrity-check')
                .then(response => response.json())
                .then(data => {
                    let html = '';
                    
                    data.checks.forEach(check => {
                        const statusClass = check.passed ? 'pass' : (check.warning ? 'warning' : 'fail');
                        const statusText = check.passed ? '✅ 通過' : (check.warning ? '⚠️ 警告' : '❌ 失敗');
                        
                        html += `
                            <div class="integrity-item">
                                <div>
                                    <strong>${check.name}</strong><br>
                                    <small>${check.description}</small>
                                </div>
                                <div class="integrity-status ${statusClass}">
                                    ${statusText}
                                </div>
                            </div>
                        `;
                    });
                    
                    resultsDiv.innerHTML = html;
                    
                    if (data.overall_status === 'healthy') {
                        showNotification('✅ 系統完整性檢查通過', 'success');
                    } else {
                        showNotification('⚠️ 發現系統完整性問題，建議執行修復', 'warning');
                    }
                })
                .catch(error => {
                    console.error('完整性檢查錯誤:', error);
                    resultsDiv.innerHTML = '<div style="text-align: center; color: #e74c3c; padding: 20px;">❌ 完整性檢查失敗</div>';
                });
        }
        
        function showNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${type === 'success' ? '#27ae60' : type === 'warning' ? '#f39c12' : type === 'error' ? '#e74c3c' : '#3498db'};
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
                z-index: 1001;
                max-width: 350px;
                animation: slideIn 0.3s ease;
            `;
            notification.innerHTML = message;
            document.body.appendChild(notification);
            
            // 添加動畫樣式
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            if (!document.querySelector('style[data-notifications]')) {
                style.setAttribute('data-notifications', 'true');
                document.head.appendChild(style);
            }
            
            // 5秒後自動消失
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
        
        // 頁面載入時執行初始檢查
        document.addEventListener('DOMContentLoaded', function() {
            // 顯示歡迎訊息
            setTimeout(() => {
                showNotification('💡 選擇清理選項後即可開始清理演示資料', 'info');
            }, 1000);
            
            // 自動執行完整性檢查
            setTimeout(() => {
                runIntegrityCheck();
            }, 2000);
        });
        
        // 快捷鍵支援
        document.addEventListener('keydown', function(e) {
            // Ctrl+Shift+C: 快速保守清理
            if (e.ctrlKey && e.shiftKey && e.key === 'C') {
                e.preventDefault();
                selectCleanupOption('conservative');
                if (confirm('快捷鍵：執行保守清理？')) {
                    startCleanup();
                }
            }
            
            // Ctrl+Shift+V: 快速驗證
            if (e.ctrlKey && e.shiftKey && e.key === 'V') {
                e.preventDefault();
                verifyAfterCleanup();
            }
        });
    </script>
</body>
</html>
"""

# 簡化版清理狀態模板
CLEANUP_STATUS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 清理狀態 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            color: #333;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .status-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        .status-title {
            font-size: 2em;
            color: #2c3e50;
            margin-bottom: 15px;
        }
        .status-message {
            font-size: 1.1em;
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stat-item {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #27ae60;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
        }
        .action-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 30px;
        }
        .action-btn {
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            text-decoration: none;
            font-size: 1em;
            transition: all 0.3s ease;
        }
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
        }
        .action-btn.primary {
            background: linear-gradient(135deg, #27ae60, #2ecc71);
        }
        .cleanup-summary {
            background: #e8f5e8;
            border: 2px solid #27ae60;
            border-radius: 10px;
            padding: 20px;
            margin: 25px 0;
            text-align: left;
        }
        .cleanup-summary h4 {
            color: #27ae60;
            margin-bottom: 10px;
        }
        .cleanup-summary ul {
            color: #555;
            margin: 10px 0;
            padding-left: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="status-icon">{{ status_icon or '✅' }}</div>
        <h1 class="status-title">{{ status_title or '清理完成' }}</h1>
        <p class="status-message">{{ status_message or '所有演示資料已成功清理，系統現在只包含真實學習資料。' }}</p>
        
        {% if cleanup_results %}
        <div class="cleanup-summary">
            <h4>🧹 清理摘要</h4>
            <ul>
                {% for result in cleanup_results %}
                <li>{{ result }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
        
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">{{ stats.real_students or 0 }}</div>
                <div class="stat-label">真實學生</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ stats.demo_students or 0 }}</div>
                <div class="stat-label">演示學生</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ stats.space_saved or 0 }} MB</div>
                <div class="stat-label">節省空間</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ stats.cleanliness_percentage or 100 }}%</div>
                <div class="stat-label">資料清潔度</div>
            </div>
        </div>
        
        <div class="action-buttons">
            <a href="/teaching-insights" class="action-btn primary">
                📊 查看真實資料分析
            </a>
            <a href="/admin-cleanup" class="action-btn">
                🔄 重新執行清理
            </a>
            <a href="/api/export/comprehensive" class="action-btn">
                📤 匯出清理後資料
            </a>
        </div>
    </div>
</body>
</html>
"""

# 清理確認模板
CLEANUP_CONFIRMATION_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚠️ 清理確認 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            color: #333;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .confirmation-container {
            max-width: 600px;
            background: rgba(255, 255, 255, 0.95);
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
            text-align: center;
        }
        .warning-icon {
            font-size: 4em;
            color: #f39c12;
            margin-bottom: 20px;
        }
        .confirmation-title {
            font-size: 2em;
            color: #2c3e50;
            margin-bottom: 20px;
        }
        .confirmation-message {
            font-size: 1.1em;
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        .preview-box {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 10px;
            padding: 20px;
            margin: 25px 0;
            text-align: left;
        }
        .preview-box h4 {
            color: #856404;
            margin-bottom: 15px;
        }
        .preview-list {
            color: #555;
            margin: 0;
            padding-left: 20px;
        }
        .preview-list li {
            margin-bottom: 8px;
        }
        .action-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 30px;
        }
        .action-btn {
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.3s ease;
        }
        .btn-danger {
            background: linear-gradient(135deg, #e74c3c, #c0392b);
            color: white;
        }
        .btn-secondary {
            background: linear-gradient(135deg, #95a5a6, #7f8c8d);
            color: white;
        }
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        .safety-notice {
            background: #ffebee;
            border: 1px solid #f44336;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            font-size: 0.9em;
        }
        .safety-notice strong {
            color: #d32f2f;
        }
    </style>
</head>
<body>
    <div class="confirmation-container">
        <div class="warning-icon">⚠️</div>
        <h1 class="confirmation-title">確認資料清理</h1>
        <p class="confirmation-message">
            您即將執行「{{ cleanup_type_name }}」操作。此操作將永久刪除以下資料，且無法復原。
        </p>
        
        <div class="preview-box">
            <h4>📋 將被清理的資料：</h4>
            <ul class="preview-list">
                {% for item in cleanup_preview %}
                <li>{{ item }}</li>
                {% endfor %}
            </ul>
        </div>
        
        <div class="safety-notice">
            <strong>⚠️ 安全提醒：</strong>
            真實學生的學習資料不會受到影響。建議在執行前先匯出完整備份。
        </div>
        
        <div class="action-buttons">
            <button class="action-btn btn-danger" onclick="confirmCleanup()">
                🗑️ 確認執行清理
            </button>
            <a href="/admin-cleanup" class="action-btn btn-secondary">
                ❌ 取消操作
            </a>
        </div>
    </div>
    
    <script>
        function confirmCleanup() {
            // 最後確認
            if (confirm('最後確認：您確定要執行此清理操作嗎？\n\n此操作無法復原！')) {
                // 重定向到實際清理頁面
                window.location.href = '/admin-cleanup/execute/{{ cleanup_type }}';
            }
        }
        
        // 防止意外關閉頁面
        window.addEventListener('beforeunload', function (e) {
            e.preventDefault();
            e.returnValue = '';
        });
    </script>
</body>
</html>
"""

def get_template(template_name):
    """取得清理管理模板"""
    templates = {
        'admin_cleanup.html': ADMIN_CLEANUP_TEMPLATE,
        'cleanup_status.html': CLEANUP_STATUS_TEMPLATE,
        'cleanup_confirmation.html': CLEANUP_CONFIRMATION_TEMPLATE,
    }
    return templates.get(template_name, '')

# 匯出
__all__ = [
    'ADMIN_CLEANUP_TEMPLATE',
    'CLEANUP_STATUS_TEMPLATE', 
    'CLEANUP_CONFIRMATION_TEMPLATE',
    'get_template'
]
