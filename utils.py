import os
import json
import datetime
import logging
import random
import google.generativeai as genai
from models import Student, Message, Analysis, db

# 設定日誌
logger = logging.getLogger(__name__)

# 初始化 Gemini AI - 使用 2.0 模型
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
model = None
current_model_name = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 根據官方文件，使用可用的 Gemini 2.0 模型
        models_to_try = [
            'gemini-2.0-flash',           # 自動更新別名，指向最新穩定版
            'gemini-2.0-flash-001',       # 最新穩定版本
            'gemini-2.0-flash-lite',      # 輕量版自動更新別名
            'gemini-2.0-flash-lite-001',  # 輕量版穩定版本
        ]
        
        for model_name in models_to_try:
            try:
                test_model = genai.GenerativeModel(model_name)
                # 進行簡單測試確認模型可用
                test_response = test_model.generate_content("測試")
                if test_response and test_response.text:
                    model = test_model
                    current_model_name = model_name
                    logger.info(f"✅ Gemini AI 成功初始化，使用模型: {model_name}")
                    break
            except Exception as e:
                logger.warning(f"⚠️ 模型 {model_name} 測試失敗: {str(e)[:100]}")
                continue
        
        if not model:
            logger.error("❌ 所有 Gemini 2.0 模型都不可用，可能需要檢查 API 權限")
            
    except Exception as e:
        logger.error(f"❌ Gemini AI 初始化失敗: {e}")
else:
    logger.warning("⚠️ Gemini API key not found")

def get_ai_response(query, student_id=None):
    """取得 AI 回應"""
    try:
        if not model:
            logger.error("❌ AI 模型未初始化")
            return "抱歉，AI 服務目前無法使用。請檢查系統設定。"
        
        if not query or len(query.strip()) == 0:
            return "請提供您的問題，我很樂意為您解答！"
        
        # 取得學生資訊
        student_context = ""
        if student_id:
            try:
                student = Student.get_by_id(student_id)
                student_context = f"（學生：{student.name}，參與度：{student.participation_rate}%）"
            except Exception as e:
                logger.warning(f"無法取得學生資訊: {e}")
        
        # 為 Gemini 2.0 優化的提示詞
        prompt = f"""你是專業的雙語教學 AI 助理，專門協助 EMI 課程學習。

請用繁體中文回答學生問題，保持友善、專業且具有教育價值。
{student_context}

學生問題：{query}

請提供清晰、有幫助的回答（建議 100-150 字）："""
        
        logger.info(f"🤖 使用 {current_model_name} 生成回應...")
        
        # Gemini 2.0 optimized generation config
        generation_config = genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=300,
            temperature=0.7,
            top_p=0.9,
            top_k=40
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            ai_response = response.text.strip()
            logger.info(f"✅ AI 回應成功生成，長度: {len(ai_response)} 字")
            return ai_response
        else:
            logger.error("❌ AI 回應為空")
            return "抱歉，我現在無法生成適當的回應。請稍後再試或重新表達您的問題。"
            
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"❌ AI 回應錯誤: {str(e)}")
        
        # 詳細的錯誤處理
        if "404" in error_msg or "not found" in error_msg:
            return "AI 模型暫時無法使用。您的專案可能無法存取 Gemini 1.5 模型，系統正嘗試使用 Gemini 2.0。"
        elif "quota" in error_msg or "limit" in error_msg or "exceeded" in error_msg:
            return "AI 服務使用量已達上限，請稍後再試。"
        elif "permission" in error_msg or "denied" in error_msg:
            return "AI 服務權限不足，請檢查 API 金鑰設定。"
        elif "unavailable" in error_msg or "not available" in error_msg:
            return "您的 Google Cloud 專案可能無法使用較新的 Gemini 模型。建議聯絡管理員或升級專案。"
        elif "safety" in error_msg:
            return "為了安全考量，AI 無法回應此問題。請嘗試重新表達您的問題。"
        else:
            return f"處理您的問題時發生錯誤。請稍後再試。"

