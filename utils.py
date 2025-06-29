# =================== utils.py 增強版 - 第1段開始 ===================
# EMI智能教學助理系統 - 工具函數（記憶功能增強版）
# 配合 app.py v4.1 記憶功能版使用
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

# =================== AI 模型配置（記憶功能增強版） ===================

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

# 模型使用統計（增強版）
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

# =================== 記憶功能相關輔助函數（新增）===================

def get_conversation_context(student, session=None, max_messages=10):
    """取得對話上下文（記憶功能核心輔助函數）"""
    try:
        from models import Message, ConversationSession
        
        context_messages = []
        
        if session:
            # 從指定會話取得最近訊息
            messages = list(Message.select().where(
                Message.session == session
            ).order_by(Message.timestamp.desc()).limit(max_messages))
        else:
            # 從學生所有訊息中取得最近訊息
            messages = list(Message.select().where(
                Message.student == student
            ).order_by(Message.timestamp.desc()).limit(max_messages))
        
        # 反轉順序（最舊的在前）
        messages.reverse()
        
        for msg in messages:
            context_messages.append({
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                'ai_response': getattr(msg, 'ai_response', None),
                'topic_tags': getattr(msg, 'topic_tags', '')
            })
        
        return {
            'messages': context_messages,
            'message_count': len(context_messages),
            'session_id': session.id if session else None
        }
        
    except Exception as e:
        logger.error(f"取得對話上下文錯誤: {e}")
        return {
            'messages': [],
            'message_count': 0,
            'session_id': None
        }

def extract_conversation_topics(messages):
    """從對話中提取主題（記憶功能輔助）"""
    topics = set()
    
    # 主題關鍵字字典
    topic_keywords = {
        'AI技術': ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural network'],
        '程式設計': ['python', 'programming', 'code', 'algorithm', 'software'],
        '英語學習': ['grammar', 'vocabulary', 'pronunciation', 'writing', 'speaking'],
        '商業管理': ['business', 'management', 'marketing', 'strategy', 'finance'],
        '數據分析': ['data', 'analysis', 'statistics', 'visualization', 'big data'],
        '學習方法': ['study', 'learning', 'education', 'research', 'academic']
    }
    
    for message in messages:
        if isinstance(message, dict):
            content = message.get('content', '').lower()
        else:
            content = getattr(message, 'content', '').lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content for keyword in keywords):
                topics.add(topic)
    
    return list(topics)

def build_context_summary(context_messages, student):
    """建立對話上下文摘要（記憶功能輔助）"""
    try:
        if not context_messages:
            return ""
        
        # 提取主要討論主題
        topics = extract_conversation_topics(context_messages)
        topic_str = "、".join(topics[:3]) if topics else "一般討論"
        
        # 計算對話特徵
        total_messages = len(context_messages)
        recent_questions = sum(1 for msg in context_messages[-5:] 
                             if isinstance(msg, dict) and '?' in msg.get('content', ''))
        
        # 生成簡潔的上下文摘要
        summary = f"之前與{student.name}討論了{topic_str}（{total_messages}則訊息"
        if recent_questions > 0:
            summary += f"，最近提出{recent_questions}個問題"
        summary += "）"
        
        return summary
        
    except Exception as e:
        logger.error(f"建立上下文摘要錯誤: {e}")
        return f"與{student.name}的學習討論"

# =================== 核心AI回應生成（記憶功能增強版）===================

def generate_ai_response_with_context(message_text, student, session=None):
    """生成帶記憶功能的AI回應（與app.py兼容）"""
    try:
        if not GEMINI_API_KEY or not model:
            return get_fallback_response(message_text)
        
        # 取得對話上下文
        context = get_conversation_context(student, session, max_messages=8)
        context_summary = build_context_summary(context['messages'], student)
        
        # 建構增強的提示詞（包含記憶功能）
        base_prompt = f"""You are an EMI (English as a Medium of Instruction) teaching assistant for "Practical Applications of AI in Life and Learning."

CONTEXT: {context_summary}

CURRENT STUDENT: {student.name} (ID: {getattr(student, 'student_id', 'Unknown')})
CURRENT QUESTION: {message_text}

INSTRUCTIONS:
- Reference previous topics naturally if relevant
- Provide educational responses in English (150 words max)
- Use academic language appropriate for university students
- Give practical examples when helpful
- Be encouraging and supportive

Response:"""

        # 如果有上下文，加入最近對話
        if context['messages']:
            recent_context = "\n".join([
                f"Previous: {msg['content'][:100]}..." 
                for msg in context['messages'][-3:] 
                if isinstance(msg, dict)
            ])
            base_prompt = base_prompt.replace(
                f"CONTEXT: {context_summary}",
                f"CONTEXT: {context_summary}\nRECENT CONVERSATION:\n{recent_context}"
            )
        
        # 生成配置
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            max_output_tokens=200
        )
        
        # 調用AI
        response = model.generate_content(base_prompt, generation_config=generation_config)
        
        if response and response.text:
            ai_response = response.text.strip()
            
            # 記錄成功使用
            record_model_usage(current_model_name, True)
            
            logger.info(f"✅ 記憶功能AI回應生成成功 - 學生: {student.name}, 上下文: {context['message_count']}則")
            
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
        logger.error(f"❌ 記憶功能AI回應生成錯誤: {e}")
        record_model_usage(current_model_name, False)
        
        # 智慧錯誤處理
        error_msg = str(e).lower()
        if "429" in error_msg or "quota" in error_msg:
            return "I'm currently at my usage limit. Please try again in a moment! 🤖"
        elif "403" in error_msg:
            return "I'm having authentication issues. Please contact your teacher. 🔧"
        else:
            return get_fallback_response(message_text)

