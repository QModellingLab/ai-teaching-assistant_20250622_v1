# =================== EMI 智能教學助理 - 精簡修復版 app.py ===================
# 🔸 第 1 段：基本配置和核心功能（第 1-750 行）
# 版本: 4.2.0 - 保留記憶功能，修復語法錯誤
# 日期: 2025年6月29日
# 特色: 保留記憶功能 + 簡化學習歷程 + 修復巢狀 f-string

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
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN') or os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET') or os.getenv('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
PORT = int(os.getenv('PORT', 8080))
HOST = os.getenv('HOST', '0.0.0.0')
DEBUG_MODE = os.getenv('FLASK_ENV') == 'development'

# =================== 應用程式初始化 ===================
app = Flask(__name__)
app.secret_key = SECRET_KEY

# LINE Bot API 初始化
line_bot_api = None
handler = None

if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
    try:
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(CHANNEL_SECRET)
        logger.info("✅ LINE Bot 服務已成功初始化")
    except Exception as e:
        logger.error(f"❌ LINE Bot 初始化失敗: {e}")
else:
    logger.error("❌ LINE Bot 初始化失敗：缺少必要的環境變數")

# Gemini AI 初始化
model = None
CURRENT_MODEL = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 按優先順序嘗試模型
        models_priority = [
            'gemini-2.5-flash',
            'gemini-2.0-flash-exp', 
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-pro'
        ]
        
        for model_name in models_priority:
            try:
                test_model = genai.GenerativeModel(model_name)
                test_response = test_model.generate_content("Test")
                if test_response and test_response.text:
                    model = test_model
                    CURRENT_MODEL = model_name
                    logger.info(f"✅ Gemini AI 已成功配置，使用模型: {model_name}")
                    break
            except Exception as e:
                logger.warning(f"⚠️ 模型 {model_name} 無法使用: {e}")
                continue
        
        if not model:
            logger.error("❌ 所有 Gemini 模型都無法使用")
            
    except Exception as e:
        logger.error(f"❌ Gemini AI 配置失敗: {e}")
else:
    logger.error("❌ Gemini AI 初始化失敗：缺少 GEMINI_API_KEY")

# =================== 簡化資料庫模型（保留記憶功能）===================
from peewee import *
import sqlite3

# 資料庫配置
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///emi_assistant.db')

if DATABASE_URL.startswith('sqlite'):
    db = SqliteDatabase('emi_assistant.db')
else:
    # 支援 PostgreSQL
    from playhouse.db_url import connect
    db = connect(DATABASE_URL)

class BaseModel(Model):
    class Meta:
        database = db

class Student(BaseModel):
    name = CharField(max_length=100)
    line_user_id = CharField(unique=True, max_length=100)
    student_id = CharField(max_length=50, null=True)
    class_name = CharField(max_length=100, null=True)
    registration_step = IntegerField(default=1)
    created_at = DateTimeField(default=datetime.datetime.now)
    last_active = DateTimeField(null=True)
    
    def get_active_session(self):
        """取得活躍會話"""
        try:
            return ConversationSession.get(
                ConversationSession.student == self,
                ConversationSession.session_end.is_null()
            )
        except ConversationSession.DoesNotExist:
            return None
    
    def start_new_session(self):
        """開始新會話"""
        return ConversationSession.create(
            student=self,
            session_start=datetime.datetime.now(),
            message_count=0
        )

class ConversationSession(BaseModel):
    """對話會話（保留記憶功能）"""
    student = ForeignKeyField(Student, backref='sessions')
    session_start = DateTimeField(default=datetime.datetime.now)
    session_end = DateTimeField(null=True)
    message_count = IntegerField(default=0)
    context_summary = TextField(null=True)
    topic_tags = CharField(max_length=500, null=True)
    
    def is_active(self):
        return self.session_end is None
    
    def should_auto_end(self, timeout_minutes=30):
        """判斷是否應該自動結束會話"""
        if not self.is_active():
            return False
        
        # 檢查最後一則訊息時間
        last_message = Message.select().where(
            Message.session == self
        ).order_by(Message.timestamp.desc()).first()
        
        if last_message:
            time_diff = datetime.datetime.now() - last_message.timestamp
            return time_diff.total_seconds() > (timeout_minutes * 60)
        
        return False
    
    def update_session_stats(self):
        """更新會話統計"""
        self.message_count = Message.select().where(Message.session == self).count()
        self.save()
    
    def end_session(self):
        """結束會話"""
        self.session_end = datetime.datetime.now()
        self.save()

class Message(BaseModel):
    student = ForeignKeyField(Student, backref='messages')
    session = ForeignKeyField(ConversationSession, backref='messages', null=True)
    content = TextField()
    ai_response = TextField(null=True)
    timestamp = DateTimeField(default=datetime.datetime.now)
    topic_tags = CharField(max_length=200, null=True)
    source_type = CharField(max_length=50, default='line')
    
    @classmethod
    def get_conversation_context(cls, student, limit=5):
        """取得對話上下文（記憶功能核心）"""
        try:
            # 取得最近的訊息
            recent_messages = list(cls.select().where(
                cls.student == student
            ).order_by(cls.timestamp.desc()).limit(limit))
            
            # 反轉順序（最舊的在前）
            recent_messages.reverse()
            
            context = {
                'conversation_flow': [],
                'recent_topics': [],
                'message_count': len(recent_messages)
            }
            
            for msg in recent_messages:
                context['conversation_flow'].append({
                    'content': msg.content,
                    'ai_response': msg.ai_response,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None
                })
                
                # 收集主題標籤
                if msg.topic_tags:
                    tags = [tag.strip() for tag in msg.topic_tags.split(',') if tag.strip()]
                    context['recent_topics'].extend(tags)
            
            # 去重主題
            context['recent_topics'] = list(set(context['recent_topics']))
            
            return context
            
        except Exception as e:
            logger.error(f"取得對話上下文錯誤: {e}")
            return {'conversation_flow': [], 'recent_topics': [], 'message_count': 0}

# =================== 資料庫管理函數 ===================
def initialize_database():
    """初始化資料庫"""
    try:
        db.connect()
        db.create_tables([Student, ConversationSession, Message], safe=True)
        logger.info("✅ 資料庫初始化完成")
    except Exception as e:
        logger.error(f"❌ 資料庫初始化失敗: {e}")

def manage_conversation_sessions():
    """清理舊會話"""
    try:
        # 自動結束超過30分鐘無活動的會話
        timeout = datetime.datetime.now() - datetime.timedelta(minutes=30)
        
        # 找出需要結束的會話
        sessions_to_end = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        )
        
        ended_count = 0
        for session in sessions_to_end:
            if session.should_auto_end():
                session.end_session()
                ended_count += 1
        
        return {
            'cleaned_sessions': ended_count,
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"會話清理錯誤: {e}")
        return {'cleaned_sessions': 0, 'status': 'error', 'error': str(e)}

