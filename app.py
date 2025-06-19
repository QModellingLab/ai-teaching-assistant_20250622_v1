import os
import sqlite3
from datetime import datetime, timedelta
import re
import json
from collections import Counter
import schedule
import threading
import time
from flask import Flask, request, abort, render_template_string, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import random

app = Flask(__name__)

# LINE Bot 設定
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

# 18週課程進度與智能提問系統
COURSE_SCHEDULE_18_WEEKS = {
    1: {
        "topic": "Course Introduction and AI Era Overview",
        "chinese": "課程介紹,人工智慧如何改變我們的生活?",
        "keywords": ["artificial intelligence", "ai overview", "transformation", "introduction"],
        "focus": "基礎認知"
    },
    2: {
        "topic": "Generative AI Technologies and Applications",
        "chinese": "生成式AI技術與應用：大型語言模型實務操作",
        "keywords": ["generative ai", "chatgpt", "claude", "large language models", "llm"],
        "focus": "實務操作"
    },
    3: {
        "topic": "Student Project Sharing - Generative AI Cases",
        "chinese": "學生專題分享：生成式AI實際應用案例報告",
        "keywords": ["project sharing", "case study", "generative ai applications"],
        "focus": "專題分享"
    },
    4: {
        "topic": "AI Applications in Learning",
        "chinese": "AI在學習領域的應用：學習輔助工具、知識管理系統",
        "keywords": ["learning tools", "knowledge management", "education ai", "study assistant"],
        "focus": "學習應用"
    },
    5: {
        "topic": "Student Project Sharing - AI Learning Tools",
        "chinese": "學生專題分享：AI學習工具使用經驗與成效報告",
        "keywords": ["learning tools experience", "effectiveness report", "ai study"],
        "focus": "專題分享"
    },
    6: {
        "topic": "AI in Creative and Professional Fields",
        "chinese": "AI在創意與職場的應用：內容創作、工作流程優化",
        "keywords": ["content creation", "workflow optimization", "creative ai", "professional"],
        "focus": "職場應用"
    },
    7: {
        "topic": "Student Project Sharing - Creative AI Applications",
        "chinese": "學生專題分享：AI在創意與職場的創新應用展示",
        "keywords": ["creative applications", "innovation showcase", "professional ai"],
        "focus": "專題分享"
    },
    8: {
        "topic": "AI Tool Development and Customization",
        "chinese": "AI工具開發與客製化：無程式碼平台應用",
        "keywords": ["no-code platform", "tool development", "customization", "personalized ai"],
        "focus": "工具開發"
    },
    9: {
        "topic": "Student Project Sharing - Custom AI Tools",
        "chinese": "學生專題分享：自製AI工具開發過程與成果展示",
        "keywords": ["custom tools", "development process", "tool showcase"],
        "focus": "專題分享"
    },
    10: {
        "topic": "Fundamentals of AI (I) - Core Concepts",
        "chinese": "AI基礎概念(一)：核心概念、運作原理與技術架構",
        "keywords": ["core concepts", "operational principles", "technical architecture", "fundamentals"],
        "focus": "理論基礎"
    },
    11: {
        "topic": "Fundamentals of AI (II) - Trends and Prospects",
        "chinese": "AI基礎概念(二)：發展趨勢與應用展望",
        "keywords": ["development trends", "application prospects", "future ai"],
        "focus": "理論基礎"
    },
    12: {
        "topic": "Student Project Sharing - AI Fundamental Analysis",
        "chinese": "學生專題分享：AI基礎概念關鍵議題研析",
        "keywords": ["fundamental analysis", "key issues", "concept discussion"],
        "focus": "專題分享"
    },
    13: {
        "topic": "Industry 4.0 and Smart Manufacturing",
        "chinese": "工業4.0與智慧製造：AI在工業領域的革新應用",
        "keywords": ["industry 4.0", "smart manufacturing", "industrial ai", "manufacturing"],
        "focus": "工業應用"
    },
    14: {
        "topic": "Student Project Sharing - AI Manufacturing Cases",
        "chinese": "學生專題分享：AI輔助製造案例分析報告",
        "keywords": ["manufacturing cases", "industrial analysis", "ai manufacturing"],
        "focus": "專題分享"
    },
    15: {
        "topic": "AI in Home and Daily Life",
        "chinese": "AI在家庭與日常生活的應用：智慧家居、健康管理",
        "keywords": ["smart home", "health management", "daily life", "home automation"],
        "focus": "生活應用"
    },
    16: {
        "topic": "Student Project Sharing - Daily Life AI Innovations",
        "chinese": "學生專題分享：生活中的AI創新應用提案",
        "keywords": ["daily life innovation", "application proposals", "life quality"],
        "focus": "專題分享"
    },
    17: {
        "topic": "Final Exam",
        "chinese": "期末考試",
        "keywords": ["final exam", "assessment", "evaluation"],
        "focus": "評量"
    },
    18: {
        "topic": "Flexible Teaching Week",
        "chinese": "彈性教學週：自主學習指定教材",
        "keywords": ["flexible learning", "self-directed", "review"],
        "focus": "自主學習"
    }
}

