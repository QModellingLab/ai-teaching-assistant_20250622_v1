# =================== app.py 優化版 - 第1段開始 ===================
# 基本導入和配置

import os
import json
import logging
import datetime
import time
import threading
import re
from flask import Flask, request, abort, jsonify, render_template_string
from flask import make_response, flash, redirect, url_for
from datetime import timedelta
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai
from urllib.parse import quote

# =================== 日誌配置 ===================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# =================== 環境變數配置 ===================

# LINE Bot 設定
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN') or os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET') or os.getenv('LINE_CHANNEL_SECRET')

# Gemini AI 設定
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Flask 設定
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
PORT = int(os.getenv('PORT', 8080))
HOST = os.getenv('HOST', '0.0.0.0')

# =================== 應用程式初始化 ===================

app = Flask(__name__)
app.secret_key = SECRET_KEY

# LINE Bot API 初始化
if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(CHANNEL_SECRET)
    logger.info("✅ LINE Bot 服務已成功初始化")
else:
    line_bot_api = None
    handler = None
    logger.error("❌ LINE Bot 初始化失敗：缺少必要的環境變數")

# Gemini AI 初始化
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("✅ Gemini AI 已成功配置")
    except Exception as e:
        logger.error(f"❌ Gemini AI 配置失敗: {e}")
else:
    logger.error("❌ Gemini AI 初始化失敗：缺少 GEMINI_API_KEY")

# =================== 模型配置 ===================

def get_best_available_model():
    """獲取最佳可用的 Gemini 模型"""
    models_priority = [
        'gemini-2.5-flash',
        'gemini-2.0-flash-exp', 
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro'
    ]
    
    if not GEMINI_API_KEY:
        return None
    
    try:
        available_models = [m.name for m in genai.list_models()]
        for model in models_priority:
            if f'models/{model}' in available_models:
                logger.info(f"🤖 使用模型: {model}")
                return model
        
        # 如果找不到優先模型，使用第一個可用的
        if available_models:
            fallback_model = available_models[0].replace('models/', '')
            logger.info(f"🔄 使用備用模型: {fallback_model}")
            return fallback_model
            
    except Exception as e:
        logger.error(f"❌ 模型檢查錯誤: {e}")
    
    return 'gemini-pro'  # 默認模型

CURRENT_MODEL = get_best_available_model()

# =================== 學生註冊機制（優化版）===================

def handle_student_registration(line_user_id, message_text, display_name=""):
    """優化的註冊流程：學號 → 姓名 → 確認"""
    from models import Student
    
    student = Student.get_or_none(Student.line_user_id == line_user_id)
    
    # === 步驟 1: 新用戶，詢問學號 ===
    if not student:
        student = Student.create(
            name="",
            line_user_id=line_user_id,
            student_id="",
            registration_step=1,  # 等待學號
            created_at=datetime.datetime.now(),
            last_active=datetime.datetime.now()
        )
        
        return """🎓 Welcome to EMI AI Teaching Assistant!

I'm your AI learning partner for the course "Practical Applications of AI in Life and Learning."

**Step 1/3:** Please provide your **Student ID**
(請提供您的學號)

Format: A1234567
Example: A1234567"""
    
    # === 步驟 2: 收到學號，詢問姓名 ===
    elif student.registration_step == 1:
        student_id = message_text.strip().upper()
        
        # 簡單驗證學號格式
        if len(student_id) >= 6 and student_id[0].isalpha():
            student.student_id = student_id
            student.registration_step = 2  # 等待姓名
            student.save()
            
            return f"""✅ Student ID received: {student_id}

**Step 2/3:** Please tell me your **name**
(請告訴我您的姓名)

Example: John Smith / 王小明"""
        else:
            return """❌ Invalid format. Please provide a valid Student ID.

Format: A1234567 (Letter + Numbers)
Example: A1234567"""
    
    # === 步驟 3: 收到姓名，最終確認 ===
    elif student.registration_step == 2:
        name = message_text.strip()
        
        if len(name) >= 2:  # 基本驗證
            student.name = name
            student.registration_step = 3  # 等待確認
            student.save()
            
            return f"""**Step 3/3:** Please confirm your information:

📋 **Your Information:**
• **Name:** {name}
• **Student ID:** {student.student_id}

Reply with:
• **"YES"** to confirm and complete registration
• **"NO"** to start over

(回覆 YES 確認，或 NO 重新填寫)"""
        else:
            return """❌ Please provide a valid name (at least 2 characters).

Example: John Smith / 王小明"""
    
    # === 步驟 4: 處理確認回應 ===
    elif student.registration_step == 3:
        response = message_text.strip().upper()
        
        if response in ['YES', 'Y', '是', '確認', 'CONFIRM']:
            student.registration_step = 0  # 註冊完成
            student.save()
            
            return f"""🎉 Registration completed successfully!

📋 **Welcome, {student.name}!**
• **Student ID:** {student.student_id}
• **Registration Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

🚀 **You can now start learning!**

I can help you with:
📚 **Academic questions** - Course content and concepts
🔤 **English learning** - Grammar, vocabulary, pronunciation  
💡 **Study guidance** - Learning strategies and tips
🎯 **Course discussions** - AI applications in life and learning

**Just ask me anything!** 😊
Example: "What is machine learning?" or "Help me with English grammar"."""
            
        elif response in ['NO', 'N', '否', '重新', 'RESTART']:
            # 重新開始註冊
            student.registration_step = 1
            student.name = ""
            student.student_id = ""
            student.save()
            
            return """🔄 **Restarting registration...**

**Step 1/3:** Please provide your **Student ID**
(請提供您的學號)

Format: A1234567
Example: A1234567"""
        else:
            return f"""❓ Please reply with **YES** or **NO**:

📋 **Your Information:**
• **Name:** {student.name}
• **Student ID:** {student.student_id}

Reply with:
• **"YES"** to confirm ✅
• **"NO"** to restart ❌"""
    
    # 註冊已完成
    return None