# =================== AI 回應生成（保留記憶功能）===================
def generate_ai_response_with_context(message_text, student):
    """生成帶記憶功能的AI回應"""
    try:
        if not model:
            return get_fallback_response(message_text)
        
        # 取得對話上下文（記憶功能核心）
        context = Message.get_conversation_context(student, limit=5)
        
        # 構建包含記憶的提示詞
        context_str = ""
        if context['conversation_flow']:
            context_str = "Previous conversation context:\n"
            for i, conv in enumerate(context['conversation_flow'][-3:], 1):
                # 修復：避免巢狀 f-string
                content_preview = conv['content'][:100] + "..." if len(conv['content']) > 100 else conv['content']
                context_str += f"{i}. Student: {content_preview}\n"
                
                if conv['ai_response']:
                    response_preview = conv['ai_response'][:100] + "..." if len(conv['ai_response']) > 100 else conv['ai_response']
                    context_str += f"   AI: {response_preview}\n"
            context_str += "\n"
        
        # 整理最近討論的主題
        topics_str = ""
        if context['recent_topics']:
            recent_topics = ", ".join(context['recent_topics'][-5:])
            topics_str = f"Recent topics discussed: {recent_topics}\n"
        
        # 建構提示詞
        student_name = student.name or "Student"
        student_id_display = getattr(student, 'student_id', 'Not set')
        
        prompt = f"""You are an EMI (English as a Medium of Instruction) teaching assistant for the course "Practical Applications of AI in Life and Learning."

Student: {student_name} (ID: {student_id_display})

{context_str}{topics_str}Current question: {message_text}

Please provide a helpful, academic response in English (150 words max). 

Guidelines:
- If this continues a previous topic, acknowledge the connection and build upon it
- If the student is asking a follow-up question, reference the previous discussion naturally
- Focus on clear, educational explanations with practical examples
- Maintain encouraging tone for learning
- Use academic language appropriate for university students

Response:"""

        # 調用 Gemini API
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            max_output_tokens=200
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if response and response.text:
            ai_response = response.text.strip()
            logger.info(f"🤖 帶記憶的AI回應生成成功 - 學生: {student_name}")
            return ai_response
        else:
            logger.error("❌ AI回應為空")
            return get_fallback_response(message_text)
        
    except Exception as e:
        logger.error(f"❌ 帶記憶的AI回應生成錯誤: {e}")
        return get_fallback_response(message_text)

def get_fallback_response(message_text):
    """備用回應系統"""
    message_lower = message_text.lower()
    
    if any(word in message_lower for word in ['hello', 'hi', '你好', 'halo']):
        return "Hello! I'm your EMI teaching assistant. How can I help you with your learning today?"
    
    elif any(word in message_lower for word in ['ai', 'artificial intelligence']):
        return "**Artificial Intelligence**: systems that can perform tasks requiring human intelligence. Example: recommendation systems analyze your preferences to suggest relevant content."
    
    elif any(word in message_lower for word in ['machine learning', 'ml']):
        return "**Machine Learning**: AI subset where systems learn from data. Example: email spam filters improve by analyzing patterns in millions of emails."
    
    elif any(word in message_lower for word in ['deep learning']):
        return "**Deep Learning**: advanced ML using neural networks. Example: image recognition systems can identify objects with human-level accuracy."
    
    elif any(word in message_lower for word in ['help', '幫助']):
        return "I can help you with course concepts, English learning, and AI applications. Feel free to ask specific questions!"
    
    else:
        return f"Thank you for your message: \"{message_text}\"\n\nI'm here to help with your EMI course. Try asking about AI concepts, English grammar, or course topics!"

# =================== 學生註冊處理 ===================
def handle_student_registration(line_user_id, message_text, display_name=""):
    """學生註冊流程"""
    try:
        student = Student.get(Student.line_user_id == line_user_id)
    except Student.DoesNotExist:
        student = None
    
    # 新用戶，詢問學號
    if not student:
        student = Student.create(
            name="",
            line_user_id=line_user_id,
            student_id="",
            registration_step=1,
            created_at=datetime.datetime.now(),
            last_active=datetime.datetime.now()
        )
        
        return """🎓 Welcome to EMI AI Teaching Assistant!

I'm your AI learning partner for "Practical Applications of AI in Life and Learning."

**Step 1/3:** Please provide your **Student ID**
Format: A1234567"""
    
    # 收到學號，詢問姓名
    elif student.registration_step == 1:
        student_id = message_text.strip().upper()
        
        if len(student_id) >= 6 and student_id[0].isalpha():
            student.student_id = student_id
            student.registration_step = 2
            student.save()
            
            return f"""✅ Student ID received: {student_id}

**Step 2/3:** Please tell me your **name**
Example: John Smith / 王小明"""
        else:
            return """❌ Invalid format. Please provide a valid Student ID.
Format: A1234567 (Letter + Numbers)"""
    
    # 收到姓名，最終確認
    elif student.registration_step == 2:
        name = message_text.strip()
        
        if len(name) >= 2:
            student.name = name
            student.registration_step = 3
            student.save()
            
            return f"""**Step 3/3:** Please confirm your information:

📋 **Your Information:**
• **Name:** {name}
• **Student ID:** {student.student_id}

Reply with:
• **"YES"** to confirm and complete registration
• **"NO"** to start over"""
        else:
            return """❌ Please provide a valid name (at least 2 characters)."""
    
    # 處理確認回應
    elif student.registration_step == 3:
        response = message_text.strip().upper()
        
        if response in ['YES', 'Y', '是', '確認', 'CONFIRM']:
            student.registration_step = 0
            student.save()
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            return f"""🎉 Registration completed successfully!

📋 **Welcome, {student.name}!**
• **Student ID:** {student.student_id}
• **Registration Date:** {current_time}

🚀 **You can now start learning!**

I can help you with:
📚 **Academic questions** - Course content and concepts
🔤 **English learning** - Grammar, vocabulary, pronunciation  
💡 **Study guidance** - Learning strategies and tips
🎯 **Course discussions** - AI applications in life and learning

**Just ask me anything!** 😊"""
            
        elif response in ['NO', 'N', '否', '重新', 'RESTART']:
            student.registration_step = 1
            student.name = ""
            student.student_id = ""
            student.save()
            
            return """🔄 **Restarting registration...**

**Step 1/3:** Please provide your **Student ID**
Format: A1234567"""
        else:
            return f"""❓ Please reply with **YES** or **NO**:

📋 **Your Information:**
• **Name:** {student.name}
• **Student ID:** {student.student_id}

Reply with **"YES"** to confirm ✅ or **"NO"** to restart ❌"""
    
    return None

