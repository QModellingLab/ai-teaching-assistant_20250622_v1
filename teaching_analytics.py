# teaching_analytics.py - 教學分析核心功能（2025年最新Gemini模型版）
# 包含：英文對話摘要、個人化建議、班級分析
# 更新日期：2025年6月25日

import os
import json
import datetime
import logging
import time
from collections import defaultdict, Counter
import google.generativeai as genai
from models import Student, Message, Analysis, db

logger = logging.getLogger(__name__)

# =================== 教學分析專用模型配置 (2025最新版本) ===================

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# 教學分析專用模型優先順序 - 基於教學效果、成本效益和穩定性
# 策略：Flash系列優先（性價比最佳），Pro系列用於複雜分析，Lite系列用於大量處理

ANALYTICS_MODELS = [
    "gemini-2.5-flash",        # 🥇 首選：最佳性價比 + 思考能力 + 速度
    "gemini-2.5-pro",          # 🏆 深度分析：最高智能 + 複雜推理 + 思考能力
    "gemini-2.5-flash-lite",   # 🚀 大量處理：最快速度 + 最低成本 + 高吞吐
    "gemini-2.0-flash",        # 🥈 穩定備用：成熟穩定 + 多模態 + 代理功能
    "gemini-2.0-pro",          # 💻 專業分析：編程專家 + 2M context + 實驗功能
    "gemini-2.0-flash-lite",   # 💰 經濟選擇：成本優化 + 比1.5更佳性能
    # === 備用舊版本 (向下兼容保證) ===
    "gemini-1.5-flash",        # 📦 備案1：成熟穩定 + 生產就緒
    "gemini-1.5-pro",          # 📦 備案2：功能完整 + 深度分析
    "gemini-1.5-flash-8b",     # 📦 備案3：效率優化 + 輕量版
    "gemini-1.0-pro",          # 📦 最後備案：基礎穩定
]

# 分析模型詳細規格 - 針對教學分析場景優化
ANALYTICS_MODEL_SPECS = {
    "gemini-2.5-flash": {
        "generation": "2.5",
        "type": "Flash",
        "analysis_quality": "excellent",
        "thinking_capability": True,
        "context_window": "1M",
        "speed": "fast",
        "cost_tier": "balanced",
        "free_limit": "high",
        "best_for_analysis": [
            "daily_teaching_summaries", 
            "student_progress_analysis", 
            "participation_insights",
            "real_time_feedback"
        ],
        "analysis_strength": "最佳教學分析平衡：高品質 + 快速 + 思考能力",
        "recommended_for": "日常教學分析的首選模型"
    },
    "gemini-2.5-pro": {
        "generation": "2.5",
        "type": "Pro", 
        "analysis_quality": "outstanding",
        "thinking_capability": True,
        "context_window": "1M",
        "speed": "moderate",
        "cost_tier": "premium",
        "free_limit": "moderate",
        "best_for_analysis": [
            "complex_learning_patterns",
            "deep_student_insights", 
            "advanced_recommendations",
            "research_grade_analysis"
        ],
        "analysis_strength": "最高級教學洞察：深度思考 + 複雜推理 + 頂級品質",
        "recommended_for": "複雜教學研究和深度學生分析"
    },
    "gemini-2.5-flash-lite": {
        "generation": "2.5",
        "type": "Flash-Lite",
        "analysis_quality": "very_good",
        "thinking_capability": True,
        "context_window": "1M", 
        "speed": "very_fast",
        "cost_tier": "economy",
        "free_limit": "very_high",
        "best_for_analysis": [
            "bulk_analysis",
            "classification_tasks",
            "quick_summaries", 
            "high_volume_processing"
        ],
        "analysis_strength": "高效大量分析：超快速度 + 低成本 + 思考能力",
        "recommended_for": "大量學生資料的批次分析"
    },
    "gemini-2.0-flash": {
        "generation": "2.0",
        "type": "Flash",
        "analysis_quality": "good",
        "thinking_capability": False,
        "context_window": "1M",
        "speed": "fast", 
        "cost_tier": "standard",
        "free_limit": "high",
        "best_for_analysis": [
            "stable_daily_analysis",
            "multimodal_content",
            "agent_based_insights",
            "reliable_summaries"
        ],
        "analysis_strength": "穩定可靠分析：成熟技術 + 多模態 + 代理功能",
        "recommended_for": "需要穩定性的生產環境分析"
    },
    "gemini-2.0-pro": {
        "generation": "2.0",
        "type": "Pro",
        "analysis_quality": "very_good",
        "thinking_capability": False,
        "context_window": "2M",
        "speed": "moderate",
        "cost_tier": "premium", 
        "free_limit": "limited",
        "best_for_analysis": [
            "large_document_analysis",
            "coding_behavior_analysis",
            "experimental_insights",
            "comprehensive_reports"
        ],
        "analysis_strength": "專業深度分析：超大文檔 + 編程專長 + 實驗功能",
        "recommended_for": "大型教學資料集和實驗性分析"
    },
    "gemini-2.0-flash-lite": {
        "generation": "2.0", 
        "type": "Flash-Lite",
        "analysis_quality": "good",
        "thinking_capability": False,
        "context_window": "1M",
        "speed": "very_fast",
        "cost_tier": "economy",
        "free_limit": "very_high",
        "best_for_analysis": [
            "cost_sensitive_analysis",
            "frequent_processing",
            "basic_insights",
            "volume_operations"
        ],
        "analysis_strength": "經濟高效分析：成本優化 + 比1.5更佳 + 高頻使用",
        "recommended_for": "預算受限的大量分析任務"
    },
    # 備用模型規格
    "gemini-1.5-flash": {
        "generation": "1.5",
        "type": "Flash",
        "analysis_quality": "stable",
        "thinking_capability": False,
        "context_window": "1M",
        "speed": "fast",
        "cost_tier": "standard",
        "free_limit": "moderate", 
        "best_for_analysis": ["stable_production", "reliable_summaries"],
        "analysis_strength": "成熟穩定分析：生產就緒 + 可靠性高",
        "recommended_for": "穩定生產環境的備用選擇"
    },
    "gemini-1.5-pro": {
        "generation": "1.5",
        "type": "Pro",
        "analysis_quality": "comprehensive",
        "thinking_capability": False,
        "context_window": "2M",
        "speed": "slow",
        "cost_tier": "premium",
        "free_limit": "limited",
        "best_for_analysis": ["comprehensive_analysis", "detailed_reports"],
        "analysis_strength": "功能完整分析：詳細報告 + 大文檔處理",
        "recommended_for": "需要詳細報告的綜合性分析"
    },
    "gemini-1.5-flash-8b": {
        "generation": "1.5",
        "type": "Flash-8B",
        "analysis_quality": "efficient",
        "thinking_capability": False,
        "context_window": "1M",
        "speed": "very_fast",
        "cost_tier": "economy",
        "free_limit": "high",
        "best_for_analysis": ["optimized_tasks", "resource_constrained"],
        "analysis_strength": "效率優化分析：資源節約 + 速度優化",
        "recommended_for": "資源受限環境的效率分析"
    },
    "gemini-1.0-pro": {
        "generation": "1.0",
        "type": "Pro", 
        "analysis_quality": "basic",
        "thinking_capability": False,
        "context_window": "32K",
        "speed": "moderate",
        "cost_tier": "standard",
        "free_limit": "basic",
        "best_for_analysis": ["fallback_analysis", "basic_summaries"],
        "analysis_strength": "基礎穩定分析：最後備用 + 基本功能",
        "recommended_for": "所有新模型都失效時的最後選擇"
    }
}

