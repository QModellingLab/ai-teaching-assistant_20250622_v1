from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import sqlite3
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re

app = Flask(__name__)

# LINE Bot 設定
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

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
    study_period = (max(dates) - min(dates)).days + 1
    
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
            'question_ratio': len(questions) / total_interactions,
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
    return '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>AI實務應用課程</title>
        <style>
            body { font-family: Microsoft JhengHei; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .header { text-align: center; margin-bottom: 40px; color: #333; }
            .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .btn { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📚 AI在生活與學習上的實務應用</h1>
                <p>通識教育中心 | 授課教師：曾郁堯</p>
            </div>
            <div class="cards">
                <div class="card">
                    <h3>👥 個人學習分析</h3>
                    <p>查看每位學生的詳細學習報告</p>
                    <a href="/student_list" class="btn">學生列表</a>
                </div>
                <div class="card">
                    <h3>📊 班級整體分析</h3>
                    <p>全班學習狀況和教學成效</p>
                    <a href="/class_analysis" class="btn">班級分析</a>
                </div>
                <div class="card">
                    <h3>📈 研究數據</h3>
                    <p>EMI教學實踐研究數據</p>
                    <a href="/research_dashboard" class="btn">研究儀表板</a>
                </div>
                <div class="card">
                    <h3>📄 數據匯出</h3>
                    <p>匯出完整的學習數據</p>
                    <a href="/export_research_data" class="btn">匯出數據</a>
                </div>
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
                   AVG(i.quality_score) as avg_quality
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
            <title>學生列表</title>
            <style>
                body { font-family: Microsoft JhengHei; margin: 40px; }
                table { width: 100%; border-collapse: collapse; }
                th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
                th { background: #f8f9fa; }
                .btn { padding: 6px 12px; background: #007bff; color: white; text-decoration: none; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>👥 學生個人分析列表</h1>
            <table>
                <tr>
                    <th>學生姓名</th>
                    <th>互動次數</th>
                    <th>平均品質</th>
                    <th>操作</th>
                </tr>
        '''
        
        for student in students:
            user_id, user_name, interactions, quality = student
            html += f'''
                <tr>
                    <td>{user_name}</td>
                    <td>{interactions or 0}</td>
                    <td>{quality:.2f if quality else 0}</td>
                    <td><a href="/student_analysis/{user_id}" class="btn">詳細分析</a></td>
                </tr>
            '''
        
        html += '''
            </table>
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
        </div>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>{analysis['user_name']} - 個人分析</title>
        <style>
            body {{ font-family: Microsoft JhengHei; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .header {{ text-align: center; margin-bottom: 30px; color: #333; }}
            .section {{ margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
            .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
            .value {{ font-weight: bold; color: #007bff; }}
        </style>
    </head>
    <body>
        <div class="container">
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
                    <span>參與度等級</span>
                    <span class="value">{analysis['participation']['participation_level']}</span>
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
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>班級整體分析</title>
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
            </style>
        </head>
        <body>
            <div class="container">
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
        '''
        
        for i, (name, interactions, quality, english) in enumerate(rankings, 1):
            rank_color = "#ffd700" if i <= 3 else "#c0c0c0" if i <= 5 else "#cd7f32"
            html_part = f'''
                        <tr>
                            <td style="background: {rank_color}; color: white; font-weight: bold; text-align: center;">{i}</td>
                            <td><strong>{name}</strong></td>
                            <td>{interactions or 0}</td>
                            <td>{quality:.2f if quality else 0}</td>
                            <td>{english:.1%} if english else 0%</td>
                        </tr>
            '''
        
        html_end = '''
                    </table>
                </div>
                
                <div class="section">
                    <h2>💡 教學改進建議</h2>
                    <div style="background: #d4edda; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
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
        
        for suggestion in suggestions:
            html_end += f"<p>{suggestion}</p>"
        
        html_end += '''
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        return html_part + html_end
        
    except Exception as e:
        return f"錯誤: {e}"

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
            </style>
        </head>
        <body>
            <div class="container">
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
                
                <div style="margin-top: 40px; text-align: center;">
                    <h2>🎯 教學實踐研究目標</h2>
                    <p>透過生成式AI輔助雙語教學，提升EMI課程學生參與度與跨文化能力</p>
                    <div style="margin-top: 20px;">
                        <a href="/export_research_data" style="padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">📄 匯出研究數據</a>
                        <a href="/student_list" style="padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">👥 查看學生分析</a>
                        <a href="/class_analysis" style="padding: 12px 24px; background: #17a2b8; color: white; text-decoration: none; border-radius: 5px; margin: 10px;">📊 班級整體分析</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f"錯誤: {e}"

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
            csv_content += f'"{row[0]}","{row[1]}","{row[2][:50]}...","{row[3]}",{row[4]},{row[5]},{row[6]},"{row[7] or ""}"\n'
        
        from flask import Response
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=research_data.csv"}
        )
        
    except Exception as e:
        return f"匯出錯誤: {e}"

@app.route("/health")
def health_check():
    """健康檢查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system": "AI課程分析系統",
        "version": "2.0"
    })

# 初始化資料庫
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# Gunicorn 兼容性
application = app