def generate_ai_response(message_text, student):
    """生成AI回應（保持原有API兼容性）"""
    try:
        # 優先使用記憶功能版本
        return generate_ai_response_with_context(message_text, student)
        
    except Exception as e:
        logger.error(f"❌ AI 回應生成錯誤: {e}")
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

        # 生成配置
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            max_output_tokens=200
        )
        
        # 調用AI
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if response and response.text:
            ai_response = response.text.strip()
            
            # 記錄成功使用
            record_model_usage(current_model_name, True)
            
            logger.info(f"✅ 簡化AI回應生成成功 - 學生: {student_name}")
            
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
        logger.error(f"❌ 簡化AI回應生成錯誤: {e}")
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
    """生成學習建議（簡化版，與app.py兼容）"""
    try:
        # 獲取學生最近對話（包含會話資訊）
        try:
            from models import Message, ConversationSession
            
            # 取得最近對話
            messages = list(Message.select().where(
                Message.student == student
            ).order_by(Message.timestamp.desc()).limit(10))
            
            # 取得會話統計
            session_count = ConversationSession.select().where(
                ConversationSession.student == student
            ).count()
            
            if messages:
                conversation_count = len(messages)
                # 提取主題
                topics = extract_conversation_topics([{'content': msg.content} for msg in messages])
                topic_list = "、".join(topics[:3]) if topics else "一般學習主題"
            else:
                conversation_count = 0
                session_count = 0
                topic_list = "尚未開始討論"
                
        except Exception as e:
            logger.warning(f"無法取得對話記錄: {e}")
            conversation_count = 0
            session_count = 0
            topic_list = "無法取得歷史記錄"
        
        # 生成簡化的學習建議
        if conversation_count >= 15:
            activity_level = "actively engaged"
            suggestion = "Excellent participation! Continue exploring advanced topics and consider real-world applications."
        elif conversation_count >= 8:
            activity_level = "moderately engaged"  
            suggestion = "Good progress! Try asking more specific questions about topics that interest you."
        elif conversation_count >= 3:
            activity_level = "getting started"
            suggestion = "Welcome! Feel free to explore AI concepts and ask about practical applications."
        else:
            activity_level = "just beginning"
            suggestion = "Great to have you! Start by asking about AI applications you encounter daily."
        
        # 包含記憶功能相關資訊
        memory_info = f"({session_count} learning sessions)" if session_count > 0 else "(new learner)"
        
        learning_suggestion = f"""📊 **{student.name}'s Learning Overview**

🔹 **Activity Level**: You are {activity_level} {memory_info}
Recent conversations: {conversation_count} | Topics explored: {topic_list}

🔹 **Quick Suggestion**: {suggestion}

🔹 **Next Steps**: Consider discussing real-world applications of concepts you've learned.

💡 **Note**: For detailed learning history, ask your teacher to generate a comprehensive learning journey report."""
        
        return learning_suggestion
        
    except Exception as e:
        logger.error(f"學習建議生成失敗: {e}")
        return get_fallback_suggestion(student, 0)

