#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =================== EMI 智能教學助理 - Railway 修復版 app.py ===================
# 第 1 段：基本配置和核心功能（第 1-650 行）
# 版本: 4.2.2 - Railway 部署修復版 (移除 emoji)
# 日期: 2025年6月30日
# 特色: 保留記憶功能 + 強制資料庫初始化 + 修復語法錯誤 + 移除 emoji

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

# 記錄環境變數狀態
logger.info("檢查環境變數...")
for var_name, var_value in [
    ('CHANNEL_ACCESS_TOKEN', CHANNEL_ACCESS_TOKEN),
    ('CHANNEL_SECRET', CHANNEL_SECRET), 
    ('GEMINI_API_KEY', GEMINI_API_KEY),
    ('DATABASE_URL', os.getenv('DATABASE_URL'))
]:
    if var_value:
        logger.info(f"[OK] {var_name}: 已設定")
    else:
        logger.warning(f"[WARNING] {var_name}: 未設定")

# =================== 應用程式初始化 ===================
app = Flask(__name__)
app.secret_key = SECRET_KEY

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
    
    @classmethod
    def get_by_id(cls, student_id):
        """修復版的 get_by_id 方法"""
        try:
            return cls.select().where(cls.id == student_id).get()
        except cls.DoesNotExist:
            logger.warning(f"找不到 ID: {student_id} 的學生")
            return None
        except Exception as e:
            logger.error(f"[ERROR] 取得學生失敗: {e}")
            return None

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

# =================== Railway 修復：強制資料庫初始化 ===================
DATABASE_INITIALIZED = False

try:
    logger.info("[INIT] Railway 部署 - 強制執行資料庫初始化...")
    
    # 連接並初始化資料庫
    if db.is_closed():
        db.connect()
    
    # 強制創建表格
    db.create_tables([Student, ConversationSession, Message], safe=True)
    logger.info("[OK] Railway 資料庫初始化成功")
    
    # 檢查表格是否存在的函數
    def check_table_exists(model_class):
        try:
            model_class.select().count()
            return True
        except Exception:
            return False
    
    # 驗證所有表格
    tables_status = {
        'students': check_table_exists(Student),
        'sessions': check_table_exists(ConversationSession),
        'messages': check_table_exists(Message)
    }
    
    if all(tables_status.values()):
        logger.info("[OK] 所有資料表已確認存在")
        DATABASE_INITIALIZED = True
    else:
        logger.error(f"[ERROR] 部分資料表創建失敗: {tables_status}")
        DATABASE_INITIALIZED = False
        
except Exception as init_error:
    logger.error(f"[ERROR] Railway 資料庫初始化失敗: {init_error}")
    DATABASE_INITIALIZED = False

# =================== 資料庫管理函數 ===================
def initialize_database():
    """初始化資料庫"""
    try:
        if db.is_closed():
            db.connect()
        db.create_tables([Student, ConversationSession, Message], safe=True)
        logger.info("[OK] 資料庫初始化完成")
        return True
    except Exception as e:
        logger.error(f"[ERROR] 資料庫初始化失敗: {e}")
        return False

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

def check_database_ready():
    """檢查資料庫是否就緒"""
    try:
        # 嘗試執行簡單查詢
        Student.select().count()
        return True
    except Exception as e:
        logger.error(f"資料庫未就緒: {e}")
        return False

# =================== LINE Bot API 初始化 ===================
line_bot_api = None
handler = None

if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
    try:
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(CHANNEL_SECRET)
        logger.info("[OK] LINE Bot 服務已成功初始化")
    except Exception as e:
        logger.error(f"[ERROR] LINE Bot 初始化失敗: {e}")
else:
    logger.error("[ERROR] LINE Bot 初始化失敗：缺少必要的環境變數")

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
                    logger.info(f"[OK] Gemini AI 已成功配置，使用模型: {model_name}")
                    break
            except Exception as e:
                logger.warning(f"[WARNING] 模型 {model_name} 無法使用: {e}")
                continue
        
        if not model:
            logger.error("[ERROR] 所有 Gemini 模型都無法使用")
            
    except Exception as e:
        logger.error(f"[ERROR] Gemini AI 配置失敗: {e}")
else:
    logger.error("[ERROR] Gemini AI 初始化失敗：缺少 GEMINI_API_KEY")

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
            logger.info(f"[AI] 帶記憶的AI回應生成成功 - 學生: {student_name}")
            return ai_response
        else:
            logger.error("[ERROR] AI回應為空")
            return get_fallback_response(message_text)
        
    except Exception as e:
        logger.error(f"[ERROR] 帶記憶的AI回應生成錯誤: {e}")
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
        
        return """Welcome to EMI AI Teaching Assistant!

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
            
            return f"""[OK] Student ID received: {student_id}

**Step 2/3:** Please tell me your **name**
Example: John Smith / 王小明"""
        else:
            return """[ERROR] Invalid format. Please provide a valid Student ID.
Format: A1234567 (Letter + Numbers)"""
    
    # 收到姓名，最終確認
    elif student.registration_step == 2:
        name = message_text.strip()
        
        if len(name) >= 2:
            student.name = name
            student.registration_step = 3
            student.save()
            
            return f"""**Step 3/3:** Please confirm your information:

**Your Information:**
• **Name:** {name}
• **Student ID:** {student.student_id}

Reply with:
• **"YES"** to confirm and complete registration
• **"NO"** to start over"""
        else:
            return """[ERROR] Please provide a valid name (at least 2 characters)."""
    
    # 處理確認回應
    elif student.registration_step == 3:
        response = message_text.strip().upper()
        
        if response in ['YES', 'Y', '是', '確認', 'CONFIRM']:
            student.registration_step = 0
            student.save()
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            return f"""[SUCCESS] Registration completed successfully!

**Welcome, {student.name}!**
• **Student ID:** {student.student_id}
• **Registration Date:** {current_time}

**You can now start learning!**

I can help you with:
**Academic questions** - Course content and concepts
**English learning** - Grammar, vocabulary, pronunciation  
**Study guidance** - Learning strategies and tips
**Course discussions** - AI applications in life and learning

**Just ask me anything!**"""
            
        elif response in ['NO', 'N', '否', '重新', 'RESTART']:
            student.registration_step = 1
            student.name = ""
            student.student_id = ""
            student.save()
            
            return """**Restarting registration...**

**Step 1/3:** Please provide your **Student ID**
Format: A1234567"""
        else:
            return f"""Please reply with **YES** or **NO**:

**Your Information:**
• **Name:** {student.name}
• **Student ID:** {student.student_id}

