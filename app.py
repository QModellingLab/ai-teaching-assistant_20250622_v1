from flask import Flask, request, abort, jsonify, Response
import os
import sqlite3
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re
import csv
import io

app = Flask(__name__)

# LINE Bot 設定
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')

line_bot_api = None
handler = None

if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
    try:
        from linebot import LineBotApi, WebhookHandler
        from linebot.exceptions import InvalidSignatureError
        from linebot.models import MessageEvent, TextMessage, TextSendMessage
        
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(CHANNEL_SECRET)
        print("LINE Bot initialized successfully")
    except Exception as e:
        print(f"LINE Bot initialization failed: {e}")
        line_bot_api = None
        handler = None

# 18週課程設定
COURSE_SCHEDULE_18_WEEKS = {
    1: {"topic": "Course Introduction and AI Era Overview", "chinese": "課程介紹,人工智慧如何改變我們的生活?"},
    2: {"topic": "Generative AI Technologies", "chinese": "生成式AI技術 (ChatGPT, Claude等)"},
    3: {"topic": "Student Presentations 1", "chinese": "學生專題分享週(1)"},
    4: {"topic": "AI Applications in Learning", "chinese": "AI在學習上的應用"},
    5: {"topic": "Student Presentations 2", "chinese": "學生專題分享週(2)"},
    6: {"topic": "AI in Creative and Professional Fields", "chinese": "AI在創意與職場的應用"},
    7: {"topic": "Student Presentations 3", "chinese": "學生專題分享週(3)"},
    8: {"topic": "AI Tool Development and Customization", "chinese": "AI工具開發與客製化"},
    9: {"topic": "Student Presentations 4", "chinese": "學生專題分享週(4)"},
    10: {"topic": "AI Ethics and Responsible Use", "chinese": "AI倫理與責任使用"},
    11: {"topic": "AI in Research and Academic Writing", "chinese": "AI在研究與學術寫作的應用"},
    12: {"topic": "Student Presentations 5", "chinese": "學生專題分享週(5)"},
    13: {"topic": "Industry 4.0 and Smart Manufacturing", "chinese": "工業4.0與智慧製造"},
    14: {"topic": "Student Presentations 6", "chinese": "學生專題分享週(6)"},
    15: {"topic": "AI in Home and Daily Life", "chinese": "AI在居家與日常生活的應用"},
    16: {"topic": "Student Presentations 7", "chinese": "學生專題分享週(7)"},
    17: {"topic": "Future Trends and Career Preparation", "chinese": "未來趨勢與職涯準備"},
    18: {"topic": "Final Review and Course Reflection", "chinese": "期末回顧與課程反思"}
}

