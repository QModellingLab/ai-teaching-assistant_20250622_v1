# app.py - Railway部署版本
# LINE Bot + Gemini AI 教學助手 (部署版)

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

def save_interaction(user_id, user_name, message, ai_response):
    """記錄學生與AI的互動"""
    conn = sqlite3.connect('teaching_bot.db')
    cursor = conn.cursor()
    
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

# =============================================================================
# AI 教學助手功能 - EMI英語教學
# =============================================================================

def generate_ai_response(user_message, user_name="Student"):
    """使用Gemini AI生成教學回應 - EMI全英語教學"""
    try:
        # EMI教學情境的英文提示詞
        prompt = f"""
You are an AI Teaching Assistant for the course "Practical Applications of AI in Life and Learning" - an EMI (English-Medium Instruction) course.

Student Name: {user_name}
Student Question: {user_message}

Please respond in ENGLISH ONLY with a friendly, professional attitude and:
1. Provide clear and easy-to-understand explanations
2. Give practical real-life examples
3. Encourage students to think deeper
4. Use academic but accessible English
5. Keep responses under 200 words
6. Be encouraging and supportive for non-native English speakers

If the student greets you, respond warmly and guide them toward learning.
If the question is beyond the course scope, gently redirect to AI applications topics.
Remember: This is an EMI course, so maintain English throughout.
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
# LINE Bot 訊息處理
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
    """處理學生的文字訊息"""
    # 獲取學生資訊
    user_id = event.source.user_id
    user_message = event.message.text
    
    # 獲取學生姓名（如果可能）
    try:
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
    except:
        user_name = "Student"
    
    # 生成AI回應
    ai_response = generate_ai_response(user_message, user_name)
    
    # 記錄互動數據（用於研究分析）
    save_interaction(user_id, user_name, user_message, ai_response)
    
    # 回覆學生
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_response)
    )
    
    print(f"✅ Responded to student {user_name}: {user_message[:30]}...")

# =============================================================================
# 健康檢查端點
# =============================================================================

@app.route("/health", methods=['GET'])
def health_check():
    """健康檢查 - Railway監控用"""
    return {"status": "healthy", "service": "AI Teaching Assistant"}, 200

# =============================================================================
# 主程式執行 - Railway部署版
# =============================================================================

if __name__ == "__main__":
    print("🚀 Starting AI Teaching Assistant...")
    print("📚 Course: Practical Applications of AI in Life and Learning (EMI)")
    print("👩‍🏫 Principal Investigator: Prof. Yu-Yao Tseng")
    print("🌍 Language: English-Medium Instruction (EMI)")
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
    print("• Research data export for academic study")
    print("=" * 60)
    
    # Railway部署設定
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)