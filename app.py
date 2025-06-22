# app_fixed.py - 修復版應用程式
import os
import json
import datetime
import logging
from flask import Flask, request, abort, render_template_string, jsonify

# 設定更詳細的日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask 應用初始化
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# 全域變數
db = None
Student = None
Message = None
Analysis = None
WEB_TEMPLATES_AVAILABLE = False
line_bot_api = None
handler = None

def safe_import_models():
    """安全地導入模型"""
    global db, Student, Message, Analysis
    try:
        from models import db, Student, Message, Analysis, initialize_db
        initialize_db()
        logger.info("✅ 模型導入成功")
        return True
    except Exception as e:
        logger.error(f"❌ 模型導入失敗: {e}")
        return False

def safe_import_templates():
    """安全地導入模板"""
    global WEB_TEMPLATES_AVAILABLE
    try:
        from templates_main import INDEX_TEMPLATE
        from templates_analysis_part1 import TEACHING_INSIGHTS_TEMPLATE
        WEB_TEMPLATES_AVAILABLE = True
        logger.info("✅ 模板導入成功")
        return True
    except Exception as e:
        logger.error(f"❌ 模板導入失敗: {e}")
        WEB_TEMPLATES_AVAILABLE = False
        return False

def safe_import_linebot():
    """安全地導入 LINE Bot"""
    global line_bot_api, handler
    try:
        CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN') or os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        CHANNEL_SECRET = os.getenv('CHANNEL_SECRET') or os.getenv('LINE_CHANNEL_SECRET')
        
        if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
            from linebot import LineBotApi, WebhookHandler
            line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
            handler = WebhookHandler(CHANNEL_SECRET)
            logger.info("✅ LINE Bot 初始化成功")
            return True
        else:
            logger.warning("⚠️ LINE Bot 憑證未設定")
            return False
    except Exception as e:
        logger.error(f"❌ LINE Bot 初始化失敗: {e}")
        return False

