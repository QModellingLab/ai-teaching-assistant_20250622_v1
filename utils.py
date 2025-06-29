# =================== utils.py 優化版 - 第1段開始 ===================
# EMI智能教學助理系統 - 工具函數（優化版）
# 配合 app.py v4.0 優化版使用
# 更新日期：2025年6月29日

import os
import logging
import json
import datetime
import time
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter
import google.generativeai as genai

# 設定日誌
logger = logging.getLogger(__name__)

# =================== AI 模型配置（優化版） ===================

# 取得 API 金鑰
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 優化的模型配置
AVAILABLE_MODELS = [
    "gemini-2.5-flash",        # 🥇 首選：最佳性價比
    "gemini-2.0-flash-exp",    # 🥈 備用：實驗版本
    "gemini-1.5-flash",        # 📦 備案：成熟穩定
    "gemini-1.5-pro",          # 📦 備案：功能完整
    "gemini-pro"               # 📦 最後備案：舊版
]

# 當前模型配置
current_model_name = "gemini-2.5-flash"
model = None

# 模型使用統計（優化版）
model_usage_stats = {
    model_name: {
        'calls': 0, 
        'errors': 0, 
        'last_used': None,
        'success_rate': 0.0
    } for model_name in AVAILABLE_MODELS
}

# 初始化AI模型
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(current_model_name)
        logger.info(f"✅ Gemini AI 初始化成功 - 使用模型: {current_model_name}")
    except Exception as e:
        logger.error(f"❌ Gemini AI 初始化失敗: {e}")
        model = None
else:
    logger.warning("⚠️ GEMINI_API_KEY 未設定")

# =================== 核心AI回應生成（與app.py兼容）===================

def generate_ai_response(message_text, student):
    """生成AI回應（與app.py的generate_ai_response函數兼容）"""
    try:
        if not GEMINI_API_KEY or not model:
            return get_fallback_response(message_text)
        
        # 建構提示詞
        prompt = f"""You are an EMI (English as a Medium of Instruction) teaching assistant for the course "Practical Applications of AI in Life and Learning."

Student: {student.name} (ID: {getattr(student, 'student_id', 'Unknown')})
Question: {message_text}

Please provide a helpful, academic response in English (150 words max). Focus on:
- Clear, educational explanations
- Practical examples when relevant  
- Encouraging tone for learning
- Academic language appropriate for university students

Response:"""

        # 生成配置（優化速度和質量）
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            max_output_tokens=200  # 限制輸出長度確保150字內
        )
        
        # 調用AI
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if response and response.text:
            ai_response = response.text.strip()
            
            # 記錄成功使用
            record_model_usage(current_model_name, True)
            
            logger.info(f"✅ AI 回應生成成功 - 學生: {student.name}, 長度: {len(ai_response)} 字")
            
            # 基本長度檢查
            if len(ai_response) < 10:
                logger.warning("⚠️ AI 回應過短，使用備用回應")
                return get_fallback_response(message_text)
            
            return ai_response
        else:
            logger.error("❌ AI 回應為空")
            record_model_usage(current_model_name, False)
            return get_fallback_response(message_text)
            
    except Exception as e:
        logger.error(f"❌ AI 回應生成錯誤: {e}")
        record_model_usage(current_model_name, False)
        
        # 智慧錯誤處理
        error_msg = str(e).lower()
        if "429" in error_msg or "quota" in error_msg:
            return "I'm currently at my usage limit. Please try again in a moment! 🤖"
        elif "403" in error_msg:
            return "I'm having authentication issues. Please contact your teacher. 🔧"
        else:
            return get_fallback_response(message_text)

def generate_simple_ai_response(student_name, student_id, query):
    """生成簡化的AI回應（向後兼容函數）"""
    try:
        if not GEMINI_API_KEY or not model:
            return get_fallback_response(query)
        
        # EMI課程專用提示詞（150字限制）
        prompt = f"""You are an academic AI assistant for EMI course: "Practical Applications of AI in Life and Learning"

STRICT RULES:
1. Maximum 150 words total
2. Structure: **Term**: technical definition. Example: specific real application.
3. NO greetings, questions, or filler words
4. Use bold for key concepts: **term**
5. One concrete example with company/data

Student: {student_name}
Question: {query}

Respond with academic precision and brevity."""

        # 生成配置（優化速度和質量）
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            max_output_tokens=200  # 限制輸出長度確保150字內
        )
        
        # 調用AI
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if response and response.text:
            ai_response = response.text.strip()
            
            # 記錄成功使用
            record_model_usage(current_model_name, True)
            
            logger.info(f"✅ AI 回應生成成功 - 學生: {student_name}, 長度: {len(ai_response)} 字")
            
            # 基本長度檢查
            if len(ai_response) < 10:
                logger.warning("⚠️ AI 回應過短，使用備用回應")
                return get_fallback_response(query)
            
            return ai_response
        else:
            logger.error("❌ AI 回應為空")
            record_model_usage(current_model_name, False)
            return get_fallback_response(query)
            
    except Exception as e:
        logger.error(f"❌ AI 回應生成錯誤: {e}")
        record_model_usage(current_model_name, False)
        
        # 智慧錯誤處理
        error_msg = str(e).lower()
        if "429" in error_msg or "quota" in error_msg:
            return "I'm currently at my usage limit. Please try again in a moment! 🤖"
        elif "403" in error_msg:
            return "I'm having authentication issues. Please contact your teacher. 🔧"
        else:
            return get_fallback_response(query)

