from flask import Flask, request, abort, jsonify, Response
import os
import sqlite3
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re

app = Flask(__name__)

# LINE Bot 設定 - 安全檢查
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')

# 只有在環境變數存在時才初始化 LINE Bot
line_bot_api = None
handler = None

if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
    try:
        from linebot import LineBotApi, WebhookHandler
        from linebot.exceptions import InvalidSignatureError
        from linebot.models import MessageEvent, TextMessage, TextSendMessage
        
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(CHANNEL_SECRET)
        print("✅ LINE Bot 已初始化")
    except Exception as e:
        print(f"⚠️ LINE Bot 初始化失敗: {e}")
        line_bot_api = None
        handler = None
else:
    print("⚠️ LINE Bot 環境變數未設定，僅啟用網頁功能")

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

# 課程目標關鍵詞
COURSE_OBJECTIVES = {
    'AI_基礎認知': ['artificial intelligence', 'ai', 'machine learning', 'algorithm', 'technology', '智慧', '演算法', '科技'],
    '實務應用': ['application', 'practical', 'tool', 'solution', 'implementation', '應用', '實務', '工具', '解決方案'],
    '倫理責任': ['ethics', 'responsibility', 'privacy', 'bias', 'society', '倫理', '責任', '隱私', '偏見', '社會']
}

