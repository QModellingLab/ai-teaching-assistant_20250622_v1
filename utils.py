# =================== utils.py 簡化版 - 第1段開始 ===================
# EMI智能教學助理系統 - 工具函數（簡化版）
# 簡化AI回應邏輯，專注核心功能
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

# =================== AI 模型配置（簡化版） ===================

# 取得 API 金鑰
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 簡化的模型配置
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

# 模型使用統計（簡化版）
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

# =================== 核心AI回應生成（簡化版） ===================

def generate_simple_ai_response(student_name, student_id, query):
    """生成簡化的AI回應（150字英文學術風格）"""
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

def generate_learning_suggestion(student_name, student_id, conversation_count=0):
    """生成學習建議（150字英文）"""
    try:
        if not GEMINI_API_KEY or not model:
            return get_fallback_suggestion(student_name, conversation_count)
        
        # 獲取學生最近對話（簡化版）
        try:
            from models import Student, Message
            messages = list(Message.select().where(
                Message.student_id == student_id
            ).order_by(Message.timestamp.desc()).limit(10))
            
            if messages:
                recent_conversations = "\n".join([
                    f"- {msg.content[:80]}..." for msg in messages[:5] if msg.content
                ])
            else:
                recent_conversations = "No recent conversations"
                
        except Exception as e:
            logger.warning(f"無法取得對話記錄: {e}")
            recent_conversations = "Unable to access conversation history"
        
        # 學習建議生成提示詞
        prompt = f"""Based on conversation history, provide learning advice in simple English (150 words max).

Student: {student_name}
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
            logger.info(f"✅ 學習建議生成成功 - 學生: {student_name}")
            return suggestion
        else:
            logger.error("❌ 學習建議生成失敗")
            record_model_usage(current_model_name, False)
            return get_fallback_suggestion(student_name, conversation_count)
            
    except Exception as e:
        logger.error(f"❌ 學習建議生成錯誤: {e}")
        record_model_usage(current_model_name, False)
        return get_fallback_suggestion(student_name, conversation_count)

def get_fallback_response(user_message):
    """備用回應生成器（簡化版）"""
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
    
    elif '?' in user_message:
        return "Great question! I can help explain AI concepts with practical examples. Could you specify which aspect interests you most?"
    
    else:
        return "I'm here to help with AI and technology topics! Feel free to ask about artificial intelligence, machine learning, or data applications."

def get_fallback_suggestion(student_name, conversation_count):
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
    
    return f"""📊 {student_name}'s Learning Progress

**Current Status**: You are {activity_level} with {conversation_count} conversations.

**Strengths**: Shows curiosity about AI and technology topics. Demonstrates willingness to learn new concepts.

**Suggestions**: {suggestion}

