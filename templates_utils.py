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