# =================== AI回應生成（簡化，移除快取）===================

def generate_ai_response(message_text, student):
    """生成AI回應（移除快取機制）"""
    try:
        if not GEMINI_API_KEY or not CURRENT_MODEL:
            return "AI service is currently unavailable. Please try again later."
        
        # 建構提示詞
        prompt = f"""You are an EMI (English as a Medium of Instruction) teaching assistant for the course "Practical Applications of AI in Life and Learning."

Student: {student.name} (ID: {student.student_id})
Question: {message_text}

Please provide a helpful, academic response in English (150 words max). Focus on:
- Clear, educational explanations
- Practical examples when relevant  
- Encouraging tone for learning
- Academic language appropriate for university students

Response:"""

        # 調用 Gemini API
        model = genai.GenerativeModel(CURRENT_MODEL)
        response = model.generate_content(prompt)
        
        return response.text if response.text else "I'm sorry, I couldn't generate a proper response. Could you please rephrase your question?"
        
    except Exception as e:
        logger.error(f"❌ AI 回應生成錯誤: {e}")
        return "Sorry, I encountered an issue. Please rephrase your question!"

def generate_learning_suggestion(student):
    """生成學習建議（簡化版）"""
    from models import Message
    
    try:
        # 獲取最近對話記錄
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(10))
        
        if not messages:
            return "Welcome! Start asking questions to receive personalized learning suggestions."
        
        # 準備給AI的簡潔提示
        recent_conversations = "\n".join([
            f"- {msg.content[:80]}..." for msg in messages[:5] if msg.content
        ])
        
        prompt = f"""Based on recent conversations, provide learning advice in simple English (150 words max).

Student: {student.name}
Total conversations: {len(messages)}
Recent topics:
{recent_conversations}

Provide:
1. Learning strengths (1-2 sentences)
2. Areas for improvement (1-2 sentences)  
3. Specific recommendations (1-2 sentences)

Keep it encouraging and practical. Use simple vocabulary."""

        if not GEMINI_API_KEY or not CURRENT_MODEL:
            return get_fallback_suggestion(student, len(messages))
        
        model = genai.GenerativeModel(CURRENT_MODEL)
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text.strip()
        else:
            return get_fallback_suggestion(student, len(messages))
            
    except Exception as e:
        logger.error(f"AI生成建議失敗: {e}")
        return get_fallback_suggestion(student, len(messages))

def get_fallback_suggestion(student, message_count):
    """備用的學習建議（不依賴AI）"""
    if message_count >= 10:
        activity_level = "actively participating"
        suggestion = "Keep up this great learning enthusiasm! Try challenging yourself with more complex topics."
    elif message_count >= 5:
        activity_level = "moderately engaged"
        suggestion = "Good learning attitude! Consider increasing interaction frequency for better results."
    else:
        activity_level = "getting started"
        suggestion = "Welcome! Feel free to ask more questions - any learning doubts can be discussed anytime."
    
    days_since_creation = (datetime.datetime.now() - student.created_at).days
    
    return f"""📊 {student.name}'s Learning Status

🔹 **Performance**: You are {activity_level}
You have {message_count} conversation records in {days_since_creation} days, showing continuous learning motivation.

🔹 **Suggestion**: {suggestion}

🔹 **Tip**: Regularly review previous discussions and try applying what you've learned in real situations to deepen understanding!"""

# =================== app.py 優化版 - 第1段結束 ===================

# =================== app.py 優化版 - 第2段開始 ===================
# LINE Bot Webhook 和訊息處理（同步流程）

@app.route('/callback', methods=['POST'])
def callback():
    """LINE Bot Webhook 回調處理"""
    if not (line_bot_api and handler):
        logger.error("❌ LINE Bot 未正確配置")
        abort(500)
    
    # 取得請求標頭中的 X-Line-Signature
    signature = request.headers.get('X-Line-Signature', '')
    
    # 取得請求內容
    body = request.get_data(as_text=True)
    logger.info(f"📥 收到 Webhook 請求")
    
    # 驗證請求
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("❌ 無效的 LINE Signature")
        abort(400)
    except Exception as e:
        logger.error(f"❌ Webhook 處理錯誤: {e}")
        abort(500)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """優化的訊息處理流程（同步處理）"""
    logger.info(f"📱 收到 LINE 訊息: {event.message.text[:50]}...")
    
    try:
        from models import Student, Message
        
        # === 1. 獲取用戶資訊 ===
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
        # 取得用戶資料
        try:
            profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name
            logger.info(f"👤 用戶: {display_name} ({user_id[:10]}...)")
        except Exception as e:
            logger.warning(f"⚠️ 無法取得用戶資料: {e}")
            display_name = f"用戶_{user_id[:8]}"
        
        # === 2. 處理註冊流程 ===
        registration_response = handle_student_registration(user_id, message_text, display_name)
        if registration_response:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=registration_response)
            )
            return
        
        # === 3. 取得已註冊學生 ===
        student = Student.get_or_none(Student.line_user_id == user_id)
        if not student or student.registration_step != 0:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="Please complete registration first.")
            )
            return
        
        # === 4. 記錄學生訊息到資料庫 ===
        student_message = Message.create(
            student=student,
            content=message_text,
            timestamp=datetime.datetime.now(),
            source_type='student'
        )
        logger.info(f"💾 學生訊息已記錄: ID {student_message.id}")
        
        # === 5. 生成 AI 回應 ===
        start_time = time.time()
        ai_response_text = generate_ai_response(message_text, student)
        response_time = time.time() - start_time
        logger.info(f"🤖 AI 回應生成完成，耗時: {response_time:.2f}秒")
        
        # === 6. 記錄 AI 回應到資料庫 ===
        ai_message = Message.create(
            student=student,
            content=ai_response_text,
            timestamp=datetime.datetime.now(),
            source_type='ai'
        )
        logger.info(f"💾 AI 回應已記錄: ID {ai_message.id}")
        
        # === 7. 發送回應給學生 ===
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response_text)
        )
        
        # === 8. 更新學生活動記錄 ===
        student.last_active = datetime.datetime.now()
        if hasattr(student, 'message_count'):
            student.message_count = (student.message_count or 0) + 1
        student.save()
        
        logger.info(f"✅ 訊息處理完成 - 學生: {student.name}")
        
    except LineBotApiError as e:
        logger.error(f"❌ LINE Bot API 錯誤: {e}")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="Sorry, I'm having some technical difficulties. Please try again! 🔧")
            )
        except:
            pass
            
    except Exception as e:
        logger.error(f"❌ 訊息處理錯誤: {e}")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="I encountered an issue. Please try again! 🤔")
            )
        except:
            pass