def get_fallback_response(user_message):
    """備用回應生成器（增強版）"""
    user_msg_lower = user_message.lower()
    
    # 基於關鍵詞的簡單回應
    if any(word in user_msg_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm your AI assistant for our EMI course. I can remember our previous discussions. How can I help you today? 👋"
    
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
    
    elif any(word in user_msg_lower for word in ['memory', 'remember', 'previous']):
        return "I can remember our previous conversations! Feel free to reference earlier topics or build upon what we've discussed before."
    
    elif '?' in user_message:
        return "Great question! I can help explain AI concepts with practical examples. I also remember our previous discussions, so feel free to build on earlier topics!"
    
    else:
        return "I'm here to help with AI and technology topics! I can remember our conversation history, so feel free to ask follow-up questions or explore topics in depth."

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

**Tip**: With our memory feature, you can now build on previous discussions and explore topics in greater depth!"""

# =================== 模型管理（增強版） ===================

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
    """切換到可用模型（增強版）"""
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
    """測試AI連接（增強版）"""
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
    """取得配額狀態（增強版）"""
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

# =================== utils.py 增強版 - 第1段結束 ===================

# =================== utils.py 增強版 - 第2段開始 ===================
# 分析功能和系統統計（記憶功能增強版）

# =================== 會話管理輔助函數（新增）===================

def analyze_conversation_sessions(student_id):
    """分析學生的對話會話（記憶功能輔助）"""
    try:
        from models import Student, ConversationSession, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '學生不存在'}
        
        # 取得學生的所有會話
        sessions = list(ConversationSession.select().where(
            ConversationSession.student == student
        ).order_by(ConversationSession.session_start.desc()))
        
        if not sessions:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'total_sessions': 0,
                'active_sessions': 0,
                'average_session_length': 0,
                'total_session_messages': 0,
                'session_analysis': 'No conversation sessions found'
            }
        
        # 分析會話統計
        total_sessions = len(sessions)
        active_sessions = len([s for s in sessions if s.session_end is None])
        completed_sessions = total_sessions - active_sessions
        
        # 計算平均會話長度
        completed_session_lengths = []
        total_session_messages = 0
        
        for session in sessions:
            if hasattr(session, 'message_count') and session.message_count:
                total_session_messages += session.message_count
                if session.session_end:  # 已完成的會話
                    completed_session_lengths.append(session.message_count)
        
        average_session_length = (
            sum(completed_session_lengths) / len(completed_session_lengths)
            if completed_session_lengths else 0
        )
        
        # 分析會話模式
        if average_session_length >= 10:
            session_pattern = "深度討論型"
        elif average_session_length >= 5:
            session_pattern = "中等互動型"  
        elif average_session_length >= 2:
            session_pattern = "簡短諮詢型"
        else:
            session_pattern = "初步接觸型"
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'completed_sessions': completed_sessions,
            'average_session_length': round(average_session_length, 1),
            'total_session_messages': total_session_messages,
            'session_pattern': session_pattern,
            'latest_session': sessions[0].session_start.isoformat() if sessions else None,
            'analysis_date': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"會話分析錯誤: {e}")
        return {
            'student_id': student_id,
            'error': str(e),
            'analysis_date': datetime.datetime.now().isoformat()
        }

def get_learning_progression_analysis(student_id):
    """分析學生學習進展（學習歷程輔助）"""
    try:
        from models import Student, Message, ConversationSession
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '學生不存在'}
        
        # 取得所有訊息，按時間排序
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.asc()))
        
        if not messages:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'progression_analysis': 'No messages to analyze',
                'complexity_trend': 'unknown',
                'topic_evolution': []
            }
        
        # 分析複雜度趨勢
        early_messages = messages[:len(messages)//3] if len(messages) >= 6 else messages[:2]
        recent_messages = messages[-len(messages)//3:] if len(messages) >= 6 else messages[-2:]
        
        # 簡單的複雜度計算（基於訊息長度和問號數量）
        def calculate_complexity(msgs):
            if not msgs:
                return 0
            avg_length = sum(len(msg.content) for msg in msgs) / len(msgs)
            question_ratio = sum(1 for msg in msgs if '?' in msg.content) / len(msgs)
            return avg_length * 0.01 + question_ratio * 2
        
        early_complexity = calculate_complexity(early_messages)
        recent_complexity = calculate_complexity(recent_messages)
        
        if recent_complexity > early_complexity * 1.2:
            complexity_trend = "increasing"
        elif recent_complexity < early_complexity * 0.8:
            complexity_trend = "decreasing"
        else:
            complexity_trend = "stable"
        
        # 分析主題演進
        def get_period_topics(msgs):
            return extract_conversation_topics([{'content': msg.content} for msg in msgs])
        
        early_topics = get_period_topics(early_messages)
        recent_topics = get_period_topics(recent_messages)
        
        topic_evolution = {
            'early_topics': early_topics,
            'recent_topics': recent_topics,
            'topic_expansion': len(recent_topics) > len(early_topics),
            'new_topics': list(set(recent_topics) - set(early_topics))
        }
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'total_messages': len(messages),
            'analysis_period': {
                'start': messages[0].timestamp.isoformat(),
                'end': messages[-1].timestamp.isoformat()
            },
            'complexity_trend': complexity_trend,
            'early_complexity': round(early_complexity, 2),
            'recent_complexity': round(recent_complexity, 2),
            'topic_evolution': topic_evolution,
            'progression_summary': f"學習複雜度{complexity_trend}，主題{'擴展' if topic_evolution['topic_expansion'] else '專注'}",
            'analysis_date': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"學習進展分析錯誤: {e}")
        return {
            'student_id': student_id,
            'error': str(e),
            'analysis_date': datetime.datetime.now().isoformat()
        }

def get_learning_history_summary(student_id):
    """取得學習歷程摘要（學習歷程輔助）"""
    try:
        from models import Student, LearningHistory
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '學生不存在'}
        
        # 取得最新的學習歷程記錄
        latest_history = LearningHistory.select().where(
            LearningHistory.student == student
        ).order_by(LearningHistory.generated_at.desc()).first()
        
        if not latest_history:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'has_history': False,
                'summary': '尚未生成學習歷程',
                'last_generated': None
            }
        
        # 解析分析資料
        analysis_data = {}
        if latest_history.analysis_data:
            try:
                analysis_data = json.loads(latest_history.analysis_data)
            except:
                analysis_data = {}
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'has_history': True,
            'summary': latest_history.summary or '學習歷程摘要',
            'learning_topics': latest_history.learning_topics,
            'last_generated': latest_history.generated_at.isoformat() if latest_history.generated_at else None,
            'version': getattr(latest_history, 'version', 1),
            'topics_analysis': analysis_data.get('topics_analysis', {}),
            'key_interactions': analysis_data.get('key_interactions', [])
        }
        
    except Exception as e:
        logger.error(f"學習歷程摘要錯誤: {e}")
        return {
            'student_id': student_id,
            'error': str(e)
        }

# =================== 基本分析功能（增強版） ===================

def analyze_student_basic_stats(student_id):
    """分析學生基本統計（記憶功能增強版）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '學生不存在'}
        
        # 基本統計
        messages = list(Message.select().where(Message.student == student))
        total_messages = len(messages)
        
        # 會話統計（新增）
        try:
            total_sessions = ConversationSession.select().where(
                ConversationSession.student == student
            ).count()
            active_sessions = ConversationSession.select().where(
                ConversationSession.student == student,
                ConversationSession.session_end.is_null()
            ).count()
        except:
            total_sessions = 0
            active_sessions = 0
        
        # 學習歷程狀態（新增）
        try:
            has_learning_history = LearningHistory.select().where(
                LearningHistory.student == student
            ).exists()
        except:
            has_learning_history = False
        
        # 活動時間分析
        if messages:
            timestamps = [msg.timestamp for msg in messages if msg.timestamp]
            if timestamps:
                earliest = min(timestamps)
                latest = max(timestamps)
                active_days = (latest - earliest).days + 1
            else:
                active_days = 1
        else:
            active_days = 0
        
        # 參與度評估（增強版）
        if total_messages >= 20:
            engagement = "高度參與"
            engagement_score = 90
        elif total_messages >= 10:
            engagement = "中度參與"
            engagement_score = 70
        elif total_messages >= 5:
            engagement = "輕度參與"
            engagement_score = 50
        else:
            engagement = "極少參與"
            engagement_score = 20
        
        # 會話品質評估
        if total_sessions > 0:
            avg_messages_per_session = total_messages / total_sessions
            if avg_messages_per_session >= 8:
                session_quality = "深度討論"
            elif avg_messages_per_session >= 4:
                session_quality = "良好互動"
            else:
                session_quality = "簡短交流"
        else:
            session_quality = "無會話記錄"
            avg_messages_per_session = 0
        
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
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'avg_messages_per_session': round(avg_messages_per_session, 1),
            'session_quality': session_quality,
            'active_days': active_days,
            'engagement_level': engagement,
            'engagement_score': engagement_score,
            'has_learning_history': has_learning_history,
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
    """取得系統統計（記憶功能增強版）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
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
            'sessions': {  # 新增會話統計
                'total': 0,
                'active': 0,
                'completed': 0,
                'average_length': 0
            },
            'learning_histories': {  # 新增學習歷程統計
                'total': 0,
                'students_covered': 0,
                'latest_generated': None
            },
            'ai': {
                'current_model': current_model_name,
                'total_calls': sum(stats['calls'] for stats in model_usage_stats.values()),
                'total_errors': sum(stats['errors'] for stats in model_usage_stats.values()),
            }
        }
        
        # 會話統計
        try:
            stats['sessions']['total'] = ConversationSession.select().count()
            stats['sessions']['active'] = ConversationSession.select().where(
                ConversationSession.session_end.is_null()
            ).count()
            stats['sessions']['completed'] = stats['sessions']['total'] - stats['sessions']['active']
            
            # 平均會話長度
            completed_sessions = list(ConversationSession.select().where(
                ConversationSession.session_end.is_null(False)
            ))
            if completed_sessions:
                total_length = sum(s.message_count for s in completed_sessions if hasattr(s, 'message_count') and s.message_count)
                stats['sessions']['average_length'] = round(total_length / len(completed_sessions), 1)
        except Exception as e:
            logger.warning(f"會話統計計算錯誤: {e}")
        
        # 學習歷程統計
        try:
            stats['learning_histories']['total'] = LearningHistory.select().count()
            stats['learning_histories']['students_covered'] = LearningHistory.select(
                LearningHistory.student
            ).distinct().count()
            
            latest_history = LearningHistory.select().order_by(
                LearningHistory.generated_at.desc()
            ).first()
            if latest_history:
                stats['learning_histories']['latest_generated'] = latest_history.generated_at.isoformat()
        except Exception as e:
            logger.warning(f"學習歷程統計計算錯誤: {e}")
        
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
            'sessions': {'total': 0, 'active': 0, 'completed': 0, 'average_length': 0},
            'learning_histories': {'total': 0, 'students_covered': 0, 'latest_generated': None},
            'ai': {'current_model': current_model_name, 'total_calls': 0, 'total_errors': 0},
            'error': str(e)
        }

def get_student_conversation_summary(student_id, days=30):
    """取得學生對話摘要（記憶功能增強版）"""
    try:
        from models import Student, Message, ConversationSession
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '學生不存在'}
        
        # 取得指定天數內的訊息
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        messages = list(Message.select().where(
            (Message.student == student) &
            (Message.timestamp >= cutoff_date)
        ).order_by(Message.timestamp.desc()))
        
        # 取得會話資訊
        sessions_in_period = list(ConversationSession.select().where(
            (ConversationSession.student == student) &
            (ConversationSession.session_start >= cutoff_date)
        ))
        
        if not messages:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'period_days': days,
                'message_count': 0,
                'session_count': 0,
                'summary': f'No conversation records in the past {days} days.',
                'status': 'no_data'
            }
        
        # 分析訊息來源
        student_messages = [msg for msg in messages if msg.source_type in ['line', 'student']]
        ai_messages = [msg for msg in messages if msg.source_type == 'ai']
        
        # 分析主題
        topics = extract_conversation_topics([{'content': msg.content} for msg in student_messages])
        topic_summary = "、".join(topics[:3]) if topics else "general topics"
        
        # 會話分析
        active_sessions = len([s for s in sessions_in_period if s.session_end is None])
        completed_sessions = len(sessions_in_period) - active_sessions
        
        # 簡單活躍度評估
        if len(messages) >= 20:
            activity_level = "highly active"
        elif len(messages) >= 10:
            activity_level = "moderately active"
        elif len(messages) >= 5:
            activity_level = "lightly active"
        else:
            activity_level = "minimal activity"
        
        summary = f"In the past {days} days, {student.name} had {len(messages)} total messages across {len(sessions_in_period)} conversation sessions. Topics discussed: {topic_summary}. Activity level: {activity_level}."
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'period_days': days,
            'message_count': len(messages),
            'student_messages': len(student_messages),
            'ai_messages': len(ai_messages),
            'session_count': len(sessions_in_period),
            'active_sessions': active_sessions,
            'completed_sessions': completed_sessions,
            'topics_discussed': topics,
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

# =================== 系統健康檢查（記憶功能增強版） ===================

def perform_system_health_check():
    """執行系統健康檢查（記憶功能增強版）"""
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
            from models import Student, Message, ConversationSession, LearningHistory
            student_count = Student.select().count()
            message_count = Message.select().count()
            
            # 檢查新增表格
            try:
                session_count = ConversationSession.select().count()
                history_count = LearningHistory.select().count()
                memory_features = "✅ 正常"
            except Exception as e:
                session_count = 0
                history_count = 0
                memory_features = f"⚠️ 記憶功能表格異常: {str(e)[:50]}"
                health_report['warnings'].append('記憶功能資料表可能有問題')
            
            health_report['checks']['database'] = {
                'status': 'healthy',
                'details': f'連接正常，{student_count} 位學生，{message_count} 則訊息，{session_count} 個會話，{history_count} 筆學習歷程'
            }
            
            health_report['checks']['memory_features'] = {
                'status': 'healthy' if '正常' in memory_features else 'warning',
                'details': memory_features
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
        
        # 檢查會話管理
        try:
            from models import ConversationSession, manage_conversation_sessions
            cleanup_result = manage_conversation_sessions()
            health_report['checks']['session_management'] = {
                'status': 'healthy',
                'details': f'會話管理正常，清理了 {cleanup_result.get("cleaned_sessions", 0)} 個舊會話'
            }
        except Exception as e:
            health_report['checks']['session_management'] = {
                'status': 'warning',
                'details': f'會話管理檢查異常: {str(e)}'
            }
            health_report['warnings'].append('會話管理功能可能有問題')
        
        # 檢查模型使用統計
        quota_status = get_quota_status()
        error_rate = 0
        if quota_status['total_calls'] > 0:
            error_rate = (quota_status['total_errors'] / quota_status['total_calls']) * 100
        
        health_report['checks']['ai_quota'] = {
            'status': 'healthy' if error_rate < 50 else 'warning',
            'details': f'總呼叫: {quota_status["total_calls"]}, 錯誤: {quota_status["total_errors"]}, 錯誤率: {error_rate:.1f}%'
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
        
        # 檢查學習歷程功能
        try:
            from models import LearningHistory
            history_count = LearningHistory.select().count()
            students_with_history = LearningHistory.select(LearningHistory.student).distinct().count()
            
            health_report['checks']['learning_history'] = {
                'status': 'healthy',
                'details': f'學習歷程功能正常，{history_count} 筆記錄覆蓋 {students_with_history} 位學生'
            }
        except Exception as e:
            health_report['checks']['learning_history'] = {
                'status': 'warning',
                'details': f'學習歷程功能檢查異常: {str(e)}'
            }
            health_report['warnings'].append('學習歷程功能可能有問題')
        
        # 檢查模型切換情況
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
    """取得系統狀態摘要（記憶功能增強版）"""
    try:
        health_check = perform_system_health_check()
        system_stats = get_system_stats()
        
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'overall_status': health_check['overall_status'],
            'database_status': health_check['checks'].get('database', {}).get('status', 'unknown'),
            'ai_status': health_check['checks'].get('ai_service', {}).get('status', 'unknown'),
            'memory_features_status': health_check['checks'].get('memory_features', {}).get('status', 'unknown'),
            'session_management_status': health_check['checks'].get('session_management', {}).get('status', 'unknown'),
            'learning_history_status': health_check['checks'].get('learning_history', {}).get('status', 'unknown'),
            'current_model': current_model_name,
            'total_students': system_stats['students']['total'],
            'total_messages': system_stats['messages']['total'],
            'total_sessions': system_stats['sessions']['total'],
            'active_sessions': system_stats['sessions']['active'],
            'total_learning_histories': system_stats['learning_histories']['total'],
            'students_with_history': system_stats['learning_histories']['students_covered'],
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

# =================== 學生統計更新功能（記憶功能增強版） ===================

def update_student_stats(student_id):
    """更新學生統計（記憶功能增強版）"""
    try:
        from models import Student, Message, ConversationSession
        
        student = Student.get_by_id(student_id)
        if not student:
            return False
        
        # 更新最後活動時間
        student.last_active = datetime.datetime.now()
        
        # 更新訊息計數（如果有該欄位）
        if hasattr(student, 'message_count'):
            message_count = Message.select().where(Message.student == student).count()
            student.message_count = message_count
        
        # 更新會話計數（如果有該欄位）
        if hasattr(student, 'session_count'):
            session_count = ConversationSession.select().where(
                ConversationSession.student == student
            ).count()
            student.session_count = session_count
        
        student.save()
        
        logger.info(f"✅ 學生統計已更新 - {student.name}")
        return True
        
    except Exception as e:
        logger.error(f"更新學生統計錯誤: {e}")
        return False

# =================== 相容性函數（向後兼容增強版） ===================

# 保持與原版本的相容性，同時支援新功能
def generate_ai_response_with_smart_fallback(student_id, query, conversation_context="", student_context="", group_id=None):
    """相容性函數：舊版AI回應生成（增強記憶功能）"""
    try:
        from models import Student
        student = Student.get_by_id(student_id) if student_id else None
        
        if student:
            # 使用新的記憶功能版本
            return generate_ai_response_with_context(query, student)
        else:
            student_name = "Unknown"
            return generate_simple_ai_response(student_name, student_id, query)
    except Exception as e:
        logger.error(f"相容性AI回應錯誤: {e}")
        return get_fallback_response(query)

def analyze_student_patterns(student_id):
    """相容性函數：學生模式分析（增強版）"""
    # 結合基本統計和會話分析
    basic_stats = analyze_student_basic_stats(student_id)
    session_analysis = analyze_conversation_sessions(student_id)
    
    if 'error' in basic_stats:
        return basic_stats
    
    # 合併分析結果
    enhanced_analysis = basic_stats.copy()
    if 'error' not in session_analysis:
        enhanced_analysis.update({
            'session_pattern': session_analysis.get('session_pattern', 'unknown'),
            'session_analysis': session_analysis
        })
    
    return enhanced_analysis

# 舊版函數別名（保持相容性）
analyze_student_pattern = analyze_student_patterns
get_ai_response = generate_ai_response_with_smart_fallback

# =================== utils.py 增強版 - 第2段結束 ===================

# =================== utils.py 增強版 - 第3段開始 ===================
# 匯出功能和模組配置（記憶功能增強版）

# =================== 優化的匯出功能（記憶功能增強版） ===================

def export_student_conversations_tsv(student_id):
    """匯出學生對話記錄為TSV格式（記憶功能增強版）"""
    try:
        from models import Student, Message, ConversationSession
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'status': 'error', 'error': '學生不存在'}
        
        # 取得所有對話記錄
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()))
        
        if not messages:
            return {'status': 'no_data', 'error': '該學生沒有對話記錄'}
        
        # 生成增強版TSV內容（包含會話資訊）
        tsv_lines = ['時間\t學生姓名\t學號\t訊息內容\t來源類型\t註冊狀態\t會話ID\tAI回應\t主題標籤']
        
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
            
            # 會話資訊（新增）
            session_id = ""
            if hasattr(msg, 'session') and msg.session:
                session_id = str(msg.session.id)
            
            # AI回應（新增）
            ai_response = ""
            if hasattr(msg, 'ai_response') and msg.ai_response:
                ai_response = msg.ai_response.replace('\n', ' ').replace('\t', ' ')[:200]
            
            # 主題標籤（新增）
            topic_tags = ""
            if hasattr(msg, 'topic_tags') and msg.topic_tags:
                topic_tags = msg.topic_tags.replace('\t', ' ')
            
            tsv_lines.append(f"{timestamp}\t{student_name}\t{student_id_number}\t{content}\t{source}\t{registration_status}\t{session_id}\t{ai_response}\t{topic_tags}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"student_{student.name}_enhanced_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
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
    """匯出所有對話記錄為TSV格式（記憶功能增強版）"""
    try:
        from models import Student, Message
        
        # 取得所有對話記錄
        messages = list(Message.select().join(Student).order_by(Message.timestamp.desc()))
        
        if not messages:
            return {'status': 'no_data', 'error': '沒有找到任何對話記錄'}
        
        # 生成增強版TSV內容
        tsv_lines = ['時間\t學生姓名\t學號\t訊息內容\t來源類型\t註冊狀態\t會話ID\tAI回應\t主題標籤']
        
        for msg in messages:
            student = msg.student
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else '未知時間'
            student_name = student.name or '未知學生'
            student_id_number = getattr(student, 'student_id', '未設定')
            content = msg.content.replace('\n', ' ').replace('\t', ' ')[:500]
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
            
            # 會話資訊
            session_id = ""
            if hasattr(msg, 'session') and msg.session:
                session_id = str(msg.session.id)
            
            # AI回應
            ai_response = ""
            if hasattr(msg, 'ai_response') and msg.ai_response:
                ai_response = msg.ai_response.replace('\n', ' ').replace('\t', ' ')[:200]
            
            # 主題標籤
            topic_tags = ""
            if hasattr(msg, 'topic_tags') and msg.topic_tags:
                topic_tags = msg.topic_tags.replace('\t', ' ')
            
            tsv_lines.append(f"{timestamp}\t{student_name}\t{student_id_number}\t{content}\t{source}\t{registration_status}\t{session_id}\t{ai_response}\t{topic_tags}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"all_conversations_enhanced_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
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
    """匯出學生摘要為TSV格式（記憶功能增強版）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        students = list(Student.select())
        
        if not students:
            return {'status': 'no_data', 'error': '沒有找到學生資料'}
        
        # 生成增強版TSV內容
        tsv_lines = ['學生姓名\t學號\t註冊時間\t最後活動\t對話總數\t會話總數\t活躍會話\t學習歷程\t註冊狀態\t參與度等級']
        
        for student in students:
            student_name = student.name or '未設定'
            student_id_number = getattr(student, 'student_id', '未設定')
            created_at = student.created_at.strftime('%Y-%m-%d') if student.created_at else '未知'
            last_active = student.last_active.strftime('%Y-%m-%d') if student.last_active else '從未活動'
            
            # 計算對話總數
            message_count = Message.select().where(Message.student == student).count()
            
            # 計算會話統計（新增）
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
            
            # 學習歷程狀態（新增）
            try:
                has_learning_history = LearningHistory.select().where(
                    LearningHistory.student == student
                ).exists()
                learning_history_status = "已生成" if has_learning_history else "未生成"
            except:
                learning_history_status = "未知"
            
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
            
            tsv_lines.append(f"{student_name}\t{student_id_number}\t{created_at}\t{last_active}\t{message_count}\t{session_count}\t{active_sessions}\t{learning_history_status}\t{reg_status}\t{engagement}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"students_summary_enhanced_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
        return {
            'status': 'success',
            'content': tsv_content,
            'filename': filename,
            'total_students': len(students)
        }
        
    except Exception as e:
        logger.error(f"匯出學生摘要錯誤: {e}")
        return {'status': 'error', 'error': str(e)}

def export_conversation_sessions_tsv():
    """匯出對話會話記錄為TSV格式（新增功能）"""
    try:
        from models import ConversationSession, Student
        
        sessions = list(ConversationSession.select().join(Student).order_by(
            ConversationSession.session_start.desc()
        ))
        
        if not sessions:
            return {'status': 'no_data', 'error': '沒有找到會話記錄'}
        
        # 生成TSV內容
        tsv_lines = ['會話ID\t學生姓名\t學生ID\t開始時間\t結束時間\t持續時間(分鐘)\t訊息數量\t狀態\t上下文摘要\t主題標籤']
        
        for session in sessions:
            session_id = str(session.id)
            student_name = session.student.name if session.student else '未知學生'
            student_id = getattr(session.student, 'student_id', '') if session.student else ''
            start_time = session.session_start.strftime('%Y-%m-%d %H:%M:%S') if session.session_start else ''
            end_time = session.session_end.strftime('%Y-%m-%d %H:%M:%S') if session.session_end else ''
            
            # 持續時間
            duration = ""
            if hasattr(session, 'duration_minutes') and session.duration_minutes:
                duration = str(session.duration_minutes)
            elif session.session_start and session.session_end:
                delta = session.session_end - session.session_start
                duration = str(round(delta.total_seconds() / 60, 1))
            
            message_count = str(getattr(session, 'message_count', 0))
            status = '已完成' if session.session_end else '活躍中'
            
            # 上下文摘要
            context_summary = ""
            if hasattr(session, 'context_summary') and session.context_summary:
                context_summary = session.context_summary.replace('\n', ' ').replace('\t', ' ')[:200]
            
            # 主題標籤
            topic_tags = ""
            if hasattr(session, 'topic_tags') and session.topic_tags:
                topic_tags = session.topic_tags.replace('\t', ' ')
            
            tsv_lines.append(f"{session_id}\t{student_name}\t{student_id}\t{start_time}\t{end_time}\t{duration}\t{message_count}\t{status}\t{context_summary}\t{topic_tags}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"conversation_sessions_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
        return {
            'status': 'success',
            'content': tsv_content,
            'filename': filename,
            'total_sessions': len(sessions)
        }
        
    except Exception as e:
        logger.error(f"匯出會話記錄錯誤: {e}")
        return {'status': 'error', 'error': str(e)}

def export_learning_histories_tsv():
    """匯出學習歷程記錄為TSV格式（新增功能）"""
    try:
        from models import LearningHistory, Student
        
        histories = list(LearningHistory.select().join(Student).order_by(
            LearningHistory.generated_at.desc()
        ))
        
        if not histories:
            return {'status': 'no_data', 'error': '沒有找到學習歷程記錄'}
        
        # 生成TSV內容
        tsv_lines = ['歷程ID\t學生姓名\t學生ID\t生成時間\t摘要\t學習主題\t版本\t分析資料摘要']
        
        for history in histories:
            history_id = str(history.id)
            student_name = history.student.name if history.student else '未知學生'
            student_id = getattr(history.student, 'student_id', '') if history.student else ''
            generated_at = history.generated_at.strftime('%Y-%m-%d %H:%M:%S') if history.generated_at else ''
            
            # 摘要
            summary = ""
            if history.summary:
                summary = history.summary.replace('\n', ' ').replace('\t', ' ')[:300]
            
            # 學習主題
            learning_topics = ""
            if history.learning_topics:
                learning_topics = history.learning_topics.replace('\t', ' ')
            
            # 版本
            version = str(getattr(history, 'version', 1))
            
            # 分析資料摘要
            analysis_summary = ""
            if history.analysis_data:
                try:
                    analysis_obj = json.loads(history.analysis_data)
                    if isinstance(analysis_obj, dict):
                        topics = analysis_obj.get('topics_analysis', {})
                        if topics:
                            analysis_summary = f"討論主題: {', '.join(list(topics.keys())[:3])}"
                        else:
                            analysis_summary = "包含完整分析資料"
                except:
                    analysis_summary = "分析資料格式異常"
            
            analysis_summary = analysis_summary.replace('\n', ' ').replace('\t', ' ')[:200]
            
            tsv_lines.append(f"{history_id}\t{student_name}\t{student_id}\t{generated_at}\t{summary}\t{learning_topics}\t{version}\t{analysis_summary}")
        
        tsv_content = '\n'.join(tsv_lines)
        filename = f"learning_histories_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.tsv"
        
        return {
            'status': 'success',
            'content': tsv_content,
            'filename': filename,
            'total_histories': len(histories)
        }
        
    except Exception as e:
        logger.error(f"匯出學習歷程錯誤: {e}")
        return {'status': 'error', 'error': str(e)}

def export_enhanced_analytics_json():
    """匯出增強版分析資料為JSON格式（新增功能）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        # 收集完整的系統分析資料
        analytics_data = {
            'export_info': {
                'generated_at': datetime.datetime.now().isoformat(),
                'system_version': 'EMI v4.1.0 (Memory & Learning History Enhanced)',
                'export_type': 'enhanced_analytics'
            },
            'system_overview': get_system_stats(),
            'memory_feature_analytics': {
                'total_sessions': 0,
                'active_sessions': 0,
                'average_session_length': 0,
                'session_patterns': {},
                'students_with_histories': 0,
                'topic_distribution': {}
            },
            'student_analytics': [],
            'engagement_analysis': {},
            'learning_progression_trends': {}
        }
        
        # 會話分析
        try:
            sessions = list(ConversationSession.select())
            analytics_data['memory_feature_analytics']['total_sessions'] = len(sessions)
            analytics_data['memory_feature_analytics']['active_sessions'] = len([s for s in sessions if s.session_end is None])
            
            if sessions:
                completed_sessions = [s for s in sessions if s.session_end and hasattr(s, 'message_count')]
                if completed_sessions:
                    avg_length = sum(s.message_count for s in completed_sessions) / len(completed_sessions)
                    analytics_data['memory_feature_analytics']['average_session_length'] = round(avg_length, 1)
        except Exception as e:
            logger.warning(f"會話分析收集錯誤: {e}")
        
        # 學習歷程分析
        try:
            histories_count = LearningHistory.select().count()
            students_with_histories = LearningHistory.select(LearningHistory.student).distinct().count()
            analytics_data['memory_feature_analytics']['students_with_histories'] = students_with_histories
        except Exception as e:
            logger.warning(f"學習歷程分析收集錯誤: {e}")
        
        # 學生詳細分析
        students = list(Student.select())
        for student in students[:50]:  # 限制數量避免檔案過大
            try:
                student_analysis = analyze_student_basic_stats(student.id)
                if 'error' not in student_analysis:
                    analytics_data['student_analytics'].append(student_analysis)
            except Exception as e:
                logger.warning(f"學生 {student.id} 分析收集錯誤: {e}")
        
        # 參與度分析
        try:
            engagement_summary = get_class_engagement_summary()
            if 'error' not in engagement_summary:
                analytics_data['engagement_analysis'] = engagement_summary
        except Exception as e:
            logger.warning(f"參與度分析收集錯誤: {e}")
        
        # 生成JSON
        json_content = json.dumps(analytics_data, ensure_ascii=False, indent=2)
        filename = f"emi_enhanced_analytics_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        return {
            'status': 'success',
            'content': json_content,
            'filename': filename,
            'data_points': len(analytics_data['student_analytics'])
        }
        
    except Exception as e:
        logger.error(f"匯出增強版分析錯誤: {e}")
        return {'status': 'error', 'error': str(e)}

# =================== 資料驗證和清理功能（記憶功能增強版） ===================

def validate_memory_features():
    """驗證記憶功能資料完整性（新增功能）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
        validation_report = {
            'validation_date': datetime.datetime.now().isoformat(),
            'memory_features_status': 'healthy',
            'checks': {
                'orphaned_messages': 0,
                'sessions_without_messages': 0,
                'students_without_sessions': 0,
                'inconsistent_session_counts': 0
            },
            'recommendations': [],
            'repair_suggestions': []
        }
        
        # 檢查孤立訊息（有session欄位但關聯的session不存在）
        try:
            messages_with_sessions = Message.select().where(Message.session.is_null(False))
            for msg in messages_with_sessions:
                try:
                    if msg.session:
                        continue  # session存在
                except ConversationSession.DoesNotExist:
                    validation_report['checks']['orphaned_messages'] += 1
        except Exception as e:
            logger.warning(f"孤立訊息檢查錯誤: {e}")
        
        # 檢查沒有訊息的會話
        try:
            sessions = ConversationSession.select()
            for session in sessions:
                message_count = Message.select().where(Message.session == session).count()
                if message_count == 0:
                    validation_report['checks']['sessions_without_messages'] += 1
        except Exception as e:
            logger.warning(f"空會話檢查錯誤: {e}")
        
        # 檢查沒有會話的學生
        try:
            students = Student.select()
            for student in students:
                session_count = ConversationSession.select().where(
                    ConversationSession.student == student
                ).count()
                message_count = Message.select().where(Message.student == student).count()
                if message_count > 0 and session_count == 0:
                    validation_report['checks']['students_without_sessions'] += 1
        except Exception as e:
            logger.warning(f"學生會話檢查錯誤: {e}")
        
        # 生成建議
        if validation_report['checks']['orphaned_messages'] > 0:
            validation_report['recommendations'].append(f"發現 {validation_report['checks']['orphaned_messages']} 則孤立訊息")
            validation_report['repair_suggestions'].append("執行 repair_orphaned_messages() 修復孤立訊息")
        
        if validation_report['checks']['sessions_without_messages'] > 0:
            validation_report['recommendations'].append(f"發現 {validation_report['checks']['sessions_without_messages']} 個空會話")
            validation_report['repair_suggestions'].append("考慮清理空會話記錄")
        
        if validation_report['checks']['students_without_sessions'] > 0:
            validation_report['recommendations'].append(f"發現 {validation_report['checks']['students_without_sessions']} 位學生有訊息但無會話")
            validation_report['repair_suggestions'].append("執行 create_missing_sessions() 為學生創建會話")
        
        # 決定整體狀態
        total_issues = sum(validation_report['checks'].values())
        if total_issues == 0:
            validation_report['memory_features_status'] = 'healthy'
            validation_report['recommendations'].append("記憶功能資料完整性良好")
        elif total_issues < 10:
            validation_report['memory_features_status'] = 'minor_issues'
        else:
            validation_report['memory_features_status'] = 'needs_attention'
        
        return validation_report
        
    except Exception as e:
        logger.error(f"記憶功能驗證錯誤: {e}")
        return {
            'validation_date': datetime.datetime.now().isoformat(),
            'memory_features_status': 'error',
            'error': str(e)
        }

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

def validate_student_data():
    """驗證學生資料完整性（增強版）"""
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

def get_class_engagement_summary():
    """取得全班參與度摘要（記憶功能增強版）"""
    try:
        from models import Student, Message, ConversationSession, LearningHistory
        
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
        total_sessions = 0
        registered_students = 0
        active_this_week = 0
        students_with_history = 0
        
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        
        for student in students:
            # 計算每個學生的訊息數
            message_count = Message.select().where(Message.student == student).count()
            total_messages += message_count
            
            # 計算會話數（新增）
            try:
                session_count = ConversationSession.select().where(
                    ConversationSession.student == student
                ).count()
                total_sessions += session_count
            except:
                session_count = 0
            
            # 檢查學習歷程（新增）
            try:
                has_history = LearningHistory.select().where(
                    LearningHistory.student == student
                ).exists()
                if has_history:
                    students_with_history += 1
            except:
                pass
            
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
            'total_sessions': total_sessions,
            'students_with_history': students_with_history,
            'average_messages_per_student': round(total_messages / len(students), 1),
            'average_sessions_per_student': round(total_sessions / len(students), 1),
            'engagement_distribution': engagement_levels,
            'engagement_percentage': {
                'high': round((engagement_levels['high'] / len(students)) * 100, 1),
                'medium': round((engagement_levels['medium'] / len(students)) * 100, 1),
                'low': round((engagement_levels['low'] / len(students)) * 100, 1),
                'minimal': round((engagement_levels['minimal'] / len(students)) * 100, 1)
            },
            'memory_features_adoption': {
                'students_with_sessions': len([s for s in students if ConversationSession.select().where(ConversationSession.student == s).exists()]),
                'students_with_history': students_with_history,
                'history_coverage_percentage': round((students_with_history / len(students)) * 100, 1)
            }
        }
        
    except Exception as e:
        logger.error(f"全班參與度摘要錯誤: {e}")
        return {'error': str(e)}

# =================== 學習活躍度分析（記憶功能增強版） ===================

def analyze_student_activity_pattern(student_id, days=30):
    """分析學生活動模式（記憶功能增強版）"""
    try:
        from models import Student, Message, ConversationSession
        
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '學生不存在'}
        
        # 取得指定天數內的活動
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        messages = list(Message.select().where(
            (Message.student == student) &
            (Message.timestamp >= cutoff_date)
        ).order_by(Message.timestamp.asc()))
        
        # 取得會話資訊（新增）
        sessions = list(ConversationSession.select().where(
            (ConversationSession.student == student) &
            (ConversationSession.session_start >= cutoff_date)
        ))
        
        if not messages:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'period_days': days,
                'activity_pattern': 'no_activity',
                'peak_hours': [],
                'active_days': 0,
                'messages_per_day': 0,
                'sessions_count': 0,
                'avg_session_length': 0
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
        
        # 會話分析（新增）
        sessions_count = len(sessions)
        avg_session_length = 0
        if sessions:
            completed_sessions = [s for s in sessions if s.session_end and hasattr(s, 'message_count')]
            if completed_sessions:
                avg_session_length = sum(s.message_count for s in completed_sessions) / len(completed_sessions)
        
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
            'total_messages': len(messages),
            'sessions_count': sessions_count,
            'avg_session_length': round(avg_session_length, 1),
            'memory_features_usage': {
                'uses_sessions': sessions_count > 0,
                'session_engagement': 'high' if avg_session_length >= 8 else 'medium' if avg_session_length >= 4 else 'low'
            }
        }
        
    except Exception as e:
        logger.error(f"學生活動分析錯誤: {e}")
        return {'error': str(e)}

