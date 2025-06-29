# =================== app.py 更新版 - 第1段開始 ===================
# 基本導入和配置（增加記憶功能和學習歷程支援）

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

# =================== 會話管理功能（新增）===================

def get_or_create_active_session(student):
    """取得或創建學生的活躍會話"""
    try:
        from models import ConversationSession
        
        # 檢查是否有活躍會話
        active_session = student.get_active_session()
        
        if not active_session:
            # 創建新會話
            active_session = student.start_new_session()
            logger.info(f"🆕 為學生 {student.name} 創建新會話 (ID: {active_session.id})")
        else:
            logger.debug(f"🔄 使用現有會話 (ID: {active_session.id})")
        
        return active_session
    except Exception as e:
        logger.error(f"❌ 會話管理錯誤: {e}")
        return None

def should_end_session(session):
    """判斷會話是否應該結束（基於時間間隔）"""
    if not session or not session.is_active():
        return False
    
    # 如果會話已經超過30分鐘沒有活動，應該結束
    return session.should_auto_end(timeout_minutes=30)

# =================== 學生註冊機制（保持不變）===================

def handle_student_registration(line_user_id, message_text, display_name=""):
    """優化的註冊流程：學號 → 姓名 → 確認（保持原有邏輯）"""
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

# =================== AI回應生成（增強版，支援記憶功能）===================

def generate_ai_response_with_context(message_text, student):
    """生成帶記憶功能的AI回應"""
    try:
        if not GEMINI_API_KEY or not CURRENT_MODEL:
            return "AI service is currently unavailable. Please try again later."
        
        from models import Message
        
        # === 1. 取得對話上下文（記憶功能）===
        context = Message.get_conversation_context(student, limit=5)
        
        # === 2. 構建包含記憶的提示詞 ===
        context_str = ""
        if context['conversation_flow']:
            context_str = "Previous conversation context:\n"
            for i, conv in enumerate(context['conversation_flow'][-3:], 1):  # 最近3輪對話
                context_str += f"{i}. Student: {conv['content'][:100]}...\n"
                if conv['ai_response']:
                    context_str += f"   AI: {conv['ai_response'][:100]}...\n"
            context_str += "\n"
        
        # 整理最近討論的主題
        recent_topics = ", ".join(context['recent_topics'][-5:]) if context['recent_topics'] else ""
        topics_str = f"Recent topics discussed: {recent_topics}\n" if recent_topics else ""
        
        # === 3. 建構增強的提示詞 ===
        prompt = f"""You are an EMI (English as a Medium of Instruction) teaching assistant for the course "Practical Applications of AI in Life and Learning."

Student: {student.name} (ID: {getattr(student, 'student_id', 'Not set')})

{context_str}{topics_str}Current question: {message_text}

Please provide a helpful, academic response in English (150 words max). 

Guidelines:
- If this continues a previous topic, acknowledge the connection and build upon it
- If the student is asking a follow-up question, reference the previous discussion naturally
- Focus on clear, educational explanations with practical examples
- Maintain encouraging tone for learning
- Use academic language appropriate for university students

Response:"""

        # === 4. 調用 Gemini API ===
        model = genai.GenerativeModel(CURRENT_MODEL)
        
        # 配置生成參數
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            max_output_tokens=200
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if response and response.text:
            ai_response = response.text.strip()
            logger.info(f"🤖 帶記憶的AI回應生成成功 - 學生: {student.name}, 長度: {len(ai_response)} 字")
            return ai_response
        else:
            logger.error("❌ AI回應為空")
            return get_fallback_response_with_context(message_text, context)
        
    except Exception as e:
        logger.error(f"❌ 帶記憶的AI回應生成錯誤: {e}")
        return get_fallback_response_with_context(message_text, context if 'context' in locals() else {})

def get_fallback_response_with_context(message_text, context):
    """帶上下文的備用回應"""
    
    # 檢查是否是後續問題
    if context.get('recent_topics'):
        recent_topic = context['recent_topics'][-1] if context['recent_topics'] else ""
        if any(word in message_text.lower() for word in ['what about', 'how about', 'and', 'also', 'more']):
            return f"I understand you want to explore more about {recent_topic}. This is a great follow-up question! Let me help you dive deeper into this concept."
    
    # 基於關鍵詞的回應
    message_lower = message_text.lower()
    
    if any(word in message_lower for word in ['ai', 'artificial intelligence']):
        return "**Artificial Intelligence**: systems that can perform tasks that typically require human intelligence. Example: recommendation systems like Netflix suggest content based on your viewing patterns."
    
    elif any(word in message_lower for word in ['machine learning', 'ml']):
        return "**Machine Learning**: AI subset where systems learn from data without explicit programming. Example: email spam filters improve by analyzing patterns in millions of emails."
    
    elif any(word in message_lower for word in ['deep learning']):
        return "**Deep Learning**: advanced ML using neural networks with multiple layers. Example: image recognition systems that can identify objects in photos with human-level accuracy."
    
    else:
        return "I'm having some technical difficulties processing your question. Could you please rephrase it? I'm here to help with your AI and learning questions! 🤖"

# =================== 原有的generate_ai_response函數（保持向後相容）===================

def generate_ai_response(message_text, student):
    """原有的AI回應函數（現在調用增強版）"""
    return generate_ai_response_with_context(message_text, student)

# =================== app.py 更新版 - 第1段結束 ===================

# =================== app.py 更新版 - 第2段開始 ===================

# =================== 學習歷程生成功能（新增）===================

def generate_learning_history(student_id):
    """生成學習歷程（後台按需生成，替換原來的即時學習建議）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        logger.info(f"📚 開始生成學生 {student_id} 的學習歷程...")
        
        # === 1. 獲取學生和驗證 ===
        student = Student.get_by_id(student_id)
        if not student:
            return {
                'status': 'error',
                'message': '找不到指定的學生'
            }
        
        # === 2. 收集學習資料 ===
        all_messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp))
        
        all_sessions = list(ConversationSession.select().where(
            ConversationSession.student == student
        ).order_by(ConversationSession.session_start))
        
        if not all_messages:
            return {
                'status': 'error',
                'message': '該學生尚無學習記錄'
            }
        
        # === 3. 分析學習數據 ===
        
        # 討論主題分析
        topics_analysis = analyze_discussion_topics(all_messages)
        
        # 學習軌跡分析
        learning_progression = analyze_learning_progression(all_messages, all_sessions)
        
        # 關鍵互動識別
        key_interactions = identify_key_interactions(all_messages, all_sessions)
        
        # === 4. 構建AI分析提示 ===
        message_sample = "\n".join([
            f"[{msg.timestamp.strftime('%m-%d %H:%M')}] {msg.content[:150]}..."
            for msg in all_messages[-20:]  # 最近20則訊息
        ])
        
        prompt = f"""分析以下學生的完整學習歷程，生成詳細的學習歷程報告：

學生資訊：
- 姓名：{student.name}
- 學號：{getattr(student, 'student_id', '未設定')}
- 學習期間：{all_messages[0].timestamp.strftime('%Y-%m-%d')} 至 {all_messages[-1].timestamp.strftime('%Y-%m-%d')}
- 總對話數：{len(all_messages)}
- 總會話次數：{len(all_sessions)}

學習活動樣本：
{message_sample}

討論主題統計：{topics_analysis}
學習發展特點：{learning_progression}
關鍵學習時刻：{key_interactions}

請生成包含以下部分的繁體中文學習歷程：

📚 **主要學習主題**
[列出學生討論過的核心主題，展現學習廣度]

📈 **學習發展軌跡**
[描述學生從初學到進階的學習演進過程]

💡 **關鍵學習時刻**
[記錄重要的理解突破和深度討論時刻]

🔍 **學習深度分析**
[評估學生提問的深度和學習的主動性]

🎯 **個性化學習特色**
[總結學生獨特的學習風格和偏好]

🚀 **未來發展建議**
[提供具體的學習方向和改進建議]