Reply with **"YES"** to confirm or **"NO"** to restart"""
    
    return None

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
# 第1段結束 - 包含：基本配置、資料庫模型、強制初始化、AI服務、註冊處理
# 下一段將包含：LINE Bot 處理、路由、學生管理頁面

# =================== EMI 智能教學助理 - Railway 修復版 app.py ===================
# 第 2 段：LINE Bot 處理和路由管理（第 651-1300 行）
# 接續第1段，包含：LINE Bot處理、緊急修復路由、系統首頁、學生管理

# =================== Railway 修復：緊急資料庫設置路由 ===================
@app.route('/setup-database-force')
def setup_database_force():
    """緊急資料庫設置（Railway 修復專用）"""
    global DATABASE_INITIALIZED
    
    try:
        logger.info("[EMERGENCY] 執行緊急資料庫設置...")
        
        # 強制重新連接
        if not db.is_closed():
            db.close()
        db.connect()
        
        # 強制創建表格
        db.create_tables([Student, ConversationSession, Message], safe=True)
        
        # 驗證表格存在
        def check_table_exists(model_class):
            try:
                model_class.select().count()
                return True
            except Exception:
                return False
        
        tables_status = {
            'students': check_table_exists(Student),
            'messages': check_table_exists(Message), 
            'sessions': check_table_exists(ConversationSession)
        }
        
        # 基本統計
        try:
            student_count = Student.select().count()
            message_count = Message.select().count()
            session_count = ConversationSession.select().count()
        except Exception as e:
            student_count = f"錯誤: {e}"
            message_count = f"錯誤: {e}"
            session_count = f"錯誤: {e}"
        
        # 更新全域標記
        if all(tables_status.values()):
            DATABASE_INITIALIZED = True
        
        success_message = "[OK] 資料庫修復成功！現在可以正常使用系統了。" if all(tables_status.values()) else "[ERROR] 部分表格仍有問題，請檢查 Railway 資料庫配置。"
        
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>緊急資料庫修復</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background: #f8f9fa; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        .success {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .error {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .info {{ background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Railway 緊急資料庫修復結果</h1>
        
        <h3>表格狀態檢查:</h3>
        <div class="{'success' if tables_status['students'] else 'error'}">
            Students 表格: {'[OK] 存在' if tables_status['students'] else '[ERROR] 不存在'}
        </div>
        <div class="{'success' if tables_status['messages'] else 'error'}">
            Messages 表格: {'[OK] 存在' if tables_status['messages'] else '[ERROR] 不存在'}
        </div>
        <div class="{'success' if tables_status['sessions'] else 'error'}">
            Sessions 表格: {'[OK] 存在' if tables_status['sessions'] else '[ERROR] 不存在'}
        </div>
        
        <h3>資料統計:</h3>
        <div class="info">
            <strong>學生數量:</strong> {student_count}<br>
            <strong>訊息數量:</strong> {message_count}<br>
            <strong>會話數量:</strong> {session_count}
        </div>
        
        <h3>修復狀態:</h3>
        <div class="{'success' if all(tables_status.values()) else 'error'}">
            {success_message}
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="/" class="btn">返回首頁</a>
            <a href="/health" class="btn">健康檢查</a>
            <a href="/students" class="btn">學生管理</a>
        </div>
    </div>
</body>
</html>
        """
        
    except Exception as e:
        logger.error(f"[ERROR] 緊急資料庫設置失敗: {e}")
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>資料庫修復失敗</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background: #f8f9fa; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        .error {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>資料庫修復失敗</h1>
        <div class="error">
            <strong>錯誤詳情:</strong><br>
            {str(e)}
        </div>
        
        <h3>建議解決方案:</h3>
        <ol>
            <li>檢查 Railway 中的 DATABASE_URL 環境變數</li>
            <li>確認 PostgreSQL 服務正在運行</li>
            <li>檢查資料庫連線權限</li>
            <li>聯繫技術支援</li>
        </ol>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="/setup-database-force" class="btn">重試修復</a>
            <a href="/" class="btn">返回首頁</a>
        </div>
    </div>
</body>
</html>
        """

@app.route('/database-status')
def database_status():
    """資料庫狀態檢查頁面"""
    db_ready = check_database_ready()
    
    if not db_ready:
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>資料庫初始化中</title>
    <style>
        body {{ 
            font-family: sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0; 
            padding: 0; 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }}
        .status-card {{ 
            background: white; 
            padding: 40px; 
            border-radius: 15px; 
            text-align: center; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            max-width: 500px; 
        }}
        .spinner {{ 
            border: 4px solid #f3f3f3; 
            border-top: 4px solid #3498db; 
            border-radius: 50%; 
            width: 40px; 
            height: 40px; 
            animation: spin 2s linear infinite; 
            margin: 20px auto; 
        }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .btn {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background: #e74c3c; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px; 
            font-weight: bold; 
            margin: 10px; 
        }}
    </style>
    <script>
        setTimeout(function() {{
            window.location.reload();
        }}, 10000);
    </script>
</head>
<body>
    <div class="status-card">
        <h1>[WARNING] 資料庫初始化中</h1>
        <div class="spinner"></div>
        <p>系統正在初始化資料庫，請稍候...</p>
        <p style="color: #666; font-size: 0.9em;">
            如果此頁面持續顯示超過1分鐘，<br>
            請點擊下方按鈕進行手動修復
        </p>
        
        <div>
            <a href="/setup-database-force" class="btn">手動修復資料庫</a>
            <a href="/" class="btn" style="background: #3498db;">重新檢查</a>
        </div>
        
        <p style="margin-top: 30px; font-size: 0.8em; color: #999;">
            頁面將在10秒後自動重新載入
        </p>
    </div>
</body>
</html>
        """
    else:
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>資料庫就緒</title>
    <style>
        body {{ 
            font-family: sans-serif; 
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            margin: 0; 
            padding: 0; 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }}
        .status-card {{ 
            background: white; 
            padding: 40px; 
            border-radius: 15px; 
            text-align: center; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
        }}
        .btn {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background: #3498db; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px; 
            font-weight: bold; 
            margin: 10px; 
        }}
    </style>
    <script>
        setTimeout(function() {{
            window.location.href = '/';
        }}, 3000);
    </script>
</head>
<body>
    <div class="status-card">
        <h1>[OK] 資料庫就緒</h1>
        <p>資料庫初始化完成！</p>
        <p style="color: #666;">正在跳轉到首頁...</p>
        
        <div>
            <a href="/" class="btn">立即前往首頁</a>
        </div>
        
        <p style="margin-top: 20px; font-size: 0.8em; color: #999;">
            3秒後自動跳轉
        </p>
    </div>
