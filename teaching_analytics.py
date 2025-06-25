# teaching_analytics.py - 教學分析核心功能（英文版本）
# 包含：英文對話摘要、個人化建議、班級分析

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
            logger.warning(f"⚠️ 切換到模型 {next_model_name} 失敗: {e}")
            continue
    
    logger.error("❌ 無法切換到任何可用的分析模型")
    return False

def execute_with_fallback(func, *args, **kwargs):
    """使用備案機制執行分析函數"""
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            if not current_analytics_model:
                initialize_analytics_model()
            
            if current_analytics_model:
                return func(current_analytics_model, *args, **kwargs)
            else:
                raise Exception("No analytics model available")
                
        except Exception as e:
            logger.error(f"❌ 分析函數執行失敗 (嘗試 {attempt + 1}/{max_attempts}): {e}")
            
            if attempt < max_attempts - 1:
                # 嘗試切換模型
                if switch_analytics_model():
                    logger.info(f"🔄 已切換模型，重新嘗試...")
                    continue
                else:
                    logger.error("❌ 無法切換模型，停止重試")
                    break
    
    # 所有嘗試都失敗，返回錯誤狀態
    return {'status': 'error', 'error': '所有分析模型都無法使用'}

# =================== 英文對話摘要功能 ===================

def _generate_conversation_summary_internal(model, student_id, days=30):
    """內部對話摘要生成函數 - 英文版本"""
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
    
    # 修改：生成英文教學重點摘要
    summary_prompt = f"""As an EMI (English-Medium Instruction) educational analyst using {analytics_model_name}, analyze this student's conversation patterns and provide teaching insights in English:

Student Profile:
- Name: {student.name}
- Participation Rate: {student.participation_rate}%
- Total Messages in Period: {len(messages)}
- Analysis Period: {days} days
- Analysis Model: {analytics_model_name}

Recent Conversation Sample:
{chr(10).join(conversation_text[-10:])}

Please provide a comprehensive English teaching summary with these sections:

**🎯 Key Learning Topics:**
[Main subjects and concepts the student has engaged with during this period]

**📈 Academic Progress:**
[Assessment of student's learning development and comprehension level]

**💡 Teaching Recommendations:**
[Specific pedagogical suggestions for continued learning and areas to focus on]

**🔍 Learning Behavior Patterns:**
[Observable patterns in how this student learns, asks questions, and participates]

**📊 Engagement Analysis:**
[Quality and frequency of student participation and interaction]

Please write in clear, professional English suitable for EMI instructors. Keep the summary comprehensive but focused, approximately 300-400 words."""

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
            'language': 'english',  # 標記為英文摘要
            'status': 'success'
        }
    else:
        # 英文備用摘要
        fallback_summary = f"""**Teaching Summary for {student.name}**

**🎯 Key Learning Topics:**
During the {days}-day analysis period, this student engaged in {len(messages)} interactions, demonstrating involvement in English language learning activities. The student's communication pattern shows {'high engagement' if student.participation_rate > 70 else 'moderate engagement' if student.participation_rate > 40 else 'developing engagement'}.

**📈 Academic Progress:**
The student maintains a participation rate of {student.participation_rate}%, indicating {'strong academic engagement' if student.participation_rate > 70 else 'satisfactory progress' if student.participation_rate > 40 else 'need for additional encouragement'} in the EMI learning environment.

**💡 Teaching Recommendations:**
Based on the interaction patterns, recommend {'maintaining current engagement strategies' if student.participation_rate > 70 else 'implementing more interactive activities to boost participation' if student.participation_rate > 40 else 'providing additional support and encouragement'}.

**🔍 Learning Behavior Patterns:**
The student demonstrates {'consistent participation' if len(messages) > 10 else 'moderate participation' if len(messages) > 5 else 'limited but meaningful participation'} in learning activities.

**📊 Engagement Analysis:**
Overall academic engagement is {'excellent' if student.participation_rate > 80 else 'good' if student.participation_rate > 60 else 'satisfactory'} with room for continued development in English-medium instruction settings."""
        
        return {
            'student_id': student_id,
            'student_name': student.name,  
            'summary': fallback_summary,
            'model_used': 'fallback_english',
            'message_count': len(messages),
            'analysis_period_days': days,
            'generated_at': datetime.datetime.now().isoformat(),
            'language': 'english',
            'status': 'fallback_used'
        }