# 當前分析模型狀態
current_analytics_model = None
analytics_model_name = "gemini-2.5-flash"  # 預設使用最佳性價比模型
model_switch_count = 0
analysis_task_history = []
model_performance_stats = {model: {'calls': 0, 'successes': 0, 'errors': 0, 'avg_response_time': 0} for model in ANALYTICS_MODELS}

# =================== 智慧模型管理系統 ===================

def initialize_analytics_model():
    """初始化教學分析模型（智慧優先順序選擇）"""
    global current_analytics_model, analytics_model_name
    
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY 未設定")
        return None
    
    logger.info("🔬 開始初始化教學分析模型（2025最新版本）...")
    logger.info(f"📋 可用模型清單: {', '.join(ANALYTICS_MODELS[:3])} 等 {len(ANALYTICS_MODELS)} 個模型")
    
    # 按智慧優先順序嘗試初始化模型
    for idx, model_name in enumerate(ANALYTICS_MODELS):
        try:
            logger.info(f"🧪 嘗試初始化模型 [{idx+1}/{len(ANALYTICS_MODELS)}]: {model_name}")
            
            start_time = time.time()
            genai.configure(api_key=GEMINI_API_KEY)
            test_model = genai.GenerativeModel(model_name)
            
            # 使用教學分析特定的測試內容
            test_response = test_model.generate_content("Analyze: student learning engagement in EMI environment")
            response_time = time.time() - start_time
            
            if test_response and test_response.text:
                current_analytics_model = test_model
                analytics_model_name = model_name
                
                specs = ANALYTICS_MODEL_SPECS.get(model_name, {})
                logger.info(f"✅ 教學分析模型初始化成功: {model_name}")
                logger.info(f"📊 模型世代: {specs.get('generation', 'N/A')}")
                logger.info(f"🎯 分析品質: {specs.get('analysis_quality', 'unknown')}")
                logger.info(f"🧠 思考能力: {'是' if specs.get('thinking_capability') else '否'}")
                logger.info(f"📖 上下文窗口: {specs.get('context_window', 'unknown')}")
                logger.info(f"⚡ 回應時間: {response_time:.2f}秒")
                logger.info(f"💡 建議用途: {specs.get('recommended_for', '一般分析')}")
                
                # 記錄成功初始化的性能
                model_performance_stats[model_name]['calls'] += 1
                model_performance_stats[model_name]['successes'] += 1
                model_performance_stats[model_name]['avg_response_time'] = response_time
                
                return test_model
                
        except Exception as e:
            logger.warning(f"⚠️ 模型 {model_name} 初始化失敗: {e}")
            model_performance_stats[model_name]['calls'] += 1
            model_performance_stats[model_name]['errors'] += 1
            continue
    
    logger.error("❌ 所有教學分析模型都無法初始化")
    return None

def switch_analytics_model(reason="manual_switch"):
    """智慧切換到下一個最佳可用分析模型"""
    global current_analytics_model, analytics_model_name, model_switch_count
    
    if not GEMINI_API_KEY:
        logger.error("❌ API Key 未配置，無法切換模型")
        return False
    
    current_index = ANALYTICS_MODELS.index(analytics_model_name) if analytics_model_name in ANALYTICS_MODELS else 0
    old_model = analytics_model_name
    
    logger.info(f"🔄 開始智慧模型切換")
    logger.info(f"📊 當前模型: {analytics_model_name} (優先順序: {current_index + 1})")
    logger.info(f"🎯 切換原因: {reason}")
    
    # 按優先順序嘗試下一個最佳模型
    for i in range(1, len(ANALYTICS_MODELS)):
        next_index = (current_index + i) % len(ANALYTICS_MODELS)
        next_model_name = ANALYTICS_MODELS[next_index]
        
        # 檢查該模型的歷史表現
        stats = model_performance_stats[next_model_name]
        error_rate = (stats['errors'] / max(stats['calls'], 1)) * 100 if stats['calls'] > 0 else 0
        
        logger.info(f"🧪 考慮切換到: {next_model_name} (錯誤率: {error_rate:.1f}%)")
        
        # 如果錯誤率太高，跳過這個模型
        if error_rate > 75 and stats['calls'] > 2:
            logger.warning(f"⚠️ 跳過 {next_model_name}，錯誤率過高: {error_rate:.1f}%")
            continue
        
        try:
            start_time = time.time()
            genai.configure(api_key=GEMINI_API_KEY)
            new_model = genai.GenerativeModel(next_model_name)
            
            # 使用教學分析特定的測試
            test_response = new_model.generate_content("Analyze: teaching effectiveness and student engagement")
            response_time = time.time() - start_time
            
            if test_response and test_response.text:
                current_analytics_model = new_model
                analytics_model_name = next_model_name
                model_switch_count += 1
                
                specs = ANALYTICS_MODEL_SPECS.get(next_model_name, {})
                logger.info(f"✅ 教學分析模型切換成功!")
                logger.info(f"📈 切換路徑: {old_model} → {next_model_name}")
                logger.info(f"🔢 第 {model_switch_count} 次模型切換")
                logger.info(f"📊 新模型分析能力: {specs.get('analysis_strength', '未知')}")
                logger.info(f"⚡ 測試回應時間: {response_time:.2f}秒")
                
                # 更新性能統計
                model_performance_stats[next_model_name]['calls'] += 1
                model_performance_stats[next_model_name]['successes'] += 1
                model_performance_stats[next_model_name]['avg_response_time'] = response_time
                
                # 記錄切換歷史
                analysis_task_history.append({
                    'action': 'intelligent_model_switch',
                    'from_model': old_model,
                    'to_model': next_model_name,
                    'reason': reason,
                    'switch_count': model_switch_count,
                    'response_time': response_time,
                    'timestamp': datetime.datetime.now()
                })
                
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ 切換到模型 {next_model_name} 失敗: {e}")
            model_performance_stats[next_model_name]['calls'] += 1
            model_performance_stats[next_model_name]['errors'] += 1
            continue
    
    logger.error("❌ 無法切換到任何可用的分析模型")
    return False

def execute_with_intelligent_fallback(func, *args, **kwargs):
    """使用智慧備案機制執行分析函數"""
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            if not current_analytics_model:
                logger.info("🔧 分析模型未初始化，嘗試智慧初始化...")
                initialize_analytics_model()
            
            if current_analytics_model:
                start_time = time.time()
                logger.info(f"🎯 執行分析任務: {func.__name__}")
                logger.info(f"📊 使用模型: {analytics_model_name}")
                
                result = func(current_analytics_model, *args, **kwargs)
                response_time = time.time() - start_time
                
                # 更新成功統計
                model_performance_stats[analytics_model_name]['calls'] += 1
                model_performance_stats[analytics_model_name]['successes'] += 1
                
                # 記錄成功的分析任務
                analysis_task_history.append({
                    'action': 'analysis_success',
                    'model': analytics_model_name,
                    'function': func.__name__,
                    'attempt': attempt + 1,
                    'response_time': response_time,
                    'timestamp': datetime.datetime.now()
                })
                
                logger.info(f"✅ 分析任務完成: {func.__name__} ({response_time:.2f}秒)")
                return result
            else:
                raise Exception("No analytics model available")
                
        except Exception as e:
            logger.error(f"❌ 分析函數執行失敗 (嘗試 {attempt + 1}/{max_attempts}): {e}")
            
            # 更新錯誤統計
            if analytics_model_name in model_performance_stats:
                model_performance_stats[analytics_model_name]['calls'] += 1
                model_performance_stats[analytics_model_name]['errors'] += 1
            
            # 記錄失敗的分析任務
            analysis_task_history.append({
                'action': 'analysis_error',
                'model': analytics_model_name,
                'function': func.__name__,
                'attempt': attempt + 1,
                'error': str(e)[:100],
                'timestamp': datetime.datetime.now()
            })
            
            if attempt < max_attempts - 1:
                # 智慧切換模型
                switch_reason = f"analysis_error_{func.__name__}"
                if switch_analytics_model(reason=switch_reason):
                    logger.info(f"🔄 已智慧切換模型，重新嘗試分析任務...")
                    continue
                else:
                    logger.error("❌ 無法切換模型，停止重試")
                    break
    
    # 所有嘗試都失敗，返回增強錯誤狀態
    return {
        'status': 'error', 
        'error': '所有分析模型都無法使用',
        'attempted_models': model_switch_count + 1,
        'last_error': str(e) if 'e' in locals() else 'Unknown error',
        'fallback_mode': 'enhanced_error_handling',
        'retry_suggestions': [
            '檢查網路連接和API配額',
            '稍後重試分析任務',
            '聯繫系統管理員檢查模型可用性'
        ]
    }

