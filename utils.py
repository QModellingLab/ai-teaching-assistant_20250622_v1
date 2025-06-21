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
                test_response = test_model.generate_content("Hello")
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

# =========================================
# 新增：對話會話管理
# =========================================

class ConversationManager:
    """對話會話管理器"""
    
    def __init__(self):
        self.max_context_turns = 8  # 保留最近8輪對話
        self.session_timeout = 2    # 2小時無活動則會話暫停
    
    def get_session_id(self, student_id, group_id=None):
        """生成會話ID"""
        today = datetime.date.today().strftime('%Y%m%d')
        if group_id:
            return f"group_{group_id}_{today}"
        else:
            return f"private_{student_id}_{today}"
    
    def get_conversation_context(self, student_id, group_id=None):
        """取得對話上下文"""
        try:
            session_id = self.get_session_id(student_id, group_id)
            
            # 取得最近的對話記錄
            cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=self.session_timeout)
            
            recent_messages = list(Message.select().where(
                (Message.student_id == student_id) &
                (Message.timestamp > cutoff_time)
            ).order_by(Message.timestamp.desc()).limit(self.max_context_turns))
            
            if not recent_messages:
                return ""
            
            # 按時間順序排列
            recent_messages.reverse()
            
            # 格式化對話上下文
            context_parts = []
            for msg in recent_messages:
                # 包含學生訊息和AI回應
                if msg.message_type in ['question', 'statement']:
                    context_parts.append(f"Student: {msg.content}")
                    
                    # 查找對應的AI回應
                    ai_response = self.get_ai_response_for_message(msg.id)
                    if ai_response:
                        context_parts.append(f"AI: {ai_response}")
            
            # 限制上下文長度
            context = "\n".join(context_parts[-6:])  # 最近3輪對話
            return context
            
        except Exception as e:
            logger.error(f"❌ 取得對話上下文錯誤: {e}")
            return ""
    
    def get_ai_response_for_message(self, message_id):
        """取得訊息對應的AI回應"""
        try:
            # 可以從 AIResponse 表或其他地方取得
            # 這裡先簡化處理
            return None
        except Exception as e:
            logger.error(f"取得AI回應錯誤: {e}")
            return None
    
    def save_conversation_turn(self, student_id, user_message, ai_response, group_id=None):
        """儲存一輪對話"""
        try:
            session_id = self.get_session_id(student_id, group_id)
            
            # 儲存學生訊息（如果還沒儲存）
            # 這通常在 LINE webhook 處理時已經儲存
            
            # 儲存AI回應記錄（如果需要專門的表）
            # 可以新增 AIResponse 模型來記錄
            
            logger.info(f"✅ 儲存對話輪次: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ 儲存對話輪次錯誤: {e}")

# 初始化對話管理器
conversation_manager = ConversationManager()

# =========================================
# 新增：問題分類系統
# =========================================

QUESTION_CATEGORIES = {
    "content_domain": [
        "Technology", "Science", "Business", "Culture", 
        "Language", "General_Knowledge", "Academic_Skills"
    ],
    "cognitive_level": [
        "Remember",     # 記憶層次：What is...?
        "Understand",   # 理解層次：Can you explain...?
        "Apply",        # 應用層次：How to use...?
        "Analyze",      # 分析層次：What's the difference...?
        "Evaluate",     # 評估層次：Which is better...?
        "Create"        # 創造層次：How to design...?
    ],
    "question_type": [
        "Definition",      # 定義型問題
        "Example",         # 舉例型問題
        "Comparison",      # 比較型問題
        "Procedure",       # 程序型問題
        "Cause_Effect",    # 因果關係
        "Problem_Solving"  # 問題解決
    ],
    "language_complexity": [
        "Basic",           # 基礎詞彙
        "Intermediate",    # 中級詞彙
        "Advanced"         # 高級詞彙
    ]
}

