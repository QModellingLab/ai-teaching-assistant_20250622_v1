# app.py - Railway部署版本
# LINE Bot + Gemini AI 教學助手 (完整更新版)

import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

# =============================================================================
# 環境變數設定（Railway部署用）
# =============================================================================

# 從環境變數讀取API金鑰（部署時自動使用）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '/FWGFeTl5+9MyyqJry49vlafcpvAl5d5UekpsZbkd/V5Cnk8zES8J9YDM6msNqkJJeC39ivYPA/zQNmuamcDQexc23SakFgwl61hPhdDsk4P2koHSusVKC4oYP67up/+AKrql1cQY8vLf3Tx3prh1QdB04t89/1O/w1cDnyilFU=')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', 'cf2728ecaf0dba522c10c15a99801f68')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyD2kVQffsdK0RDwHjIe8xWQAqlm-9ZK3Rs')

# =============================================================================
# 初始化設定
# =============================================================================

app = Flask(__name__)

# LINE Bot API 初始化
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Gemini AI 初始化
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# =============================================================================
# 資料庫設定 - 自動記錄學生互動數據
# =============================================================================

def init_database():
    """初始化SQLite資料庫"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        # 建立學生互動記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT,
                message TEXT,
                ai_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_type TEXT DEFAULT 'question'
            )
        ''')
        
        # 建立使用統計表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date DATE DEFAULT CURRENT_DATE,
                message_count INTEGER DEFAULT 1,
                UNIQUE(user_id, date)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

def save_interaction(user_id, user_name, message, ai_response):
    """記錄學生與AI的互動"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        # 先嘗試建立表格（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT,
                message TEXT,
                ai_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_type TEXT DEFAULT 'question'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date DATE DEFAULT CURRENT_DATE,
                message_count INTEGER DEFAULT 1,
                UNIQUE(user_id, date)
            )
        ''')
        
        # 記錄互動
        cursor.execute('''
            INSERT INTO student_interactions 
            (user_id, user_name, message, ai_response)
            VALUES (?, ?, ?, ?)
        ''', (user_id, user_name, message, ai_response))
        
        # 更新使用統計
        cursor.execute('''
            INSERT OR REPLACE INTO usage_stats (user_id, date, message_count)
            VALUES (?, date('now'), 
                    COALESCE((SELECT message_count FROM usage_stats 
                             WHERE user_id = ? AND date = date('now')), 0) + 1)
        ''', (user_id, user_id))
        
        conn.commit()
        conn.close()
        print(f"✅ Interaction saved for user {user_name}")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        # 即使資料庫失敗，也不影響LINE回應

# =============================================================================
# AI 教學助手功能 - EMI英語教學（簡潔版）
# =============================================================================

def generate_ai_response(user_message, user_name="Student"):
    """使用Gemini AI生成教學回應 - 簡潔版"""
    try:
        # EMI教學情境的英文提示詞 - 簡潔版
        prompt = f"""
You are an AI Teaching Assistant for the course "Practical Applications of AI in Life and Learning" - an EMI course at a Taiwanese university.

Student Name: {user_name}
Student Question: {user_message}

RESPONSE GUIDELINES:
1. KEEP IT SHORT: 2-3 sentences maximum unless student asks for more details
2. PRIMARY LANGUAGE: English (EMI course)
3. TAIWANESE CONTEXT: Use Traditional Chinese (繁體中文) assistance when needed
4. SIMPLE & CLEAR: Use basic academic English, avoid jargon
5. PRACTICAL: Give ONE simple example, not multiple

RESPONSE PATTERN:
- Brief answer (2-3 sentences)
- ONE simple example
- If needed: Key term in Traditional Chinese (關鍵詞繁體中文)
- End with: "Want to know more?" or "需要更詳細的說明嗎？"

EXAMPLES:
Q: "What is AI?"
A: "AI is computer systems that can think and learn like humans. For example, Siri understanding your voice. (人工智慧 = 像人類一樣思考學習的電腦系統) Want to know more?"

Q: "什麼是機器學習？"
A: "Machine Learning means computers learn from data without being programmed for every task (機器學習 = 電腦從資料中自動學習). Like how Netflix recommends movies based on what you watched. 需要更詳細的說明嗎？"

REMEMBER: Short, simple, practical. Let students ask for details if they want more.
"""
        
        # 調用Gemini API
        response = model.generate_content(prompt)
        
        # 檢查回應是否有效
        if response.text:
            return response.text.strip()
        else:
            return "I apologize, but I cannot answer this question right now. Please try again later or rephrase your question."
            
    except Exception as e:
        print(f"AI Response Error: {e}")
        return "I'm sorry, the AI assistant is temporarily unavailable. Please try again later."

# =============================================================================
# LINE Bot 訊息處理 - 支援群組@觸發
# =============================================================================

@app.route("/", methods=['GET'])
def home():
    """首頁 - 確認服務運行"""
    return """
    <h1>🤖 AI Teaching Assistant</h1>
    <h2>📚 Course: Practical Applications of AI in Life and Learning (EMI)</h2>
    <h3>👩‍🏫 Principal Investigator: Prof. Yu-Yao Tseng</h3>
    <p>✅ Service is running successfully!</p>
    <p>🔗 Add our LINE Bot to start learning!</p>
    <hr>
    <h4>📱 How to use:</h4>
    <ul>
        <li><strong>Personal chat:</strong> Ask directly</li>
        <li><strong>Group chat:</strong> Start with @ symbol</li>
    </ul>
    """

@app.route("/callback", methods=['POST'])
def callback():
    """LINE Bot Webhook 接收訊息"""
    # 獲取X-Line-Signature標頭
    signature = request.headers['X-Line-Signature']
    
    # 獲取請求內容
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理學生的文字訊息 - 群組中使用@觸發"""
    
    # 獲取訊息資訊
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    
    # 檢查是否為群組訊息
    is_group_message = hasattr(event.source, 'group_id') or hasattr(event.source, 'room_id')
    
    # 群組中的@觸發條件
    if is_group_message:
        # 只檢查@符號開頭
        if user_message.startswith('@'):
            # 移除@符號和可能的AI關鍵字，保留實際問題
            user_message = user_message[1:].strip()  # 移除@符號
            
            # 移除常見的AI呼叫詞（如果有的話）
            ai_keywords = ['ai', 'AI', '助教', '小助教']
            for keyword in ai_keywords:
                if user_message.startswith(keyword):
                    user_message = user_message[len(keyword):].strip()
                    break
        else:
            # 群組中沒有@符號開頭，不回應
            return
    
    # 如果處理後沒有實際問題，不回應
    if not user_message:
        return
    
    # 獲取學生姓名
    try:
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
    except:
        user_name = "Student"
    
    # 生成AI回應
    ai_response = generate_ai_response(user_message, user_name)
    
    # 群組中添加@回應
    if is_group_message:
        ai_response = f"@{user_name} {ai_response}"
    
    # 記錄互動數據（用於研究分析）
    save_interaction(user_id, user_name, user_message, ai_response)
    
    # 回覆學生
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_response)
    )
    
    print(f"✅ Responded to student {user_name}: {user_message[:30]}...")

# =============================================================================
# 研究數據分析功能
# =============================================================================

def get_usage_statistics():
    """獲取使用統計數據（用於研究分析）"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        # 總互動次數
        cursor.execute('SELECT COUNT(*) FROM student_interactions')
        total_interactions = cursor.fetchone()[0]
        
        # 活躍學生數
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM student_interactions')
        active_students = cursor.fetchone()[0]
        
        # 今日使用量
        cursor.execute('''
            SELECT COUNT(*) FROM student_interactions 
            WHERE date(timestamp) = date('now')
        ''')
        today_usage = cursor.fetchone()[0]
        
        # 每位學生的使用頻率
        cursor.execute('''
            SELECT user_name, COUNT(*) as interaction_count
            FROM student_interactions 
            GROUP BY user_id, user_name
            ORDER BY interaction_count DESC
        ''')
        user_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_interactions': total_interactions,
            'active_students': active_students,
            'today_usage': today_usage,
            'user_stats': user_stats
        }
    except Exception as e:
        print(f"❌ Statistics error: {e}")
        return {'error': str(e)}

def export_research_data():
    """匯出研究數據為JSON格式"""
    try:
        conn = sqlite3.connect('teaching_bot.db')
        cursor = conn.cursor()
        
        # 獲取所有互動記錄
        cursor.execute('''
            SELECT user_id, user_name, message, ai_response, timestamp
            FROM student_interactions
            ORDER BY timestamp
        ''')
        
        interactions = []
        for row in cursor.fetchall():
            interactions.append({
                'user_id': row[0],
                'user_name': row[1],
                'message': row[2],
                'ai_response': row[3],
                'timestamp': row[4]
            })
        
        conn.close()
        
        # 儲存為JSON檔案
        filename = f'research_data_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(interactions, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Research data exported: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Export error: {e}")
        return None

# =============================================================================
# 健康檢查端點
# =============================================================================

@app.route("/health", methods=['GET'])
def health_check():
    """健康檢查 - Railway監控用"""
    return {"status": "healthy", "service": "AI Teaching Assistant"}, 200

@app.route("/stats", methods=['GET'])
def show_stats():
    """顯示使用統計 - 研究用"""
    stats = get_usage_statistics()
    return stats

# =============================================================================
# 主程式執行 - Railway部署版
# =============================================================================

if __name__ == "__main__":
    print("🚀 Starting AI Teaching Assistant...")
    print("📚 Course: Practical Applications of AI in Life and Learning (EMI)")
    print("👩‍🏫 Principal Investigator: Prof. Yu-Yao Tseng")
    print("🌍 Language: English-Medium Instruction (EMI)")
    print("📱 Usage: Personal chat (direct), Group chat (@symbol)")
    print("=" * 60)
    
    # 初始化資料庫
    init_database()
    
    # 顯示設定狀態
    print("✅ LINE Bot Configuration Complete")
    print("✅ Gemini AI Configuration Complete")
    print("=" * 60)
    print("📊 System Features:")
    print("• Students interact with AI through LINE (English)")
    print("• Automatic data logging for research analysis")
    print("• EMI teaching support and engagement")
    print("• Group chat support with @ trigger")
    print("• Concise, student-friendly responses")
    print("• Traditional Chinese assistance when needed")
    print("=" * 60)
    
    # Railway部署設定
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