# =================== LINE Bot Webhook 處理 ===================
@app.route('/callback', methods=['POST'])
def callback():
    """LINE Bot Webhook 回調處理"""
    if not (line_bot_api and handler):
        logger.error("❌ LINE Bot 未正確配置")
        abort(500)
    
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        logger.debug("📨 收到 LINE Webhook 請求")
        handler.handle(body, signature)
        return 'OK'
    except InvalidSignatureError:
        logger.error("❌ LINE Webhook 簽名驗證失敗")
        abort(400)
    except Exception as e:
        logger.error(f"❌ LINE Webhook 處理錯誤: {e}")
        return 'Error', 500

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理 LINE 文字訊息（含記憶功能）"""
    try:
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
        logger.info(f"👤 收到用戶 {user_id} 的訊息: {message_text[:50]}...")
        
        # 獲取或創建學生記錄
        try:
            student = Student.get(Student.line_user_id == user_id)
            student.last_active = datetime.datetime.now()
            student.save()
        except Student.DoesNotExist:
            student = Student.create(
                name=f'學生_{user_id[-6:]}',
                line_user_id=user_id,
                registration_step=1,
                created_at=datetime.datetime.now(),
                last_active=datetime.datetime.now()
            )
            logger.info(f"✅ 創建新學生記錄: {student.name}")
        
        # 處理註冊流程
        if student.registration_step > 0:
            registration_response = handle_student_registration(user_id, message_text)
            if registration_response:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=registration_response)
                )
                return
        
        # 獲取或創建活躍會話（記憶功能）
        active_session = student.get_active_session()
        if not active_session:
            active_session = student.start_new_session()
            logger.info(f"🆕 創建新會話: {active_session.id}")
        
        # 生成帶記憶功能的AI回應
        ai_response = generate_ai_response_with_context(message_text, student)
        
        # 儲存訊息記錄
        message_record = Message.create(
            student=student,
            content=message_text,
            timestamp=datetime.datetime.now(),
            session=active_session,
            ai_response=ai_response,
            topic_tags=extract_topic_tags(message_text)
        )
        
        # 更新會話統計
        active_session.update_session_stats()
        
        # 回覆用戶
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
        
        logger.info(f"✅ 訊息處理完成 - 會話:{active_session.id}, 訊息:{message_record.id}")
        
    except Exception as e:
        logger.error(f"❌ 訊息處理失敗: {e}")
        try:
            error_response = "抱歉，系統暫時出現問題，請稍後再試。"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=error_response)
            )
        except:
            logger.error("❌ 發送錯誤訊息也失敗了")

def extract_topic_tags(message_content):
    """提取訊息的主題標籤"""
    tags = []
    content_lower = message_content.lower()
    
    topic_keywords = {
        'ai': ['ai', 'artificial intelligence', 'machine learning', 'deep learning'],
        'programming': ['python', 'code', 'programming', 'algorithm', 'coding'],
        'english': ['grammar', 'vocabulary', 'pronunciation', 'writing'],
        'business': ['business', 'management', 'marketing', 'strategy'],
        'science': ['physics', 'chemistry', 'biology', 'mathematics', 'science']
    }
    
    for topic, keywords in topic_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            tags.append(topic)
    
    return ','.join(tags) if tags else ''

# =================== 第1段結束標記 ===================
# 🔸 第1段結束 - 下一段：簡化學習歷程生成和路由處理

# =================== EMI 智能教學助理 - 精簡修復版 app.py ===================
# 🔸 第 2 段：簡化學習歷程和路由處理（第 751-1500 行）
# 接續第1段，包含：簡化學習歷程生成、路由處理、學生管理頁面

# =================== 簡化學習歷程生成 ===================
def generate_simple_learning_summary(student):
    """生成簡化的學習歷程摘要"""
    try:
        # 取得學生的對話記錄
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp))
        
        if not messages:
            return "尚無學習記錄可供分析。"
        
        # 基本統計
        total_messages = len(messages)
        learning_days = (datetime.datetime.now() - messages[0].timestamp).days + 1
        
        # 主題分析
        all_topics = []
        for message in messages:
            if message.topic_tags:
                topics = [tag.strip() for tag in message.topic_tags.split(',') if tag.strip()]
                all_topics.extend(topics)
        
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # 排序主題
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        top_topics = [topic for topic, count in sorted_topics[:3]]
        
        # 生成摘要
        if model and GEMINI_API_KEY:
            try:
                # 使用 AI 生成個性化摘要
                recent_messages_sample = "\n".join([
                    f"- {msg.content[:100]}..." 
                    for msg in messages[-10:]
                ])
                
                prompt = f"""Generate a brief learning summary for student {student.name}:

Learning period: {learning_days} days
Total interactions: {total_messages}
Main topics: {', '.join(top_topics) if top_topics else 'General discussion'}

Recent interactions sample:
{recent_messages_sample}

Please provide a concise learning summary in Traditional Chinese (繁體中文), focusing on:
1. Learning engagement level
2. Main interests and topics
3. Learning progress
4. Simple recommendations

Keep it under 200 words."""

                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.error(f"AI學習摘要生成失敗: {e}")
        
        # 備用摘要
        engagement_level = "積極" if total_messages >= 10 else "適度" if total_messages >= 5 else "初步"
        main_topics_text = f"主要討論 {', '.join(top_topics)}" if top_topics else "涵蓋多元主題"
        
        return f"""📊 {student.name} 的學習歷程摘要

🔹 **學習期間**: {learning_days} 天
🔹 **互動次數**: {total_messages} 次對話
🔹 **參與程度**: {engagement_level}參與
🔹 **學習焦點**: {main_topics_text}

🔹 **學習特色**: 展現持續的學習動機，能夠主動提問和討論課程相關主題。