def analyze_question_type(question_text, student_context=""):
    """智能問題分類分析"""
    try:
        if not model:
            logger.warning("⚠️ AI 模型未初始化，無法進行問題分析")
            return None
            
        analysis_prompt = f"""As an educational expert, analyze this student question for teaching insights:

Question: "{question_text}"
Student context: {student_context}

Classify the question using these categories:

1. Content Domain: Technology/Science/Business/Culture/Language/General_Knowledge/Academic_Skills
2. Cognitive Level: Remember/Understand/Apply/Analyze/Evaluate/Create (Bloom's Taxonomy)
3. Question Type: Definition/Example/Comparison/Procedure/Cause_Effect/Problem_Solving
4. Language Complexity: Basic/Intermediate/Advanced
5. Key Concepts: Extract 3-5 main concepts/keywords
6. Difficulty Prediction: Easy/Medium/Hard

Return ONLY a JSON object in this exact format:
{{
    "content_domain": "Technology",
    "cognitive_level": "Understand",
    "question_type": "Definition",
    "language_complexity": "Intermediate",
    "key_concepts": ["concept1", "concept2", "concept3"],
    "difficulty": "Medium",
    "reasoning": "Brief explanation"
}}"""
        
        generation_config = genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=300,
            temperature=0.3,
        )
        
        response = model.generate_content(
            analysis_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            try:
                # 嘗試解析 JSON
                json_text = response.text.strip()
                if json_text.startswith('```json'):
                    json_text = json_text.replace('```json', '').replace('```', '')
                elif json_text.startswith('```'):
                    json_text = json_text.replace('```', '')
                
                analysis_result = json.loads(json_text)
                logger.info(f"✅ 問題分類分析完成: {analysis_result.get('content_domain', 'Unknown')}")
                return analysis_result
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 解析錯誤: {e}")
                logger.debug(f"原始回應: {response.text}")
                return None
                
        else:
            logger.error("❌ 問題分析回應為空")
            return None
            
    except Exception as e:
        logger.error(f"❌ 問題分類分析錯誤: {e}")
        return None

# =========================================
# 更新：改進的 AI 回應函數（英文為主）
# =========================================

def get_ai_response(query, student_id=None, group_id=None):
    """取得 AI 回應 - 英文為主，支援對話上下文"""
    try:
        if not model:
            logger.error("❌ AI 模型未初始化")
            return "Sorry, AI service is currently unavailable. Please check system settings."
        
        if not query or len(query.strip()) == 0:
            return "Please provide your question, and I'll be happy to help you!"
        
        # 取得學生資訊和對話上下文
        student_context = ""
        conversation_context = ""
        
        if student_id:
            try:
                student = Student.get_by_id(student_id)
                student_context = f"Student: {student.name} (Participation: {student.participation_rate}%)"
                
                # 取得對話上下文
                conversation_context = conversation_manager.get_conversation_context(student_id, group_id)
                
            except Exception as e:
                logger.warning(f"無法取得學生資訊: {e}")
        
        # 問題分類分析
        question_analysis = analyze_question_type(query, student_context)
        
        # 為 EMI 教學優化的英文提示詞
        prompt = f"""You are a professional EMI (English as Medium of Instruction) teaching assistant for university students. Your goal is to help students learn and understand concepts in English while being supportive and educational.

{"Previous conversation context:" + chr(10) + conversation_context + chr(10) if conversation_context else ""}

Instructions:
- Respond primarily in clear, simple English suitable for university-level ESL learners
- Use vocabulary appropriate for intermediate English learners
- For technical terms, provide Chinese translation in parentheses when helpful
- Maintain a friendly, encouraging, and educational tone
- If this continues a previous conversation, build on what was discussed before
- Encourage further questions and deeper thinking

{student_context if student_context else ""}

Student question: {query}

Please provide a helpful response (100-150 words):"""
        
        logger.info(f"🤖 使用 {current_model_name} 生成英文回應...")
        
        # Gemini 2.0 optimized generation config
        generation_config = genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=350,
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
            logger.info(f"✅ AI 英文回應成功生成，長度: {len(ai_response)} 字")
            
            # 儲存對話輪次
            conversation_manager.save_conversation_turn(student_id, query, ai_response, group_id)
            
            # 儲存問題分析結果
            if question_analysis and student_id:
                save_question_analysis(student_id, query, question_analysis)
            
            return ai_response
        else:
            logger.error("❌ AI 回應為空")
            return "Sorry, I cannot generate an appropriate response right now. Please try again later or rephrase your question."
            
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"❌ AI 回應錯誤: {str(e)}")
        
        # 詳細的錯誤處理
        if "404" in error_msg or "not found" in error_msg:
            return "AI model is temporarily unavailable. Your project may not have access to Gemini 1.5 models. The system is trying to use Gemini 2.0."
        elif "quota" in error_msg or "limit" in error_msg or "exceeded" in error_msg:
            return "AI service usage limit reached. Please try again later."
        elif "permission" in error_msg or "denied" in error_msg:
            return "AI service permission insufficient. Please check API key settings."
        elif "unavailable" in error_msg or "not available" in error_msg:
            return "Your Google Cloud project may not have access to newer Gemini models. Please contact administrator."
        elif "safety" in error_msg:
            return "For safety reasons, AI cannot respond to this question. Please try rephrasing your question."
        else:
            return f"An error occurred while processing your question. Please try again later."