**Tip**: Regular engagement helps reinforce learning. Try connecting AI concepts to real-world examples you encounter daily!"""

# =================== 模型管理（簡化版） ===================

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
    """切換到可用模型（簡化版）"""
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
    """測試AI連接（簡化版）"""
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
    """取得配額狀態（簡化版）"""
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

# =================== 基本分析功能（簡化版） ===================

def analyze_student_basic_stats(student_id):
    """分析學生基本統計（簡化版）"""
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
            earliest = min(msg.timestamp for msg in messages if msg.timestamp)
            latest = max(msg.timestamp for msg in messages if msg.timestamp)
            active_days = (latest - earliest).days + 1 if earliest and latest else 1
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
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'student_id_number': getattr(student, 'student_id', ''),
            'total_messages': total_messages,
            'active_days': active_days,
            'engagement_level': engagement,
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
    """取得系統統計（簡化版）"""
    try:
        from models import Student, Message
        
        stats = {
            'students': {
                'total': Student.select().count(),
                'active_this_week': 0,
                'registered': Student.select().where(
                    Student.registration_step == 0
                ).count() if hasattr(Student, 'registration_step') else 0,
                'need_registration': Student.select().where(
                    Student.registration_step > 0
                ).count() if hasattr(Student, 'registration_step') else 0,
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
        
        # 計算本週活躍學生
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        stats['students']['active_this_week'] = Student.select().where(
            Student.last_active.is_null(False) & 
            (Student.last_active >= week_ago)
        ).count()
        
        # 計算今日訊息
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stats['messages']['today'] = Message.select().where(
            Message.timestamp >= today_start
        ).count()
        
        # 計算本週訊息
        stats['messages']['this_week'] = Message.select().where(
            Message.timestamp >= week_ago
        ).count()
        
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
    """取得學生對話摘要（簡化版）"""
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
        student_messages = [msg for msg in messages if msg.source_type == 'line']
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

# =================== utils.py 簡化版 - 第1段結束 ===================

# =================== utils.py 簡化版 - 第2段開始 ===================
# 下載功能和相容性函數

# =================== 簡化的匯出功能 ===================

def export_student_conversations_tsv(student_id):
    """匯出學生對話記錄為TSV格式（簡化版）"""
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
        tsv_lines = ['時間\t學生姓名\t學號\t訊息內容\t來源類型']
        
        for msg in messages:
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else '未知時間'
            student_name = student.name or '未知學生'
            student_id_number = getattr(student, 'student_id', '未設定')
            content = msg.content.replace('\n', ' ').replace('\t', ' ')[:500]  # 限制長度
            source = '學生' if msg.source_type == 'line' else 'AI助理'
            
            tsv_lines.append(f"{timestamp}\t{student_name}\t{student_id_number}\t{content}\t{source}")
        
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
    """匯出所有對話記錄為TSV格式（簡化版）"""
    try:
        from models import Student, Message
        
        # 取得所有對話記錄
        messages = list(Message.select().join(Student).order_by(Message.timestamp.desc()))
        
        if not messages:
            return {'status': 'no_data', 'error': '沒有找到任何對話記錄'}
        
        # 生成TSV內容
        tsv_lines = ['時間\t學生姓名\t學號\t訊息內容\t來源類型']
        
        for msg in messages:
            student = msg.student
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else '未知時間'
            student_name = student.name or '未知學生'
            student_id_number = getattr(student, 'student_id', '未設定')
            content = msg.content.replace('\n', ' ').replace('\t', ' ')[:500]  # 限制長度
            source = '學生' if msg.source_type == 'line' else 'AI助理'
            
            tsv_lines.append(f"{timestamp}\t{student_name}\t{student_id_number}\t{content}\t{source}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"all_conversations_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
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
    """匯出學生摘要為TSV格式（簡化版）"""
    try:
        from models import Student, Message
        
        students = list(Student.select())
        
        if not students:
            return {'status': 'no_data', 'error': '沒有找到學生資料'}
        
        # 生成TSV內容
        tsv_lines = ['學生姓名\t學號\t註冊時間\t最後活動\t對話總數\t註冊狀態']
        
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
            
            tsv_lines.append(f"{student_name}\t{student_id_number}\t{created_at}\t{last_active}\t{message_count}\t{reg_status}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"students_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
        return {
            'status': 'success',
            'content': tsv_content,
            'filename': filename,
            'total_students': len(students)
        }
        
    except Exception as e:
        logger.error(f"匯出學生摘要錯誤: {e}")
        return {'status': 'error', 'error': str(e)}

# =================== 系統健康檢查（簡化版） ===================

def perform_system_health_check():
    """執行系統健康檢查（簡化版）"""
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
    """取得系統狀態摘要（簡化版）"""
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

# =================== 相容性函數（向後兼容） ===================

# 保持與原版本的相容性
def generate_ai_response_with_smart_fallback(student_id, query, conversation_context="", student_context="", group_id=None):
    """相容性函數：舊版AI回應生成"""
    try:
        from models import Student
        student = Student.get_by_id(student_id) if student_id else None
        student_name = student.name if student else "Unknown"
        
        return generate_simple_ai_response(student_name, student_id, query)
    except Exception as e:
        logger.error(f"相容性AI回應錯誤: {e}")
        return get_fallback_response(query)

def analyze_student_patterns(student_id):
    """相容性函數：學生模式分析"""
    return analyze_student_basic_stats(student_id)

def update_student_stats(student_id):
    """更新學生統計（簡化版）"""
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return False
        
        # 更新訊息計數
        student.update_message_count()
        
        # 更新活動時間
        student.update_activity()
        
        logger.info(f"✅ 學生統計已更新 - {student.name}")
        return True
        
    except Exception as e:
        logger.error(f"更新學生統計錯誤: {e}")
        return False

# 舊版函數別名（保持相容性）
generate_ai_response = generate_ai_response_with_smart_fallback
get_ai_response = generate_ai_response_with_smart_fallback
analyze_student_pattern = analyze_student_patterns

# 匯出函數別名
export_student_questions_tsv = export_student_conversations_tsv
export_all_questions_tsv = export_all_conversations_tsv
export_class_analytics_tsv = export_students_summary_tsv
export_student_analytics_tsv = export_student_conversations_tsv

# =================== 模組匯出列表 ===================

__all__ = [
    # 核心AI功能
    'generate_simple_ai_response',
    'generate_learning_suggestion', 
    'get_fallback_response',
    'get_fallback_suggestion',
    
    # 相容性AI函數
    'generate_ai_response_with_smart_fallback',
    'generate_ai_response',
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

# =================== 版本說明 ===================

"""
EMI 智能教學助理系統 - utils.py 簡化版
=====================================

🎯 簡化重點:
- 🤖 AI回應簡化：150字英文學術風格
- 📊 移除複雜分析：專注基本統計
- 🔧 保留核心功能：AI生成、匯出、健康檢查
- 🔄 向後相容：保留舊函數名稱和介面

✨ 主要功能:
- AI回應生成：符合EMI課程需求的簡潔回應
- 學習建議：150字英文個人化建議
- 基本分析：學生統計、對話摘要
- 匯出功能：TSV格式資料下載
- 系統監控：健康檢查、狀態統計

🤖 AI配置:
- 主要模型：gemini-2.5-flash
- 備用模型：自動切換機制
- 回應限制：150字英文
- 學術風格：技術定義+實際應用

📊 分析簡化:
- 基本統計：對話數、活動時間
- 參與度評估：簡單分級（高/中/低）
- 匯出功能：TSV格式，包含必要欄位

🔄 相容性:
- 保留所有舊函數名稱
- 介面保持一致
- 錯誤處理強化

版本日期: 2025年6月29日
簡化版本: v3.0
設計理念: 簡潔、實用、穩定、高效
"""

# =================== utils.py 簡化版 - 第2段結束 ===================
# =================== 程式檔案結束 ===================
