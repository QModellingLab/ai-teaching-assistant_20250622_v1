# teaching_analytics.py - 教學分析核心功能（優先順序備案機制版）
# 包含：對話摘要、個人化建議、班級分析

import os
import json
import datetime
import logging
from collections import defaultdict, Counter
import google.generativeai as genai
from models import Student, Message, Analysis, db

logger = logging.getLogger(__name__)

# =================== 教學分析專用模型配置 ===================

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# 教學分析專用模型優先順序（基於分析一致性和配額考量）
ANALYTICS_MODELS = [
    "gemini-2.0-flash",        # 🥇 首選：最新版本 + 高配額(200次/日)
    "gemini-2.0-flash-lite",   # 🥈 備案1：輕量但一致的分析能力
    "gemini-1.5-flash",        # 🥉 備案2：穩定可靠的分析
    "gemini-1.5-flash-8b",     # 🏅 備案3：效率優化版本
    "gemini-1.5-pro",          # 🏅 備案4：深度分析能力
]

# 當前分析模型狀態
current_analytics_model = None
analytics_model_name = "gemini-2.0-flash"  # 預設首選
model_switch_count = 0

def initialize_analytics_model():
    """初始化教學分析模型（支援優先順序切換）"""
    global current_analytics_model, analytics_model_name
    
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY 未設定")
        return None
    
    # 按優先順序嘗試初始化模型
    for model_name in ANALYTICS_MODELS:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            test_model = genai.GenerativeModel(model_name)
            
            # 測試模型是否可用（簡單測試）
            test_response = test_model.generate_content("Test connection")
            
            if test_response and test_response.text:
                current_analytics_model = test_model
                analytics_model_name = model_name
                logger.info(f"✅ 教學分析模型初始化成功: {model_name}")
                return test_model
                
        except Exception as e:
            logger.warning(f"⚠️ 模型 {model_name} 初始化失敗: {e}")
            continue
    
    logger.error("❌ 所有教學分析模型都無法初始化")
    return None

def switch_analytics_model():
    """切換到下一個可用的分析模型"""
    global current_analytics_model, analytics_model_name, model_switch_count
    
    if not GEMINI_API_KEY:
        return False
    
    current_index = ANALYTICS_MODELS.index(analytics_model_name) if analytics_model_name in ANALYTICS_MODELS else 0
    
    # 嘗試下一個模型
    for i in range(1, len(ANALYTICS_MODELS)):
        next_index = (current_index + i) % len(ANALYTICS_MODELS)
        next_model_name = ANALYTICS_MODELS[next_index]
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            new_model = genai.GenerativeModel(next_model_name)
            # 簡單測試
            test_response = new_model.generate_content("Hello")
            
            if test_response and test_response.text:
                current_analytics_model = new_model
                analytics_model_name = next_model_name
                model_switch_count += 1
                logger.info(f"🔄 教學分析模型切換成功: {next_model_name} (第{model_switch_count}次切換)")
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ 切換至模型 {next_model_name} 失敗: {e}")
            continue
    
    logger.error("❌ 無法切換到任何可用的分析模型")
    return False

def get_analytics_model():
    """取得當前分析模型（自動初始化或切換）"""
    global current_analytics_model
    
    if current_analytics_model is None:
        current_analytics_model = initialize_analytics_model()
    
    return current_analytics_model

def execute_with_fallback(analysis_function, *args, **kwargs):
    """執行分析功能，支援模型切換備案"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            model = get_analytics_model()
            if not model:
                return {'error': 'No analytics model available'}
            
            # 執行分析功能
            return analysis_function(model, *args, **kwargs)
            
        except Exception as e:
            logger.warning(f"⚠️ 分析執行失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # 嘗試切換模型
                if switch_analytics_model():
                    logger.info("🔄 已切換分析模型，重新執行...")
                    continue
                else:
                    logger.error("❌ 無法切換模型，分析失敗")
                    break
    
    return {'error': f'Analysis failed after {max_retries} attempts'}

# =========================================
# 1. 智能對話摘要功能
# =========================================

def _generate_conversation_summary_internal(model, student_id, days=30):
    """內部對話摘要生成函數"""
    student = Student.get_by_id(student_id)
    
    # 取得指定期間的對話
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    messages = list(Message.select().where(
        (Message.student_id == student_id) &
        (Message.timestamp > cutoff_date)
    ).order_by(Message.timestamp.asc()))
    
    if len(messages) < 3:
        return {'status': 'insufficient_data', 'message_count': len(messages)}
    
    # 構建對話內容
    conversation_text = []
    for msg in messages:
        if msg.message_type in ['question', 'statement']:
            conversation_text.append(f"Student: {msg.content[:100]}")
    
    # 生成教學重點摘要 - 加入模型資訊以確保一致性
    summary_prompt = f"""As an educational expert using {analytics_model_name}, analyze this student's conversation patterns for teaching insights:

Student: {student.name}
Participation Rate: {student.participation_rate}%
Total Messages: {len(messages)}
Analysis Model: {analytics_model_name}

Recent Conversation Excerpts:
{chr(10).join(conversation_text[-10:])}

Create a teaching-focused summary with these sections:

**🎯 Key Topics Discussed:**
[Main subjects and concepts the student engaged with]

**📈 Understanding Level:**
[Assessment of student's current comprehension and learning progress]

**💡 Teaching Recommendations:**
[Specific suggestions for continued learning and areas to focus on]

**🔍 Learning Patterns:**
[Observable patterns in how this student learns and asks questions]

Format as clear, actionable insights for EMI instructors (max 250 words):"""

    response = model.generate_content(summary_prompt)
    
    if response and response.text:
        return {
            'student_id': student_id,
            'student_name': student.name,
            'summary': response.text,
            'model_used': analytics_model_name,
            'message_count': len(messages),
            'analysis_period_days': days,
            'generated_at': datetime.datetime.now().isoformat(),
            'status': 'success'
        }
    else:
        raise Exception("Model response was empty or invalid")

def generate_conversation_summary(student_id, days=30):
    """生成學生對話摘要（支援備案機制）"""
    return execute_with_fallback(_generate_conversation_summary_internal, student_id, days)

# =========================================
# 2. 個人化學習建議功能
# =========================================

def _generate_personalized_recommendations_internal(model, student_id):
    """內部個人化建議生成函數"""
    student = Student.get_by_id(student_id)
    
    # 收集學生資料
    messages = list(Message.select().where(Message.student_id == student_id).limit(20))
    analyses = list(Analysis.select().where(Analysis.student_id == student_id).limit(10))
    
    if len(messages) < 3:
        return {'status': 'insufficient_data', 'message_count': len(messages)}
    
    # 構建學生檔案
    student_context = f"""
Student Profile:
- Name: {student.name}
- Total Messages: {student.message_count}
- Questions Asked: {student.question_count}
- Participation Rate: {student.participation_rate}%
- Recent Activity: {len(messages)} recent messages
- Analysis Records: {len(analyses)} records
    """
    
    recommendations_prompt = f"""As an EMI educational expert using {analytics_model_name}, provide personalized learning recommendations:

{student_context}

Recent Messages Sample:
{chr(10).join([f"- {msg.content[:80]}..." for msg in messages[-5:]])}

Generate specific, actionable recommendations in these areas:

**📚 Learning Focus Areas:**
[Specific topics or skills this student should focus on]

**🎯 Engagement Strategies:**
[Methods to increase this student's participation and motivation]

**💡 Next Steps:**
[Concrete actions for continued learning progress]

**⚠️ Areas for Attention:**
[Potential challenges or areas needing extra support]

Format as practical, implementable suggestions for both student and instructor (max 300 words):"""

    response = model.generate_content(recommendations_prompt)
    
    if response and response.text:
        return {
            'student_id': student_id,
            'student_name': student.name,
            'recommendations': response.text,
            'model_used': analytics_model_name,
            'data_points': len(messages) + len(analyses),
            'generated_at': datetime.datetime.now().isoformat(),
            'status': 'success'
        }
    else:
        raise Exception("Model response was empty or invalid")

def generate_personalized_recommendations(student_id):
    """生成個人化學習建議（支援備案機制）"""
    return execute_with_fallback(_generate_personalized_recommendations_internal, student_id)

# =========================================
# 3. 班級整體分析功能
# =========================================

def _generate_class_analysis_internal(model):
    """內部班級分析函數"""
    # 取得所有真實學生資料
    real_students = list(Student.select().where(
        ~Student.name.startswith('[DEMO]') & 
        ~Student.line_user_id.startswith('demo_')
    ))
    
    if len(real_students) < 2:
        return {'status': 'insufficient_students', 'student_count': len(real_students)}
    
    # 計算班級統計
    total_messages = sum(s.message_count for s in real_students)
    total_questions = sum(s.question_count for s in real_students)
    avg_participation = sum(s.participation_rate for s in real_students) / len(real_students)
    
    # 取得近期活動
    recent_messages = Message.select().where(
        Message.timestamp > datetime.datetime.now() - datetime.timedelta(days=7)
    ).count()
    
    class_context = f"""
Class Overview:
- Total Students: {len(real_students)}
- Total Messages: {total_messages}
- Total Questions: {total_questions}
- Average Participation: {avg_participation:.1f}%
- Recent Activity (7 days): {recent_messages} messages
- Most Active Students: {[s.name for s in sorted(real_students, key=lambda x: x.participation_rate, reverse=True)[:3]]}
- Analysis Date: {datetime.datetime.now().strftime('%Y-%m-%d')}
    """
    
    class_analysis_prompt = f"""As an EMI educational analyst using {analytics_model_name}, analyze this class performance:

{class_context}

Provide comprehensive class insights:

**📊 Overall Performance:**
[Assessment of class engagement and learning progress]

**🎯 Strengths:**
[What the class is doing well in terms of participation and learning]

**⚠️ Areas for Improvement:**
[Specific challenges and areas needing attention]

**💡 Teaching Strategies:**
[Recommended approaches to enhance class learning and engagement]

**📈 Next Steps:**
[Actionable recommendations for improved class outcomes]

Format as professional educational analysis for instructor review (max 400 words):"""

    response = model.generate_content(class_analysis_prompt)
    
    if response and response.text:
        return {
            'class_analysis': response.text,
            'model_used': analytics_model_name,
            'student_count': len(real_students),
            'data_summary': {
                'total_messages': total_messages,
                'total_questions': total_questions,
                'avg_participation': round(avg_participation, 1),
                'recent_activity': recent_messages
            },
            'generated_at': datetime.datetime.now().isoformat(),
            'status': 'success'
        }
    else:
        raise Exception("Model response was empty or invalid")

def generate_class_analysis():
    """生成班級整體分析（支援備案機制）"""
    return execute_with_fallback(_generate_class_analysis_internal)

# =========================================
# 4. 系統狀態和工具函數
# =========================================

def get_analytics_status():
    """取得分析系統狀態"""
    return {
        'current_model': analytics_model_name,
        'model_switches': model_switch_count,
        'available_models': ANALYTICS_MODELS,
        'model_initialized': current_analytics_model is not None,
        'api_key_configured': GEMINI_API_KEY is not None,
        'system_status': 'ready' if current_analytics_model else 'initializing'
    }

def build_comprehensive_student_profile(student_id):
    """建立綜合學生檔案"""
    try:
        student = Student.get_by_id(student_id)
        
        # 收集所有相關資料
        messages = list(Message.select().where(Message.student_id == student_id))
        analyses = list(Analysis.select().where(
            (Analysis.student_id == student_id) &
            (Analysis.analysis_type == 'question_classification')
        ))
        
        profile = {
            'student_info': {
                'id': student.id,
                'name': student.name,
                'participation_rate': student.participation_rate,
                'question_count': student.question_count,
                'message_count': student.message_count,
                'learning_period_days': (datetime.datetime.now() - student.created_at).days if student.created_at else 0
            },
            'data_summary': {
                'total_messages': len(messages),
                'total_analyses': len(analyses),
                'data_quality': 'sufficient' if len(messages) >= 5 else 'limited'
            },
            'model_info': {
                'current_model': analytics_model_name,
                'model_switches': model_switch_count
            },
            'profile_generated': datetime.datetime.now().isoformat()
        }
        
        return profile
        
    except Exception as e:
        logger.error(f"學生檔案建立錯誤: {e}")
        return {'error': str(e)}

# =========================================
# 5. 初始化和匯出
# =========================================

# 初始化分析模型
logger.info("🔬 初始化教學分析系統...")
initialize_analytics_model()

# 匯出主要函數
__all__ = [
    'generate_conversation_summary',
    'generate_personalized_recommendations', 
    'generate_class_analysis',
    'build_comprehensive_student_profile',
    'get_analytics_status',
    'switch_analytics_model'
]