</body>
</html>
        """

# =================== LINE Bot Webhook 處理 ===================
@app.route('/callback', methods=['POST'])
def callback():
    """LINE Bot Webhook 回調處理"""
    if not (line_bot_api and handler):
        logger.error("[ERROR] LINE Bot 未正確配置")
        abort(500)
    
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        logger.debug("[LINE] 收到 LINE Webhook 請求")
        handler.handle(body, signature)
        return 'OK'
    except InvalidSignatureError:
        logger.error("[ERROR] LINE Webhook 簽名驗證失敗")
        abort(400)
    except Exception as e:
        logger.error(f"[ERROR] LINE Webhook 處理錯誤: {e}")
        return 'Error', 500

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理 LINE 文字訊息（含記憶功能）"""
    try:
        # 檢查資料庫是否就緒
        if not DATABASE_INITIALIZED or not check_database_ready():
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="系統正在初始化，請稍後再試。")
            )
            return
        
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
        logger.info(f"[USER] 收到用戶 {user_id} 的訊息: {message_text[:50]}...")
        
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
            logger.info(f"[OK] 創建新學生記錄: {student.name}")
        
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
            logger.info(f"[NEW] 創建新會話: {active_session.id}")
        
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
        
        logger.info(f"[OK] 訊息處理完成 - 會話:{active_session.id}, 訊息:{message_record.id}")
        
    except Exception as e:
        logger.error(f"[ERROR] 訊息處理失敗: {e}")
        try:
            error_response = "抱歉，系統暫時出現問題，請稍後再試。"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=error_response)
            )
        except:
            logger.error("[ERROR] 發送錯誤訊息也失敗了")

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
        
        return f"""{student.name} 的學習歷程摘要

**學習期間**: {learning_days} 天
**互動次數**: {total_messages} 次對話
**參與程度**: {engagement_level}參與
**學習焦點**: {main_topics_text}

**學習特色**: 展現持續的學習動機，能夠主動提問和討論課程相關主題。

**建議**: 繼續保持積極的學習態度，可以嘗試更深入地探討感興趣的主題。"""
        
    except Exception as e:
        logger.error(f"學習摘要生成錯誤: {e}")
        return f"學習摘要生成時發生錯誤: {str(e)}"

