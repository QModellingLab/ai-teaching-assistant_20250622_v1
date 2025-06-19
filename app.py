import os
import sqlite3
from datetime import datetime, timedelta
import re
from flask import Flask, request, abort, render_template_string, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import random

app = Flask(__name__)

# LINE Bot 設定
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

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

def calculate_quality_score(message):
    """計算討論品質分數（1-5分）"""
    score = 1.0
    
    # 長度加分
    if len(message) > 50:
        score += 1.0
    if len(message) > 100:
        score += 0.5
    
    # 問號加分（提問）
    if '?' in message:
        score += 0.5
    
    # 學術關鍵詞加分
    if contains_academic_keywords(message):
        score += 1.0
    
    # 英語使用加分
    english_ratio = calculate_english_ratio(message)
    if english_ratio > 0.3:
        score += 0.5
    
    return min(score, 5.0)

def contains_academic_keywords(message):
    """檢查是否包含學術關鍵詞"""
    academic_keywords = [
        'analysis', 'research', 'study', 'theory', 'concept', 'methodology',
        'data', 'evidence', 'hypothesis', 'conclusion', 'literature',
        '分析', '研究', '理論', '概念', '方法', '數據', '證據'
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in academic_keywords)

def calculate_english_ratio(message):
    """計算英語使用比例"""
    english_chars = sum(1 for char in message if char.isascii() and char.isalpha())
    total_chars = sum(1 for char in message if char.isalpha())
    return english_chars / max(total_chars, 1)

def log_interaction(user_id, user_name, message, is_group=False):
    """記錄用戶互動到資料庫"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 確保用戶存在
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, user_name) 
            VALUES (?, ?)
        ''', (user_id, user_name))
        
        # 記錄互動
        cursor.execute('''
            INSERT INTO interactions 
            (user_id, message_type, content, quality_score, contains_keywords, english_ratio, group_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, 
            classify_message_type(message),
            message,
            calculate_quality_score(message),
            1 if contains_academic_keywords(message) else 0,
            calculate_english_ratio(message),
            'group_1' if is_group else None
        ))
        
        conn.commit()
        conn.close()
        print(f"✅ 記錄互動成功: {user_name} - {message[:50]}")
        
    except Exception as e:
        print(f"❌ 記錄互動失敗: {e}")

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
        print(f"✅ 記錄AI回應成功")
        
    except Exception as e:
        print(f"❌ 記錄AI回應失敗: {e}")

def generate_contextual_response(user_message, user_name):
    """生成情境式回應"""
    greetings = [
        f"Hi {user_name}! 我是您的EMI教學助手。我可以幫您解答學術問題，也可以用英語進行討論。有什麼我可以協助的嗎？",
        f"Hello {user_name}! Welcome to our EMI learning environment. Feel free to ask me questions in English or Chinese!",
        f"很高興見到您，{user_name}！我可以協助您進行英語學習和學術討論。請隨時提問！"
    ]
    return random.choice(greetings)

def generate_ai_response(user_message, user_name):
    """生成AI回應"""
    # 簡單的AI回應邏輯
    user_message_lower = user_message.lower()
    
    # 關鍵詞匹配回應
    if any(word in user_message_lower for word in ['smart home', '智能家居', 'iot']):
        return f"Hi {user_name}, a smart home leverages Industry 4.0 technologies like IoT (物聯網) to automate and customize aspects of home life, such as lighting and temperature control. Think of automated blinds adjusting to sunlight or appliances predicting your needs. Want to know more?"
    
    elif any(word in user_message_lower for word in ['industry 4.0', '工業4.0', 'ai', 'artificial intelligence']):
        return f"That's a great question, {user_name}! Industry 4.0 leverages AI for smart manufacturing and automation to enable mass customization – think personalized products at scale. Consider how AI optimizes processes within the \"智慧製造\" (Smart Manufacturing) framework. Want to know more?"
    
    elif any(word in user_message_lower for word in ['machine learning', '機器學習']):
        return f"Excellent topic, {user_name}! Machine Learning is a subset of AI that enables systems to learn and improve from data without explicit programming. In EMI contexts, it's often discussed alongside concepts like neural networks (神經網路) and deep learning. What specific aspect interests you?"
    
    elif any(word in user_message_lower for word in ['sustainability', '永續', 'environment']):
        return f"Great question about sustainability, {user_name}! Environmental sustainability (環境永續) involves balancing economic growth with ecological protection. In EMI courses, we often explore how technology and innovation can support sustainable development goals. Which area would you like to explore further?"
    
    else:
        # 通用學習支持回應
        responses = [
            f"That's an interesting point, {user_name}! Can you elaborate on your thoughts? This kind of critical thinking is valuable in EMI learning environments.",
            f"Good question, {user_name}! In academic contexts, it's important to consider multiple perspectives. What do you think are the key factors to consider here?",
            f"Thanks for sharing, {user_name}! This is exactly the kind of engagement we encourage in EMI courses. How do you think this relates to our course concepts?"
        ]
        return random.choice(responses)

def is_group_message(event):
    """檢查是否為群組訊息"""
    try:
        # 檢查 source 物件是否有 group_id 屬性
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
        
        # 處理群組訊息 - 只有@提到bot才回應
        is_group = is_group_message(event)
        if is_group:
            if not user_message.strip().startswith('@AI'):
                return
            
            # 移除@AI前綴
            user_message = user_message.replace('@AI', '').strip()
            if not user_message:
                user_message = "Hi"
        
        # 🔥 重要：記錄互動數據到資料庫
        log_interaction(user_id, user_name, user_message, is_group)
        
        # 生成回應
        if user_message.lower() in ['hi', 'hello', 'help', '幫助']:
            response = generate_contextual_response(user_message, user_name)
        else:
            response = generate_ai_response(user_message, user_name)
        
        # 🔥 重要：記錄AI回應到資料庫
        log_ai_response(user_id, response)
        
        # 發送回應
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response)
        )
        
    except Exception as e:
        print(f"Error handling message: {e}")
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
        
        # 假設總學生數為30（您可以根據實際情況調整）
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
        print(f"Error getting research stats: {e}")
        return {
            'total_interactions': 0,
            'active_students': 0,
            'today_usage': 0,
            'avg_quality': 0,
            'weekly_usage_rate': 0,
            'avg_interactions_per_user': 0
        }

def get_student_engagement():
    """獲取學生參與度排行"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                u.user_name,
                COUNT(i.id) as message_count,
                AVG(i.quality_score) as avg_quality,
                CASE 
                    WHEN COUNT(i.id) >= 10 THEN '高度參與'
                    WHEN COUNT(i.id) >= 5 THEN '中度參與'
                    ELSE '低度參與'
                END as engagement_level
            FROM users u
            LEFT JOIN interactions i ON u.user_id = i.user_id
            GROUP BY u.user_id, u.user_name
            ORDER BY message_count DESC
            LIMIT 10
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
        
    except Exception as e:
        print(f"Error getting student engagement: {e}")
        return []