請用具體的例子支持每個觀點，展現學生的學習成長軌跡。"""

        # === 5. 調用AI生成詳細分析 ===
        if GEMINI_API_KEY and CURRENT_MODEL:
            try:
                model = genai.GenerativeModel(CURRENT_MODEL)
                generation_config = genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    top_k=20,
                    max_output_tokens=1000
                )
                
                response = model.generate_content(prompt, generation_config=generation_config)
                
                if response and response.text:
                    ai_analysis = response.text.strip()
                    logger.info(f"✅ AI學習歷程分析生成成功")
                else:
                    ai_analysis = generate_fallback_learning_history(student, len(all_messages), len(all_sessions))
            except Exception as e:
                logger.error(f"❌ AI學習歷程生成失敗: {e}")
                ai_analysis = generate_fallback_learning_history(student, len(all_messages), len(all_sessions))
        else:
            ai_analysis = generate_fallback_learning_history(student, len(all_messages), len(all_sessions))
        
        # === 6. 保存學習歷程到資料庫 ===
        learning_history = LearningHistory.create(
            student=student,
            summary=ai_analysis[:500],  # 摘要前500字
            learning_topics=','.join(topics_analysis.keys()) if topics_analysis else '',
            analysis_data=json.dumps({
                'topics_analysis': topics_analysis,
                'learning_progression': learning_progression,
                'key_interactions': key_interactions,
                'full_analysis': ai_analysis
            }, ensure_ascii=False),
            generated_at=datetime.datetime.now(),
            version=1
        )
        
        logger.info(f"✅ 學習歷程已保存到資料庫 (ID: {learning_history.id})")
        
        return {
            'status': 'success',
            'history_id': learning_history.id,
            'content': ai_analysis,
            'summary': learning_history.summary,
            'generated_at': learning_history.generated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 學習歷程生成失敗: {e}")
        return {
            'status': 'error',
            'message': f'學習歷程生成失敗：{str(e)}'
        }

# =================== 學習歷程分析輔助函數 ===================

def analyze_discussion_topics(messages):
    """分析討論主題"""
    topics = {}
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural network']
    programming_keywords = ['python', 'code', 'programming', 'algorithm', 'coding']
    english_keywords = ['grammar', 'vocabulary', 'pronunciation', 'writing', 'speaking']
    business_keywords = ['business', 'management', 'marketing', 'strategy', 'finance']
    
    for message in messages:
        content_lower = message.content.lower()
        
        for keyword in ai_keywords:
            if keyword in content_lower:
                topics['AI與機器學習'] = topics.get('AI與機器學習', 0) + 1
        
        for keyword in programming_keywords:
            if keyword in content_lower:
                topics['程式設計'] = topics.get('程式設計', 0) + 1
        
        for keyword in english_keywords:
            if keyword in content_lower:
                topics['英語學習'] = topics.get('英語學習', 0) + 1
        
        for keyword in business_keywords:
            if keyword in content_lower:
                topics['商業管理'] = topics.get('商業管理', 0) + 1
    
    return topics

def analyze_learning_progression(messages, sessions):
    """分析學習軌跡"""
    progression = {
        'start_period': 'beginner',
        'current_period': 'intermediate',
        'key_milestones': [],
        'complexity_growth': 'steady'
    }
    
    # 根據會話長度判斷學習深度
    if len(sessions) > 0:
        total_messages = sum(session.message_count for session in sessions if hasattr(session, 'message_count'))
        avg_session_length = total_messages / len(sessions) if len(sessions) > 0 else 0
        
        if avg_session_length > 8:
            progression['current_period'] = 'advanced'
        elif avg_session_length > 4:
            progression['current_period'] = 'intermediate'
        else:
            progression['current_period'] = 'beginner'
    
    # 識別學習里程碑
    if len(messages) > 20:
        progression['key_milestones'].append('達成活躍學習者水準')
    if len(sessions) > 5:
        progression['key_milestones'].append('展現持續學習動機')
    if len([msg for msg in messages if len(msg.content) > 100]) > 5:
        progression['key_milestones'].append('能夠提出深度問題')
    
    return progression

def identify_key_interactions(messages, sessions):
    """識別關鍵互動"""
    key_moments = []
    
    # 找出長對話會話
    for session in sessions:
        if hasattr(session, 'message_count') and session.message_count > 8:
            key_moments.append({
                'type': 'deep_discussion',
                'timestamp': session.session_start.isoformat() if session.session_start else '',
                'description': f'深度討論會話（{session.message_count}則訊息）'
            })
    
    # 找出複雜問題
    complex_questions = [msg for msg in messages if len(msg.content) > 100 and '?' in msg.content]
    if len(complex_questions) > 3:
        key_moments.append({
            'type': 'complex_thinking',
            'count': len(complex_questions),
            'description': '展現深度思考能力的複雜問題'
        })
    
    # 找出學習突破點（基於訊息間隔變化）
    if len(messages) > 10:
        recent_activity = len([msg for msg in messages[-10:] if msg.timestamp > datetime.datetime.now() - datetime.timedelta(days=7)])
        if recent_activity > 5:
            key_moments.append({
                'type': 'learning_acceleration',
                'description': '最近一週學習活動顯著增加'
            })
    
    return key_moments

def generate_fallback_learning_history(student, message_count, session_count):
    """備用學習歷程生成"""
    days_learning = (datetime.datetime.now() - student.created_at).days if student.created_at else 0
    
    return f"""📚 **主要學習主題**
{student.name} 在 {days_learning} 天的學習期間，主要專注於人工智慧與生活應用相關主題。從對話記錄可以看出對於 AI 技術的基礎概念有持續的學習興趣。

📈 **學習發展軌跡**
學習歷程顯示從基礎概念理解逐步向應用層面發展。總共進行了 {message_count} 次互動，透過 {session_count} 個學習會話展現學習的持續性。

💡 **關鍵學習時刻**
學習過程中展現了積極的提問態度，能夠主動尋求知識澄清和深化理解。

🔍 **學習深度分析**
學習態度認真，具備良好的學習動機。建議繼續保持這種積極的學習態度。

🎯 **個性化學習特色**
展現出對 AI 技術應用的學習興趣，學習風格偏向理論與實踐結合。

🚀 **未來發展建議**
建議擴展學習範圍，嘗試更深入的技術討論，並將所學概念應用到實際場景中。"""

# =================== 學習建議功能（保留原有API，但簡化）===================

def generate_learning_suggestion(student):
    """保留的學習建議函數（為了向後相容，但功能簡化）"""
    from models import Message
    
    try:
        # 獲取最近對話記錄
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(10))
        
        if not messages:
            return "Welcome! Start asking questions to receive personalized learning suggestions."
        
        # 簡化的建議生成
        message_count = len(messages)
        recent_activity = "active" if message_count >= 5 else "moderate"
        
        suggestion = f"""📊 **{student.name}'s Learning Overview**

🔹 **Activity Level**: You are {recent_activity}ly engaged
Recent conversations: {message_count} in your learning journey

🔹 **Quick Suggestion**: {"Continue this excellent engagement! Try exploring more advanced topics." if message_count >= 5 else "Great start! Feel free to ask more questions to deepen your understanding."}

🔹 **Next Steps**: Consider discussing real-world applications of the concepts you've learned.

💡 **Note**: For detailed learning history, ask your teacher to generate a comprehensive learning journey report."""
        
        return suggestion
        
    except Exception as e:
        logger.error(f"學習建議生成失敗: {e}")
        return get_fallback_suggestion(student, 0)

def get_fallback_suggestion(student, message_count):
    """備用的學習建議（保持原有邏輯）"""
    if message_count >= 10:
        activity_level = "actively participating"
        suggestion = "Keep up this great learning enthusiasm! Try challenging yourself with more complex topics."
    elif message_count >= 5:
        activity_level = "moderately engaged"
        suggestion = "Good learning attitude! Consider increasing interaction frequency for better results."
    else:
        activity_level = "getting started"
        suggestion = "Welcome! Feel free to ask more questions - any learning doubts can be discussed anytime."
    
    days_since_creation = (datetime.datetime.now() - student.created_at).days if student.created_at else 0
    
    return f"""📊 {student.name}'s Learning Status

🔹 **Performance**: You are {activity_level}
You have {message_count} conversation records in {days_since_creation} days, showing continuous learning motivation.

🔹 **Suggestion**: {suggestion}

🔹 **Tip**: Regularly review previous discussions and try applying what you've learned in real situations to deepen understanding!"""

# =================== LINE Bot Webhook 和訊息處理（增強版，支援會話管理）===================

@app.route('/callback', methods=['POST'])
def callback():
    """LINE Bot Webhook 回調處理（增強版支援記憶功能）"""
    if not (line_bot_api and handler):
        logger.error("❌ LINE Bot 未正確配置")
        abort(500)
    
    # 驗證請求來源
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
    """處理 LINE 文字訊息（增強版支援記憶功能）"""
    try:
        from models import Student, Message, ConversationSession
        
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
        logger.info(f"👤 收到用戶 {user_id} 的訊息: {message_text[:50]}...")
        
        # === 1. 獲取或創建學生記錄 ===
        student, created = Student.get_or_create(
            line_user_id=user_id,
            defaults={
                'name': f'學生_{user_id[-6:]}',
                'registration_step': 1,
                'created_at': datetime.datetime.now()
            }
        )
        
        if created:
            logger.info(f"✅ 創建新學生記錄: {student.name}")
        
        # === 2. 處理註冊流程 ===
        if student.registration_step > 0:
            registration_response = handle_registration(student, message_text)
            if registration_response:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=registration_response)
                )
                return
        
        # === 3. 獲取或創建活躍會話 ===
        active_session = student.get_active_session()
        if not active_session:
            active_session = ConversationSession.create(
                student=student,
                session_start=datetime.datetime.now(),
                message_count=0
            )
            logger.info(f"🆕 創建新會話: {active_session.id}")
        
        # === 4. 生成帶記憶功能的AI回應 ===
        ai_response = generate_ai_response_with_context(student, message_text, active_session)
        
        # === 5. 儲存訊息記錄（包含會話關聯）===
        message_record = Message.create(
            student=student,
            content=message_text,
            timestamp=datetime.datetime.now(),
            session=active_session,
            ai_response=ai_response,
            topic_tags=extract_topic_tags(message_text)
        )
        
        # === 6. 更新會話統計 ===
        active_session.update_session_stats()
        
        # === 7. 回覆用戶 ===
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
        
        logger.info(f"✅ 訊息處理完成 - 會話:{active_session.id}, 訊息:{message_record.id}")
        
    except Exception as e:
        logger.error(f"❌ 訊息處理失敗: {e}")
        try:
            error_response = "抱歉，系統暫時出現問題，請稍後再試。如果問題持續，請聯繫管理員。"
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
    
    # 定義主題關鍵字
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

# =================== 原有的註冊處理函數（保持不變）===================