def save_question_analysis(student_id, question, analysis_result):
    """儲存問題分析結果"""
    try:
        if not analysis_result:
            return
            
        # 更新訊息記錄中的分析資料
        recent_message = Message.select().where(
            (Message.student_id == student_id) &
            (Message.content == question)
        ).order_by(Message.timestamp.desc()).first()
        
        if recent_message:
            # 如果 Message 模型有相關欄位，就更新
            # 這裡需要根據您的實際 Message 模型結構調整
            pass
            
        # 也可以儲存到 Analysis 表
        Analysis.create(
            student_id=student_id,
            analysis_type='question_classification',
            analysis_data=json.dumps(analysis_result),
            confidence_score=0.8,
            timestamp=datetime.datetime.now()
        )
        
        logger.info(f"✅ 問題分析結果已儲存")
        
    except Exception as e:
        logger.error(f"❌ 儲存問題分析錯誤: {e}")

# =========================================
# 保留原有函數（稍作調整）
# =========================================

def analyze_student_patterns(student_id):
    """分析學生學習模式 - 更新為英文分析"""
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
            return "Insufficient interaction records (less than 3 messages) for effective analysis."
        
        # 準備分析資料
        messages_text = [msg.content[:80] for msg in recent_messages]
        questions = [msg.content[:80] for msg in recent_messages if msg.message_type == 'question']
        
        # 英文版分析提示
        analysis_prompt = f"""As an educational expert, analyze this student's learning patterns for EMI course improvement:

Student Profile:
- Name: {student.name}
- Total Messages: {student.message_count}
- Questions Asked: {student.question_count}
- Participation Rate: {student.participation_rate}%

Recent Interactions:
{chr(10).join(f"• {msg}" for msg in messages_text)}

Main Questions:
{chr(10).join(f"• {q}" for q in questions) if questions else "• No questions recorded yet"}

Please analyze in English (120-150 words):
1. Learning style characteristics
2. Engagement level assessment
3. Specific learning recommendations

Analysis Report:"""
        
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
            return "AI analysis service is temporarily unavailable. Please try again later."
            
    except Exception as e:
        logger.error(f"❌ 學生模式分析錯誤: {e}")
        return f"Analysis error occurred: {str(e)[:50]}..."

# =========================================
# 新增：取得問題分類統計
# =========================================