def generate_learning_suggestion(student):
    """生成學習建議（與app.py的generate_learning_suggestion函數兼容）"""
    try:
        if not GEMINI_API_KEY or not model:
            return get_fallback_suggestion(student, 0)
        
        # 獲取學生最近對話（優化版）
        try:
            from models import Message
            messages = list(Message.select().where(
                Message.student == student
            ).order_by(Message.timestamp.desc()).limit(10))
            
            if messages:
                recent_conversations = "\n".join([
                    f"- {msg.content[:80]}..." for msg in messages[:5] if msg.content
                ])
                conversation_count = len(messages)
            else:
                recent_conversations = "No recent conversations"
                conversation_count = 0
                
        except Exception as e:
            logger.warning(f"無法取得對話記錄: {e}")
            recent_conversations = "Unable to access conversation history"
            conversation_count = 0
        
        # 學習建議生成提示詞
        prompt = f"""Based on conversation history, provide learning advice in simple English (150 words max).

Student: {student.name}
Total conversations: {conversation_count}
Recent topics:
{recent_conversations}

Provide:
1. Learning strengths (1-2 sentences)
2. Areas for improvement (1-2 sentences)  
3. Specific recommendations (1-2 sentences)

Use encouraging tone and practical advice. Simple vocabulary only."""

        # 生成配置
        generation_config = genai.types.GenerationConfig(
            temperature=0.6,
            top_p=0.8,
            top_k=20,
            max_output_tokens=200
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if response and response.text:
            suggestion = response.text.strip()
            record_model_usage(current_model_name, True)
            logger.info(f"✅ 學習建議生成成功 - 學生: {student.name}")
            return suggestion
        else:
            logger.error("❌ 學習建議生成失敗")
            record_model_usage(current_model_name, False)
            return get_fallback_suggestion(student, conversation_count)
            
    except Exception as e:
        logger.error(f"❌ 學習建議生成錯誤: {e}")
        record_model_usage(current_model_name, False)
        return get_fallback_suggestion(student, 0)

def get_fallback_response(user_message):
    """備用回應生成器（優化版）"""
    user_msg_lower = user_message.lower()
    
    # 基於關鍵詞的簡單回應
    if any(word in user_msg_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm your AI assistant for our EMI course. How can I help you today? 👋"
    
    elif any(word in user_msg_lower for word in ['ai', 'artificial intelligence']):
        return "**Artificial Intelligence**: systems that simulate human intelligence. Example: Google Search uses AI algorithms to rank millions of web pages in milliseconds."
    
    elif any(word in user_msg_lower for word in ['machine learning', 'ml']):
        return "**Machine Learning**: AI subset where systems learn from data without explicit programming. Example: Netflix recommends shows based on your viewing history."
    
    elif any(word in user_msg_lower for word in ['data', 'big data']):
        return "**Big Data**: extremely large datasets requiring special tools for analysis. Example: Facebook processes 4 billion posts daily for content personalization."
    
    elif any(word in user_msg_lower for word in ['algorithm']):
        return "**Algorithm**: step-by-step instructions for solving problems. Example: YouTube's recommendation algorithm suggests videos based on user behavior patterns."
    
    elif any(word in user_msg_lower for word in ['deep learning']):
        return "**Deep Learning**: AI technique using neural networks with multiple layers. Example: Tesla's self-driving cars use deep learning to recognize objects and make driving decisions."
    
    elif any(word in user_msg_lower for word in ['neural network']):
        return "**Neural Network**: computing system inspired by biological brain structure. Example: Google Translate uses neural networks to translate text between 100+ languages accurately."
    
    elif '?' in user_message:
        return "Great question! I can help explain AI concepts with practical examples. Could you specify which aspect interests you most?"
    
    else:
        return "I'm here to help with AI and technology topics! Feel free to ask about artificial intelligence, machine learning, or data applications."

def get_fallback_suggestion(student, conversation_count):
    """備用學習建議（不依賴AI）"""
    if conversation_count >= 15:
        activity_level = "actively engaged"
        suggestion = "Excellent participation! Continue exploring advanced AI applications. Consider researching emerging technologies like generative AI."
    elif conversation_count >= 8:
        activity_level = "moderately engaged"
        suggestion = "Good learning progress! Try asking more specific questions about AI applications in your field of interest."
    elif conversation_count >= 3:
        activity_level = "getting started"
        suggestion = "Welcome to our AI course! Feel free to ask about basic concepts like machine learning, algorithms, or data science."
    else:
        activity_level = "just beginning"
        suggestion = "Great to have you in our course! Start by asking about everyday AI applications you encounter."
    
    return f"""📊 {student.name}'s Learning Progress

**Current Status**: You are {activity_level} with {conversation_count} conversations.

**Strengths**: Shows curiosity about AI and technology topics. Demonstrates willingness to learn new concepts.

**Suggestions**: {suggestion}

**Tip**: Regular engagement helps reinforce learning. Try connecting AI concepts to real-world examples you encounter daily!"""

# =================== 模型管理（優化版） ===================

def record_model_usage(model_name: str, success: bool = True):
    """記錄模型使用統計"""
    if model_name in model_usage_stats:
        stats = model_usage_stats[model_name]
        stats['calls'] += 1
        stats['last_used'] = time.time()
        if not success:
            stats['errors'] += 1
        
        # 計算成功率
        if stats['calls'] > 0:
            stats['success_rate'] = ((stats['calls'] - stats['errors']) / stats['calls']) * 100

def switch_to_available_model():
    """切換到可用模型（優化版）"""
    global model, current_model_name
    
    if not GEMINI_API_KEY:
        return False
    
    # 嘗試切換到下一個可用模型
    current_index = AVAILABLE_MODELS.index(current_model_name) if current_model_name in AVAILABLE_MODELS else 0
    
    for i in range(1, len(AVAILABLE_MODELS)):
        next_index = (current_index + i) % len(AVAILABLE_MODELS)
        next_model_name = AVAILABLE_MODELS[next_index]
        
        try:
            logger.info(f"🔄 嘗試切換到模型: {next_model_name}")
            new_model = genai.GenerativeModel(next_model_name)
            
            # 簡單測試
            test_response = new_model.generate_content("Test")
            if test_response and test_response.text:
                model = new_model
                current_model_name = next_model_name
                logger.info(f"✅ 成功切換到模型: {current_model_name}")
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ 模型 {next_model_name} 切換失敗: {e}")
            continue
    
    logger.error("❌ 所有模型都無法使用")
    return False

def test_ai_connection():
    """測試AI連接（優化版）"""
    try:
        if not GEMINI_API_KEY:
            return False, "API 金鑰未設定"
        
        if not model:
            return False, "AI 模型未初始化"
        
        # 簡單連接測試
        test_response = model.generate_content("Hello")
        if test_response and test_response.text:
            return True, f"連接正常 - 當前模型: {current_model_name}"
        else:
            return False, "AI 回應測試失敗"
            
    except Exception as e:
        return False, f"連接錯誤: {str(e)[:50]}..."

def get_quota_status():
    """取得配額狀態（優化版）"""
    status = {
        'current_model': current_model_name,
        'models': {},
        'total_calls': 0,
        'total_errors': 0
    }
    
    for model_name, stats in model_usage_stats.items():
        status['models'][model_name] = {
            'calls': stats['calls'],
            'errors': stats['errors'],
            'success_rate': round(stats['success_rate'], 1),
            'status': '正常' if stats['success_rate'] > 50 or stats['calls'] == 0 else '可能有問題'
        }
        status['total_calls'] += stats['calls']
        status['total_errors'] += stats['errors']
    
    return status

# =================== utils.py 優化版 - 第1段結束 ===================

# =================== utils.py 優化版 - 第2段開始 ===================
# 分析功能和系統統計（優化版）

# =================== 基本分析功能（優化版） ===================

def analyze_student_basic_stats(student_id):
    """分析學生基本統計（優化版）"""
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '學生不存在'}
        
        # 基本統計
        messages = list(Message.select().where(Message.student_id == student_id))
        total_messages = len(messages)
        
        # 活動時間分析
        if messages:
            # 計算學習天數
            timestamps = [msg.timestamp for msg in messages if msg.timestamp]
            if timestamps:
                earliest = min(timestamps)
                latest = max(timestamps)
                active_days = (latest - earliest).days + 1
            else:
                active_days = 1
        else:
            active_days = 0
        
        # 簡單參與度評估
        if total_messages >= 20:
            engagement = "高度參與"
        elif total_messages >= 10:
            engagement = "中度參與"
        elif total_messages >= 5:
            engagement = "輕度參與"
        else:
            engagement = "極少參與"
        
        # 註冊狀態檢查
        registration_status = "未知"
        if hasattr(student, 'registration_step'):
            if student.registration_step == 0 and student.name and getattr(student, 'student_id', ''):
                registration_status = "已完成"
            elif student.registration_step > 0:
                registration_status = "進行中"
            else:
                registration_status = "未完成"
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'student_id_number': getattr(student, 'student_id', ''),
            'total_messages': total_messages,
            'active_days': active_days,
            'engagement_level': engagement,
            'registration_status': registration_status,
            'last_active': student.last_active.isoformat() if student.last_active else None,
            'created_at': student.created_at.isoformat() if student.created_at else None,
            'analysis_date': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"學生統計分析錯誤: {e}")
        return {
            'student_id': student_id,
            'error': str(e),
            'analysis_date': datetime.datetime.now().isoformat()
        }