# =================== 智慧模型選擇系統 ===================

def get_optimal_model_for_task(task_type: str, data_size: str = "medium", complexity: str = "medium") -> str:
    """根據任務特性智慧選擇最佳模型"""
    
    selection_matrix = {
        # 深度分析任務 - 使用最強模型
        'deep_learning_analysis': {
            'small': 'gemini-2.5-flash',
            'medium': 'gemini-2.5-pro', 
            'large': 'gemini-2.5-pro'
        },
        # 日常摘要 - 平衡性價比
        'daily_summary': {
            'small': 'gemini-2.5-flash',
            'medium': 'gemini-2.5-flash',
            'large': 'gemini-2.5-flash-lite'
        },
        # 大量處理 - 優先速度和成本
        'bulk_processing': {
            'small': 'gemini-2.5-flash',
            'medium': 'gemini-2.5-flash-lite',
            'large': 'gemini-2.5-flash-lite'
        },
        # 複雜推理 - 使用思考能力模型
        'complex_reasoning': {
            'small': 'gemini-2.5-flash',
            'medium': 'gemini-2.5-pro',
            'large': 'gemini-2.5-pro'
        },
        # 即時分析 - 優先速度
        'real_time_analysis': {
            'small': 'gemini-2.5-flash-lite',
            'medium': 'gemini-2.5-flash',
            'large': 'gemini-2.0-flash'
        },
        # 成本敏感 - 最經濟選擇
        'cost_optimized': {
            'small': 'gemini-2.5-flash-lite',
            'medium': 'gemini-2.5-flash-lite', 
            'large': 'gemini-2.0-flash-lite'
        }
    }
    
    recommended = selection_matrix.get(task_type, {}).get(data_size, 'gemini-2.5-flash')
    
    logger.info(f"🎯 智慧模型選擇: {task_type} + {data_size}資料 → {recommended}")
    return recommended

def optimize_model_selection(student_count: int, message_count: int, complexity: str = 'medium') -> str:
    """根據工作負載智慧優化模型選擇"""
    
    # 判斷資料規模
    if student_count > 100 or message_count > 2000:
        data_size = "large"
    elif student_count > 20 or message_count > 500:
        data_size = "medium"  
    else:
        data_size = "small"
    
    # 根據複雜度選擇任務類型
    if complexity == 'high':
        task_type = 'complex_reasoning'
    elif message_count > 1000:
        task_type = 'bulk_processing'
    elif complexity == 'low':
        task_type = 'cost_optimized'
    else:
        task_type = 'daily_summary'
    
    recommended = get_optimal_model_for_task(task_type, data_size, complexity)
    
    logger.info(f"📊 工作負載分析: {student_count}學生, {message_count}訊息, {complexity}複雜度")
    logger.info(f"💡 推薦模型: {recommended}")
    
    return recommended

# =================== 英文對話摘要功能 (最新版本) ===================

def _generate_conversation_summary_internal(model, student_id, days=30):
    """內部對話摘要生成函數 - 2025最新英文版本"""
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
    
    # 智慧選擇最佳模型
    recommended_model = optimize_model_selection(1, len(messages), 'medium')
    current_specs = ANALYTICS_MODEL_SPECS.get(analytics_model_name, {})
    
    # 2025最新版英文教學摘要生成 prompt
    summary_prompt = f"""As a senior EMI (English-Medium Instruction) educational analyst using the advanced {analytics_model_name} model (Generation {current_specs.get('generation', 'N/A')}), provide a comprehensive learning analysis in professional English:

**📋 Student Learning Profile:**
- Name: {student.name}
- Participation Rate: {student.participation_rate}%
- Total Learning Interactions: {len(messages)} messages
- Analysis Period: {days} days
- Analysis Model: {analytics_model_name}
- Model Capabilities: {current_specs.get('analysis_strength', 'Standard analysis')}
- Thinking Capability: {'Advanced reasoning enabled' if current_specs.get('thinking_capability') else 'Standard processing'}
- Context Window: {current_specs.get('context_window', 'Standard')}

**📚 Recent Learning Sample:**
{chr(10).join(conversation_text[-10:])}

Generate a comprehensive English teaching analysis with these sections:

**🎯 Learning Focus & Academic Engagement:**
[Analyze the main subjects, topics, and academic areas this student has engaged with. Identify learning preferences and subject matter interests.]

**📈 Learning Progress & Development Trajectory:**  
[Evaluate academic growth patterns, skill development, and learning improvements observed during this period.]

**🧠 Learning Style & Cognitive Patterns:**
[Assess how this student approaches learning, their interaction patterns, question-asking behavior, and cognitive engagement style.]

**💡 Personalized Teaching Strategies:**
[Provide specific, actionable recommendations for EMI instructors to optimize this student's learning experience and academic outcomes.]

**📊 Engagement Quality & Participation Analysis:**
[Analyze the depth, frequency, and quality of student participation in the learning environment.]

**🔍 Learning Opportunities & Growth Areas:**
[Identify areas for improvement, potential challenges, and opportunities for enhanced academic development.]

**🚀 Action Plan & Next Steps:**
[Suggest concrete steps for continued learning progress and specific goals for upcoming learning periods.]

Target: 450-550 words of professional English suitable for EMI educators and academic administrators."""

    try:
        start_time = time.time()
        response = model.generate_content(summary_prompt)
        response_time = time.time() - start_time
        
        if response and response.text:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'summary': response.text,
                'model_used': analytics_model_name,
                'model_generation': current_specs.get('generation', 'unknown'),
                'model_type': current_specs.get('type', 'unknown'),
                'analysis_quality': current_specs.get('analysis_quality', 'standard'),
                'thinking_enabled': current_specs.get('thinking_capability', False),
                'context_window': current_specs.get('context_window', 'unknown'),
                'response_time': round(response_time, 2),
                'message_count': len(messages),
                'analysis_period_days': days,
                'generated_at': datetime.datetime.now().isoformat(),
                'language': 'english',
                'recommended_model': recommended_model,
                'model_specs': current_specs,
                'status': 'success'
            }
    except Exception as e:
        logger.error(f"摘要生成錯誤: {e}")
    
    # 2025增強版英文備用摘要
    fallback_summary = f"""**Comprehensive Learning Analysis for {student.name}**
*Generated by Enhanced Fallback System (Model: {analytics_model_name})*

**🎯 Learning Focus & Academic Engagement:**
During the {days}-day analysis period, this student demonstrated active participation in English-medium instruction with {len(messages)} recorded learning interactions. The engagement pattern shows {'excellent academic involvement' if student.participation_rate > 75 else 'strong learning commitment' if student.participation_rate > 50 else 'developing academic participation'} across various educational activities and discussions.

**📈 Learning Progress & Development Trajectory:**
The student maintains a {student.participation_rate}% participation rate, indicating {'outstanding academic progress' if student.participation_rate > 75 else 'solid learning development' if student.participation_rate > 50 else 'emerging growth potential'} in the EMI learning environment. This level demonstrates {'exceptional learning momentum' if student.participation_rate > 75 else 'consistent academic advancement' if student.participation_rate > 50 else 'foundational skill building with positive trajectory'}.

**🧠 Learning Style & Cognitive Patterns:**
Analysis reveals {'highly active and engaged learning behaviors' if len(messages) > 20 else 'consistent participation patterns with regular engagement' if len(messages) > 10 else 'developing interaction skills with steady involvement'} in academic discussions and learning activities. The student shows {'advanced cognitive engagement' if len(messages) > 25 else 'moderate intellectual curiosity' if len(messages) > 10 else 'emerging academic interest'} in course content.

**💡 Personalized Teaching Strategies:**
Recommended approaches include {'implementing advanced challenge projects and peer mentoring opportunities' if student.participation_rate > 75 else 'introducing collaborative learning strategies and interactive discussion formats' if student.participation_rate > 50 else 'providing structured support activities and confidence-building exercises'} to optimize learning outcomes in the EMI context.

**📊 Engagement Quality & Participation Analysis:**
Overall academic engagement demonstrates {'exceptional quality and consistency' if student.participation_rate > 80 else 'high-quality participation with strong commitment' if student.participation_rate > 60 else 'developing engagement with positive growth indicators'} suitable for {'advanced academic challenges' if student.participation_rate > 75 else 'continued skill development' if student.participation_rate > 50 else 'supportive learning environments'}.

**🔍 Learning Opportunities & Growth Areas:**
Current analysis suggests {'minimal intervention needed with focus on advanced skill development' if student.participation_rate > 75 else 'moderate support beneficial for continued growth and confidence building' if student.participation_rate > 50 else 'targeted assistance recommended for foundational skill strengthening'} within the EMI framework.

**🚀 Action Plan & Next Steps:**
Priority focus areas include {'advanced project-based learning and leadership development opportunities' if student.participation_rate > 75 else 'increased interactive participation and collaborative skill building' if student.participation_rate > 50 else 'basic confidence enhancement and supported practice sessions'} with regular progress monitoring and adaptive instruction."""
    
    return {
        'student_id': student_id,
        'student_name': student.name,  
        'summary': fallback_summary,
        'model_used': 'enhanced_fallback_2025',
        'model_generation': 'fallback',
        'model_type': 'Fallback-Enhanced',
        'analysis_quality': 'fallback_comprehensive',
        'thinking_enabled': False,
        'context_window': 'limited',
        'response_time': 0.1,
        'message_count': len(messages),
        'analysis_period_days': days,
        'generated_at': datetime.datetime.now().isoformat(),
        'language': 'english',
        'recommended_model': recommended_model,
        'model_specs': {'type': 'Fallback', 'analysis_strength': 'Enhanced backup analysis'},
        'status': 'fallback_enhanced'
    }