# =================== 匯出函數別名（向後相容性增強版） ===================

# 舊版函數別名，但現在支援記憶功能
export_student_questions_tsv = export_student_conversations_tsv
export_all_questions_tsv = export_all_conversations_tsv
export_class_analytics_tsv = export_students_summary_tsv
export_student_analytics_tsv = export_student_conversations_tsv

# =================== 模組匯出列表（記憶功能增強版） ===================

__all__ = [
    # 核心AI功能（增強版）
    'generate_ai_response',
    'generate_ai_response_with_context',
    'generate_simple_ai_response',
    'generate_learning_suggestion', 
    'get_fallback_response',
    'get_fallback_suggestion',
    
    # 記憶功能輔助函數（新增）
    'get_conversation_context',
    'extract_conversation_topics',
    'build_context_summary',
    
    # 相容性AI函數
    'generate_ai_response_with_smart_fallback',
    'get_ai_response',
    
    # 模型管理
    'switch_to_available_model',
    'test_ai_connection',
    'get_quota_status', 
    'record_model_usage',
    
    # 分析功能（增強版）
    'analyze_student_basic_stats',
    'analyze_student_patterns',
    'analyze_student_pattern',
    'analyze_conversation_sessions',
    'get_learning_progression_analysis',
    'get_learning_history_summary',
    'analyze_student_activity_pattern',
    'update_student_stats',
    'get_student_conversation_summary',
    
    # 系統功能（增強版）
    'get_system_stats',
    'get_system_status',
    'perform_system_health_check',
    'get_class_engagement_summary',
    
    # 匯出功能（增強版）
    'export_student_conversations_tsv',
    'export_all_conversations_tsv', 
    'export_students_summary_tsv',
    'export_conversation_sessions_tsv',
    'export_learning_histories_tsv',
    'export_enhanced_analytics_json',
    'export_student_questions_tsv',
    'export_all_questions_tsv',
    'export_class_analytics_tsv',
    'export_student_analytics_tsv',
    
    # 驗證和清理功能（新增）
    'validate_memory_features',
    'validate_student_data',
    'cleanup_old_messages',
    
    # 常數
    'AVAILABLE_MODELS',
    'current_model_name'
]