def get_system_stats():
    """取得系統統計（優化版）"""
    try:
        from models import Student, Message
        
        stats = {
            'students': {
                'total': Student.select().count(),
                'active_this_week': 0,
                'registered': 0,
                'need_registration': 0,
            },
            'messages': {
                'total': Message.select().count(),
                'today': 0,
                'this_week': 0
            },
            'ai': {
                'current_model': current_model_name,
                'total_calls': sum(stats['calls'] for stats in model_usage_stats.values()),
                'total_errors': sum(stats['errors'] for stats in model_usage_stats.values()),
            }
        }
        
        # 計算註冊統計
        try:
            if hasattr(Student, 'registration_step'):
                stats['students']['registered'] = Student.select().where(
                    Student.registration_step == 0
                ).count()
                stats['students']['need_registration'] = Student.select().where(
                    Student.registration_step > 0
                ).count()
            else:
                stats['students']['registered'] = stats['students']['total']
                stats['students']['need_registration'] = 0
        except Exception as e:
            logger.warning(f"註冊統計計算錯誤: {e}")
        
        # 計算本週活躍學生
        try:
            week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            stats['students']['active_this_week'] = Student.select().where(
                Student.last_active.is_null(False) & 
                (Student.last_active >= week_ago)
            ).count()
        except Exception as e:
            logger.warning(f"活躍學生統計錯誤: {e}")
        
        # 計算今日訊息
        try:
            today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            stats['messages']['today'] = Message.select().where(
                Message.timestamp >= today_start
            ).count()
        except Exception as e:
            logger.warning(f"今日訊息統計錯誤: {e}")
        
        # 計算本週訊息
        try:
            week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            stats['messages']['this_week'] = Message.select().where(
                Message.timestamp >= week_ago
            ).count()
        except Exception as e:
            logger.warning(f"本週訊息統計錯誤: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"系統統計錯誤: {e}")
        return {
            'students': {'total': 0, 'active_this_week': 0, 'registered': 0, 'need_registration': 0},
            'messages': {'total': 0, 'today': 0, 'this_week': 0},
            'ai': {'current_model': current_model_name, 'total_calls': 0, 'total_errors': 0},
            'error': str(e)
        }

def get_student_conversation_summary(student_id, days=30):
    """取得學生對話摘要（優化版）"""
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '學生不存在'}
        
        # 取得指定天數內的訊息
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        messages = list(Message.select().where(
            (Message.student_id == student_id) &
            (Message.timestamp >= cutoff_date)
        ).order_by(Message.timestamp.desc()))
        
        if not messages:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'period_days': days,
                'message_count': 0,
                'summary': f'No conversation records in the past {days} days.',
                'status': 'no_data'
            }
        
        # 分析訊息來源
        student_messages = [msg for msg in messages if msg.source_type in ['line', 'student']]
        ai_messages = [msg for msg in messages if msg.source_type == 'ai']
        
        # 簡單活躍度評估
        if len(messages) >= 20:
            activity_level = "highly active"
        elif len(messages) >= 10:
            activity_level = "moderately active"
        elif len(messages) >= 5:
            activity_level = "lightly active"
        else:
            activity_level = "minimal activity"
        
        summary = f"In the past {days} days, {student.name} had {len(messages)} total messages ({len(student_messages)} student messages, {len(ai_messages)} AI responses). Activity level: {activity_level}."
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'period_days': days,
            'message_count': len(messages),
            'student_messages': len(student_messages),
            'ai_messages': len(ai_messages),
            'activity_level': activity_level,
            'summary': summary,
            'generated_at': datetime.datetime.now().isoformat(),
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"對話摘要錯誤: {e}")
        return {
            'student_id': student_id,
            'error': str(e),
            'status': 'error'
        }

