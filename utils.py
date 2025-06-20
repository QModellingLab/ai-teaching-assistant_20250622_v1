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
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        logger.info("✅ Gemini AI 已成功初始化")
    except Exception as e:
        model = None
        logger.error(f"❌ Gemini AI 初始化失敗: {e}")
else:
    model = None
    logger.warning("⚠️ Gemini API key not found")

def get_ai_response(query, student_id=None):
    """取得 AI 回應"""
    try:
        if not model:
            logger.error("❌ AI 模型未初始化")
            return "抱歉，AI 服務目前無法使用。請檢查 API 設定。"
        
        if not query or len(query.strip()) == 0:
            return "請提供您的問題，我很樂意為您解答！"
        
        # 取得學生資訊
        student_context = ""
        if student_id:
            try:
                student = Student.get_by_id(student_id)
                student_context = f"""
學生背景：
- 姓名：{student.name}
- 參與度：{student.participation_rate}%
- 提問率：{student.question_rate}%
- 學習風格：{student.learning_style or '分析中'}
"""
            except Exception as e:
                logger.warning(f"無法取得學生資訊: {e}")
        
        # 構建提示詞
        prompt = f"""
你是一個專業的雙語教學AI助理，專門協助EMI（English as Medium of Instruction）課程學習。

身份：友善、專業、有耐心的教學助理
語言：主要使用繁體中文回應，必要時提供英文術語
風格：簡潔明瞭、具有教育意義

任務：回答學生的問題，提供準確且有幫助的學習指導。

回應原則：
1. 使用友善、鼓勵的語調
2. 提供清晰、準確的解答
3. 適當時給出學習建議
4. 回應長度控制在 200 字以內
5. 如果是英文問題，可以用中英雙語回應

{student_context}

學生問題：{query}

請提供有幫助的回應：
"""
        
        logger.info(f"🤖 正在為學生生成 AI 回應...")
        
        # 取得 AI 回應
        response = model.generate_content(prompt)
        
        if response and response.text:
            ai_response = response.text.strip()
            logger.info(f"✅ AI 回應成功生成，長度: {len(ai_response)} 字")
            return ai_response
        else:
            logger.error("❌ AI 回應為空")
            return "抱歉，我現在無法生成適當的回應。請稍後再試或重新表達您的問題。"
            
    except Exception as e:
        logger.error(f"❌ AI 回應生成錯誤: {str(e)}")
        return f"抱歉，處理您的問題時發生錯誤：{str(e)[:100]}。請稍後再試。"

def analyze_student_patterns(student_id):
    """分析學生學習模式"""
    try:
        if not model:
            logger.warning("⚠️ AI 模型未初始化，無法進行學習模式分析")
            return None
            
        student = Student.get_by_id(student_id)
        
        # 取得最近的訊息
        recent_messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(20))
        
        if not recent_messages:
            return "該學生尚無足夠的互動記錄進行分析。"
        
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

近期互動內容（最多10則）：
{chr(10).join(messages_text[:10])}

主要提問內容（最多5則）：
{chr(10).join(questions[:5]) if questions else "尚無提問記錄"}

請提供150-200字的學習模式分析，包含：
1. 學習風格特點（主動/被動、探索型/實作型等）
2. 參與程度評估
3. 具體學習建議
4. 需要教師關注的方面