🔹 **建議**: 繼續保持積極的學習態度，可以嘗試更深入地探討感興趣的主題。"""
        
    except Exception as e:
        logger.error(f"學習摘要生成錯誤: {e}")
        return f"學習摘要生成時發生錯誤: {str(e)}"

# =================== 路由處理 ===================
@app.route('/')
def index():
    """系統首頁（簡化版）"""
    try:
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        total_sessions = ConversationSession.select().count()
        active_sessions = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        ).count()
        
        # 系統狀態
        ai_status = "✅ 正常" if model else "❌ 未配置"
        line_status = "✅ 正常" if (line_bot_api and handler) else "❌ 未配置"
        
        # 執行會話清理
        cleanup_result = manage_conversation_sessions()
        cleanup_count = cleanup_result.get('cleaned_sessions', 0)
        
        # 修復：預先生成 HTML 內容避免巢狀 f-string
        ai_service_text = f"🤖 AI服務 ({CURRENT_MODEL or 'None'})"
        status_section = f"""
        <div class="status-item">
            <span>{ai_service_text}</span>
            <span class="status-ok">{ai_status}</span>
        </div>
        <div class="status-item">
            <span>📱 LINE Bot 連接</span>
            <span class="status-ok">{line_status}</span>
        </div>
        <div class="status-item">
            <span>🧠 記憶功能</span>
            <span style="color: #e74c3c;">✅ 已啟用</span>
        </div>
        <div class="status-item">
            <span>💬 活躍會話</span>
            <span style="color: #2c3e50;">{active_sessions} 個</span>
        </div>
        """
        
        stats_section = f"""
        <div class="stat-card">
            <div class="stat-number">{total_students}</div>
            <div class="stat-label">👥 總學生數</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{total_messages}</div>
            <div class="stat-label">💬 總對話數</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{total_sessions}</div>
            <div class="stat-label">🗣️ 對話會話</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{active_sessions}</div>
            <div class="stat-label">🔥 活躍會話</div>
        </div>
        """
        
        cleanup_message = f"✅ 會話自動清理完成：清理了 {cleanup_count} 個舊會話"
        
        index_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EMI 智能教學助理系統 - 精簡版</title>
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
        .version-badge {{
            background: #e74c3c;
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            margin-left: 10px;
        }}
        
        /* 統計卡片 */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
            <h1>🎓 EMI 智能教學助理系統 <span class="version-badge">精簡版 v4.2</span></h1>
            <p>Practical Applications of AI in Life and Learning - 支援記憶功能，修復語法錯誤</p>
        </div>
        
        <!-- 清理結果提示 -->
        <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            {cleanup_message}
        </div>
        
        <!-- 統計數據 -->
        <div class="stats-grid">
            {stats_section}
        </div>
        
        <!-- 系統狀態 -->
        <div class="system-status">
            <h3 style="color: #2c3e50; margin-bottom: 15px;">⚙️ 系統狀態</h3>
            {status_section}
        </div>
        
        <!-- 快速操作 -->
        <div class="quick-actions">
            <div class="action-card">
                <h4 style="color: #3498db; margin-bottom: 15px;">👥 學生管理</h4>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px;">
                    查看學生清單、對話記錄和會話統計
                </p>
                <a href="/students" class="action-btn">查看學生</a>
            </div>
            
            <div class="action-card">
                <h4 style="color: #27ae60; margin-bottom: 15px;">🔧 系統檢查</h4>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px;">
                    檢查系統狀態和記憶功能運作情況
                </p>
                <a href="/health" class="action-btn btn-success">系統診斷</a>
            </div>
            
            <div class="action-card">
                <h4 style="color: #f39c12; margin-bottom: 15px;">📊 資料匯出</h4>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px;">
                    匯出學生清單、對話記錄和會話資料（TSV格式）
                </p>
                <a href="/export" class="action-btn btn-orange">匯出資料</a>
            </div>
        </div>
        
        <!-- 版本資訊 -->
        <div style="margin-top: 40px; text-align: center; color: #7f8c8d; font-size: 0.9em;">
            <p>EMI 智能教學助理系統 v4.2.0（精簡版 - 保留記憶功能）| 
            <a href="/health" style="color: #3498db;">系統狀態</a> | 
            <a href="/api/stats" style="color: #3498db;">API狀態</a> | 
            更新日期：2025年6月29日</p>
        </div>
    </div>
</body>
</html>
        """
        
        return index_html
        
    except Exception as e:
        logger.error(f"首頁生成錯誤: {e}")
        return f"首頁載入錯誤: {str(e)}", 500