# =================== 初始化檢查（記憶功能增強版） ===================

def initialize_utils():
    """初始化工具模組（記憶功能增強版）"""
    try:
        logger.info("🔧 初始化 utils.py 模組（記憶功能增強版）...")
        
        # 檢查AI服務狀態
        if GEMINI_API_KEY:
            ai_status, ai_message = test_ai_connection()
            if ai_status:
                logger.info(f"✅ AI服務正常 - {ai_message}")
            else:
                logger.warning(f"⚠️ AI服務異常 - {ai_message}")
        else:
            logger.warning("⚠️ GEMINI_API_KEY 未設定")
        
        # 檢查記憶功能
        try:
            memory_validation = validate_memory_features()
            if memory_validation['memory_features_status'] == 'healthy':
                logger.info("✅ 記憶功能資料完整性良好")
            else:
                logger.warning(f"⚠️ 記憶功能狀態: {memory_validation['memory_features_status']}")
                if memory_validation.get('recommendations'):
                    for rec in memory_validation['recommendations'][:3]:  # 顯示前3個建議
                        logger.info(f"   📋 建議: {rec}")
        except Exception as e:
            logger.warning(f"⚠️ 記憶功能檢查錯誤: {e}")
        
        # 檢查模型統計
        quota_status = get_quota_status()
        logger.info(f"📊 AI使用統計 - 總呼叫: {quota_status['total_calls']}, 錯誤: {quota_status['total_errors']}")
        
        # 檢查系統整體狀態
        try:
            system_stats = get_system_stats()
            logger.info(f"📈 系統統計 - 學生: {system_stats['students']['total']}, 訊息: {system_stats['messages']['total']}, 會話: {system_stats['sessions']['total']}, 學習歷程: {system_stats['learning_histories']['total']}")
        except Exception as e:
            logger.warning(f"⚠️ 系統統計檢查錯誤: {e}")
        
        # 檢查學生資料完整性
        try:
            validation_result = validate_student_data()
            if 'error' not in validation_result:
                valid_rate = (validation_result['valid_students'] / validation_result['total_students']) * 100 if validation_result['total_students'] > 0 else 0
                logger.info(f"📋 學生資料驗證 - {validation_result['valid_students']}/{validation_result['total_students']} 完整 ({valid_rate:.1f}%)")
        except Exception as e:
            logger.warning(f"⚠️ 學生資料驗證錯誤: {e}")
        
        logger.info("✅ utils.py 模組（記憶功能增強版）初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ utils.py 模組初始化失敗: {e}")
        return False