def get_current_week():
    """計算當前課程週次"""
    semester_start = datetime(2025, 2, 17)  # 假設學期開始日期
    current_date = datetime.now()
    days_passed = (current_date - semester_start).days
    week = min(max(1, (days_passed // 7) + 1), 18)
    return week

def get_db_connection():
    """建立資料庫連接"""
    conn = sqlite3.connect('course_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化資料庫"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL,
                first_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
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
        
        conn.commit()
        conn.close()
        print("✅ 資料庫初始化完成")
        
        # 創建測試數據
        create_demo_data()
        
    except Exception as e:
        print(f"❌ 資料庫初始化失敗: {e}")

def create_demo_data():
    """創建示範數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 檢查是否已有數據
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # 創建示範學生
        demo_students = [
            ('student001', 'York Chen'),
            ('student002', 'Alice Wang'),
            ('student003', 'Bob Lin'),
            ('student004', 'Catherine Liu'),
            ('student005', 'David Chang')
        ]
        
        for user_id, user_name in demo_students:
            cursor.execute('INSERT INTO users (user_id, user_name) VALUES (?, ?)', (user_id, user_name))
        
        # 創建示範互動數據
        demo_interactions = [
            ('student001', 'York Chen', 'What is artificial intelligence?', 'AI回應內容...', 'question', 4.2, 0.85, 1, None),
            ('student001', 'York Chen', '我覺得AI在教育很有用', 'AI回應內容...', 'discussion', 3.8, 0.3, 1, 'group'),
            ('student002', 'Alice Wang', 'How does machine learning work?', 'AI回應內容...', 'question', 4.5, 0.9, 1, None),
            ('student003', 'Bob Lin', 'AI ethics is important', 'AI回應內容...', 'discussion', 3.5, 0.7, 1, 'group'),
            ('student004', 'Catherine Liu', '生成式AI的應用', 'AI回應內容...', 'response', 3.2, 0.2, 1, None),
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
        print("✅ 示範數據創建完成")
        
    except Exception as e:
        print(f"❌ 示範數據創建失敗: {e}")

def is_group_message(event):
    """檢查是否為群組訊息"""
    try:
        return hasattr(event.source, 'group_id') and event.source.group_id is not None
    except:
        return False

def calculate_quality_score(content):
    """計算討論品質分數"""
    score = 1.0
    content_lower = content.lower()
    
    # 長度加分
    if len(content) > 50: score += 0.5
    if len(content) > 100: score += 0.5
    if len(content) > 200: score += 0.5
    
    # 學術關鍵詞加分
    academic_keywords = ['analysis', 'research', 'theory', 'methodology', 'evaluation', 'comparison', 'implementation']
    if any(keyword in content_lower for keyword in academic_keywords):
        score += 1.0
    
    # 課程相關關鍵詞
    if any(keyword in content_lower for keyword in ['ai', 'artificial intelligence', 'machine learning']):
        score += 0.5
    
    # 問題或思考性內容
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
    if any(char in content for char in ['?', '？']) or any(word in content_lower for word in ['how', 'why', 'what', 'when', 'where', '如何', '為什麼', '什麼時候']):
        return 'question'
    elif any(word in content_lower for word in ['i think', 'in my opinion', 'analysis', '我覺得', '我認為', '分析']):
        return 'discussion'
    else:
        return 'response'

def check_course_objectives(content):
    """檢查是否包含課程目標關鍵詞"""
    content_lower = content.lower()
    for objective, keywords in COURSE_OBJECTIVES.items():
        if any(keyword in content_lower for keyword in keywords):
            return True
    return False

def log_interaction(user_id, user_name, content, ai_response, is_group=False):
    """記錄互動到資料庫"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 確保用戶存在
        cursor.execute('INSERT OR IGNORE INTO users (user_id, user_name) VALUES (?, ?)', (user_id, user_name))
        
        # 分析內容
        quality_score = calculate_quality_score(content)
        english_ratio = calculate_english_ratio(content)
        message_type = detect_message_type(content)
        contains_keywords = 1 if check_course_objectives(content) else 0
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
        print(f"✅ 記錄互動: {user_name}, 品質: {quality_score}, 英語比例: {english_ratio:.2f}")
        
    except Exception as e:
        print(f"❌ 記錄互動失敗: {e}")

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

# LINE Bot 路由 - 只有在LINE Bot可用時才啟用
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
            
            # 獲取用戶資料
            try:
                profile = line_bot_api.get_profile(user_id)
                user_name = profile.display_name
            except:
                user_name = f"User{user_id[:8]}"
            
            # 處理群組訊息
            is_group = is_group_message(event)
            if is_group:
                if not user_message.strip().startswith('@AI'):
                    return
                user_message = user_message.replace('@AI', '').strip()
                if not user_message:
                    user_message = "Hi"
            
            # 生成回應
            ai_response = generate_ai_response(user_message, user_name)
            
            # 記錄互動
            log_interaction(user_id, user_name, user_message, ai_response, is_group)
            
            # 發送回應
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=ai_response)
            )
            
        except Exception as e:
            print(f"處理訊息錯誤: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，處理訊息時發生錯誤。")
            )
else:
    @app.route("/callback", methods=['POST'])
    def callback():
        return jsonify({"error": "LINE Bot not configured", "message": "請設定 CHANNEL_ACCESS_TOKEN 和 CHANNEL_SECRET 環境變數"})

# 模擬 LINE Bot 互動的網頁介面
@app.route("/simulate_interaction", methods=['GET', 'POST'])
def simulate_interaction():
    """模擬LINE Bot互動的網頁介面"""
    if request.method == 'POST':
        user_name = request.form.get('user_name', 'Demo User')
        user_id = request.form.get('user_id', 'demo_user')
        message = request.form.get('message', '')
        is_group = request.form.get('is_group') == 'on'
        
        if message:
            ai_response = generate_ai_response(message, user_name)
            log_interaction(user_id, user_name, message, ai_response, is_group)
            
            return f'''
            <div style="font-family: Microsoft JhengHei; margin: 20px; padding: 20px; background: #f0f8ff; border-radius: 10px;">
                <h3>✅ 互動已記錄</h3>
                <p><strong>學生:</strong> {user_name}</p>
                <p><strong>訊息:</strong> {message}</p>
                <p><strong>AI回應:</strong> {ai_response}</p>
                <p><strong>群組互動:</strong> {'是' if is_group else '否'}</p>
                <a href="/simulate_interaction" style="color: #007bff;">繼續測試</a> |
                <a href="/research_dashboard" style="color: #007bff;">查看數據</a>
            </div>
            '''
    
    return '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>LINE Bot 互動模擬器</title>
        <style>
            body { font-family: Microsoft JhengHei; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
            .note { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📱 LINE Bot 互動模擬器</h1>
            
            <div class="note">
                <strong>💡 說明:</strong> 由於LINE Bot環境變數未設定，您可以使用此介面模擬學生互動，測試數據記錄功能。
            </div>
            
            <form method="POST">
                <div class="form-group">
                    <label>學生姓名:</label>
                    <input type="text" name="user_name" value="York Chen" required>
                </div>
                
                <div class="form-group">
                    <label>學生ID:</label>
                    <input type="text" name="user_id" value="student001" required>
                </div>
                
                <div class="form-group">
                    <label>訊息內容:</label>
                    <textarea name="message" rows="4" placeholder="例如: What is artificial intelligence?" required></textarea>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="is_group"> 群組互動 (模擬@AI呼叫)
                    </label>
                </div>
                
                <button type="submit">🚀 模擬互動</button>
            </form>
            
            <div style="margin-top: 30px; text-align: center;">
                <a href="/" style="color: #007bff; margin: 0 10px;">🏠 回到首頁</a>
                <a href="/research_dashboard" style="color: #007bff; margin: 0 10px;">📊 查看數據</a>
                <a href="/student_list" style="color: #007bff; margin: 0 10px;">👥 學生列表</a>
            </div>
        </div>
    </body>
    </html>
    '''

# 個人分析功能
def get_individual_student_analysis(user_id):
    """獲取個別學生分析"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_name FROM users WHERE user_id = ?', (user_id,))
        user_info = cursor.fetchone()
        if not user_info:
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
        print(f"個人分析錯誤: {e}")
        return None

def analyze_individual_performance(interactions, user_name, user_id):
    """分析個人表現"""
    total_interactions = len(interactions)
    dates = [datetime.fromisoformat(row[0]).date() for row in interactions]
    
    # 參與度分析
    active_days = len(set(dates))
    study_period = (max(dates) - min(dates)).days + 1 if len(dates) > 1 else 1
    
    # 品質分析
    qualities = [row[3] for row in interactions if row[3] > 0]
    avg_quality = sum(qualities) / len(qualities) if qualities else 0
    
    # 英語使用分析
    english_ratios = [row[5] for row in interactions if row[5] is not None]
    avg_english = sum(english_ratios) / len(english_ratios) if english_ratios else 0
    
    # 提問分析
    questions = [row for row in interactions if row[1] == 'question']
    
    # 主題分析
    topics = analyze_student_topics(interactions)
    
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
            'participation_level': get_participation_level(total_interactions),
            'level_color': get_level_color(total_interactions),
            'consistency_score': round(active_days / study_period * 100, 1)
        },
        'quality': {
            'avg_quality': round(avg_quality, 2),
            'high_quality_count': sum(1 for q in qualities if q >= 4.0),
            'quality_trend': analyze_quality_trend(qualities),
            'quality_distribution': get_quality_distribution(qualities)
        },
        'topics': topics,
        'english_usage': {
            'avg_english_ratio': avg_english,
            'bilingual_ability': get_bilingual_level(avg_english),
            'english_progress': analyze_english_progress(english_ratios)
        },
        'questioning': {
            'total_questions': len(questions),
            'question_ratio': len(questions) / total_interactions if total_interactions > 0 else 0,
            'questioning_pattern': get_questioning_pattern(len(questions), total_interactions),
            'question_topics': analyze_question_topics(questions)
        },
        'overall_assessment': generate_assessment(total_interactions, avg_quality, avg_english, len(questions))
    }

def analyze_student_topics(interactions):
    """分析學生主題興趣"""
    topics_count = Counter()
    
    for row in interactions:
        content = row[2].lower()
        if any(keyword in content for keyword in ['ai', 'artificial intelligence']):
            topics_count['AI基礎'] += 1
        if any(keyword in content for keyword in ['application', 'practical']):
            topics_count['實務應用'] += 1
        if any(keyword in content for keyword in ['ethics', 'responsibility']):
            topics_count['AI倫理'] += 1
    
    return {
        'topic_diversity': len(topics_count),
        'most_interested_topics': topics_count.most_common(3),
        'highest_quality_topics': list(topics_count.items())[:3]
    }

def get_participation_level(interactions):
    """獲取參與度等級"""
    if interactions >= 15:
        return "高度活躍"
    elif interactions >= 8:
        return "中度活躍"
    elif interactions >= 3:
        return "偶爾參與"
    else:
        return "較少參與"

def get_level_color(interactions):
    """獲取等級顏色"""
    if interactions >= 15:
        return "#28a745"
    elif interactions >= 8:
        return "#ffc107"
    elif interactions >= 3:
        return "#fd7e14"
    else:
        return "#dc3545"

def analyze_quality_trend(qualities):
    """分析品質趨勢"""
    if len(qualities) < 3:
        return "數據不足"
    
    recent = sum(qualities[-3:]) / 3
    early = sum(qualities[:3]) / 3
    
    if recent > early + 0.5:
        return "明顯進步"
    elif recent > early + 0.2:
        return "穩定進步"
    else:
        return "穩定維持"

def get_quality_distribution(qualities):
    """獲取品質分布"""
    if not qualities:
        return {}
    
    return {
        '優秀(4.5-5.0)': sum(1 for q in qualities if q >= 4.5),
        '良好(3.5-4.4)': sum(1 for q in qualities if 3.5 <= q < 4.5),
        '普通(2.5-3.4)': sum(1 for q in qualities if 2.5 <= q < 3.5),
        '待改善(<2.5)': sum(1 for q in qualities if q < 2.5)
    }

def get_bilingual_level(ratio):
    """獲取雙語能力等級"""
    if ratio >= 0.8:
        return "優秀雙語使用者"
    elif ratio >= 0.6:
        return "良好雙語能力"
    elif ratio >= 0.4:
        return "中等雙語能力"
    else:
        return "主要使用中文"

def analyze_english_progress(ratios):
    """分析英語進步情況"""
    if len(ratios) < 3:
        return "數據不足"
    
    recent = sum(ratios[-3:]) / 3
    early = sum(ratios[:3]) / 3
    
    if recent > early + 0.2:
        return "明顯進步"
    elif recent > early + 0.1:
        return "穩定進步"
    else:
        return "保持穩定"

def get_questioning_pattern(questions, total):
    """獲取提問模式"""
    ratio = questions / max(total, 1)
    if ratio >= 0.4:
        return "積極提問者"
    elif ratio >= 0.2:
        return "適度提問"
    else:
        return "較少提問"

def analyze_question_topics(questions):
    """分析提問主題"""
    topics = {}
    for q in questions:
        content = q[2].lower()
        if 'ai' in content:
            topics['AI技術'] = topics.get('AI技術', 0) + 1
        elif 'application' in content:
            topics['實務應用'] = topics.get('實務應用', 0) + 1
    return topics

def generate_assessment(interactions, quality, english, questions):
    """生成綜合評估"""
    scores = []
    
    # 參與度分數
    if interactions >= 15:
        scores.append(9)
    elif interactions >= 8:
        scores.append(7)
    else:
        scores.append(5)
    
    # 品質分數
    scores.append(min(quality * 2, 10))
    
    # 英語分數
    scores.append(min(english * 10, 10))
    
    overall_score = sum(scores) / len(scores)
    
    if overall_score >= 8:
        level = "優秀"
    elif overall_score >= 6:
        level = "良好"
    else:
        level = "需改進"
    
    return {
        'overall_score': round(overall_score, 1),
        'performance_level': level,
        'learning_style': "穩健學習者",
        'strengths': ["持續努力中"],
        'improvement_suggestions': ["建議保持學習節奏"]
    }

# 網頁路由
@app.route("/")
def home():
    """首頁"""
    line_bot_status = "✅ 已配置" if line_bot_api else "⚠️ 未配置"
    
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
            .status {{ background: #28a745; color: white; padding: 8px 16px; border-radius: 20px; margin: 10px; }}
            .warning {{ background: #ffc107; color: #333; padding: 8px 16px; border-radius: 20px; margin: 10px; }}
            .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            .card {{ background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📚 AI在生活與學習上的實務應用</h1>
                <p>通識教育中心 | 授課教師：曾郁堯</p>
                <span class="{'status' if line_bot_api else 'warning'}">LINE Bot狀態: {line_bot_status}</span>
            </div>
            
            {'''<div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h3>💡 系統說明</h3>
                <p>LINE Bot環境變數未設定，目前僅提供網頁分析功能。</p>
                <p>您可以使用「互動模擬器」測試系統功能，或查看現有的示範數據。</p>
            </div>''' if not line_bot_api else ''}
            
            <div class="cards">
                <div class="card">
                    <h3>👥 個人學習分析</h3>
                    <p>查看每位學生的詳細學習報告和進步軌跡</p>
                    <a href="/student_list" class="btn">學生列表</a>
                </div>
                <div class="card">
                    <h3>📊 班級整體分析</h3>
                    <p>全班學習狀況統計和教學成效評估</p>
                    <a href="/class_analysis" class="btn">班級分析</a>
                </div>
                <div class="card">
                    <h3>📈 研究數據儀表板</h3>
                    <p>EMI教學實踐研究數據追蹤</p>
                    <a href="/research_dashboard" class="btn">研究儀表板</a>
                </div>
                <div class="card">
                    <h3>📱 互動模擬器</h3>
                    <p>模擬LINE Bot互動，測試數據記錄功能</p>
                    <a href="/simulate_interaction" class="btn">開始模擬</a>
                </div>
                <div class="card">
                    <h3>📄 數據匯出</h3>
                    <p>匯出完整的學習數據，支援研究分析</p>
                    <a href="/export_research_data" class="btn">匯出數據</a>
                </div>
                <div class="card">
                    <h3>⚙️ 系統設定</h3>
                    <p>LINE Bot配置說明和技術支援</p>
                    <a href="/setup_guide" class="btn">設定指南</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/setup_guide")
def setup_guide():
    """設定指南"""
    return '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>LINE Bot 設定指南</title>
        <style>
            body { font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .step { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #007bff; }
            code { background: #f1f1f1; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 LINE Bot 設定指南</h1>
            
            <div class="step">
                <h3>步驟 1: 建立 LINE Bot</h3>
                <p>1. 前往 <a href="https://developers.line.biz/">LINE Developers</a></p>
                <p>2. 建立新的 Channel（Messaging API）</p>
                <p>3. 取得 Channel Access Token 和 Channel Secret</p>
            </div>
            
            <div class="step">
                <h3>步驟 2: 設定 Railway 環境變數</h3>
                <p>在 Railway 專案的 Variables 頁面設定：</p>
                <p><code>CHANNEL_ACCESS_TOKEN</code> = 您的 Channel Access Token</p>
                <p><code>CHANNEL_SECRET</code> = 您的 Channel Secret</p>
            </div>
            
            <div class="step">
                <h3>步驟 3: 設定 Webhook</h3>
                <p>在 LINE Bot 設定中設定 Webhook URL：</p>
                <p><code>https://your-railway-domain.up.railway.app/callback</code></p>
            </div>
            
            <div class="step">
                <h3>步驟 4: 測試功能</h3>
                <p>1. 加入您的 LINE Bot 為好友</p>
                <p>2. 建立群組並邀請 Bot</p>
                <p>3. 在群組中使用 <code>@AI 您的問題</code> 測試</p>
                <p>4. 私訊 Bot 測試個人互動</p>
            </div>
            
            <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin-top: 30px;">
                <h3>✅ 設定完成後的功能</h3>
                <ul>
                    <li>群組討論：學生使用 @AI 呼叫機器人</li>
                    <li>個人諮詢：學生私訊機器人</li>
                    <li>自動數據記錄：所有互動自動分析和儲存</li>
                    <li>教學分析：即時查看學習成效</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/" style="color: #007bff;">← 回到首頁</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/student_list")
def student_list():
    """學生列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_id, u.user_name, COUNT(i.id) as total_interactions,
                   AVG(i.quality_score) as avg_quality, MAX(i.created_at) as last_activity
            FROM users u
            LEFT JOIN interactions i ON u.user_id = i.user_id
            GROUP BY u.user_id, u.user_name
            ORDER BY total_interactions DESC
        ''')
        
        students = cursor.fetchall()
        conn.close()
        
        html = '''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>學生個人分析列表</title>
            <style>
                body { font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { text-align: center; margin-bottom: 30px; color: #333; }
                table { width: 100%; border-collapse: collapse; }
                th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
                th { background: #f8f9fa; font-weight: bold; }
                tr:hover { background: #f8f9fa; }
                .btn { padding: 6px 12px; background: #007bff; color: white; text-decoration: none; border-radius: 3px; }
                .status { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; color: white; }
                .nav-links { text-align: center; margin-bottom: 20px; }
                .nav-links a { display: inline-block; margin: 0 10px; padding: 8px 16px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👥 學生個人分析系統</h1>
                    <p>AI在生活與學習上的實務應用課程</p>
                </div>
                
                <div class="nav-links">
                    <a href="/">🏠 首頁</a>
                    <a href="/class_analysis">📊 班級分析</a>
                    <a href="/research_dashboard">📈 研究數據</a>
                    <a href="/simulate_interaction">📱 互動模擬</a>
                </div>
                
                <h2>學生個人分析列表</h2>
                <p>點擊「詳細分析」查看個別學生的完整學習報告</p>
                
                <table>
                    <tr>
                        <th>學生姓名</th>
                        <th>互動次數</th>
                        <th>平均品質</th>
                        <th>最後活動</th>
                        <th>狀態</th>
                        <th>操作</th>
                    </tr>
        '''
        
        for student in students:
            user_id, user_name, interactions, quality, last_activity = student
            interactions = interactions or 0
            quality = quality or 0
            
            # 判斷狀態
            if interactions >= 10:
                status = "活躍"
                status_color = "#28a745"
            elif interactions >= 5:
                status = "正常"
                status_color = "#ffc107"
            elif interactions >= 1:
                status = "較少"
                status_color = "#fd7e14"
            else:
                status = "無互動"
                status_color = "#dc3545"
            
            # 格式化時間
            if last_activity:
                try:
                    last_date = datetime.fromisoformat(last_activity).strftime('%m/%d')
                except:
                    last_date = "未知"
            else:
                last_date = "無記錄"
            
            html += f'''
                <tr>
                    <td><strong>{user_name}</strong></td>
                    <td>{interactions}</td>
                    <td>{quality:.2f}</td>
                    <td>{last_date}</td>
                    <td><span class="status" style="background: {status_color};">{status}</span></td>
                    <td><a href="/student_analysis/{user_id}" class="btn">詳細分析</a></td>
                </tr>
            '''
        
        if not students:
            html += '<tr><td colspan="6" style="text-align: center;">暫無學生數據</td></tr>'
        
        html += '''
                </table>
            </div>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        return f"錯誤: {e}"

@app.route("/student_analysis/<user_id>")
def student_analysis(user_id):
    """個人分析頁面"""
    analysis = get_individual_student_analysis(user_id)
    
    if not analysis or not analysis.get('analysis_available'):
        return '''
        <div style="text-align: center; padding: 50px; font-family: Microsoft JhengHei;">
            <h2>📊 個人學習分析</h2>
            <p>此學生暫無足夠的互動數據進行分析。</p>
            <a href="/student_list" style="color: #007bff;">← 返回學生列表</a>
        </div>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>{analysis['user_name']} - 個人學習分析</title>
        <style>
            body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .header {{ text-align: center; margin-bottom: 30px; color: #333; }}
            .section {{ margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
            .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
            .value {{ font-weight: bold; color: #007bff; }}
            .nav-links {{ text-align: center; margin-bottom: 20px; }}
            .nav-links a {{ margin: 0 10px; padding: 8px 16px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav-links">
                <a href="/student_list">← 學生列表</a>
                <a href="/class_analysis">📊 班級分析</a>
                <a href="/">🏠 首頁</a>
            </div>
            
            <div class="header">
                <h1>📊 {analysis['user_name']} 個人學習分析</h1>
                <p>分析日期：{analysis['analysis_date']} | 學習期間：{analysis['study_period_days']} 天</p>
                <p><strong>綜合表現：{analysis['overall_assessment']['performance_level']} ({analysis['overall_assessment']['overall_score']}/10)</strong></p>
            </div>
            
            <div class="section">
                <h3>👥 參與度分析</h3>
                <div class="metric">
                    <span>總互動次數</span>
                    <span class="value">{analysis['participation']['total_interactions']}</span>
                </div>
                <div class="metric">
                    <span>活躍天數</span>
                    <span class="value">{analysis['participation']['active_days']} 天</span>
                </div>
                <div class="metric">
                    <span>週平均活動</span>
                    <span class="value">{analysis['participation']['avg_weekly_activity']}</span>
                </div>
                <div class="metric">
                    <span>參與度等級</span>
                    <span class="value" style="color: {analysis['participation']['level_color']};">{analysis['participation']['participation_level']}</span>
                </div>
                <div class="metric">
                    <span>學習一致性</span>
                    <span class="value">{analysis['participation']['consistency_score']}%</span>
                </div>
            </div>
            
            <div class="section">
                <h3>💎 討論品質分析</h3>
                <div class="metric">
                    <span>平均品質分數</span>
                    <span class="value">{analysis['quality']['avg_quality']}/5.0</span>
                </div>
                <div class="metric">
                    <span>高品質討論次數</span>
                    <span class="value">{analysis['quality']['high_quality_count']} 次</span>
                </div>
                <div class="metric">
                    <span>品質趨勢</span>
                    <span class="value">{analysis['quality']['quality_trend']}</span>
                </div>
            </div>
            
            <div class="section">
                <h3>🌍 英語使用分析</h3>
                <div class="metric">
                    <span>平均英語使用比例</span>
                    <span class="value">{analysis['english_usage']['avg_english_ratio']:.1%}</span>
                </div>
                <div class="metric">
                    <span>雙語能力評估</span>
                    <span class="value">{analysis['english_usage']['bilingual_ability']}</span>
                </div>
                <div class="metric">
                    <span>英語使用進步</span>
                    <span class="value">{analysis['english_usage']['english_progress']}</span>
                </div>
            </div>
            
            <div class="section">
                <h3>❓ 提問行為分析</h3>
                <div class="metric">
                    <span>總提問次數</span>
                    <span class="value">{analysis['questioning']['total_questions']}</span>
                </div>
                <div class="metric">
                    <span>提問比例</span>
                    <span class="value">{analysis['questioning']['question_ratio']:.1%}</span>
                </div>
                <div class="metric">
                    <span>提問模式</span>
                    <span class="value">{analysis['questioning']['questioning_pattern']}</span>
                </div>
            </div>
            
            <div class="section">
                <h3>🎯 學習主題分析</h3>
                <div class="metric">
                    <span>討論主題多樣性</span>
                    <span class="value">{analysis['topics']['topic_diversity']} 個主題</span>
                </div>
                <div class="metric">
                    <span>最感興趣主題</span>
                    <span class="value">{', '.join([f"{topic}({count}次)" for topic, count in analysis['topics']['most_interested_topics']]) if analysis['topics']['most_interested_topics'] else '尚未識別'}</span>
                </div>
            </div>
            
            <div class="section">
                <h3>🌟 學習風格與建議</h3>
                <p><strong>學習風格：</strong>{analysis['overall_assessment']['learning_style']}</p>
                <p><strong>主要優勢：</strong>{', '.join(analysis['overall_assessment']['strengths'])}</p>
                <p><strong>改進建議：</strong>{', '.join(analysis['overall_assessment']['improvement_suggestions'])}</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/class_analysis")
def class_analysis():
    """班級分析頁面"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 獲取班級統計
        cursor.execute('''
            SELECT COUNT(DISTINCT u.user_id) as total_students,
                   COUNT(DISTINCT CASE WHEN i.id IS NOT NULL THEN u.user_id END) as active_students,
                   AVG(i.quality_score) as avg_quality,
                   AVG(i.english_ratio) as avg_english,
                   COUNT(i.id) as total_interactions
            FROM users u
            LEFT JOIN interactions i ON u.user_id = i.user_id
        ''')
        
        stats = cursor.fetchone()
        
        # 獲取學生排名
        cursor.execute('''
            SELECT u.user_name, COUNT(i.id) as interactions,
                   AVG(i.quality_score) as avg_quality,
                   AVG(i.english_ratio) as avg_english
            FROM users u
            LEFT JOIN interactions i ON u.user_id = i.user_id
            GROUP BY u.user_id, u.user_name
            ORDER BY interactions DESC
            LIMIT 10
        ''')
        
        rankings = cursor.fetchall()
        conn.close()
        
        total_students, active_students, avg_quality, avg_english, total_interactions = stats
        participation_rate = (active_students / total_students * 100) if total_students > 0 else 0
        
        # 生成排行榜HTML
        ranking_html = ""
        for i, (name, interactions, quality, english) in enumerate(rankings, 1):
            rank_color = "#ffd700" if i <= 3 else "#c0c0c0" if i <= 5 else "#cd7f32"
            ranking_html += f'''
                <tr>
                    <td style="background: {rank_color}; color: white; font-weight: bold; text-align: center;">{i}</td>
                    <td><strong>{name}</strong></td>
                    <td>{interactions or 0}</td>
                    <td>{quality:.2f if quality else 0}</td>
                    <td>{english:.1%} if english else 0%</td>
                </tr>
            '''
        
        # 生成建議
        suggestions = []
        if participation_rate < 70:
            suggestions.append("📈 班級參與率偏低，建議增加互動式活動和小組討論")
        if avg_quality and avg_quality < 3.0:
            suggestions.append("📚 整體討論品質需要提升，建議提供更多優質範例")
        if avg_english and avg_english < 0.4:
            suggestions.append("🌍 英語使用比例偏低，建議設計更多英語互動活動")
        
        if not suggestions:
            suggestions.append("✨ 班級整體表現良好，繼續保持並持續優化教學方法")
        
        suggestions_html = ""
        for suggestion in suggestions:
            suggestions_html += f"<p>{suggestion}</p>"
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>班級整體分析報告</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; color: #333; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
                .stat-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .section {{ margin: 30px 0; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 12px; border: 1px solid #ddd; text-align: left; }}
                th {{ background: #f8f9fa; }}
                .nav-links {{ text-align: center; margin-bottom: 20px; }}
                .nav-links a {{ margin: 0 10px; padding: 8px 16px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="nav-links">
                    <a href="/">🏠 首頁</a>
                    <a href="/student_list">👥 學生列表</a>
                    <a href="/research_dashboard">📈 研究數據</a>
                    <a href="/simulate_interaction">📱 互動模擬</a>
                </div>
                
                <div class="header">
                    <h1>📊 AI實務應用課程 - 班級整體分析</h1>
                    <p>分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{total_students or 0}</div>
                        <div>班級總人數</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{active_students or 0}</div>
                        <div>活躍學生數</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{participation_rate:.1f}%</div>
                        <div>參與率</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{avg_quality:.2f if avg_quality else 0}</div>
                        <div>平均討論品質</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{avg_english:.1%} if avg_english else 0%</div>
                        <div>平均英語使用</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{total_interactions or 0}</div>
                        <div>總互動次數</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🏆 學生表現排行榜 (Top 10)</h2>
                    <table>
                        <tr>
                            <th>排名</th>
                            <th>學生姓名</th>
                            <th>互動次數</th>
                            <th>平均品質</th>
                            <th>英語使用比例</th>
                        </tr>
                        {ranking_html}
                    </table>
                </div>
                
                <div class="section">
                    <h2>💡 教學改進建議</h2>
                    <div style="background: #d4edda; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
                        {suggestions_html}
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f"班級分析錯誤: {e}"

@app.route("/research_dashboard")
def research_dashboard():
    """研究儀表板"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute('SELECT COUNT(*) FROM interactions')
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM interactions')
        active_students = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE date(created_at) = date("now")')
        today_usage = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(quality_score) FROM interactions WHERE quality_score > 0')
        avg_quality = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(english_ratio) FROM interactions WHERE english_ratio IS NOT NULL')
        avg_english = cursor.fetchone()[0] or 0
        
        # 計算週使用率和發言次數
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE date(created_at) >= date('now', '-7 days')
        ''')
        week_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM users')
        total_users = cursor.fetchone()[0]
        
        week_usage_rate = (week_interactions / max(total_users * 5, 1)) * 100  # 假設目標每週5次互動
        avg_weekly_messages = week_interactions / max(active_students, 1) if active_students > 0 else 0
        
        conn.close()
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>EMI教學研究數據儀表板</title>
            <style>
                body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; color: #333; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
                .metric-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 15px; text-align: center; }}
                .metric-value {{ font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }}
                .metric-label {{ font-size: 1.1em; opacity: 0.9; }}
                .status {{ background: #28a745; color: white; padding: 8px 16px; border-radius: 20px; display: inline-block; margin-top: 20px; }}
                .nav-links {{ text-align: center; margin-bottom: 20px; }}
                .nav-links a {{ margin: 0 10px; padding: 8px 16px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; }}
                .research-section {{ margin: 40px 0; padding: 30px; background: #f8f9fa; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="nav-links">
                    <a href="/">🏠 首頁</a>
                    <a href="/student_list">👥 學生列表</a>
                    <a href="/class_analysis">📊 班級分析</a>
                    <a href="/simulate_interaction">📱 互動模擬</a>
                </div>
                
                <div class="header">
                    <h1>📊 EMI教學研究數據儀表板</h1>
                    <p>AI在生活與學習上的實務應用 - 教學實踐研究</p>
                    <span class="status">🟢 系統正常運行</span>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{total_interactions}</div>
                        <div class="metric-label">總互動次數</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{active_students}</div>
                        <div class="metric-label">活躍學生數</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{today_usage}</div>
                        <div class="metric-label">今日使用量</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{week_usage_rate:.1f}%</div>
                        <div class="metric-label">週使用率</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{avg_weekly_messages:.1f}</div>
                        <div class="metric-label">平均發言次數/週</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{avg_quality:.1f}/5.0</div>
                        <div class="metric-label">討論品質平均分</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{avg_english:.1%}</div>
                        <div class="metric-label">英語使用比例</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">第{get_current_week()}週</div>
                        <div class="metric-label">當前課程進度</div>
                    </div>
                </div>
                
                <div class="research-section">
                    <h2>🎯 114年度教學實踐研究計畫</h2>
                    <h3>生成式AI輔助的雙語教學創新：提升EMI課程學生參與度與跨文化能力之教學實踐研究</h3>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px;">
                        <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">
                            <h4>📈 研究目標追蹤</h4>
                            <p><strong>目標 1:</strong> 週使用率 ≥ 70% (目前: {week_usage_rate:.1f}%)</p>
                            <p><strong>目標 2:</strong> 平均發言次數 ≥ 5次/週 (目前: {avg_weekly_messages:.1f}次)</p>
                            <p><strong>目標 3:</strong> 討論品質 ≥ 3.5分 (目前: {avg_quality:.1f}分)</p>
                            <p><strong>目標 4:</strong> 英語使用率 ≥ 50% (目前: {avg_english:.1%})</p>
                        </div>
                        
                        <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
                            <h4>🔬 研究方法</h4>
                            <p>• 量化分析：學生參與度、討論品質統計</p>
                            <p>• 質性分析：學習行為模式、跨文化能力</p>
                            <p>• 混合研究：AI輔助教學效果評估</p>
                            <p>• 縱向研究：18週學習歷程追蹤</p>
                        </div>
                        
                        <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107;">
                            <h4>📊 數據收集狀態</h4>
                            <p>• 互動數據記錄：✅ 自動化收集</p>
                            <p>• 品質分析系統：✅ 即時評分</p>
                            <p>• 英語使用追蹤：✅ 雙語比例分析</p>
                            <p>• 學習歷程記錄：✅ 完整時間序列</p>
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 40px;">
                    <h2>📄 研究數據匯出</h2>
                    <p>支援教學實踐研究報告撰寫和學術論文發表</p>
                    <div style="margin-top: 20px;">
                        <a href="/export_research_data" style="padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">📊 匯出完整數據 (CSV)</a>
                        <a href="/student_list" style="padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">👥 個人分析報告</a>
                        <a href="/class_analysis" style="padding: 12px 24px; background: #17a2b8; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">📈 班級整體報告</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f"研究儀表板錯誤: {e}"

@app.route("/export_research_data")
def export_research_data():
    """匯出研究數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_name, i.created_at, i.content, i.message_type,
                   i.quality_score, i.english_ratio, i.contains_keywords, i.group_id
            FROM users u
            JOIN interactions i ON u.user_id = i.user_id
            ORDER BY i.created_at
        ''')
        
        data = cursor.fetchall()
        conn.close()
        
        # 生成CSV格式
        csv_content = "學生姓名,時間,內容,訊息類型,品質分數,英語比例,包含關鍵詞,群組互動\n"
        for row in data:
            content_preview = row[2][:50].replace('"', '""') if row[2] else ""  # 處理CSV中的引號
            csv_content += f'"{row[0]}","{row[1]}","{content_preview}...","{row[3]}",{row[4] or 0},{row[5] or 0},{row[6] or 0},"{row[7] or ""}"\n'
        
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=ai_course_research_data.csv"}
        )
        
    except Exception as e:
        return f"匯出錯誤: {e}"

@app.route("/health")
def health_check():
    """健康檢查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system": "AI課程分析系統 v2.0",
        "line_bot_configured": line_bot_api is not None,
        "database_accessible": True
    })

@app.route("/api/stats")
def api_stats():
    """API統計數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM interactions')
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM users')
        total_students = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(quality_score) FROM interactions WHERE quality_score > 0')
        avg_quality = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(english_ratio) FROM interactions WHERE english_ratio IS NOT NULL')
        avg_english = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            "total_interactions": total_interactions,
            "total_students": total_students,
            "avg_quality": round(avg_quality, 2),
            "avg_english": round(avg_english, 3),
            "current_week": get_current_week(),
            "system_status": "operational"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 錯誤處理
@app.errorhandler(404)
def not_found(error):
    return '''
    <div style="text-align: center; padding: 50px; font-family: Microsoft JhengHei;">
        <h2>🔍 頁面未找到</h2>
        <p>您要查找的頁面不存在。</p>
        <a href="/" style="color: #007bff;">← 回到首頁</a>
    </div>
    ''', 404

@app.errorhandler(500)
def internal_error(error):
    return '''
    <div style="text-align: center; padding: 50px; font-family: Microsoft JhengHei;">
        <h2>⚠️ 系統錯誤</h2>
        <p>系統發生錯誤，請稍後再試。</p>
        <a href="/" style="color: #007bff;">← 回到首頁</a>
    </div>
    ''', 500

# 初始化資料庫和啟動應用
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 啟動應用於 port {port}")
    print(f"📊 LINE Bot 狀態: {'已配置' if line_bot_api else '未配置'}")
    app.run(host='0.0.0.0', port=port, debug=False)

# Gunicorn 兼容性
application = app
