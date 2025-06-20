# utils.py - 工具函數
import json
import datetime
import logging
from flask import current_app
from models import db, Student, Message, Analysis, AIResponse

logger = logging.getLogger(__name__)

def ensure_db_connection():
    """確保資料庫連接"""
    if db.is_closed():
        db.connect()

def analyze_message_type(content):
    """使用 Gemini 分析訊息類型"""
    gemini_model = current_app.config.get('gemini_model')
    if not gemini_model:
        return "text"
    
    try:
        prompt = f"""
        分析以下訊息的類型，回答必須是以下其中一個：
        - question: 如果是問題
        - statement: 如果是陳述或分享
        
        訊息: "{content}"
        
        只回答類型，不需要其他說明。
        """
        
        response = gemini_model.generate_content(prompt)
        result = response.text.strip().lower()
        
        if result in ['question', 'statement']:
            return result
        return 'text'
    except:
        return 'text'

def generate_ai_response(user_id, message):
    """生成個人化AI回應"""
    gemini_model = current_app.config.get('gemini_model')
    if not gemini_model:
        return "感謝你的訊息！我會記錄下來。"
    
    try:
        # 獲取學生資訊
        ensure_db_connection()
        student = Student.get(Student.user_id == user_id)
        
        # 獲取最近的對話記錄
        recent_messages = Message.select().where(
            Message.user_id == user_id
        ).order_by(Message.timestamp.desc()).limit(5)
        
        context = "\n".join([f"- {msg.content}" for msg in recent_messages])
        
        prompt = f"""
        你是一位友善的AI助教，請回應學生「{student.student_name}」的訊息。
        
        學生說：「{message}」
        
        最近對話記錄：
        {context}
        
        請用友善、鼓勵的語氣回應，如果是問題就給予解答，如果是分享就給予肯定。
        回應限制在100字以內。
        """
        
        response = gemini_model.generate_content(prompt)
        ai_response = response.text.strip()
        
        # 記錄AI回應
        AIResponse.create(
            user_id=user_id,
            question=message,
            response=ai_response
        )
        
        return ai_response
    except Exception as e:
        logger.error(f"Gemini API錯誤: {e}")
        return "謝謝你的分享！我已經記錄下來了。"

def analyze_student_patterns(user_id):
    """分析學生的提問模式和興趣"""
    gemini_model = current_app.config.get('gemini_model')
    if not gemini_model:
        return None
    
    try:
        ensure_db_connection()
        
        # 獲取所有訊息
        messages = Message.select().where(
            Message.user_id == user_id
        ).order_by(Message.timestamp)
        
        if not messages:
            return None
        
        # 準備分析內容
        all_messages = "\n".join([f"{i+1}. {msg.content}" for i, msg in enumerate(messages)])
        
        prompt = f"""
        分析以下學生的所有發言記錄，找出：
        1. 最常問的問題類型（例如：技術問題、概念理解、應用案例等）
        2. 主要興趣領域
        3. 學習風格（主動提問、被動聆聽、喜歡討論等）
        4. 需要加強的地方
        
        發言記錄：
        {all_messages}
        
        請用JSON格式回答，包含以下欄位：
        {{
            "frequent_topics": ["主題1", "主題2"],
            "question_types": ["類型1", "類型2"],
            "learning_style": "描述",
            "interests": ["興趣1", "興趣2"],
            "suggestions": "給學生的建議"
        }}
        """
        
        response = gemini_model.generate_content(prompt)
        
        # 解析JSON
        try:
            analysis_result = json.loads(response.text)
        except:
            # 如果無法解析JSON，使用預設格式
            analysis_result = {
                "frequent_topics": ["待分析"],
                "question_types": ["待分析"],
                "learning_style": response.text[:100],
                "interests": ["待分析"],
                "suggestions": "持續參與課程討論"
            }
        
        # 儲存分析結果
        Analysis.create(
            user_id=user_id,
            analysis_type='question_pattern',
            content=json.dumps(analysis_result, ensure_ascii=False)
        )
        
        return analysis_result
    except Exception as e:
        logger.error(f"分析錯誤: {e}")
        return None