# =================== 系統路由 ===================

@app.route('/')
def index():
    """簡化版系統首頁"""
    try:
        from models import Student, Message
        
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        
        # 本週活躍學生
        week_ago = datetime.datetime.now() - timedelta(days=7)
        try:
            active_students = Student.select().where(
                Student.last_active.is_null(False) & 
                (Student.last_active >= week_ago)
            ).count()
        except:
            active_students = 0
        
        # 今日對話數
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            today_messages = Message.select().where(
                Message.timestamp >= today_start
            ).count()
        except:
            today_messages = 0
        
        # 系統狀態
        ai_status = "✅ 正常" if GEMINI_API_KEY else "❌ 未配置"
        line_status = "✅ 已連接" if (CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET) else "❌ 未配置"
        
        # 生成簡化首頁HTML
        index_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EMI 智能教學助理系統</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .header p {{
            color: #7f8c8d;
            font-size: 1.1em;
        }}
        
        /* 統計卡片 */
        .stats-simple {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-left: 4px solid #3498db;
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        /* 系統狀態 */
        .system-status {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .status-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }}
        .status-item:last-child {{
            border-bottom: none;
        }}
        .status-ok {{
            color: #27ae60;
            font-weight: bold;
        }}
        
        /* 快速操作按鈕 */
        .quick-actions {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        .action-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .action-card:hover {{
            transform: translateY(-5px);
        }}
        .action-btn {{
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            transition: background 0.3s ease;
        }}
        .action-btn:hover {{
            background: #2980b9;
        }}
        .btn-success {{ background: #27ae60; }}
        .btn-success:hover {{ background: #219a52; }}
        .btn-orange {{ background: #f39c12; }}
        .btn-orange:hover {{ background: #d68910; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 系統標題 -->
        <div class="header">
            <h1>🎓 EMI 智能教學助理系統</h1>
            <p>Practical Applications of AI in Life and Learning - 優化版</p>
        </div>
        
        <!-- 簡化統計 -->
        <div class="stats-simple">
            <div class="stat-card">
                <div class="stat-number">{total_students}</div>
                <div class="stat-label">👥 總學生數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_messages}</div>
                <div class="stat-label">💬 總對話數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{active_students}</div>
                <div class="stat-label">🔥 本週活躍</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{today_messages}</div>
                <div class="stat-label">📅 今日對話</div>
            </div>
        </div>
        
        <!-- 系統狀態 -->
        <div class="system-status">
            <h3 style="color: #2c3e50; margin-bottom: 15px;">⚙️ 系統狀態</h3>
            <div class="status-item">
                <span>🤖 AI服務 ({CURRENT_MODEL})</span>
                <span class="status-ok">{ai_status}</span>
            </div>
            <div class="status-item">
                <span>📱 LINE Bot 連接</span>
                <span class="status-ok">{line_status}</span>
            </div>
            <div class="status-item">
                <span>⚡ 回應模式</span>
                <span style="color: #2c3e50;">同步處理 (移除快取)</span>
            </div>
            <div class="status-item">
                <span>📝 註冊流程</span>
                <span style="color: #2c3e50;">學號→姓名→確認</span>
            </div>
        </div>
        
        <!-- 快速操作 -->
        <div class="quick-actions">
            <div class="action-card">
                <h4 style="color: #3498db; margin-bottom: 15px;">👥 學生管理</h4>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px;">
                    查看所有學生清單和基本統計
                </p>
                <a href="/students" class="action-btn">查看學生</a>
            </div>
            
            <div class="action-card">
                <h4 style="color: #27ae60; margin-bottom: 15px;">🔧 系統檢查</h4>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px;">
                    檢查系統運行狀態和資料庫
                </p>
                <a href="/health" class="action-btn btn-success">系統診斷</a>
            </div>
            
            <div class="action-card">
                <h4 style="color: #f39c12; margin-bottom: 15px;">📊 資料匯出</h4>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px;">
                    匯出學生清單和對話記錄
                </p>
                <a href="/download-all-questions" class="action-btn btn-orange">匯出資料</a>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        return index_html
        
    except Exception as e:
        logger.error(f"❌ 首頁載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>🤖 EMI 智能教學助理系統</h1>
            <p style="color: #dc3545;">首頁載入錯誤：{str(e)}</p>
            <a href="/health" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">檢查系統狀態</a>
        </div>
        """

# =================== app.py 優化版 - 第2段結束 ===================

# =================== app.py 優化版 - 第3段開始 ===================
# 學生管理路由

@app.route('/students')
def students_list():
    """簡化版學生管理列表頁面"""
    try:
        from models import Student, Message
        
        # 獲取所有學生
        students = list(Student.select().order_by(Student.last_active.desc()))
        
        students_page = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>學生管理 - EMI 智能教學助理</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 0; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .page-title { text-align: center; font-size: 2.5em; margin-bottom: 10px; }
        .page-subtitle { text-align: center; opacity: 0.9; }
        .controls { display: flex; justify-content: space-between; align-items: center; margin: 30px 0; }
        .search-box { padding: 10px 15px; border: 1px solid #ddd; border-radius: 25px; width: 300px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; border: none; cursor: pointer; margin-left: 10px; }
        .btn:hover { background: #0056b3; }
        .students-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        .student-card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); transition: transform 0.2s; }
        .student-card:hover { transform: translateY(-5px); }
        .student-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .student-name { font-size: 1.2em; font-weight: bold; color: #333; }
        .student-status { padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
        .status-active { background: #d4edda; color: #155724; }
        .status-inactive { background: #f8d7da; color: #721c24; }
        .student-info { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
        .info-item { text-align: center; padding: 10px; background: #f8f9fa; border-radius: 8px; }
        .info-number { font-size: 1.5em; font-weight: bold; color: #007bff; }
        .info-label { font-size: 0.8em; color: #666; margin-top: 5px; }
        .student-meta { font-size: 0.9em; color: #666; margin-bottom: 15px; }
        .student-actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .btn-sm { padding: 6px 12px; font-size: 0.8em; }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #218838; }
        .stats-summary { background: white; border-radius: 15px; padding: 20px; margin-bottom: 30px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .stat-item { text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .stat-label { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1 class="page-title">👥 學生管理系統</h1>
            <p class="page-subtitle">優化版學生清單和統計</p>
        </div>
    </div>
    
    <div class="container">
        <div class="stats-summary">
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-number">""" + str(len(students)) + """</div>
                    <div class="stat-label">總註冊學生</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">""" + str(len([s for s in students if hasattr(s, 'last_active') and s.last_active and (datetime.datetime.now() - s.last_active).days <= 7])) + """</div>
                    <div class="stat-label">本週活躍</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">""" + str(Message.select().count()) + """</div>
                    <div class="stat-label">總對話數</div>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <input type="text" class="search-box" placeholder="🔍 搜尋學生姓名..." id="searchBox" onkeyup="filterStudents()">
            <div>
                <button class="btn" onclick="location.href='/'">← 返回首頁</button>
                <button class="btn" onclick="refreshPage()">🔄 重新整理</button>
            </div>
        </div>
        
        <div class="students-grid" id="studentsGrid">"""

        if students:
            for student in students:
                # 計算學生統計資料 (簡化版)
                try:
                    message_count = Message.select().where(Message.student == student).count()
                except:
                    message_count = 0
                
                last_active_str = student.last_active.strftime('%Y-%m-%d %H:%M') if hasattr(student, 'last_active') and student.last_active else '從未使用'
                created_str = student.created_at.strftime('%Y-%m-%d') if hasattr(student, 'created_at') and student.created_at else '未知'
                
                # 計算活躍度 (簡化)
                days_since_active = 999
                if hasattr(student, 'last_active') and student.last_active:
                    days_since_active = (datetime.datetime.now() - student.last_active).days
                
                status_class = "status-active" if days_since_active <= 7 else "status-inactive"
                status_text = "活躍" if days_since_active <= 7 else "非活躍"
                
                students_page += f"""
            <div class="student-card" data-name="{student.name.lower()}">
                <div class="student-header">
                    <div class="student-name">{student.name}</div>
                    <div class="student-status {status_class}">{status_text}</div>
                </div>
                
                <div class="student-info">
                    <div class="info-item">
                        <div class="info-number">{message_count}</div>
                        <div class="info-label">對話數</div>
                    </div>
                    <div class="info-item">
                        <div class="info-number">{days_since_active if days_since_active < 999 else '∞'}</div>
                        <div class="info-label">天前活動</div>
                    </div>
                </div>
                
                <div class="student-meta">
                    📅 註冊：{created_str}<br>
                    🕒 最後活動：{last_active_str}<br>
                    🎓 學號：{getattr(student, 'student_id', '未設定')}
                </div>
                
                <div class="student-actions">
                    <a href="/student/{student.id}" class="btn btn-sm">📊 查看對話</a>
                    <a href="/students/{student.id}/summary" class="btn btn-sm btn-success">📋 學習建議</a>
                </div>
            </div>"""
        else:
            students_page += """
            <div style="grid-column: 1 / -1; text-align: center; padding: 60px; color: #666;">
                <div style="font-size: 4em; margin-bottom: 20px;">👥</div>
                <h3>還沒有註冊的學生</h3>
                <p>當學生首次使用 LINE Bot 時，系統會自動引導註冊流程。</p>
                <p><strong>✨ 優化功能：</strong>學號→姓名→確認，三步驟完成註冊！</p>
            </div>"""
        
        students_page += """
        </div>
    </div>
    
    <script>
        function filterStudents() {
            const searchTerm = document.getElementById('searchBox').value.toLowerCase();
            const studentCards = document.querySelectorAll('.student-card');
            
            studentCards.forEach(card => {
                const name = card.getAttribute('data-name');
                card.style.display = name.includes(searchTerm) ? 'block' : 'none';
            });
        }
        
        function refreshPage() {
            location.reload();
        }
    </script>
</body>
</html>
        """
        
        return students_page
        
    except Exception as e:
        logger.error(f"❌ 學生列表載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>👥 學生管理系統</h1>
            <p style="color: #dc3545;">載入錯誤：{str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """簡化版學生詳細資料頁面"""
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return """
            <div style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>❌ 學生不存在</h1>
                <p>無法找到指定的學生記錄</p>
                <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
            </div>
            """
        
        # 獲取學生的對話記錄（最近20次）
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()).limit(20))
        
        # 簡化統計
        total_messages = Message.select().where(Message.student_id == student_id).count()
        
        # 生成簡化的學生詳細頁面
        detail_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{student.name} - 學生對話記錄</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 0; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .student-header {{ text-align: center; }}
        .student-name {{ font-size: 2.5em; margin-bottom: 10px; }}
        .student-id {{ opacity: 0.8; font-size: 1.1em; }}
        .content-section {{ background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 20px 0; }}
        .section-title {{ font-size: 1.3em; font-weight: bold; margin-bottom: 20px; color: #495057; }}
        .stats-simple {{ display: flex; justify-content: space-around; margin-bottom: 20px; }}
        .stat-item {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
        .stat-number {{ font-size: 1.8em; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #6c757d; font-size: 0.9em; margin-top: 5px; }}
        .message-list {{ max-height: 400px; overflow-y: auto; }}
        .message-item {{ background: #f8f9fa; margin-bottom: 15px; padding: 15px; border-radius: 10px; }}
        .message-meta {{ font-size: 0.8em; color: #6c757d; margin-bottom: 8px; }}
        .message-content {{ line-height: 1.5; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .back-button:hover {{ background: rgba(255,255,255,0.3); }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <a href="/students" class="back-button">← 返回學生列表</a>
            <div class="student-header">
                <h1 class="student-name">{student.name}</h1>
                <p class="student-id">學號: {getattr(student, 'student_id', '未設定')} | 註冊: {student.created_at.strftime('%Y年%m月%d日') if hasattr(student, 'created_at') and student.created_at else '未知'}</p>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="content-section">
            <div class="section-title">📊 基本統計</div>
            <div class="stats-simple">
                <div class="stat-item">
                    <div class="stat-number">{total_messages}</div>
                    <div class="stat-label">總對話數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{(datetime.datetime.now() - student.last_active).days if hasattr(student, 'last_active') and student.last_active else '∞'}</div>
                    <div class="stat-label">天前活動</div>
                </div>
            </div>
            
            <div style="margin-top: 15px; text-align: center;">
                <a href="/students/{student.id}/summary" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px;">📋 查看學習建議</a>
            </div>
        </div>
        
        <div class="content-section">
            <div class="section-title">💬 最近對話記錄</div>
            <div class="message-list">
        """
        
        if messages:
            for message in messages:
                msg_type_icon = "👤" if message.source_type in ['line', 'student'] else "🤖"
                msg_time = message.timestamp.strftime('%m月%d日 %H:%M') if message.timestamp else '未知時間'
                
                detail_html += f"""
                    <div class="message-item">
                        <div class="message-meta">
                            {msg_type_icon} {msg_time} • {'學生' if message.source_type in ['line', 'student'] else 'AI助理'}
                        </div>
                        <div class="message-content">{message.content[:300]}{'...' if len(message.content) > 300 else ''}</div>
                    </div>
                """
        else:
            detail_html += """
                    <div style="text-align: center; padding: 40px; color: #6c757d;">
                        <div style="font-size: 3em; margin-bottom: 15px;">💭</div>
                        <h4>尚無對話記錄</h4>
                        <p>這位學生還沒有開始與AI助理的對話。</p>
                    </div>
                """
        
        detail_html += f"""
            </div>
            {f'<div style="margin-top: 15px; text-align: center; padding: 10px; background: #fff3cd; border-radius: 5px; font-size: 0.9em;">📋 顯示最近20條記錄，共有 {total_messages} 條對話</div>' if total_messages > 20 else ''}
        </div>
    </div>
</body>
</html>
        """
        
        return detail_html
        
    except Exception as e:
        logger.error(f"❌ 學生詳細資料載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>❌ 載入錯誤</h1>
            <p style="color: #dc3545;">學生詳細資料載入失敗：{str(e)}</p>
            <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
        </div>
        """

# =================== app.py 優化版 - 第3段結束 ===================

# =================== app.py 優化版 - 第4段開始 ===================
# 學習建議和系統工具路由

@app.route('/students/<int:student_id>/summary')
def student_summary(student_id):
    """學生學習建議頁面（優化版）"""
    try:
        logger.info(f"📊 載入學生 {student_id} 的學習建議...")
        
        from models import Student, Message
        
        # 驗證學生是否存在
        try:
            student = Student.get_by_id(student_id)
        except:
            return """
            <div style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>❌ 學生不存在</h1>
                <p>無法找到指定的學生記錄</p>
                <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
            </div>
            """
        
        # 獲取學生基本統計資料
        messages = list(Message.select().where(Message.student_id == student_id))
        total_messages = len(messages)
        
        # 計算學習天數
        if messages:
            first_message = min(messages, key=lambda m: m.timestamp)
            learning_days = (datetime.datetime.now() - first_message.timestamp).days + 1
        else:
            learning_days = 0

        # 生成學習建議
        ai_suggestion = generate_learning_suggestion(student)

        # 生成建議頁面HTML（優化版）
        summary_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 {student.name} - 學習建議</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .student-name {{ font-size: 2em; color: #333; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-item {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-number {{ font-size: 1.5em; font-weight: bold; color: #007bff; }}
        .suggestion-content {{ background: #f8fafc; padding: 25px; border-radius: 10px; line-height: 1.7; white-space: pre-wrap; border-left: 4px solid #17a2b8; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .action-buttons {{ display: flex; gap: 10px; justify-content: center; margin-top: 20px; }}
        .btn {{ padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .btn-info {{ background: #17a2b8; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/students" class="back-button">← 返回學生列表</a>
        
        <div class="header">
            <div class="student-name">👤 {student.name}</div>
            <p>📊 個人學習建議（AI生成 150字英文）</p>
        </div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{total_messages}</div>
                <div>總對話數</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{learning_days}</div>
                <div>學習天數</div>
            </div>
        </div>
        
        <div class="suggestion-content">{ai_suggestion}</div>
        
        <div class="action-buttons">
            <a href="/student/{student_id}" class="btn btn-info">📊 查看對話記錄</a>
        </div>
    </div>
</body>
</html>
        """
        
        return summary_html
        
    except Exception as e:
        logger.error(f"❌ 學生建議頁面錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>📊 學習建議</h1>
            <p style="color: #dc3545;">建議生成錯誤：{str(e)}</p>
            <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
        </div>
        """

# =================== 系統工具路由 ===================

@app.route('/health')
def health_check():
    """系統健康檢查"""
    try:
        from models import Student, Message
        
        # 檢查資料庫連線
        student_count = Student.select().count()
        message_count = Message.select().count()
        
        # 檢查註冊狀態
        try:
            need_registration = Student.select().where(Student.registration_step > 0).count()
            completed_registration = Student.select().where(Student.registration_step == 0).count()
        except:
            need_registration = 0
            completed_registration = student_count
        
        # 檢查 AI 服務
        ai_status = "✅ 正常" if GEMINI_API_KEY else "❌ API金鑰未設定"
        current_model = CURRENT_MODEL or "未配置"
        
        # 檢查 LINE Bot
        line_status = "✅ 正常" if (CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET) else "❌ 憑證未設定"
        
        health_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系統健康檢查 - EMI 智能教學助理</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 0; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        .page-title {{ text-align: center; font-size: 2.5em; margin-bottom: 10px; }}
        .page-subtitle {{ text-align: center; opacity: 0.9; }}
        .health-card {{ background: white; border-radius: 15px; padding: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 20px 0; }}
        .status-item {{ display: flex; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid #eee; }}
        .status-item:last-child {{ border-bottom: none; }}
        .status-label {{ font-weight: bold; }}
        .status-value {{ padding: 5px 10px; border-radius: 5px; font-size: 0.9em; }}
        .status-ok {{ background: #d4edda; color: #155724; }}
        .status-error {{ background: #f8d7da; color: #721c24; }}
        .status-info {{ background: #d1ecf1; color: #0c5460; }}
        .status-warning {{ background: #fff3cd; color: #856404; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .back-button:hover {{ background: rgba(255,255,255,0.3); }}
        .refresh-btn {{ background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
        .refresh-btn:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <a href="/" class="back-button">← 返回首頁</a>
            <h1 class="page-title">🔍 系統健康檢查</h1>
            <p class="page-subtitle">優化版系統狀態監控</p>
        </div>
    </div>
    
    <div class="container">
        <div class="health-card">
            <h3>🔧 核心服務狀態</h3>
            <div class="status-item">
                <span class="status-label">AI 服務 (Gemini)</span>
                <span class="status-value {'status-ok' if GEMINI_API_KEY else 'status-error'}">{ai_status}</span>
            </div>
            <div class="status-item">
                <span class="status-label">LINE Bot 服務</span>
                <span class="status-value {'status-ok' if (CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET) else 'status-error'}">{line_status}</span>
            </div>
            <div class="status-item">
                <span class="status-label">資料庫連線</span>
                <span class="status-value status-ok">✅ 正常</span>
            </div>
            <div class="status-item">
                <span class="status-label">當前 AI 模型</span>
                <span class="status-value status-ok">{current_model}</span>
            </div>
        </div>
        
        <div class="health-card">
            <h3>📊 資料統計</h3>
            <div class="status-item">
                <span class="status-label">註冊學生數量</span>
                <span class="status-value status-ok">{student_count}</span>
            </div>
            <div class="status-item">
                <span class="status-label">對話記錄總數</span>
                <span class="status-value status-ok">{message_count}</span>
            </div>
            <div class="status-item">
                <span class="status-label">完成註冊</span>
                <span class="status-value status-ok">{completed_registration}</span>
            </div>
            <div class="status-item">
                <span class="status-label">待完成註冊</span>
                <span class="status-value {'status-warning' if need_registration > 0 else 'status-ok'}">{need_registration}</span>
            </div>
        </div>
        
        <div class="health-card">
            <h3>✨ 優化功能特色</h3>
            <div class="status-item">
                <span class="status-label">註冊流程優化</span>
                <span class="status-value status-ok">✅ 學號→姓名→確認</span>
            </div>
            <div class="status-item">
                <span class="status-label">回應處理機制</span>
                <span class="status-value status-ok">✅ 同步處理</span>
            </div>
            <div class="status-item">
                <span class="status-label">快取系統</span>
                <span class="status-value status-info">🚫 已移除</span>
            </div>
            <div class="status-item">
                <span class="status-label">AI回應風格</span>
                <span class="status-value status-ok">✅ 150字學術英文</span>
            </div>
            <div class="status-item">
                <span class="status-label">最後檢查時間</span>
                <span class="status-value status-ok">{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <button class="refresh-btn" onclick="location.reload()">🔄 重新檢查</button>
        </div>
    </div>
</body>
</html>
        """
        
        return health_html
        
    except Exception as e:
        logger.error(f"❌ 健康檢查錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>🔍 系統健康檢查</h1>
            <p style="color: #dc3545;">健康檢查失敗：{str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """

# =================== API 路由（簡化版）===================

@app.route('/api/system-stats')
def api_system_stats():
    """系統統計 API（優化版）"""
    try:
        from models import Student, Message
        
        total_students = Student.select().count()
        total_messages = Message.select().count()
        
        # 本週活躍學生
        week_ago = datetime.datetime.now() - timedelta(days=7)
        try:
            active_students = Student.select().where(
                Student.last_active.is_null(False) & 
                (Student.last_active >= week_ago)
            ).count()
        except:
            active_students = 0
        
        # 今日對話數
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            today_messages = Message.select().where(
                Message.timestamp >= today_start
            ).count()
        except:
            today_messages = 0
        
        # 註冊狀態統計
        try:
            need_registration = Student.select().where(Student.registration_step > 0).count()
            completed_registration = Student.select().where(Student.registration_step == 0).count()
        except:
            need_registration = 0
            completed_registration = total_students
        
        return jsonify({
            'total_students': total_students,
            'total_messages': total_messages,
            'active_students': active_students,
            'today_messages': today_messages,
            'completed_registration': completed_registration,
            'need_registration': need_registration,
            'ai_model': CURRENT_MODEL,
            'system_status': 'optimized',
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 系統統計API錯誤: {e}")
        return jsonify({'error': str(e)}), 500

# =================== 資料匯出功能（簡化版）===================

@app.route('/download-all-questions')
def download_all_questions():
    """下載所有學生對話記錄（優化版）"""
    try:
        from models import Student, Message
        
        logger.info("📄 下載所有學生的對話記錄...")
        
        # 獲取所有訊息
        messages = list(Message.select().join(Student).order_by(Message.timestamp.desc()))
        
        if not messages:
            return jsonify({'error': '沒有找到任何對話記錄'}), 404
        
        # 生成TSV內容（優化版）
        tsv_content = "時間\t學生姓名\t學號\t訊息內容\t來源\t註冊狀態\n"
        
        for msg in messages:
            student = msg.student
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else '未知時間'
            student_name = student.name or '未知學生'
            student_id = getattr(student, 'student_id', '未設定')
            content = msg.content.replace('\n', ' ').replace('\t', ' ')[:200]  # 限制長度
            source = '學生' if msg.source_type in ['line', 'student'] else 'AI助理'
            reg_status = '已完成' if getattr(student, 'registration_step', 0) == 0 else '未完成'
            
            tsv_content += f"{timestamp}\t{student_name}\t{student_id}\t{content}\t{source}\t{reg_status}\n"
        
        # 建立回應
        response = make_response(tsv_content)
        response.headers['Content-Type'] = 'text/tab-separated-values; charset=utf-8'
        filename = f"EMI_conversations_optimized_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"✅ 成功下載 {len(messages)} 條對話記錄")
        return response
        
    except Exception as e:
        logger.error(f"❌ 下載對話記錄錯誤: {e}")
        return jsonify({'error': '下載失敗，請稍後再試'}), 500

# =================== 載入 routes.py 的額外功能 ===================

# 載入 routes.py 中的額外路由和功能
try:
    from routes import register_routes
    register_routes(app)
    logger.info("✅ 成功載入 routes.py 的額外功能")
except ImportError:
    logger.warning("⚠️ routes.py 未找到，跳過額外功能載入")
except Exception as e:
    logger.error(f"❌ 載入 routes.py 時發生錯誤: {e}")

# =================== app.py 優化版 - 第4段結束 ===================

# =================== app.py 優化版 - 第5段開始 ===================
# 主程式啟動配置和版本說明

if __name__ == '__main__':
    """優化版主程式啟動配置"""
    
    logger.info("🚀 EMI智能教學助理系統啟動中...")
    logger.info("✨ 版本：v4.0 優化版")
    
    # 資料庫初始化檢查
    try:
        from models import initialize_db, Student, Message
        initialize_db()
        
        # 檢查資料庫連線
        student_count = Student.select().count()
        message_count = Message.select().count()
        logger.info(f"📊 資料庫狀態: {student_count} 位學生, {message_count} 條對話記錄")
        
        # 檢查註冊狀態
        try:
            need_registration = Student.select().where(Student.registration_step > 0).count()
            if need_registration > 0:
                logger.info(f"📝 待完成註冊: {need_registration} 位學生")
        except:
            pass
        
    except Exception as e:
        logger.error(f"❌ 資料庫初始化失敗: {e}")
        logger.info("🔄 嘗試重新初始化資料庫...")
        try:
            from models import create_tables
            create_tables()
            logger.info("✅ 資料庫重新初始化成功")
        except Exception as e2:
            logger.error(f"❌ 資料庫重新初始化也失敗: {e2}")
    
    # 檢查服務狀態
    if GEMINI_API_KEY:
        logger.info(f"✅ AI 服務已配置 - 模型: {CURRENT_MODEL}")
    else:
        logger.warning("⚠️ AI 服務未配置，請設定 GEMINI_API_KEY 環境變數")
    
    if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
        logger.info("✅ LINE Bot 服務已配置")
    else:
        logger.warning("⚠️ LINE Bot 服務未配置，請設定相關環境變數")
    
    # 優化功能說明
    logger.info("✨ 優化功能特色:")
    logger.info("  - 🎓 優化註冊流程：學號→姓名→確認（三步驟）")
    logger.info("  - 🤖 同步回應處理：訊息→AI→DB→回應（移除快取）")
    logger.info("  - 📊 統計邏輯簡化：只顯示對話數、時間等基本資訊")
    logger.info("  - 🚫 移除快取系統：每次提供個性化回應")
    logger.info("  - 🔧 保留必要功能：AI對話、學生管理、學習建議、匯出")
    
    # 啟動 Flask 應用程式
    logger.info(f"🌐 啟動 Web 服務於 {HOST}:{PORT}")
    logger.info("📚 可用功能:")
    logger.info("  - 🤖 AI 對話系統（150字學術英文回應）")
    logger.info("  - 📱 LINE Bot 整合（優化註冊流程）")
    logger.info("  - 👥 學生管理（簡化版統計）")
    logger.info("  - 📋 學習建議（AI生成個人化建議）")
    logger.info("  - 🔍 系統監控（健康檢查與狀態確認）")
    logger.info("  - 📊 資料匯出（TSV格式對話記錄）")
    
    try:
        app.run(
            host=HOST,
            port=PORT,
            debug=False,  # 生產環境建議設為 False
            threaded=True
        )
    except Exception as e:
        logger.error(f"❌ 應用程式啟動失敗: {e}")
        raise

# =================== 版本說明 ===================

"""
EMI 智能教學助理系統 v4.0 - 優化版
=====================================

🎯 主要優化重點:
- 🎓 註冊流程優化：學號→姓名→確認（三步驟，含驗證）
- 🤖 回應機制改進：同步處理流程，移除快取系統
- 📊 統計功能簡化：專注核心數據，移除複雜計算
- 🔧 程式碼精簡：保留必要功能，提升維護性
- 💾 資料庫優化：完善的註冊狀態追蹤

✨ 新功能特色:
- 三步驟註冊流程：清晰的學號→姓名→確認過程
- 同步回應處理：訊息→AI處理→資料庫記錄→發送回應
- 移除快取系統：確保每次都提供個性化教學回應
- 優化錯誤處理：完善的異常捕獲和用戶友好提示
- 簡化統計顯示：專注於對話數、活動時間等核心指標

🚀 保留核心功能:
- AI 對話系統: 支援 Gemini 2.5 系列模型，150字學術英文回應
- LINE Bot 整合: 完整 Webhook 支援，優化的註冊引導流程
- 學生管理系統: 註冊狀態追蹤、基本統計、學生清單管理
- 學習建議生成: AI個人化建議，基於對話歷史分析
- 系統監控工具: 健康檢查、狀態確認、效能統計
- 資料匯出功能: TSV格式對話記錄，包含註冊狀態

📋 移除/簡化功能:
- 快取系統 → 完全移除，確保回應個性化
- 複雜統計計算 → 簡化為基本對話數和活動時間統計
- 冗長註冊流程 → 優化為清晰的三步驟確認流程
- 複雜圖表和報告 → 簡化為實用的列表和基本統計展示

🔧 技術改進:
- 同步處理架構：避免併發問題，確保資料一致性
- 錯誤處理強化：完善的異常捕獲和日誌記錄
- 資料庫查詢優化：簡化查詢邏輯，提升效能
- 程式碼結構清理：移除冗餘代碼，提升可維護性

📈 預期效益:
- 用戶體驗提升：清晰的註冊流程，穩定的回應機制
- 系統穩定性增強：移除複雜快取邏輯，減少故障點
- 維護成本降低：程式碼簡化，功能聚焦核心需求
- 教學品質改善：個性化AI回應，無快取干擾

🔄 升級路徑:
從 v3.0 → v4.0 的主要變更：
1. 重寫註冊流程處理函數
2. 移除所有快取相關程式碼
3. 優化訊息處理為同步流程
4. 簡化統計和展示邏輯
5. 保留並優化所有核心教學功能

版本日期: 2025年6月29日
優化版本: v4.0
設計理念: 簡潔、穩定、高效、專注教學核心
開發團隊: EMI智能教學助理系統開發組
"""

# =================== 相容性和向後支援 ===================

# 確保與現有 routes.py 和 utils.py 的相容性
try:
    # 嘗試載入 utils.py 中的輔助函數（如果需要）
    from utils import get_system_stats, perform_system_health_check
    logger.info("✅ 成功載入 utils.py 輔助函數")
except ImportError:
    logger.info("ℹ️ utils.py 輔助函數未載入，使用內建功能")
except Exception as e:
    logger.warning(f"⚠️ 載入 utils.py 時發生警告: {e}")

# 向後相容性函數（如果其他模組需要）
def get_cached_response(*args, **kwargs):
    """向後相容性函數 - 快取系統已移除"""
    return None

def cache_response(*args, **kwargs):
    """向後相容性函數 - 快取系統已移除"""
    pass

def cleanup_response_cache():
    """向後相容性函數 - 快取系統已移除"""
    pass

# =================== 模組匯出 ===================

__all__ = [
    # Flask 應用程式
    'app',
    
    # 核心配置
    'CHANNEL_ACCESS_TOKEN', 'CHANNEL_SECRET', 'GEMINI_API_KEY',
    'line_bot_api', 'handler', 'CURRENT_MODEL',
    
    # 註冊和AI函數
    'handle_student_registration',
    'generate_ai_response', 
    'generate_learning_suggestion',
    'get_fallback_suggestion',
    
    # 向後相容性函數
    'get_cached_response', 'cache_response', 'cleanup_response_cache',
    
    # 版本資訊
    '__version__'
]

__version__ = "4.0.0"

# =================== app.py 優化版 - 第5段結束 ===================
# =================== 程式檔案結束 ===================