def handle_registration(student, message_text):
    """處理學生註冊流程（保持原有邏輯）"""
    step = student.registration_step
    
    if step == 1:
        # 詢問姓名
        student.name = message_text
        student.registration_step = 2
        student.save()
        return f"您好 {student.name}！歡迎使用 EMI 智能教學助理！\n\n請告訴我您的學號："
    
    elif step == 2:
        # 設置學號
        student.student_id = message_text
        student.registration_step = 3
        student.save()
        return f"學號已設定為：{student.student_id}\n\n請選擇您的班級（例如：資工一甲、企管二乙）："
    
    elif step == 3:
        # 設置班級
        student.class_name = message_text
        student.registration_step = 0  # 完成註冊
        student.save()
        
        welcome_message = f"""🎉 註冊完成！

📋 您的資料：
• 姓名：{student.name}
• 學號：{student.student_id}
• 班級：{student.class_name}

🤖 我是您的 EMI 智能教學助理，可以協助您：
• 回答學習相關問題
• 提供英語學習建議
• 解釋 AI 與科技概念
• 協助課業討論

現在您可以開始向我提問了！有任何學習上的疑問都歡迎詢問。"""
        
        return welcome_message
    
    return None

# =================== app.py 更新版 - 第2段結束 ===================

# =================== app.py 更新版 - 第3段開始 ===================

# =================== 主題標籤提取（簡單版）===================

def extract_simple_topic_tags(message_text):
    """簡單的主題標籤提取"""
    tags = []
    content_lower = message_text.lower()
    
    # AI相關關鍵詞
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural network', 'algorithm']
    if any(keyword in content_lower for keyword in ai_keywords):
        tags.append('AI技術')
    
    # 程式設計關鍵詞
    programming_keywords = ['python', 'code', 'programming', 'software', 'development']
    if any(keyword in content_lower for keyword in programming_keywords):
        tags.append('程式設計')
    
    # 英語學習關鍵詞
    english_keywords = ['grammar', 'vocabulary', 'pronunciation', 'writing', 'speaking']
    if any(keyword in content_lower for keyword in english_keywords):
        tags.append('英語學習')
    
    # 學習方法關鍵詞
    study_keywords = ['study', 'learn', 'understand', 'explain', 'help', 'how']
    if any(keyword in content_lower for keyword in study_keywords):
        tags.append('學習諮詢')
    
    return tags

# =================== 系統路由（增強版，包含會話統計）===================