# =================== 系統健康檢查（優化版） ===================

def perform_system_health_check():
    """執行系統健康檢查（優化版）"""
    health_report = {
        'timestamp': datetime.datetime.now().isoformat(),
        'overall_status': 'healthy',
        'checks': {},
        'warnings': [],
        'errors': []
    }
    
    try:
        # 檢查資料庫連接
        try:
            from models import Student, Message
            student_count = Student.select().count()
            message_count = Message.select().count()
            
            health_report['checks']['database'] = {
                'status': 'healthy',
                'details': f'連接正常，{student_count} 位學生，{message_count} 則訊息'
            }
        except Exception as e:
            health_report['checks']['database'] = {
                'status': 'error',
                'details': f'資料庫連接失敗: {str(e)}'
            }
            health_report['errors'].append('資料庫連接失敗')
        
        # 檢查AI服務
        ai_status, ai_message = test_ai_connection()
        health_report['checks']['ai_service'] = {
            'status': 'healthy' if ai_status else 'error',
            'details': ai_message
        }
        if not ai_status:
            health_report['errors'].append('AI服務連接失敗')
        
        # 檢查模型使用統計
        quota_status = get_quota_status()
        health_report['checks']['ai_quota'] = {
            'status': 'healthy' if quota_status['total_errors'] < quota_status['total_calls'] * 0.5 else 'warning',
            'details': f'總呼叫: {quota_status["total_calls"]}, 錯誤: {quota_status["total_errors"]}'
        }
        
        # 檢查註冊狀態
        try:
            from models import Student
            if hasattr(Student, 'registration_step'):
                need_registration = Student.select().where(Student.registration_step > 0).count()
                if need_registration > 0:
                    health_report['warnings'].append(f'{need_registration} 位學生需要完成註冊')
                    health_report['checks']['registration'] = {
                        'status': 'warning',
                        'details': f'{need_registration} 位學生需要完成註冊'
                    }
                else:
                    health_report['checks']['registration'] = {
                        'status': 'healthy',
                        'details': '所有學生都已完成註冊'
                    }
        except Exception as e:
            health_report['checks']['registration'] = {
                'status': 'error',
                'details': f'無法檢查註冊狀態: {str(e)}'
            }
        
        # 檢查模型切換情況
        error_rate = 0
        if quota_status['total_calls'] > 0:
            error_rate = (quota_status['total_errors'] / quota_status['total_calls']) * 100
        
        if error_rate > 20:
            health_report['warnings'].append(f'AI錯誤率過高: {error_rate:.1f}%')
        
        # 決定整體狀態
        if health_report['errors']:
            health_report['overall_status'] = 'error'
        elif health_report['warnings']:
            health_report['overall_status'] = 'warning'
        else:
            health_report['overall_status'] = 'healthy'
        
        return health_report
        
    except Exception as e:
        logger.error(f"系統健康檢查錯誤: {e}")
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'overall_status': 'error',
            'checks': {},
            'warnings': [],
            'errors': [f'健康檢查失敗: {str(e)}']
        }