def generate_conversation_summary(student_id, days=30):
    """生成學生對話摘要（支援2025最新模型智慧備案）"""
    return execute_with_intelligent_fallback(_generate_conversation_summary_internal, student_id, days)

# =================== 個人化建議生成 (2025最新版本) ===================

def _generate_personalized_recommendations_internal(model, student_id):
    """內部個人化建議生成函數 - 2025最新英文版本"""
    student = Student.get_by_id(student_id)
    
    # 收集學生資料
    messages = list(Message.select().where(Message.student_id == student_id).limit(20))
    analyses = list(Analysis.select().where(Analysis.student_id == student_id).limit(10))
    
    if len(messages) < 3:
        return {'status': 'insufficient_data', 'message_count': len(messages)}
    
    # 智慧模型選擇
    recommended_model = optimize_model_selection(1, len(messages), 'medium')
    current_specs = ANALYTICS_MODEL_SPECS.get(analytics_model_name, {})
    
    # 構建2025增強版學生檔案
    student_context = f"""
**Comprehensive Student Profile for Advanced EMI Analysis (2025):**
- Student Name: {student.name}
- Total Learning Interactions: {student.message_count}
- Academic Questions Posed: {student.question_count}
- Participation Rate: {student.participation_rate}%
- Recent Activity Sample: {len(messages)} recent messages
- Historical Analysis Records: {len(analyses)} educational assessments
- Learning Context: English-Medium Instruction (EMI) educational environment
- Analysis Technology: {analytics_model_name} ({current_specs.get('analysis_quality', 'standard')} analysis capability)
- Model Generation: {current_specs.get('generation', 'N/A')} with {current_specs.get('type', 'Standard')} configuration
- Advanced Features: {'Thinking capability enabled' if current_specs.get('thinking_capability') else 'Standard processing mode'}
    """
    
    # 2025增強版建議生成 prompt
    recommendations_prompt = f"""As a distinguished EMI (English-Medium Instruction) educational consultant utilizing {analytics_model_name} (Generation {current_specs.get('generation', 'N/A')}) with {current_specs.get('analysis_quality', 'standard')} analysis capabilities, provide evidence-based personalized educational recommendations:

{student_context}

**Recent Learning Interaction Patterns:**
{chr(10).join([f"- {msg.content[:80]}..." for msg in messages[-8:]])}

Generate comprehensive, research-backed recommendations in professional English across these strategic areas:

**📚 Academic Skill Development & Learning Priorities:**
[Identify specific English language competencies, subject knowledge areas, and academic skills requiring focused attention for optimal EMI learning progression.]

**🎯 Personalized Learning Methodologies & Instructional Approaches:**
[Recommend evidence-based pedagogical strategies, learning techniques, and instructional methods specifically tailored to enhance this student's academic success in EMI environments.]

**💡 Immediate Implementation Strategies & Learning Objectives:**
[Provide actionable, measurable steps and short-term academic goals that can be implemented immediately for tangible learning progress.]

**⚠️ Learning Challenges & Strategic Interventions:**
[Identify potential academic obstacles, language proficiency barriers, or skill development needs requiring targeted educational support with specific intervention strategies.]

**🔧 Instructional Adaptations & Teaching Modifications:**
[Suggest specific classroom strategies, instructional adjustments, and pedagogical modifications that EMI educators should implement to maximize learning outcomes for this student.]

**📈 Progress Assessment & Monitoring Frameworks:**
[Recommend systematic approaches for tracking academic development, measuring learning improvements, and adapting instructional strategies based on ongoing performance data.]

**🌟 Strength Amplification & Talent Optimization:**
[Identify existing student capabilities and recommend strategies to leverage these strengths for enhanced learning and potential academic leadership opportunities.]

**🚀 Long-term Academic Development & Career Preparation:**
[Suggest pathways for sustained academic growth and preparation for advanced educational or professional opportunities in English-medium contexts.]

Format as actionable, research-informed recommendations in professional English for both student self-directed learning and EMI instructor implementation (target: 400-500 words)."""

    try:
        start_time = time.time()
        response = model.generate_content(recommendations_prompt)
        response_time = time.time() - start_time
        
        if response and response.text:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'recommendations': response.text,
                'model_used': analytics_model_name,
                'model_generation': current_specs.get('generation', 'unknown'),
                'model_type': current_specs.get('type', 'unknown'),
                'analysis_quality': current_specs.get('analysis_quality', 'standard'),
                'thinking_enabled': current_specs.get('thinking_capability', False),
                'response_time': round(response_time, 2),
                'data_points': len(messages) + len(analyses),
                'recommended_model': recommended_model,
                'model_specs': current_specs,
                'generated_at': datetime.datetime.now().isoformat(),
                'language': 'english',
                'status': 'success'
            }
    except Exception as e:
        logger.error(f"建議生成錯誤: {e}")
    
    # 2025增強版備用建議
    fallback_recommendations = f"""**Advanced Personalized Learning Recommendations for {student.name}**
*Generated by Enhanced 2025 Recommendation System*

**📚 Academic Skill Development & Learning Priorities:**
Based on {len(messages)} learning interactions and {student.participation_rate}% participation rate, this student should focus on {'advanced English academic discourse, critical thinking skills, and subject-specific terminology mastery' if student.participation_rate > 75 else 'intermediate English communication skills, analytical thinking development, and academic vocabulary expansion' if student.participation_rate > 50 else 'foundational English language confidence, basic academic interaction skills, and core vocabulary building'}.

**🎯 Personalized Learning Methodologies & Instructional Approaches:**
Implement {'inquiry-based learning with independent research projects, peer collaboration, and advanced discussion facilitation' if len(messages) > 15 else 'structured guided practice with scaffolded support, collaborative learning activities, and progressive skill building' if len(messages) > 8 else 'supportive individual learning with frequent positive feedback, confidence-building activities, and structured practice sessions'} to maximize engagement and achievement in the EMI environment.

**💡 Immediate Implementation Strategies & Learning Objectives:**
1. {'Maintain current high-engagement patterns while expanding into leadership and mentoring roles' if student.participation_rate > 75 else 'Increase active participation frequency and develop stronger academic communication skills' if student.participation_rate > 50 else 'Build fundamental academic confidence through supported practice and incremental challenge progression'}
2. Develop personalized learning portfolio with measurable weekly targets
3. Establish regular self-reflection and progress monitoring routines
4. Create subject-specific vocabulary and concept mastery goals

**⚠️ Learning Challenges & Strategic Interventions:**
Priority areas for attention include {'maintaining academic excellence while exploring new challenge domains and leadership opportunities' if student.participation_rate > 75 else 'addressing participation barriers, building academic confidence, and strengthening core subject knowledge' if student.participation_rate > 50 else 'providing comprehensive language support, creating safe learning environments, and building foundational academic skills'}.

**🔧 Instructional Adaptations & Teaching Modifications:**
Utilize {'advanced project-based learning, student-led discussions, and independent research methodologies' if student.participation_rate > 75 else 'interactive activities with clear structure, peer support systems, and collaborative learning formats' if student.participation_rate > 50 else 'supportive, low-pressure learning environments with individualized attention and positive reinforcement strategies'} to optimize educational outcomes.

**📈 Progress Assessment & Monitoring Frameworks:**
Implement comprehensive formative assessment strategies including learning reflection journals, peer feedback systems, progress tracking tools, and regular instructor-student conferences to monitor development and adjust instruction as needed.

**🌟 Strength Amplification & Talent Optimization:**
Leverage this student's {'natural academic leadership abilities, strong analytical skills, and high motivation' if student.participation_rate > 75 else 'emerging academic competencies, positive learning attitude, and developing communication skills' if student.participation_rate > 50 else 'unique individual potential, personal learning style, and areas of natural interest'} to create meaningful learning opportunities and build on existing capabilities.

**🚀 Long-term Academic Development & Career Preparation:**
Focus on {'advanced academic preparation, research skills development, and leadership opportunity creation' if student.participation_rate > 75 else 'continued skill building, academic confidence development, and expanded learning opportunities' if student.participation_rate > 50 else 'foundational skill strengthening, confidence building, and gradual academic challenge increase'} to prepare for future educational and professional success in English-medium contexts."""
    
    return {
        'student_id': student_id,
        'student_name': student.name,
        'recommendations': fallback_recommendations,
        'model_used': 'enhanced_fallback_2025',
        'model_generation': 'fallback',
        'model_type': 'Fallback-Enhanced',
        'analysis_quality': 'fallback_comprehensive',
        'thinking_enabled': False,
        'response_time': 0.1,
        'data_points': len(messages) + len(analyses),
        'recommended_model': recommended_model,
        'model_specs': {'type': 'Fallback', 'analysis_strength': 'Enhanced backup recommendations'},
        'generated_at': datetime.datetime.now().isoformat(),
        'language': 'english',
        'status': 'fallback_enhanced'
    }