# 針對不同週次的智能提問題庫
WEEKLY_INTELLIGENT_QUESTIONS = {
    1: [
        "How do you think AI has already changed your daily routine without you realizing it?",
        "What aspects of AI transformation do you find most exciting or concerning?",
        "Can you identify three AI applications you use regularly in your life?"
    ],
    2: [
        "What's your experience with ChatGPT or Claude so far? Which tasks do you find them most helpful for?",
        "How do you think generative AI might change the way we create content and communicate?",
        "What are the main differences you've noticed between different large language models?"
    ],
    4: [
        "Which AI learning tools have you tried, and how effective were they for your studies?",
        "How might AI-powered knowledge management systems change the way we organize information?",
        "What challenges do you face when using AI for learning, and how do you overcome them?"
    ],
    6: [
        "How could AI tools enhance creativity rather than replace human creativity?",
        "What workflow optimizations have you implemented using AI in your work or studies?",
        "What ethical considerations should we keep in mind when using AI for content creation?"
    ],
    8: [
        "What kind of personalized AI tool would be most useful for your specific needs?",
        "How do no-code platforms democratize AI development for non-technical users?",
        "What are the limitations of no-code AI development compared to traditional programming?"
    ],
    10: [
        "How do you explain the core concepts of AI to someone with no technical background?",
        "What misconceptions about AI do you think are most common among the general public?",
        "How do the operational principles of AI relate to human intelligence?"
    ],
    13: [
        "How might Industry 4.0 change the job market and required skills in manufacturing?",
        "What are the main benefits and challenges of implementing AI in industrial settings?",
        "How can traditional manufacturers transition to smart manufacturing successfully?"
    ],
    15: [
        "What smart home applications do you think will become mainstream in the next 5 years?",
        "How can AI improve health management while protecting personal privacy?",
        "What daily life tasks would you most like to see enhanced by AI?"
    ]
}