# =================== 路由處理（含資料庫檢查）===================
@app.route('/')
def index():
    """系統首頁（含資料庫狀態檢查）"""
    try:
        # 檢查資料庫是否就緒
        if not DATABASE_INITIALIZED or not check_database_ready():
            return """
            <script>
                window.location.href = '/database-status';
            </script>
            """
        
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        total_sessions = ConversationSession.select().count()
        active_sessions = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        ).count()
        
        # 系統狀態
        ai_status = "[OK] 正常" if model else "[ERROR] 未配置"
        line_status = "[OK] 正常" if (line_bot_api and handler) else "[ERROR] 未配置"
        db_status = "[OK] 正常" if DATABASE_INITIALIZED else "[ERROR] 初始化失敗"
        
        # 執行會話清理
        cleanup_result = manage_conversation_sessions()
        cleanup_count = cleanup_result.get('cleaned_sessions', 0)
        
        # 預先生成 HTML 內容避免巢狀 f-string
        ai_service_text = f"AI服務 ({CURRENT_MODEL or 'None'})"
        
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cleanup_message = f"[OK] 會話自動清理完成：清理了 {cleanup_count} 個舊會話"
        
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EMI 智能教學助理系統 - Railway 修復版</title>
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
        .btn-danger {{ background: #e74c3c; }}
        .btn-danger:hover {{ background: #c0392b; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 系統標題 -->
        <div class="header">
            <h1>EMI 智能教學助理系統 <span class="version-badge">Railway 修復版 v4.2.2</span></h1>
            <p>Practical Applications of AI in Life and Learning - Railway 部署修復版</p>
        </div>
        
        <!-- 清理結果提示 -->
        <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            {cleanup_message}
        </div>
        
        <!-- 統計數據 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_students}</div>
                <div class="stat-label">總學生數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_messages}</div>
                <div class="stat-label">總對話數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_sessions}</div>
                <div class="stat-label">對話會話</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{active_sessions}</div>
                <div class="stat-label">活躍會話</div>
            </div>
        </div>
        
        <!-- 系統狀態 -->
        <div class="system-status">
            <h3 style="color: #2c3e50; margin-bottom: 15px;">系統狀態</h3>
            <div class="status-item">
                <span>{ai_service_text}</span>
                <span class="status-ok">{ai_status}</span>
            </div>
            <div class="status-item">
                <span>LINE Bot 連接</span>
                <span class="status-ok">{line_status}</span>
            </div>
            <div class="status-item">
                <span>資料庫狀態</span>
                <span class="status-ok">{db_status}</span>
            </div>
            <div class="status-item">
                <span>記憶功能</span>
                <span style="color: #e74c3c;">[OK] 已啟用</span>
            </div>
            <div class="status-item">
                <span>活躍會話</span>
                <span style="color: #2c3e50;">{active_sessions} 個</span>
            </div>
        </div>
        
        <!-- 快速操作 -->
        <div class="quick-actions">
            <div class="action-card">
                <h4>學生管理</h4>
                <p>查看學生名單、註冊狀態和基本統計</p>
                <a href="/students" class="action-btn">進入管理</a>
            </div>
            
            <div class="action-card">
                <h4>系統檢查</h4>
                <p>詳細的系統健康檢查和狀態報告</p>
                <a href="/health" class="action-btn btn-success">健康檢查</a>
            </div>
            
            <div class="action-card">
                <h4>API 統計</h4>
                <p>查看 API 調用統計和系統效能指標</p>
                <a href="/api/stats" class="action-btn btn-orange">API 統計</a>
            </div>
            
            <div class="action-card">
                <h4>緊急修復</h4>
                <p>如果遇到資料庫問題，可使用緊急修復工具</p>
                <a href="/setup-database-force" class="action-btn btn-danger">修復資料庫</a>
            </div>
        </div>
        
        <!-- 系統資訊 -->
        <div style="margin-top: 40px; padding: 20px; background: #f1f2f6; border-radius: 10px; text-align: center;">
            <h4 style="color: #2f3542; margin-bottom: 15px;">系統資訊</h4>
            <p style="color: #57606f; margin: 5px 0;">
                <strong>版本:</strong> EMI Teaching Assistant v4.2.2 (Railway 修復版)<br>
                <strong>部署環境:</strong> Railway PostgreSQL + Flask<br>
                <strong>記憶功能:</strong> [OK] 已啟用 - 支援上下文記憶和會話管理<br>
                <strong>最後更新:</strong> {current_time}
            </p>
        </div>
    </div>
</body>
</html>
        """
        
    except Exception as e:
        logger.error(f"[ERROR] 首頁載入錯誤: {e}")
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>系統載入錯誤</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background: #f8f9fa; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        .error {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>[ERROR] 系統載入錯誤</h1>
        <div class="error">
            <strong>錯誤詳情:</strong><br>
            {str(e)}
        </div>
        
        <h3>建議解決方案:</h3>
        <ol>
            <li><a href="/database-status">檢查資料庫狀態</a></li>
            <li><a href="/setup-database-force">手動修復資料庫</a></li>
            <li><a href="/health">執行系統健康檢查</a></li>
        </ol>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="/setup-database-force" class="btn">緊急修復</a>
            <a href="/" class="btn" style="background: #28a745;">重新載入</a>
        </div>
    </div>
</body>
</html>
        """

# =================== 第2段結束標記 ===================
# 第2段結束 - 下一段：學生詳細頁面、API端點和系統工具

# =================== EMI 智能教學助理 - Railway 修復版 app.py ===================
# 第 3A 段：學生管理頁面和詳細頁面（第 1301-1625 行）
# 接續第2段，包含：學生管理頁面、學生詳細頁面

@app.route('/students')
def students_list():
    """學生管理頁面（含資料庫檢查）"""
    try:
        # 檢查資料庫是否就緒
        if not DATABASE_INITIALIZED or not check_database_ready():
            return """
            <script>
                window.location.href = '/database-status';
            </script>
            """
        
        # 取得所有學生
        students = list(Student.select().order_by(Student.created_at.desc()))
        
        # 統計資料
        total_students = len(students)
        registered_students = len([s for s in students if s.registration_step == 0])
        pending_students = len([s for s in students if s.registration_step > 0])
        
        # 生成學生列表 HTML
        student_rows = ""
        for student in students:
            # 計算統計
            msg_count = Message.select().where(Message.student == student).count()
            session_count = ConversationSession.select().where(ConversationSession.student == student).count()
            
            # 註冊狀態
            if student.registration_step == 0:
                status_badge = '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;">[OK] 已註冊</span>'
            elif student.registration_step == 1:
                status_badge = '<span style="background: #ffc107; color: #212529; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;">[WAIT] 等待學號</span>'
            elif student.registration_step == 2:
                status_badge = '<span style="background: #17a2b8; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;">[WAIT] 等待姓名</span>'
            elif student.registration_step == 3:
                status_badge = '<span style="background: #6f42c1; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;">[WAIT] 等待確認</span>'
            else:
                status_badge = '<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;">[ERROR] 需重設</span>'
            
            # 最後活動時間
            last_active = student.last_active.strftime('%m/%d %H:%M') if student.last_active else '無'
            
            student_rows += f"""
            <tr>
                <td>{student.id}</td>
                <td><strong>{student.name or '未設定'}</strong></td>
                <td><code>{student.student_id or '未設定'}</code></td>
                <td>{status_badge}</td>
                <td style="text-align: center;">{msg_count}</td>
                <td style="text-align: center;">{session_count}</td>
                <td>{last_active}</td>
                <td>
                    <a href="/student/{student.id}" style="background: #007bff; color: white; padding: 5px 10px; border-radius: 3px; text-decoration: none; font-size: 0.8em;">
                        詳細
                    </a>
                </td>
            </tr>
            """
        
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>學生管理 - EMI 智能教學助理</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }}
        .stats-row {{
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
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            margin: 5px;
        }}
        .btn-primary {{ background: #007bff; color: white; }}
        .btn-success {{ background: #28a745; color: white; }}
        .btn-secondary {{ background: #6c757d; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="color: #2c3e50; margin: 0;">學生管理</h1>
            <div>
                <a href="/" class="btn btn-secondary">返回首頁</a>
                <a href="/students/export" class="btn btn-success">匯出清單</a>
            </div>
        </div>
        
        <!-- 統計摘要 -->
        <div class="stats-row">
            <div class="stat-box">
                <div class="stat-number">{total_students}</div>
                <div class="stat-label">總學生數</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{registered_students}</div>
                <div class="stat-label">[OK] 已完成註冊</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{pending_students}</div>
                <div class="stat-label">[WAIT] 註冊進行中</div>
            </div>
        </div>
        
        <!-- 學生列表 -->
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>姓名</th>
                    <th>學號</th>
                    <th>註冊狀態</th>
                    <th>訊息數</th>
                    <th>會話數</th>
                    <th>最後活動</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {student_rows or '<tr><td colspan="8" style="text-align: center; color: #999; padding: 40px;">尚無學生資料</td></tr>'}
            </tbody>
        </table>
        
        <!-- 操作說明 -->
        <div style="margin-top: 30px; padding: 20px; background: #e3f2fd; border-radius: 10px;">
            <h4 style="color: #1976d2; margin-bottom: 10px;">學生管理說明</h4>
            <ul style="color: #1565c0; margin: 0;">
                <li><strong>註冊流程:</strong> 學生透過 LINE Bot 自動完成三步驟註冊（學號 → 姓名 → 確認）</li>
                <li><strong>活動追蹤:</strong> 系統自動記錄學生的對話次數、會話數量和最後活動時間</li>
                <li><strong>詳細資訊:</strong> 點擊「詳細」可查看個別學生的完整學習歷程和對話記錄</li>
                <li><strong>資料匯出:</strong> 可將學生清單匯出為 TSV 格式，方便進一步分析</li>
            </ul>
        </div>
    </div>
</body>
</html>
        """
        
    except Exception as e:
        logger.error(f"[ERROR] 學生列表載入錯誤: {e}")
        return f"""
        <h1>[ERROR] 載入錯誤</h1>
        <p>學生列表載入時發生錯誤: {str(e)}</p>
        <a href="/">返回首頁</a>
        """

# =================== 學生詳細頁面 ===================
@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """學生詳細頁面"""
    try:
        # 檢查資料庫是否就緒
        if not DATABASE_INITIALIZED or not check_database_ready():
            return redirect('/database-status')
        
        # 查詢學生
        try:
            student = Student.get_by_id(student_id)
            if not student:
                return "學生不存在", 404
        except Student.DoesNotExist:
            return "學生不存在", 404
        
        # 獲取學生統計
        total_messages = Message.select().where(Message.student == student).count()
        total_sessions = ConversationSession.select().where(ConversationSession.student == student).count()
        active_session = student.get_active_session()
        
        # 獲取最近的對話
        recent_messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(10))
        
        # 格式化時間
        last_active_str = student.last_active.strftime('%Y-%m-%d %H:%M:%S') if student.last_active else '從未活躍'
        created_str = student.created_at.strftime('%Y-%m-%d %H:%M:%S') if student.created_at else '未知'
        
        # 生成對話記錄 HTML
        messages_html = ""
        for msg in recent_messages:
            timestamp_str = msg.timestamp.strftime('%m-%d %H:%M') if msg.timestamp else '未知'
            messages_html += f"""
            <div class="message-item">
                <div class="message-header">
                    <span class="message-time">{timestamp_str}</span>
                    <span class="message-type">[學生]</span>
                </div>
                <div class="message-content">{msg.content}</div>
                
                <div class="message-header" style="margin-top: 10px;">
                    <span class="message-time">{timestamp_str}</span>
                    <span class="message-type ai">[AI]</span>
                </div>
                <div class="message-content ai">{msg.ai_response or '無回應'}</div>
            </div>
            """
        
        if not messages_html:
            messages_html = '<div class="no-messages">尚無對話記錄</div>'
        
        # 狀態標籤
        status_text = '[ACTIVE] 活躍' if active_session else '[IDLE] 休息'
        status_class = 'active' if active_session else ''
        
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{student.name} - 學生詳細資料</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f8f9fa;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .back-btn {{
            background: #6c757d;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            margin-bottom: 20px;
            display: inline-block;
        }}
        .student-header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .student-header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .student-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .info-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .info-card h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 10px;
        }}
        .info-item {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding: 5px 0;
        }}
        .info-label {{
            font-weight: bold;
            color: #7f8c8d;
        }}
        .info-value {{
            color: #2c3e50;
        }}
        .status-badge {{
            background: #3498db;
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
        }}
        .active {{
            background: #27ae60;
        }}
        .messages-section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .message-item {{
            border-bottom: 1px solid #ecf0f1;
            padding: 15px 0;
            margin-bottom: 15px;
        }}
        .message-item:last-child {{
            border-bottom: none;
            margin-bottom: 0;
        }}
        .message-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .message-time {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .message-type {{
            background: #3498db;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }}
        .message-type.ai {{
            background: #e74c3c;
        }}
        .message-content {{
            background: #f8f9fa;
            padding: 10px 15px;
            border-radius: 8px;
            margin-left: 20px;
            line-height: 1.4;
        }}
        .message-content.ai {{
            background: #fdf2f2;
            border-left: 3px solid #e74c3c;
        }}
        .no-messages {{
            text-align: center;
            color: #7f8c8d;
            padding: 40px;
            font-style: italic;
        }}
        .action-buttons {{
            text-align: center;
            margin-top: 30px;
        }}
        .btn {{
            background: #3498db;
            color: white;
            padding: 12px 24px;
            border-radius: 5px;
            text-decoration: none;
            margin: 5px;
            display: inline-block;
            transition: background 0.3s ease;
        }}
        .btn:hover {{
            background: #2980b9;
        }}
        .btn-success {{
            background: #27ae60;
        }}
        .btn-success:hover {{
            background: #219a52;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/students" class="back-btn">← 返回學生列表</a>
        
        <div class="student-header">
            <h1>{student.name} <span class="status-badge {status_class}">{status_text}</span></h1>
            <p style="color: #7f8c8d;">學生詳細資料和對話記錄</p>
        </div>
        
        <div class="student-info">
            <div class="info-card">
                <h3>基本資料</h3>
                <div class="info-item">
                    <span class="info-label">學生 ID:</span>
                    <span class="info-value">{student.id}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">姓名:</span>
                    <span class="info-value">{student.name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">學號:</span>
                    <span class="info-value">{student.student_id or '未設定'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">LINE ID:</span>
                    <span class="info-value">{student.line_user_id[-12:]}...</span>
                </div>
                <div class="info-item">
                    <span class="info-label">註冊步驟:</span>
                    <span class="info-value">{'已完成' if student.registration_step == 0 else f'步驟 {student.registration_step}'}</span>
                </div>
            </div>
            
            <div class="info-card">
                <h3>活動統計</h3>
                <div class="info-item">
                    <span class="info-label">對話次數:</span>
                    <span class="info-value">{total_messages}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">會話次數:</span>
                    <span class="info-value">{total_sessions}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">活躍會話:</span>
                    <span class="info-value">{'有' if active_session else '無'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">註冊時間:</span>
                    <span class="info-value">{created_str}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">最後活躍:</span>
                    <span class="info-value">{last_active_str}</span>
                </div>
            </div>
        </div>
        
        <div class="messages-section">
            <h3 style="color: #2c3e50; margin-bottom: 20px;">最近對話記錄 (最新 10 筆)</h3>
            {messages_html}
        </div>
        
        <div class="action-buttons">
            <a href="/api/learning-summary/{student.id}" class="btn btn-success">檢視完整學習歷程</a>
            <a href="/api/student/{student.id}/conversations" class="btn">API 對話記錄</a>
        </div>
    </div>
</body>
</html>
        """
        
    except Exception as e:
        logger.error(f"[ERROR] 學生詳細頁面錯誤: {e}")
        return f"""
        <div style="text-align: center; margin: 50px;">
            <h2>[ERROR] 學生詳細資料載入失敗</h2>
            <p>錯誤: {str(e)}</p>
            <a href="/students" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">返回學生列表</a>
        </div>
        """

# =================== 第3A段結束標記 ===================
# 第3A段結束 - 包含：學生管理頁面、學生詳細頁面
# 下一段：資料匯出功能、API端點

# =================== EMI 智能教學助理 - Railway 修復版 app.py ===================
# 第 3B 段：資料匯出和API端點（第 1626-1950 行）
# 接續第3A段，包含：資料匯出功能、API端點、強制初始化

# =================== 資料匯出功能 ===================
@app.route('/export/tsv')
def export_tsv():
    """匯出學生對話資料為 TSV 格式"""
    try:
        # 檢查資料庫是否就緒
        if not DATABASE_INITIALIZED or not check_database_ready():
            return "資料庫未就緒，請稍後再試", 500
        
        # 查詢所有對話資料
        messages = Message.select(
            Message.id,
            Message.content,
            Message.ai_response,
            Message.timestamp,
            Message.topic_tags,
            Student.name,
            Student.line_user_id,
            ConversationSession.id.alias('session_id')
        ).join(Student).join(ConversationSession, join_type='LEFT').order_by(Message.timestamp)
        
        # 生成 TSV 內容
        tsv_lines = []
        tsv_lines.append("訊息ID\t學生姓名\tLINE用戶ID\t會話ID\t學生訊息\tAI回應\t時間戳記\t主題標籤")
        
        for message in messages:
            line_user_id_short = message.student.line_user_id[-8:] if message.student.line_user_id else "N/A"
            session_id = message.session.id if message.session else "N/A"
            timestamp_str = message.timestamp.strftime('%Y-%m-%d %H:%M:%S') if message.timestamp else "N/A"
            
            # 清理文字中的換行符和製表符
            student_msg = (message.content or "").replace('\n', ' ').replace('\t', ' ')
            ai_response = (message.ai_response or "").replace('\n', ' ').replace('\t', ' ')
            topic_tags = (message.topic_tags or "").replace('\n', ' ').replace('\t', ' ')
            
            tsv_lines.append(f"{message.id}\t{message.student.name}\t{line_user_id_short}\t{session_id}\t{student_msg}\t{ai_response}\t{timestamp_str}\t{topic_tags}")
        
        tsv_content = '\n'.join(tsv_lines)
        
        # 設置檔案下載回應
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"emi_conversations_{timestamp}.tsv"
        
        response = make_response(tsv_content)
        response.headers['Content-Type'] = 'text/tab-separated-values; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = len(tsv_content.encode('utf-8'))
        
        logger.info(f"[OK] TSV 匯出成功: {filename}, 包含 {len(tsv_lines)-1} 筆對話記錄")
        return response
        
    except Exception as e:
        logger.error(f"[ERROR] TSV 匯出失敗: {e}")
        return f"匯出失敗: {str(e)}", 500

@app.route('/students/export')
def export_students():
    """匯出學生清單為 TSV"""
    try:
        # 檢查資料庫是否就緒
        if not DATABASE_INITIALIZED or not check_database_ready():
            return "資料庫未就緒，請稍後再試", 500
        
        # 查詢所有學生資料
        students = Student.select().order_by(Student.created_at.desc())
        
        # 生成 TSV 內容
        tsv_lines = []
        tsv_lines.append("學生ID\t姓名\t學號\tLINE用戶ID\t註冊步驟\t對話數\t會話數\t創建時間\t最後活躍時間")
        
        for student in students:
            # 計算統計
            msg_count = Message.select().where(Message.student == student).count()
            session_count = ConversationSession.select().where(ConversationSession.student == student).count()
            
            # 格式化時間
            created_str = student.created_at.strftime('%Y-%m-%d %H:%M:%S') if student.created_at else "N/A"
            last_active_str = student.last_active.strftime('%Y-%m-%d %H:%M:%S') if student.last_active else "N/A"
            
            # 註冊狀態
            registration_status = "已完成" if student.registration_step == 0 else f"步驟{student.registration_step}"
            
            # LINE ID 簡化顯示
            line_id_short = student.line_user_id[-12:] if student.line_user_id else "N/A"
            
            tsv_lines.append(f"{student.id}\t{student.name}\t{student.student_id or 'N/A'}\t{line_id_short}\t{registration_status}\t{msg_count}\t{session_count}\t{created_str}\t{last_active_str}")
        
        tsv_content = '\n'.join(tsv_lines)
        
        # 設置檔案下載回應
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"emi_students_{timestamp}.tsv"
        
        response = make_response(tsv_content)
        response.headers['Content-Type'] = 'text/tab-separated-values; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = len(tsv_content.encode('utf-8'))
        
        logger.info(f"[OK] 學生清單匯出成功: {filename}, 包含 {len(tsv_lines)-1} 筆學生記錄")
        return response
        
    except Exception as e:
        logger.error(f"[ERROR] 學生清單匯出失敗: {e}")
        return f"匯出失敗: {str(e)}", 500

# =================== API 端點 ===================
@app.route('/api/student/<int:student_id>/conversations')
def get_student_conversations(student_id):
    """取得特定學生的對話記錄 API"""
    try:
        # 檢查資料庫是否就緒
        if not DATABASE_INITIALIZED or not check_database_ready():
            return jsonify({"error": "資料庫未就緒"}), 500
        
        # 查詢學生
        try:
            student = Student.get_by_id(student_id)
        except Student.DoesNotExist:
            return jsonify({"error": "學生不存在"}), 404
        
        # 查詢對話記錄
        messages = Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(50)
        
        conversations = []
        for message in messages:
            conversations.append({
                "id": message.id,
                "content": message.content,
                "ai_response": message.ai_response,
                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                "topic_tags": message.topic_tags,
                "session_id": message.session.id if message.session else None
            })
        
        return jsonify({
            "student": {
                "id": student.id,
                "name": student.name,
                "line_user_id": student.line_user_id[-8:] + "..." if student.line_user_id else None
            },
            "conversations": conversations,
            "total_count": len(conversations)
        })
        
    except Exception as e:
        logger.error(f"[ERROR] 學生對話記錄 API 錯誤: {e}")
        return jsonify({"error": f"API 錯誤: {str(e)}"}), 500

@app.route('/api/learning-summary/<int:student_id>')
def get_learning_summary(student_id):
    """取得學生學習摘要 API"""
    try:
        # 檢查資料庫是否就緒
        if not DATABASE_INITIALIZED or not check_database_ready():
            return "資料庫未就緒，請稍後再試", 500
        
        # 查詢學生
        try:
            student = Student.get_by_id(student_id)
        except Student.DoesNotExist:
            return "學生不存在", 404
        
        # 生成學習摘要
        learning_summary = generate_simple_learning_summary(student)
        
        # 基本統計
        total_messages = Message.select().where(Message.student == student).count()
        total_sessions = ConversationSession.select().where(ConversationSession.student == student).count()
        active_session = student.get_active_session()
        
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{student.name} 的學習歷程</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f8f9fa;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #ecf0f1;
        }}
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .summary-content {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            line-height: 1.6;
            white-space: pre-line;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: #e8f4fd;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 1.8em;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .btn {{
            background: #3498db;
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            display: inline-block;
            margin: 10px 5px;
            transition: background 0.3s ease;
        }}
        .btn:hover {{
            background: #2980b9;
        }}
        .btn-secondary {{
            background: #95a5a6;
        }}
        .btn-secondary:hover {{
            background: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{student.name} 的學習歷程</h1>
            <p style="color: #7f8c8d;">詳細學習分析報告</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total_messages}</div>
                <div class="stat-label">總對話數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_sessions}</div>
                <div class="stat-label">會話次數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{'活躍' if active_session else '休息'}</div>
                <div class="stat-label">目前狀態</div>
            </div>
        </div>
        
        <div class="summary-content">
            {learning_summary}
        </div>
        
        <div style="text-align: center;">
            <a href="/students" class="btn btn-secondary">返回學生管理</a>
            <a href="/api/student/{student.id}/conversations" class="btn">檢視對話記錄</a>
        </div>
    </div>
</body>
</html>
        """
        
    except Exception as e:
        logger.error(f"[ERROR] 學習摘要 API 錯誤: {e}")
        return f"學習摘要載入失敗: {str(e)}", 500

@app.route('/api/stats')
def get_stats():
    """系統統計 API"""
    try:
        # 檢查資料庫是否就緒
        if not DATABASE_INITIALIZED or not check_database_ready():
            return jsonify({"error": "資料庫未就緒"}), 500
        
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        total_sessions = ConversationSession.select().count()
        active_sessions = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        ).count()
        
        # 今日統計
        today = datetime.date.today()
        today_messages = Message.select().where(
            Message.timestamp >= datetime.datetime.combine(today, datetime.time.min)
        ).count()
        
        # 系統狀態
        system_status = {
            "database": "healthy" if DATABASE_INITIALIZED else "error",
            "ai_service": "healthy" if model else "unavailable",
            "line_bot": "healthy" if (line_bot_api and handler) else "unavailable"
        }
        
        return jsonify({
            "students": {
                "total": total_students,
                "registered_today": 0  # 可以之後實作
            },
            "conversations": {
                "total_messages": total_messages,
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "today_messages": today_messages
            },
            "system": system_status,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"[ERROR] 統計 API 錯誤: {e}")
        return jsonify({"error": f"統計資料載入失敗: {str(e)}"}), 500

# =================== 強制資料庫初始化函數 ===================
def force_initialize_database():
    """強制初始化資料庫 - 用於 Gunicorn 環境"""
    global DATABASE_INITIALIZED
    try:
        logger.info("[FORCE INIT] 執行強制資料庫初始化...")
        
        # 重新連接
        if not db.is_closed():
            db.close()
        db.connect()
        
        # 創建表格
        db.create_tables([Student, ConversationSession, Message], safe=True)
        
        # 驗證
        Student.select().count()
        Message.select().count()
        ConversationSession.select().count()
        
        DATABASE_INITIALIZED = True
        logger.info("[OK] 強制資料庫初始化成功")
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] 強制資料庫初始化失敗: {e}")
        DATABASE_INITIALIZED = False
        return False

# =================== 第3B段結束標記 ===================
# 第3B段結束 - 包含：資料匯出功能、API端點、強制初始化
# 下一段：健康檢查、錯誤處理和啟動配置

# =================== EMI 智能教學助理 - Railway 修復版 app.py ===================
# 第 4 段：健康檢查、錯誤處理和啟動配置（第 1951 行 - 結束）
# 接續第3段，包含：健康檢查、錯誤處理、啟動配置

# =================== 健康檢查端點 ===================
@app.route('/health')
def health_check():
    """系統健康檢查"""
    try:
        # 資料庫檢查
        db_status = "healthy"
        db_details = "[OK] 正常"
        try:
            if DATABASE_INITIALIZED and check_database_ready():
                # 測試基本查詢
                student_count = Student.select().count()
                message_count = Message.select().count()
                db_details = f"[OK] 正常 (學生: {student_count}, 訊息: {message_count})"
            else:
                db_status = "error"
                db_details = "[ERROR] 未初始化或連線失敗"
        except Exception as e:
            db_status = "error"
            db_details = f"[ERROR] 錯誤: {str(e)}"
        
        # AI 服務檢查
        ai_status = "healthy" if model and GEMINI_API_KEY else "unavailable"
        ai_details = f"[OK] Gemini {CURRENT_MODEL}" if model else "[ERROR] 未配置或 API 金鑰無效"
        
        # LINE Bot 檢查
        line_status = "healthy" if (line_bot_api and handler) else "unavailable"
        line_details = "[OK] 已連接" if (line_bot_api and handler) else "[ERROR] 未配置或連線失敗"
        
        # 整體健康狀態
        overall_status = "healthy" if all([
            db_status == "healthy",
            ai_status in ["healthy", "unavailable"],  # AI 可以是未配置狀態
            line_status in ["healthy", "unavailable"]  # LINE Bot 可以是未配置狀態
        ]) else "error"
        
        # 記憶功能檢查（基於資料庫表格存在性）
        memory_status = "enabled" if db_status == "healthy" else "disabled"
        memory_details = "[OK] 會話記憶功能已啟用" if memory_status == "enabled" else "[ERROR] 記憶功能無法使用"
        
        # 會話管理檢查
        session_management = "unknown"
        session_details = "檢查中..."
        try:
            if db_status == "healthy":
                active_sessions = ConversationSession.select().where(
                    ConversationSession.session_end.is_null()
                ).count()
                total_sessions = ConversationSession.select().count()
                session_management = "healthy"
                session_details = f"[OK] 正常 (活躍: {active_sessions}, 總計: {total_sessions})"
            else:
                session_management = "error"
                session_details = "[ERROR] 資料庫未就緒"
        except Exception as e:
            session_management = "error"
            session_details = f"[ERROR] 錯誤: {str(e)}"
        
        health_data = {
            "status": overall_status,
            "timestamp": datetime.datetime.now().isoformat(),
            "services": {
                "database": {
                    "status": db_status,
                    "details": db_details
                },
                "ai_service": {
                    "status": ai_status,
                    "details": ai_details
                },
                "line_bot": {
                    "status": line_status,
                    "details": line_details
                },
                "memory_function": {
                    "status": memory_status,
                    "details": memory_details
                },
                "session_management": {
                    "status": session_management,
                    "details": session_details
                }
            }
        }
        
        # HTML 格式的健康檢查頁面
        status_color = {
            "healthy": "#27ae60",
            "error": "#e74c3c", 
            "unavailable": "#f39c12",
            "enabled": "#27ae60",
            "disabled": "#e74c3c"
        }
        
        services_html = ""
        for service_name, service_info in health_data["services"].items():
            service_display_name = {
                "database": "資料庫",
                "ai_service": "AI 服務",
                "line_bot": "LINE Bot",
                "memory_function": "記憶功能",
                "session_management": "會話管理"
            }.get(service_name, service_name)
            
            color = status_color.get(service_info["status"], "#95a5a6")
            
            services_html += f"""
            <div class="service-item">
                <div class="service-header">
                    <span class="service-name">{service_display_name}</span>
                    <span class="status-badge" style="background: {color};">
                        {service_info["status"].upper()}
                    </span>
                </div>
                <div class="service-details">
                    {service_info["details"]}
                </div>
            </div>
            """
        
        overall_color = status_color.get(overall_status, "#95a5a6")
        overall_icon = "[OK]" if overall_status == "healthy" else "[WARNING]" if overall_status == "warning" else "[ERROR]"
        
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系統健康檢查 - EMI 智能教學助理</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f8f9fa;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .overall-status {{
            background: {overall_color};
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .overall-status h2 {{
            margin: 0;
            font-size: 1.5em;
        }}
        
        .services-list {{
            space-y: 15px;
        }}
        .service-item {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
        }}
        .service-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .service-name {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.1em;
        }}
        .status-badge {{
            padding: 4px 12px;
            border-radius: 15px;
            color: white;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .service-details {{
            color: #7f8c8d;
            font-size: 0.9em;
            line-height: 1.4;
        }}
        
        .actions {{
            text-align: center;
            margin-top: 30px;
        }}
        .btn {{
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            margin: 10px;
            transition: background 0.3s ease;
        }}
        .btn:hover {{
            background: #2980b9;
        }}
        .btn-danger {{
            background: #e74c3c;
        }}
        .btn-danger:hover {{
            background: #c0392b;
        }}
        .btn-secondary {{
            background: #95a5a6;
        }}
        .btn-secondary:hover {{
            background: #7f8c8d;
        }}
        
        .timestamp {{
            text-align: center;
            color: #999;
            font-size: 0.9em;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
        }}
        
        .json-section {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            overflow-x: auto;
        }}
    </style>
    <script>
        // 每30秒自動刷新
        setTimeout(function() {{
            window.location.reload();
        }}, 30000);
        
        function showJSON() {{
            document.getElementById('json-data').style.display = 
                document.getElementById('json-data').style.display === 'none' ? 'block' : 'none';
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>系統健康檢查</h1>
            <p>EMI 智能教學助理 - 服務狀態監控</p>
        </div>
        
        <div class="overall-status">
            <h2>{overall_icon} 系統整體狀態: {overall_status.upper()}</h2>
            <p>上次檢查時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="services-list">
            {services_html}
        </div>
        
        <div class="actions">
            <a href="/" class="btn btn-secondary">返回首頁</a>
            <a href="/students" class="btn">學生管理</a>
            <a href="/setup-database-force" class="btn btn-danger">緊急修復</a>
            <button onclick="showJSON()" class="btn" style="background: #8e44ad;">顯示 JSON</button>
        </div>
        
        <div id="json-data" class="json-section" style="display: none;">
            <pre>{json.dumps(health_data, indent=2, ensure_ascii=False)}</pre>
        </div>
        
        <div class="timestamp">
            <p>頁面將在30秒後自動刷新</p>
            <p>系統時區: {os.environ.get('TZ', 'UTC')} | Railway 修復版 v4.2.2</p>
        </div>
    </div>
</body>
</html>
        """
        
    except Exception as e:
        logger.error(f"[ERROR] 健康檢查失敗: {e}")
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>健康檢查失敗</title>
    <style>
        body {{ font-family: sans-serif; text-align: center; margin: 50px; background: #f8f9fa; }}
        .error {{ background: #f8d7da; color: #721c24; padding: 20px; border-radius: 10px; max-width: 600px; margin: 0 auto; }}
        .btn {{ display: inline-block; background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px; }}
    </style>
</head>
<body>
    <div class="error">
        <h1>[ERROR] 健康檢查系統失敗</h1>
        <p><strong>錯誤詳情:</strong><br>{str(e)}</p>
        <a href="/" class="btn">返回首頁</a>
        <a href="/setup-database-force" class="btn" style="background: #dc3545;">緊急修復</a>
    </div>
</body>
</html>
        """, 500

# =================== 錯誤處理 ===================
@app.errorhandler(404)
def not_found_error(error):
    """404 錯誤處理"""
    return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - 頁面不存在</title>
    <style>
        body {{
            font-family: sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .error-container {{
            background: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            max-width: 500px;
        }}
        .error-code {{
            font-size: 4em;
            font-weight: bold;
            color: #e74c3c;
            margin-bottom: 20px;
        }}
        .btn {{
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            margin: 10px;
            transition: background 0.3s ease;
        }}
        .btn:hover {{
            background: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">404</div>
        <h2>[NOT FOUND] 頁面不存在</h2>
        <p>您訪問的頁面不存在或已被移動。</p>
        
        <div>
            <a href="/" class="btn">返回首頁</a>
            <a href="/students" class="btn">學生管理</a>
            <a href="/health" class="btn">健康檢查</a>
        </div>
    </div>
</body>
</html>
    """, 404

@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    logger.error(f"[ERROR] 內部伺服器錯誤: {str(error)}")
    return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>500 - 伺服器錯誤</title>
    <style>
        body {{
            font-family: sans-serif;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .error-container {{
            background: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            max-width: 600px;
        }}
        .error-code {{
            font-size: 4em;
            font-weight: bold;
            color: #e74c3c;
            margin-bottom: 20px;
        }}
        .btn {{
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            margin: 10px;
            transition: background 0.3s ease;
        }}
        .btn:hover {{
            background: #2980b9;
        }}
        .btn-danger {{
            background: #e74c3c;
        }}
        .btn-danger:hover {{
            background: #c0392b;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">500</div>
        <h2>[ERROR] 伺服器內部錯誤</h2>
        <p>系統發生內部錯誤，請稍後再試。</p>
        
        <div>
            <a href="/" class="btn">返回首頁</a>
            <a href="/health" class="btn">健康檢查</a>
            <a href="/setup-database-force" class="btn btn-danger">緊急修復</a>
        </div>
    </div>
</body>
</html>
    """, 500

# =================== 應用程式啟動配置 ===================
if __name__ == '__main__':
    try:
        # 啟動前的最終檢查
        logger.info("[STARTUP] 啟動 EMI 智能教學助理系統...")
        logger.info(f"[DATABASE] 資料庫狀態: {'[OK] 已初始化' if DATABASE_INITIALIZED else '[ERROR] 未初始化'}")
        logger.info(f"[AI] AI 模型: {CURRENT_MODEL or '未配置'}")
        logger.info(f"[LINE] LINE Bot: {'[OK] 已配置' if (line_bot_api and handler) else '[ERROR] 未配置'}")
        
        # 執行會話清理
        cleanup_result = manage_conversation_sessions()
        logger.info(f"[CLEANUP] 啟動時會話清理: 清理了 {cleanup_result.get('cleaned_sessions', 0)} 個舊會話")
        
        # 啟動 Flask 應用
        port = int(os.environ.get('PORT', 5000))
        app.run(
            host='0.0.0.0',
            port=port,
            debug=os.environ.get('FLASK_ENV') == 'development'
        )
        
    except Exception as e:
        logger.error(f"[ERROR] 應用程式啟動失敗: {e}")
        raise

# =================== Railway 部署專用啟動點 ===================
# Railway 使用 Gunicorn 啟動，所以上面的 if __name__ == '__main__' 不會執行
# 但資料庫初始化已經在模組載入時完成，這裡只需要確保 app 對象可用

# 確保在 Gunicorn 環境下也能正確初始化
if not DATABASE_INITIALIZED:
    logger.warning("[WARNING] Gunicorn 環境下資料庫未初始化，嘗試緊急初始化...")
    try:
        initialize_database()
        logger.info("[OK] Gunicorn 環境下緊急初始化成功")
    except Exception as e:
        logger.error(f"[ERROR] Gunicorn 環境下緊急初始化失敗: {e}")

# 輸出最終狀態
logger.info("=" * 60)
logger.info("EMI 智能教學助理系統 - Railway 修復版 v4.2.2")
logger.info(f"[DATABASE] 資料庫: {'[OK] 就緒' if DATABASE_INITIALIZED else '[ERROR] 未就緒'}")
logger.info(f"[AI] AI: {'[OK] 就緒' if model else '[ERROR] 未配置'}")
logger.info(f"[LINE] LINE: {'[OK] 就緒' if (line_bot_api and handler) else '[ERROR] 未配置'}")
logger.info(f"[MEMORY] 記憶功能: {'[OK] 已啟用' if DATABASE_INITIALIZED else '[ERROR] 無法使用'}")
logger.info("[READY] 系統準備就緒，等待請求...")
logger.info("=" * 60)

# =================== 檔案結束標記 ===================
# 第4段完成 - 這是 app.py 的最後一段
# 功能包含：健康檢查、錯誤處理、啟動配置
# 修復版本：專門解決 Railway 部署時的 emoji 語法錯誤問題
# 
# 重要修復項目：
# 1. 移除所有 emoji 字符，避免語法錯誤
# 2. 使用文字標籤替代 (如 [OK], [ERROR], [WARNING])
# 3. 保留完整功能性，包括記憶功能和會話管理
# 4. 強化錯誤處理和資料庫初始化
# 5. 確保 Railway 部署環境相容性