def get_student_statistics(user_id):
    """獲取學生統計數據"""
    ensure_db_connection()
    
    # 基本統計
    total_messages = Message.select().where(Message.user_id == user_id).count()
    questions = Message.select().where(
        (Message.user_id == user_id) & (Message.message_type == 'question')
    ).count()
    
    # 每日統計
    daily_stats = {}
    messages = Message.select().where(Message.user_id == user_id)
    
    for msg in messages:
        date = msg.timestamp.date()
        if date not in daily_stats:
            daily_stats[date] = 0
        daily_stats[date] += 1
    
    # 最近分析
    latest_analysis = Analysis.select().where(
        (Analysis.user_id == user_id) & (Analysis.analysis_type == 'question_pattern')
    ).order_by(Analysis.created_at.desc()).first()
    
    pattern_analysis = None
    if latest_analysis:
        try:
            pattern_analysis = json.loads(latest_analysis.content)
        except:
            pass
    
    return {
        'total_messages': total_messages,
        'total_questions': questions,
        'daily_stats': daily_stats,
        'pattern_analysis': pattern_analysis,
        'engagement_rate': round((questions / max(total_messages, 1)) * 100, 1)
    }

def init_demo_data():
    """初始化虛擬學生示範數據"""
    ensure_db_connection()
    
    # 清除現有虛擬數據
    Message.delete().where(
        Message.user_id.in_(
            Student.select(Student.user_id).where(Student.is_demo == 1)
        )
    ).execute()
    Student.delete().where(Student.is_demo == 1).execute()
    
    # 虛擬學生資料
    demo_students = [
        {
            'user_id': 'demo_alice',
            'line_name': '【虛擬】王小美',
            'student_name': 'Alice Wang',
            'messages': [
                ("老師，什麼是機器學習？", "question"),
                ("我覺得深度學習很有趣", "statement"),
                ("請問神經網路和大腦有什麼關係？", "question"),
                ("今天的課程很精彩", "statement"),
                ("如何開始學習AI？有推薦的資源嗎？", "question"),
            ]
        },
        {
            'user_id': 'demo_bob',
            'line_name': '【虛擬】陳大明',
            'student_name': 'Bob Chen',
            'messages': [
                ("AI會取代人類的工作嗎？", "question"),
                ("我想了解更多關於自然語言處理", "statement"),
                ("ChatGPT是怎麼運作的？", "question"),
                ("最近在練習寫Python", "statement"),
                ("機器學習需要很強的數學嗎？", "question"),
            ]
        },
        {
            'user_id': 'demo_carol',
            'line_name': '【虛擬】林小華',
            'student_name': 'Carol Lin',
            'messages': [
                ("謝謝老師的講解", "statement"),
                ("可以多講一些實際應用的例子嗎？", "question"),
                ("AI在醫療領域的應用", "statement"),
                ("如何評估模型的好壞？", "question"),
            ]
        }
    ]
    
    # 建立虛擬學生和訊息
    base_time = datetime.datetime.now() - datetime.timedelta(days=7)
    
    for student_data in demo_students:
        # 建立學生
        student = Student.create(
            user_id=student_data['user_id'],
            line_name=student_data['line_name'],
            student_name=student_data['student_name'],
            is_demo=1,
            total_messages=len(student_data['messages'])
        )
        
        # 建立訊息記錄
        for i, (content, msg_type) in enumerate(student_data['messages']):
            timestamp = base_time + datetime.timedelta(hours=i*12)
            Message.create(
                user_id=student_data['user_id'],
                content=content,
                message_type=msg_type,
                engagement_type='group',
                timestamp=timestamp
            )
    
    logger.info("虛擬學生數據初始化完成")