# 備用模板
FALLBACK_INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EMI 智能教學助理 - 系統檢查</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .status-card {
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .status-ok { background: #d4edda; border-left: 4px solid #28a745; }
        .status-warning { background: #fff3cd; border-left: 4px solid #ffc107; }
        .status-error { background: #f8d7da; border-left: 4px solid #dc3545; }
        .nav-links {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }
        .nav-link {
            background: #007bff;
            color: white;
            padding: 15px;
            text-decoration: none;
            border-radius: 8px;
            text-align: center;
            transition: background 0.3s;
        }
        .nav-link:hover {
            background: #0056b3;
            text-decoration: none;
            color: white;
        }
        .system-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .info-item {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 5px 0;
            border-bottom: 1px solid #dee2e6;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 EMI 智能教學助理</h1>
            <p>系統狀態檢查</p>
        </div>
        
        <div class="status-grid">
            <div class="status-card {{ 'status-ok' if system_status.database == 'connected' else 'status-error' }}">
                <h3>🗄️ 資料庫</h3>
                <p>{{ system_status.database }}</p>
            </div>
            
            <div class="status-card {{ 'status-ok' if system_status.templates else 'status-warning' }}">
                <h3>🎨 模板系統</h3>
                <p>{{ '正常' if system_status.templates else '簡化模式' }}</p>
            </div>
            
            <div class="status-card {{ 'status-ok' if system_status.linebot else 'status-warning' }}">
                <h3>📱 LINE Bot</h3>
                <p>{{ '已配置' if system_status.linebot else '未配置' }}</p>
            </div>
            
            <div class="status-card {{ 'status-ok' if system_status.ai else 'status-warning' }}">
                <h3>🤖 AI 服務</h3>
                <p>{{ '已配置' if system_status.ai else '未配置' }}</p>
            </div>
        </div>
        
        <div class="system-info">
            <h3>📊 系統資訊</h3>
            <div class="info-item">
                <span>總學生數：</span>
                <span>{{ stats.total_students or 0 }}</span>
            </div>
            <div class="info-item">
                <span>總訊息數：</span>
                <span>{{ stats.total_messages or 0 }}</span>
            </div>
            <div class="info-item">
                <span>系統時間：</span>
                <span>{{ current_time.strftime('%Y-%m-%d %H:%M:%S') }}</span>
            </div>
            <div class="info-item">
                <span>運行模式：</span>
                <span>{{ '完整模式' if system_status.templates else '簡化模式' }}</span>
            </div>
        </div>
        
        <div class="nav-links">
            <a href="/health" class="nav-link">🏥 健康檢查</a>
            <a href="/stats" class="nav-link">📈 統計資料</a>
            {% if system_status.database == 'connected' %}
            <a href="/students" class="nav-link">👥 學生列表</a>
            {% endif %}
            <a href="/api/sync-all-students" class="nav-link">🔄 同步資料</a>
        </div>
        
        {% if not system_status.templates %}
        <div style="background: #fff3cd; padding: 20px; border-radius: 10px; border-left: 4px solid #ffc107;">
            <strong>⚠️ 注意：</strong>系統正在簡化模式下運行。部分功能可能不可用。
            請檢查模板檔案是否正確部署。
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

FALLBACK_STUDENTS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>學生列表 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 40px;
            background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
            color: #333;
            min-height: 100vh;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .back-btn {
            background: #007bff;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 8px;
            margin-bottom: 20px;
            display: inline-block;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .demo-badge {
            background: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
        }
        .view-link {
            background: #007bff;
            color: white;
            padding: 5px 10px;
            text-decoration: none;
            border-radius: 4px;
            font-size: 0.9em;
        }
        .view-link:hover {
            background: #0056b3;
            text-decoration: none;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← 返回首頁</a>
        <h1>👥 學生管理</h1>
        <p>查看所有學生的學習狀況</p>
        
        <table>
            <thead>
                <tr>
                    <th>姓名</th>
                    <th>參與度</th>
                    <th>訊息數</th>
                    <th>問題數</th>
                    <th>最後活動</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for student in students %}
                <tr>
                    <td>
                        {{ student.name }}
                        {% if student.name.startswith('[DEMO]') %}
                            <span class="demo-badge">演示</span>
                        {% endif %}
                    </td>
                    <td>{{ "%.1f"|format(student.participation_rate) }}%</td>
                    <td>{{ student.message_count }}</td>
                    <td>{{ student.question_count }}</td>
                    <td>
                        {% if student.last_active %}
                            {{ student.last_active.strftime('%m-%d %H:%M') }}
                        {% else %}
                            無記錄
                        {% endif %}
                    </td>
                    <td>
                        <a href="/student/{{ student.id }}" class="view-link">查看詳情</a>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" style="text-align: center; color: #666; padding: 40px;">
                        暫無學生資料。<br>
                        <small>當學生開始使用系統後，這裡將顯示他們的資料。</small>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

def get_system_status():
    """取得系統狀態"""
    status = {
        'database': 'disconnected',
        'templates': WEB_TEMPLATES_AVAILABLE,
        'linebot': line_bot_api is not None,
        'ai': bool(os.getenv('GEMINI_API_KEY'))
    }
    
    try:
        if db and not db.is_closed():
            status['database'] = 'connected'
        elif db:
            db.connect()
            status['database'] = 'connected'
    except:
        status['database'] = 'error'
    
    return status

def get_safe_stats():
    """安全地取得統計資料"""
    try:
        if Student and db and not db.is_closed():
            total_students = Student.select().count()
            total_messages = Message.select().count() if Message else 0
            return {
                'total_students': total_students,
                'total_messages': total_messages,
                'avg_engagement': 0
            }
    except:
        pass
    
    return {
        'total_students': 0,
        'total_messages': 0,
        'avg_engagement': 0
    }

def get_safe_students():
    """安全地取得學生列表"""
    try:
        if Student and db and not db.is_closed():
            students = list(Student.select().order_by(Student.last_active.desc()))
            return students
    except Exception as e:
        logger.error(f"取得學生列表錯誤: {e}")
    
    return []

# 路由定義
@app.route('/')
def index():
    """首頁"""
    try:
        system_status = get_system_status()
        stats = get_safe_stats()
        
        if WEB_TEMPLATES_AVAILABLE:
            from templates_main import INDEX_TEMPLATE
            template = INDEX_TEMPLATE
        else:
            template = FALLBACK_INDEX_TEMPLATE
        
        return render_template_string(
            template,
            system_status=system_status,
            stats=stats,
            current_time=datetime.datetime.now()
        )
    except Exception as e:
        logger.error(f"首頁錯誤: {e}")
        return render_template_string(
            FALLBACK_INDEX_TEMPLATE,
            system_status={'database': 'error', 'templates': False, 'linebot': False, 'ai': False},
            stats={'total_students': 0, 'total_messages': 0, 'avg_engagement': 0},
            current_time=datetime.datetime.now()
        ), 500

@app.route('/students')
def students():
    """學生列表"""
    try:
        students_data = get_safe_students()
        
        if WEB_TEMPLATES_AVAILABLE:
            from templates_main import STUDENTS_TEMPLATE
            template = STUDENTS_TEMPLATE
        else:
            template = FALLBACK_STUDENTS_TEMPLATE
        
        return render_template_string(template, students=students_data)
    except Exception as e:
        logger.error(f"學生列表錯誤: {e}")
        return render_template_string(
            FALLBACK_STUDENTS_TEMPLATE,
            students=[]
        )

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """學生詳細頁面"""
    try:
        if not Student:
            return "資料庫未初始化", 500
        
        student = Student.get_by_id(student_id)
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(10)) if Message else []
        
        # 簡化版學生詳情頁面
        simple_template = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>{{ student.name }} - 學習分析</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 40px;
            background: linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%);
            color: #333;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .back-btn {
            background: #007bff;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 8px;
            margin-bottom: 20px;
            display: inline-block;
        }
        .student-header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stat-card {
            background: #e3f2fd;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #1976d2;
        }
        .messages-section {
            margin-top: 30px;
        }
        .message-item {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }
        .message-meta {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/students" class="back-btn">← 返回學生列表</a>
        
        <div class="student-header">
            <h1>{{ student.name }}</h1>
            {% if student.name.startswith('[DEMO]') %}
            <p style="color: #28a745; font-weight: bold;">演示學生資料</p>
            {% endif %}
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ "%.1f"|format(student.participation_rate) }}%</div>
                <div>參與度</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ student.message_count }}</div>
                <div>總訊息數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ student.question_count }}</div>
                <div>問題數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ "%.1f"|format(student.question_rate) }}%</div>
                <div>提問率</div>
            </div>
        </div>
        
        <div class="messages-section">
            <h3>📝 最近訊息</h3>
            {% for message in messages %}
            <div class="message-item">
                <div class="message-meta">
                    {{ message.timestamp.strftime('%Y-%m-%d %H:%M') }} - {{ message.message_type }}
                </div>
                <div>{{ message.content[:100] }}{% if message.content|length > 100 %}...{% endif %}</div>
            </div>
            {% else %}
            <div style="text-align: center; color: #666; padding: 40px;">
                暫無訊息記錄
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
        '''
        
        return render_template_string(simple_template, student=student, messages=messages)
        
    except Student.DoesNotExist:
        return "學生未找到", 404
    except Exception as e:
        logger.error(f"學生詳細頁面錯誤: {e}")
        return f"載入學生資料時發生錯誤: {str(e)}", 500

@app.route('/health')
def health_check():
    """健康檢查"""
    try:
        system_status = get_system_status()
        stats = get_safe_stats()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'system_status': system_status,
            'stats': stats,
            'environment': {
                'DATABASE_URL': 'configured' if os.getenv('DATABASE_URL') else 'not_configured',
                'GEMINI_API_KEY': 'configured' if os.getenv('GEMINI_API_KEY') else 'not_configured',
                'LINE_ACCESS_TOKEN': 'configured' if os.getenv('CHANNEL_ACCESS_TOKEN') else 'not_configured'
            }
        })
    except Exception as e:
        logger.error(f"健康檢查錯誤: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

@app.route('/stats')
def get_stats_page():
    """統計資料頁面"""
    try:
        stats = get_safe_stats()
        system_status = get_system_status()
        
        stats_template = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>系統統計 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .back-btn {
            background: #007bff;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 8px;
            margin-bottom: 20px;
            display: inline-block;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stat-card {
            background: #e3f2fd;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #1976d2;
            margin-bottom: 10px;
        }
        .system-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .info-item {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← 返回首頁</a>
        <h1>📊 系統統計</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_students }}</div>
                <div>總學生數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_messages }}</div>
                <div>總訊息數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.avg_engagement }}%</div>
                <div>平均參與度</div>
            </div>
        </div>
        
        <div class="system-info">
            <h3>🔧 系統狀態</h3>
            <div class="info-item">
                <span>資料庫：</span>
                <span style="color: {{ '#28a745' if system_status.database == 'connected' else '#dc3545' }}">
                    {{ system_status.database }}
                </span>
            </div>
            <div class="info-item">
                <span>模板系統：</span>
                <span style="color: {{ '#28a745' if system_status.templates else '#ffc107' }}">
                    {{ '正常' if system_status.templates else '簡化模式' }}
                </span>
            </div>
            <div class="info-item">
                <span>LINE Bot：</span>
                <span style="color: {{ '#28a745' if system_status.linebot else '#6c757d' }}">
                    {{ '已配置' if system_status.linebot else '未配置' }}
                </span>
            </div>
            <div class="info-item">
                <span>AI 服務：</span>
                <span style="color: {{ '#28a745' if system_status.ai else '#6c757d' }}">
                    {{ '已配置' if system_status.ai else '未配置' }}
                </span>
            </div>
            <div class="info-item">
                <span>更新時間：</span>
                <span>{{ current_time.strftime('%Y-%m-%d %H:%M:%S') }}</span>
            </div>
        </div>
    </div>
</body>
</html>
        '''
        
        return render_template_string(
            stats_template,
            stats=stats,
            system_status=system_status,
            current_time=datetime.datetime.now()
        )
    except Exception as e:
        logger.error(f"統計頁面錯誤: {e}")
        return f"載入統計資料時發生錯誤: {str(e)}", 500

