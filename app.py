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
            
            # 計算百分比值
            english_percentage = (avg_english or 0) * 100
            
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
                        <strong>{english_percentage:.0f}%</strong>
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
        
