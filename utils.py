import os
import json
import datetime
import logging
import random
import google.generativeai as genai
from models import Student, Message, Analysis, db

# 設定日誌
logger = logging.getLogger(__name__)

# 初始化 Gemini AI - 使用最新可用模型
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 嘗試使用最新的可用模型（按優先順序）
        models_to_try = [
            'gemini-2.0-flash',      # 最新 2.0 模型
            'gemini-1.5-flash',      # 如果有使用記錄
            'gemini-1.5-pro',        # 如果有使用記錄
            'gemini-pro',            # 舊版備用
            'models/gemini-pro'      # 完整路徑
        ]
        
        for model_name in models_to_try:
            try:
                test_model = genai.GenerativeModel(model_name)
                # 進行簡單測試
                test_response = test_model.generate_content("Hello")
                if test_response and test_response.text:
                    model = test_model
                    logger.info(f"✅ Gemini AI 成功初始化，使用模型: {model_name}")
                    break
            except Exception as e:
                logger.warning(f"⚠️ 模型 {model_name} 不可用: {e}")
                continue
        
        if not model:
            logger.error("❌ 所有 Gemini 模型都不可用")
            
    except Exception as e:
        logger.error(f"❌ Gemini AI 初始化失敗: {e}")
else:
    logger.warning("⚠️ Gemini API key not found")

def get_ai_response(query, student_id=None):
    """取得 AI 回應 - 支援多種模型"""
    try:
        if not model:
            logger.error("❌ AI 模型未初始化")
            return "抱歉，AI 服務目前無法使用。系統可能需要升級模型版本。"
        
        if not query or len(query.strip()) == 0:
            return "請提供您的問題，我很樂意為您解答！"
        
        # 取得學生資訊
        student_context = ""
        if student_id:
            try:
                student = Student.get_by_id(student_id)
                student_context = f"學生：{student.name}，參與度：{student.participation_rate}%"
            except Exception as e:
                logger.warning(f"無法取得學生資訊: {e}")
        
        # 構建簡化的提示詞（適用於各種模型）
        prompt = f"""你是專業的教學助理，請用繁體中文簡潔回答：

{student_context}

問題：{query}

回答（100字內）："""
        
        logger.info(f"🤖 正在生成 AI 回應...")
        
        # 基本生成配置
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    'max_output_tokens': 200,
                    'temperature': 0.7,
                }
            )
        except:
            # 如果配置失敗，使用基本方式
            response = model.generate_content(prompt)
        
        if response and hasattr(response, 'text') and response.text:
            ai_response = response.text.strip()
            logger.info(f"✅ AI 回應成功，長度: {len(ai_response)} 字")
            return ai_response
        elif response and hasattr(response, 'candidates') and response.candidates:
            # 處理候選回應
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                ai_response = candidate.content.parts[0].text.strip()
                logger.info(f"✅ AI 回應成功（候選），長度: {len(ai_response)} 字")
                return ai_response
        
        logger.error("❌ AI 回應為空")
        return "抱歉，我現在無法生成適當的回應。請稍後再試。"
            
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"❌ AI 回應錯誤: {str(e)}")
        
        # 根據錯誤類型提供適當回應
        if "404" in error_msg or "not found" in error_msg:
            return "AI 模型暫時無法使用。系統可能需要更新模型版本。"
        elif "quota" in error_msg or "limit" in error_msg or "exceeded" in error_msg:
            return "AI 服務使用量已達上限，請稍後再試。"
        elif "permission" in error_msg or "denied" in error_msg:
            return "AI 服務權限有問題，請檢查 API 設定。"
        elif "unavailable" in error_msg:
            return "您的專案可能無法使用較新的 Gemini 模型，請聯絡管理員。"
        else:
            return "處理您的問題時發生錯誤，請稍後再試。"

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
        ).order_by(Message.timestamp.desc()).limit(5))
        
        if not recent_messages:
            return "該學生互動記錄不足，無法進行分析。"
        
        # 簡化分析提示
        messages_text = [msg.content[:50] for msg in recent_messages]
        analysis_prompt = f"""分析學生學習模式：

學生：{student.name}
發言：{student.message_count}次
提問：{student.question_count}次

近期內容：{', '.join(messages_text)}

請用50字內分析學習風格："""
        
        try:
            response = model.generate_content(analysis_prompt)
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
        except:
            pass
            
        return "無法進行AI分析，請稍後再試。"
            
    except Exception as e:
        logger.error(f"❌ 學習模式分析錯誤: {e}")
        return None

def list_available_models():
    """列出可用的模型"""
    try:
        if not GEMINI_API_KEY:
            return []
        
        genai.configure(api_key=GEMINI_API_KEY)
        models = []
        
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    models.append(m.name)
        except Exception as e:
            logger.warning(f"無法列出模型: {e}")
            # 返回可能可用的模型列表
            models = [
                'gemini-2.0-flash',
                'gemini-1.5-flash', 
                'gemini-1.5-pro',
                'gemini-pro'
            ]
            
        return models
    except Exception as e:
        logger.error(f"列出模型時錯誤: {e}")
        return []

def test_ai_connection():
    """測試 AI 連接"""
    try:
        if not model:
            return False, "AI 模型未初始化"
        
        # 簡單測試
        test_response = model.generate_content("Hi")
        
        if test_response and hasattr(test_response, 'text') and test_response.text:
            return True, f"連接正常，回應: {test_response.text[:30]}..."
        elif test_response and hasattr(test_response, 'candidates'):
            return True, "連接正常（候選回應格式）"
        else:
            return False, "回應格式異常"
            
    except Exception as e:
        return False, f"連接錯誤: {str(e)[:50]}..."

def get_model_info():
    """取得當前模型資訊"""
    if not model:
        return "未初始化"
    
    try:
        return getattr(model, 'model_name', '未知模型')
    except:
        return "模型資訊無法取得"

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
            {'content': '謝謝老師的說明', 'type': 'statement'},
            {'content': 'What is the difference between AI and ML?', 'type': 'question'},
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
            'available_models': available_models[:5],  # 限制顯示數量
            'total_students': Student.select().count(),
            'real_students': Student.select().where(~Student.name.startswith('[DEMO]')).count(),
            'demo_students': Student.select().where(Student.name.startswith('[DEMO]')).count(),
            'total_messages': Message.select().count(),
            'last_update': datetime.datetime.now().isoformat(),
            'sdk_warning': 'google-generativeai SDK 將於 2025年8月31日停止支援'
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
    
    logger.info(f"🔧 當前使用模型: {get_model_info()}")
    logger.info("✅ Utils 模組初始化完成")

# 自動執行初始化
initialize_utils()