# 資料庫初始化
def init_database():
    """初始化資料庫表格"""
    conn = sqlite3.connect('emi_research.db')
    cursor = conn.cursor()
    
    # 用戶表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            user_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 互動記錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message_type TEXT,
            content TEXT NOT NULL,
            quality_score REAL DEFAULT 0,
            contains_keywords INTEGER DEFAULT 0,
            english_ratio REAL DEFAULT 0,
            group_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # AI回應記錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            response TEXT NOT NULL,
            response_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """獲取資料庫連接"""
    conn = sqlite3.connect('emi_research.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_current_course_week():
    """獲取當前課程週次（基於學期開始日期計算）"""
    # 假設學期開始日期為2025年2月24日（第1週）
    semester_start = datetime(2025, 2, 24)
    current_date = datetime.now()
    
    days_passed = (current_date - semester_start).days
    current_week = min(max(1, days_passed // 7 + 1), 18)
    
    return current_week

def classify_message_type(message):
    """分類訊息類型"""
    message_lower = message.lower()
    if any(word in message_lower for word in ['?', 'what', 'how', 'why', 'when', 'where', '什麼', '如何', '為什麼']):
        return 'question'
    elif any(word in message_lower for word in ['think', 'believe', 'opinion', '我覺得', '我認為']):
        return 'discussion'
    elif any(word in message_lower for word in ['thanks', 'thank you', 'hi', 'hello', '謝謝', '你好']):
        return 'greeting'
    else:
        return 'response'

def calculate_english_ratio(message):
    """計算英語使用比例"""
    english_chars = sum(1 for char in message if char.isascii() and char.isalpha())
    total_chars = sum(1 for char in message if char.isalpha())
    return english_chars / max(total_chars, 1)

def calculate_course_specific_quality_score(message, current_week):
    """根據課程特定目標計算品質分數"""
    score = 1.0
    message_lower = message.lower()
    
    # 基礎分數
    if len(message) > 50:
        score += 1.0
    if len(message) > 100:
        score += 0.5
    
    # AI基礎認知相關加分
    ai_concepts = ["artificial intelligence", "machine learning", "algorithm", "neural network", 
                  "deep learning", "automation", "智慧", "演算法", "自動化"]
    if any(concept in message_lower for concept in ai_concepts):
        score += 1.0
    
    # 實務應用相關加分
    practical_terms = ["application", "practical", "implementation", "tool", "solution", 
                      "應用", "實務", "工具", "解決", "實作"]
    if any(term in message_lower for term in practical_terms):
        score += 1.0
    
    # 倫理責任相關加分
    ethics_terms = ["ethics", "responsibility", "privacy", "bias", "fairness", 
                   "倫理", "責任", "隱私", "偏見", "公平"]
    if any(term in message_lower for term in ethics_terms):
        score += 1.0
    
    # 當週主題相關加分
    if current_week in COURSE_SCHEDULE_18_WEEKS:
        week_keywords = COURSE_SCHEDULE_18_WEEKS[current_week]["keywords"]
        if any(keyword in message_lower for keyword in week_keywords):
            score += 0.5
    
    # 英語使用加分（因為是英語授課）
    english_ratio = calculate_english_ratio(message)
    if english_ratio > 0.7:
        score += 1.0
    elif english_ratio > 0.5:
        score += 0.5
    
    # 問號加分（鼓勵提問）
    if '?' in message:
        score += 0.5
    
    return min(score, 5.0)

def contains_course_keywords(message, current_week):
    """檢查是否包含課程特定關鍵詞"""
    message_lower = message.lower()
    
    # 通用AI課程關鍵詞
    course_keywords = [
        'artificial intelligence', 'machine learning', 'ai', 'automation',
        'generative ai', 'chatgpt', 'claude', 'application', 'practical',
        'ethics', 'responsibility', 'privacy', 'tool', 'technology',
        '人工智慧', '機器學習', '應用', '實務', '倫理', '工具'
    ]
    
    # 當週特定關鍵詞
    if current_week in COURSE_SCHEDULE_18_WEEKS:
        week_keywords = COURSE_SCHEDULE_18_WEEKS[current_week]["keywords"]
        course_keywords.extend(week_keywords)
    
    return any(keyword in message_lower for keyword in course_keywords)

def log_course_interaction(user_id, user_name, message, is_group, current_week):
    """記錄課程特定的互動數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 確保用戶存在
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, user_name) 
            VALUES (?, ?)
        ''', (user_id, user_name))
        
        # 使用課程特定的品質評分
        quality_score = calculate_course_specific_quality_score(message, current_week)
        
        # 記錄互動
        cursor.execute('''
            INSERT INTO interactions 
            (user_id, message_type, content, quality_score, contains_keywords, english_ratio, group_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, 
            classify_message_type(message),
            message,
            quality_score,
            1 if contains_course_keywords(message, current_week) else 0,
            calculate_english_ratio(message),
            'group_1' if is_group else None
        ))
        
        conn.commit()
        conn.close()
        print(f"課程互動記錄成功: {user_name} - Week {current_week} - {message[:50]}")
        
    except Exception as e:
        print(f"記錄課程互動失敗: {e}")

def log_ai_response(user_id, response):
    """記錄AI回應"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_responses (user_id, response, response_time)
            VALUES (?, ?, ?)
        ''', (user_id, response, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        print("AI回應記錄成功")
        
    except Exception as e:
        print(f"記錄AI回應失敗: {e}")

def generate_course_contextual_response(user_message, user_name, current_week):
    """生成課程情境式回應"""
    if current_week in COURSE_SCHEDULE_18_WEEKS:
        week_info = COURSE_SCHEDULE_18_WEEKS[current_week]
        topic = week_info["topic"]
        chinese_topic = week_info["chinese"]
        
        greetings = [
            f"Hi {user_name}! Welcome to our AI Practical Applications course! This week (Week {current_week}) we're exploring: {topic}. How can I assist you with today's learning?",
            f"Hello {user_name}! Great to see you engaging with our course material. We're currently in Week {current_week} focusing on {topic}. What questions do you have?",
            f"Hi {user_name}! 很高興見到您參與我們的AI實務應用課程。本週我們討論{chinese_topic}。有什麼我可以協助您的嗎？"
        ]
    else:
        greetings = [
            f"Hi {user_name}! Welcome to our AI Practical Applications course! I'm here to help you explore how AI can enhance your life and learning.",
            f"Hello {user_name}! Ready to dive into the fascinating world of AI applications? Let's discover together!",
            f"Hi {user_name}! 歡迎來到AI實務應用課程！讓我們一起探索AI如何改變生活與學習。"
        ]
    
    return random.choice(greetings)

def generate_course_specific_response(user_message, user_name, current_week):
    """生成課程特定的AI回應"""
    user_message_lower = user_message.lower()
    
    # 根據當週主題生成回應
    if current_week in COURSE_SCHEDULE_18_WEEKS:
        week_info = COURSE_SCHEDULE_18_WEEKS[current_week]
        topic = week_info["topic"]
        focus = week_info["focus"]
        
        # 生成式AI相關（第2週）
        if current_week == 2 and any(term in user_message_lower for term in ["chatgpt", "claude", "generative", "llm"]):
            return f"Great question about generative AI, {user_name}! As we're exploring this week, tools like ChatGPT and Claude represent a major breakthrough in how we interact with AI. What specific aspects of these large language models do you find most interesting for practical applications?"
        
        # 學習工具相關（第4週）
        elif current_week == 4 and any(term in user_message_lower for term in ["learning", "study", "education"]):
            return f"Excellent point, {user_name}! This week we're focusing on AI applications in learning. These tools can personalize education, provide instant feedback, and adapt to individual learning styles. Have you tried any AI-powered learning assistants? What was your experience?"
        
        # 職場應用相關（第6週）
        elif current_week == 6 and any(term in user_message_lower for term in ["work", "professional", "creative", "job"]):
            return f"That's very relevant to our current topic, {user_name}! AI is transforming creative and professional fields by automating routine tasks and enhancing human capabilities. How do you think AI tools can augment rather than replace human creativity in your field of interest?"
        
        # 工業4.0相關（第13週）
        elif current_week == 13 and any(term in user_message_lower for term in ["industry", "manufacturing", "smart", "4.0"]):
            return f"Perfect timing for this discussion, {user_name}! Industry 4.0 represents the convergence of AI, IoT, and manufacturing. Smart factories use AI for predictive maintenance, quality control, and supply chain optimization. What aspects of smart manufacturing do you think will have the biggest impact?"
        
        # 日常生活應用相關（第15週）
        elif current_week == 15 and any(term in user_message_lower for term in ["home", "daily", "life", "smart home"]):
            return f"Great connection to our current focus, {user_name}! AI in daily life is becoming increasingly sophisticated - from voice assistants to smart thermostats that learn your preferences. What daily tasks do you think would benefit most from AI assistance?"
    
    # 通用回應
    general_responses = [
        f"That's an insightful observation, {user_name}! In the context of AI applications, it's important to consider both the benefits and potential challenges. How do you think we can ensure responsible AI use?",
        f"Excellent point, {user_name}! This relates well to our course objectives of understanding AI's practical applications. Can you think of specific examples where this might be implemented?",
        f"Great question, {user_name}! As we explore AI's role in life and learning, critical thinking like yours is essential. What are your thoughts on the ethical implications of this application?"
    ]
    
    return random.choice(general_responses)

def generate_weekly_intelligent_question(user_name, current_week):
    """根據當前週次生成智能提問"""
    if current_week in WEEKLY_INTELLIGENT_QUESTIONS:
        questions = WEEKLY_INTELLIGENT_QUESTIONS[current_week]
        question = random.choice(questions)
        week_info = COURSE_SCHEDULE_18_WEEKS.get(current_week, {})
        topic = week_info.get("topic", f"Week {current_week}")
        
        return f"Hi {user_name}! 🤔 This week we're exploring: {topic}. {question} I'd love to hear your perspective and encourage you to share your thoughts with the class!"
    
    # 通用智能提問
    general_questions = [
        "How has your understanding of AI applications evolved throughout this course?",
        "What practical AI tool have you found most useful for your daily life or studies?",
        "What ethical considerations do you think are most important when using AI?",
        "How do you see AI changing your future career or field of study?"
    ]
    
    return f"Hi {user_name}! 💭 {random.choice(general_questions)} Feel free to share your insights!"

def should_trigger_course_intelligent_question(user_id, current_week):
    """判斷是否應該觸發課程智能提問"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 檢查用戶本週的互動次數
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE user_id = ? AND created_at >= datetime('now', '-7 days')
        ''', (user_id,))
        weekly_interactions = cursor.fetchone()[0]
        
        # 檢查用戶今日的互動次數
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE user_id = ? AND DATE(created_at) = DATE('now')
        ''', (user_id,))
        daily_interactions = cursor.fetchone()[0]
        
        # 檢查是否為專題分享週（需要更多互動）
        is_project_week = current_week in [3, 5, 7, 9, 12, 14, 16]
        
        conn.close()
        
        # 觸發條件：週互動少於3次，且今日互動為1次（剛開始參與）
        if weekly_interactions < 3 and daily_interactions == 1:
            return True
        
        # 專題分享週需要更多互動
        if is_project_week and weekly_interactions < 5:
            return True
        
        return False
        
    except Exception as e:
        print(f"判斷課程智能提問錯誤: {e}")
        return False

def is_group_message(event):
    """檢查是否為群組訊息"""
    try:
        return hasattr(event.source, 'group_id') and event.source.group_id is not None
    except:
        return False

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
            user_name = f"User_{user_id[:8]}"
        
        # 處理群組訊息
        is_group = is_group_message(event)
        if is_group:
            if not user_message.strip().startswith('@AI'):
                return
            
            user_message = user_message.replace('@AI', '').strip()
            if not user_message:
                user_message = "Hi"
        
        # 獲取當前課程週次
        current_week = get_current_course_week()
        
        # 記錄互動數據（使用課程特定評分）
        log_course_interaction(user_id, user_name, user_message, is_group, current_week)
        
        # 生成課程特定回應
        if user_message.lower() in ['hi', 'hello', 'help', '幫助']:
            response = generate_course_contextual_response(user_message, user_name, current_week)
        else:
            response = generate_course_specific_response(user_message, user_name, current_week)
        
        # 記錄AI回應
        log_ai_response(user_id, response)
        
        # 發送回應
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response)
        )
        
        # 檢查是否需要智能提問
        if should_trigger_course_intelligent_question(user_id, current_week):
            intelligent_question = generate_weekly_intelligent_question(user_name, current_week)
            # 延遲發送智能提問
            def delayed_course_question():
                time.sleep(300)  # 5分鐘後發送
                try:
                    line_bot_api.push_message(user_id, TextSendMessage(text=intelligent_question))
                except:
                    pass
            
            threading.Thread(target=delayed_course_question, daemon=True).start()
        
    except Exception as e:
        print(f"處理課程訊息錯誤: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="抱歉，處理訊息時發生錯誤。請稍後再試。")
        )

# 研究數據分析函數
def get_research_stats():
    """獲取研究統計數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 總互動次數
        cursor.execute('SELECT COUNT(*) FROM interactions')
        total_interactions = cursor.fetchone()[0]
        
        # 活躍學生數
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM interactions')
        active_students = cursor.fetchone()[0]
        
        # 今日使用量
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE DATE(created_at) = ?', (today,))
        today_usage = cursor.fetchone()[0]
        
        # 平均討論品質
        cursor.execute('SELECT AVG(quality_score) FROM interactions WHERE quality_score > 0')
        avg_quality = cursor.fetchone()[0] or 0
        
        # 週使用率計算
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM interactions WHERE DATE(created_at) >= ?', (week_ago,))
        weekly_active = cursor.fetchone()[0]
        
        total_students = max(active_students, 30)
        weekly_usage_rate = (weekly_active / total_students) * 100 if total_students > 0 else 0
        
        # 平均發言次數
        cursor.execute('''
            SELECT AVG(interaction_count) FROM (
                SELECT COUNT(*) as interaction_count 
                FROM interactions 
                WHERE DATE(created_at) >= ? 
                GROUP BY user_id
            )
        ''', (week_ago,))
        avg_interactions = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_interactions': total_interactions,
            'active_students': active_students,
            'today_usage': today_usage,
            'avg_quality': round(avg_quality, 2),
            'weekly_usage_rate': round(weekly_usage_rate, 1),
            'avg_interactions_per_user': round(avg_interactions, 1)
        }
        
    except Exception as e:
        print(f"獲取統計數據錯誤: {e}")
        return {
            'total_interactions': 0,
            'active_students': 0,
            'today_usage': 0,
            'avg_quality': 0,
            'weekly_usage_rate': 0,
            'avg_interactions_per_user': 0
        }

def get_course_specific_analytics():
    """獲取課程特定的分析數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        current_week = get_current_course_week()
        
        # 當週主題參與度
        if current_week in COURSE_SCHEDULE_18_WEEKS:
            week_keywords = COURSE_SCHEDULE_18_WEEKS[current_week]["keywords"]
            keyword_conditions = " OR ".join([f"LOWER(content) LIKE '%{keyword}%'" for keyword in week_keywords])
            
            cursor.execute(f'''
                SELECT COUNT(*) FROM interactions 
                WHERE ({keyword_conditions})
                AND DATE(created_at) >= DATE('now', '-7 days')
            ''')
            weekly_topic_engagement = cursor.fetchone()[0]
        else:
            weekly_topic_engagement = 0
        
        # 三大課程目標相關討論統計
        # 1. AI基礎認知
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE (LOWER(content) LIKE '%artificial intelligence%' 
                OR LOWER(content) LIKE '%machine learning%'
                OR LOWER(content) LIKE '%algorithm%'
                OR LOWER(content) LIKE '%智慧%')
        ''')
        ai_fundamentals_discussions = cursor.fetchone()[0]
        
        # 2. 實務應用
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE (LOWER(content) LIKE '%application%' 
                OR LOWER(content) LIKE '%practical%'
                OR LOWER(content) LIKE '%tool%'
                OR LOWER(content) LIKE '%應用%'
                OR LOWER(content) LIKE '%實務%')
        ''')
        practical_applications_discussions = cursor.fetchone()[0]
        
        # 3. 倫理與責任
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE (LOWER(content) LIKE '%ethics%' 
                OR LOWER(content) LIKE '%responsibility%'
                OR LOWER(content) LIKE '%privacy%'
                OR LOWER(content) LIKE '%倫理%'
                OR LOWER(content) LIKE '%責任%')
        ''')
        ethics_discussions = cursor.fetchone()[0]
        
        # 英語授課成效
        cursor.execute('''
            SELECT AVG(english_ratio) FROM interactions 
            WHERE english_ratio > 0
        ''')
        avg_english_usage = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'current_week': current_week,
            'current_topic': COURSE_SCHEDULE_18_WEEKS.get(current_week, {}).get('topic', 'N/A'),
            'weekly_topic_engagement': weekly_topic_engagement,
            'ai_fundamentals_discussions': ai_fundamentals_discussions,
            'practical_applications_discussions': practical_applications_discussions,
            'ethics_discussions': ethics_discussions,
            'avg_english_usage': round(avg_english_usage, 3),
            'course_objectives_coverage': {
                'AI基礎認知': ai_fundamentals_discussions,
                '實務應用': practical_applications_discussions,
                '倫理責任': ethics_discussions
            }
        }
        
    except Exception as e:
        print(f"獲取課程特定分析錯誤: {e}")
        return {}

