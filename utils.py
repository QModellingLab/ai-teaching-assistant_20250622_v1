import os
import json
import datetime
import logging
import random
import google.generativeai as genai
from models import Student, Message, Analysis, db

# 設定日誌
logger = logging.getLogger(__name__)

# 初始化 Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    logger.info("Gemini AI 已初始化")
else:
    model = None
    logger.warning("Gemini API key not found")

def get_ai_response(query, student_id=None):
    """取得 AI 回應"""
    try:
        if not model:
            return "AI 服務暫時無法使用，請稍後再試。"
        
        # 取得學生資訊
        student_context = ""
        if student_id:
            try:
                student = Student.get_by_id(student_id)
                student_context = f"""
學生資訊：
- 姓名：{student.name}
- 參與度：{student.participation_rate}%
- 提問率：{student.question_rate}%
- 學習風格：{student.learning_style or '待分析'}
"""
            except:
                pass
        
        # 構建提示詞
        prompt = f"""
你是一個專業的雙語教學AI助理，專門協助EMI（English as Medium of Instruction）課程。

任務：回答學生問題，提供清晰、準確且有教育意義的回應。

指導原則：
1. 使用中英文雙語回應（以中文為主，關鍵術語提供英文）
2. 提供簡潔但完整的答案
3. 鼓勵學生進一步思考
4. 適合大學程度的內容

{student_context}

學生問題：{query}

請提供有幫助的回應：
"""
        
        # 取得 AI 回應
        response = model.generate_content(prompt)
        
        if response.text:
            return response.text.strip()
        else:
            return "抱歉，我現在無法回應這個問題。請稍後再試或重新表達您的問題。"
            
    except Exception as e:
        logger.error(f"AI 回應錯誤: {e}")
        return "抱歉，處理您的問題時發生錯誤。請稍後再試。"

def analyze_student_patterns(student_id):
    """分析學生學習模式"""
    try:
        if not model:
            return None
            
        student = Student.get_by_id(student_id)
        
        # 取得最近的訊息
        recent_messages = Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(20)
        
        if not recent_messages:
            return None
        
        # 準備分析資料
        messages_text = []
        questions = []
        
        for msg in recent_messages:
            messages_text.append(msg.content)
            if msg.message_type == 'question':
                questions.append(msg.content)
        
        # 構建分析提示詞
        analysis_prompt = f"""
作為教育數據分析專家，請分析以下學生的學習模式：

學生基本資料：
- 姓名：{student.name}
- 總發言數：{student.message_count}
- 提問次數：{student.question_count}
- 參與度：{student.participation_rate}%

近期訊息內容：
{chr(10).join(messages_text[:10])}

主要提問：
{chr(10).join(questions[:5])}

請提供200字左右的學習模式分析，包含：
1. 學習風格特點
2. 參與程度評估
3. 學習建議
4. 需要關注的方面

分析結果：
"""
        
        response = model.generate_content(analysis_prompt)
        
        if response.text:
            return response.text.strip()
        else:
            return None
            
    except Exception as e:
        logger.error(f"學生模式分析錯誤: {e}")
        return None

def update_student_stats(student_id):
    """更新學生統計資料"""
    try:
        student = Student.get_by_id(student_id)
        student.update_stats()
        logger.info(f"更新學生統計: {student.name}")
        
    except Exception as e:
        logger.error(f"更新統計錯誤: {e}")