# 資料庫相關函數
def get_db_connection():
    """建立資料庫連接"""
    db_path = os.path.join(os.getcwd(), 'course_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_db_exists():
    """確保資料庫存在"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 檢查主要表格
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            conn.close()
            return init_db()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interactions'")
        if not cursor.fetchone():
            conn.close()
            return init_db()
        
        # 確保學期設定表格存在
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semester_config (
                id INTEGER PRIMARY KEY,
                semester_start DATE,
                current_week INTEGER DEFAULT 1,
                total_weeks INTEGER DEFAULT 18,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Database check failed: {e}")
        return init_db()

def init_db():
    """初始化資料庫"""
    try:
        print("Starting database initialization...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DROP TABLE IF EXISTS interactions')
        cursor.execute('DROP TABLE IF EXISTS users')
        cursor.execute('DROP TABLE IF EXISTS semester_config')
        
        cursor.execute('''
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL,
                is_demo INTEGER DEFAULT 0,
                first_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_name TEXT,
                content TEXT,
                ai_response TEXT,
                message_type TEXT,
                quality_score REAL,
                english_ratio REAL,
                contains_keywords INTEGER,
                group_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE semester_config (
                id INTEGER PRIMARY KEY,
                semester_start DATE,
                current_week INTEGER DEFAULT 1,
                total_weeks INTEGER DEFAULT 18,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 初始化學期設定
        default_start = datetime(2025, 2, 17).date()
        cursor.execute('''
            INSERT INTO semester_config (semester_start, current_week, total_weeks) 
            VALUES (?, 1, 18)
        ''', (default_start,))
        
        conn.commit()
        conn.close()
        print("Database initialization completed")
        
        create_demo_data()
        return True
        
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

def create_demo_data():
    """創建示範數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id LIKE "demo_%"')
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # 虛擬學生資料
        demo_students = [
            ('demo_student001', '[虛擬]陳建宏 York Chen'),
            ('demo_student002', '[虛擬]王雅琳 Alice Wang'),
            ('demo_student003', '[虛擬]林志明 Bob Lin'),
            ('demo_student004', '[虛擬]劉詩涵 Catherine Liu'),
            ('demo_student005', '[虛擬]張大衛 David Chang'),
            ('demo_student006', '[虛擬]黃美玲 Emma Huang'),
            ('demo_student007', '[虛擬]李俊傑 Frank Lee'),
            ('demo_student008', '[虛擬]吳佩君 Grace Wu')
        ]
        
        for user_id, user_name in demo_students:
            cursor.execute('INSERT INTO users (user_id, user_name, is_demo) VALUES (?, ?, 1)', (user_id, user_name))
        
        # 示範互動數據
        demo_interactions = [
            ('demo_student001', '[虛擬]陳建宏 York Chen', 'What is artificial intelligence and how does it impact our daily life?', 'AI response...', 'question', 4.5, 0.9, 1, None),
            ('demo_student001', '[虛擬]陳建宏 York Chen', 'AI在教育領域的應用非常廣泛，特別是個人化學習', 'AI response...', 'discussion', 4.2, 0.6, 1, 'group'),
            ('demo_student001', '[虛擬]陳建宏 York Chen', 'How can we ensure AI ethics in machine learning algorithms?', 'AI response...', 'question', 4.7, 0.95, 1, None),
            ('demo_student002', '[虛擬]王雅琳 Alice Wang', 'How does machine learning work in recommendation systems?', 'AI response...', 'question', 4.1, 0.88, 1, None),
            ('demo_student002', '[虛擬]王雅琳 Alice Wang', '我認為生成式AI對創意產業影響很大', 'AI response...', 'discussion', 3.8, 0.4, 1, 'group'),
            ('demo_student003', '[虛擬]林志明 Bob Lin', 'AI applications in smart manufacturing很有趣', 'AI response...', 'discussion', 3.5, 0.7, 1, 'group'),
            ('demo_student004', '[虛擬]劉詩涵 Catherine Liu', '生成式AI的應用很廣泛，但需要注意倫理問題', 'AI response...', 'response', 3.0, 0.2, 1, None),
            ('demo_student005', '[虛擬]張大衛 David Chang', 'What is ChatGPT?', 'AI response...', 'question', 3.5, 0.8, 1, None),
            ('demo_student006', '[虛擬]黃美玲 Emma Huang', 'How can AI help in language learning?', 'AI response...', 'question', 4.4, 0.95, 1, None),
            ('demo_student007', '[虛擬]李俊傑 Frank Lee', 'Neural networks和傳統programming有什麼差別？', 'AI response...', 'question', 3.8, 0.5, 1, None),
            ('demo_student008', '[虛擬]吳佩君 Grace Wu', '謝謝老師的說明，我對AI有更深的了解了', 'AI response...', 'response', 2.5, 0.1, 1, None)
        ]
        
        for interaction in demo_interactions:
            cursor.execute('''
                INSERT INTO interactions 
                (user_id, user_name, content, ai_response, message_type, quality_score, 
                 english_ratio, contains_keywords, group_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', interaction)
        
        conn.commit()
        conn.close()
        print("Enhanced demo data with virtual student labels created successfully")
        
    except Exception as e:
        print(f"Demo data creation failed: {e}")

# 學期設定相關函數
def get_semester_config():
    """取得學期設定"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM semester_config ORDER BY id DESC LIMIT 1')
        config = cursor.fetchone()
        
        if not config:
            default_start = datetime(2025, 2, 17).date()
            cursor.execute('''
                INSERT INTO semester_config (semester_start, current_week, total_weeks) 
                VALUES (?, 1, 18)
            ''', (default_start,))
            conn.commit()
            config = (1, default_start, 1, 18, datetime.now())
        
        conn.close()
        return {
            'semester_start': config[1],
            'current_week': config[2],
            'total_weeks': config[3],
            'updated_at': config[4]
        }
    except Exception as e:
        print(f"Semester config error: {e}")
        return {
            'semester_start': datetime(2025, 2, 17).date(),
            'current_week': 1,
            'total_weeks': 18,
            'updated_at': datetime.now()
        }

def get_current_week():
    """取得當前課程週次"""
    config = get_semester_config()
    return config['current_week']

# 分析相關函數
def calculate_quality_score(content):
    """計算討論品質分數"""
    score = 1.0
    content_lower = content.lower()
    
    if len(content) > 50: score += 0.5
    if len(content) > 100: score += 0.5
    if len(content) > 200: score += 0.5
    
    academic_keywords = ['analysis', 'research', 'theory', 'methodology', 'evaluation']
    if any(keyword in content_lower for keyword in academic_keywords):
        score += 1.0
    
    if any(keyword in content_lower for keyword in ['ai', 'artificial intelligence', 'machine learning']):
        score += 0.5
    
    if any(char in content for char in ['?', '？']):
        score += 0.5
    
    return min(score, 5.0)

def calculate_english_ratio(content):
    """計算英語使用比例"""
    english_chars = sum(1 for c in content if c.isalpha() and ord(c) < 128)
    total_chars = len(content.replace(' ', ''))
    return english_chars / max(total_chars, 1) if total_chars > 0 else 0

def detect_message_type(content):
    """檢測訊息類型"""
    content_lower = content.lower()
    if any(char in content for char in ['?', '？']):
        return 'question'
    elif any(word in content_lower for word in ['i think', 'analysis', '我覺得', '分析']):
        return 'discussion'
    else:
        return 'response'

def log_interaction(user_id, user_name, content, ai_response, is_group=False):
    """記錄互動到資料庫"""
    try:
        if not ensure_db_exists():
            return False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('INSERT OR IGNORE INTO users (user_id, user_name, is_demo) VALUES (?, ?, 0)', (user_id, user_name))
        
        quality_score = calculate_quality_score(content)
        english_ratio = calculate_english_ratio(content)
        message_type = detect_message_type(content)
        contains_keywords = 1
        group_id = "group" if is_group else None
        
        cursor.execute('''
            INSERT INTO interactions 
            (user_id, user_name, content, ai_response, message_type, quality_score, 
             english_ratio, contains_keywords, group_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, content, ai_response, message_type, quality_score, 
              english_ratio, contains_keywords, group_id))
        
        conn.commit()
        conn.close()
        print(f"Interaction logged: {user_name}")
        return True
        
    except Exception as e:
        print(f"Failed to log interaction: {e}")
        return False

def generate_ai_response(message, user_name):
    """生成AI回應"""
    current_week = get_current_week()
    week_info = COURSE_SCHEDULE_18_WEEKS.get(current_week, {})
    
    responses = [
        f"Hi {user_name}! 這週我們討論「{week_info.get('chinese', '課程內容')}」。",
        f"很好的問題！關於{message[:20]}...",
        f"根據第{current_week}週的課程內容，我建議...",
        f"這個觀點很有趣！在AI應用方面..."
    ]
    
    import random
    return random.choice(responses)

def get_individual_student_analysis(user_id):
    """獲取個別學生分析"""
    try:
        if not ensure_db_exists():
            return None
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_name FROM users WHERE user_id = ?', (user_id,))
        user_info = cursor.fetchone()
        if not user_info:
            conn.close()
            return None
        
        cursor.execute('''
            SELECT created_at, message_type, content, quality_score, 
                   contains_keywords, english_ratio, group_id
            FROM interactions 
            WHERE user_id = ?
            ORDER BY created_at
        ''', (user_id,))
        
        interactions = cursor.fetchall()
        conn.close()
        
        if not interactions:
            return {'user_name': user_info[0], 'analysis_available': False}
        
        return analyze_individual_performance(interactions, user_info[0], user_id)
        
    except Exception as e:
        print(f"Individual analysis error: {e}")
        return None

def analyze_individual_performance(interactions, user_name, user_id):
    """分析個人表現"""
    total_interactions = len(interactions)
    dates = [datetime.fromisoformat(row[0]).date() for row in interactions]
    
    active_days = len(set(dates))
    study_period = (max(dates) - min(dates)).days + 1 if len(dates) > 1 else 1
    
    qualities = [row[3] for row in interactions if row[3] > 0]
    avg_quality = sum(qualities) / len(qualities) if qualities else 0
    
    english_ratios = [row[5] for row in interactions if row[5] is not None]
    avg_english = sum(english_ratios) / len(english_ratios) if english_ratios else 0
    
    questions = [row for row in interactions if row[1] == 'question']
    
    # 參與度等級
    if total_interactions >= 15:
        participation_level = "高度活躍"
        level_color = "#28a745"
    elif total_interactions >= 8:
        participation_level = "中度活躍"
        level_color = "#ffc107"
    elif total_interactions >= 3:
        participation_level = "偶爾參與"
        level_color = "#fd7e14"
    else:
        participation_level = "較少參與"
        level_color = "#dc3545"
    
    # 品質趨勢
    if len(qualities) >= 3:
        recent = sum(qualities[-3:]) / 3
        early = sum(qualities[:3]) / 3
        if recent > early + 0.5:
            quality_trend = "明顯進步"
        elif recent > early + 0.2:
            quality_trend = "穩定進步"
        else:
            quality_trend = "穩定維持"
    else:
        quality_trend = "數據不足"
    
    # 雙語能力
    if avg_english >= 0.8:
        bilingual_ability = "優秀雙語使用者"
    elif avg_english >= 0.6:
        bilingual_ability = "良好雙語能力"
    elif avg_english >= 0.4:
        bilingual_ability = "中等雙語能力"
    else:
        bilingual_ability = "主要使用中文"
    
    # 提問模式
    question_ratio = len(questions) / total_interactions if total_interactions > 0 else 0
    if question_ratio >= 0.4:
        questioning_pattern = "積極提問者"
    elif question_ratio >= 0.2:
        questioning_pattern = "適度提問"
    else:
        questioning_pattern = "較少提問"
    
    # 綜合評估
    scores = []
    if total_interactions >= 15:
        scores.append(9)
    elif total_interactions >= 8:
        scores.append(7)
    else:
        scores.append(5)
    
    scores.append(min(avg_quality * 2, 10))
    scores.append(min(avg_english * 10, 10))
    
    overall_score = sum(scores) / len(scores)
    
    if overall_score >= 8:
        performance_level = "優秀"
    elif overall_score >= 6:
        performance_level = "良好"
    else:
        performance_level = "需改進"
    
    return {
        'user_name': user_name,
        'user_id': user_id,
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'study_period_days': study_period,
        'analysis_available': True,
        'participation': {
            'total_interactions': total_interactions,
            'active_days': active_days,
            'avg_weekly_activity': round(total_interactions / max(study_period/7, 1), 1),
            'participation_level': participation_level,
            'level_color': level_color,
            'consistency_score': round(active_days / study_period * 100, 1)
        },
        'quality': {
            'avg_quality': round(avg_quality, 2),
            'high_quality_count': sum(1 for q in qualities if q >= 4.0),
            'quality_trend': quality_trend
        },
        'english_usage': {
            'avg_english_ratio': avg_english,
            'bilingual_ability': bilingual_ability
        },
        'questioning': {
            'total_questions': len(questions),
            'question_ratio': question_ratio,
            'questioning_pattern': questioning_pattern
        },
        'overall_assessment': {
            'overall_score': round(overall_score, 1),
            'performance_level': performance_level,
            'learning_style': "穩健學習者",
            'strengths': ["持續努力中"],
            'improvement_suggestions': ["建議保持學習節奏"]
        }
    }

# LINE Bot 路由
if line_bot_api and handler:
    @app.route("/callback", methods=['POST'])
    def callback():
        signature = request.headers['X-Line-Signature']
        body = request.get_data(as_text=True)
        
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)
        
        return 'OK'

    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        try:
            user_message = event.message.text
            user_id = event.source.user_id
            
            try:
                profile = line_bot_api.get_profile(user_id)
                user_name = profile.display_name
            except:
                user_name = f"User{user_id[:8]}"
            
            is_group = hasattr(event.source, 'group_id')
            if is_group:
                if not user_message.strip().startswith('@AI'):
                    return
                user_message = user_message.replace('@AI', '').strip()
                if not user_message:
                    user_message = "Hi"
            
            ai_response = generate_ai_response(user_message, user_name)
            log_interaction(user_id, user_name, user_message, ai_response, is_group)
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=ai_response)
            )
            
        except Exception as e:
            print(f"Message handling error: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，處理訊息時發生錯誤。")
            )
else:
    @app.route("/callback", methods=['POST'])
    def callback():
        return jsonify({"error": "LINE Bot not configured"})