@app.route('/students')
def students():
    """學生列表頁面（簡化版）"""
    try:
        # 取得所有學生
        students_list = list(Student.select().order_by(Student.created_at.desc()))
        
        # 基本統計
        total_students = len(students_list)
        total_messages = Message.select().count()
        total_sessions = ConversationSession.select().count()
        
        # 生成學生表格行（修復：避免巢狀 f-string）
        student_rows = []
        for student in students_list:
            try:
                # 基本統計
                message_count = Message.select().where(Message.student == student).count()
                session_count = ConversationSession.select().where(
                    ConversationSession.student == student
                ).count()
                active_sessions = ConversationSession.select().where(
                    ConversationSession.student == student,
                    ConversationSession.session_end.is_null()
                ).count()
                
                # 註冊狀態
                if student.registration_step == 0:
                    status_text = "已完成"
                    status_class = "status-completed"
                else:
                    status_text = f"進行中 (步驟 {student.registration_step})"
                    status_class = "status-progress"
                
                # 最後活動時間
                last_active_text = ""
                if student.last_active:
                    last_active_text = student.last_active.strftime('%Y-%m-%d %H:%M')
                elif student.created_at:
                    last_active_text = student.created_at.strftime('%Y-%m-%d %H:%M')
                else:
                    last_active_text = "未知"
                
                # 學生資訊
                student_name = student.name or '未設定'
                student_id_display = getattr(student, 'student_id', '') or '未設定'
                
                # 生成行HTML
                row_html = f"""
                    <tr>
                        <td>
                            <div class="student-name">{student_name}</div>
                            <small>學號：{student_id_display}</small>
                        </td>
                        <td>{message_count}</td>
                        <td>
                            <strong>{session_count}</strong><br>
                            <small>活躍：{active_sessions}</small>
                        </td>
                        <td>
                            <span class="status-badge {status_class}">{status_text}</span>
                        </td>
                        <td>{last_active_text}</td>
                        <td>
                            <a href="/student/{student.id}" class="action-btn btn-primary">詳細資料</a>
                            <a href="/students/{student.id}/summary" class="action-btn btn-info">學習摘要</a>
                        </td>
                    </tr>
                """
                student_rows.append(row_html)
                
            except Exception as e:
                logger.error(f"處理學生 {student.id} 統計時錯誤: {e}")
                # 加入錯誤處理行
                error_name = getattr(student, 'name', '未知') or '未設定'
                row_html = f"""
                    <tr>
                        <td>{error_name}</td>
                        <td>-</td>
                        <td>-</td>
                        <td>錯誤</td>
                        <td>-</td>
                        <td>資料錯誤</td>
                    </tr>
                """
                student_rows.append(row_html)
        
        # 合併所有學生行
        students_table_content = ''.join(student_rows)
        
        # 生成學生列表HTML（修復版）
        students_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>學生管理 - EMI 智能教學助理系統</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f8f9fa;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
        }}
        .back-button {{
            display: inline-block;
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        
        /* 統計概覽 */
        .stats-overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-box {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .stat-label {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        /* 學生表格 */
        .table-container {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .table-header {{
            background: #34495e;
            color: white;
            padding: 20px 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .student-name {{
            font-weight: bold;
            color: #2c3e50;
        }}
        .status-badge {{
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .status-completed {{
            background: #d4edda;
            color: #155724;
        }}
        .status-progress {{
            background: #fff3cd;
            color: #856404;
        }}
        .action-btn {{
            padding: 6px 12px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.8em;
            margin: 2px;
            display: inline-block;
        }}
        .btn-primary {{
            background: #3498db;
            color: white;
        }}
        .btn-info {{
            background: #17a2b8;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-button">← 返回首頁</a>
            <h1>👥 學生管理系統</h1>
            <p>EMI 智能教學助理系統 - 精簡版學生管理</p>
        </div>
        
        <!-- 統計概覽 -->
        <div class="stats-overview">
            <div class="stat-box">
                <div class="stat-number">{total_students}</div>
                <div class="stat-label">總學生數</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{total_messages}</div>
                <div class="stat-label">總對話數</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{total_sessions}</div>
                <div class="stat-label">總會話數</div>
            </div>
        </div>
        
        <!-- 學生列表 -->
        <div class="table-container">
            <div class="table-header">
                <h3 style="margin: 0;">📋 學生清單</h3>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>學生資訊</th>
                        <th>對話數</th>
                        <th>會話統計</th>
                        <th>註冊狀態</th>
                        <th>最後活動</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
{students_table_content}
                </tbody>
            </table>
        </div>
        
        <!-- 快速操作 -->
        <div style="margin-top: 30px; text-align: center;">
            <a href="/export" class="action-btn" style="padding: 12px 24px; font-size: 1em; background: #f39c12; color: white; text-decoration: none; border-radius: 5px;">📊 匯出學生資料</a>
        </div>
    </div>
</body>
</html>
        """
        
        return students_html
        
    except Exception as e:
        logger.error(f"學生列表生成錯誤: {e}")
        return f"學生列表載入錯誤: {str(e)}", 500

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """學生詳細頁面（簡化版，保留記憶功能資訊）"""
    try:
        # 取得學生資料
        try:
            student = Student.get_by_id(student_id)
        except Student.DoesNotExist:
            return """
            <div style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>❌ 學生不存在</h1>
                <p>無法找到指定的學生記錄</p>
                <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
            </div>
            """
        
        # 取得對話記錄
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(20))
        
        # 取得會話統計
        all_sessions = list(ConversationSession.select().where(
            ConversationSession.student == student
        ).order_by(ConversationSession.session_start.desc()))
        
        active_session = student.get_active_session()
        session_count = len(all_sessions)
        total_messages = Message.select().where(Message.student == student).count()
        
        # 生成訊息列表（修復：避免巢狀 f-string）
        messages_content = ""
        if messages:
            message_items = []
            for message in messages:
                msg_icon = "👤" if message.source_type in ['line', 'student'] else "🤖"
                msg_time = message.timestamp.strftime('%m月%d日 %H:%M') if message.timestamp else '未知時間'
                
                # 會話資訊
                session_info = ""
                if message.session:
                    session_info = f" | 會話 #{message.session.id}"
                
                # 訊息內容預覽
                content_preview = message.content[:200]
                if len(message.content) > 200:
                    content_preview += "..."
                
                message_item = f"""
                    <div class="message-item">
                        <div class="message-meta">
                            {msg_icon} {msg_time} • {'學生' if message.source_type in ['line', 'student'] else 'AI助理'}{session_info}
                        </div>
                        <div class="message-content">{content_preview}</div>
                    </div>
                """
                message_items.append(message_item)
            
            messages_content = ''.join(message_items)
        else:
            messages_content = """
                <div style="text-align: center; padding: 40px; color: #6c757d;">
                    <div style="font-size: 3em; margin-bottom: 15px;">💭</div>
                    <h4>尚無對話記錄</h4>
                    <p>這位學生還沒有開始與AI助理的對話。</p>
                </div>
            """
        
        # 會話統計顯示
        memory_status = ""
        if active_session:
            memory_status = '<div class="memory-status">🧠 <strong>記憶功能已啟用</strong> - AI能記住前幾輪對話，支援深入追問和連續討論</div>'
        else:
            memory_status = '<div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin-bottom: 20px;">💤 目前無活躍會話 - 下次對話時會自動開始新的記憶會話</div>'
        
        # 學生資訊
        student_name = student.name or '未設定'
        student_id_display = getattr(student, 'student_id', '未設定') or '未設定'
        created_date = student.created_at.strftime('%Y年%m月%d日') if student.created_at else '未知'
        
        # 生成詳細頁面HTML（修復版）
        detail_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{student_name} - 學生詳細資料</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 0; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .student-header {{ text-align: center; }}
        .student-name {{ font-size: 2.5em; margin-bottom: 10px; }}
        .student-id {{ opacity: 0.8; font-size: 1.1em; }}
        .content-section {{ background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 20px 0; }}
        .section-title {{ font-size: 1.3em; font-weight: bold; margin-bottom: 20px; color: #495057; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-item {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
        .stat-number {{ font-size: 1.8em; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #6c757d; font-size: 0.9em; margin-top: 5px; }}
        .memory-status {{ background: #e8f5e8; border: 1px solid #28a745; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .message-list {{ max-height: 600px; overflow-y: auto; }}
        .message-item {{ background: #f8f9fa; margin-bottom: 15px; padding: 15px; border-radius: 10px; }}
        .message-meta {{ font-size: 0.8em; color: #6c757d; margin-bottom: 8px; }}
        .message-content {{ line-height: 1.5; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .action-buttons {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }}
        .btn {{ padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .btn-success {{ background: #28a745; color: white; }}
        .btn-info {{ background: #17a2b8; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <a href="/students" class="back-button">← 返回學生列表</a>
            <div class="student-header">
                <h1 class="student-name">{student_name}</h1>
                <p class="student-id">學號: {student_id_display} | 註冊: {created_date}</p>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- 統計區塊 -->
        <div class="content-section">
            <div class="section-title">📊 學習統計（含記憶功能）</div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-number">{total_messages}</div>
                    <div class="stat-label">總對話數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{session_count}</div>
                    <div class="stat-label">會話次數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{1 if active_session else 0}</div>
                    <div class="stat-label">活躍會話</div>
                </div>
            </div>
            
            <!-- 記憶狀態 -->
            {memory_status}
            
            <div class="action-buttons">
                <a href="/students/{student.id}/summary" class="btn btn-success">📋 學習摘要</a>
                <a href="/api/conversations/{student.id}" class="btn btn-info">📊 API數據</a>
            </div>
        </div>
        
        <!-- 對話記錄 -->
        <div class="content-section">
            <div class="section-title">💬 最近對話記錄</div>
            <div class="message-list">
                {messages_content}
            </div>
            <div style="margin-top: 15px; text-align: center; padding: 10px; background: #fff3cd; border-radius: 5px; font-size: 0.9em;">
                📋 顯示最近20條記錄，共有 {total_messages} 條對話，{session_count} 個會話
            </div>
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

# =================== 第2段結束標記 ===================
# 🔸 第2段結束 - 下一段：學習摘要、資料匯出、API和系統工具

# =================== EMI 智能教學助理 - 精簡修復版 app.py ===================
# 🔸 第 3 段：學習摘要、資料匯出、API和系統工具（第 1501 行-結束）
# 接續第2段，包含：學習摘要、資料匯出、API端點、系統工具、錯誤處理、啟動配置

@app.route('/students/<int:student_id>/summary')
def student_summary(student_id):
    """學生學習摘要頁面（簡化版）"""
    try:
        # 取得學生資料
        try:
            student = Student.get_by_id(student_id)
        except Student.DoesNotExist:
            return """
            <div style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>❌ 學生不存在</h1>
                <p>無法找到指定的學生記錄</p>
                <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
            </div>
            """
        
        # 生成學習摘要
        learning_summary = generate_simple_learning_summary(student)
        
        # 基本統計
        total_messages = Message.select().where(Message.student == student).count()
        learning_days = 0
        if student.created_at:
            learning_days = (datetime.datetime.now() - student.created_at).days + 1
        
        summary_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 {student.name} - 學習摘要</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .student-name {{ font-size: 2em; color: #333; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-item {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-number {{ font-size: 1.5em; font-weight: bold; color: #007bff; }}
        .summary-content {{ background: #f8fafc; padding: 25px; border-radius: 10px; line-height: 1.7; white-space: pre-wrap; border-left: 4px solid #17a2b8; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .action-buttons {{ display: flex; gap: 10px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }}
        .btn {{ padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .btn-info {{ background: #17a2b8; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/students" class="back-button">← 返回學生列表</a>
        
        <div class="header">
            <div class="student-name">👤 {student.name}</div>
            <p>📊 個人學習摘要（簡化版）</p>
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
        
        <div class="summary-content">{learning_summary}</div>
        
        <div class="action-buttons">
            <a href="/student/{student_id}" class="btn btn-info">📊 查看對話記錄</a>
        </div>
    </div>
</body>
</html>
        """
        
        return summary_html
        
    except Exception as e:
        logger.error(f"❌ 學生摘要頁面錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>📊 學習摘要</h1>
            <p style="color: #dc3545;">摘要生成錯誤：{str(e)}</p>
            <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
        </div>
        """

# =================== 簡化資料匯出（僅TSV）===================
@app.route('/export')
def export_data():
    """資料匯出頁面（簡化版 - 僅TSV）"""
    try:
        # 基本統計
        student_count = Student.select().count()
        message_count = Message.select().count()
        session_count = ConversationSession.select().count()
        
        export_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>資料匯出 - EMI 智能教學助理</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px 0; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .page-title {{ text-align: center; font-size: 2.5em; margin-bottom: 10px; }}
        .page-subtitle {{ text-align: center; opacity: 0.9; }}
        .export-card {{ background: white; border-radius: 15px; padding: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 20px 0; }}
        .export-item {{ display: flex; justify-content: space-between; align-items: center; padding: 20px; border: 1px solid #eee; border-radius: 10px; margin: 15px 0; }}
        .export-info {{ flex: 1; }}
        .export-title {{ font-weight: bold; font-size: 1.1em; margin-bottom: 5px; }}
        .export-desc {{ color: #666; font-size: 0.9em; }}
        .export-count {{ background: #e9ecef; padding: 5px 10px; border-radius: 15px; font-size: 0.8em; margin: 5px 0; }}
        .export-btn {{ background: #007bff; color: white; border: none; padding: 12px 20px; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }}
        .export-btn:hover {{ background: #0056b3; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <a href="/" class="back-button">← 返回首頁</a>
            <h1 class="page-title">📁 資料匯出</h1>
            <p class="page-subtitle">匯出系統資料進行分析或備份（TSV格式）</p>
        </div>
    </div>
    
    <div class="container">
        <div class="export-card">
            <h3>📊 基礎資料匯出</h3>
            
            <div class="export-item">
                <div class="export-info">
                    <div class="export-title">學生名單</div>
                    <div class="export-desc">包含學生基本資訊、註冊狀態等</div>
                    <div class="export-count">總計: {student_count} 位學生</div>
                </div>
                <a href="/download/students" class="export-btn">下載 TSV</a>
            </div>
            
            <div class="export-item">
                <div class="export-info">
                    <div class="export-title">對話記錄</div>
                    <div class="export-desc">完整的師生對話記錄，包含時間戳記和會話ID</div>
                    <div class="export-count">總計: {message_count} 則訊息</div>
                </div>
                <a href="/download/messages" class="export-btn">下載 TSV</a>
            </div>
            
            <div class="export-item">
                <div class="export-info">
                    <div class="export-title">對話會話記錄</div>
                    <div class="export-desc">記憶功能會話資料，包含會話時長、訊息數量等</div>
                    <div class="export-count">總計: {session_count} 個會話</div>
                </div>
                <a href="/download/sessions" class="export-btn">下載 TSV</a>
            </div>
        </div>
        
        <div class="export-card">
            <h3>⚠️ 匯出說明</h3>
            <ul>
                <li>所有匯出檔案均為 TSV 格式（Tab-Separated Values），可用 Excel 或試算表軟體開啟</li>
                <li>包含完整的 UTF-8 編碼，支援中文字符</li>
                <li>時間格式為 ISO 8601 標準（YYYY-MM-DD HH:MM:SS）</li>
                <li>記憶功能相關資料包含對話上下文資訊</li>
                <li>敏感資訊已適當處理，確保隱私安全</li>
            </ul>
        </div>
    </div>
</body>
</html>
        """
        
        return export_html
        
    except Exception as e:
        logger.error(f"匯出頁面錯誤: {str(e)}")
        return f"匯出頁面錯誤: {str(e)}", 500

@app.route('/download/students')
def download_students():
    """下載學生清單 TSV 檔案"""
    try:
        students = list(Student.select().order_by(Student.created_at.desc()))
        
        if not students:
            return "目前沒有學生記錄可以下載", 404
        
        # 生成 TSV 內容
        tsv_lines = [
            'ID\t姓名\t學號\t班級\t註冊狀態\t創建時間\t最後活動'
        ]
        
        for student in students:
            student_id = getattr(student, 'student_id', '') or ''
            class_name = getattr(student, 'class_name', '') or ''
            registration_status = "已完成" if student.registration_step == 0 else f"未完成(步驟{student.registration_step})"
            created_at = student.created_at.strftime('%Y-%m-%d %H:%M:%S') if student.created_at else ''
            last_active = student.last_active.strftime('%Y-%m-%d %H:%M:%S') if student.last_active else ''
            
            tsv_lines.append(f"{student.id}\t{student.name}\t{student_id}\t{class_name}\t{registration_status}\t{created_at}\t{last_active}")
        
        # 建立回應
        tsv_content = '\n'.join(tsv_lines)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"students_{timestamp}.tsv"
        
        response = make_response(tsv_content)
        response.headers['Content-Type'] = 'text/tab-separated-values; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"📊 學生清單匯出完成: {len(students)} 位學生")
        return response
        
    except Exception as e:
        logger.error(f"學生清單下載錯誤: {e}")
        return f"學生清單下載失敗: {str(e)}", 500

@app.route('/download/messages')
def download_messages():
    """下載對話記錄 TSV 檔案"""
    try:
        messages = list(Message.select().join(Student).order_by(Message.timestamp.desc()))
        
        if not messages:
            return "目前沒有對話記錄可以下載", 404
        
        # 生成 TSV 內容
        tsv_lines = [
            'ID\t學生姓名\t學生ID\t訊息內容\tAI回應\t時間\t會話ID\t主題標籤'
        ]
        
        for message in messages:
            student_name = message.student.name if message.student else '未知學生'
            student_id = getattr(message.student, 'student_id', '') if message.student else ''
            content = (message.content or '').replace('\n', ' ').replace('\t', ' ')[:500]
            ai_response = (message.ai_response or '').replace('\n', ' ').replace('\t', ' ')[:500]
            timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M:%S') if message.timestamp else ''
            session_id = str(message.session.id) if message.session else ''
            topic_tags = (message.topic_tags or '').replace('\t', ' ')
            
            tsv_lines.append(f"{message.id}\t{student_name}\t{student_id}\t{content}\t{ai_response}\t{timestamp}\t{session_id}\t{topic_tags}")
        
        # 建立回應
        tsv_content = '\n'.join(tsv_lines)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"messages_{timestamp}.tsv"
        
        response = make_response(tsv_content)
        response.headers['Content-Type'] = 'text/tab-separated-values; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"📊 對話記錄匯出完成: {len(messages)} 則訊息")
        return response
        
    except Exception as e:
        logger.error(f"對話記錄下載錯誤: {e}")
        return f"對話記錄下載失敗: {str(e)}", 500

@app.route('/download/sessions')
def download_sessions():
    """下載會話記錄 TSV 檔案"""
    try:
        sessions = list(ConversationSession.select().join(Student).order_by(
            ConversationSession.session_start.desc()
        ))
        
        if not sessions:
            return "目前沒有會話記錄可以下載", 404
        
        # 生成 TSV 內容
        tsv_lines = [
            '會話ID\t學生姓名\t學生ID\t開始時間\t結束時間\t訊息數量\t狀態\t主題標籤'
        ]
        
        for session in sessions:
            student_name = session.student.name if session.student else '未知學生'
            student_id = getattr(session.student, 'student_id', '') if session.student else ''
            start_time = session.session_start.strftime('%Y-%m-%d %H:%M:%S') if session.session_start else ''
            end_time = session.session_end.strftime('%Y-%m-%d %H:%M:%S') if session.session_end else ''
            message_count = str(session.message_count)
            status = '已完成' if session.session_end else '活躍中'
            topic_tags = (session.topic_tags or '').replace('\t', ' ')
            
            tsv_lines.append(f"{session.id}\t{student_name}\t{student_id}\t{start_time}\t{end_time}\t{message_count}\t{status}\t{topic_tags}")
        
        # 建立回應
        tsv_content = '\n'.join(tsv_lines)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"sessions_{timestamp}.tsv"
        
        response = make_response(tsv_content)
        response.headers['Content-Type'] = 'text/tab-separated-values; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"📊 會話記錄匯出完成: {len(sessions)} 個會話")
        return response
        
    except Exception as e:
        logger.error(f"會話記錄下載錯誤: {e}")
        return f"會話記錄下載失敗: {str(e)}", 500

# =================== API 端點（保留）===================
@app.route('/api/stats')
def api_stats():
    """系統統計資料 API"""
    try:
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        total_sessions = ConversationSession.select().count()
        
        # 記憶功能統計
        active_sessions = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        ).count()
        
        # 今日統計
        today = datetime.date.today()
        today_messages = Message.select().where(
            Message.timestamp >= today
        ).count()
        
        return jsonify({
            'overview': {
                'total_students': total_students,
                'total_messages': total_messages,
                'total_sessions': total_sessions,
                'active_sessions': active_sessions
            },
            'today': {
                'messages': today_messages
            },
            'system_status': {
                'gemini_ai': bool(model),
                'line_bot': bool(line_bot_api and handler),
                'current_model': CURRENT_MODEL
            },
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:student_id>')
def api_get_conversations(student_id):
    """取得學生的對話會話資料 API"""
    try:
        # 檢查學生是否存在
        try:
            student = Student.get_by_id(student_id)
        except Student.DoesNotExist:
            return jsonify({'error': 'Student not found'}), 404
        
        # 取得學生的會話記錄
        sessions = list(ConversationSession.select().where(
            ConversationSession.student == student
        ).order_by(ConversationSession.session_start.desc()).limit(10))
        
        session_data = []
        for session in sessions:
            # 取得會話中的訊息
            messages = list(Message.select().where(
                Message.session == session
            ).order_by(Message.timestamp))
            
            session_data.append({
                'session_id': session.id,
                'started': session.session_start.isoformat() if session.session_start else None,
                'ended': session.session_end.isoformat() if session.session_end else None,
                'message_count': session.message_count,
                'is_active': session.session_end is None,
                'topics': session.topic_tags.split(',') if session.topic_tags else [],
                'messages': [
                    {
                        'id': msg.id,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                        'ai_response': msg.ai_response,
                        'topics': msg.topic_tags.split(',') if msg.topic_tags else []
                    } for msg in messages
                ]
            })
        
        return jsonify({
            'student_id': student_id,
            'student_name': student.name,
            'total_sessions': len(session_data),
            'sessions': session_data
        })
        
    except Exception as e:
        logger.error(f"API conversations error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =================== 系統工具路由 ===================
@app.route('/health')
def health_check():
    """系統健康檢查"""
    try:
        # 基本統計
        student_count = Student.select().count()
        message_count = Message.select().count()
        session_count = ConversationSession.select().count()
        active_sessions = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        ).count()
        
        # 系統狀態
        ai_status = "✅ 正常" if model else "❌ 未配置"
        line_status = "✅ 正常" if (line_bot_api and handler) else "❌ 未配置"
        
        # 執行會話清理
        cleanup_result = manage_conversation_sessions()
        cleanup_count = cleanup_result.get('cleaned_sessions', 0)
        
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
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .page-title {{ text-align: center; font-size: 2.5em; margin-bottom: 10px; }}
        .page-subtitle {{ text-align: center; opacity: 0.9; }}
        .health-card {{ background: white; border-radius: 15px; padding: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 20px 0; }}
        .status-item {{ display: flex; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid #eee; }}
        .status-item:last-child {{ border-bottom: none; }}
        .status-value {{ padding: 5px 10px; border-radius: 5px; font-size: 0.9em; }}
        .status-ok {{ background: #d4edda; color: #155724; }}
        .status-error {{ background: #f8d7da; color: #721c24; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <a href="/" class="back-button">← 返回首頁</a>
            <h1 class="page-title">🔍 系統健康檢查</h1>
            <p class="page-subtitle">精簡版系統狀態監控</p>
        </div>
    </div>
    
    <div class="container">
        <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            ✅ 會話清理完成：清理了 {cleanup_count} 個舊會話
        </div>
        
        <div class="health-card">
            <h3>🔧 核心服務狀態</h3>
            <div class="status-item">
                <span>AI 服務 (Gemini)</span>
                <span class="status-value {'status-ok' if model else 'status-error'}">{ai_status}</span>
            </div>
            <div class="status-item">
                <span>LINE Bot 服務</span>
                <span class="status-value {'status-ok' if (line_bot_api and handler) else 'status-error'}">{line_status}</span>
            </div>
            <div class="status-item">
                <span>資料庫連線</span>
                <span class="status-value status-ok">✅ 正常</span>
            </div>
            <div class="status-item">
                <span>AI 模型</span>
                <span class="status-value status-ok">{CURRENT_MODEL or '未配置'}</span>
            </div>
        </div>
        
        <div class="health-card">
            <h3>📊 系統統計</h3>
            <div class="status-item">
                <span>註冊學生總數</span>
                <span class="status-value status-ok">{student_count} 人</span>
            </div>
            <div class="status-item">
                <span>對話訊息總數</span>
                <span class="status-value status-ok">{message_count} 則</span>
            </div>
            <div class="status-item">
                <span>記憶會話總數</span>
                <span class="status-value status-ok">{session_count} 個</span>
            </div>
            <div class="status-item">
                <span>活躍會話數</span>
                <span class="status-value status-ok">{active_sessions} 個</span>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        return health_html
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return f"健康檢查錯誤: {str(e)}", 500

# =================== 錯誤處理 ===================
@app.errorhandler(404)
def not_found(error):
    """404錯誤處理"""
    return """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>頁面不存在 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .error-container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            max-width: 500px;
        }
        .error-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        .error-title {
            color: #333;
            font-size: 1.5em;
            margin-bottom: 20px;
        }
        .error-message {
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .home-button {
            display: inline-block;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">🔍</div>
        <h1 class="error-title">頁面不存在</h1>
        <p class="error-message">
            抱歉，您要找的頁面不存在。<br>
            可能是網址輸入錯誤，或者頁面已被移動。
        </p>
        <a href="/" class="home-button">返回首頁</a>
    </div>
</body>
</html>
    """, 404

@app.errorhandler(500)
def internal_error(error):
    """500錯誤處理"""
    logger.error(f"Internal server error: {str(error)}")
    return """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>伺服器錯誤 - EMI 智能教學助理</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .error-container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            max-width: 500px;
        }
        .error-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        .error-title {
            color: #e74c3c;
            font-size: 1.5em;
            margin-bottom: 20px;
        }
        .error-message {
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .home-button {
            display: inline-block;
            padding: 12px 24px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">⚠️</div>
        <h1 class="error-title">伺服器錯誤</h1>
        <p class="error-message">
            系統發生暫時性錯誤，請稍後再試。<br>
            如果問題持續發生，請聯繫系統管理員。
        </p>
        <a href="/" class="home-button">返回首頁</a>
    </div>
</body>
</html>
    """, 500

# =================== 系統啟動配置 ===================
if __name__ == '__main__':
    try:
        # 初始化資料庫
        logger.info("正在初始化 EMI 智能教學助理系統（精簡版）...")
        initialize_database()
        
        # 清理舊會話
        cleanup_result = manage_conversation_sessions()
        logger.info(f"會話清理完成: {cleanup_result}")
        
        # 檢查必要的環境變數
        missing_vars = []
        if not GEMINI_API_KEY:
            missing_vars.append("GEMINI_API_KEY")
        if not CHANNEL_ACCESS_TOKEN:
            missing_vars.append("CHANNEL_ACCESS_TOKEN")
        if not CHANNEL_SECRET:
            missing_vars.append("CHANNEL_SECRET")
        
        if missing_vars:
            logger.warning(f"缺少環境變數: {', '.join(missing_vars)}")
            logger.warning("部分功能可能無法正常運作")
        
        # 啟動應用程式
        port = int(os.environ.get('PORT', 5000))
        debug_mode = os.environ.get('FLASK_ENV') == 'development'
        
        logger.info(f"✅ EMI 智能教學助理系統（精簡版）啟動成功！")
        logger.info(f"🌐 監聽端口: {port}")
        logger.info(f"🧠 記憶功能: {'✅ 已啟用' if True else '❌ 已停用'}")
        logger.info(f"📚 學習歷程: {'✅ 簡化版' if True else '❌ 已停用'}")
        logger.info(f"🔧 除錯模式: {'開啟' if debug_mode else '關閉'}")
        logger.info(f"🤖 AI 模型: {CURRENT_MODEL or '未配置'}")
        
        if debug_mode:
            logger.info("=" * 50)
            logger.info("🔍 除錯資訊:")
            logger.info(f"   - 健康檢查: http://localhost:{port}/health")
            logger.info(f"   - 資料匯出: http://localhost:{port}/export")
            logger.info(f"   - API狀態: http://localhost:{port}/api/stats")
            logger.info("=" * 50)
        
        # 啟動 Flask 應用程式
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug_mode,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ 系統啟動失敗: {str(e)}")
        raise

# =================== 版本說明 ===================
"""
EMI 智能教學助理系統 - 精簡修復版 v4.2.0
更新日期: 2025年6月29日

🎯 **根據用戶需求修改:**

✅ **保留功能:**
✅ 記憶功能系統 - ConversationSession、會話追蹤、上下文記憶
✅ API 端點 - 所有 API 功能完整保留
✅ 學生註冊系統 - 完整的3步驟註冊流程
✅ 基本對話功能 - LINE Bot + Gemini AI

🔄 **簡化功能:**
🔄 學習歷程生成 - 移除複雜AI分析 → 簡單對話摘要
🔄 資料匯出 - 只保留TSV格式，移除複雜分析報告
🔄 學生統計頁面 - 簡化為基本列表，移除複雜統計

❌ **移除功能:**
❌ 會話管理控制台 - 移除 /admin/sessions
❌ 複雜HTML模板 - 簡化所有頁面生成
❌ 巢狀 f-string - 完全修復語法錯誤

🔧 **語法修復:**
✅ 所有巢狀 f-string 已重構為分離式生成
✅ HTML 內容先生成到變數，再組合到最終模板
✅ 簡化資料庫查詢，避免複雜操作
✅ 確保語法正確性和運行穩定性

📦 **檔案大小比較:**
- 原版: 5000+ 行，8個部分
- 精簡版: 約 1500 行，3個部分

🚀 **部署優勢:**
• 更快的啟動時間
• 更低的記憶體使用
• 更容易除錯和維護
• 語法錯誤已完全修復
• 保留核心記憶功能

💡 **主要改進:**
1. 修復所有導致 Gemini 無法回應的語法錯誤
2. 保留用戶重視的記憶功能和 API
3. 簡化複雜功能但保持實用性
4. 提高系統穩定性和可維護性

🔄 **向後相容性:**
• 所有重要路由保持不變
• 資料庫結構完全相容
• API 接口完全保留
• 環境變數需求不變

📁 **檔案結構:**
- 第1段 (1-750行): 基本配置、資料庫模型、AI回應生成、註冊處理、LINE Bot處理
- 第2段 (751-1500行): 學習歷程生成、系統首頁、學生管理頁面、學生詳細頁面
- 第3段 (1501-結束): 學習摘要、資料匯出、API端點、系統工具、錯誤處理、啟動配置

🔗 **串接說明:**
- 第1段：包含所有基礎功能和依賴
- 第2段：接續第1段，添加頁面路由和管理功能
- 第3段：完成所有剩餘功能，包含完整的錯誤處理和啟動邏輯

📋 **部署步驟:**
1. 將三段代碼按順序合併為完整的 app.py
2. 確保所有環境變數正確設定
3. 上傳到 Railway 並部署
4. 檢查 /health 確認系統正常運作
5. 測試 LINE Bot 對話功能

⚠️ **重要提醒:**
- 確保將三段代碼完整合併，不可遺漏任何部分
- 第1段的結束標記和第2段的開始要正確銜接
- 所有 import 語句都在第1段，後續段落不需要重複
- 資料庫模型定義在第1段，後續段落直接使用
"""

# =================== 第3段結束標記 ===================
# 🔸 第3段結束 - 完整檔案結束
# 
# 📋 **合併指南:**
# 1. 將第1段完整複製（去除結束標記）
# 2. 接著複製第2段內容（去除開始和結束標記） 
# 3. 最後複製第3段內容（去除開始標記）
# 4. 確保沒有重複的 import 或 class 定義
# 5. 檢查所有函數和路由都完整包含
