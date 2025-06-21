# teaching_analytics.py - 教學分析核心功能
# 包含：對話摘要、個人化建議、班級分析

import os
import json
import datetime
import logging
from collections import defaultdict, Counter
import google.generativeai as genai
from models import Student, Message, Analysis, db

logger = logging.getLogger(__name__)

# 初始化 Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
    except:
        model = None
else:
    model = None

# =========================================
# 1. 智能對話摘要功能
# =========================================

def generate_conversation_summary(student_id, days=30):
    """生成學生對話摘要"""
    try:
        if not model:
            return {'error': 'AI model not available'}
            
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
        
        # 生成教學重點摘要
        summary_prompt = f"""As an educational expert, analyze this student's conversation patterns for teaching insights:

Student: {student.name}
Participation Rate: {student.participation_rate}%
Total Messages: {len(messages)}

Recent Conversation Excerpts:
{chr(10).join(conversation_text[-10:])}  # 最近10則

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
            # 解析摘要內容
            summary_text = response.text.strip()
            parsed_summary = parse_summary_sections(summary_text)
            
            return {
                'success': True,
                'raw_summary': summary_text,
                'parsed_summary': parsed_summary,
                'key_topics': parsed_summary.get('key_topics', 'Analyzing discussion content...'),
                'understanding_level': parsed_summary.get('understanding_level', 'Assessing comprehension...'),
                'recommendations': parsed_summary.get('recommendations', 'Generating teaching suggestions...'),
                'learning_patterns': parsed_summary.get('learning_patterns', 'Identifying patterns...'),
                'message_count': len(messages),
                'analysis_period': f"{days} days",
                'generated_at': datetime.datetime.now().isoformat()
            }
        else:
            return {'error': 'Failed to generate summary'}
            
    except Exception as e:
        logger.error(f"對話摘要生成錯誤: {e}")
        return {'error': str(e)}

def parse_summary_sections(summary_text):
    """解析摘要文本的各個部分"""
    try:
        sections = {
            'key_topics': '',
            'understanding_level': '',
            'recommendations': '',
            'learning_patterns': ''
        }
        
        # 簡單的文本解析
        lines = summary_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if '🎯' in line or 'Key Topics' in line:
                current_section = 'key_topics'
            elif '📈' in line or 'Understanding Level' in line:
                current_section = 'understanding_level'
            elif '💡' in line or 'Teaching Recommendations' in line:
                current_section = 'recommendations'
            elif '🔍' in line or 'Learning Patterns' in line:
                current_section = 'learning_patterns'
            elif line and current_section and not line.startswith('**'):
                sections[current_section] += line + ' '
        
        # 如果解析失敗，使用整個摘要作為理解程度
        if not any(sections.values()):
            sections['understanding_level'] = summary_text
        
        return sections
        
    except Exception as e:
        logger.error(f"摘要解析錯誤: {e}")
        return {'understanding_level': summary_text}

def generate_teaching_focused_summary(student_id):
    """生成教學重點摘要（更詳細版本）"""
    try:
        if not model:
            return {'error': 'AI model not available'}
            
        student = Student.get_by_id(student_id)
        
        # 取得所有對話和分析資料
        all_messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.asc()))
        
        question_analyses = list(Analysis.select().where(
            (Analysis.student_id == student_id) &
            (Analysis.analysis_type == 'question_classification')
        ))
        
        if len(all_messages) < 5:
            return {'status': 'insufficient_data'}
        
        # 分析學習進展
        learning_progression = analyze_learning_progression(all_messages, question_analyses)
        
        # 生成詳細教學摘要
        detailed_prompt = f"""Create a comprehensive teaching summary for this EMI student:

Student Profile:
- Name: {student.name}
- Total Interactions: {len(all_messages)}
- Questions Asked: {student.question_count}
- Participation Rate: {student.participation_rate}%
- Learning Period: {(all_messages[-1].timestamp - all_messages[0].timestamp).days} days