def generate_personalized_recommendations(student_id):
    """生成個人化學習建議（支援2025最新模型智慧備案）"""
    return execute_with_intelligent_fallback(_generate_personalized_recommendations_internal, student_id)

# =================== 班級整體分析 (2025最新版本) ===================

def _generate_class_analysis_internal(model):
    """內部班級分析函數 - 2025最新英文版本"""
    # 取得所有真實學生資料
    real_students = list(Student.select().where(
        ~Student.name.startswith('[DEMO]') & 
        ~Student.line_user_id.startswith('demo_')
    ))
    
    if len(real_students) < 2:
        return {'status': 'insufficient_students', 'student_count': len(real_students)}
    
    # 計算詳細班級統計
    total_messages = sum(s.message_count for s in real_students)
    total_questions = sum(s.question_count for s in real_students)
    avg_participation = sum(s.participation_rate for s in real_students) / len(real_students)
    
    # 分析參與度分佈
    high_engagement = [s for s in real_students if s.participation_rate > 70]
    medium_engagement = [s for s in real_students if 40 <= s.participation_rate <= 70]
    low_engagement = [s for s in real_students if s.participation_rate < 40]
    
    # 取得近期活動
    recent_messages = Message.select().where(
        Message.timestamp > datetime.datetime.now() - datetime.timedelta(days=7)
    ).count()
    
    # 智慧模型選擇
    recommended_model = optimize_model_selection(len(real_students), total_messages, 'medium')
    current_specs = ANALYTICS_MODEL_SPECS.get(analytics_model_name, {})
    
    # 2025增強版班級分析 prompt
    class_context = f"""
**Comprehensive EMI Class Analysis Profile (2025):**
- Total Active Students: {len(real_students)}
- Total Learning Interactions: {total_messages}
- Total Academic Questions: {total_questions}
- Average Class Participation Rate: {avg_participation:.1f}%
- Recent Activity (7 days): {recent_messages} messages
- High Engagement Students: {len(high_engagement)} ({len(high_engagement)/len(real_students)*100:.1f}%)
- Medium Engagement Students: {len(medium_engagement)} ({len(medium_engagement)/len(real_students)*100:.1f}%)
- Low Engagement Students: {len(low_engagement)} ({len(low_engagement)/len(real_students)*100:.1f}%)
- Most Active Learners: {[s.name for s in sorted(real_students, key=lambda x: x.participation_rate, reverse=True)[:3]]}
- Analysis Date: {datetime.datetime.now().strftime('%Y-%m-%d')}
- Learning Environment: English-Medium Instruction (EMI)
- Analysis Technology: {analytics_model_name} ({current_specs.get('analysis_quality', 'standard')} analysis)
- Model Generation: {current_specs.get('generation', 'N/A')} with {current_specs.get('type', 'Standard')} configuration
    """
    
    class_analysis_prompt = f"""As a senior EMI (English-Medium Instruction) educational researcher using advanced {analytics_model_name} (Generation {current_specs.get('generation', 'N/A')}) with {current_specs.get('analysis_quality', 'standard')} analysis capabilities, provide a comprehensive class performance analysis in professional English:

{class_context}

Deliver a detailed English class analysis covering these comprehensive areas:

**📊 Overall Class Performance & Learning Dynamics:**
[Assess overall class engagement patterns, participation trends, and collective learning progress in the EMI environment with specific attention to performance distribution.]

**🎯 Class Strengths & Educational Achievements:**
[Identify what this class excels at in terms of English language learning, academic participation, collaborative learning, and educational outcomes.]

**⚠️ Areas Requiring Strategic Improvement & Intervention:**
[Specify challenges and areas where the class needs focused attention, targeted support, and strategic educational interventions.]

**💡 Evidence-Based Teaching Strategies & Methodologies:**
[Recommend proven EMI teaching approaches, instructional strategies, and pedagogical methods to enhance overall class learning and engagement.]

**📈 Learning Development Trends & Progress Patterns:**
[Analyze observable patterns in class academic progress, engagement evolution, and suggest strategies for sustained educational growth.]

**🔧 Implementation Guidelines & Practical Applications:**
[Provide specific, actionable recommendations for improved EMI class outcomes with concrete implementation steps and timelines.]

**👥 Student Engagement Distribution & Support Strategies:**
[Address the needs of different engagement levels within the class and recommend differentiated support approaches.]

**🚀 Future Development & Enhancement Opportunities:**
[Suggest long-term strategies for class advancement and opportunities for expanding learning capabilities.]

Format as a comprehensive professional educational analysis in English for EMI instructors, department heads, and academic administrators (target: 500-600 words)."""

    try:
        start_time = time.time()
        response = model.generate_content(class_analysis_prompt)
        response_time = time.time() - start_time
        
        if response and response.text:
            return {
                'class_analysis': response.text,
                'model_used': analytics_model_name,
                'model_generation': current_specs.get('generation', 'unknown'),
                'model_type': current_specs.get('type', 'unknown'),
                'analysis_quality': current_specs.get('analysis_quality', 'standard'),
                'thinking_enabled': current_specs.get('thinking_capability', False),
                'response_time': round(response_time, 2),
                'student_count': len(real_students),
                'engagement_distribution': {
                    'high_engagement': len(high_engagement),
                    'medium_engagement': len(medium_engagement),
                    'low_engagement': len(low_engagement)
                },
                'data_summary': {
                    'total_messages': total_messages,
                    'total_questions': total_questions,
                    'avg_participation': round(avg_participation, 1),
                    'recent_activity': recent_messages
                },
                'recommended_model': recommended_model,
                'model_specs': current_specs,
                'generated_at': datetime.datetime.now().isoformat(),
                'language': 'english',
                'status': 'success'
            }
    except Exception as e:
        logger.error(f"班級分析生成錯誤: {e}")
    
    # 2025增強版備用班級分析
    fallback_analysis = f"""**Comprehensive EMI Class Performance Analysis (2025)**
*Generated by Enhanced Fallback Analysis System*

**📊 Overall Class Performance & Learning Dynamics:**
This EMI class consists of {len(real_students)} active students with a collective total of {total_messages} learning interactions and {total_questions} academic questions. The average participation rate of {avg_participation:.1f}% indicates {'exceptional overall class engagement' if avg_participation > 70 else 'strong class participation' if avg_participation > 50 else 'developing class engagement'} in English-medium instruction activities. The engagement distribution shows {len(high_engagement)} high-performing students ({len(high_engagement)/len(real_students)*100:.1f}%), {len(medium_engagement)} moderate performers ({len(medium_engagement)/len(real_students)*100:.1f}%), and {len(low_engagement)} students requiring additional support ({len(low_engagement)/len(real_students)*100:.1f}%).

**🎯 Class Strengths & Educational Achievements:**
The class demonstrates {'exceptional collaborative learning and academic excellence' if avg_participation > 70 else 'solid academic progress and consistent engagement' if avg_participation > 50 else 'emerging participation patterns with growth potential'} with {recent_messages} recent interactions indicating {'highly active learning community' if recent_messages > 50 else 'steady academic engagement' if recent_messages > 20 else 'developing learning momentum'}. Students show {'advanced questioning behavior and intellectual curiosity' if total_questions > total_messages * 0.3 else 'balanced communication patterns with academic focus'} in the EMI environment.

**⚠️ Areas Requiring Strategic Improvement & Intervention:**
Priority focus needed on {'maintaining current excellence while expanding advanced learning opportunities' if avg_participation > 70 else 'increasing overall participation rates and strengthening student engagement' if avg_participation > 50 else 'building foundational engagement and confidence across the class'}. Specific attention required for {'advanced challenge provision' if len(high_engagement) > len(real_students) * 0.5 else 'differentiated support strategies' if len(medium_engagement) > len(real_students) * 0.4 else 'comprehensive engagement building'}.

**💡 Evidence-Based Teaching Strategies & Methodologies:**
Recommended approaches include:
1. {'Advanced project-based learning and student-led research initiatives' if avg_participation > 70 else 'Interactive collaborative activities with structured peer support' if avg_participation > 50 else 'Supportive individual practice with confidence-building group work'}
2. Implement differentiated instruction to address the needs of {len(high_engagement)} high achievers, {len(medium_engagement)} developing learners, and {len(low_engagement)} students requiring additional support
3. Use diverse EMI teaching methods including multimedia resources, interactive discussions, and hands-on learning experiences
4. Establish peer mentoring systems to leverage high-performing students as learning facilitators

**📈 Learning Development Trends & Progress Patterns:**
The class shows {'outstanding academic momentum with sustained high performance' if avg_participation > 70 else 'positive development trajectory with consistent improvement' if avg_participation > 50 else 'emerging growth patterns with significant potential'} in EMI learning outcomes. Recent activity patterns suggest {'excellent learning community cohesion' if recent_messages > 30 else 'developing collaborative learning dynamics'} with opportunities for {'advanced skill development' if avg_participation > 70 else 'continued growth and engagement enhancement'}.

**🔧 Implementation Guidelines & Practical Applications:**
- Conduct weekly progress monitoring for all engagement levels
- Implement tiered assignment strategies to challenge high performers while supporting developing learners
- Use formative assessment tools to track individual and class progress
- Create flexible learning groups based on student needs and interests
- Establish regular feedback cycles for continuous improvement

**👥 Student Engagement Distribution & Support Strategies:**
Address the diverse needs through targeted interventions: advanced enrichment for high performers, skill-building support for medium engagement students, and intensive assistance for low engagement learners, ensuring all students can succeed in the EMI environment.

**🚀 Future Development & Enhancement Opportunities:**
Focus on {'leadership development and advanced academic challenges' if avg_participation > 70 else 'sustained engagement building and skill advancement' if avg_participation > 50 else 'foundational confidence building and gradual challenge increase'} to prepare the entire class for continued success in English-medium academic environments."""
    
    return {
        'class_analysis': fallback_analysis,
        'model_used': 'enhanced_fallback_2025',
        'model_generation': 'fallback',
        'model_type': 'Fallback-Enhanced',
        'analysis_quality': 'fallback_comprehensive',
        'thinking_enabled': False,
        'response_time': 0.1,
        'student_count': len(real_students),
        'engagement_distribution': {
            'high_engagement': len(high_engagement),
            'medium_engagement': len(medium_engagement),
            'low_engagement': len(low_engagement)
        },
        'data_summary': {
            'total_messages': total_messages,
            'total_questions': total_questions,
            'avg_participation': round(avg_participation, 1),
            'recent_activity': recent_messages
        },
        'recommended_model': recommended_model,
        'model_specs': {'type': 'Fallback', 'analysis_strength': 'Enhanced backup class analysis'},
        'generated_at': datetime.datetime.now().isoformat(),
        'language': 'english',
        'status': 'fallback_enhanced'
    }