@app.route('/')
def index():
    """增強版系統首頁，包含會話統計"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        
        # 會話統計（新增）
        try:
            total_sessions = ConversationSession.select().count()
            active_sessions = ConversationSession.select().where(
                ConversationSession.session_end.is_null()
            ).count()
        except:
            total_sessions = 0
            active_sessions = 0
        
        # 學習歷程統計（新增）
        try:
            total_histories = LearningHistory.select().count()
            students_with_history = LearningHistory.select(
                LearningHistory.student
            ).distinct().count()
        except:
            total_histories = 0
            students_with_history = 0
        
        # 本週活躍學生
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
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
        
        # 生成增強首頁HTML
        index_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EMI 智能教學助理系統 - 記憶功能版</title>
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
        .stats-enhanced {{
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
        .stat-card.new-feature {{
            border-left-color: #e74c3c;
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
        .stat-new {{
            color: #e74c3c;
            font-size: 0.7em;
            margin-top: 5px;
            font-weight: bold;
        }}
        
        /* 新功能展示 */
        .new-features {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            border-left: 5px solid #e74c3c;
        }}
        .feature-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .feature-item {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid #27ae60;
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
        .btn-purple {{ background: #9b59b6; }}
        .btn-purple:hover {{ background: #8e44ad; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 系統標題 -->
        <div class="header">
            <h1>🎓 EMI 智能教學助理系統 <span class="version-badge">記憶功能版</span></h1>
            <p>Practical Applications of AI in Life and Learning - 支援連續對話記憶和學習歷程</p>
        </div>
        
        <!-- 新功能介紹 -->
        <div class="new-features">
            <h3 style="color: #e74c3c; margin-bottom: 15px;">🎉 新增功能特色</h3>
            <div class="feature-list">
                <div class="feature-item">
                    <strong>🧠 記憶功能</strong><br>
                    AI能記住前幾輪對話，支援深入追問和連續討論
                </div>
                <div class="feature-item">
                    <strong>📚 學習歷程</strong><br>
                    後台生成詳細的個人化學習軌跡分析報告
                </div>
                <div class="feature-item">
                    <strong>💬 會話追蹤</strong><br>
                    自動管理對話會話，提供更好的學習體驗
                </div>
                <div class="feature-item">
                    <strong>🏷️ 主題標籤</strong><br>
                    自動識別討論主題，建立學習知識圖譜
                </div>
            </div>
        </div>
        
        <!-- 增強統計 -->
        <div class="stats-enhanced">
            <div class="stat-card">
                <div class="stat-number">{total_students}</div>
                <div class="stat-label">👥 總學生數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_messages}</div>
                <div class="stat-label">💬 總對話數</div>
            </div>
            <div class="stat-card new-feature">
                <div class="stat-number">{total_sessions}</div>
                <div class="stat-label">🗣️ 對話會話</div>
                <div class="stat-new">NEW</div>
            </div>
            <div class="stat-card new-feature">
                <div class="stat-number">{total_histories}</div>
                <div class="stat-label">📚 學習歷程</div>
                <div class="stat-new">NEW</div>
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
                <span>🧠 記憶功能</span>
                <span style="color: #e74c3c;">✅ 已啟用</span>
            </div>
            <div class="status-item">
                <span>💬 活躍會話</span>
                <span style="color: #2c3e50;">{active_sessions} 個</span>
            </div>
            <div class="status-item">
                <span>📚 學習歷程覆蓋</span>
                <span style="color: #2c3e50;">{students_with_history} 位學生</span>
            </div>
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
                    檢查系統狀態、會話管理和記憶功能
                </p>
                <a href="/health" class="action-btn btn-success">系統診斷</a>
            </div>
            
            <div class="action-card">
                <h4 style="color: #f39c12; margin-bottom: 15px;">📊 資料匯出</h4>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px;">
                    匯出學生清單、對話記錄和會話資料
                </p>
                <a href="/export" class="action-btn btn-orange">匯出資料</a>
            </div>
            
            <div class="action-card">
                <h4 style="color: #9b59b6; margin-bottom: 15px;">💬 會話管理</h4>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px;">
                    管理活躍會話和記憶功能設定
                </p>
                <a href="/admin/sessions" class="action-btn btn-purple">會話控制台</a>
            </div>
        </div>
        
        <!-- 版本資訊 -->
        <div style="margin-top: 40px; text-align: center; color: #7f8c8d; font-size: 0.9em;">
            <p>EMI 智能教學助理系統 v4.1.0（記憶功能版）| 
            <a href="/health" style="color: #3498db;">系統狀態</a> | 
            <a href="/export" style="color: #3498db;">資料匯出</a> | 
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

# =================== 學生管理路由（增強版，包含會話統計）===================

@app.route('/students')
def students():
    """學生列表頁面（增強版包含會話和學習歷程統計）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        # 取得所有學生並計算增強統計
        students_data = []
        students = list(Student.select().order_by(Student.created_at.desc()))
        
        for student in students:
            try:
                # 基本統計
                message_count = Message.select().where(Message.student == student).count()
                
                # 會話統計（新增）
                try:
                    session_count = ConversationSession.select().where(
                        ConversationSession.student == student
                    ).count()
                    active_sessions = ConversationSession.select().where(
                        ConversationSession.student == student,
                        ConversationSession.session_end.is_null()
                    ).count()
                except:
                    session_count = 0
                    active_sessions = 0
                
                # 學習歷程統計（新增）
                try:
                    has_learning_history = LearningHistory.select().where(
                        LearningHistory.student == student
                    ).exists()
                    latest_history = LearningHistory.select().where(
                        LearningHistory.student == student
                    ).order_by(LearningHistory.generated_at.desc()).first()
                except:
                    has_learning_history = False
                    latest_history = None
                
                # 最後活動時間
                last_message = Message.select().where(
                    Message.student == student
                ).order_by(Message.timestamp.desc()).first()
                
                last_active = last_message.timestamp if last_message else student.created_at
                
                # 註冊狀態
                registration_status = "已完成"
                if hasattr(student, 'registration_step') and student.registration_step > 0:
                    registration_status = f"進行中 (步驟 {student.registration_step})"
                elif not student.name or student.name.startswith('學生_'):
                    registration_status = "未完成"
                
                students_data.append({
                    'id': student.id,
                    'name': student.name or '未設定',
                    'student_id': getattr(student, 'student_id', ''),
                    'class_name': getattr(student, 'class_name', ''),
                    'message_count': message_count,
                    'session_count': session_count,
                    'active_sessions': active_sessions,
                    'has_learning_history': has_learning_history,
                    'latest_history_date': latest_history.generated_at.strftime('%Y-%m-%d') if latest_history else None,
                    'last_active': last_active.strftime('%Y-%m-%d %H:%M') if last_active else '',
                    'created_at': student.created_at.strftime('%Y-%m-%d') if student.created_at else '',
                    'registration_status': registration_status
                })
            except Exception as e:
                logger.error(f"處理學生 {student.id} 統計時錯誤: {e}")
                students_data.append({
                    'id': student.id,
                    'name': student.name or '未設定',
                    'student_id': getattr(student, 'student_id', ''),
                    'class_name': getattr(student, 'class_name', ''),
                    'message_count': 0,
                    'session_count': 0,
                    'active_sessions': 0,
                    'has_learning_history': False,
                    'latest_history_date': None,
                    'last_active': '',
                    'created_at': '',
                    'registration_status': '未知'
                })
        
        # 總體統計
        total_students = len(students_data)
        total_messages = sum(s['message_count'] for s in students_data)
        total_sessions = sum(s['session_count'] for s in students_data)
        students_with_history = sum(1 for s in students_data if s['has_learning_history'])
        active_session_count = sum(s['active_sessions'] for s in students_data)
        
        # 生成增強學生列表HTML
        students_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>學生管理 - EMI 智能教學助理系統（記憶功能版）</title>
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
        .back-button:hover {{
            background: rgba(255,255,255,0.3);
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
        .stat-new {{
            color: #e74c3c;
            font-size: 0.7em;
            font-weight: bold;
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
        .status-incomplete {{
            background: #f8d7da;
            color: #721c24;
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
        .btn-success {{
            background: #27ae60;
            color: white;
        }}
        .btn-warning {{
            background: #f39c12;
            color: white;
        }}
        .btn-new {{
            background: #e74c3c;
            color: white;
        }}
        .new-feature {{
            position: relative;
        }}
        .new-badge {{
            background: #e74c3c;
            color: white;
            padding: 2px 6px;
            border-radius: 8px;
            font-size: 0.6em;
            position: absolute;
            top: -5px;
            right: -5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-button">← 返回首頁</a>
            <h1>👥 學生管理系統</h1>
            <p>EMI 智能教學助理系統 - 記憶功能版學生管理控制台</p>
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
                <div class="stat-new">NEW</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{students_with_history}</div>
                <div class="stat-label">有學習歷程</div>
                <div class="stat-new">NEW</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{active_session_count}</div>
                <div class="stat-label">活躍會話</div>
                <div class="stat-new">NEW</div>
            </div>
        </div>
        
        <!-- 學生列表 -->
        <div class="table-container">
            <div class="table-header">
                <h3 style="margin: 0;">📋 學生清單與統計</h3>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>學生資訊</th>
                        <th>對話數</th>
                        <th class="new-feature">會話統計 <span class="new-badge">NEW</span></th>
                        <th class="new-feature">學習歷程 <span class="new-badge">NEW</span></th>
                        <th>註冊狀態</th>
                        <th>最後活動</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # 生成每個學生的行
        for student in students_data:
            # 註冊狀態樣式
            if student['registration_status'] == '已完成':
                status_class = 'status-completed'
            elif '進行中' in student['registration_status']:
                status_class = 'status-progress'
            else:
                status_class = 'status-incomplete'
            
            # 學習歷程顯示
            if student['has_learning_history']:
                history_display = f"✅ 已生成<br><small>{student['latest_history_date']}</small>"
                history_btn = f'<a href="/admin/history/{student["id"]}" class="action-btn btn-success">查看歷程</a>'
            else:
                history_display = "❌ 未生成"
                history_btn = f'<a href="/admin/generate_history/{student["id"]}" class="action-btn btn-new">生成歷程</a>'
            
            students_html += f"""
                    <tr>
                        <td>
                            <div class="student-name">{student['name']}</div>
                            <small>學號：{student['student_id'] or '未設定'}</small><br>
                            <small>班級：{student['class_name'] or '未設定'}</small>
                        </td>
                        <td>{student['message_count']}</td>
                        <td>
                            <strong>{student['session_count']}</strong> 個會話<br>
                            <small>活躍：{student['active_sessions']} 個</small>
                        </td>
                        <td>{history_display}</td>
                        <td>
                            <span class="status-badge {status_class}">{student['registration_status']}</span>
                        </td>
                        <td>{student['last_active']}</td>
                        <td>
                            <a href="/student/{student['id']}" class="action-btn btn-primary">詳細資料</a>
                            {history_btn}
                        </td>
                    </tr>
            """
        
        students_html += """
                </tbody>
            </table>
        </div>
        
        <!-- 批量操作 -->
        <div style="margin-top: 30px; text-align: center;">
            <a href="/export" class="action-btn btn-warning" style="padding: 12px 24px; font-size: 1em;">📊 匯出完整資料</a>
            <a href="/admin/sessions" class="action-btn btn-new" style="padding: 12px 24px; font-size: 1em;">💬 會話管理</a>
        </div>
        
        <!-- 說明文字 -->
        <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px; color: #6c757d; font-size: 0.9em;">
            <h4 style="color: #495057;">📝 功能說明</h4>
            <ul>
                <li><strong>會話統計：</strong>顯示學生的對話會話數量，支援記憶功能的連續討論追蹤</li>
                <li><strong>學習歷程：</strong>後台生成的個人化學習軌跡分析，包含討論主題和學習發展</li>
                <li><strong>活躍會話：</strong>目前正在進行中的對話會話，支援上下文記憶功能</li>
                <li><strong>註冊狀態：</strong>學生註冊完成度，影響功能使用權限</li>
            </ul>
        </div>
    </div>
</body>
</html>
        """
        
        return students_html
        
    except Exception as e:
        logger.error(f"學生列表生成錯誤: {e}")
        return f"學生列表載入錯誤: {str(e)}", 500

# =================== 管理員路由（增強版，包含學習歷程生成）===================

@app.route('/admin/generate_history/<int:student_id>')
def admin_generate_history(student_id):
    """管理員生成學習歷程路由（新增功能）"""
    try:
        logger.info(f"📚 管理員觸發學習歷程生成 - 學生ID: {student_id}")
        
        # 生成學習歷程
        result = generate_learning_history(student_id)
        
        if result['status'] == 'success':
            success_message = f"""
            ✅ 學習歷程生成成功！
            
            📊 生成資訊：
            • 歷程ID：{result['history_id']}
            • 生成時間：{result['generated_at']}
            • 分析摘要：{result['summary'][:100]}...
            
            🔄 正在跳轉到學生詳細頁面...
            """
            
            # 生成成功頁面並自動跳轉
            return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>學習歷程生成成功</title>
    <meta http-equiv="refresh" content="3;url=/student/{student_id}">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .success-card {{
            background: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            max-width: 500px;
        }}
        .success-icon {{
            font-size: 4em;
            margin-bottom: 20px;
        }}
        .success-title {{
            color: #27ae60;
            font-size: 1.5em;
            margin-bottom: 20px;
        }}
        .success-content {{
            color: #2c3e50;
            line-height: 1.6;
            white-space: pre-line;
        }}
        .loading {{
            margin-top: 20px;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="success-card">
        <div class="success-icon">🎉</div>
        <h2 class="success-title">學習歷程生成成功！</h2>
        <div class="success-content">{success_message}</div>
        <div class="loading">⏳ 3秒後自動跳轉...</div>
    </div>
</body>
</html>
            """
        else:
            # 生成失敗，顯示錯誤頁面
            error_message = result.get('message', '未知錯誤')
            return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>學習歷程生成失敗</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .error-card {{
            background: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            max-width: 500px;
        }}
        .error-icon {{
            font-size: 4em;
            margin-bottom: 20px;
        }}
        .error-title {{
            color: #e74c3c;
            font-size: 1.5em;
            margin-bottom: 20px;
        }}
        .error-content {{
            color: #2c3e50;
            line-height: 1.6;
        }}
        .back-btn {{
            margin-top: 20px;
            padding: 10px 20px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <div class="error-card">
        <div class="error-icon">❌</div>
        <h2 class="error-title">學習歷程生成失敗</h2>
        <div class="error-content">
            錯誤原因：{error_message}<br><br>
            請檢查學生是否有足夠的對話記錄，或聯繫系統管理員。
        </div>
        <a href="/students" class="back-btn">返回學生列表</a>
    </div>
</body>
</html>
            """
            
    except Exception as e:
        logger.error(f"學習歷程生成路由錯誤: {e}")
        return f"學習歷程生成錯誤: {str(e)}", 500

@app.route('/admin/sessions')
def admin_sessions():
    """會話管理控制台（新增功能）"""
    try:
        from models import ConversationSession, Student, manage_conversation_sessions
        
        # 執行會話清理
        cleanup_result = manage_conversation_sessions()
        
        # 取得會話統計
        total_sessions = ConversationSession.select().count()
        active_sessions = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        ).count()
        completed_sessions = total_sessions - active_sessions
        
        # 取得最近的會話
        recent_sessions = list(ConversationSession.select().join(Student).order_by(
            ConversationSession.session_start.desc()
        ).limit(20))
        
        # 生成會話管理頁面
        sessions_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>會話管理控制台 - EMI智能教學助理</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f8f9fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
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
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .stat-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .cleanup-result {{
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .sessions-table {{
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
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
        }}
        .session-active {{
            color: #27ae60;
            font-weight: bold;
        }}
        .session-completed {{
            color: #7f8c8d;
        }}
        .action-btn {{
            padding: 6px 12px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.8em;
            margin: 2px;
        }}
        .btn-info {{
            background: #3498db;
            color: white;
        }}
        .btn-warning {{
            background: #f39c12;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-button">← 返回首頁</a>
            <h1>💬 會話管理控制台</h1>
            <p>記憶功能會話監控與管理</p>
        </div>
        
        <!-- 清理結果 -->
        <div class="cleanup-result">
            ✅ 會話清理完成：清理了 {cleanup_result.get('cleaned_sessions', 0)} 個舊會話，
            清理了 {cleanup_result.get('cleaned_messages', 0)} 個孤立訊息
        </div>
        
        <!-- 統計概覽 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_sessions}</div>
                <div class="stat-label">總會話數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{active_sessions}</div>
                <div class="stat-label">活躍會話</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{completed_sessions}</div>
                <div class="stat-label">已完成會話</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{cleanup_result.get('cleaned_sessions', 0)}</div>
                <div class="stat-label">本次清理</div>
            </div>
        </div>
        
        <!-- 最近會話 -->
        <div class="sessions-table">
            <h3 style="padding: 20px; margin: 0; background: #34495e; color: white;">📋 最近會話記錄</h3>
            <table>
                <thead>
                    <tr>
                        <th>會話ID</th>
                        <th>學生</th>
                        <th>開始時間</th>
                        <th>結束時間</th>
                        <th>訊息數</th>
                        <th>狀態</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # 生成會話記錄
        for session in recent_sessions:
            status = "活躍中" if session.session_end is None else "已完成"
            status_class = "session-active" if session.session_end is None else "session-completed"
            
            start_time = session.session_start.strftime('%m-%d %H:%M') if session.session_start else '未知'
            end_time = session.session_end.strftime('%m-%d %H:%M') if session.session_end else '-'
            
            sessions_html += f"""
                    <tr>
                        <td>{session.id}</td>
                        <td>{session.student.name if session.student else '未知'}</td>
                        <td>{start_time}</td>
                        <td>{end_time}</td>
                        <td>{session.message_count}</td>
                        <td class="{status_class}">{status}</td>
                        <td>
                            <a href="/student/{session.student.id if session.student else 0}" class="action-btn btn-info">查看學生</a>
                        </td>
                    </tr>
            """
        
        sessions_html += """
                </tbody>
            </table>
        </div>
        
        <!-- 操作按鈕 -->
        <div style="margin-top: 30px; text-align: center;">
            <a href="/students" class="action-btn btn-info" style="padding: 12px 24px; font-size: 1em;">👥 返回學生列表</a>
            <a href="/export" class="action-btn btn-warning" style="padding: 12px 24px; font-size: 1em;">📊 匯出會話資料</a>
        </div>
        
        <!-- 說明 -->
        <div style="margin-top: 30px; padding: 20px; background: white; border-radius: 10px;">
            <h4>💡 會話管理說明</h4>
            <ul>
                <li><strong>活躍會話：</strong>正在進行中的對話，支援記憶功能</li>
                <li><strong>自動清理：</strong>超過24小時無活動的會話會自動結束</li>
                <li><strong>記憶範圍：</strong>每個會話保留最近10則訊息的上下文</li>
                <li><strong>會話統計：</strong>幫助了解學生的學習互動模式</li>
            </ul>
        </div>
    </div>
</body>
</html>
        """
        
        return sessions_html
        
    except Exception as e:
        logger.error(f"會話管理頁面錯誤: {e}")
        return f"會話管理載入錯誤: {str(e)}", 500

# =================== 資料下載路由（增強版，支援會話和學習歷程）===================

@app.route('/download/sessions')
def download_sessions():
    """下載會話記錄 TSV 檔案（新增功能）"""
    try:
        from models import ConversationSession, Student
        
        # 取得所有會話記錄
        sessions = list(ConversationSession.select().join(Student).order_by(
            ConversationSession.session_start.desc()
        ))
        
        if not sessions:
            return "目前沒有會話記錄可以下載", 404
        
        # 生成 TSV 內容
        tsv_lines = [
            '會話ID\t學生姓名\t學生ID\t開始時間\t結束時間\t持續時間(分鐘)\t訊息數量\t狀態\t上下文摘要\t主題標籤'
        ]
        
        for session in sessions:
            student_name = session.student.name if session.student else '未知學生'
            student_id = getattr(session.student, 'student_id', '') if session.student else ''
            start_time = session.session_start.strftime('%Y-%m-%d %H:%M:%S') if session.session_start else ''
            end_time = session.session_end.strftime('%Y-%m-%d %H:%M:%S') if session.session_end else ''
            duration = str(session.duration_minutes) if hasattr(session, 'duration_minutes') and session.duration_minutes else ''
            message_count = str(session.message_count) if hasattr(session, 'message_count') else '0'
            status = '已完成' if session.session_end else '活躍中'
            context_summary = (session.context_summary or '').replace('\n', ' ').replace('\t', ' ')[:200]
            topic_tags = (session.topic_tags or '').replace('\t', ' ')
            
            tsv_lines.append(f"{session.id}\t{student_name}\t{student_id}\t{start_time}\t{end_time}\t{duration}\t{message_count}\t{status}\t{context_summary}\t{topic_tags}")
        
        # 建立回應
        tsv_content = '\n'.join(tsv_lines)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"conversation_sessions_{timestamp}.tsv"
        
        response = make_response(tsv_content)
        response.headers['Content-Type'] = 'text/tab-separated-values; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"📊 會話記錄匯出完成: {len(sessions)} 筆會話")
        return response
        
    except Exception as e:
        logger.error(f"會話記錄下載錯誤: {e}")
        return f"會話記錄下載失敗: {str(e)}", 500

@app.route('/download/histories')
def download_histories():
    """下載學習歷程記錄 TSV 檔案（新增功能）"""
    try:
        from models import LearningHistory, Student
        
        # 取得所有學習歷程記錄
        histories = list(LearningHistory.select().join(Student).order_by(
            LearningHistory.generated_at.desc()
        ))
        
        if not histories:
            return "目前沒有學習歷程記錄可以下載", 404
        
        # 生成 TSV 內容
        tsv_lines = [
            '歷程ID\t學生姓名\t學生ID\t生成時間\t摘要\t學習主題\t版本\t分析資料'
        ]
        
        for history in histories:
            student_name = history.student.name if history.student else '未知學生'
            student_id = getattr(history.student, 'student_id', '') if history.student else ''
            generated_at = history.generated_at.strftime('%Y-%m-%d %H:%M:%S') if history.generated_at else ''
            summary = (history.summary or '').replace('\n', ' ').replace('\t', ' ')[:300]
            learning_topics = (history.learning_topics or '').replace('\t', ' ')
            version = str(history.version) if hasattr(history, 'version') else '1'
            
            # 處理分析資料
            analysis_preview = ''
            if history.analysis_data:
                try:
                    analysis_obj = json.loads(history.analysis_data)
                    if isinstance(analysis_obj, dict):
                        analysis_preview = str(analysis_obj.get('topics_analysis', {}))[:100]
                except:
                    analysis_preview = str(history.analysis_data)[:100]
            
            analysis_preview = analysis_preview.replace('\n', ' ').replace('\t', ' ')
            
            tsv_lines.append(f"{history.id}\t{student_name}\t{student_id}\t{generated_at}\t{summary}\t{learning_topics}\t{version}\t{analysis_preview}")
        
        # 建立回應
        tsv_content = '\n'.join(tsv_lines)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"learning_histories_{timestamp}.tsv"
        
        response = make_response(tsv_content)
        response.headers['Content-Type'] = 'text/tab-separated-values; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"📚 學習歷程匯出完成: {len(histories)} 筆記錄")
        return response
        
    except Exception as e:
        logger.error(f"學習歷程下載錯誤: {e}")
        return f"學習歷程下載失敗: {str(e)}", 500

@app.route('/download/full_analysis')
def download_full_analysis():
    """下載完整分析報告（新增功能）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        # 收集所有資料
        students = list(Student.select())
        messages = list(Message.select())
        sessions = list(ConversationSession.select())
        histories = list(LearningHistory.select())
        
        # 生成完整分析報告
        analysis_data = {
            'export_info': {
                'generated_at': datetime.datetime.now().isoformat(),
                'system_version': 'EMI v4.1.0 (Memory Enhanced)',
                'total_students': len(students),
                'total_messages': len(messages),
                'total_sessions': len(sessions),
                'total_histories': len(histories)
            },
            'students_summary': [],
            'memory_feature_stats': {
                'active_sessions': len([s for s in sessions if s.session_end is None]),
                'average_session_length': sum(s.message_count for s in sessions if hasattr(s, 'message_count')) / len(sessions) if sessions else 0,
                'students_with_history': len(set(h.student.id for h in histories if h.student))
            }
        }
        
        # 學生摘要統計
        for student in students:
            try:
                student_messages = [m for m in messages if m.student.id == student.id]
                student_sessions = [s for s in sessions if s.student and s.student.id == student.id]
                student_histories = [h for h in histories if h.student and h.student.id == student.id]
                
                analysis_data['students_summary'].append({
                    'id': student.id,
                    'name': student.name,
                    'student_id': getattr(student, 'student_id', ''),
                    'message_count': len(student_messages),
                    'session_count': len(student_sessions),
                    'active_sessions': len([s for s in student_sessions if s.session_end is None]),
                    'has_learning_history': len(student_histories) > 0,
                    'latest_activity': max([m.timestamp for m in student_messages]).isoformat() if student_messages else None,
                    'registration_complete': getattr(student, 'registration_step', 0) == 0
                })
            except Exception as e:
                logger.error(f"處理學生 {student.id} 統計時錯誤: {e}")
        
        # 建立回應
        json_content = json.dumps(analysis_data, ensure_ascii=False, indent=2)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"emi_full_analysis_{timestamp}.json"
        
        response = make_response(json_content)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"📈 完整分析報告匯出完成")
        return response
        
    except Exception as e:
        logger.error(f"完整分析下載錯誤: {e}")
        return f"完整分析下載失敗: {str(e)}", 500

# =================== app.py 更新版 - 第3段結束 ===================

# =================== app.py 更新版 - 第4段開始 ===================

# =================== 學生詳細頁面（增強版，包含會話資訊）===================

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """增強版學生詳細資料頁面，包含會話和記憶功能資訊"""
    try:
        from models import Student, Message, ConversationSession
        
        student = Student.get_by_id(student_id)
        if not student:
            return """
            <div style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>❌ 學生不存在</h1>
                <p>無法找到指定的學生記錄</p>
                <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
            </div>
            """
        
        # 獲取學生的對話記錄（最近30次，包含會話資訊）
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()).limit(30))
        
        # 獲取會話統計
        try:
            all_sessions = list(ConversationSession.select().where(
                ConversationSession.student == student
            ).order_by(ConversationSession.session_start.desc()))
            
            active_session = student.get_active_session()
            session_count = len(all_sessions)
        except:
            all_sessions = []
            active_session = None
            session_count = 0
        
        # 統計資料
        total_messages = Message.select().where(Message.student_id == student_id).count()
        
        # 分析對話上下文
        try:
            context = Message.get_conversation_context(student, limit=10)
            recent_topics = context.get('recent_topics', [])
        except:
            recent_topics = []
        
        # 生成增強的學生詳細頁面
        detail_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{student.name} - 學生記憶對話記錄</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 0; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .student-header {{ text-align: center; }}
        .student-name {{ font-size: 2.5em; margin-bottom: 10px; }}
        .student-id {{ opacity: 0.8; font-size: 1.1em; }}
        .memory-badge {{ background: #e74c3c; color: white; padding: 4px 12px; border-radius: 15px; font-size: 0.8em; margin-left: 10px; }}
        .content-section {{ background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 20px 0; }}
        .section-title {{ font-size: 1.3em; font-weight: bold; margin-bottom: 20px; color: #495057; }}
        .stats-enhanced {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-item {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
        .stat-number {{ font-size: 1.8em; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #6c757d; font-size: 0.9em; margin-top: 5px; }}
        .memory-status {{ background: #e8f5e8; border: 1px solid #28a745; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .sessions-list {{ max-height: 300px; overflow-y: auto; margin-bottom: 20px; }}
        .session-item {{ background: #f8f9fa; margin-bottom: 10px; padding: 15px; border-radius: 8px; border-left: 4px solid #6f42c1; }}
        .session-meta {{ font-size: 0.8em; color: #6c757d; margin-bottom: 5px; }}
        .session-info {{ font-size: 0.9em; }}
        .topics-tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
        .topic-tag {{ background: #007bff; color: white; padding: 4px 12px; border-radius: 15px; font-size: 0.8em; }}
        .message-list {{ max-height: 500px; overflow-y: auto; }}
        .message-item {{ background: #f8f9fa; margin-bottom: 15px; padding: 15px; border-radius: 10px; }}
        .message-item.has-session {{ border-left: 4px solid #6f42c1; }}
        .message-meta {{ font-size: 0.8em; color: #6c757d; margin-bottom: 8px; }}
        .message-content {{ line-height: 1.5; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .back-button:hover {{ background: rgba(255,255,255,0.3); }}
        .action-buttons {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }}
        .btn {{ padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .btn-success {{ background: #28a745; color: white; }}
        .btn-purple {{ background: #6f42c1; color: white; }}
        .btn-info {{ background: #17a2b8; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <a href="/students" class="back-button">← 返回學生列表</a>
            <div class="student-header">
                <h1 class="student-name">{student.name} 
                    {'<span class="memory-badge">記憶功能</span>' if session_count > 0 else ''}
                </h1>
                <p class="student-id">學號: {getattr(student, 'student_id', '未設定')} | 註冊: {student.created_at.strftime('%Y年%m月%d日') if hasattr(student, 'created_at') and student.created_at else '未知'}</p>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- 增強統計區塊 -->
        <div class="content-section">
            <div class="section-title">📊 學習統計（記憶功能版）</div>
            <div class="stats-enhanced">
                <div class="stat-item">
                    <div class="stat-number">{total_messages}</div>
                    <div class="stat-label">總對話數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{session_count}</div>
                    <div class="stat-label">會話次數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{len(recent_topics)}</div>
                    <div class="stat-label">討論主題</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{(datetime.datetime.now() - student.last_active).days if hasattr(student, 'last_active') and student.last_active else '∞'}</div>
                    <div class="stat-label">天前活動</div>
                </div>
            </div>
            
            <!-- 記憶狀態 -->
            {'<div class="memory-status">🧠 <strong>記憶功能已啟用</strong> - AI能記住前幾輪對話，支援深入追問和連續討論</div>' if active_session else '<div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin-bottom: 20px;">💤 目前無活躍會話 - 下次對話時會自動開始新的記憶會話</div>'}
            
            <div class="action-buttons">
                <a href="/students/{student.id}/summary" class="btn btn-success">📋 學習建議</a>
                <a href="/admin/generate_history/{student.id}" class="btn btn-purple">📚 生成學習歷程</a>
                <a href="/student/{student.id}/history" class="btn btn-info">📖 查看學習歷程</a>
            </div>
        </div>
        
        <!-- 討論主題標籤 -->
        {f'''<div class="content-section">
            <div class="section-title">🏷️ 討論主題</div>
            <div class="topics-tags">
                {''.join([f'<span class="topic-tag">{topic}</span>' for topic in recent_topics[:10]])}
            </div>
        </div>''' if recent_topics else ''}
        
        <!-- 會話記錄 -->
        {f'''<div class="content-section">
            <div class="section-title">💬 對話會話記錄</div>
            <div class="sessions-list">
                {''.join([f'''<div class="session-item">
                    <div class="session-meta">
                        {'🟢 進行中' if session.is_active() else '🔴 已結束'} | 
                        開始: {session.session_start.strftime('%m月%d日 %H:%M')} | 
                        {'持續中' if session.is_active() else f'時長: {session.get_duration_minutes():.1f}分鐘'}
                    </div>
                    <div class="session-info">
                        會話ID: {session.id} | 訊息數: {session.message_count} | 
                        {f'主題提示: {session.topic_hint}' if session.topic_hint else '無主題標籤'}
                    </div>
                </div>''' for session in all_sessions[:5]])}
            </div>
        </div>''' if all_sessions else ''}
        
        <!-- 對話記錄 -->
        <div class="content-section">
            <div class="section-title">💬 最近對話記錄</div>
            <div class="message-list">
        """
        
        if messages:
            for message in messages:
                msg_type_icon = "👤" if message.source_type in ['line', 'student'] else "🤖"
                msg_time = message.timestamp.strftime('%m月%d日 %H:%M') if message.timestamp else '未知時間'
                
                # 檢查是否關聯到會話
                session_info = ""
                has_session_class = ""
                if hasattr(message, 'session') and message.session:
                    session_info = f" | 會話 #{message.session.id}"
                    has_session_class = " has-session"
                
                detail_html += f"""
                    <div class="message-item{has_session_class}">
                        <div class="message-meta">
                            {msg_type_icon} {msg_time} • {'學生' if message.source_type in ['line', 'student'] else 'AI助理'}{session_info}
                        </div>
                        <div class="message-content">{message.content[:400]}{'...' if len(message.content) > 400 else ''}</div>
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
            {f'<div style="margin-top: 15px; text-align: center; padding: 10px; background: #fff3cd; border-radius: 5px; font-size: 0.9em;">📋 顯示最近30條記錄，共有 {total_messages} 條對話，{session_count} 個會話</div>' if total_messages > 30 else ''}
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

# =================== 學習建議路由（保持向後相容）===================

@app.route('/students/<int:student_id>/summary')
def student_summary(student_id):
    """學生學習建議頁面（保持原有邏輯，但增加學習歷程連結）"""
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

        # 生成學習建議（使用簡化版）
        ai_suggestion = generate_learning_suggestion(student)

        # 生成建議頁面HTML（增強版）
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
        .notice {{ background: #e8f5e8; border: 1px solid #28a745; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-item {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-number {{ font-size: 1.5em; font-weight: bold; color: #007bff; }}
        .suggestion-content {{ background: #f8fafc; padding: 25px; border-radius: 10px; line-height: 1.7; white-space: pre-wrap; border-left: 4px solid #17a2b8; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .action-buttons {{ display: flex; gap: 10px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }}
        .btn {{ padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .btn-info {{ background: #17a2b8; color: white; }}
        .btn-purple {{ background: #6f42c1; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/students" class="back-button">← 返回學生列表</a>
        
        <div class="header">
            <div class="student-name">👤 {student.name}</div>
            <p>📊 個人學習建議（簡化版）</p>
        </div>
        
        <div class="notice">
            <strong>💡 升級提示：</strong> 現在可以生成更詳細的「學習歷程報告」，包含深度學習軌跡分析和個性化發展建議！
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
            <a href="/admin/generate_history/{student_id}" class="btn btn-purple">📚 生成詳細學習歷程</a>
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

# =================== 會話管理路由（新增）===================

@app.route('/admin/sessions')
def admin_sessions():
    """會話管理頁面"""
    try:
        from models import ConversationSession, manage_conversation_sessions
        
        # 執行會話清理
        cleanup_result = manage_conversation_sessions()
        
        # 獲取會話統計
        total_sessions = ConversationSession.select().count()
        active_sessions = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        ).count()
        
        # 獲取最近的會話
        recent_sessions = list(ConversationSession.select().order_by(
            ConversationSession.session_start.desc()
        ).limit(20))
        
        sessions_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💬 會話管理 - EMI 智能教學助理</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 0; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .page-title {{ text-align: center; font-size: 2.5em; margin-bottom: 10px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #6f42c1; }}
        .stat-label {{ color: #666; }}
        .sessions-list {{ background: white; border-radius: 15px; padding: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .session-item {{ background: #f8f9fa; margin-bottom: 15px; padding: 15px; border-radius: 8px; border-left: 4px solid #6f42c1; }}
        .session-active {{ border-left-color: #28a745; }}
        .session-meta {{ font-size: 0.9em; color: #666; margin-bottom: 8px; }}
        .session-info {{ font-weight: bold; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .cleanup-info {{ background: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <a href="/" class="back-button">← 返回首頁</a>
            <h1 class="page-title">💬 對話會話管理</h1>
            <p style="text-align: center; opacity: 0.9;">記憶功能會話追蹤和管理</p>
        </div>
    </div>
    
    <div class="container">
        <div class="cleanup-info">
            <strong>🔧 自動清理結果：</strong> 
            結束了 {cleanup_result.get('ended_sessions', 0)} 個非活躍會話，
            清理了 {cleanup_result.get('cleaned_sessions', 0)} 個舊會話記錄
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_sessions}</div>
                <div class="stat-label">總會話數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{active_sessions}</div>
                <div class="stat-label">活躍會話</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_sessions - active_sessions}</div>
                <div class="stat-label">已結束會話</div>
            </div>
        </div>
        
        <div class="sessions-list">
            <h3>最近會話記錄</h3>
        """
        
        for session in recent_sessions:
            status_class = "session-active" if session.is_active() else ""
            status_text = "🟢 進行中" if session.is_active() else "🔴 已結束"
            duration_text = "持續中" if session.is_active() else f"{session.get_duration_minutes():.1f}分鐘"
            
            sessions_html += f"""
            <div class="session-item {status_class}">
                <div class="session-meta">
                    {status_text} | 開始: {session.session_start.strftime('%Y-%m-%d %H:%M')} | 時長: {duration_text}
                </div>
                <div class="session-info">
                    學生: {session.student.name} | 會話ID: #{session.id} | 訊息數: {session.message_count}
                    {f' | 主題: {session.topic_hint}' if session.topic_hint else ''}
                </div>
            </div>
            """
        
        sessions_html += """
        </div>
    </div>
</body>
</html>
        """
        
        return sessions_html
        
    except Exception as e:
        logger.error(f"❌ 會話管理頁面錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>💬 會話管理</h1>
            <p style="color: #dc3545;">載入錯誤：{str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """

# =================== app.py 更新版 - 第4段結束 ===================

# =================== app.py 更新版 - 第5段開始 ===================

# =================== 系統工具路由（增強版）===================

@app.route('/health')
def health_check():
    """增強版系統健康檢查，包含記憶功能和學習歷程檢查"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory, manage_conversation_sessions
        
        # 檢查資料庫連線
        student_count = Student.select().count()
        message_count = Message.select().count()
        
        # 檢查記憶功能相關統計
        try:
            session_count = ConversationSession.select().count()
            active_sessions = ConversationSession.select().where(
                ConversationSession.session_end.is_null()
            ).count()
            history_count = LearningHistory.select().count()
        except:
            session_count = 0
            active_sessions = 0
            history_count = 0
        
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
        
        # 執行會話清理檢查
        try:
            cleanup_result = manage_conversation_sessions()
            cleanup_status = f"✅ 正常 (清理了{cleanup_result.get('cleaned_sessions', 0)}個舊會話)"
        except Exception as e:
            cleanup_status = f"⚠️ 清理異常: {str(e)}"
        
        health_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系統健康檢查 - EMI 智能教學助理（記憶功能版）</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 0; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .page-title {{ text-align: center; font-size: 2.5em; margin-bottom: 10px; }}
        .page-subtitle {{ text-align: center; opacity: 0.9; }}
        .version-badge {{ background: #e74c3c; color: white; padding: 4px 12px; border-radius: 15px; font-size: 0.8em; margin-left: 10px; }}
        .health-card {{ background: white; border-radius: 15px; padding: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 20px 0; }}
        .status-item {{ display: flex; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid #eee; }}
        .status-item:last-child {{ border-bottom: none; }}
        .status-label {{ font-weight: bold; }}
        .status-value {{ padding: 5px 10px; border-radius: 5px; font-size: 0.9em; }}
        .status-ok {{ background: #d4edda; color: #155724; }}
        .status-error {{ background: #f8d7da; color: #721c24; }}
        .status-info {{ background: #d1ecf1; color: #0c5460; }}
        .status-warning {{ background: #fff3cd; color: #856404; }}
        .status-new {{ background: #e7e3ff; color: #6f42c1; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .back-button:hover {{ background: rgba(255,255,255,0.3); }}
        .refresh-btn {{ background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
        .refresh-btn:hover {{ background: #0056b3; }}
        .new-features {{ background: #e8f5e8; border: 1px solid #28a745; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <a href="/" class="back-button">← 返回首頁</a>
            <h1 class="page-title">🔍 系統健康檢查 <span class="version-badge">記憶功能版</span></h1>
            <p class="page-subtitle">增強版系統狀態監控，包含記憶功能和學習歷程檢查</p>
        </div>
    </div>
    
    <div class="container">
        <!-- 新功能狀態 -->
        <div class="new-features">
            <h3 style="color: #28a745; margin-bottom: 15px;">🎉 新功能狀態檢查</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div style="text-align: center;">
                    <div style="font-size: 1.5em; font-weight: bold; color: #6f42c1;">{session_count}</div>
                    <div style="font-size: 0.9em;">總對話會話</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.5em; font-weight: bold; color: #28a745;">{active_sessions}</div>
                    <div style="font-size: 0.9em;">活躍記憶會話</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.5em; font-weight: bold; color: #e74c3c;">{history_count}</div>
                    <div style="font-size: 0.9em;">學習歷程記錄</div>
                </div>
            </div>
        </div>
        
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
                <span class="status-label">AI 模型</span>
                <span class="status-value status-info">{current_model}</span>
            </div>
            <div class="status-item">
                <span class="status-label">會話管理</span>
                <span class="status-value {'status-ok' if 'cleared' in cleanup_status else 'status-warning'}">{cleanup_status}</span>
            </div>
        </div>
        
        <div class="health-card">
            <h3>📊 資料統計</h3>
            <div class="status-item">
                <span class="status-label">註冊學生總數</span>
                <span class="status-value status-info">{student_count} 人</span>
            </div>
            <div class="status-item">
                <span class="status-label">已完成註冊</span>
                <span class="status-value status-ok">{completed_registration} 人</span>
            </div>
            <div class="status-item">
                <span class="status-label">待完成註冊</span>
                <span class="status-value {'status-warning' if need_registration > 0 else 'status-ok'}">{need_registration} 人</span>
            </div>
            <div class="status-item">
                <span class="status-label">對話訊息總數</span>
                <span class="status-value status-info">{message_count} 則</span>
            </div>
            <div class="status-item">
                <span class="status-label">記憶會話總數</span>
                <span class="status-value status-new">{session_count} 個</span>
            </div>
            <div class="status-item">
                <span class="status-label">學習歷程記錄</span>
                <span class="status-value status-new">{history_count} 筆</span>
            </div>
        </div>
        
        <div class="health-card">
            <h3>⚙️ 系統操作</h3>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button class="refresh-btn" onclick="location.reload()">🔄 重新檢查</button>
                <button class="refresh-btn" onclick="window.open('/admin', '_blank')" style="background: #28a745;">🎛️ 管理控制台</button>
                <button class="refresh-btn" onclick="window.open('/export', '_blank')" style="background: #fd7e14;">📁 資料匯出</button>
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

@app.route('/debug_db')
def debug_db():
    """資料庫除錯資訊（增強版）"""
    if not DEBUG_MODE:
        abort(404)
    
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        # 基本統計
        student_count = Student.select().count()
        message_count = Message.select().count()
        
        # 記憶功能統計
        session_count = ConversationSession.select().count()
        active_sessions = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        ).count()
        history_count = LearningHistory.select().count()
        
        # 最近的會話資訊
        recent_sessions = list(ConversationSession.select().order_by(
            ConversationSession.session_start.desc()
        ).limit(5))
        
        # 最近的學習歷程
        recent_histories = list(LearningHistory.select().order_by(
            LearningHistory.generated_at.desc()
        ).limit(3))
        
        debug_info = {
            'database_status': 'OK',
            'tables': {
                'students': student_count,
                'messages': message_count,
                'conversation_sessions': session_count,
                'learning_histories': history_count
            },
            'memory_features': {
                'total_sessions': session_count,
                'active_sessions': active_sessions,
                'completed_sessions': session_count - active_sessions
            },
            'recent_sessions': [
                {
                    'id': s.id,
                    'student_id': s.student.id if s.student else None,
                    'started': s.session_start.isoformat() if s.session_start else None,
                    'ended': s.session_end.isoformat() if s.session_end else None,
                    'message_count': s.message_count,
                    'is_active': s.session_end is None
                } for s in recent_sessions
            ],
            'recent_histories': [
                {
                    'id': h.id,
                    'student_id': h.student.id if h.student else None,
                    'generated_at': h.generated_at.isoformat() if h.generated_at else None,
                    'summary_preview': (h.summary or '')[:100] + '...' if h.summary and len(h.summary) > 100 else h.summary
                } for h in recent_histories
            ],
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"Debug DB error: {str(e)}")
        return jsonify({
            'error': str(e),
            'database_status': 'ERROR'
        }), 500

@app.route('/export')
def export_data():
    """資料匯出頁面（增強版）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        # 基本統計
        student_count = Student.select().count()
        message_count = Message.select().count()
        session_count = ConversationSession.select().count()
        history_count = LearningHistory.select().count()
        
        export_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>資料匯出 - EMI 智能教學助理（記憶功能版）</title>
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
        .export-btn.new {{ background: #6f42c1; }}
        .export-btn.new:hover {{ background: #5a32a3; }}
        .back-button {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
        .back-button:hover {{ background: rgba(255,255,255,0.3); }}
        .new-badge {{ background: #dc3545; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7em; margin-left: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <a href="/" class="back-button">← 返回首頁</a>
            <h1 class="page-title">📁 資料匯出</h1>
            <p class="page-subtitle">匯出系統資料進行分析或備份（含記憶功能數據）</p>
        </div>
    </div>
    
    <div class="container">
        <div class="export-card">
            <h3>📊 基礎資料匯出</h3>
            
            <div class="export-item">
                <div class="export-info">
                    <div class="export-title">學生名單</div>
                    <div class="export-desc">包含學生基本資訊、註冊狀態、班級等</div>
                    <div class="export-count">總計: {student_count} 位學生</div>
                </div>
                <a href="/download/students" class="export-btn">下載 TSV</a>
            </div>
            
            <div class="export-item">
                <div class="export-info">
                    <div class="export-title">對話記錄</div>
                    <div class="export-desc">完整的師生對話記錄，包含時間戳記</div>
                    <div class="export-count">總計: {message_count} 則訊息</div>
                </div>
                <a href="/download/messages" class="export-btn">下載 TSV</a>
            </div>
        </div>
        
        <div class="export-card">
            <h3>🧠 記憶功能資料匯出 <span class="new-badge">NEW</span></h3>
            
            <div class="export-item">
                <div class="export-info">
                    <div class="export-title">對話會話記錄</div>
                    <div class="export-desc">連續對話會話資料，包含會話時長、訊息數量等</div>
                    <div class="export-count">總計: {session_count} 個會話</div>
                </div>
                <a href="/download/sessions" class="export-btn new">下載 TSV</a>
            </div>
            
            <div class="export-item">
                <div class="export-info">
                    <div class="export-title">學習歷程記錄</div>
                    <div class="export-desc">AI生成的學習歷程分析，包含討論主題、學習軌跡等</div>
                    <div class="export-count">總計: {history_count} 筆記錄</div>
                </div>
                <a href="/download/histories" class="export-btn new">下載 TSV</a>
            </div>
        </div>
        
        <div class="export-card">
            <h3>📈 進階分析匯出</h3>
            
            <div class="export-item">
                <div class="export-info">
                    <div class="export-title">完整分析報告</div>
                    <div class="export-desc">包含所有資料表的完整匯出，適合深度分析</div>
                    <div class="export-count">包含: 學生、對話、會話、歷程數據</div>
                </div>
                <a href="/download/full_analysis" class="export-btn new">下載完整報告</a>
            </div>
        </div>
        
        <div class="export-card">
            <h3>⚠️ 匯出說明</h3>
            <ul>
                <li>所有匯出檔案均為 TSV 格式（Tab-Separated Values），可用 Excel 或試算表軟體開啟</li>
                <li>包含完整的 UTF-8 編碼，支援中文字符</li>
                <li>時間格式為 ISO 8601 標準（YYYY-MM-DD HH:MM:SS）</li>
                <li>記憶功能相關資料包含對話上下文和 AI 分析結果</li>
                <li>學習歷程為 JSON 格式，包含豐富的結構化學習資料</li>
                <li>敏感資訊已適當處理，確保隱私安全</li>
            </ul>
        </div>
    </div>
</body>
</html>
        """
        
        return export_html
        
    except Exception as e:
        logger.error(f"Export page error: {str(e)}")
        return f"匯出頁面錯誤: {str(e)}", 500

# =================== API 路由（增強版）===================

@app.route('/api/conversations/<int:student_id>')
def api_get_conversations(student_id):
    """取得學生的對話會話資料 API"""
    try:
        from models import Student, ConversationSession, Message
        
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
                'duration_minutes': session.duration_minutes,
                'message_count': session.message_count,
                'is_active': session.session_end is None,
                'context_summary': session.context_summary,
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

@app.route('/api/learning_history/<int:student_id>')
def api_get_learning_history(student_id):
    """取得學生的學習歷程資料 API"""
    try:
        from models import Student, LearningHistory
        
        # 檢查學生是否存在
        try:
            student = Student.get_by_id(student_id)
        except Student.DoesNotExist:
            return jsonify({'error': 'Student not found'}), 404
        
        # 取得學習歷程記錄
        histories = list(LearningHistory.select().where(
            LearningHistory.student == student
        ).order_by(LearningHistory.generated_at.desc()))
        
        history_data = []
        for history in histories:
            try:
                analysis_data = json.loads(history.analysis_data) if history.analysis_data else {}
            except:
                analysis_data = {}
            
            history_data.append({
                'id': history.id,
                'generated_at': history.generated_at.isoformat() if history.generated_at else None,
                'summary': history.summary,
                'learning_topics': history.learning_topics,
                'version': history.version,
                'analysis_data': analysis_data
            })
        
        return jsonify({
            'student_id': student_id,
            'student_name': student.name,
            'total_histories': len(history_data),
            'histories': history_data
        })
        
    except Exception as e:
        logger.error(f"API learning history error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """系統統計資料 API（增強版）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        total_sessions = ConversationSession.select().count()
        total_histories = LearningHistory.select().count()
        
        # 記憶功能統計
        active_sessions = ConversationSession.select().where(
            ConversationSession.session_end.is_null()
        ).count()
        
        # 今日統計
        today = datetime.date.today()
        today_messages = Message.select().where(
            Message.timestamp >= today
        ).count()
        
        today_sessions = ConversationSession.select().where(
            ConversationSession.session_start >= today
        ).count()
        
        # 最活躍學生
        from models import db
        active_students = list(db.execute_sql("""
            SELECT s.id, s.name, COUNT(m.id) as message_count,
                   COUNT(DISTINCT cs.id) as session_count
            FROM student s
            LEFT JOIN message m ON s.id = m.student_id
            LEFT JOIN conversationsession cs ON s.id = cs.student_id
            WHERE s.registration_step = 0
            GROUP BY s.id, s.name
            ORDER BY message_count DESC
            LIMIT 10
        """).fetchall())
        
        return jsonify({
            'overview': {
                'total_students': total_students,
                'total_messages': total_messages,
                'total_sessions': total_sessions,
                'total_histories': total_histories,
                'active_sessions': active_sessions
            },
            'today': {
                'messages': today_messages,
                'sessions': today_sessions
            },
            'top_students': [
                {
                    'id': row[0],
                    'name': row[1],
                    'message_count': row[2],
                    'session_count': row[3]
                } for row in active_students
            ],
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =================== 錯誤處理（保持原有功能）===================

@app.errorhandler(404)
def not_found(error):
    return "頁面不存在", 404

@app.errorhandler(500)
def internal_error(error):
    return "伺服器內部錯誤", 500

# =================== 系統啟動配置（增強版）===================

if __name__ == '__main__':
    try:
        # 初始化資料庫和記憶功能
        logger.info("正在初始化 EMI 智能教學助理系統（記憶功能版）...")
        
        from models import initialize_database, migrate_database
        
        # 執行資料庫初始化和遷移
        initialize_database()
        migrate_database()
        
        # 清理舊會話
        from models import manage_conversation_sessions
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
        
        logger.info(f"✅ EMI 智能教學助理系統（記憶功能版）啟動成功！")
        logger.info(f"🌐 監聽端口: {port}")
        logger.info(f"🧠 記憶功能: 已啟用")
        logger.info(f"📚 學習歷程: 已啟用")
        logger.info(f"🔧 除錯模式: {'開啟' if debug_mode else '關閉'}")
        logger.info(f"🤖 AI 模型: {CURRENT_MODEL}")
        
        if debug_mode:
            logger.info("=" * 50)
            logger.info("🔍 除錯資訊:")
            logger.info(f"   - 健康檢查: http://localhost:{port}/health")
            logger.info(f"   - 資料庫除錯: http://localhost:{port}/debug_db")
            logger.info(f"   - 資料匯出: http://localhost:{port}/export")
            logger.info(f"   - 管理控制台: http://localhost:{port}/admin")
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

# =================== app.py 更新版 - 第5段結束 ===================

"""
EMI 智能教學助理系統 - app.py（記憶功能版）
版本: 4.1.0 (Memory & Learning History Enhanced)
更新日期: 2025年6月29日

主要新增功能:
✅ 記憶功能 - 支援連續對話上下文記憶
✅ 學習歷程 - AI生成學習軌跡分析
✅ 會話管理 - 自動追蹤和清理對話會話
✅ 增強統計 - 包含記憶功能相關數據
✅ API 強化 - 新增會話和歷程 API 端點
✅ 管理優化 - 後台觸發學習歷程生成
✅ 資料匯出 - 支援記憶功能數據匯出

系統架構:
- Flask Web 框架
- Peewee ORM 資料庫管理
- LINE Bot API 整合
- Google Gemini AI 模型
- 記憶功能會話追蹤
- 學習歷程分析系統

相容性:
- 完全向後相容舊版功能
- 自動資料庫遷移
- 智慧預設值處理
- 錯誤恢復機制

維護說明:
- 自動會話清理（24小時）
- 學習歷程版本管理
- 系統健康監控
- 詳細日誌記錄
"""