def get_system_status():
    """取得系統狀態摘要（優化版）"""
    try:
        health_check = perform_system_health_check()
        system_stats = get_system_stats()
        
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'overall_status': health_check['overall_status'],
            'database_status': health_check['checks'].get('database', {}).get('status', 'unknown'),
            'ai_status': health_check['checks'].get('ai_service', {}).get('status', 'unknown'),
            'current_model': current_model_name,
            'total_students': system_stats['students']['total'],
            'total_messages': system_stats['messages']['total'],
            'active_students_this_week': system_stats['students']['active_this_week'],
            'messages_today': system_stats['messages']['today'],
            'registered_students': system_stats['students']['registered'],
            'need_registration': system_stats['students']['need_registration'],
            'ai_calls': system_stats['ai']['total_calls'],
            'ai_errors': system_stats['ai']['total_errors'],
            'warnings': health_check['warnings'],
            'errors': health_check['errors']
        }
        
    except Exception as e:
        logger.error(f"取得系統狀態錯誤: {e}")
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'overall_status': 'error',
            'error': str(e)
        }

# =================== 學生統計更新功能（優化版） ===================

def update_student_stats(student_id):
    """更新學生統計（優化版）"""
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return False
        
        # 更新最後活動時間
        student.last_active = datetime.datetime.now()
        
        # 更新訊息計數（如果有該欄位）
        if hasattr(student, 'message_count'):
            message_count = Message.select().where(Message.student == student).count()
            student.message_count = message_count
        
        student.save()
        
        logger.info(f"✅ 學生統計已更新 - {student.name}")
        return True
        
    except Exception as e:
        logger.error(f"更新學生統計錯誤: {e}")
        return False

# =================== 學生活躍度分析（優化版） ===================

def analyze_student_activity_pattern(student_id, days=30):
    """分析學生活動模式（優化版）"""
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '學生不存在'}
        
        # 取得指定天數內的活動
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        messages = list(Message.select().where(
            (Message.student_id == student_id) &
            (Message.timestamp >= cutoff_date)
        ).order_by(Message.timestamp.asc()))
        
        if not messages:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'period_days': days,
                'activity_pattern': 'no_activity',
                'peak_hours': [],
                'active_days': 0,
                'messages_per_day': 0
            }
        
        # 分析活動時間模式
        hours = [msg.timestamp.hour for msg in messages if msg.timestamp]
        hour_counts = Counter(hours)
        peak_hours = [hour for hour, count in hour_counts.most_common(3)]
        
        # 計算活躍天數
        active_dates = set(msg.timestamp.date() for msg in messages if msg.timestamp)
        active_days = len(active_dates)
        
        # 平均每日訊息數
        messages_per_day = len(messages) / max(active_days, 1)
        
        # 活動模式分類
        if messages_per_day >= 5:
            activity_pattern = "highly_active"
        elif messages_per_day >= 2:
            activity_pattern = "moderately_active"
        elif messages_per_day >= 1:
            activity_pattern = "lightly_active"
        else:
            activity_pattern = "minimal_activity"
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'period_days': days,
            'activity_pattern': activity_pattern,
            'peak_hours': peak_hours,
            'active_days': active_days,
            'messages_per_day': round(messages_per_day, 1),
            'total_messages': len(messages)
        }
        
    except Exception as e:
        logger.error(f"學生活動分析錯誤: {e}")
        return {'error': str(e)}