def generate_class_analysis():
    """生成班級整體分析（支援2025最新模型智慧備案）"""
    return execute_with_intelligent_fallback(_generate_class_analysis_internal)

# =================== 系統狀態和管理功能 ===================

def get_analytics_status():
    """取得增強的分析系統狀態 (2025版本)"""
    current_specs = ANALYTICS_MODEL_SPECS.get(analytics_model_name, {})
    
    # 計算模型性能統計
    total_calls = sum(stats['calls'] for stats in model_performance_stats.values())
    total_successes = sum(stats['successes'] for stats in model_performance_stats.values())
    total_errors = sum(stats['errors'] for stats in model_performance_stats.values())
    overall_success_rate = (total_successes / max(total_calls, 1)) * 100
    
    # 找出表現最佳的模型
    best_models = sorted(
        [(name, stats) for name, stats in model_performance_stats.items() if stats['calls'] > 0],
        key=lambda x: (x[1]['successes'] / max(x[1]['calls'], 1), -x[1]['avg_response_time']),
        reverse=True
    )[:3]
    
    status = {
        # 當前模型資訊
        'current_model': analytics_model_name,
        'model_generation': current_specs.get('generation', 'unknown'),
        'model_type': current_specs.get('type', 'unknown'),
        'analysis_quality': current_specs.get('analysis_quality', 'unknown'),
        'thinking_capability': current_specs.get('thinking_capability', False),
        'context_window': current_specs.get('context_window', 'unknown'),
        'analysis_strength': current_specs.get('analysis_strength', '未知'),
        'recommended_for': current_specs.get('recommended_for', '一般分析'),
        
        # 系統統計
        'model_switches': model_switch_count,
        'total_analysis_calls': total_calls,
        'overall_success_rate': round(overall_success_rate, 1),
        'total_errors': total_errors,
        
        # 模型清單和規格
        'available_models': ANALYTICS_MODELS,
        'model_specs': ANALYTICS_MODEL_SPECS,
        'model_performance_stats': model_performance_stats,
        'best_performing_models': [name for name, _ in best_models],
        
        # 系統狀態
        'model_initialized': current_analytics_model is not None,
        'api_key_configured': GEMINI_API_KEY is not None,
        'system_status': 'optimal' if current_analytics_model and overall_success_rate > 80 else 'functional' if current_analytics_model else 'initializing',
        
        # 活動歷史
        'recent_tasks': analysis_task_history[-10:] if analysis_task_history else [],
        'total_analysis_tasks': len(analysis_task_history),
        
        # 智慧建議
        'optimization_suggestions': generate_optimization_suggestions(current_specs, model_performance_stats),
        
        # 版本資訊
        'system_version': '2025.06.25',
        'last_updated': datetime.datetime.now().isoformat()
    }
    
    return status