def generate_course_progress_html(current_week):
    """生成課程進度HTML"""
    html = ""
    for week in range(1, 19):
        status = "current" if week == current_week else ("completed" if week < current_week else "upcoming")
        color = "#28a745" if status == "completed" else ("#007bff" if status == "current" else "#6c757d")
        
        html += f'''
        <div style="background: {color}; color: white; padding: 10px; border-radius: 5px; font-size: 0.8em;">
            Week {week}
            <br>
            {COURSE_SCHEDULE_18_WEEKS.get(week, {}).get('focus', '')}
        </div>
        '''
    return html

# 網頁路由
@app.route("/", methods=['GET'])
def enhanced_home():
    """首頁"""
    return '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI實務應用課程儀表板</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Microsoft JhengHei', sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 3rem;
            }
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
                font-weight: 300;
            }
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
            .card-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 2rem;
                margin-bottom: 3rem;
            }
            .card {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 2rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            .card:hover {
                transform: translateY(-5px);
            }
            .card h3 {
                color: #5a67d8;
                margin-bottom: 1rem;
                font-size: 1.4rem;
            }
            .card p {
                line-height: 1.6;
                margin-bottom: 1rem;
            }
            .btn {
                display: inline-block;
                padding: 0.8rem 2rem;
                background: #5a67d8;
                color: white;
                text-decoration: none;
                border-radius: 25px;
                transition: background 0.3s ease;
                font-weight: 500;
            }
            .btn:hover {
                background: #4c51bf;
            }
            .status {
                display: inline-block;
                padding: 0.3rem 1rem;
                background: #48bb78;
                color: white;
                border-radius: 15px;
                font-size: 0.9rem;
                margin-left: 1rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📚 AI在生活與學習上的實務應用</h1>
                <p>Practical Applications of AI in Life and Learning</p>
                <p>授課教師：曾郁堯 | 通識教育中心</p>
                <span class="status">🟢 系統運行中</span>
            </div>
            
            <div class="card-grid">
                <div class="card">
                    <h3>🎯 課程目標追蹤</h3>
                    <p>AI基礎認知 + 實務應用 + 倫理責任</p>
                    <p>透過18週系統性學習，培養AI應用與批判思考能力</p>
                    <a href="/course_dashboard" class="btn">查看課程儀表板</a>
                </div>
                
                <div class="card">
                    <h3>📊 學習成效分析</h3>
                    <p>即時追蹤學生參與度、討論品質、英語使用比例</p>
                    <p>支援EMI雙語教學與個人化學習回饋</p>
                    <a href="/research_dashboard" class="btn">查看研究數據</a>
                </div>
                
                <div class="card">
                    <h3>🤖 AI智能助手</h3>
                    <p>LINE Bot整合18週課程內容，provide 24/7學習支援</p>
                    <p>根據課程進度主動提問，促進深度學習</p>
                    <a href="/weekly_report" class="btn">查看週報告</a>
                </div>
                
                <div class="card">
                    <h3>📈 教學研究支援</h3>
                    <p>完整的學習行為數據記錄與分析</p>
                    <p>支援教學實踐研究與成果發表</p>
                    <a href="/export_research_data" class="btn">匯出研究數據</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/course_dashboard", methods=['GET'])
def course_dashboard():
    """課程特定儀表板"""
    course_analytics = get_course_specific_analytics()
    basic_stats = get_research_stats()
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>AI實務應用課程儀表板</title>
        <style>
            body {{ font-family: 'Microsoft JhengHei', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1400px; margin: 0 auto; }}
            .header {{ text-align: center; background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .metric {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0; }}
            .metric-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
            .progress-bar {{ width: 100%; height: 10px; background: #e9ecef; border-radius: 5px; margin: 10px 0; }}
            .progress-fill {{ height: 100%; background: linear-gradient(90deg, #007bff, #28a745); border-radius: 5px; }}
            .objective {{ background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            .week-info {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📚 AI在生活與學習上的實務應用 - 課程儀表板</h1>
                <p>Practical Applications of AI in Life and Learning</p>
                <p>授課教師：曾郁堯 | 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="grid">
                <div class="card">
                    <div class="week-info">
                        <h2>📅 當前課程進度</h2>
                        <p><strong>第 {course_analytics.get('current_week', 'N/A')} 週</strong></p>
                        <p>{course_analytics.get('current_topic', 'N/A')}</p>
                        <p>本週主題參與：{course_analytics.get('weekly_topic_engagement', 0)} 次討論</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🎯 三大課程目標達成情況</h3>
                    <div class="objective">
                        <h4>AI基礎認知</h4>
                        <p>{course_analytics.get('ai_fundamentals_discussions', 0)} 次相關討論</p>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(course_analytics.get('ai_fundamentals_discussions', 0) * 10, 100)}%"></div>
                        </div>
                    </div>
                    <div class="objective">
                        <h4>實務應用</h4>
                        <p>{course_analytics.get('practical_applications_discussions', 0)} 次相關討論</p>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(course_analytics.get('practical_applications_discussions', 0) * 10, 100)}%"></div>
                        </div>
                    </div>
                    <div class="objective">
                        <h4>倫理與責任</h4>
                        <p>{course_analytics.get('ethics_discussions', 0)} 次相關討論</p>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(course_analytics.get('ethics_discussions', 0) * 10, 100)}%"></div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🌐 英語授課成效</h3>
                    <div class="metric">
                        <div class="metric-value">{course_analytics.get('avg_english_usage', 0):.1%}</div>
                        <p>平均英語使用比例</p>
                    </div>
                    <p>{"✅ 英語使用良好" if course_analytics.get('avg_english_usage', 0) > 0.6 else "⚠️ 建議增加英語互動"}</p>
                </div>
                
                <div class="card">
                    <h3>📊 基礎統計數據</h3>
                    <div class="metric">
                        <div class="metric-value">{basic_stats['total_interactions']}</div>
                        <p>總互動次數</p>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{basic_stats['active_students']}</div>
                        <p>活躍學生數</p>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{basic_stats['avg_quality']}</div>
                        <p>平均討論品質</p>
                    </div>
                </div>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <h3>📝 18週課程規劃進度</h3>
                <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; text-align: center;">
                    {generate_course_progress_html(course_analytics.get('current_week', 1))}
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/research_dashboard", methods=['GET'])
def research_dashboard():
    """研究數據儀表板"""
    stats = get_research_stats()
    current_week = get_current_course_week()
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>EMI研究儀表板</title>
        <style>
            body {{ font-family: 'Microsoft JhengHei', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
            .metric-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
            .metric-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
            .metric-label {{ color: #666; margin-top: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 EMI教學研究數據儀表板</h1>
                <p>更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 當前週次: 第{current_week}週</p>
            </div>
            
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value">{stats['total_interactions']}</div>
                    <div class="metric-label">總互動次數</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats['active_students']}</div>
                    <div class="metric-label">活躍學生數</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats['today_usage']}</div>
                    <div class="metric-label">今日使用量</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats['weekly_usage_rate']}%</div>
                    <div class="metric-label">週使用率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats['avg_interactions_per_user']}</div>
                    <div class="metric-label">平均發言次數/週</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats['avg_quality']}/5.0</div>
                    <div class="metric-label">討論品質平均分</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/weekly_report", methods=['GET'])
def weekly_report():
    """週報告頁面"""
    stats = get_research_stats()
    current_week = get_current_course_week()
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>AI課程週報告</title>
        <style>
            body {{ font-family: 'Microsoft JhengHei', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #eee; padding-bottom: 20px; }}
            .section {{ margin: 20px 0; }}
            .stat-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 15px 0; }}
            .stat-item {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 AI實務應用課程週報告</h1>
                <p>第{current_week}週 • {datetime.now().strftime('%Y年%m月%d日')}</p>
            </div>
            
            <div class="section">
                <h2>📈 本週數據摘要</h2>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div style="font-size: 1.5em; font-weight: bold;">{stats['total_interactions']}</div>
                        <div>總互動次數</div>
                    </div>
                    <div class="stat-item">
                        <div style="font-size: 1.5em; font-weight: bold;">{stats['active_students']}</div>
                        <div>活躍學生數</div>
                    </div>
                    <div class="stat-item">
                        <div style="font-size: 1.5em; font-weight: bold;">{stats['weekly_usage_rate']}%</div>
                        <div>週使用率</div>
                    </div>
                    <div class="stat-item">
                        <div style="font-size: 1.5em; font-weight: bold;">{stats['avg_quality']}</div>
                        <div>平均品質分</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>🎯 課程目標達成情況</h2>
                <p><strong>週使用率:</strong> {stats['weekly_usage_rate']}% {'✅ 已達標' if stats['weekly_usage_rate'] >= 70 else '❌ 未達標 (目標≥70%)'}</p>
                <p><strong>平均發言次數:</strong> {stats['avg_interactions_per_user']}次/週 {'✅ 已達標' if stats['avg_interactions_per_user'] >= 5 else '❌ 未達標 (目標≥5次)'}</p>
                <p><strong>討論品質:</strong> {stats['avg_quality']}/5.0 {'✅ 良好' if stats['avg_quality'] >= 3.0 else '⚠️ 待改善'}</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/export_research_data", methods=['GET'])
def export_research_data():
    """匯出研究數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                i.created_at,
                u.user_name,
                i.message_type,
                i.content,
                i.quality_score,
                i.contains_keywords,
                i.english_ratio,
                i.group_id
            FROM interactions i
            JOIN users u ON i.user_id = u.user_id
            ORDER BY i.created_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        csv_content = "時間,學生姓名,訊息類型,內容,品質分數,包含關鍵詞,英語比例,群組ID\n"
        for row in results:
            content = row[3].replace('"', '""')[:50] + "..." if len(row[3]) > 50 else row[3].replace('"', '""')
            csv_content += f'"{row[0]}","{row[1]}","{row[2]}","{content}",{row[4]},{row[5]},{row[6]},"{row[7] or ""}"\n'
        
        return csv_content, 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': f'attachment; filename="ai_course_data_{datetime.now().strftime("%Y%m%d")}.csv"'
        }
        
    except Exception as e:
        return f"匯出失敗: {e}", 500

@app.route("/test_routes")
def test_routes():
    """測試路由"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{list(rule.methods)} {rule.rule} -> {rule.endpoint}")
    
    return "<br>".join([f"<h2>Total routes: {len(routes)}</h2>"] + routes)

@app.route("/health")
def health_check():
    """健康檢查"""
    return "OK"

# 定時任務
def setup_course_scheduled_tasks():
    """設定課程定時任務"""
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

# 初始化
init_database()
setup_course_scheduled_tasks()

# Gunicorn 應用物件
application = app

if __name__ == "__main__":
    current_week = get_current_course_week()
    print("📚 AI在生活與學習上的實務應用 - 課程系統啟動")
    print(f"🗓️ 當前週次：第 {current_week} 週")
    print(f"📖 本週主題：{COURSE_SCHEDULE_18_WEEKS.get(current_week, {}).get('topic', 'N/A')}")
    print("🎯 課程目標：AI基礎認知 + 實務應用 + 倫理責任")
    print("🌐 授課語言：英語 (EMI)")
    print("📊 功能：智能問答 + 學習追蹤 + 成效分析")
    
    # 顯示註冊的路由
    print("\n📝 系統路由：")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)
