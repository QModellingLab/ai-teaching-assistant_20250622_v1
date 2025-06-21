# templates_utils.py - 模板管理工具

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
            ]
        }
    
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
    
    elif template_name == 'teaching_insights.html':
        return {
            **base_data,
            'category_stats': {
                'grammar_questions': 45,
                'vocabulary_questions': 32,
                'pronunciation_questions': 18,
                'cultural_questions': 12
            },
            'engagement_analysis': {
                'daily_average': 78.5,
                'weekly_trend': 5.2,
                'peak_hours': ['10:00-11:00', '14:00-15:00', '19:00-20:00']
            }
        }
    
    elif template_name == 'storage_management.html':
        return {
            **base_data,
            'storage_stats': {
                'used_gb': 2.5,
                'available_gb': 7.5,
                'total_gb': 10.0,
                'usage_percentage': 25,
                'daily_growth_mb': 15,
                'days_until_full': 180
            },
            'data_breakdown': {
                'conversations': {'size': '1.2GB', 'percentage': 48},
                'analysis': {'size': '0.8GB', 'percentage': 32},
                'cache': {'size': '0.3GB', 'percentage': 12},
                'exports': {'size': '0.15GB', 'percentage': 6},
                'logs': {'size': '0.05GB', 'percentage': 2}
            },
            'cleanup_estimates': {
                'safe': 150,
                'aggressive': 500,
                'archive': 800,
                'optimize': 200
            },
            'alerts': [
                {
                    'type': 'info',
                    'title': '系統狀態良好',
                    'message': '目前儲存空間使用正常，系統運行穩定。'
                }
            ],
            'recommendations': {
                'cache_cleanup': 150
            }
        }
    
    elif template_name == 'data_export.html':
        return {
            **base_data,
            'default_dates': {
                'today': datetime.now().strftime('%Y-%m-%d'),
                'month_ago': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                'semester_start': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            },
            'export_jobs': [
                {
                    'id': 1,
                    'name': '學生對話記錄匯出',
                    'status': 'processing',
                    'progress': 65,
                    'description': '正在處理 2024年3月 的對話記錄'
                }
            ],
            'export_history': [
                {
                    'id': 1,
                    'name': '二月份分析報告',
                    'created_at': datetime.now() - timedelta(days=7),
                    'file_size': '2.5MB',
                    'format': 'pdf',
                    'available': True,
                    'file_path': '/exports/feb_analysis.pdf'
                }
            ]
        }
    
    elif template_name == 'health.html':
        return {
            **base_data,
            'overall_status': 'ok',
            'overall_status_text': '正常',
            'health_checks': [
                {
                    'name': '資料庫連接',
                    'description': '檢查資料庫服務狀態',
                    'status': 'ok',
                    'status_text': '正常'
                },
                {
                    'name': 'AI 服務',
                    'description': '檢查 AI 分析服務可用性',
                    'status': 'ok',
                    'status_text': '正常'
                },
                {
                    'name': '儲存空間',
                    'description': '檢查系統儲存空間',
                    'status': 'warning',
                    'status_text': '75% 使用中'
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
    
    # 系統常數
    'CACHE_DURATION'
]