def get_class_engagement_summary():
    """取得全班參與度摘要（優化版）"""
    try:
        from models import Student, Message
        
        students = list(Student.select())
        if not students:
            return {'error': '沒有學生資料'}
        
        engagement_levels = {
            'high': 0,    # >= 20 messages
            'medium': 0,  # 10-19 messages  
            'low': 0,     # 5-9 messages
            'minimal': 0  # < 5 messages
        }
        
        total_messages = 0
        registered_students = 0
        active_this_week = 0
        
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        
        for student in students:
            # 計算每個學生的訊息數
            message_count = Message.select().where(Message.student == student).count()
            total_messages += message_count
            
            # 分類參與度
            if message_count >= 20:
                engagement_levels['high'] += 1
            elif message_count >= 10:
                engagement_levels['medium'] += 1
            elif message_count >= 5:
                engagement_levels['low'] += 1
            else:
                engagement_levels['minimal'] += 1
            
            # 檢查註冊狀態
            if hasattr(student, 'registration_step'):
                if student.registration_step == 0 and student.name and getattr(student, 'student_id', ''):
                    registered_students += 1
            
            # 檢查本週活躍
            if student.last_active and student.last_active >= week_ago:
                active_this_week += 1
        
        return {
            'total_students': len(students),
            'registered_students': registered_students,
            'active_this_week': active_this_week,
            'total_messages': total_messages,
            'average_messages_per_student': round(total_messages / len(students), 1),
            'engagement_distribution': engagement_levels,
            'engagement_percentage': {
                'high': round((engagement_levels['high'] / len(students)) * 100, 1),
                'medium': round((engagement_levels['medium'] / len(students)) * 100, 1),
                'low': round((engagement_levels['low'] / len(students)) * 100, 1),
                'minimal': round((engagement_levels['minimal'] / len(students)) * 100, 1)
            }
        }
        
    except Exception as e:
        logger.error(f"全班參與度摘要錯誤: {e}")
        return {'error': str(e)}

# =================== 資料驗證和清理功能（優化版） ===================

def validate_student_data():
    """驗證學生資料完整性（優化版）"""
    try:
        from models import Student
        
        validation_report = {
            'total_students': 0,
            'valid_students': 0,
            'issues': {
                'missing_name': 0,
                'missing_student_id': 0,
                'incomplete_registration': 0,
                'invalid_registration_step': 0
            },
            'recommendations': []
        }
        
        students = list(Student.select())
        validation_report['total_students'] = len(students)
        
        for student in students:
            is_valid = True
            
            # 檢查姓名
            if not student.name or student.name.strip() == "":
                validation_report['issues']['missing_name'] += 1
                is_valid = False
            
            # 檢查學號
            if not hasattr(student, 'student_id') or not getattr(student, 'student_id', ''):
                validation_report['issues']['missing_student_id'] += 1
                is_valid = False
            
            # 檢查註冊步驟
            if hasattr(student, 'registration_step'):
                if student.registration_step > 0:
                    validation_report['issues']['incomplete_registration'] += 1
                    is_valid = False
                elif student.registration_step < 0:
                    validation_report['issues']['invalid_registration_step'] += 1
                    is_valid = False
            
            if is_valid:
                validation_report['valid_students'] += 1
        
        # 生成建議
        if validation_report['issues']['missing_name'] > 0:
            validation_report['recommendations'].append(f"修正 {validation_report['issues']['missing_name']} 位學生的姓名資料")
        
        if validation_report['issues']['missing_student_id'] > 0:
            validation_report['recommendations'].append(f"修正 {validation_report['issues']['missing_student_id']} 位學生的學號資料")
        
        if validation_report['issues']['incomplete_registration'] > 0:
            validation_report['recommendations'].append(f"協助 {validation_report['issues']['incomplete_registration']} 位學生完成註冊")
        
        if not validation_report['recommendations']:
            validation_report['recommendations'].append("所有學生資料都已完整")
        
        return validation_report
        
    except Exception as e:
        logger.error(f"學生資料驗證錯誤: {e}")
        return {'error': str(e)}

def cleanup_old_messages(days=90):
    """清理舊訊息（可選功能）"""
    try:
        from models import Message
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        old_messages = Message.select().where(Message.timestamp < cutoff_date)
        
        count = old_messages.count()
        if count == 0:
            return {
                'status': 'no_data',
                'message': f'沒有超過 {days} 天的舊訊息需要清理'
            }
        
        # 注意：這是危險操作，預設只返回統計不實際刪除
        return {
            'status': 'info',
            'old_messages_count': count,
            'cutoff_date': cutoff_date.isoformat(),
            'message': f'發現 {count} 則超過 {days} 天的舊訊息，可考慮清理',
            'warning': '實際清理需要額外確認步驟'
        }
        
    except Exception as e:
        logger.error(f"清理舊訊息檢查錯誤: {e}")
        return {'error': str(e)}

# =================== 相容性函數（向後兼容） ===================

# 保持與原版本的相容性
def generate_ai_response_with_smart_fallback(student_id, query, conversation_context="", student_context="", group_id=None):
    """相容性函數：舊版AI回應生成"""
    try:
        from models import Student
        student = Student.get_by_id(student_id) if student_id else None
        
        if student:
            return generate_ai_response(query, student)
        else:
            student_name = "Unknown"
            return generate_simple_ai_response(student_name, student_id, query)
    except Exception as e:
        logger.error(f"相容性AI回應錯誤: {e}")
        return get_fallback_response(query)