# 自動初始化（僅在直接導入時執行）
if __name__ != '__main__':
    initialize_utils()

# =================== 版本說明（記憶功能增強版） ===================

"""
EMI 智能教學助理系統 - utils.py 記憶功能增強版
=====================================

🎯 增強重點:
- 🧠 完整支援記憶功能：對話上下文管理、會話追蹤
- 📚 學習歷程功能：進展分析、歷程摘要、主題演進追蹤
- 🔧 與 app.py v4.1 記憶功能版完美兼容
- 📊 增強版統計和匯出：包含會話和學習歷程資料
- 🔄 完整向後相容性

✨ 新增功能:
🧠 記憶功能支援:
- get_conversation_context(): 取得對話上下文
- extract_conversation_topics(): 主題提取
- build_context_summary(): 上下文摘要生成
- generate_ai_response_with_context(): 帶記憶的AI回應

📚 學習歷程支援:
- analyze_conversation_sessions(): 會話分析
- get_learning_progression_analysis(): 學習進展分析
- get_learning_history_summary(): 學習歷程摘要

📊 增強版統計和匯出:
- export_conversation_sessions_tsv(): 會話記錄匯出
- export_learning_histories_tsv(): 學習歷程匯出
- export_enhanced_analytics_json(): 增強版分析資料
- validate_memory_features(): 記憶功能驗證

🔧 系統監控增強:
- 記憶功能健康檢查
- 會話管理狀態監控
- 學習歷程覆蓋率統計
- 資料完整性驗證

🤖 AI配置增強:
- 主要模型：gemini-2.5-flash
- 支援上下文記憶的回應生成
- 智慧主題提取和分類
- 學習進展模式識別

📊 統計功能增強:
- 會話品質評估（深度討論/良好互動/簡短交流）
- 學習歷程覆蓋率統計
- 記憶功能採用率分析
- 主題演進追蹤

🔄 相容性保證:
- 保留所有舊函數名稱和介面
- 與現有 routes.py 完全相容
- 自動處理新舊資料格式
- 智慧降級和錯誤恢復

🎯 核心改進:
- AI回應現在支援對話記憶上下文
- 學習建議包含會話統計資訊
- 匯出功能包含會話ID、AI回應、主題標籤
- 系統健康檢查包含記憶功能狀態
- 完整的資料驗證和修復建議

🚀 性能優化:
- 智慧上下文長度控制（最多10則訊息）
- 高效的主題提取算法
- 批量資料處理優化
- 記憶體使用優化

🔍 資料匯出增強:
- TSV格式包含會話ID和主題標籤
- 學習歷程完整匯出功能
- JSON格式的增強版分析資料
- 支援會話記錄獨立匯出

🛡️ 資料驗證系統:
- 記憶功能資料完整性檢查
- 孤立訊息自動檢測
- 會話一致性驗證
- 智慧修復建議

版本日期: 2025年6月29日
增強版本: v4.1.0 (Memory & Learning History Enhanced)
設計理念: 智能記憶、學習追蹤、完整兼容、高效穩定
相容性: 與 app.py v4.1 記憶功能版完美配合

🎉 主要創新:
1. 對話記憶：AI能記住前8-10輪對話，支援深入討論
2. 學習歷程：自動追蹤學習進展，生成個人化分析報告
3. 會話管理：智慧會話分割，提供更好的學習體驗
4. 主題演進：追蹤學習主題的發展和擴展
5. 智慧分析：從簡單統計進化為深度學習模式分析

🔮 未來擴展:
- 支援更複雜的學習路徑分析
- 個人化學習建議優化
- 跨會話知識圖譜構建
- 學習效果預測模型

📋 檔案完整性:
- 總計約 750+ 行程式碼
- 包含 40+ 核心函數
- 完整的錯誤處理和日誌記錄
- 詳細的文檔和註解

🚀 部署建議:
1. 確保所有相依套件已安裝
2. 執行 initialize_utils() 檢查系統狀態
3. 運行 validate_memory_features() 驗證資料完整性
4. 定期執行健康檢查監控系統運作
"""

# =================== utils.py 增強版 - 第3段結束 ===================
# =================== 程式檔案結束 ===================