@app.route('/api/sync-all-students')
def sync_all_students():
    """同步所有學生統計"""
    try:
        if not Student:
            return jsonify({
                'success': False,
                'error': '資料庫未初始化'
            }), 500
        
        students = list(Student.select())
        updated_count = 0
        
        for student in students:
            try:
                # 簡化的統計更新
                if Message:
                    messages = list(Message.select().where(Message.student == student))
                    student.message_count = len(messages)
                    student.question_count = len([m for m in messages if m.message_type == 'question'])
                    student.question_rate = (student.question_count / max(student.message_count, 1)) * 100
                    student.last_active = datetime.datetime.now()
                    student.save()
                    updated_count += 1
            except Exception as e:
                logger.error(f"更新學生 {student.name} 統計錯誤: {e}")
                continue
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'成功同步 {updated_count} 位學生的統計資料'
        })
    except Exception as e:
        logger.error(f"同步學生統計錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# LINE Bot 回調（如果可用）
@app.route("/callback", methods=['POST'])
def callback():
    """LINE Bot Webhook"""
    if not handler:
        return jsonify({'error': 'LINE Bot 未配置'}), 503
    
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
        return 'OK'
    except Exception as e:
        logger.error(f"LINE Bot 回調錯誤: {e}")
        abort(400)

# 錯誤處理
@app.errorhandler(404)
def not_found_error(error):
    """404 錯誤處理"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    
    error_template = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>頁面未找到 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 100px 20px;
            margin: 0;
            min-height: 100vh;
        }
        .error-container {
            max-width: 600px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 4em; margin-bottom: 20px; }
        p { font-size: 1.2em; margin-bottom: 30px; }
        a {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 25px;
            transition: all 0.3s ease;
        }
        a:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1>404</h1>
        <p>抱歉，您請求的頁面不存在</p>
        <a href="/">返回首頁</a>
    </div>
</body>
</html>
    '''
    return render_template_string(error_template), 404

@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    logger.error(f"Internal server error: {error}")
    
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    
    error_template = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>系統錯誤 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            text-align: center;
            padding: 100px 20px;
            margin: 0;
            min-height: 100vh;
        }
        .error-container {
            max-width: 600px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 4em; margin-bottom: 20px; }
        p { font-size: 1.2em; margin-bottom: 30px; }
        a {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 25px;
            transition: all 0.3s ease;
        }
        a:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
        .error-details {
            background: rgba(0, 0, 0, 0.2);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: left;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1>500</h1>
        <p>系統發生內部錯誤</p>
        <div class="error-details">
            <strong>可能的原因：</strong><br>
            • 資料庫連線問題<br>
            • 模板載入失敗<br>
            • 環境變數配置錯誤<br>
            • 依賴模組缺失
        </div>
        <a href="/">返回首頁</a>
        <a href="/health" style="margin-left: 15px;">檢查系統狀態</a>
    </div>
</body>
</html>
    '''
    return render_template_string(error_template), 500

# 初始化函數
def initialize_app():
    """初始化應用程式"""
    logger.info("🚀 開始初始化 EMI 智能教學助理...")
    
    # 嘗試載入各個元件
    models_ok = safe_import_models()
    templates_ok = safe_import_templates()
    linebot_ok = safe_import_linebot()
    
    logger.info(f"📊 初始化結果:")
    logger.info(f"  - 資料庫模型: {'✅' if models_ok else '❌'}")
    logger.info(f"  - 模板系統: {'✅' if templates_ok else '❌'}")
    logger.info(f"  - LINE Bot: {'✅' if linebot_ok else '❌'}")
    logger.info(f"  - AI 服務: {'✅' if os.getenv('GEMINI_API_KEY') else '❌'}")
    
    # 創建範例資料（如果資料庫可用且為空）
    if models_ok:
        try:
            if Student.select().count() == 0:
                logger.info("🎯 創建範例資料...")
                from utils import create_sample_data
                create_sample_data()
                logger.info("✅ 範例資料創建完成")
        except Exception as e:
            logger.warning(f"⚠️ 範例資料創建失敗: {e}")
    
    return {
        'models': models_ok,
        'templates': templates_ok,
        'linebot': linebot_ok,
        'ai': bool(os.getenv('GEMINI_API_KEY'))
    }

# 應用程式啟動
if __name__ == "__main__":
    # 初始化應用程式
    init_result = initialize_app()
    
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🌐 啟動 Web 服務器...")
    logger.info(f"📍 URL: http://localhost:{port}")
    logger.info(f"🔧 模式: {'開發' if debug else '生產'}")
    
    if not any(init_result.values()):
        logger.warning("⚠️ 系統在最小化模式下運行")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

# WSGI 進入點
application = app