def analyze_student_patterns(student_id):
    """相容性函數：學生模式分析"""
    return analyze_student_basic_stats(student_id)

# 舊版函數別名（保持相容性）
analyze_student_pattern = analyze_student_patterns
get_ai_response = generate_ai_response_with_smart_fallback

# =================== utils.py 優化版 - 第2段結束 ===================

# =================== utils.py 優化版 - 第3段開始 ===================
# 匯出功能和模組配置

# =================== 優化的匯出功能 ===================

def export_student_conversations_tsv(student_id):
    """匯出學生對話記錄為TSV格式（優化版）"""
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'status': 'error', 'error': '學生不存在'}
        
        # 取得所有對話記錄
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()))
        
        if not messages:
            return {'status': 'no_data', 'error': '該學生沒有對話記錄'}
        
        # 生成TSV內容
        tsv_lines = ['時間\t學生姓名\t學號\t訊息內容\t來源類型\t註冊狀態']
        
        # 取得註冊狀態
        registration_status = "未知"
        if hasattr(student, 'registration_step'):
            if student.registration_step == 0 and student.name and getattr(student, 'student_id', ''):
                registration_status = "已完成"
            elif student.registration_step > 0:
                registration_status = "進行中"
            else:
                registration_status = "未完成"
        
        for msg in messages:
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else '未知時間'
            student_name = student.name or '未知學生'
            student_id_number = getattr(student, 'student_id', '未設定')
            content = msg.content.replace('\n', ' ').replace('\t', ' ')[:500]  # 限制長度
            source = '學生' if msg.source_type in ['line', 'student'] else 'AI助理'
            
            tsv_lines.append(f"{timestamp}\t{student_name}\t{student_id_number}\t{content}\t{source}\t{registration_status}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"student_{student.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
        return {
            'status': 'success',
            'content': tsv_content,
            'filename': filename,
            'message_count': len(messages),
            'student_name': student.name
        }
        
    except Exception as e:
        logger.error(f"匯出學生對話錯誤: {e}")
        return {'status': 'error', 'error': str(e)}

def export_all_conversations_tsv():
    """匯出所有對話記錄為TSV格式（優化版）"""
    try:
        from models import Student, Message
        
        # 取得所有對話記錄
        messages = list(Message.select().join(Student).order_by(Message.timestamp.desc()))
        
        if not messages:
            return {'status': 'no_data', 'error': '沒有找到任何對話記錄'}
        
        # 生成TSV內容
        tsv_lines = ['時間\t學生姓名\t學號\t訊息內容\t來源類型\t註冊狀態']
        
        for msg in messages:
            student = msg.student
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else '未知時間'
            student_name = student.name or '未知學生'
            student_id_number = getattr(student, 'student_id', '未設定')
            content = msg.content.replace('\n', ' ').replace('\t', ' ')[:500]  # 限制長度
            source = '學生' if msg.source_type in ['line', 'student'] else 'AI助理'
            
            # 取得註冊狀態
            registration_status = "未知"
            if hasattr(student, 'registration_step'):
                if student.registration_step == 0 and student.name and getattr(student, 'student_id', ''):
                    registration_status = "已完成"
                elif student.registration_step > 0:
                    registration_status = "進行中"
                else:
                    registration_status = "未完成"
            
            tsv_lines.append(f"{timestamp}\t{student_name}\t{student_id_number}\t{content}\t{source}\t{registration_status}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"all_conversations_optimized_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
        return {
            'status': 'success',
            'content': tsv_content,
            'filename': filename,
            'total_messages': len(messages),
            'unique_students': len(set(msg.student.id for msg in messages))
        }
        
    except Exception as e:
        logger.error(f"匯出所有對話錯誤: {e}")
        return {'status': 'error', 'error': str(e)}

def export_students_summary_tsv():
    """匯出學生摘要為TSV格式（優化版）"""
    try:
        from models import Student, Message
        
        students = list(Student.select())
        
        if not students:
            return {'status': 'no_data', 'error': '沒有找到學生資料'}
        
        # 生成TSV內容
        tsv_lines = ['學生姓名\t學號\t註冊時間\t最後活動\t對話總數\t註冊狀態\t參與度等級']
        
        for student in students:
            student_name = student.name or '未設定'
            student_id_number = getattr(student, 'student_id', '未設定')
            created_at = student.created_at.strftime('%Y-%m-%d') if student.created_at else '未知'
            last_active = student.last_active.strftime('%Y-%m-%d') if student.last_active else '從未活動'
            
            # 計算對話總數
            message_count = Message.select().where(Message.student == student).count()
            
            # 註冊狀態
            if hasattr(student, 'registration_step'):
                if student.registration_step == 0 and student.name and getattr(student, 'student_id', ''):
                    reg_status = '已完成'
                elif student.registration_step > 0:
                    reg_status = '進行中'
                else:
                    reg_status = '未完成'
            else:
                reg_status = '未知'
            
            # 參與度等級
            if message_count >= 20:
                engagement = "高度參與"
            elif message_count >= 10:
                engagement = "中度參與"
            elif message_count >= 5:
                engagement = "輕度參與"
            else:
                engagement = "極少參與"
            
            tsv_lines.append(f"{student_name}\t{student_id_number}\t{created_at}\t{last_active}\t{message_count}\t{reg_status}\t{engagement}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"students_summary_optimized_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
        return {
            'status': 'success',
            'content': tsv_content,
            'filename': filename,
            'total_students': len(students)
        }
        
    except Exception as e:
        logger.error(f"匯出學生摘要錯誤: {e}")
        return {'status': 'error', 'error': str(e)}

# =================== 匯出函數別名（向後相容性） ===================

# 舊版函數別名
export_student_questions_tsv = export_student_conversations_tsv
export_all_questions_tsv = export_all_conversations_tsv
export_class_analytics_tsv = export_students_summary_tsv
export_student_analytics_tsv = export_student_conversations_tsv

# =================== 模組匯出列表 ===================

__all__ = [
    # 核心AI功能
    'generate_ai_response',
    'generate_simple_ai_response',
    'generate_learning_suggestion', 
    'get_fallback_response',
    'get_fallback_suggestion',
    
    # 相容性AI函數
    'generate_ai_response_with_smart_fallback',
    'get_ai_response',
    
    # 模型管理
    'switch_to_available_model',
    'test_ai_connection',
    'get_quota_status', 
    'record_model_usage',
    
    # 分析功能
    'analyze_student_basic_stats',
    'analyze_student_patterns',
    'analyze_student_pattern',
    'update_student_stats',
    'get_student_conversation_summary',
    
    # 系統功能
    'get_system_stats',
    'get_system_status',
    'perform_system_health_check',
    
    # 匯出功能
    'export_student_conversations_tsv',
    'export_all_conversations_tsv', 
    'export_students_summary_tsv',
    'export_student_questions_tsv',
    'export_all_questions_tsv',
    'export_class_analytics_tsv',
    'export_student_analytics_tsv',
    
    # 常數
    'AVAILABLE_MODELS',
    'current_model_name'
]

# =================== 初始化檢查 ===================

def initialize_utils():
    """初始化工具模組"""
    try:
        logger.info("🔧 初始化 utils.py 模組...")
        
        # 檢查AI服務狀態
        if GEMINI_API_KEY:
            ai_status, ai_message = test_ai_connection()
            if ai_status:
                logger.info(f"✅ AI服務正常 - {ai_message}")
            else:
                logger.warning(f"⚠️ AI服務異常 - {ai_message}")
        else:
            logger.warning("⚠️ GEMINI_API_KEY 未設定")
        
        # 檢查模型統計
        quota_status = get_quota_status()
        logger.info(f"📊 AI使用統計 - 總呼叫: {quota_status['total_calls']}, 錯誤: {quota_status['total_errors']}")
        
        logger.info("✅ utils.py 模組初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ utils.py 模組初始化失敗: {e}")
        return False

# 自動初始化（僅在直接導入時執行）
if __name__ != '__main__':
    initialize_utils()

# =================== 版本說明 ===================

"""
EMI 智能教學助理系統 - utils.py 優化版
=====================================

🎯 優化重點:
- 🤖 與 app.py v4.0 完美兼容
- 📊 移除快取依賴，專注核心功能
- 🔧 保留所有必要功能，增強錯誤處理
- 🔄 完整向後相容性

✨ 主要功能:
- AI回應生成：與 app.py 的 generate_ai_response 函數完全兼容
- 學習建議：與 app.py 的 generate_learning_suggestion 函數完全兼容
- 基本分析：學生統計、對話摘要、註冊狀態追蹤
- 匯出功能：TSV格式資料下載，包含註冊狀態
- 系統監控：健康檢查、狀態統計、AI服務監控

🤖 AI配置:
- 主要模型：gemini-2.5-flash
- 備用模型：自動切換機制
- 回應限制：150字英文
- 學術風格：技術定義+實際應用

📊 統計優化:
- 基本統計：對話數、活動時間、註冊狀態
- 參與度評估：簡單分級（高/中/低）
- 匯出功能：TSV格式，包含註冊狀態欄位
- 健康檢查：AI服務、資料庫、註冊狀態

🔄 相容性保證:
- 保留所有舊函數名稱和介面
- 與現有 routes.py 完全相容
- 錯誤處理強化，穩定性提升
- 支援 app.py v4.0 的新註冊流程

🔧 主要改進:
- 與 app.py 函數簽名完全一致
- 增加註冊狀態相關統計和匯出
- 優化錯誤處理和日誌記錄
- 移除對快取系統的依賴
- 增強 AI 服務監控和自動切換

版本日期: 2025年6月29日
優化版本: v4.0
設計理念: 穩定、兼容、高效、專注核心功能
相容性: 與 app.py v4.0 完美配合
"""

# =================== utils.py 優化版 - 第3段結束 ===================
# =================== 程式檔案結束 ===================
