# templates_utils.py - 模板管理工具 (更新版 - 支援空狀態)

from flask import render_template_string
import os
import time
from typing import Dict, Optional, List

# 導入所有模板文件
try:
    from templates_main import (
        INDEX_TEMPLATE, 
        STUDENTS_TEMPLATE, 
        STUDENT_DETAIL_TEMPLATE,
        get_template as get_main_template
    )
except ImportError:
    INDEX_TEMPLATE = STUDENTS_TEMPLATE = STUDENT_DETAIL_TEMPLATE = ""
    get_main_template = lambda x: ""

try:
    from templates_analysis import (
        TEACHING_INSIGHTS_TEMPLATE,
        CONVERSATION_SUMMARIES_TEMPLATE,
        LEARNING_RECOMMENDATIONS_TEMPLATE,
        get_template as get_analysis_template
    )
except ImportError:
    TEACHING_INSIGHTS_TEMPLATE = CONVERSATION_SUMMARIES_TEMPLATE = LEARNING_RECOMMENDATIONS_TEMPLATE = ""
    get_analysis_template = lambda x: ""

try:
    from templates_management import (
        STORAGE_MANAGEMENT_TEMPLATE,
        DATA_EXPORT_TEMPLATE,
        get_template as get_management_template
    )
except ImportError:
    STORAGE_MANAGEMENT_TEMPLATE = DATA_EXPORT_TEMPLATE = ""
    get_management_template = lambda x: ""

# 模板快取
template_cache: Dict[str, str] = {}
cache_timestamps: Dict[str, float] = {}
CACHE_DURATION = 300  # 5分鐘快取

