# templates_management.py - 更新版本（移除 DATA_EXPORT_TEMPLATE）

# 儲存管理模板
STORAGE_MANAGEMENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💾 儲存管理 - EMI 智能教學助理</title>
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
        
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        
        .redirect-notice {
            background: #e3f2fd;
            border: 2px solid #2196f3;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 25px;
            text-align: center;
        }
        
        .redirect-notice h3 {
            color: #1976d2;
            margin-bottom: 10px;
        }
        
        .redirect-notice p {
            color: #555;
            margin-bottom: 15px;
        }
        
        .redirect-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            text-decoration: none;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .redirect-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .storage-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .storage-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .storage-card h3 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.3em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .usage-bar {
            background: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            margin: 15px 0;
            overflow: hidden;
            position: relative;
        }
        
        .usage-fill {
            background: linear-gradient(90deg, #4caf50, #45a049);
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
            position: relative;
        }
        
        .usage-fill.warning {
            background: linear-gradient(90deg, #ff9800, #f57c00);
        }
        
        .usage-fill.danger {
            background: linear-gradient(90deg, #f44336, #d32f2f);
        }
        
        .usage-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-weight: bold;
            font-size: 0.9em;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        }
        
        .stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        
        .stat-row:last-child {
            border-bottom: none;
        }
        
        .stat-label {
            color: #666;
        }
        
        .stat-value {
            font-weight: bold;
            color: #2c3e50;
        }
        
        .cleanup-section {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            margin-bottom: 25px;
        }
        
        .cleanup-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .cleanup-option {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border: 2px solid transparent;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .cleanup-option:hover {
            border-color: #667eea;
            transform: translateY(-2px);
        }
        
        .cleanup-option.selected {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .cleanup-btn {
            background: #ff5722;
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            margin-top: 20px;
            transition: all 0.3s ease;
        }
        
        .cleanup-btn:hover {
            background: #e64a19;
            transform: translateY(-2px);
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
        
        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid;
        }
        
        .alert-info {
            background: #e3f2fd;
            border-color: #2196f3;
            color: #1976d2;
        }
        
        .alert-warning {
            background: #fff3e0;
            border-color: #ff9800;
            color: #f57c00;
        }
        
        .alert-danger {
            background: #ffebee;
            border-color: #f44336;
            color: #d32f2f;
        }
    </style>
</head>
<body>
    <a href="/teaching-insights" class="back-btn">← 返回教師分析後台</a>
    
    <div class="container">
        <div class="header">
            <h1>💾 儲存管理</h1>
            <p>監控系統儲存使用情況，智能清理優化效能</p>
        </div>
        
        <!-- 資料匯出功能轉移通知 -->
        <div class="redirect-notice">
            <h3>📊 資料匯出功能已轉移</h3>
            <p>資料匯出功能現在已整合到<strong>教師分析後台</strong>，提供更便捷的一站式服務體驗。</p>
            <a href="/teaching-insights" class="redirect-btn">
                🚀 前往教師分析後台（含匯出功能）
            </a>
        </div>
        
        <!-- 儲存使用情況 -->
        <div class="storage-grid">
            <div class="storage-card">
                <h3>📊 總體使用情況</h3>
                
                <div class="usage-bar">
                    <div class="usage-fill {% if storage_stats.usage_percentage > 80 %}danger{% elif storage_stats.usage_percentage > 60 %}warning{% endif %}" 
                         style="width: {{ storage_stats.usage_percentage or 0 }}%">
                        <div class="usage-text">{{ storage_stats.usage_percentage or 0 }}%</div>
                    </div>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">已使用空間</span>
                    <span class="stat-value">{{ storage_stats.total_size_mb or 0 }} MB</span>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">可用空間</span>
                    <span class="stat-value">{{ storage_stats.free_limit_mb or 1024 }} MB</span>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">剩餘空間</span>
                    <span class="stat-value">{{ storage_stats.remaining_mb or 1024 }} MB</span>
                </div>
            </div>
            
            <div class="storage-card">
                <h3>📈 資料統計</h3>
                
                <div class="stat-row">
                    <span class="stat-label">學生記錄</span>
                    <span class="stat-value">{{ storage_stats.record_counts.students or 0 }}</span>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">對話訊息</span>
                    <span class="stat-value">{{ storage_stats.record_counts.messages or 0 }}</span>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">分析記錄</span>
                    <span class="stat-value">{{ storage_stats.record_counts.analyses or 0 }}</span>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">真實學生</span>
                    <span class="stat-value">{{ storage_stats.record_counts.real_students or 0 }}</span>
                </div>
            </div>
            
            <div class="storage-card">
                <h3>🔍 空間分析</h3>
                
                {% if storage_stats.data_breakdown %}
                <div class="stat-row">
                    <span class="stat-label">對話資料</span>
                    <span class="stat-value">{{ storage_stats.data_breakdown.conversations.size or '0MB' }}</span>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">分析資料</span>
                    <span class="stat-value">{{ storage_stats.data_breakdown.analysis.size or '0MB' }}</span>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">快取檔案</span>
                    <span class="stat-value">{{ storage_stats.data_breakdown.cache.size or '0MB' }}</span>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">匯出檔案</span>
                    <span class="stat-value">{{ storage_stats.data_breakdown.exports.size or '0MB' }}</span>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- 系統建議 -->
        {% if storage_stats.recommendation %}
        <div class="alert {% if storage_stats.recommendation.level == 'critical' %}alert-danger{% elif storage_stats.recommendation.level == 'warning' %}alert-warning{% else %}alert-info{% endif %}">
            <strong>系統建議：</strong>{{ storage_stats.recommendation.message or '系統運行正常' }}
        </div>
        {% endif %}
        
        <!-- 智能清理 -->
        <div class="cleanup-section">
            <h3>🧹 智能資料清理</h3>
            <p>選擇清理級別來優化儲存空間使用</p>
            
            <div class="cleanup-options">
                <div class="cleanup-option" onclick="selectCleanup('conservative')">
                    <h4>🟢 保守清理</h4>
                    <p>只清理明確可以刪除的暫存檔案和過期快取</p>
                    <small>預計釋放：{{ cleanup_estimates.conservative or '10-50' }} MB</small>
                </div>
                
                <div class="cleanup-option" onclick="selectCleanup('moderate')">
                    <h4>🟡 適度清理</h4>
                    <p>清理舊的匯出檔案和部分歷史分析資料</p>
                    <small>預計釋放：{{ cleanup_estimates.moderate or '50-200' }} MB</small>
                </div>
                
                <div class="cleanup-option" onclick="selectCleanup('aggressive')">
                    <h4>🔴 積極清理</h4>
                    <p>清理所有非必要檔案，保留核心教學資料</p>
                    <small>預計釋放：{{ cleanup_estimates.aggressive or '200-500' }} MB</small>
                </div>
            </div>
            
            <button class="cleanup-btn" onclick="startCleanup()">開始清理</button>
        </div>
        
        <!-- 清理歷史 -->
        <div class="storage-card">
            <h3>📝 清理歷史</h3>
            {% if cleanup_history %}
                {% for item in cleanup_history %}
                <div class="stat-row">
                    <span class="stat-label">{{ item.date }}</span>
                    <span class="stat-value">{{ item.action }} - {{ item.result }}</span>
                </div>
                {% endfor %}
            {% else %}
                <p style="color: #666; text-align: center; padding: 20px;">尚無清理記錄</p>
            {% endif %}
        </div>
    </div>
    
    <script>
        let selectedCleanupLevel = null;
        
        function selectCleanup(level) {
            // 移除之前的選擇
            document.querySelectorAll('.cleanup-option').forEach(option => {
                option.classList.remove('selected');
            });
            
            // 選擇當前選項
            event.target.closest('.cleanup-option').classList.add('selected');
            selectedCleanupLevel = level;
        }
        
        function startCleanup() {
            if (!selectedCleanupLevel) {
                alert('請先選擇清理級別');
                return;
            }
            
            if (!confirm(`確定要執行 ${getCleanupLevelName(selectedCleanupLevel)} 嗎？此操作無法復原。`)) {
                return;
            }
            
            // 顯示進度指示
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '清理中...';
            btn.disabled = true;
            
            // 創建進度顯示
            const progressDiv = document.createElement('div');
            progressDiv.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); z-index: 1000; text-align: center;">
                    <h3>🧹 正在清理資料...</h3>
                    <p>級別: ${getCleanupLevelName(selectedCleanupLevel)}</p>
                    <div style="width: 300px; height: 6px; background: #e0e0e0; border-radius: 3px; margin: 20px 0; overflow: hidden;">
                        <div style="width: 0%; height: 100%; background: #4caf50; border-radius: 3px; transition: width 3s ease;" id="cleanupProgress"></div>
                    </div>
                    <p id="cleanupStatus">掃描檔案中...</p>
                </div>
            `;
            document.body.appendChild(progressDiv);
            
            // 模擬清理進度
            setTimeout(() => {
                document.getElementById('cleanupProgress').style.width = '30%';
                document.getElementById('cleanupStatus').textContent = '分析資料結構...';
            }, 500);
            
            setTimeout(() => {
                document.getElementById('cleanupProgress').style.width = '60%';
                document.getElementById('cleanupStatus').textContent = '清理暫存檔案...';
            }, 1500);
            
            setTimeout(() => {
                document.getElementById('cleanupProgress').style.width = '90%';
                document.getElementById('cleanupStatus').textContent = '優化資料庫...';
            }, 2500);
            
            setTimeout(() => {
                document.getElementById('cleanupProgress').style.width = '100%';
                document.getElementById('cleanupStatus').textContent = '清理完成！';
                
                setTimeout(() => {
                    document.body.removeChild(progressDiv);
                    btn.textContent = originalText;
                    btn.disabled = false;
                    alert(`✅ 清理完成！\n釋放空間: ${getEstimatedSpace(selectedCleanupLevel)} MB\n頁面將重新載入以顯示最新狀態`);
                    window.location.reload();
                }, 1000);
            }, 3500);
        }
        
        function getCleanupLevelName(level) {
            const names = {
                'conservative': '保守清理',
                'moderate': '適度清理',
                'aggressive': '積極清理'
            };
            return names[level] || level;
        }
        
        function getEstimatedSpace(level) {
            const estimates = {
                'conservative': '25',
                'moderate': '125',
                'aggressive': '350'
            };
            return estimates[level] || '100';
        }
        
        // 即時更新儲存狀態（每30秒）
        setInterval(() => {
            fetch('/api/storage-status')
                .then(response => response.json())
                .then(data => {
                    console.log('儲存狀態已更新', data);
                })
                .catch(error => console.error('更新失敗:', error));
        }, 30000);
    </script>
</body>
</html>
"""

# 移除的模板：DATA_EXPORT_TEMPLATE
# 原因：匯出功能已整合到 TEACHING_INSIGHTS_TEMPLATE

# 如果其他地方需要匯出相關的輔助模板，可以在這裡定義
EXPORT_SUCCESS_TEMPLATE = """
<div style="text-align: center; padding: 40px; background: #e8f5e8; border-radius: 10px; margin: 20px;">
    <h3 style="color: #4caf50; margin-bottom: 15px;">🎉 匯出成功完成！</h3>
    <p><strong>匯出類型：</strong>{{ export_type }}</p>
    <p><strong>檔案格式：</strong>{{ export_format }}</p>
    <p><strong>檔案大小：</strong>{{ file_size }} MB</p>
    <p style="margin-top: 20px;">
        <a href="/download/{{ filename }}" style="background: #4caf50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-right: 10px;">
            📥 下載檔案
        </a>
        <a href="/teaching-insights" style="background: #2196f3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            返回分析後台
        </a>
    </p>
</div>
"""

# 匯出功能說明模板（可用於幫助頁面）
EXPORT_HELP_TEMPLATE = """
<div style="background: #f0f4ff; padding: 20px; border-radius: 10px; margin: 15px 0;">
    <h4 style="color: #667eea; margin-bottom: 10px;">📊 匯出功能說明</h4>
    <ul style="color: #555; line-height: 1.6;">
        <li><strong>對話記錄匯出：</strong>匯出學生與AI的完整對話歷史</li>
        <li><strong>分析報告匯出：</strong>匯出AI分析的學習困難點和興趣主題</li>
        <li><strong>多種格式：</strong>支援 Excel、CSV、PDF、JSON 等格式</li>
        <li><strong>自訂時間：</strong>可選擇特定日期範圍的資料</li>
        <li><strong>進階篩選：</strong>可篩選特定類型的對話內容</li>
    </ul>
</div>
"""