def generate_conversation_summary(student_id, days=30):
    """生成學生對話摘要（支援備案機制）- 英文版本"""
    return execute_with_fallback(_generate_conversation_summary_internal, student_id, days)

# =================== 英文個人化學習建議功能 ===================

def _generate_personalized_recommendations_internal(model, student_id):
    """內部個人化建議生成函數 - 英文版本"""
    student = Student.get_by_id(student_id)
    
    # 收集學生資料
    messages = list(Message.select().where(Message.student_id == student_id).limit(20))
    analyses = list(Analysis.select().where(Analysis.student_id == student_id).limit(10))
    
    if len(messages) < 3:
        return {'status': 'insufficient_data', 'message_count': len(messages)}
    
    # 修改：構建英文學生檔案
    student_context = f"""
Student Profile for EMI Analysis:
- Name: {student.name}
- Total Messages: {student.message_count}
- Questions Asked: {student.question_count}
- Participation Rate: {student.participation_rate}%
- Recent Activity: {len(messages)} recent messages
- Analysis Records: {len(analyses)} records
- Learning Context: English-Medium Instruction (EMI) environment
    """
    
    # 修改：英文建議生成 prompt
    recommendations_prompt = f"""As an experienced EMI (English-Medium Instruction) educator using {analytics_model_name}, provide personalized English learning recommendations for this student:

{student_context}

Sample Recent Messages:
{chr(10).join([f"- {msg.content[:80]}..." for msg in messages[-5:]])}

Please generate specific, actionable recommendations in English for these areas:

**📚 Academic Focus Areas:**
[Specific English language skills and subjects this student should prioritize]

**🎯 Learning Strategies:**
[Recommended approaches to increase this student's engagement and comprehension in EMI courses]

**💡 Next Learning Steps:**
[Concrete actions and goals for continued academic progress]

**⚠️ Areas Requiring Attention:**
[Potential challenges or skills needing additional support and practice]

**🔧 Instructional Approaches:**
[Specific teaching methods and techniques that would benefit this student]

Format as practical, implementable suggestions in professional English for both student and EMI instructor use (approximately 250-350 words)."""

    response = model.generate_content(recommendations_prompt)
    
    if response and response.text:
        return {
            'student_id': student_id,
            'student_name': student.name,
            'recommendations': response.text,
            'model_used': analytics_model_name,
            'data_points': len(messages) + len(analyses),
            'generated_at': datetime.datetime.now().isoformat(),
            'language': 'english',
            'status': 'success'
        }
    else:
        # 英文備用建議
        fallback_recommendations = f"""**Personalized Learning Recommendations for {student.name}**

**📚 Academic Focus Areas:**
Based on {len(messages)} interactions, this student should focus on {'advanced English communication skills' if student.participation_rate > 70 else 'foundational English language development' if student.participation_rate > 40 else 'basic English interaction and confidence building'}.

**🎯 Learning Strategies:**
Implement {'collaborative learning approaches' if len(messages) > 10 else 'structured individual practice' if len(messages) > 5 else 'guided learning with frequent feedback'} to enhance engagement in the EMI environment.

**💡 Next Learning Steps:**
1. {'Continue current engagement patterns' if student.participation_rate > 70 else 'Increase participation frequency' if student.participation_rate > 40 else 'Build confidence through supported practice'}
2. Focus on specific skill areas identified through interaction patterns
3. Set measurable learning goals for the next academic period

**⚠️ Areas Requiring Attention:**
{'Maintain current momentum' if student.participation_rate > 70 else 'Address participation barriers' if student.participation_rate > 40 else 'Provide additional language support and encouragement'}.

**🔧 Instructional Approaches:**
Use {'peer collaboration and advanced discussion' if student.participation_rate > 70 else 'structured activities with clear expectations' if student.participation_rate > 40 else 'supportive, low-pressure learning environments'} to maximize learning outcomes."""
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'recommendations': fallback_recommendations,
            'model_used': 'fallback_english',
            'data_points': len(messages) + len(analyses),
            'generated_at': datetime.datetime.now().isoformat(),
            'language': 'english',
            'status': 'fallback_used'
        }

def generate_personalized_recommendations(student_id):
    """生成個人化學習建議（支援備案機制）- 英文版本"""
    return execute_with_fallback(_generate_personalized_recommendations_internal, student_id)

# =================== 英文班級整體分析功能 ===================