# 系統模板
HEALTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏥 系統健康檢查 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .status-ok { color: #27ae60; }
        .status-warning { color: #f39c12; }
        .status-error { color: #e74c3c; }
        .health-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #3498db;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 系統健康檢查</h1>
        <p>系統運行狀態：<span class="status-{{ overall_status }}">{{ overall_status_text }}</span></p>
        
        {% for check in health_checks %}
        <div class="health-item">
            <div>
                <strong>{{ check.name }}</strong><br>
                <small>{{ check.description }}</small>
            </div>
            <div class="status-{{ check.status }}">
                {{ check.status_text }}
            </div>
        </div>
        {% endfor %}
        
        <div style="margin-top: 30px; text-align: center;">
            <button onclick="window.location.reload()" style="background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                重新檢查
            </button>
        </div>
    </div>
</body>
</html>
"""

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>❌ 系統錯誤 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .error-container {
            max-width: 600px;
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        .error-code {
            font-size: 4em;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .error-message {
            font-size: 1.2em;
            margin-bottom: 30px;
            opacity: 0.9;
        }
        .back-btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 15px 30px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 25px;
            text-decoration: none;
            transition: all 0.3s ease;
        }
        .back-btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">{{ error_code or 500 }}</div>
        <div class="error-message">
            {{ error_message or '系統發生未預期的錯誤，請稍後再試' }}
        </div>
        <a href="/" class="back-btn">返回首頁</a>
    </div>
</body>
</html>
"""

# 新增：空狀態模板
EMPTY_STATE_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 教師分析後台 - 等待真實資料</title>
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
            max-width: 1200px;
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
        
        .empty-state-main {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 60px 40px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }
        
        .empty-icon {
            font-size: 5em;
            margin-bottom: 20px;
            opacity: 0.7;
        }
        
        .empty-title {
            font-size: 2em;
            color: #2c3e50;
            margin-bottom: 15px;
        }
        
        .empty-subtitle {
            font-size: 1.2em;
            color: #7f8c8d;
            margin-bottom: 30px;
        }
        
        .setup-steps {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 30px;
            margin: 30px 0;
            text-align: left;
        }
        
        .setup-steps h3 {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 25px;
            font-size: 1.4em;
        }
        
        .steps-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .step-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            border-left: 4px solid #667eea;
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
            margin-bottom: 15px;
        }
        
        .step-title {
            font-size: 1.1em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .step-description {
            color: #666;
            font-size: 0.95em;
            line-height: 1.5;
        }
        
        .demo-section {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .demo-notice {
            background: #e3f2fd;
            border: 2px solid #2196f3;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .demo-notice h4 {
            color: #1976d2;
            margin-bottom: 10px;
        }
        
        .demo-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .demo-card {
            background: #f8f9fa;
            border: 2px dashed #bdc3c7;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        
        .demo-card h4 {
            color: #7f8c8d;
            margin-bottom: 10px;
        }
        
        .demo-placeholder {
            background: #ecf0f1;
            height: 100px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #95a5a6;
            font-size: 0.9em;
            margin: 15px 0;
        }
        
        .progress-indicator {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .progress-indicator h3 {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 20px;
        }
        
        .status-items {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .status-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #e74c3c;
        }
        
        .status-item.ready {
            border-left-color: #27ae60;
        }
        
        .status-item.pending {
            border-left-color: #f39c12;
        }
        
        .status-label {
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .status-value {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .cta-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 30px;
        }
        
        .cta-btn {
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
        
        .cta-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .cta-btn.secondary {
            background: #34495e;
        }
        
        .refresh-notice {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            text-align: center;
        }
        
        .refresh-notice strong {
            color: #856404;
        }
        
        @media (max-width: 768px) {
            .steps-grid,
            .demo-cards,
            .status-items {
                grid-template-columns: 1fr;
            }
            
            .cta-buttons {
                flex-direction: column;
                align-items: center;
            }
            
            .empty-state-main {
                padding: 40px 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 教師分析後台</h1>
            <p>EMI 智能教學助理 - 等待真實學生資料中</p>
        </div>
        
        <!-- 主要空狀態區域 -->
        <div class="empty-state-main">
            <div class="empty-icon">📈</div>
            <h2 class="empty-title">準備開始分析</h2>
            <p class="empty-subtitle">
                系統已準備就緒，等待學生開始使用 LINE Bot 進行對話
            </p>
            <p style="color: #666; margin-bottom: 30px;">
                當學生開始與 AI 助理對話時，真實的教學洞察將自動在此顯示
            </p>
            
            <div class="cta-buttons">
                <a href="#setup" class="cta-btn">
                    🚀 查看設定步驟
                </a>
                <a href="/health" class="cta-btn secondary">
                    🔧 系統狀態檢查
                </a>
            </div>
        </div>
        
        <!-- 設定步驟說明 -->
        <div class="setup-steps" id="setup">
            <h3>🎯 開始收集真實教學資料</h3>
            <div class="steps-grid">
                <div class="step-card">
                    <div class="step-number">1</div>
                    <div class="step-title">設定 LINE Bot</div>
                    <div class="step-description">
                        確保您的 LINE Bot 已正確設定並連接到系統。檢查 CHANNEL_ACCESS_TOKEN 和 CHANNEL_SECRET 環境變數。
                    </div>
                </div>
                
                <div class="step-card">
                    <div class="step-number">2</div>
                    <div class="step-title">分享給學生</div>
                    <div class="step-description">
                        將 LINE Bot 的 QR Code 或連結分享給您的學生，邀請他們加入並開始對話。
                    </div>
                </div>
                
                <div class="step-card">
                    <div class="step-number">3</div>
                    <div class="step-title">鼓勵互動</div>
                    <div class="step-description">
                        鼓勵學生主動提問英語相關問題，如文法、詞彙、發音或文化等主題。
                    </div>
                </div>
                
                <div class="step-card">
                    <div class="step-number">4</div>
                    <div class="step-title">自動分析</div>
                    <div class="step-description">
                        系統將自動分析對話內容，識別學習困難點和興趣主題，並在此後台顯示洞察。
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 預覽區域 -->
        <div class="demo-section">
            <div class="demo-notice">
                <h4>📋 分析功能預覽</h4>
                <p>以下是當有真實學生資料時，系統將提供的分析功能：</p>
            </div>
            
            <div class="demo-cards">
                <div class="demo-card">
                    <h4>🎯 學習困難點分析</h4>
                    <div class="demo-placeholder">
                        等待真實對話資料<br>
                        將顯示文法、詞彙等困難點
                    </div>
                    <p style="color: #7f8c8d; font-size: 0.9em;">
                        AI 將自動識別學生在對話中表現出的學習困難
                    </p>
                </div>
                
                <div class="demo-card">
                    <h4>⭐ 學生興趣主題</h4>
                    <div class="demo-placeholder">
                        等待學生提問<br>
                        將分析熱門討論主題
                    </div>
                    <p style="color: #7f8c8d; font-size: 0.9em;">
                        基於學生主動提問分析學習興趣和偏好
                    </p>
                </div>
                
                <div class="demo-card">
                    <h4>💬 對話記錄分析</h4>
                    <div class="demo-placeholder">
                        等待對話開始<br>
                        將顯示師生互動分析
                    </div>
                    <p style="color: #7f8c8d; font-size: 0.9em;">
                        完整的對話歷史和 AI 教學建議
                    </p>
                </div>
            </div>
        </div>
        
        <!-- 系統狀態指示器 -->
        <div class="progress-indicator">
            <h3>🔍 系統準備狀態</h3>
            <div class="status-items">
                <div class="status-item ready">
                    <div class="status-label">✅ 資料庫連接</div>
                    <div class="status-value">已連接並準備儲存資料</div>
                </div>
                
                <div class="status-item ready">
                    <div class="status-label">✅ AI 分析引擎</div>
                    <div class="status-value">Gemini 2.0 已配置</div>
                </div>
                
                <div class="status-item pending">
                    <div class="status-label">⏳ LINE Bot 狀態</div>
                    <div class="status-value">等待學生開始對話</div>
                </div>
                
                <div class="status-item pending">
                    <div class="status-label">⏳ 真實學生資料</div>
                    <div class="status-value">目前：0 位真實學生</div>
                </div>
            </div>
            
            <div class="refresh-notice">
                <strong>💡 提示：</strong>
                當學生開始使用 LINE Bot 後，請重新整理此頁面查看真實分析資料
            </div>
        </div>
    </div>
    
    <script>
        // 自動檢查是否有新的學生資料
        let checkInterval;
        
        function startDataCheck() {
            checkInterval = setInterval(async () => {
                try {
                    const response = await fetch('/api/dashboard-stats');
                    const data = await response.json();
                    
                    if (data.success && data.stats.real_students > 0) {
                        // 發現真實學生資料，顯示通知並建議重新整理
                        showDataFoundNotification(data.stats.real_students);
                        clearInterval(checkInterval);
                    }
                } catch (error) {
                    console.log('檢查資料狀態時發生錯誤:', error);
                }
            }, 30000); // 每30秒檢查一次
        }
        
        function showDataFoundNotification(studentCount) {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #27ae60;
                color: white;
                padding: 20px 25px;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(39, 174, 96, 0.3);
                z-index: 1000;
                max-width: 350px;
                animation: slideIn 0.5s ease;
            `;
            
            notification.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 1.2em;">🎉</span>
                    <strong>發現真實學生資料！</strong>
                </div>
                <p style="margin: 10px 0; font-size: 0.9em;">
                    已有 ${studentCount} 位學生開始使用系統
                </p>
                <button onclick="window.location.reload()" 
                        style="background: rgba(255,255,255,0.2); color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-size: 0.9em;">
                    🔄 重新整理查看分析
                </button>
                <button onclick="this.parentNode.remove()" 
                        style="background: none; color: white; border: none; padding: 8px; cursor: pointer; float: right; font-size: 1.1em;">
                    ✕
                </button>
            `;
            
            document.body.appendChild(notification);
            
            // 添加動畫樣式
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
            
            // 10秒後自動消失
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    notification.style.animation = 'slideOut 0.5s ease';
                    setTimeout(() => {
                        if (document.body.contains(notification)) {
                            document.body.removeChild(notification);
                        }
                    }, 500);
                }
            }, 10000);
        }
        
        // 頁面載入時開始檢查
        document.addEventListener('DOMContentLoaded', function() {
            startDataCheck();
            
            // 顯示歡迎訊息
            setTimeout(() => {
                const welcomeMsg = document.createElement('div');
                welcomeMsg.style.cssText = `
                    position: fixed;
                    bottom: 20px;
                    left: 20px;
                    background: #3498db;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 10px;
                    box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
                    max-width: 300px;
                    font-size: 0.9em;
                `;
                
                welcomeMsg.innerHTML = `
                    <div style="margin-bottom: 8px;"><strong>💡 系統提示</strong></div>
                    <div>系統正在等待學生開始對話。請確保已分享 LINE Bot 給學生。</div>
                    <button onclick="this.parentNode.remove()" 
                            style="background: none; color: white; border: none; padding: 5px; cursor: pointer; float: right; margin-top: 5px;">
                        知道了
                    </button>
                `;
                
                document.body.appendChild(welcomeMsg);
                
                // 8秒後自動消失
                setTimeout(() => {
                    if (document.body.contains(welcomeMsg)) {
                        document.body.removeChild(welcomeMsg);
                    }
                }, 8000);
            }, 2000);
        });
        
        // 頁面卸載時清理定時器
        window.addEventListener('beforeunload', function() {
            if (checkInterval) {
                clearInterval(checkInterval);
            }
        });
    </script>
</body>
</html>
"""

# 統一模板管理
ALL_TEMPLATES = {
    # 主要頁面
    'index.html': INDEX_TEMPLATE,
    'students.html': STUDENTS_TEMPLATE,
    'student_detail.html': STUDENT_DETAIL_TEMPLATE,
    
    # 分析功能
    'teaching_insights.html': TEACHING_INSIGHTS_TEMPLATE,
    'conversation_summaries.html': CONVERSATION_SUMMARIES_TEMPLATE,
    'learning_recommendations.html': LEARNING_RECOMMENDATIONS_TEMPLATE,
    
    # 管理功能
    'storage_management.html': STORAGE_MANAGEMENT_TEMPLATE,
    'data_export.html': DATA_EXPORT_TEMPLATE,
    
    # 系統模板
    'health.html': HEALTH_TEMPLATE,
    'error.html': ERROR_TEMPLATE,
    'empty_state.html': EMPTY_STATE_TEMPLATE,  # 新增
}

def get_template(template_name: str) -> str:
    """
    取得指定模板
    
    Args:
        template_name: 模板名稱（如 'index.html'）
        
    Returns:
        模板內容字串
    """
    # 首先檢查統一模板字典
    if template_name in ALL_TEMPLATES:
        return ALL_TEMPLATES[template_name]
    
    # 檢查各個模組
    template = get_main_template(template_name)
    if template and template != "":
        return template
        
    template = get_analysis_template(template_name)
    if template and template != "":
        return template
        
    template = get_management_template(template_name)
    if template and template != "":
        return template
    
    # 如果都找不到，返回錯誤模板
    return ERROR_TEMPLATE

def get_cached_template(template_name: str) -> str:
    """
    取得快取版本的模板
    
    Args:
        template_name: 模板名稱
        
    Returns:
        快取的模板內容
    """
    current_time = time.time()
    
    # 檢查快取是否存在且未過期
    if (template_name in template_cache and 
        template_name in cache_timestamps and
        current_time - cache_timestamps[template_name] < CACHE_DURATION):
        return template_cache[template_name]
    
    # 重新載入模板並快取
    template = get_template(template_name)
    template_cache[template_name] = template
    cache_timestamps[template_name] = current_time
    
    return template

def validate_template(template_name: str) -> bool:
    """
    驗證模板是否存在
    
    Args:
        template_name: 模板名稱
        
    Returns:
        True 如果模板存在，否則 False
    """
    try:
        template = get_template(template_name)
        return template != ERROR_TEMPLATE and len(template.strip()) > 0
    except Exception:
        return False

def render_template_with_error_handling(template_name: str, **context):
    """
    安全渲染模板，包含錯誤處理
    
    Args:
        template_name: 模板名稱
        **context: 模板變數
        
    Returns:
        渲染結果或錯誤頁面
    """
    try:
        template = get_cached_template(template_name)
        return render_template_string(template, **context)
    except Exception as e:
        # 如果模板渲染失敗，返回錯誤頁面
        error_context = {
            'error_code': 500,
            'error_message': f'模板 {template_name} 渲染失敗：{str(e)}'
        }
        return render_template_string(ERROR_TEMPLATE, **error_context)

def clear_template_cache():
    """清除所有模板快取"""
    global template_cache, cache_timestamps
    template_cache.clear()
    cache_timestamps.clear()

def get_template_info() -> Dict:
    """
    取得模板系統資訊
    
    Returns:
        包含模板統計的字典
    """
    available_templates = list(ALL_TEMPLATES.keys())
    cached_templates = list(template_cache.keys())
    
    return {
        'total_templates': len(available_templates),
        'cached_templates': len(cached_templates),
        'cache_hit_rate': len(cached_templates) / max(len(available_templates), 1) * 100,
        'available_templates': available_templates,
        'cached_templates': cached_templates,
        'cache_duration': CACHE_DURATION
    }

def preview_template(template_name: str, sample_data: Optional[Dict] = None) -> str:
    """
    預覽模板（開發用）
    
    Args:
        template_name: 模板名稱
        sample_data: 範例資料
        
    Returns:
        渲染的預覽內容
    """
    if sample_data is None:
        sample_data = get_sample_data(template_name)
    
    try:
        template = get_template(template_name)
        return render_template_string(template, **sample_data)
    except Exception as e:
        return f"預覽失敗：{str(e)}"

def get_sample_data(template_name: str) -> Dict:
    """
    為不同模板提供範例資料
    
    Args:
        template_name: 模板名稱
        
    Returns:
        範例資料字典
    """
    from datetime import datetime, timedelta
    
    base_data = {
        'current_time': datetime.now(),
        'user_name': '張教授',
        'system_name': 'EMI 智能教學助理'
    }
    
    if template_name == 'index.html':
        return {
            **base_data,
            'stats': {
                'total_students': 45,
                'real_students': 0,  # 更新：預設為0以顯示等待狀態
                'active_conversations': 12,
                'total_messages': 1234,
                'avg_engagement': 78.5
            },
            'recent_messages': [
                {
                    'student': {'name': '王小明'},
                    'timestamp': datetime.now() - timedelta(minutes=5),
                    'message_type': '問題',
                    'content': 'Could you help me understand this grammar point?'
                },
                {
                    'student': {'name': '李小華'},
                    'timestamp': datetime.now() - timedelta(minutes=15),
                    'message_type': '回答',
                    'content': 'Thank you for the explanation, it was very helpful!'
                }
            ],
            'data_status': 'WAITING_FOR_DATA'  # 新增狀態指示
        }
    
    elif template_name == 'empty_state.html':
        return {
            **base_data,
            'waiting_message': '系統已準備就緒，等待學生開始使用 LINE Bot',
            'setup_complete': True
        }
    
    # 其他模板的範例資料保持原有邏輯...
    elif template_name == 'students.html':
        return {
            **base_data,
            'students': [
                {
                    'id': 1,
                    'name': '王小明',
                    'email': 'wang@example.com',
                    'total_messages': 45,
                    'engagement_score': 85.2,
                    'last_active': datetime.now() - timedelta(hours=2),
                    'status': 'active'
                },
                {
                    'id': 2,
                    'name': '李小華',
                    'email': 'li@example.com',
                    'total_messages': 32,
                    'engagement_score': 72.8,
                    'last_active': datetime.now() - timedelta(days=1),
                    'status': 'moderate'
                }
            ]
        }
    
    else:
        return base_data

# 向後相容的函數別名
def render_template_safe(template_name: str, **context):
    """向後相容的安全渲染函數"""
    return render_template_with_error_handling(template_name, **context)

def get_all_templates() -> List[str]:
    """取得所有可用模板列表"""
    return list(ALL_TEMPLATES.keys())

def template_exists(template_name: str) -> bool:
    """檢查模板是否存在（向後相容）"""
    return validate_template(template_name)

# 開發工具函數
def debug_template_system():
    """除錯模板系統（開發用）"""
    info = get_template_info()
    print("=== 模板系統除錯資訊 ===")
    print(f"總模板數量：{info['total_templates']}")
    print(f"快取模板數量：{info['cached_templates']}")
    print(f"快取命中率：{info['cache_hit_rate']:.1f}%")
    print(f"可用模板：{', '.join(info['available_templates'])}")
    print(f"快取持續時間：{info['cache_duration']} 秒")
    
    # 測試每個模板
    print("\n=== 模板驗證結果 ===")
    for template_name in info['available_templates']:
        is_valid = validate_template(template_name)
        status = "✅ 正常" if is_valid else "❌ 錯誤"
        print(f"{template_name}: {status}")

# 匯出所有公開函數和變數
__all__ = [
    # 主要函數
    'get_template',
    'get_cached_template',
    'validate_template',
    'render_template_with_error_handling',
    'clear_template_cache',
    'get_template_info',
    'preview_template',
    'get_sample_data',
    
    # 向後相容函數
    'render_template_safe',
    'get_all_templates',
    'template_exists',
    
    # 開發工具
    'debug_template_system',
    
    # 模板常數
    'ALL_TEMPLATES',
    'HEALTH_TEMPLATE',
    'ERROR_TEMPLATE',
    'EMPTY_STATE_TEMPLATE',  # 新增
    
    # 系統常數
    'CACHE_DURATION'
]