def generate_optimization_suggestions(current_specs, performance_stats):
    """生成智慧優化建議"""
    suggestions = []
    
    # 基於當前模型性能
    current_stats = performance_stats.get(analytics_model_name, {})
    if current_stats.get('calls', 0) > 0:
        error_rate = (current_stats.get('errors', 0) / current_stats['calls']) * 100
        if error_rate > 30:
            suggestions.append("考慮切換到更穩定的模型，當前錯誤率較高")
        elif error_rate < 5:
            suggestions.append("當前模型表現優秀，建議保持使用")
    
    # 基於模型類型
    if current_specs.get('thinking_capability'):
        suggestions.append("利用思考能力模型進行更深度的學習分析")
    
    if current_specs.get('analysis_quality') == 'outstanding':
        suggestions.append("當前使用頂級分析模型，適合複雜教學研究")
    elif current_specs.get('analysis_quality') == 'excellent':
        suggestions.append("使用高品質分析模型，平衡效能與成本")
    
    # 基於系統使用模式
    if model_switch_count > 5:
        suggestions.append("頻繁模型切換，建議檢查網路連接和API配額")
    
    return suggestions

def build_comprehensive_student_profile(student_id):
    """建立綜合學生檔案 (2025增強版)"""
    try:
        student = Student.get_by_id(student_id)
        
        # 收集所有相關資料
        messages = list(Message.select().where(Message.student_id == student_id))
        analyses = list(Analysis.select().where(
            (Analysis.student_id == student_id) &
            (Analysis.analysis_type == 'question_classification')
        ))
        
        # 計算學習期間
        learning_period = (datetime.datetime.now() - student.created_at).days if student.created_at else 0
        
        # 智慧模型推薦
        recommended_model = optimize_model_selection(1, len(messages), 'medium')
        
        profile = {
            'student_info': {
                'id': student.id,
                'name': student.name,
                'participation_rate': student.participation_rate,
                'question_count': student.question_count,
                'message_count': student.message_count,
                'engagement_level': 'high' if student.participation_rate > 70 else 'medium' if student.participation_rate > 40 else 'developing'
            },
            'data_summary': {
                'total_messages': len(messages),
                'total_analyses': len(analyses),
                'data_quality': 'rich' if len(messages) >= 20 else 'sufficient' if len(messages) >= 5 else 'limited',
                'analysis_depth': 'comprehensive' if len(analyses) >= 5 else 'moderate' if len(analyses) >= 2 else 'basic'
            },
            'model_info': {
                'current_model': analytics_model_name,
                'recommended_model': recommended_model,
                'model_generation': ANALYTICS_MODEL_SPECS.get(analytics_model_name, {}).get('generation', 'unknown'),
                'analysis_quality': ANALYTICS_MODEL_SPECS.get(analytics_model_name, {}).get('analysis_quality', 'standard'),
                'thinking_capability': ANALYTICS_MODEL_SPECS.get(analytics_model_name, {}).get('thinking_capability', False),
                'model_switches': model_switch_count
            },
            'learning_insights': {
                'questions_per_message_ratio': round(student.question_count / max(student.message_count, 1), 2),
                'avg_daily_interaction': round(len(messages) / max(learning_period, 1), 2) if learning_period > 0 else 0,
                'recent_activity_trend': 'active' if len([m for m in messages if (datetime.datetime.now() - m.timestamp).days <= 7]) > 0 else 'inactive'
            },
            'recommendations': {
                'suggested_model': recommended_model,
                'analysis_priority': 'high' if student.participation_rate > 70 else 'medium' if student.participation_rate > 40 else 'supportive',
                'intervention_needed': student.participation_rate < 40,
                'strengths_focus': student.participation_rate > 70
            },
            'profile_metadata': {
                'generated_at': datetime.datetime.now().isoformat(),
                'system_version': '2025.06.25',
                'profile_completeness': 'comprehensive' if len(messages) >= 10 and len(analyses) >= 2 else 'standard'
            }
        }
        
        return profile
        
    except Exception as e:
        logger.error(f"學生檔案建立錯誤: {e}")
        return {
            'error': str(e),
            'status': 'error',
            'timestamp': datetime.datetime.now().isoformat()
        }

def get_model_recommendations_for_context(context_type: str, urgency: str = "normal") -> dict:
    """根據使用情境提供模型建議"""
    
    recommendations = {
        'daily_teaching': {
            'primary': 'gemini-2.5-flash',
            'backup': 'gemini-2.5-flash-lite',
            'reason': '最佳日常教學分析平衡'
        },
        'research_analysis': {
            'primary': 'gemini-2.5-pro',
            'backup': 'gemini-2.5-flash',
            'reason': '深度研究需要最高分析品質'
        },
        'bulk_processing': {
            'primary': 'gemini-2.5-flash-lite',
            'backup': 'gemini-2.0-flash-lite',
            'reason': '大量處理優先考慮速度和成本'
        },
        'emergency_analysis': {
            'primary': 'gemini-2.5-flash-lite',
            'backup': 'gemini-2.0-flash',
            'reason': '緊急情況需要最快回應'
        },
        'comprehensive_report': {
            'primary': 'gemini-2.5-pro',
            'backup': 'gemini-2.0-pro',
            'reason': '綜合報告需要最佳分析深度'
        }
    }
    
    if urgency == "high":
        # 高緊急度優先選擇速度
        for context in recommendations.values():
            if 'flash-lite' in context['primary']:
                continue
            context['primary'] = context['primary'].replace('pro', 'flash').replace('flash', 'flash-lite')
    
    return recommendations.get(context_type, recommendations['daily_teaching'])