def create_sample_data():
    """建立範例資料"""
    try:
        # 建立範例學生
        sample_students = [
            {
                'name': '王小明',
                'line_user_id': 'sample_user_001',
                'message_count': 25,
                'question_count': 8,
                'participation_rate': 75.5,
                'question_rate': 32.0,
                'learning_style': '主動探索型'
            },
            {
                'name': '李美華',
                'line_user_id': 'sample_user_002', 
                'message_count': 18,
                'question_count': 12,
                'participation_rate': 68.2,
                'question_rate': 66.7,
                'learning_style': '問題導向型'
            },
            {
                'name': 'John Smith',
                'line_user_id': 'sample_user_003',
                'message_count': 32,
                'question_count': 5,
                'participation_rate': 82.3,
                'question_rate': 15.6,
                'learning_style': '實作導向型'
            }
        ]
        
        for student_data in sample_students:
            try:
                # 檢查是否已存在
                existing = Student.select().where(
                    Student.line_user_id == student_data['line_user_id']
                ).first()
                
                if not existing:
                    student = Student.create(
                        name=student_data['name'],
                        line_user_id=student_data['line_user_id'],
                        message_count=student_data['message_count'],
                        question_count=student_data['question_count'],
                        participation_rate=student_data['participation_rate'],
                        question_rate=student_data['question_rate'],
                        learning_style=student_data['learning_style'],
                        created_at=datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 30)),
                        last_active=datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 48))
                    )
                    
                    # 建立範例訊息
                    create_sample_messages(student)
                    
                    logger.info(f"建立範例學生: {student.name}")
                    
            except Exception as e:
                logger.error(f"建立範例學生錯誤: {e}")
                
    except Exception as e:
        logger.error(f"建立範例資料錯誤: {e}")

def create_sample_messages(student):
    """為學生建立範例訊息"""
    try:
        sample_messages = [
            {'content': '老師好，請問今天的作業要怎麼做？', 'type': 'question'},
            {'content': '我覺得這個概念很有趣！', 'type': 'statement'},
            {'content': '可以再解釋一下嗎？', 'type': 'question'},
            {'content': '謝謝老師的說明', 'type': 'statement'},
            {'content': 'What is the difference between AI and ML?', 'type': 'question'},
        ]
        
        for i, msg_data in enumerate(sample_messages):
            if i < student.message_count:
                Message.create(
                    student=student,
                    content=msg_data['content'],
                    message_type=msg_data['type'],
                    timestamp=datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 72)),
                    source_type='user'
                )
                
    except Exception as e:
        logger.error(f"建立範例訊息錯誤: {e}")

def cleanup_database():
    """清理資料庫"""
    try:
        # 清理超過 90 天的舊資料
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=90)
        
        old_messages = Message.select().where(Message.timestamp < cutoff_date)
        deleted_count = 0
        
        for message in old_messages:
            message.delete_instance()
            deleted_count += 1
            
        logger.info(f"清理了 {deleted_count} 筆舊訊息")
        
    except Exception as e:
        logger.error(f"資料庫清理錯誤: {e}")

def validate_environment():
    """驗證環境變數"""
    required_vars = [
        'GEMINI_API_KEY',
        'CHANNEL_ACCESS_TOKEN', 
        'CHANNEL_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"缺少環境變數: {', '.join(missing_vars)}")
        return False
    
    logger.info("環境變數驗證通過")
    return True

def get_system_status():
    """取得系統狀態"""
    try:
        status = {
            'database': 'connected' if not db.is_closed() else 'disconnected',
            'ai_service': 'available' if model else 'unavailable',
            'total_students': Student.select().count(),
            'total_messages': Message.select().count(),
            'last_update': datetime.datetime.now().isoformat()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"取得系統狀態錯誤: {e}")
        return {'error': str(e)}

def safe_database_operation(operation):
    """安全的資料庫操作"""
    try:
        if db.is_closed():
            db.connect()
        
        result = operation()
        
        return result
        
    except Exception as e:
        logger.error(f"資料庫操作錯誤: {e}")
        return None
    finally:
        if not db.is_closed():
            db.close()

# 初始化檢查
def initialize_utils():
    """初始化工具模組"""
    logger.info("初始化 utils 模組...")
    
    # 驗證環境
    if not validate_environment():
        logger.warning("環境變數檢查未通過，部分功能可能無法使用")
    
    logger.info("Utils 模組初始化完成")

# 自動執行初始化
initialize_utils()