Learning Progression Analysis:
{json.dumps(learning_progression, indent=2)}

Provide a detailed teaching analysis covering:

1. **Learning Journey Overview**: How has this student's learning evolved?
2. **Cognitive Development**: What thinking skills have they demonstrated?
3. **Engagement Patterns**: When and how do they participate most effectively?
4. **Knowledge Gaps**: What areas need additional support?
5. **Strengths to Leverage**: What learning strengths can be built upon?
6. **Next Learning Steps**: Specific recommendations for continued growth

Format as structured insights for EMI instructors (300-400 words):"""

        response = model.generate_content(detailed_prompt)
        
        if response and response.text:
            return {
                'success': True,
                'detailed_summary': response.text.strip(),
                'learning_progression': learning_progression,
                'generated_at': datetime.datetime.now().isoformat()
            }
        else:
            return {'error': 'Failed to generate detailed summary'}
            
    except Exception as e:
        logger.error(f"詳細教學摘要生成錯誤: {e}")
        return {'error': str(e)}

def analyze_learning_progression(messages, analyses):
    """分析學習進展"""
    try:
        progression = {
            'early_phase': {'questions': 0, 'cognitive_levels': [], 'topics': []},
            'middle_phase': {'questions': 0, 'cognitive_levels': [], 'topics': []},
            'recent_phase': {'questions': 0, 'cognitive_levels': [], 'topics': []}
        }
        
        # 將訊息分成三個階段
        total_messages = len(messages)
        phase_size = total_messages // 3
        
        phases = [
            ('early_phase', messages[:phase_size]),
            ('middle_phase', messages[phase_size:phase_size*2]),
            ('recent_phase', messages[phase_size*2:])
        ]
        
        # 分析對應的問題分類
        for phase_name, phase_messages in phases:
            if not phase_messages:
                continue
                
            phase_analyses = [a for a in analyses 
                            if phase_messages[0].timestamp <= a.timestamp <= phase_messages[-1].timestamp]
            
            progression[phase_name]['questions'] = len([m for m in phase_messages if m.message_type == 'question'])
            
            for analysis in phase_analyses:
                try:
                    data = json.loads(analysis.analysis_data)
                    progression[phase_name]['cognitive_levels'].append(data.get('cognitive_level', 'Unknown'))
                    progression[phase_name]['topics'].append(data.get('content_domain', 'Unknown'))
                except json.JSONDecodeError:
                    continue
        
        return progression
        
    except Exception as e:
        logger.error(f"學習進展分析錯誤: {e}")
        return {}

# =========================================
# 2. 個人化學習建議功能
# =========================================

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
        
        # 分析問題模式
        question_patterns = analyze_question_patterns(analyses)
        
        # 參與度分析
        engagement_analysis = analyze_student_engagement(student, messages)
        
        # 認知發展追蹤
        cognitive_development = track_cognitive_development(analyses)
        
        # 學習風格識別
        learning_style = identify_learning_style(messages, analyses)
        
        profile = {
            'student_info': {
                'id': student.id,
                'name': student.name,
                'participation_rate': student.participation_rate,
                'question_count': student.question_count,
                'message_count': student.message_count,
                'learning_period_days': (datetime.datetime.now() - student.created_at).days if student.created_at else 0
            },
            'question_patterns': question_patterns,
            'engagement_analysis': engagement_analysis,
            'cognitive_development': cognitive_development,
            'learning_style': learning_style,
            'profile_generated': datetime.datetime.now().isoformat()
        }
        
        return profile
        
    except Exception as e:
        logger.error(f"學生檔案建立錯誤: {e}")
        return {'error': str(e)}

def analyze_question_patterns(analyses):
    """分析問題模式"""
    try:
        if not analyses:
            return {'status': 'no_data'}
        
        patterns = {
            'total_questions': len(analyses),
            'content_domains': Counter(),
            'cognitive_levels': Counter(),
            'question_types': Counter(),
            'difficulty_levels': Counter(),
            'complexity_trend': []
        }
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                
                patterns['content_domains'][data.get('content_domain', 'Unknown')] += 1
                patterns['cognitive_levels'][data.get('cognitive_level', 'Unknown')] += 1
                patterns['question_types'][data.get('question_type', 'Unknown')] += 1
                patterns['difficulty_levels'][data.get('difficulty', 'Unknown')] += 1
                
                # 追蹤複雜度趨勢
                patterns['complexity_trend'].append({
                    'date': analysis.timestamp.isoformat(),
                    'complexity': data.get('language_complexity', 'Basic')
                })
                
            except json.JSONDecodeError:
                continue
        
        # 轉換 Counter 為字典
        patterns['content_domains'] = dict(patterns['content_domains'])
        patterns['cognitive_levels'] = dict(patterns['cognitive_levels'])
        patterns['question_types'] = dict(patterns['question_types'])
        patterns['difficulty_levels'] = dict(patterns['difficulty_levels'])
        
        return patterns
        
    except Exception as e:
        logger.error(f"問題模式分析錯誤: {e}")
        return {'error': str(e)}

def analyze_student_engagement(student, messages):
    """分析學生參與度"""
    try:
        if not messages:
            return {'status': 'no_data'}
        
        # 時間分析
        active_days = len(set(msg.timestamp.date() for msg in messages))
        
        # 互動模式分析
        questions = [msg for msg in messages if msg.message_type == 'question']
        statements = [msg for msg in messages if msg.message_type == 'statement']
        
        # 最近活動趨勢
        recent_messages = [msg for msg in messages 
                          if msg.timestamp > datetime.datetime.now() - datetime.timedelta(days=7)]
        
        engagement = {
            'total_messages': len(messages),
            'total_questions': len(questions),
            'total_statements': len(statements),
            'active_days': active_days,
            'avg_daily_messages': len(messages) / max(active_days, 1),
            'question_ratio': len(questions) / max(len(messages), 1),
            'recent_activity': len(recent_messages),
            'engagement_level': classify_engagement_level(student.participation_rate),
            'activity_pattern': analyze_activity_pattern(messages)
        }
        
        return engagement
        
    except Exception as e:
        logger.error(f"參與度分析錯誤: {e}")
        return {'error': str(e)}

def classify_engagement_level(participation_rate):
    """分類參與度等級"""
    if participation_rate >= 75:
        return 'high'
    elif participation_rate >= 50:
        return 'medium'
    else:
        return 'low'

def analyze_activity_pattern(messages):
    """分析活動模式"""
    try:
        # 週間活動分析
        weekday_activity = defaultdict(int)
        hour_activity = defaultdict(int)
        
        for msg in messages:
            weekday_activity[msg.timestamp.strftime('%A')] += 1
            hour_activity[msg.timestamp.hour] += 1
        
        # 找出最活躍的時段
        most_active_weekday = max(weekday_activity.items(), key=lambda x: x[1]) if weekday_activity else ('Unknown', 0)
        most_active_hour = max(hour_activity.items(), key=lambda x: x[1]) if hour_activity else (0, 0)
        
        return {
            'most_active_weekday': most_active_weekday[0],
            'most_active_hour': most_active_hour[0],
            'weekday_distribution': dict(weekday_activity),
            'hour_distribution': dict(hour_activity)
        }
        
    except Exception as e:
        logger.error(f"活動模式分析錯誤: {e}")
        return {}

def track_cognitive_development(analyses):
    """追蹤認知發展"""
    try:
        if len(analyses) < 3:
            return {'status': 'insufficient_data'}
        
        # 按時間排序分析
        sorted_analyses = sorted(analyses, key=lambda x: x.timestamp)
        
        cognitive_progression = []
        for analysis in sorted_analyses:
            try:
                data = json.loads(analysis.analysis_data)
                cognitive_progression.append({
                    'date': analysis.timestamp.isoformat(),
                    'cognitive_level': data.get('cognitive_level', 'Unknown'),
                    'difficulty': data.get('difficulty', 'Unknown')
                })
            except json.JSONDecodeError:
                continue
        
        # 分析進展趨勢
        development_analysis = {
            'total_analyses': len(cognitive_progression),
            'progression': cognitive_progression,
            'cognitive_distribution': Counter(item['cognitive_level'] for item in cognitive_progression),
            'difficulty_progression': Counter(item['difficulty'] for item in cognitive_progression),
            'development_trend': assess_cognitive_trend(cognitive_progression)
        }
        
        return development_analysis
        
    except Exception as e:
        logger.error(f"認知發展追蹤錯誤: {e}")
        return {'error': str(e)}

def assess_cognitive_trend(progression):
    """評估認知發展趨勢"""
    try:
        if len(progression) < 3:
            return 'insufficient_data'
        
        # 簡單的趨勢分析：比較前1/3和後1/3的認知層次
        third = len(progression) // 3
        early_levels = [item['cognitive_level'] for item in progression[:third]]
        recent_levels = [item['cognitive_level'] for item in progression[-third:]]
        
        # 認知層次等級（簡化）
        level_scores = {
            'Remember': 1, 'Understand': 2, 'Apply': 3,
            'Analyze': 4, 'Evaluate': 5, 'Create': 6, 'Unknown': 0
        }
        
        early_avg = sum(level_scores.get(level, 0) for level in early_levels) / max(len(early_levels), 1)
        recent_avg = sum(level_scores.get(level, 0) for level in recent_levels) / max(len(recent_levels), 1)
        
        if recent_avg > early_avg * 1.2:
            return 'improving'
        elif recent_avg < early_avg * 0.8:
            return 'declining'
        else:
            return 'stable'
            
    except Exception as e:
        logger.error(f"認知趨勢評估錯誤: {e}")
        return 'unknown'

def identify_learning_style(messages, analyses):
    """識別學習風格"""
    try:
        if not messages and not analyses:
            return {'status': 'no_data'}
        
        style_indicators = {
            'question_asking_frequency': 0,
            'statement_making_frequency': 0,
            'preferred_question_types': [],
            'interaction_pattern': '',
            'learning_pace': ''
        }
        
        # 分析提問與陳述比例
        questions = [msg for msg in messages if msg.message_type == 'question']
        statements = [msg for msg in messages if msg.message_type == 'statement']
        
        style_indicators['question_asking_frequency'] = len(questions) / max(len(messages), 1)
        style_indicators['statement_making_frequency'] = len(statements) / max(len(messages), 1)
        
        # 分析偏好的問題類型
        if analyses:
            question_types = []
            for analysis in analyses:
                try:
                    data = json.loads(analysis.analysis_data)
                    question_types.append(data.get('question_type', 'Unknown'))
                except json.JSONDecodeError:
                    continue
            
            style_indicators['preferred_question_types'] = Counter(question_types).most_common(3)
        
        # 識別學習風格類型
        learning_style = classify_learning_style(style_indicators)
        
        return {
            'style_indicators': style_indicators,
            'identified_style': learning_style,
            'confidence': calculate_style_confidence(style_indicators)
        }
        
    except Exception as e:
        logger.error(f"學習風格識別錯誤: {e}")
        return {'error': str(e)}

def classify_learning_style(indicators):
    """分類學習風格"""
    try:
        question_freq = indicators['question_asking_frequency']
        preferred_types = [item[0] for item in indicators['preferred_question_types']]
        
        # 基於問題頻率和類型的簡單分類
        if question_freq > 0.4:
            if 'Definition' in preferred_types:
                return {
                    'type': 'inquisitive_learner',
                    'description': '好奇探究型：積極提問，喜歡深入了解概念定義'
                }
            elif 'Example' in preferred_types:
                return {
                    'type': 'example_oriented',
                    'description': '實例導向型：通過具體例子來理解抽象概念'
                }
            else:
                return {
                    'type': 'active_questioner',
                    'description': '主動提問型：經常提問，積極參與討論'
                }
        elif question_freq > 0.2:
            return {
                'type': 'moderate_participant',
                'description': '適度參與型：有選擇性地參與討論'
            }
        else:
            return {
                'type': 'observer_learner',
                'description': '觀察學習型：傾向於聽取和觀察，較少主動提問'
            }
            
    except Exception as e:
        logger.error(f"學習風格分類錯誤: {e}")
        return {'type': 'unknown', 'description': '學習風格分析中'}

def calculate_style_confidence(indicators):
    """計算風格識別信心度"""
    try:
        # 基於資料量和一致性計算信心度
        total_interactions = len(indicators.get('preferred_question_types', []))
        
        if total_interactions >= 10:
            return 'high'
        elif total_interactions >= 5:
            return 'medium'
        else:
            return 'low'
            
    except Exception as e:
        return 'unknown'

def generate_personalized_recommendations(student_id):
    """生成個人化學習建議"""
    try:
        if not model:
            return {'error': 'AI model not available'}
        
        # 建立學生檔案
        profile = build_comprehensive_student_profile(student_id)
        
        if 'error' in profile:
            return profile
        
        # 生成 AI 建議
        recommendations_prompt = f"""Based on this comprehensive student profile, provide personalized learning recommendations for EMI instruction:

Student Profile Summary:
{json.dumps(profile, indent=2)}

Generate specific, actionable recommendations in these categories:

1. **Immediate Focus Areas**: What needs attention right now?
2. **Skill Development**: What abilities should be developed next?
3. **Challenge Level**: What difficulty level is appropriate?
4. **Learning Resources**: What types of materials would help?
5. **Teacher Actions**: Specific strategies for the instructor?

Format as structured recommendations suitable for EMI educators:"""

        response = model.generate_content(recommendations_prompt)
        
        if response and response.text:
            # 解析建議內容
            parsed_recommendations = parse_recommendations(response.text)
            
            return {
                'success': True,
                'student_name': profile['student_info']['name'],
                'recommendations': parsed_recommendations,
                'raw_recommendations': response.text,
                'challenge_level': determine_challenge_level(profile),
                'analysis_based_on': profile['question_patterns'].get('total_questions', 0),
                'generated_at': datetime.datetime.now().isoformat()
            }
        else:
            return {'error': 'Failed to generate recommendations'}
            
    except Exception as e:
        logger.error(f"個人化建議生成錯誤: {e}")
        return {'error': str(e)}

def parse_recommendations(recommendations_text):
    """解析建議文本"""
    try:
        # 簡化的建議解析
        recommendations = {
            'immediate_focus': [],
            'skill_development': [],
            'learning_resources': [],
            'teacher_notes': []
        }
        
        # 將整個建議文本作為教師筆記
        recommendations['teacher_notes'] = [recommendations_text]
        
        # 基於內容生成結構化建議
        if 'participation' in recommendations_text.lower():
            recommendations['immediate_focus'].append({
                'area': 'Participation',
                'suggestion': 'Encourage more active engagement in discussions',
                'action': 'Set specific participation goals'
            })
        
        if 'question' in recommendations_text.lower():
            recommendations['skill_development'].append({
                'area': 'Questioning Skills',
                'suggestion': 'Develop higher-order thinking questions',
                'action': 'Practice analytical and evaluative questions'
            })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"建議解析錯誤: {e}")
        return {'teacher_notes': [recommendations_text]}

def determine_challenge_level(profile):
    """確定適合的挑戰程度"""
    try:
        cognitive_dev = profile.get('cognitive_development', {})
        
        participation_rate = profile['student_info']['participation_rate']
        
        if participation_rate >= 75 and cognitive_dev.get('development_trend') == 'improving':
            return 'Ready for advanced challenges'
        elif participation_rate >= 50:
            return 'Suitable for moderate complexity tasks'
        else:
            return 'Focus on foundational engagement'
            
    except Exception as e:
        return 'Assessment in progress'

# =========================================
# 3. 班級整體分析功能
# =========================================

def analyze_class_engagement():
    """分析班級整體參與度"""
    try:
        students = list(Student.select().where(~Student.name.startswith('[DEMO]')))
        
        if not students:
            return {'status': 'no_students'}
        
        # 參與度分級統計
        engagement_levels = {
            'high': len([s for s in students if s.participation_rate >= 75]),
            'medium': len([s for s in students if 50 <= s.participation_rate < 75]),
            'low': len([s for s in students if s.participation_rate < 50])
        }
        
        # 平均統計
        avg_participation = sum(s.participation_rate for s in students) / len(students)
        avg_questions = sum(s.question_count for s in students) / len(students)
        avg_messages = sum(s.message_count for s in students) / len(students)
        
        # 趨勢分析（簡化版本）
        recent_activity = analyze_recent_class_activity()
        
        return {
            'total_students': len(students),
            'engagement_levels': engagement_levels,
            'avg_participation': round(avg_participation, 1),
            'avg_questions': round(avg_questions, 1),
            'avg_messages': round(avg_messages, 1),
            'trend': recent_activity.get('trend', 'stable'),
            'class_performance': classify_class_performance(avg_participation)
        }
        
    except Exception as e:
        logger.error(f"班級參與度分析錯誤: {e}")
        return {'error': str(e)}

def analyze_recent_class_activity():
    """分析最近班級活動趨勢"""
    try:
        # 最近一週 vs 前一週的活動比較
        now = datetime.datetime.now()
        recent_week = now - datetime.timedelta(days=7)
        previous_week = now - datetime.timedelta(days=14)
        
        recent_messages = Message.select().where(Message.timestamp > recent_week).count()
        previous_messages = Message.select().where(
            Message.timestamp.between(previous_week, recent_week)
        ).count()
        
        if previous_messages > 0:
            change_ratio = recent_messages / previous_messages
            if change_ratio > 1.1:
                trend = 'increasing'
            elif change_ratio < 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'recent_messages': recent_messages,
            'previous_messages': previous_messages,
            'trend': trend,
            'change_ratio': round(change_ratio if previous_messages > 0 else 0, 2)
        }
        
    except Exception as e:
        logger.error(f"近期活動趨勢分析錯誤: {e}")
        return {'trend': 'unknown'}

def classify_class_performance(avg_participation):
    """分類班級整體表現"""
    if avg_participation >= 75:
        return 'excellent'
    elif avg_participation >= 60:
        return 'good'
    elif avg_participation >= 45:
        return 'satisfactory'
    else:
        return 'needs_attention'

def analyze_cognitive_development_trends():
    """分析班級認知發展趨勢"""
    try:
        # 取得所有問題分類分析
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ).order_by(Analysis.timestamp.asc()))
        
        if len(analyses) < 10:
            return {'status': 'insufficient_data'}
        
        # 按月分組分析認知層次分布
        monthly_cognitive = defaultdict(lambda: Counter())
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                month_key = analysis.timestamp.strftime('%Y-%m')
                cognitive_level = data.get('cognitive_level', 'Unknown')
                monthly_cognitive[month_key][cognitive_level] += 1
            except json.JSONDecodeError:
                continue
        
        # 計算趨勢
        trends = {
            'monthly_distribution': dict(monthly_cognitive),
            'overall_distribution': Counter(),
            'development_direction': 'analyzing'
        }
        
        # 計算整體分布
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                trends['overall_distribution'][data.get('cognitive_level', 'Unknown')] += 1
            except json.JSONDecodeError:
                continue
        
        trends['overall_distribution'] = dict(trends['overall_distribution'])
        
        return trends
        
    except Exception as e:
        logger.error(f"認知發展趨勢分析錯誤: {e}")
        return {'error': str(e)}

def analyze_learning_difficulties():
    """分析學習困難點"""
    try:
        # 分析低參與度學生
        struggling_students = list(Student.select().where(
            (Student.participation_rate < 50) & 
            (~Student.name.startswith('[DEMO]'))
        ))
        
        # 分析常見問題類型中的困難模式
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ))
        
        difficulty_patterns = {
            'struggling_students_count': len(struggling_students),
            'common_difficulty_areas': Counter(),
            'question_complexity_issues': Counter()
        }
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                if data.get('difficulty') == 'Hard':
                    difficulty_patterns['common_difficulty_areas'][data.get('content_domain', 'Unknown')] += 1
                
                if data.get('language_complexity') == 'Advanced':
                    difficulty_patterns['question_complexity_issues'][data.get('question_type', 'Unknown')] += 1
                    
            except json.JSONDecodeError:
                continue
        
        # 轉換為字典
        difficulty_patterns['common_difficulty_areas'] = dict(difficulty_patterns['common_difficulty_areas'])
        difficulty_patterns['question_complexity_issues'] = dict(difficulty_patterns['question_complexity_issues'])
        
        return difficulty_patterns
        
    except Exception as e:
        logger.error(f"學習困難點分析錯誤: {e}")
        return {'error': str(e)}

def generate_class_teaching_recommendations():
    """生成班級教學建議"""
    try:
        if not model:
            return [{'title': 'AI 服務不可用', 'description': '無法生成智能建議'}]
        
        # 收集班級整體分析資料
        engagement_analysis = analyze_class_engagement()
        cognitive_trends = analyze_cognitive_development_trends()
        difficulty_analysis = analyze_learning_difficulties()
        
        # 生成班級建議
        class_prompt = f"""Based on this EMI class analysis, provide teaching recommendations:

Class Engagement Analysis:
{json.dumps(engagement_analysis, indent=2)}

Cognitive Development Trends:
{json.dumps(cognitive_trends, indent=2)}

Learning Difficulties Analysis:
{json.dumps(difficulty_analysis, indent=2)}

Provide 3-5 specific, actionable teaching recommendations for this EMI class:"""

        response = model.generate_content(class_prompt)
        
        if response and response.text:
            # 解析為建議列表
            recommendations = parse_class_recommendations(response.text)
            return recommendations
        else:
            return [{'title': '建議生成中', 'description': '系統正在分析班級狀況...'}]
            
    except Exception as e:
        logger.error(f"班級教學建議生成錯誤: {e}")
        return [{'title': '分析錯誤', 'description': f'建議生成過程發生錯誤: {str(e)[:50]}'}]

def parse_class_recommendations(recommendations_text):
    """解析班級建議文本"""
    try:
        # 簡單的文本解析為建議列表
        lines = recommendations_text.split('\n')
        recommendations = []
        
        current_title = ""
        current_desc = ""
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('**') or line.startswith('#') or line.endswith(':')):
                # 如果有前一個建議，先加入列表
                if current_title:
                    recommendations.append({
                        'title': current_title,
                        'description': current_desc.strip()
                    })
                
                # 開始新建議
                current_title = line.replace('**', '').replace('#', '').replace(':', '').strip()
                current_desc = ""
            elif line and current_title:
                current_desc += line + " "
        
        # 加入最後一個建議
        if current_title:
            recommendations.append({
                'title': current_title,
                'description': current_desc.strip()
            })
        
        # 如果解析失敗，返回整個文本作為單一建議
        if not recommendations:
            recommendations = [{
                'title': '班級教學建議',
                'description': recommendations_text[:200] + "..." if len(recommendations_text) > 200 else recommendations_text
            }]
        
        return recommendations[:5]  # 最多返回5個建議
        
    except Exception as e:
        logger.error(f"班級建議解析錯誤: {e}")
        return [{'title': '建議解析中', 'description': '正在處理教學建議...'}]

# =========================================
# 輔助函數
# =========================================

def get_question_category_distribution():
    """取得問題分類分布"""
    try:
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ))
        
        categories = {}
        cognitive_levels = {}
        question_types = {}
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                
                # 內容領域
                domain = data.get('content_domain', 'Unknown')
                categories[domain] = categories.get(domain, 0) + 1
                
                # 認知層次
                cognitive = data.get('cognitive_level', 'Unknown')
                cognitive_levels[cognitive] = cognitive_levels.get(cognitive, 0) + 1
                
                # 問題類型
                q_type = data.get('question_type', 'Unknown')
                question_types[q_type] = question_types.get(q_type, 0) + 1
                
            except json.JSONDecodeError:
                continue
        
        return {
            'content_domains': categories,
            'cognitive_levels': cognitive_levels,
            'question_types': question_types
        }
        
    except Exception as e:
        return {'error': str(e)}

def get_cognitive_level_distribution():
    """取得認知層次分布"""
    try:
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ))
        
        distribution = Counter()
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                cognitive_level = data.get('cognitive_level', 'Unknown')
                distribution[cognitive_level] += 1
            except json.JSONDecodeError:
                continue
        
        return dict(distribution)
        
    except Exception as e:
        return {'error': str(e)}

def get_engagement_timeline():
    """取得參與度時間線"""
    try:
        # 按週統計參與度
        messages = list(Message.select().order_by(Message.timestamp.asc()))
        
        if not messages:
            return {'status': 'no_data'}
        
        # 按週分組
        weekly_engagement = defaultdict(int)
        
        for message in messages:
            week_key = message.timestamp.strftime('%Y-W%U')
            weekly_engagement[week_key] += 1
        
        return {
            'weekly_data': dict(weekly_engagement),
            'total_weeks': len(weekly_engagement)
        }
        
    except Exception as e:
        return {'error': str(e)}

def get_difficulty_heatmap():
    """取得困難度熱力圖資料"""
    try:
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ))
        
        heatmap_data = defaultdict(lambda: defaultdict(int))
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                content_domain = data.get('content_domain', 'Unknown')
                difficulty = data.get('difficulty', 'Unknown')
                heatmap_data[content_domain][difficulty] += 1
            except json.JSONDecodeError:
                continue
        
        # 轉換為適合前端的格式
        formatted_data = []
        for domain, difficulties in heatmap_data.items():
            for difficulty, count in difficulties.items():
                formatted_data.append({
                    'domain': domain,
                    'difficulty': difficulty,
                    'count': count
                })
        
        return formatted_data
        
    except Exception as e:
        return {'error': str(e)}

def get_class_learning_progress():
    """取得班級學習進度"""
    try:
        students = list(Student.select().where(~Student.name.startswith('[DEMO]')))
        
        progress_data = []
        
        for student in students:
            analyses = list(Analysis.select().where(
                (Analysis.student_id == student.id) &
                (Analysis.analysis_type == 'question_classification')
            ).order_by(Analysis.timestamp.asc()))
            
            if analyses:
                # 計算認知層次進展
                cognitive_progression = []
                for analysis in analyses:
                    try:
                        data = json.loads(analysis.analysis_data)
                        cognitive_level = data.get('cognitive_level', 'Unknown')
                        cognitive_progression.append(cognitive_level)
                    except json.JSONDecodeError:
                        continue
                
                progress_data.append({
                    'student_name': student.name,
                    'participation_rate': student.participation_rate,
                    'cognitive_progression': cognitive_progression,
                    'total_analyses': len(analyses)
                })
        
        return progress_data
        
    except Exception as e:
        return {'error': str(e)}