def _generate_class_analysis_internal(model):
    """內部班級分析函數 - 英文版本"""
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
    
    # 修改：英文班級分析 prompt
    class_context = f"""
EMI Class Overview:
- Total Students: {len(real_students)}
- Total Messages: {total_messages}
- Total Questions: {total_questions}
- Average Participation Rate: {avg_participation:.1f}%
- Recent Activity (7 days): {recent_messages} messages
- Most Active Students: {[s.name for s in sorted(real_students, key=lambda x: x.participation_rate, reverse=True)[:3]]}
- Analysis Date: {datetime.datetime.now().strftime('%Y-%m-%d')}
- Learning Environment: English-Medium Instruction (EMI)
    """
    
    class_analysis_prompt = f"""As an experienced EMI (English-Medium Instruction) educational analyst using {analytics_model_name}, analyze this class performance data and provide comprehensive insights in English:

{class_context}

Provide a detailed English class analysis covering these areas:

**📊 Overall Class Performance:**
[Assessment of overall class engagement, participation patterns, and learning progress in the EMI environment]

**🎯 Class Strengths:**
[What this class is excelling at in terms of English language learning and participation]

**⚠️ Areas for Class Improvement:**
[Specific challenges and areas where the class needs focused attention and support]

**💡 Recommended Teaching Strategies:**
[Evidence-based EMI teaching approaches to enhance class learning and engagement]

**📈 Learning Development Trends:**
[Observable patterns in class progress and suggestions for future academic growth]

**🔧 Implementation Guidelines:**
[Specific, actionable recommendations for improved EMI class outcomes]

Format as a comprehensive professional educational analysis in English for EMI instructors and academic administrators (approximately 400-500 words)."""

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
            'language': 'english',
            'status': 'success'
        }
    else:
        # 英文備用班級分析
        fallback_analysis = f"""**EMI Class Performance Analysis**

**📊 Overall Class Performance:**
This EMI class consists of {len(real_students)} students with a collective total of {total_messages} messages and {total_questions} questions. The average participation rate of {avg_participation:.1f}% indicates {'high overall engagement' if avg_participation > 70 else 'moderate class participation' if avg_participation > 50 else 'developing class engagement'} in English-medium instruction activities.

**🎯 Class Strengths:**
The class demonstrates {'strong collaborative learning' if recent_messages > 20 else 'steady academic progress' if recent_messages > 10 else 'emerging participation patterns'} with {recent_messages} recent interactions. Students show {'active questioning behavior' if total_questions > total_messages * 0.3 else 'balanced communication patterns'} in the EMI environment.

**⚠️ Areas for Class Improvement:**
Focus needed on {'maintaining current momentum' if avg_participation > 70 else 'increasing overall participation rates' if avg_participation > 50 else 'building foundational engagement and confidence'}. Consider implementing strategies to support less active students.

**💡 Recommended Teaching Strategies:**
1. {'Advanced collaborative projects' if avg_participation > 70 else 'Structured group activities' if avg_participation > 50 else 'Supported individual practice with peer interaction'}
2. Implement regular formative assessment to track progress
3. Use diverse EMI teaching methods to accommodate different learning styles
4. Encourage peer-to-peer learning and support

**📈 Learning Development Trends:**
The class shows {'excellent progress' if avg_participation > 70 else 'positive development' if avg_participation > 50 else 'steady growth potential'} in EMI learning outcomes. Recent activity patterns suggest {'sustained engagement' if recent_messages > 15 else 'developing consistency'}.

**🔧 Implementation Guidelines:**
- Monitor individual student progress within class context
- Adjust instruction pace based on overall class comprehension
- Provide additional support for students below average participation
- Celebrate class achievements to maintain motivation"""
        
        return {
            'class_analysis': fallback_analysis,
            'model_used': 'fallback_english',
            'student_count': len(real_students),
            'data_summary': {
                'total_messages': total_messages,
                'total_questions': total_questions,
                'avg_participation': round(avg_participation, 1),
                'recent_activity': recent_messages
            },
            'generated_at': datetime.datetime.now().isoformat(),
            'language': 'english',
            'status': 'fallback_used'
        }

def generate_class_analysis():
    """生成班級整體分析（支援備案機制）- 英文版本"""
    return execute_with_fallback(_generate_class_analysis_internal)

# =================== 系統狀態和工具函數 ===================

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

# =================== 初始化和匯出 ===================

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