def get_group_activity():
    """獲取小組活躍度排行"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COALESCE(group_id, '個人互動') as group_name,
                COUNT(id) as activity_count,
                COUNT(DISTINCT user_id) as participant_count,
                AVG(quality_score) as avg_quality
            FROM interactions
            GROUP BY group_id
            ORDER BY activity_count DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
        
    except Exception as e:
        print(f"Error getting group activity: {e}")
        return []

# 網頁路由
@app.route("/", methods=['GET'])
def enhanced_home():
    """增強版首頁"""
    html = '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EMI教學研究數據儀表板</title>
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
                <h1>📊 EMI教學研究數據儀表板</h1>
                <p>生成式AI輔助的雙語教學創新研究</p>
                <span class="status">🟢 系統運行中</span>
            </div>
            
            <div class="card-grid">
                <div class="card">
                    <h3>🎯 研究目標</h3>
                    <p>透過生成式AI技術提升EMI課程學生參與度與跨文化能力，建立創新的雙語教學模式。</p>
                    <a href="/research_dashboard" class="btn">查看研究儀表板</a>
                </div>
                
                <div class="card">
                    <h3>📈 數據分析</h3>
                    <p>即時追蹤學生互動頻率、討論品質、英語使用比例等關鍵指標，支援教學決策。</p>
                    <a href="/weekly_report" class="btn">查看週報告</a>
                </div>
                
                <div class="card">
                    <h3>🤖 AI教學助手</h3>
                    <p>LINE Bot整合智能回應系統，提供24/7學習支援，促進學生主動參與討論。</p>
                    <a href="/export_research_data" class="btn">匯出研究數據</a>
                </div>
                
                <div class="card">
                    <h3>📊 教學成效</h3>
                    <p>系統性記錄學習行為數據，支援教學實踐研究與成果發表。</p>
                    <a href="/health" class="btn">系統健康檢查</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route("/research_dashboard", methods=['GET'])
def research_dashboard():
    """研究數據儀表板"""
    stats = get_research_stats()
    student_engagement = get_student_engagement()
    group_activity = get_group_activity()
    
    html = f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EMI教學研究數據儀表板</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Microsoft JhengHei', sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 2rem;
            }}
            .header {{
                background: rgba(255,255,255,0.95);
                border-radius: 15px;
                padding: 2rem;
                margin-bottom: 2rem;
                text-align: center;
            }}
            .header h1 {{
                color: #5a67d8;
                margin-bottom: 0.5rem;
            }}
            .info-bar {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 1rem;
                font-size: 0.9rem;
                color: #666;
            }}
            .dashboard {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 2rem;
                margin-bottom: 2rem;
            }}
            .metric-card {{
                background: rgba(255,255,255,0.95);
                border-radius: 15px;
                padding: 1.5rem;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .metric-card h3 {{
                font-size: 1rem;
                margin-bottom: 1rem;
                color: #666;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .metric-value {{
                font-size: 2rem;
                font-weight: bold;
                color: #5a67d8;
                margin-bottom: 0.5rem;
            }}
            .metric-target {{
                font-size: 0.8rem;
                color: #666;
            }}
            .status {{
                display: inline-block;
                padding: 0.3rem 1rem;
                border-radius: 15px;
                font-size: 0.8rem;
                font-weight: 500;
            }}
            .status.achieved {{ background: #48bb78; color: white; }}
            .status.not-achieved {{ background: #f56565; color: white; }}
            .status.running {{ background: #48bb78; color: white; }}
            .progress-bar {{
                width: 100%;
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
                margin: 0.5rem 0;
                overflow: hidden;
            }}
            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, #667eea, #764ba2);
                border-radius: 4px;
                transition: width 0.3s ease;
            }}
            .ranking-table {{
                background: rgba(255,255,255,0.95);
                border-radius: 15px;
                padding: 1.5rem;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .ranking-table h3 {{
                margin-bottom: 1rem;
                color: #5a67d8;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .table th {{
                background: #f7fafc;
                padding: 0.8rem;
                text-align: left;
                font-weight: 500;
                color: #4a5568;
                border-bottom: 2px solid #e2e8f0;
            }}
            .table td {{
                padding: 0.8rem;
                border-bottom: 1px solid #e2e8f0;
            }}
            .table tr:hover {{
                background: #f7fafc;
            }}
            .engagement-level {{
                display: inline-block;
                padding: 0.2rem 0.8rem;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 500;
            }}
            .engagement-level.高度參與 {{ background: #48bb78; color: white; }}
            .engagement-level.中度參與 {{ background: #ed8936; color: white; }}
            .engagement-level.低度參與 {{ background: #cbd5e0; color: #4a5568; }}
            .ai-insights {{
                background: rgba(255,255,255,0.95);
                border-radius: 15px;
                padding: 1.5rem;
                margin-top: 2rem;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .ai-insights h3 {{
                color: #5a67d8;
                margin-bottom: 1rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .insight-item {{
                background: #f7fafc;
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 0.5rem;
                border-left: 4px solid #5a67d8;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 EMI教學研究數據儀表板</h1>
                <p>生成式AI輔助的雙語教學創新研究</p>
                <div class="info-bar">
                    <span>📊 當前週次：第10週</span>
                    <span>🔄 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                </div>
            </div>
            
            <div class="dashboard">
                <div class="metric-card">
                    <h3>🎯 研究關鍵指標</h3>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {stats['avg_quality']*20}%"></div>
                        </div>
                        <span class="status {'achieved' if stats['avg_quality'] >= 3.0 else 'not-achieved'}">
                            {'✅ 已達標' if stats['avg_quality'] >= 3.0 else '❌ 未達標'}
                        </span>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>📊 基礎統計資料</h3>
                    <div style="margin-bottom: 1rem;">
                        <div class="metric-target">總互動次數：</div>
                        <div class="metric-value">{stats['total_interactions']}</div>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <div class="metric-target">活躍學生數：</div>
                        <div class="metric-value">{stats['active_students']}</div>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <div class="metric-target">今日使用量：</div>
                        <div class="metric-value">{stats['today_usage']}</div>
                    </div>
                    <div>
                        <div class="metric-target">系統運行狀態：</div>
                        <span class="status running">🟢 正常運行</span>
                    </div>
                </div>
                
                <div class="ranking-table">
                    <h3>👥 學生參與度排行（本週）</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>排名</th>
                                <th>學生</th>
                                <th>發言數</th>
                                <th>品質分</th>
                                <th>參與度</th>
                            </tr>
                        </thead>
                        <tbody>
                            {generate_student_ranking_html(student_engagement)}
                        </tbody>
                    </table>
                </div>
                
                <div class="ranking-table">
                    <h3>👥 小組活躍度排行</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>小組ID</th>
                                <th>活躍分數</th>
                                <th>訊息數</th>
                                <th>參與人數</th>
                            </tr>
                        </thead>
                        <tbody>
                            {generate_group_ranking_html(group_activity)}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="ai-insights">
                <h3>🤖 AI分析建議</h3>
                {generate_ai_insights(stats)}
            </div>
        </div>
    </body>
    </html>
    '''
    return html

def generate_student_ranking_html(students):
    """生成學生排行HTML"""
    if not students:
        return '<tr><td colspan="5" style="text-align: center; color: #666;">暫無數據</td></tr>'
    
    html = ""
    for i, student in enumerate(students[:10], 1):
        html += f'''
        <tr>
            <td>{i}</td>
            <td>{student['user_name']}</td>
            <td>{student['message_count']}</td>
            <td>{student['avg_quality']:.1f}</td>
            <td><span class="engagement-level {student['engagement_level']}">{student['engagement_level']}</span></td>
        </tr>
        '''
    return html

def generate_group_ranking_html(groups):
    """生成小組排行HTML"""
    if not groups:
        return '<tr><td colspan="4" style="text-align: center; color: #666;">暫無數據</td></tr>'
    
    html = ""
    for group in groups:
        html += f'''
        <tr>
            <td>{group['group_name']}</td>
            <td>{group['activity_count']}</td>
            <td>{group['activity_count']}</td>
            <td>{group['participant_count']}</td>
        </tr>
        '''
    return html

def generate_ai_insights(stats):
    """生成AI分析建議"""
    insights = []
    
    if stats['weekly_usage_rate'] < 70:
        insights.append("建議增加互動活動以提升學生參與率")
    
    if stats['avg_interactions_per_user'] < 5:
        insights.append("可考慮設計更多引導性問題來促進討論")
    
    if stats['avg_quality'] < 3.0:
        insights.append("建議提供更多學術討論範例來提升討論品質")
    
    if stats['total_interactions'] > 0:
        insights.append(f"系統運行良好，已記錄 {stats['total_interactions']} 次互動")
    
    if not insights:
        insights.append("系統運行正常，持續監控學習成效")
    
    html = ""
    for insight in insights:
        html += f'<div class="insight-item">{insight}</div>'
    
    return html

@app.route("/weekly_report", methods=['GET'])
def weekly_report():
    """週報告頁面"""
    stats = get_research_stats()
    
    html = f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EMI教學研究週報告</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Microsoft JhengHei', sans-serif; 
                background: #f8fafc;
                color: #333;
                line-height: 1.6;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                padding: 2rem;
            }}
            .report-header {{
                background: white;
                border-radius: 10px;
                padding: 2rem;
                margin-bottom: 2rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .report-section {{
                background: white;
                border-radius: 10px;
                padding: 2rem;
                margin-bottom: 2rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .section-title {{
                color: #5a67d8;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 0.5rem;
                margin-bottom: 1.5rem;
            }}
            .stat-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin: 1rem 0;
            }}
            .stat-item {{
                background: #f7fafc;
                padding: 1rem;
                border-radius: 8px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 1.5rem;
                font-weight: bold;
                color: #5a67d8;
            }}
            .stat-label {{
                font-size: 0.9rem;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="report-header">
                <h1>📊 EMI教學研究週報告</h1>
                <p>第10週 • {datetime.now().strftime('%Y年%m月%d日')}</p>
            </div>
            
            <div class="report-section">
                <h2 class="section-title">📈 本週數據摘要</h2>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-value">{stats['total_interactions']}</div>
                        <div class="stat-label">總互動次數</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{stats['active_students']}</div>
                        <div class="stat-label">活躍學生數</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{stats['weekly_usage_rate']}%</div>
                        <div class="stat-label">週使用率</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{stats['avg_quality']}</div>
                        <div class="stat-label">平均品質分</div>
                    </div>
                </div>
            </div>
            
            <div class="report-section">
                <h2 class="section-title">🎯 研究目標達成情況</h2>
                <p><strong>週使用率：</strong> {stats['weekly_usage_rate']}% {'✅ 已達標' if stats['weekly_usage_rate'] >= 70 else '❌ 未達標 (目標≥70%)'}</p>
                <p><strong>平均發言次數：</strong> {stats['avg_interactions_per_user']}次/週 {'✅ 已達標' if stats['avg_interactions_per_user'] >= 5 else '❌ 未達標 (目標≥5次)'}</p>
                <p><strong>討論品質：</strong> {stats['avg_quality']}/5.0 {'✅ 良好' if stats['avg_quality'] >= 3.0 else '⚠️ 待改善'}</p>
            </div>
            
            <div class="report-section">
                <h2 class="section-title">💡 教學建議</h2>
                <ul>
                    <li>持續鼓勵學生使用英語進行學術討論</li>
                    <li>設計更多互動式活動來提升參與度</li>
                    <li>提供及時回饋以提升討論品質</li>
                    <li>善用AI助手引導深度思考</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route("/export_research_data", methods=['GET'])
def export_research_data():
    """匯出研究數據為CSV格式"""
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
        
        # 生成CSV內容
        csv_content = "時間,學生姓名,訊息類型,內容,品質分數,包含關鍵詞,英語比例,群組ID\n"
        for row in results:
            csv_content += f'"{row[0]}","{row[1]}","{row[2]}","{row[3][:50]}...",{row[4]},{row[5]},{row[6]},"{row[7] or ""}"\n'
        
        return csv_content, 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': f'attachment; filename="emi_research_data_{datetime.now().strftime("%Y%m%d")}.csv"'
        }
        
    except Exception as e:
        return f"匯出失敗: {e}", 500

@app.route("/test_routes")
def test_routes():
    """測試所有路由是否正常載入"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{list(rule.methods)} {rule.rule} -> {rule.endpoint}")
    
    return "<br>".join([f"<h2>Total routes: {len(routes)}</h2>"] + routes)