# =================== 系統健康檢查和診斷 ===================

def perform_system_health_check():
    """執行完整的系統健康檢查"""
    health_report = {
        'timestamp': datetime.datetime.now().isoformat(),
        'overall_status': 'unknown',
        'checks': {}
    }
    
    # 檢查API連接
    try:
        if GEMINI_API_KEY:
            health_report['checks']['api_key'] = {'status': 'ok', 'message': 'API Key 已配置'}
        else:
            health_report['checks']['api_key'] = {'status': 'error', 'message': 'API Key 未設定'}
    except Exception as e:
        health_report['checks']['api_key'] = {'status': 'error', 'message': f'API Key 檢查失敗: {e}'}
    
    # 檢查模型初始化
    try:
        if current_analytics_model:
            health_report['checks']['model_init'] = {'status': 'ok', 'message': f'模型已初始化: {analytics_model_name}'}
        else:
            health_report['checks']['model_init'] = {'status': 'warning', 'message': '模型未初始化'}
    except Exception as e:
        health_report['checks']['model_init'] = {'status': 'error', 'message': f'模型檢查失敗: {e}'}
    
    # 檢查模型性能
    try:
        current_stats = model_performance_stats.get(analytics_model_name, {})
        if current_stats.get('calls', 0) > 0:
            success_rate = (current_stats.get('successes', 0) / current_stats['calls']) * 100
            if success_rate > 80:
                health_report['checks']['performance'] = {'status': 'ok', 'message': f'性能良好: {success_rate:.1f}% 成功率'}
            elif success_rate > 50:
                health_report['checks']['performance'] = {'status': 'warning', 'message': f'性能一般: {success_rate:.1f}% 成功率'}
            else:
                health_report['checks']['performance'] = {'status': 'error', 'message': f'性能不佳: {success_rate:.1f}% 成功率'}
        else:
            health_report['checks']['performance'] = {'status': 'info', 'message': '尚無性能數據'}
    except Exception as e:
        health_report['checks']['performance'] = {'status': 'error', 'message': f'性能檢查失敗: {e}'}
    
    # 檢查系統資源
    try:
        recent_tasks = len([task for task in analysis_task_history if 
                          (datetime.datetime.now() - task['timestamp']).seconds < 3600])  # 最近1小時
        if recent_tasks > 100:
            health_report['checks']['resources'] = {'status': 'warning', 'message': f'使用量較高: {recent_tasks} 次/小時'}
        else:
            health_report['checks']['resources'] = {'status': 'ok', 'message': f'使用量正常: {recent_tasks} 次/小時'}
    except Exception as e:
        health_report['checks']['resources'] = {'status': 'error', 'message': f'資源檢查失敗: {e}'}
    
    # 計算整體狀態
    statuses = [check['status'] for check in health_report['checks'].values()]
    if 'error' in statuses:
        health_report['overall_status'] = 'error'
    elif 'warning' in statuses:
        health_report['overall_status'] = 'warning'
    else:
        health_report['overall_status'] = 'ok'
    
    return health_report

# =================== 實用工具函數 ===================

def get_model_comparison_table():
    """生成模型比較表格"""
    comparison = []
    for model_name in ANALYTICS_MODELS[:6]:  # 顯示前6個主要模型
        specs = ANALYTICS_MODEL_SPECS.get(model_name, {})
        stats = model_performance_stats.get(model_name, {})
        
        success_rate = 0
        if stats.get('calls', 0) > 0:
            success_rate = (stats.get('successes', 0) / stats['calls']) * 100
        
        comparison.append({
            'model': model_name,
            'generation': specs.get('generation', 'N/A'),
            'type': specs.get('type', 'N/A'),
            'quality': specs.get('analysis_quality', 'unknown'),
            'thinking': '是' if specs.get('thinking_capability') else '否',
            'context': specs.get('context_window', 'N/A'),
            'cost': specs.get('cost_tier', 'unknown'),
            'calls': stats.get('calls', 0),
            'success_rate': f"{success_rate:.1f}%" if stats.get('calls', 0) > 0 else 'N/A',
            'best_for': specs.get('recommended_for', '一般分析')
        })
    
    return comparison

def cleanup_old_task_history(days_to_keep=7):
    """清理舊的任務歷史記錄"""
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
    
    global analysis_task_history
    old_count = len(analysis_task_history)
    analysis_task_history = [
        task for task in analysis_task_history 
        if task.get('timestamp', datetime.datetime.now()) > cutoff_date
    ]
    new_count = len(analysis_task_history)
    
    if old_count > new_count:
        logger.info(f"🧹 清理任務歷史: 移除 {old_count - new_count} 筆舊記錄")
    
    return old_count - new_count

# =================== 初始化和匯出 ===================

def initialize_system():
    """初始化整個分析系統"""
    logger.info("🚀 初始化 EMI 教學分析系統 (2025最新版本)")
    logger.info(f"📊 可用模型數量: {len(ANALYTICS_MODELS)}")
    logger.info(f"🎯 預設模型: {analytics_model_name}")
    logger.info(f"🔧 系統版本: 2025.06.25")
    
    # 初始化分析模型
    result = initialize_analytics_model()
    
    if result:
        logger.info("✅ 系統初始化完成")
        
        # 執行健康檢查
        health = perform_system_health_check()
        logger.info(f"🏥 系統健康狀態: {health['overall_status']}")
        
        return True
    else:
        logger.error("❌ 系統初始化失敗")
        return False

# 啟動系統初始化
logger.info("🔬 開始載入增強版教學分析系統（2025最新模型）...")
if __name__ != '__main__':
    initialize_system()

# 定期清理任務（如果是主要執行）
if __name__ == '__main__':
    cleanup_old_task_history()

# =================== 匯出函數清單 ===================

__all__ = [
    # 主要分析功能
    'generate_conversation_summary',
    'generate_personalized_recommendations', 
    'generate_class_analysis',
    'build_comprehensive_student_profile',
    
    # 系統管理
    'get_analytics_status',
    'switch_analytics_model',
    'initialize_analytics_model',
    'perform_system_health_check',
    
    # 智慧選擇
    'get_optimal_model_for_task',
    'optimize_model_selection',
    'get_model_recommendations_for_context',
    
    # 工具和資訊
    'get_model_comparison_table',
    'cleanup_old_task_history',
    'initialize_system',
    
    # 配置和規格
    'ANALYTICS_MODELS',
    'ANALYTICS_MODEL_SPECS',
    
    # 系統變數（唯讀）
    'analytics_model_name',
    'model_switch_count',
    'analysis_task_history'
]

# =================== 系統版本資訊 ===================

SYSTEM_INFO = {
    'name': 'EMI Teaching Analytics System',
    'version': '2025.06.25',
    'description': '支援最新 Gemini 2.5/2.0 系列模型的智慧教學分析系統',
    'features': [
        '智慧模型選擇和切換',
        '思考能力增強分析',
        '多層次備用機制', 
        '即時性能監控',
        '成本效益優化',
        '英文教學專用分析'
    ],
    'supported_models': len(ANALYTICS_MODELS),
    'primary_models': ANALYTICS_MODELS[:3],
    'last_updated': '2025-06-25',
    'author': 'EMI Education Technology Team'
}

logger.info(f"📚 {SYSTEM_INFO['name']} v{SYSTEM_INFO['version']} 載入完成")
logger.info(f"🎯 支援 {SYSTEM_INFO['supported_models']} 個模型，主力模型: {', '.join(SYSTEM_INFO['primary_models'])}")

# 檔案結束