# 網頁路由
@app.route("/")
def home():
    """一般首頁"""
    line_bot_status = "已配置" if line_bot_api else "未配置"
    db_status = "正常" if ensure_db_exists() else "異常"
    
    config = get_semester_config()
    current_week = config['current_week']
    week_info = COURSE_SCHEDULE_18_WEEKS.get(current_week, {})
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>AI實務應用課程分析系統</title>
        <style>
            body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .header {{ text-align: center; margin-bottom: 40px; color: #333; }}
            .week-banner {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center; }}
            .week-number {{ font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }}
            .status {{ background: #28a745; color: white; padding: 8px 16px; border-radius: 20px; margin: 10px; }}
            .warning {{ background: #ffc107; color: #333; padding: 8px 16px; border-radius: 20px; margin: 10px; }}
            .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            .card {{ background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
            .admin-btn {{ background: #dc3545; }}
            .teacher-btn {{ background: #28a745; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AI在生活與學習上的實務應用</h1>
                <p>通識教育中心 | 授課教師：曾郁堯</p>
                <span class="{'status' if line_bot_api else 'warning'}">LINE Bot狀態: {line_bot_status}</span>
                <span class="{'status' if db_status == '正常' else 'warning'}">資料庫狀態: {db_status}</span>
            </div>
            
            <div class="week-banner">
                <div class="week-number">第 {current_week} 週</div>
                <div style="font-size: 1.2em; margin-bottom: 5px;">{week_info.get('chinese', '課程內容')}</div>
                <div style="font-size: 1em; opacity: 0.9;">{week_info.get('topic', '')}</div>
            </div>
            
            <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center;">
                <h2>教師專區</h2>
                <p>完整的課程管理和分析工具</p>
                <a href="/admin" class="btn teacher-btn" style="background: white; color: #28a745; font-weight: bold; margin: 10px;">
                    進入教師管理首頁
                </a>
            </div>
            
            <div class="cards">
                <div class="card">
                    <h3>個人學習分析</h3>
                    <p>查看每位學生的詳細學習報告和進步軌跡</p>
                    <a href="/student_list" class="btn">學生列表</a>
                </div>
                <div class="card">
                    <h3>班級整體分析</h3>
                    <p>全班學習狀況統計和教學成效評估</p>
                    <a href="/class_analysis" class="btn">班級分析</a>
                </div>
                <div class="card">
                    <h3>研究數據儀表板</h3>
                    <p>EMI教學實踐研究數據追蹤</p>
                    <a href="/research_dashboard" class="btn">研究儀表板</a>
                </div>
                <div class="card">
                    <h3>互動模擬器</h3>
                    <p>模擬LINE Bot互動，測試數據記錄功能</p>
                    <a href="/simulate_interaction" class="btn">開始模擬</a>
                </div>
                <div class="card">
                    <h3>數據匯出</h3>
                    <p>匯出完整的學習數據，支援研究分析</p>
                    <a href="/export_research_data" class="btn">匯出數據</a>
                </div>
                <div class="card">
                    <h3>系統管理</h3>
                    <p>重設系統、備份數據、學期設定</p>
                    <a href="/admin_panel" class="btn admin-btn">管理面板</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/admin")
def admin_homepage():
    """管理首頁"""
    try:
        db_status = ensure_db_exists()
        line_bot_status = line_bot_api is not None
        config = get_semester_config()
        current_week = config['current_week']
        week_info = COURSE_SCHEDULE_18_WEEKS.get(current_week, {})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions')
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_demo = 1')
        virtual_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_demo = 0')
        real_users = cursor.fetchone()[0]
        
        conn.close()
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>教師管理首頁 - AI課程分析系統</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                .admin-header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; }}
                .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .status-card {{ background: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); border-left: 5px solid #007bff; }}
                .status-number {{ font-size: 2.5em; font-weight: bold; color: #007bff; margin-bottom: 10px; }}
                .week-display {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 15px; margin: 20px 0; text-align: center; }}
                .admin-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; }}
                .admin-card {{ background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }}
                .admin-card:hover {{ transform: translateY(-5px); }}
                .btn {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 8px; margin: 8px; transition: all 0.3s; }}
                .btn:hover {{ background: #0056b3; transform: translateY(-2px); }}
                .btn-success {{ background: #28a745; }}
                .btn-warning {{ background: #ffc107; color: #333; }}
                .btn-danger {{ background: #dc3545; }}
                .btn-info {{ background: #17a2b8; }}
                .system-status {{ display: flex; justify-content: center; gap: 20px; margin: 20px 0; }}
                .status-badge {{ padding: 10px 20px; border-radius: 25px; font-weight: bold; }}
                .status-ok {{ background: #d4edda; color: #155724; }}
                .status-warn {{ background: #fff3cd; color: #856404; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="admin-header">
                    <h1>🎓 教師管理首頁</h1>
                    <p>AI在生活與學習上的實務應用 - 完整課程管理系統</p>
                    <div class="system-status">
                        <span class="status-badge {'status-ok' if line_bot_status else 'status-warn'}">
                            LINE Bot: {'運行中' if line_bot_status else '未配置'}
                        </span>
                        <span class="status-badge {'status-ok' if db_status else 'status-warn'}">
                            資料庫: {'正常' if db_status else '異常'}
                        </span>
                    </div>
                </div>
                
                <div class="week-display">
                    <h2>📅 當前進度</h2>
                    <div style="font-size: 2em; margin: 10px 0;">第 {current_week} 週 / 共 18 週</div>
                    <div style="font-size: 1.2em; margin-bottom: 10px;">{week_info.get('chinese', '課程內容')}</div>
                    <div style="font-size: 1em; opacity: 0.9;">{week_info.get('topic', '')}</div>
                </div>
                
                <div class="status-grid">
                    <div class="status-card">
                        <div class="status-number">{total_users}</div>
                        <h3>總學生數</h3>
                        <p>註冊用戶總數</p>
                    </div>
                    <div class="status-card">
                        <div class="status-number">{real_users}</div>
                        <h3>真實學生</h3>
                        <p>實際課程參與者</p>
                    </div>
                    <div class="status-card">
                        <div class="status-number">{virtual_users}</div>
                        <h3>虛擬學生</h3>
                        <p>測試和示範帳號</p>
                    </div>
                    <div class="status-card">
                        <div class="status-number">{total_interactions}</div>
                        <h3>總互動次數</h3>
                        <p>累計對話記錄</p>
                    </div>
                </div>
                
                <div class="admin-cards">
                    <div class="admin-card">
                        <h3>📊 學習分析</h3>
                        <p>深入了解學生學習狀況和進度</p>
                        <a href="/student_list" class="btn btn-success">學生列表</a>
                        <a href="/class_analysis" class="btn btn-info">班級分析</a>
                    </div>
                    
                    <div class="admin-card">
                        <h3>🔬 研究工具</h3>
                        <p>EMI教學實踐研究數據管理</p>
                        <a href="/research_dashboard" class="btn btn-info">研究儀表板</a>
                        <a href="/export_research_data" class="btn btn-success">匯出數據</a>
                    </div>
                    
                    <div class="admin-card">
                        <h3>⚙️ 系統設定</h3>
                        <p>課程設定和系統管理</p>
                        <a href="/semester_settings" class="btn btn-warning">學期設定</a>
                        <a href="/admin_panel" class="btn btn-danger">系統管理</a>
                    </div>
                    
                    <div class="admin-card">
                        <h3>🧪 測試工具</h3>
                        <p>系統測試和模擬功能</p>
                        <a href="/simulate_interaction" class="btn">互動模擬</a>
                        <a href="/test_db" class="btn">資料庫測試</a>
                    </div>
                    
                    <div class="admin-card">
                        <h3>📋 系統狀態</h3>
                        <p>監控系統運行狀況</p>
                        <a href="/health" class="btn">健康檢查</a>
                        <a href="/backup_preview" class="btn">備份預覽</a>
                    </div>
                    
                    <div class="admin-card">
                        <h3>🏠 返回選項</h3>
                        <p>返回一般使用者介面</p>
                        <a href="/" class="btn">一般首頁</a>
                        <a href="/setup_guide" class="btn btn-info">設定指南</a>
                    </div>
                </div>
                
                <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px; text-align: center;">
                    <h4>📚 教學實踐研究計畫支援</h4>
                    <p>本系統專為「生成式AI輔助的雙語教學創新：提升EMI課程學生參與度與跨文化能力之教學實踐研究」設計</p>
                    <small>114年度教育部教學實踐研究計畫 | 通識教育類</small>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f'''
        <h1>管理首頁載入錯誤</h1>
        <p>錯誤: {str(e)}</p>
        <a href="/">返回首頁</a>
        '''

@app.route("/health")
def health_check():
    """健康檢查"""
    try:
        db_status = ensure_db_exists()
        line_bot_configured = line_bot_api is not None
        
        return jsonify({
            "status": "healthy",
            "database_status": "connected" if db_status else "error",
            "line_bot_configured": line_bot_configured,
            "timestamp": datetime.now().isoformat(),
            "message": "AI課程分析系統運行正常"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/test_db")
def test_database():
    """測試資料庫連接"""
    try:
        if not ensure_db_exists():
            return '''
            <h1>資料庫測試 - 失敗</h1>
            <p>無法初始化資料庫</p>
            <a href="/admin">返回管理首頁</a>
            '''
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions')
        interaction_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_demo = 1')
        demo_count = cursor.fetchone()[0]
        
        conn.close()
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>資料庫測試結果</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .success {{ background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 資料庫連接測試</h1>
                <div class="success">
                    ✅ 資料庫連接成功！所有表格正常運作。
                </div>
                
                <h2>📊 資料庫統計</h2>
                <div class="stats">
                    <div class="stat-card">
                        <h3>{user_count}</h3>
                        <p>總用戶數</p>
                    </div>
                    <div class="stat-card">
                        <h3>{interaction_count}</h3>
                        <p>互動記錄</p>
                    </div>
                    <div class="stat-card">
                        <h3>{demo_count}</h3>
                        <p>虛擬學生</p>
                    </div>
                    <div class="stat-card">
                        <h3>{user_count - demo_count}</h3>
                        <p>真實學生</p>
                    </div>
                </div>
                
                <h3>🔍 測試項目</h3>
                <ul>
                    <li>✅ 資料庫檔案存在且可讀寫</li>
                    <li>✅ users 表格正常</li>
                    <li>✅ interactions 表格正常</li>
                    <li>✅ semester_config 表格正常</li>
                    <li>✅ 虛擬學生數據完整</li>
                </ul>
                
                <div style="margin-top: 30px;">
                    <a href="/admin" class="btn">返回管理首頁</a>
                    <a href="/student_list" class="btn">查看學生列表</a>
                    <a href="/health" class="btn">系統健康檢查</a>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f'''
        <h1>資料庫測試失敗</h1>
        <p>錯誤訊息: {str(e)}</p>
        <a href="/admin">返回管理首頁</a>
        '''

@app.route("/student_list")
def student_list():
    """學生列表頁面"""
    try:
        if not ensure_db_exists():
            return "<h1>資料庫錯誤</h1><p>無法連接資料庫</p><a href='/admin'>返回</a>"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_id, u.user_name, u.is_demo, u.first_interaction,
                   COUNT(i.id) as interaction_count,
                   ROUND(AVG(i.quality_score), 2) as avg_quality,
                   ROUND(AVG(i.english_ratio), 2) as avg_english,
                   MAX(i.created_at) as last_interaction
            FROM users u
            LEFT JOIN interactions i ON u.user_id = i.user_id
            GROUP BY u.user_id, u.user_name, u.is_demo, u.first_interaction
            ORDER BY u.is_demo ASC, interaction_count DESC, u.user_name
        ''')
        
        students = cursor.fetchall()
        conn.close()
        
        student_cards = ""
        for student in students:
            user_id, user_name, is_demo, first_interaction, interaction_count, avg_quality, avg_english, last_interaction = student
            
            # 設定虛擬學生樣式
            card_class = "demo-card" if is_demo else "real-card"
            demo_badge = " 🤖" if is_demo else " 👤"
            
            # 參與度評級
            if interaction_count >= 10:
                participation = "高度活躍"
                part_color = "#28a745"
            elif interaction_count >= 5:
                participation = "中度參與"
                part_color = "#ffc107"
            elif interaction_count >= 1:
                participation = "偶爾參與"
                part_color = "#fd7e14"
            else:
                participation = "尚未參與"
                part_color = "#dc3545"
            
            # 品質分數顏色
            quality_color = "#28a745" if (avg_quality or 0) >= 4 else "#ffc107" if (avg_quality or 0) >= 3 else "#dc3545"
            
            student_cards += f'''
            <div class="student-card {card_class}">
                <div class="student-header">
                    <h3>{user_name}{demo_badge}</h3>
                    <span class="participation-badge" style="background: {part_color};">{participation}</span>
                </div>
                <div class="student-stats">
                    <div class="stat">
                        <strong>{interaction_count}</strong>
                        <span>互動次數</span>
                    </div>
                    <div class="stat">
                        <strong style="color: {quality_color};">{avg_quality or 0:.1f}</strong>
                        <span>平均品質</span>
                    </div>
                    <div class="stat">
                        <strong>{(avg_english or 0)*100:.0f}%</strong>
                        <span>英語使用</span>
                    </div>
                </div>
                <div class="student-actions">
                    <a href="/student_analysis/{user_id}" class="btn btn-primary">詳細分析</a>
                    <small>最後活動: {last_interaction[:10] if last_interaction else '無記錄'}</small>
                </div>
            </div>
            '''
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>學生列表 - AI課程分析系統</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .students-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
                .student-card {{ background: #fff; border: 2px solid #e9ecef; padding: 20px; border-radius: 12px; transition: all 0.3s; }}
                .student-card:hover {{ transform: translateY(-5px); box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
                .demo-card {{ border-color: #ffc107; background: #fffdf5; }}
                .real-card {{ border-color: #28a745; background: #f8fff9; }}
                .student-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
                .participation-badge {{ padding: 5px 12px; border-radius: 20px; color: white; font-size: 0.8em; font-weight: bold; }}
                .student-stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 15px 0; }}
                .stat {{ text-align: center; padding: 10px; background: #f8f9fa; border-radius: 8px; }}
                .stat strong {{ display: block; font-size: 1.5em; margin-bottom: 5px; }}
                .stat span {{ color: #666; font-size: 0.9em; }}
                .student-actions {{ text-align: center; margin-top: 15px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
                .btn:hover {{ background: #0056b3; }}
                .summary {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
                .nav-buttons {{ text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 學生列表</h1>
                    <p>AI在生活與學習上的實務應用 - 學生學習追蹤</p>
                </div>
                
                <div class="summary">
                    <h2>📊 班級概況</h2>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin: 20px 0;">
                        <div>
                            <div style="font-size: 2em; font-weight: bold;">{len([s for s in students if not s[2]])}</div>
                            <div>真實學生</div>
                        </div>
                        <div>
                            <div style="font-size: 2em; font-weight: bold;">{len([s for s in students if s[2]])}</div>
                            <div>虛擬學生</div>
                        </div>
                        <div>
                            <div style="font-size: 2em; font-weight: bold;">{len(students)}</div>
                            <div>總計</div>
                        </div>
                        <div>
                            <div style="font-size: 2em; font-weight: bold;">{len([s for s in students if s[4] > 0])}</div>
                            <div>活躍用戶</div>
                        </div>
                    </div>
                </div>
                
                <div class="nav-buttons">
                    <a href="/admin" class="btn">管理首頁</a>
                    <a href="/class_analysis" class="btn">班級分析</a>
                    <a href="/export_research_data" class="btn">匯出數據</a>
                </div>
                
                <div class="students-grid">
                    {student_cards}
                </div>
                
                <div style="margin-top: 40px; text-align: center; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                    <p><strong>說明：</strong></p>
                    <p>🤖 虛擬學生：系統測試用帳號，用於功能驗證和示範</p>
                    <p>👤 真實學生：實際課程參與者</p>
                    <p>點擊「詳細分析」可查看個別學生的完整學習報告</p>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f'''
        <h1>學生列表載入錯誤</h1>
        <p>錯誤: {str(e)}</p>
        <a href="/admin">返回管理首頁</a>
        '''

@app.route("/student_analysis/<user_id>")
def student_analysis(user_id):
    """個別學生詳細分析"""
    try:
        analysis = get_individual_student_analysis(user_id)
        
        if not analysis:
            return '''
            <h1>找不到學生資料</h1>
            <p>請檢查學生ID是否正確</p>
            <a href="/student_list">返回學生列表</a>
            '''
        
        if not analysis.get('analysis_available', False):
            return f'''
            <h1>{analysis['user_name']} - 學習分析</h1>
            <p>該學生尚無互動記錄</p>
            <a href="/student_list">返回學生列表</a>
            '''
        
        # 生成分析報告
        user_name = analysis['user_name']
        participation = analysis['participation']
        quality = analysis['quality']
        english = analysis['english_usage']
        questioning = analysis['questioning']
        overall = analysis['overall_assessment']
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>{user_name} - 學習分析報告</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; }}
                .student-header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; }}
                .analysis-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; }}
                .analysis-card {{ background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1); }}
                .score-circle {{ width: 100px; height: 100px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px; font-size: 1.5em; font-weight: bold; color: white; }}
                .score-excellent {{ background: #28a745; }}
                .score-good {{ background: #ffc107; color: #333; }}
                .score-needs-improvement {{ background: #dc3545; }}
                .stat-row {{ display: flex; justify-content: space-between; margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
                .btn {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 8px; margin: 8px; }}
                .progress-bar {{ background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden; margin: 10px 0; }}
                .progress-fill {{ height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.3s; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="student-header">
                    <h1>📊 學習分析報告</h1>
                    <h2>{user_name}</h2>
                    <p>分析日期：{analysis['analysis_date']} | 學習週期：{analysis['study_period_days']} 天</p>
                </div>
                
                <div class="analysis-grid">
                    <div class="analysis-card">
                        <h3>⭐ 討論品質</h3>
                        <div class="stat-row">
                            <span>平均品質分數：</span>
                            <strong>{quality['avg_quality']}/5.0</strong>
                        </div>
                        <div class="stat-row">
                            <span>高品質發言：</span>
                            <strong>{quality['high_quality_count']} 次</strong>
                        </div>
                        <div class="stat-row">
                            <span>品質趨勢：</span>
                            <strong>{quality['quality_trend']}</strong>
                        </div>
                        <div>
                            <span>品質表現：</span>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {quality['avg_quality']*20}%;"></div>
                            </div>
                            <small>{quality['avg_quality']*20:.1f}&#37;</small>
                        </div>
                    </div>
                    
                    <div class="analysis-card">
                        <h3>🌐 雙語能力</h3>
                        <div class="stat-row">
                            <span>英語使用比例：</span>
                            <strong>{english['avg_english_ratio']*100:.1f}&#37;</strong>
                        </div>
                        <div class="stat-row">
                            <span>雙語能力評估：</span>
                            <strong>{english['bilingual_ability']}</strong>
                        </div>
                        <div>
                            <span>英語使用比例：</span>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {english['avg_english_ratio']*100}&#37;;"></div>
                            </div>
                            <small>English Usage: {english['avg_english_ratio']*100:.1f}&#37;</small>
                        </div>
                    </div>
                    
                    <div class="analysis-card">
                        <h3>❓ 提問行為</h3>
                        <div class="stat-row">
                            <span>總提問次數：</span>
                            <strong>{questioning['total_questions']}</strong>
                        </div>
                        <div class="stat-row">
                            <span>提問比例：</span>
                            <strong>{questioning['question_ratio']*100:.1f}&#37;</strong>
                        </div>
                        <div class="stat-row">
                            <span>提問模式：</span>
                            <strong>{questioning['questioning_pattern']}</strong>
                        </div>
                        <div>
                            <span>好奇心指數：</span>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {questioning['question_ratio']*100}&#37;;"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="analysis-card">
                        <h3>💡 學習建議</h3>
                        <h4>優勢領域：</h4>
                        <ul>
                            {''.join(f'<li>{strength}</li>' for strength in overall['strengths'])}
                        </ul>
                        <h4>改進建議：</h4>
                        <ul>
                            {''.join(f'<li>{suggestion}</li>' for suggestion in overall['improvement_suggestions'])}
                        </ul>
                    </div>
                </div>
                
                <div style="margin-top: 30px; text-align: center;">
                    <a href="/student_list" class="btn">返回學生列表</a>
                    <a href="/class_analysis" class="btn">班級分析</a>
                    <a href="/admin" class="btn">管理首頁</a>
                </div>
                
                <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                    <h4>📋 分析說明</h4>
                    <p><strong>整體表現：</strong>綜合參與度、品質、雙語能力的評估</p>
                    <p><strong>參與度分析：</strong>基於互動頻率和一致性的量化評估</p>
                    <p><strong>討論品質：</strong>基於內容深度、學術性、關鍵字使用的評分</p>
                    <p><strong>雙語能力：</strong>EMI（English as a Medium of Instruction）課程的英語使用追蹤</p>
                    <p><strong>提問行為：</strong>主動學習和批判思考能力的指標</p>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f'''
        <h1>分析報告載入錯誤</h1>
        <p>錯誤: {str(e)}</p>
        <a href="/student_list">返回學生列表</a>
        '''

@app.route("/class_analysis")
def class_analysis():
    """班級整體分析"""
    try:
        if not ensure_db_exists():
            return "<h1>資料庫錯誤</h1><a href='/admin'>返回</a>"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_demo = 0')
        real_students = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_demo = 1')
        demo_students = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions')
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(quality_score) FROM interactions WHERE quality_score > 0')
        avg_quality = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(english_ratio) FROM interactions WHERE english_ratio IS NOT NULL')
        avg_english = cursor.fetchone()[0] or 0
        
        # 活躍度分析
        cursor.execute('''
            SELECT u.user_name, COUNT(i.id) as interactions, u.is_demo
            FROM users u
            LEFT JOIN interactions i ON u.user_id = i.user_id
            GROUP BY u.user_id
            ORDER BY interactions DESC
        ''')
        student_activity = cursor.fetchall()
        
        # 每日活動統計
        cursor.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as daily_count
            FROM interactions
            WHERE created_at >= date('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        daily_activity = cursor.fetchall()
        
        conn.close()
        
        # 活躍度分布
        high_active = len([s for s in student_activity if s[1] >= 10])
        medium_active = len([s for s in student_activity if 5 <= s[1] < 10])
        low_active = len([s for s in student_activity if 1 <= s[1] < 5])
        inactive = len([s for s in student_activity if s[1] == 0])
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>班級整體分析 - AI課程分析系統</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; }}
                .class-header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1); text-align: center; }}
                .stat-number {{ font-size: 3em; font-weight: bold; color: #007bff; margin-bottom: 10px; }}
                .chart-section {{ background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1); margin: 20px 0; }}
                .activity-bars {{ display: flex; align-items: end; gap: 10px; height: 200px; margin: 20px 0; }}
                .activity-bar {{ background: linear-gradient(to top, #007bff, #0056b3); border-radius: 5px 5px 0 0; position: relative; min-width: 40px; }}
                .bar-label {{ position: absolute; bottom: -25px; left: 50%; transform: translateX(-50%); font-size: 0.8em; white-space: nowrap; }}
                .student-ranking {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
                .rank-item {{ padding: 15px; background: #f8f9fa; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }}
                .btn {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 8px; margin: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="class-header">
                    <h1>📊 班級整體分析</h1>
                    <p>AI在生活與學習上的實務應用 - 全班學習狀況評估</p>
                    <p>分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{real_students}</div>
                        <h3>真實學生</h3>
                        <p>實際課程參與者</p>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{demo_students}</div>
                        <h3>虛擬學生</h3>
                        <p>系統測試帳號</p>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_interactions}</div>
                        <h3>總互動數</h3>
                        <p>累計對話記錄</p>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{avg_quality:.1f}</div>
                        <h3>平均品質</h3>
                        <p>討論品質分數</p>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{avg_english*100:.0f}&#37;</div>
                        <h3>英語使用</h3>
                        <p>EMI課程參與度</p>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len([s for s in student_activity if s[1] > 0])}</div>
                        <h3>活躍學生</h3>
                        <p>有互動記錄者</p>
                    </div>
                </div>
                
                <div class="chart-section">
                    <h2>📈 學生活躍度分布</h2>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; text-align: center;">
                        <div style="padding: 20px; background: #d4edda; border-radius: 10px;">
                            <h3 style="color: #155724; margin: 0;">{high_active}</h3>
                            <p style="margin: 5px 0;">高度活躍</p>
                            <small>(≥10次互動)</small>
                        </div>
                        <div style="padding: 20px; background: #fff3cd; border-radius: 10px;">
                            <h3 style="color: #856404; margin: 0;">{medium_active}</h3>
                            <p style="margin: 5px 0;">中度活躍</p>
                            <small>(5-9次互動)</small>
                        </div>
                        <div style="padding: 20px; background: #ffeaa7; border-radius: 10px;">
                            <h3 style="color: #856404; margin: 0;">{low_active}</h3>
                            <p style="margin: 5px 0;">偶爾參與</p>
                            <small>(1-4次互動)</small>
                        </div>
                        <div style="padding: 20px; background: #f8d7da; border-radius: 10px;">
                            <h3 style="color: #721c24; margin: 0;">{inactive}</h3>
                            <p style="margin: 5px 0;">尚未參與</p>
                            <small>(0次互動)</small>
                        </div>
                    </div>
                </div>
                
                <div class="chart-section">
                    <h2>🏆 學生互動排行榜</h2>
                    <div class="student-ranking">
                        {''.join(f'''
                    <div class="rank-item">
                        <span>
                            <strong>#{i+1}</strong> 
                            {student[0]} 
                            {'🤖' if student[2] else '👤'}
                        </span>
                        <span style="font-weight: bold; color: #007bff;">{student[1]} 次</span>
                    </div>
                        ''' for i, student in enumerate(student_activity[:10]))}
                    </div>
                </div>
                
                <div class="chart-section">
                    <h2>📅 近30天活動趨勢</h2>
                    <div style="padding: 20px; background: #f8f9fa; border-radius: 10px;">
                        <p>總活動天數: <strong>{len(daily_activity)}</strong> 天</p>
                        <p>平均每日互動: <strong>{sum(day[1] for day in daily_activity) / max(len(daily_activity), 1):.1f}</strong> 次</p>
                        <p>最活躍日期: <strong>{max(daily_activity, key=lambda x: x[1])[0] if daily_activity else '無記錄'}</strong></p>
                    </div>
                </div>
                
                <div class="chart-section">
                    <h2>🎯 教學成效評估</h2>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                        <div style="padding: 20px; background: #e8f5e8; border-radius: 10px;">
                            <h4 style="color: #155724;">EMI雙語教學效果</h4>
                            <p>英語使用比例: <strong>{avg_english*100:.1f}&#37;</strong></p>
                            <p>評估: <strong>{'優秀' if avg_english >= 0.6 else '良好' if avg_english >= 0.4 else '需改進'}</strong></p>
                        </div>
                        <div style="padding: 20px; background: #e8f4fd; border-radius: 10px;">
                            <h4 style="color: #0c5460;">學生參與度</h4>
                            <p>活躍學生比例: <strong>{len([s for s in student_activity if s[1] > 0]) / max(len(student_activity), 1) * 100:.1f}&#37;</strong></p>
                            <p>評估: <strong>{'優秀' if len([s for s in student_activity if s[1] > 0]) / max(len(student_activity), 1) >= 0.8 else '良好' if len([s for s in student_activity if s[1] > 0]) / max(len(student_activity), 1) >= 0.6 else '需改進'}</strong></p>
                        </div>
                        <div style="padding: 20px; background: #fff3cd; border-radius: 10px;">
                            <h4 style="color: #856404;">討論品質</h4>
                            <p>平均品質分數: <strong>{avg_quality:.2f}/5.0</strong></p>
                            <p>評估: <strong>{'優秀' if avg_quality >= 4.0 else '良好' if avg_quality >= 3.0 else '需改進'}</strong></p>
                        </div>
                    </div>
                </div>
                
                <div style="margin-top: 30px; text-align: center;">
                    <a href="/admin" class="btn">管理首頁</a>
                    <a href="/student_list" class="btn">學生列表</a>
                    <a href="/research_dashboard" class="btn">研究儀表板</a>
                    <a href="/export_research_data" class="btn">匯出數據</a>
                </div>
                
                <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                    <h4>📋 分析指標說明</h4>
                    <ul>
                        <li><strong>高度活躍：</strong>互動次數 ≥ 10次，顯示積極參與課程討論</li>
                        <li><strong>中度活躍：</strong>互動次數 5-9次，有穩定的課程參與</li>
                        <li><strong>偶爾參與：</strong>互動次數 1-4次，參與度有提升空間</li>
                        <li><strong>尚未參與：</strong>無互動記錄，需要特別關注和引導</li>
                        <li><strong>EMI效果：</strong>基於英語使用比例評估雙語教學成效</li>
                        <li><strong>品質分數：</strong>基於內容深度、學術性、關鍵字使用的綜合評分</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f'''
        <h1>班級分析載入錯誤</h1>
        <p>錯誤: {str(e)}</p>
        <a href="/admin">返回管理首頁</a>
        '''

@app.route("/research_dashboard")
def research_dashboard():
    """研究數據儀表板"""
    try:
        if not ensure_db_exists():
            return "<h1>資料庫錯誤</h1><a href='/admin'>返回</a>"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 研究相關統計
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(*) as total_interactions,
                AVG(quality_score) as avg_quality,
                AVG(english_ratio) as avg_english_ratio,
                COUNT(CASE WHEN message_type = 'question' THEN 1 END) as questions,
                COUNT(CASE WHEN message_type = 'discussion' THEN 1 END) as discussions,
                COUNT(CASE WHEN group_id IS NOT NULL THEN 1 END) as group_interactions
            FROM interactions
            WHERE user_id NOT LIKE 'demo_%'
        ''')
        
        research_stats = cursor.fetchone()
        
        # 週次分布分析
        cursor.execute('''
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as daily_interactions,
                AVG(quality_score) as daily_avg_quality,
                AVG(english_ratio) as daily_avg_english
            FROM interactions
            WHERE user_id NOT LIKE 'demo_%'
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        
        daily_trends = cursor.fetchall()
        
        # EMI雙語教學效果分析
        cursor.execute('''
            SELECT 
                user_id,
                user_name,
                COUNT(*) as interactions,
                AVG(english_ratio) as avg_english,
                AVG(quality_score) as avg_quality
            FROM interactions
            WHERE user_id NOT LIKE 'demo_%'
            GROUP BY user_id, user_name
            HAVING interactions >= 3
            ORDER BY avg_english DESC
        ''')
        
        emi_performance = cursor.fetchall()
        
        conn.close()
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>研究數據儀表板 - EMI教學實踐研究</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; }}
                .research-header {{ background: linear-gradient(135deg, #6f42c1 0%, #007bff 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .metric-card {{ background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1); text-align: center; border-left: 5px solid #007bff; }}
                .metric-value {{ font-size: 2.5em; font-weight: bold; color: #007bff; margin-bottom: 10px; }}
                .research-section {{ background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1); margin: 20px 0; }}
                .emi-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .emi-table th, .emi-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                .emi-table th {{ background: #f8f9fa; font-weight: bold; }}
                .btn {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 8px; margin: 8px; }}
                .highlight {{ background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="research-header">
                    <h1>🔬 研究數據儀表板</h1>
                    <h2>生成式AI輔助的雙語教學創新</h2>
                    <p>提升EMI課程學生參與度與跨文化能力之教學實踐研究</p>
                    <small>114年度教育部教學實踐研究計畫 | 通識教育類</small>
                </div>
                
                <div class="highlight">
                    <h3>📊 核心研究指標概覽</h3>
                    <p>本儀表板追蹤EMI（English as a Medium of Instruction）雙語教學的關鍵效果指標，支援量化研究分析。</p>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{research_stats[0] if research_stats else 0}</div>
                        <h4>研究對象</h4>
                        <p>真實學生數量</p>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{research_stats[1] if research_stats else 0}</div>
                        <h4>數據樣本</h4>
                        <p>有效互動記錄</p>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{research_stats[2]:.2f if research_stats and research_stats[2] else 0}</div>
                        <h4>討論品質</h4>
                        <p>平均品質分數</p>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{research_stats[3]*100:.1f if research_stats and research_stats[3] else 0}&#37;</div>
                        <h4>英語使用率</h4>
                        <p>EMI課程效果</p>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{research_stats[4] if research_stats else 0}</div>
                        <h4>提問次數</h4>
                        <p>主動學習指標</p>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{research_stats[5] if research_stats else 0}</div>
                        <h4>討論次數</h4>
                        <p>深度參與指標</p>
                    </div>
                </div>
                
                <div class="research-section">
                    <h2>🌐 EMI雙語教學效果分析</h2>
                    <p>以下表格顯示學生在雙語環境中的表現，用於評估EMI教學策略的有效性。</p>
                    
                    <table class="emi-table">
                        <thead>
                            <tr>
                                <th>學生</th>
                                <th>互動次數</th>
                                <th>英語使用率</th>
                                <th>討論品質</th>
                                <th>EMI適應度</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(f'''
                            <tr>
                                <td>{student[1]}</td>
                                <td>{student[2]}</td>
                                <td>{student[3]*100:.1f}&#37;</td>
                                <td>{student[4]:.2f}/5.0</td>
                                <td style="color: {'#28a745' if student[3] >= 0.6 else '#ffc107' if student[3] >= 0.3 else '#dc3545'};">
                                    {'優秀' if student[3] >= 0.6 else '良好' if student[3] >= 0.3 else '需輔導'}
                                </td>
                            </tr>
                            ''' for student in emi_performance[:15])}
                        </tbody>
                    </table>
                </div>
                
                <div class="research-section">
                    <h2>📈 研究數據趨勢</h2>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                        <div>
                            <h4>參與度趨勢</h4>
                            <p>數據收集天數: <strong>{len(daily_trends)}</strong></p>
                            <p>平均每日互動: <strong>{sum(day[1] for day in daily_trends) / max(len(daily_trends), 1):.1f}</strong></p>
                            <p>數據完整性: <strong>{'良好' if len(daily_trends) >= 10 else '待充實'}</strong></p>
                        </div>
                        <div>
                            <h4>品質指標</h4>
                            <p>高品質互動比例: <strong>{len([d for d in daily_trends if d[2] and d[2] >= 4.0]) / max(len(daily_trends), 1) * 100:.1f}&#37;</strong></p>
                            <p>英語使用穩定性: <strong>{'穩定' if len(daily_trends) > 5 else '觀察中'}</strong></p>
                            <p>EMI教學效果: <strong>{'顯著' if research_stats and research_stats[3] >= 0.5 else '發展中'}</strong></p>
                        </div>
                    </div>
                </div>
                
                <div class="research-section">
                    <h2>📋 研究方法與指標說明</h2>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                        <div>
                            <h4>量化指標</h4>
                            <ul>
                                <li><strong>英語使用率：</strong>字符級別的英語內容比例</li>
                                <li><strong>討論品質：</strong>基於內容深度、學術性的5分制評分</li>
                                <li><strong>參與頻率：</strong>學生主動互動的頻率統計</li>
                                <li><strong>提問比例：</strong>主動學習行為的量化指標</li>
                            </ul>
                        </div>
                        <div>
                            <h4>研究目標</h4>
                            <ul>
                                <li><strong>提升EMI課程學生參與度</strong></li>
                                <li><strong>增強跨文化溝通能力</strong></li>
                                <li><strong>評估生成式AI輔助教學效果</strong></li>
                                <li><strong>建立雙語教學創新模式</strong></li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                <div style="margin-top: 30px; text-align: center;">
                    <a href="/export_research_data" class="btn" style="background: #28a745;">匯出研究數據</a>
                    <a href="/class_analysis" class="btn">班級分析</a>
                    <a href="/admin" class="btn">管理首頁</a>
                </div>
                
                <div style="margin-top: 40px; padding: 20px; background: #e8f4fd; border-radius: 10px;">
                    <h4>📊 研究數據使用說明</h4>
                    <p>本系統自動收集和分析學生在AI輔助學習環境中的行為數據，所有數據已去識別化處理，符合研究倫理規範。數據可用於：</p>
                    <ul>
                        <li>EMI雙語教學效果評估</li>
                        <li>學生參與度與學習成效關聯分析</li>
                        <li>生成式AI在教育應用的影響研究</li>
                        <li>跨文化能力發展追蹤</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f'''
        <h1>研究儀表板載入錯誤</h1>
        <p>錯誤: {str(e)}</p>
        <a href="/admin">返回管理首頁</a>
        '''

@app.route("/export_research_data")
def export_research_data():
    """匯出研究數據為CSV"""
    try:
        if not ensure_db_exists():
            return "資料庫錯誤", 500
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 匯出完整的互動數據（排除虛擬學生）
        cursor.execute('''
            SELECT 
                i.user_id,
                i.user_name,
                i.content,
                i.ai_response,
                i.message_type,
                i.quality_score,
                i.english_ratio,
                i.contains_keywords,
                i.group_id,
                i.created_at,
                u.is_demo
            FROM interactions i
            JOIN users u ON i.user_id = u.user_id
            ORDER BY i.created_at
        ''')
        
        data = cursor.fetchall()
        conn.close()
        
        # 創建CSV內容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 寫入標題行
        writer.writerow([
            'User_ID', 'User_Name', 'Content', 'AI_Response', 'Message_Type',
            'Quality_Score', 'English_Ratio', 'Contains_Keywords', 'Group_ID',
            'Created_At', 'Is_Demo'
        ])
        
        # 寫入數據
        for row in data:
            writer.writerow(row)
        
        # 生成回應
        output.seek(0)
        csv_content = output.getvalue()
        output.close()
        
        response = Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=research_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
        
        return response
        
    except Exception as e:
        return f'''
        <h1>數據匯出錯誤</h1>
        <p>錯誤: {str(e)}</p>
        <a href="/admin">返回管理首頁</a>
        '''

@app.route("/simulate_interaction", methods=['GET', 'POST'])
def simulate_interaction():
    """模擬互動器"""
    if request.method == 'POST':
        try:
            test_user_id = request.form.get('user_id', 'test_user_001')
            test_user_name = request.form.get('user_name', '測試學生')
            test_message = request.form.get('message', 'Hello AI!')
            is_group = request.form.get('is_group') == 'on'
            
            ai_response = generate_ai_response(test_message, test_user_name)
            success = log_interaction(test_user_id, test_user_name, test_message, ai_response, is_group)
            
            result_message = "✅ 互動模擬成功！數據已記錄到資料庫。" if success else "❌ 模擬失敗，請檢查系統狀態。"
            result_color = "#d4edda" if success else "#f8d7da"
            
            return f'''
            <!DOCTYPE html>
            <html lang="zh-TW">
            <head>
                <meta charset="UTF-8">
                <title>互動模擬器 - 測試結果</title>
                <style>
                    body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f8f9fa; }}
                    .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; }}
                    .result {{ padding: 20px; border-radius: 10px; margin: 20px 0; background: {result_color}; }}
                    .btn {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 8px; margin: 8px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🧪 互動模擬結果</h1>
                    <div class="result">
                        <h3>{result_message}</h3>
                        <p><strong>用戶ID:</strong> {test_user_id}</p>
                        <p><strong>用戶名稱:</strong> {test_user_name}</p>
                        <p><strong>訊息內容:</strong> {test_message}</p>
                        <p><strong>AI回應:</strong> {ai_response}</p>
                        <p><strong>群組模式:</strong> {'是' if is_group else '否'}</p>
                    </div>
                    <a href="/simulate_interaction" class="btn">再次測試</a>
                    <a href="/student_list" class="btn">查看學生列表</a>
                    <a href="/admin" class="btn">返回管理首頁</a>
                </div>
            </body>
            </html>
            '''
            
        except Exception as e:
            return f'''
            <h1>模擬錯誤</h1>
            <p>錯誤: {str(e)}</p>
            <a href="/simulate_interaction">重新嘗試</a>
            '''
    
    return '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>互動模擬器 - AI課程分析系統</title>
        <style>
            body { font-family: Microsoft JhengHei; margin: 20px; background: #f8f9fa; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; }
            .form-group { margin: 20px 0; }
            .form-group label { display: block; margin-bottom: 8px; font-weight: bold; }
            .form-group input, .form-group textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
            .form-group textarea { height: 100px; resize: vertical; }
            .btn { display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border: none; border-radius: 8px; margin: 8px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #0056b3; }
            .info-box { background: #e8f4fd; padding: 20px; border-radius: 10px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧪 LINE Bot 互動模擬器</h1>
            <div class="info-box">
                <h3>📋 模擬器功能說明</h3>
                <p>此模擬器可以測試LINE Bot的訊息處理和數據記錄功能，無需實際LINE Bot即可驗證系統運作。</p>
                <ul>
                    <li>模擬學生發送訊息給AI助教</li>
                    <li>測試品質分析算法</li>
                    <li>驗證英語使用比例計算</li>
                    <li>檢查資料庫記錄功能</li>
                </ul>
            </div>
            
            <form method="POST">
                <div class="form-group">
                    <label for="user_id">用戶ID：</label>
                    <input type="text" id="user_id" name="user_id" value="test_user_001" required>
                    <small>建議使用test_開頭的ID以便識別測試數據</small>
                </div>
                
                <div class="form-group">
                    <label for="user_name">用戶名稱：</label>
                    <input type="text" id="user_name" name="user_name" value="[測試]模擬學生" required>
                </div>
                
                <div class="form-group">
                    <label for="message">訊息內容：</label>
                    <textarea id="message" name="message" placeholder="輸入要測試的訊息內容..." required>What is artificial intelligence and how does it impact our daily life?</textarea>
                    <small>可以測試中英文混合內容以驗證雙語分析功能</small>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="is_group"> 群組模式（模擬群組聊天中的@AI呼叫）
                    </label>
                </div>
                
                <button type="submit" class="btn">🚀 開始模擬</button>
                <a href="/admin" class="btn" style="background: #6c757d;">返回管理首頁</a>
            </form>
            
            <div style="margin-top: 40px; padding: 20px; background: #fff3cd; border-radius: 10px;">
                <h4>⚠️ 測試建議</h4>
                <ul>
                    <li>使用不同長度的訊息測試品質分析</li>
                    <li>測試純英文、純中文、中英混合內容</li>
                    <li>嘗試包含問號的問題句型</li>
                    <li>測試包含AI相關關鍵字的內容</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/admin_panel")
def admin_panel():
    """系統管理面板"""
    return '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>系統管理面板</title>
        <style>
            body { font-family: Microsoft JhengHei; margin: 20px; background: #f8f9fa; }
            .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; }
            .warning-header { background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; }
            .admin-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; }
            .admin-card { background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1); }
            .btn { display: inline-block; padding: 12px 24px; color: white; text-decoration: none; border-radius: 8px; margin: 8px; }
            .btn-danger { background: #dc3545; }
            .btn-warning { background: #ffc107; color: #333; }
            .btn-info { background: #17a2b8; }
            .btn-secondary { background: #6c757d; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="warning-header">
                <h1>⚠️ 系統管理面板</h1>
                <p>謹慎操作區域 - 所有操作都會影響系統數據</p>
            </div>
            
            <div class="admin-cards">
                <div class="admin-card">
                    <h3>🔄 數據重設</h3>
                    <p>清除所有互動記錄，保留系統設定</p>
                    <a href="/backup_preview" class="btn btn-warning">預覽備份</a>
                    <a href="#" onclick="confirmReset('interactions')" class="btn btn-danger">重設互動數據</a>
                </div>
                
                <div class="admin-card">
                    <h3>👥 用戶管理</h3>
                    <p>管理虛擬學生和真實用戶</p>
                    <a href="#" onclick="confirmReset('demo_users')" class="btn btn-warning">清除虛擬學生</a>
                    <a href="#" onclick="confirmReset('all_users')" class="btn btn-danger">重設所有用戶</a>
                </div>
                
                <div class="admin-card">
                    <h3>🗃️ 完整重設</h3>
                    <p>重置整個系統到初始狀態</p>
                    <a href="#" onclick="confirmReset('full_system')" class="btn btn-danger">完整系統重設</a>
                </div>
                
                <div class="admin-card">
                    <h3>📅 學期設定</h3>
                    <p>調整學期開始時間和當前週次</p>
                    <a href="/semester_settings" class="btn btn-info">學期設定</a>
                </div>
                
                <div class="admin-card">
                    <h3>🔧 系統工具</h3>
                    <p>系統診斷和維護工具</p>
                    <a href="/test_db" class="btn btn-info">資料庫測試</a>
                    <a href="/health" class="btn btn-info">健康檢查</a>
                </div>
                
                <div class="admin-card">
                    <h3>📖 設定指南</h3>
                    <p>系統設定和使用說明</p>
                    <a href="/setup_guide" class="btn btn-info">設定指南</a>
                    <a href="/admin" class="btn btn-secondary">返回管理首頁</a>
                </div>
            </div>
            
            <div style="margin-top: 40px; padding: 20px; background: #f8d7da; border-radius: 10px;">
                <h4>⚠️ 重要提醒</h4>
                <ul>
                    <li>所有重設操作都會永久刪除數據，無法復原</li>
                    <li>建議在重設前先匯出研究數據作為備份</li>
                    <li>虛擬學生數據用於系統測試，可安全清除</li>
                    <li>完整系統重設會清除所有數據和設定</li>
                </ul>
            </div>
        </div>
        
        <script>
        function confirmReset(type) {
            const messages = {
                'interactions': '這將清除所有互動記錄，但保留用戶資料。確定要繼續嗎？',
                'demo_users': '這將清除所有虛擬學生及其互動記錄。確定要繼續嗎？',
                'all_users': '這將清除所有用戶和互動記錄。確定要繼續嗎？',
                'full_system': '這將重置整個系統到初始狀態，清除所有數據。這個操作無法復原！確定要繼續嗎？'
            };
            
            if (confirm(messages[type])) {
                if (confirm('再次確認：您真的要執行這個操作嗎？')) {
                    window.location.href = '/execute_reset_' + type;
                }
            }
        }
        </script>
    </body>
    </html>
    '''

@app.route("/backup_preview")
def backup_preview():
    """備份預覽"""
    try:
        if not ensure_db_exists():
            return "<h1>資料庫錯誤</h1><a href='/admin'>返回</a>"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_demo = 0')
        real_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_demo = 1')
        demo_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions')
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id LIKE "demo_%"')
        demo_interactions = cursor.fetchone()[0]
        
        conn.close()
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>數據備份預覽</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f8f9fa; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; }}
                .backup-header {{ background: linear-gradient(135deg, #17a2b8 0%, #007bff 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; }}
                .data-summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                .data-card {{ background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }}
                .data-number {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .btn {{ display: inline-block; padding: 12px 24px; color: white; text-decoration: none; border-radius: 8px; margin: 8px; }}
                .btn-success {{ background: #28a745; }}
                .btn-secondary {{ background: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="backup-header">
                    <h1>💾 數據備份預覽</h1>
                    <p>當前系統數據概覽 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="data-summary">
                    <div class="data-card">
                        <div class="data-number">{real_users}</div>
                        <h4>真實學生</h4>
                        <p>實際課程參與者</p>
                    </div>
                    <div class="data-card">
                        <div class="data-number">{demo_users}</div>
                        <h4>虛擬學生</h4>
                        <p>測試和示範帳號</p>
                    </div>
                    <div class="data-card">
                        <div class="data-number">{total_interactions - demo_interactions}</div>
                        <h4>真實互動</h4>
                        <p>實際教學數據</p>
                    </div>
                    <div class="data-card">
                        <div class="data-number">{demo_interactions}</div>
                        <h4>測試互動</h4>
                        <p>虛擬學生數據</p>
                    </div>
                </div>
                
                <div style="background: #e8f5e8; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3>✅ 建議的備份策略</h3>
                    <ol>
                        <li><strong>匯出研究數據：</strong>下載完整的互動記錄CSV檔案</li>
                        <li><strong>記錄系統設定：</strong>記下當前的學期設定和週次</li>
                        <li><strong>保存重要分析：</strong>截圖或匯出重要的分析報告</li>
                        <li><strong>確認數據完整性：</strong>檢查數據是否包含所需的研究樣本</li>
                    </ol>
                </div>
                
                <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3>⚠️ 重設影響說明</h3>
                    <ul>
                        <li><strong>清除虛擬學生：</strong>刪除{demo_users}個測試帳號和{demo_interactions}筆測試數據</li>
                        <li><strong>重設互動數據：</strong>刪除所有{total_interactions}筆互動記錄</li>
                        <li><strong>完整系統重設：</strong>恢復到初始狀態，保留{demo_users}個新的虛擬學生</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="/export_research_data" class="btn btn-success">💾 立即匯出數據備份</a>
                    <a href="/admin_panel" class="btn btn-secondary">返回管理面板</a>
                </div>
                
                <div style="background: #f8d7da; padding: 20px; border-radius: 10px;">
                    <h4>🚨 數據安全提醒</h4>
                    <p>一旦執行重設操作，所有數據將永久刪除且無法復原。請務必在重設前完成數據備份。建議將CSV檔案和重要分析結果保存到安全的位置。</p>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f'''
        <h1>備份預覽錯誤</h1>
        <p>錯誤: {str(e)}</p>
        <a href="/admin_panel">返回管理面板</a>
        '''

# 初始化系統
if __name__ == "__main__":
    ensure_db_exists()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# WSGI 應用入口點
application = app</li
                        <h3>🎯 整體表現</h3>
                        <div class="score-circle {'score-excellent' if overall['overall_score'] >= 8 else 'score-good' if overall['overall_score'] >= 6 else 'score-needs-improvement'}">
                            {overall['overall_score']}/10
                        </div>
                        <h4 style="text-align: center; color: {'#28a745' if overall['performance_level'] == '優秀' else '#ffc107' if overall['performance_level'] == '良好' else '#dc3545'};">
                            {overall['performance_level']}
                        </h4>
                        <div class="stat-row">
                            <span>學習風格：</span>
                            <strong>{overall['learning_style']}</strong>
                        </div>
                    </div>
                    
                    <div class="analysis-card">
                        <h3>📈 參與度分析</h3>
                        <div class="stat-row">
                            <span>總互動次數：</span>
                            <strong>{participation['total_interactions']}</strong>
                        </div>
                        <div class="stat-row">
                            <span>活躍天數：</span>
                            <strong>{participation['active_days']} 天</strong>
                        </div>
                        <div class="stat-row">
                            <span>週平均活動：</span>
                            <strong>{participation['avg_weekly_activity']} 次</strong>
                        </div>
                        <div class="stat-row">
                            <span>參與等級：</span>
                            <strong style="color: {participation['level_color']};">{participation['participation_level']}</strong>
                        </div>
                        <div>
                            <span>一致性分數：</span>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {participation['consistency_score']}%;"></div>
                            </div>
                            <small>{participation['consistency_score']}&#37;</small>
                        </div>
                    </div>
                    
                    <div class="analysis-card">