@app.route("/health")
def health_check():
    """健康檢查端點"""
    return "OK"

# 初始化資料庫
init_database()

# 給 Gunicorn 使用的 application 物件
application = app

if __name__ == "__main__":
    print("🚀 啟動EMI教學研究系統...")
    print("📊 研究儀表板：/research_dashboard")
    print("📈 週報告：/weekly_report") 
    print("📤 數據匯出：/export_research_data")
    print("🔍 路由測試：/test_routes")
    
    # 顯示註冊的路由
    print("\n📝 已註冊的路由：")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)="metric-target">週使用率目標：≥70%</div>
                        <div class="metric-value">{stats['weekly_usage_rate']}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(stats['weekly_usage_rate'], 100)}%"></div>
                        </div>
                        <span class="status {'achieved' if stats['weekly_usage_rate'] >= 70 else 'not-achieved'}">
                            {'✅ 已達標' if stats['weekly_usage_rate'] >= 70 else '❌ 未達標'}
                        </span>
                    </div>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <div class="metric-target">平均發言次數目標：≥5次/週</div>
                        <div class="metric-value">{stats['avg_interactions_per_user']} 次</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(stats['avg_interactions_per_user']*20, 100)}%"></div>
                        </div>
                        <span class="status {'achieved' if stats['avg_interactions_per_user'] >= 5 else 'not-achieved'}">
                            {'✅ 已達標' if stats['avg_interactions_per_user'] >= 5 else '❌ 未達標'}
                        </span>
                    </div>
                    
                    <div>
                        <div class="metric-target">討論品質平均分：</div>
                        <div class="metric-value">{stats['avg_quality']} / 5.0</div>
                        <div class