def analyze_student_patterns(student_id):
    """分析學生學習模式"""
    try:
        if not model:
            logger.warning("⚠️ AI 模型未初始化，無法進行分析")
            return None
            
        student = Student.get_by_id(student_id)
        
        # 取得最近訊息
        recent_messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(8))
        
        if len(recent_messages) < 3:
            return "該學生互動記錄不足（少於3則），無法進行有效分析。"
        
        # 準備分析資料
        messages_text = [msg.content[:80] for msg in recent_messages]
        questions = [msg.content[:80] for msg in recent_messages if msg.message_type == 'question']
        
        # 為 Gemini 2.0 優化的分析提示
        analysis_prompt = f"""作為教育專家，請分析以下學生的學習模式：

學生基本資料：
- 姓名：{student.name}
- 總發言：{student.message_count} 次
- 提問數：{student.question_count} 次
- 參與度：{student.participation_rate}%

近期互動內容：
{chr(10).join(f"• {msg}" for msg in messages_text)}

主要提問：
{chr(10).join(f"• {q}" for q in questions) if questions else "• 尚無提問記錄"}

請用 120-150 字分析該學生的：
1. 學習風格特點
2. 參與程度評估  
3. 具體學習建議

分析報告："""
        
        generation_config = genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=250,
            temperature=0.6,
        )
        
        response = model.generate_content(
            analysis_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            logger.info(f"✅ 學生學習模式分析完成: {student.name}")
            return response.text.strip()
        else:
            logger.error("❌ 學習模式分析回應為空")
            return "AI 分析服務暫時無法使用，請稍後再試。"
            
    except Exception as e:
        logger.error(f"❌ 學生模式分析錯誤: {e}")
        return f"分析過程中發生錯誤：{str(e)[:50]}..."

def test_ai_connection():
    """測試 AI 連接"""
    try:
        if not model:
            return False, "AI 模型未初始化"
        
        # 測試基本功能
        test_response = model.generate_content("請簡單回答：你好")
        
        if test_response and test_response.text:
            return True, f"連接正常，使用模型：{current_model_name}"
        else:
            return False, "AI 回應為空"
            
    except Exception as e:
        return False, f"連接錯誤：{str(e)[:60]}..."

def list_available_models():
    """列出可用的模型"""
    try:
        if not GEMINI_API_KEY:
            return ["無 API 金鑰"]
        
        genai.configure(api_key=GEMINI_API_KEY)
        models = []
        
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    models.append(m.name)
        except Exception as e:
            logger.warning(f"無法動態列出模型: {e}")
            # 根據官方文件返回已知可用模型
            models = [
                'models/gemini-2.0-flash-001',
                'models/gemini-2.0-flash-lite-001',
                'models/gemini-2.0-flash',
                'models/gemini-2.0-flash-lite'
            ]
            
        return models
    except Exception as e:
        logger.error(f"列出模型時錯誤: {e}")
        return [f"錯誤：{str(e)[:50]}"]

def get_model_info():
    """取得當前模型資訊"""
    if not model:
        return "未初始化"
    
    return current_model_name or "未知模型"

def update_student_stats(student_id):
    """更新學生統計資料"""
    try:
        student = Student.get_by_id(student_id)
        student.update_stats()
        logger.info(f"✅ 更新學生統計: {student.name}")
    except Exception as e:
        logger.error(f"❌ 更新統計錯誤: {e}")

def create_sample_data():
    """建立範例資料"""
    try:
        sample_students = [
            {
                'name': '[DEMO] 王小明',
                'line_user_id': 'demo_student_001',
                'message_count': 25,
                'question_count': 8,
                'participation_rate': 75.5,
                'question_rate': 32.0,
                'learning_style': '主動探索型',
                'notes': '系統演示用虛擬學生資料'
            },
            {
                'name': '[DEMO] 李美華',
                'line_user_id': 'demo_student_002', 
                'message_count': 18,
                'question_count': 12,
                'participation_rate': 68.2,
                'question_rate': 66.7,
                'learning_style': '問題導向型',
                'notes': '系統演示用虛擬學生資料'
            },
            {
                'name': '[DEMO] John Smith',
                'line_user_id': 'demo_student_003',
                'message_count': 32,
                'question_count': 5,
                'participation_rate': 82.3,
                'question_rate': 15.6,
                'learning_style': '實作導向型',
                'notes': '系統演示用虛擬學生資料'
            }
        ]
        
        for student_data in sample_students:
            try:
                existing = Student.select().where(
                    Student.line_user_id == student_data['line_user_id']
                ).first()
                
                if not existing:
                    student = Student.create(**{
                        **student_data,
                        'created_at': datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 30)),
                        'last_active': datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 48))
                    })
                    
                    create_sample_messages(student)
                    logger.info(f"✅ 建立演示學生: {student.name}")
                    
            except Exception as e:
                logger.error(f"❌ 建立演示學生錯誤: {e}")
                
    except Exception as e:
        logger.error(f"❌ 建立演示資料錯誤: {e}")

def create_sample_messages(student):
    """建立演示訊息"""
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
        
        messages_to_create = min(len(sample_messages), student.message_count)
        
        for i in range(messages_to_create):
            msg_data = sample_messages[i % len(sample_messages)]
            Message.create(
                student=student,
                content=msg_data['content'],
                message_type=msg_data['type'],
                timestamp=datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 72)),
                source_type='demo'
            )
                
    except Exception as e:
        logger.error(f"❌ 建立演示訊息錯誤: {e}")

def validate_environment():
    """驗證環境變數"""
    required_vars = ['GEMINI_API_KEY', 'CHANNEL_ACCESS_TOKEN', 'CHANNEL_SECRET']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var) or os.getenv(f'LINE_{var}')
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
        ai_ok, ai_msg = test_ai_connection()
        available_models = list_available_models()
        
        status = {
            'database': 'connected' if not db.is_closed() else 'disconnected',
            'ai_service': 'available' if ai_ok else 'error',
            'ai_message': ai_msg,
            'current_model': get_model_info(),
            'available_models': available_models[:8],
            'total_students': Student.select().count(),
            'real_students': Student.select().where(~Student.name.startswith('[DEMO]')).count(),
            'demo_students': Student.select().where(Student.name.startswith('[DEMO]')).count(),
            'total_messages': Message.select().count(),
            'model_info': f'使用 Gemini 2.0 系列模型（推薦用於新專案）',
            'last_update': datetime.datetime.now().isoformat()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ 取得系統狀態錯誤: {e}")
        return {'error': str(e)}

def initialize_utils():
    """初始化工具模組"""
    logger.info("🔧 初始化 utils 模組...")
    
    env_ok = validate_environment()
    if not env_ok:
        logger.warning("⚠️ 環境變數檢查未通過")
    
    ai_ok, ai_msg = test_ai_connection()
    logger.info(f"🤖 AI 狀態: {ai_msg}")
    
    models = list_available_models()
    if models:
        logger.info(f"📋 可用模型: {', '.join(models[:3])}...")
    
    logger.info(f"🚀 當前使用模型: {get_model_info()}")
    logger.info("✅ Utils 模組初始化完成")

# 自動執行初始化
initialize_utils()