分析結果：
"""
        
        response = model.generate_content(analysis_prompt)
        
        if response and response.text:
            logger.info(f"✅ 學生學習模式分析完成: {student.name}")
            return response.text.strip()
        else:
            logger.error("❌ 學習模式分析回應為空")
            return None
            
    except Exception as e:
        logger.error(f"❌ 學生模式分析錯誤: {e}")
        return None

def update_student_stats(student_id):
    """更新學生統計資料"""
    try:
        student = Student.get_by_id(student_id)
        student.update_stats()
        logger.info(f"✅ 更新學生統計: {student.name}")
        
    except Exception as e:
        logger.error(f"❌ 更新統計錯誤: {e}")

def create_sample_data():
    """建立範例資料 - 明確標示為虛擬學生"""
    try:
        # 建立範例學生 - 加上 [DEMO] 前綴
        sample_students = [
            {
                'name': '[DEMO] 王小明',
                'line_user_id': 'demo_student_001',
                'message_count': 25,
                'question_count': 8,
                'participation_rate': 75.5,
                'question_rate': 32.0,
                'learning_style': '主動探索型',
                'notes': '這是系統演示用的虛擬學生資料'
            },
            {
                'name': '[DEMO] 李美華',
                'line_user_id': 'demo_student_002', 
                'message_count': 18,
                'question_count': 12,
                'participation_rate': 68.2,
                'question_rate': 66.7,
                'learning_style': '問題導向型',
                'notes': '這是系統演示用的虛擬學生資料'
            },
            {
                'name': '[DEMO] John Smith',
                'line_user_id': 'demo_student_003',
                'message_count': 32,
                'question_count': 5,
                'participation_rate': 82.3,
                'question_rate': 15.6,
                'learning_style': '實作導向型',
                'notes': '這是系統演示用的虛擬學生資料'
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
                        notes=student_data['notes'],
                        created_at=datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 30)),
                        last_active=datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 48))
                    )
                    
                    # 建立範例訊息
                    create_sample_messages(student)
                    
                    logger.info(f"✅ 建立演示學生: {student.name}")
                    
            except Exception as e:
                logger.error(f"❌ 建立演示學生錯誤: {e}")
                
    except Exception as e:
        logger.error(f"❌ 建立演示資料錯誤: {e}")

def create_sample_messages(student):
    """為演示學生建立範例訊息"""
    try:
        sample_messages = [
            {'content': '老師好，請問今天的作業要怎麼做？', 'type': 'question'},
            {'content': '我覺得這個概念很有趣！', 'type': 'statement'},
            {'content': '可以再解釋一下 machine learning 嗎？', 'type': 'question'},
            {'content': '謝謝老師的說明，我明白了', 'type': 'statement'},
            {'content': 'What is the difference between AI and ML?', 'type': 'question'},
            {'content': '這個例子很清楚！', 'type': 'statement'},
            {'content': '請問有推薦的參考書籍嗎？', 'type': 'question'},
        ]
        
        # 只建立符合該學生訊息數量的範例
        messages_to_create = min(len(sample_messages), student.message_count)
        
        for i in range(messages_to_create):
            msg_data = sample_messages[i % len(sample_messages)]
            Message.create(
                student=student,
                content=msg_data['content'],
                message_type=msg_data['type'],
                timestamp=datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 72)),
                source_type='demo'  # 標示為演示訊息
            )
                
    except Exception as e:
        logger.error(f"❌ 建立演示訊息錯誤: {e}")

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
            
        logger.info(f"🧹 清理了 {deleted_count} 筆舊訊息")
        
    except Exception as e:
        logger.error(f"❌ 資料庫清理錯誤: {e}")

def validate_environment():
    """驗證環境變數"""
    required_vars = [
        'GEMINI_API_KEY',
        'CHANNEL_ACCESS_TOKEN', 
        'CHANNEL_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var) or os.getenv(f'LINE_{var}')  # 支援兩種格式
        if not value:
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ 缺少環境變數: {', '.join(missing_vars)}")
        return False
    
    logger.info("✅ 環境變數驗證通過")
    return True

def get_system_status():
    """取得系統狀態"""
    try:
        # 檢查 AI 服務狀態
        ai_status = 'available'
        if model:
            try:
                # 簡單測試 AI 回應
                test_response = model.generate_content("Hello")
                if not test_response or not test_response.text:
                    ai_status = 'error'
            except:
                ai_status = 'error'
        else:
            ai_status = 'unavailable'
        
        status = {
            'database': 'connected' if not db.is_closed() else 'disconnected',
            'ai_service': ai_status,
            'total_students': Student.select().count(),
            'real_students': Student.select().where(~Student.name.startswith('[DEMO]')).count(),
            'demo_students': Student.select().where(Student.name.startswith('[DEMO]')).count(),
            'total_messages': Message.select().count(),
            'last_update': datetime.datetime.now().isoformat()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ 取得系統狀態錯誤: {e}")
        return {'error': str(e)}

def safe_database_operation(operation):
    """安全的資料庫操作"""
    try:
        if db.is_closed():
            db.connect()
        
        result = operation()
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 資料庫操作錯誤: {e}")
        return None
    finally:
        if not db.is_closed():
            db.close()

def test_ai_connection():
    """測試 AI 連接"""
    try:
        if not model:
            return False, "AI 模型未初始化"
        
        test_response = model.generate_content("請簡單回答：你好")
        if test_response and test_response.text:
            return True, "AI 連接正常"
        else:
            return False, "AI 回應為空"
            
    except Exception as e:
        return False, f"AI 連接錯誤: {str(e)}"

# 初始化檢查
def initialize_utils():
    """初始化工具模組"""
    logger.info("🔧 初始化 utils 模組...")
    
    # 驗證環境
    env_ok = validate_environment()
    if not env_ok:
        logger.warning("⚠️ 環境變數檢查未通過，部分功能可能無法使用")
    
    # 測試 AI 連接
    ai_ok, ai_msg = test_ai_connection()
    logger.info(f"🤖 AI 狀態: {ai_msg}")
    
    logger.info("✅ Utils 模組初始化完成")

# 自動執行初始化
initialize_utils()