def get_question_category_stats():
    """取得問題分類統計"""
    try:
        # 取得所有問題分析記錄
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ))
        
        if not analyses:
            return {
                'total_questions': 0,
                'category_distribution': {},
                'cognitive_levels': {},
                'question_types': {},
                'difficulty_levels': {}
            }
        
        # 統計各類別
        category_counts = {}
        cognitive_counts = {}
        type_counts = {}
        difficulty_counts = {}
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                
                # 內容領域統計
                domain = data.get('content_domain', 'Unknown')
                category_counts[domain] = category_counts.get(domain, 0) + 1
                
                # 認知層次統計
                cognitive = data.get('cognitive_level', 'Unknown')
                cognitive_counts[cognitive] = cognitive_counts.get(cognitive, 0) + 1
                
                # 問題類型統計
                q_type = data.get('question_type', 'Unknown')
                type_counts[q_type] = type_counts.get(q_type, 0) + 1
                
                # 難度統計
                difficulty = data.get('difficulty', 'Unknown')
                difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"分析資料解析錯誤: {e}")
                continue
        
        return {
            'total_questions': len(analyses),
            'category_distribution': category_counts,
            'cognitive_levels': cognitive_counts,
            'question_types': type_counts,
            'difficulty_levels': difficulty_counts
        }
        
    except Exception as e:
        logger.error(f"❌ 取得問題分類統計錯誤: {e}")
        return {}

def get_student_conversation_summary(student_id, days=7):
    """取得學生對話摘要"""
    try:
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        messages = list(Message.select().where(
            (Message.student_id == student_id) &
            (Message.timestamp > cutoff_date)
        ).order_by(Message.timestamp.asc()))
        
        if not messages:
            return "No recent conversations found."
        
        # 簡單的對話摘要
        total_messages = len(messages)
        questions = [m for m in messages if m.message_type == 'question']
        
        summary = f"""Conversation Summary (Last {days} days):
- Total interactions: {total_messages}
- Questions asked: {len(questions)}
- Most recent activity: {messages[-1].timestamp.strftime('%Y-%m-%d %H:%M')}
- Average daily interactions: {total_messages / days:.1f}"""
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ 取得對話摘要錯誤: {e}")
        return "Error generating conversation summary."

# =========================================
# 保留原有的其他函數
# =========================================

def test_ai_connection():
    """測試 AI 連接"""
    try:
        if not model:
            return False, "AI 模型未初始化"
        
        # 測試基本功能
        test_response = model.generate_content("Hello, please respond briefly.")
        
        if test_response and test_response.text:
            return True, f"Connection OK, using model: {current_model_name}"
        else:
            return False, "AI response is empty"
            
    except Exception as e:
        return False, f"Connection error: {str(e)[:60]}..."

def list_available_models():
    """列出可用的模型"""
    try:
        if not GEMINI_API_KEY:
            return ["No API key"]
        
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
            {'content': 'What is machine learning?', 'type': 'question'},
            {'content': 'Thanks for the explanation!', 'type': 'statement'},
            {'content': 'Can you give me some examples?', 'type': 'question'},
            {'content': 'This is very helpful', 'type': 'statement'},
            {'content': 'How is AI different from ML?', 'type': 'question'},
            {'content': 'I understand now!', 'type': 'statement'},
            {'content': 'Are there any recommended books?', 'type': 'question'},
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
            'model_info': f'使用 Gemini 2.0 系列模型（EMI 教學優化）',
            'conversation_manager': 'enabled',
            'question_analysis': 'enabled',
            'last_update': datetime.datetime.now().isoformat()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ 取得系統狀態錯誤: {e}")
        return {'error': str(e)}

def initialize_utils():
    """初始化工具模組"""
    logger.info("🔧 初始化增強版 utils 模組...")
    
    env_ok = validate_environment()
    if not env_ok:
        logger.warning("⚠️ 環境變數檢查未通過")
    
    ai_ok, ai_msg = test_ai_connection()
    logger.info(f"🤖 AI 狀態: {ai_msg}")
    
    models = list_available_models()
    if models:
        logger.info(f"📋 可用模型: {', '.join(models[:3])}...")
    
    logger.info(f"🚀 當前使用模型: {get_model_info()}")
    logger.info("🌐 功能: 英文回應 + 對話記憶 + 問題分類")
    logger.info("✅ 增強版 Utils 模組初始化完成")

# 自動執行初始化
initialize_utils()
