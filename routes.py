import os
import json
import datetime
import csv
import zipfile
from io import StringIO, BytesIO
from flask import render_template, jsonify, request, send_file, redirect, url_for, flash
from models import Student, Message, Analysis, db
from utils import (
    get_ai_response, analyze_student_patterns, get_question_category_stats,
    get_student_conversation_summary, get_system_status
)
import google.generativeai as genai

# 初始化 Gemini (如果需要)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
    except:
        model = None
else:
    model = None

def create_routes(app):
    """建立所有路由"""

    # =========================================
    # 主要頁面路由
    # =========================================

    @app.route('/')
    def index():
        """首頁 - 系統概覽"""
        try:
            # 基本統計
            total_students = Student.select().count()
            real_students = Student.select().where(~Student.name.startswith('[DEMO]')).count()
            total_messages = Message.select().count()
            total_questions = Message.select().where(Message.message_type == 'question').count()
            
            # 最近活動
            recent_messages = list(Message.select().order_by(Message.timestamp.desc()).limit(5))
            
            # 參與度統計
            if real_students > 0:
                avg_participation = Student.select().where(
                    ~Student.name.startswith('[DEMO]')
                ).scalar(
                    fn.AVG(Student.participation_rate)
                ) or 0
            else:
                avg_participation = 0
            
            stats = {
                'total_students': total_students,
                'real_students': real_students,
                'total_messages': total_messages,
                'total_questions': total_questions,
                'avg_participation': round(avg_participation, 1),
                'question_rate': round((total_questions / max(total_messages, 1)) * 100, 1)
            }
            
            return render_template('index.html', 
                                 stats=stats, 
                                 recent_messages=recent_messages)
                                 
        except Exception as e:
            app.logger.error(f"首頁錯誤: {e}")
            return render_template('index.html', 
                                 stats={}, 
                                 recent_messages=[])

    # =========================================
    # 教師分析後台 - 視覺化統計
    # =========================================

    @app.route('/teaching-insights')
    def teaching_insights():
        """教師分析後台主頁"""
        try:
            # 問題分類統計
            category_stats = get_question_category_stats()
            
            # 學生參與度分析
            engagement_analysis = analyze_class_engagement()
            
            # 認知發展趨勢
            cognitive_trends = analyze_cognitive_development_trends()
            
            # 學習困難點分析
            difficulty_analysis = analyze_learning_difficulties()
            
            # 教學建議
            teaching_recommendations = generate_class_teaching_recommendations()
            
            return render_template('teaching_insights.html',
                                 category_stats=category_stats,
                                 engagement_analysis=engagement_analysis,
                                 cognitive_trends=cognitive_trends,
                                 difficulty_analysis=difficulty_analysis,
                                 recommendations=teaching_recommendations)
                                 
        except Exception as e:
            app.logger.error(f"教學洞察頁面錯誤: {e}")
            return render_template('teaching_insights.html',
                                 category_stats={},
                                 engagement_analysis={},
                                 cognitive_trends={},
                                 difficulty_analysis={},
                                 recommendations=[])

    @app.route('/api/visualization-data/<data_type>')
    def get_visualization_data(data_type):
        """取得視覺化資料 API"""
        try:
            if data_type == 'question_categories':
                return jsonify(get_question_category_distribution())
            elif data_type == 'cognitive_levels':
                return jsonify(get_cognitive_level_distribution())
            elif data_type == 'engagement_timeline':
                return jsonify(get_engagement_timeline())
            elif data_type == 'difficulty_heatmap':
                return jsonify(get_difficulty_heatmap())
            elif data_type == 'learning_progress':
                return jsonify(get_class_learning_progress())
            else:
                return jsonify({'error': 'Unknown data type'}), 400
                
        except Exception as e:
            app.logger.error(f"視覺化資料錯誤: {e}")
            return jsonify({'error': str(e)}), 500

    # =========================================
    # 智能對話摘要
    # =========================================

    @app.route('/conversation-summaries')
    def conversation_summaries():
        """對話摘要總覽頁面"""
        try:
            # 取得所有學生的對話摘要
            students = list(Student.select().where(~Student.name.startswith('[DEMO]')))
            
            summaries = []
            for student in students:
                summary = generate_conversation_summary(student.id)
                if summary:
                    summaries.append({
                        'student': student,
                        'summary': summary
                    })
            
            return render_template('conversation_summaries.html', summaries=summaries)
            
        except Exception as e:
            app.logger.error(f"對話摘要頁面錯誤: {e}")
            return render_template('conversation_summaries.html', summaries=[])

    @app.route('/api/conversation-summary/<int:student_id>')
    def get_conversation_summary_api(student_id):
        """取得特定學生的對話摘要 API"""
        try:
            summary = generate_conversation_summary(student_id)
            return jsonify(summary)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/generate-teaching-summary/<int:student_id>')
    def generate_teaching_summary_api(student_id):
        """生成教學重點摘要"""
        try:
            teaching_summary = generate_teaching_focused_summary(student_id)
            return jsonify(teaching_summary)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # =========================================
    # 個人化學習建議
    # =========================================

    @app.route('/learning-recommendations')
    def learning_recommendations():
        """學習建議總覽頁面"""
        try:
            students = list(Student.select().where(~Student.name.startswith('[DEMO]')))
            
            recommendations = []
            for student in students:
                recommendation = generate_personalized_recommendations(student.id)
                if recommendation:
                    recommendations.append({
                        'student': student,
                        'recommendation': recommendation
                    })
            
            return render_template('learning_recommendations.html', 
                                 recommendations=recommendations)
                                 
        except Exception as e:
            app.logger.error(f"學習建議頁面錯誤: {e}")
            return render_template('learning_recommendations.html', 
                                 recommendations=[])

    @app.route('/api/student-profile/<int:student_id>')
    def get_student_profile_api(student_id):
        """取得學生詳細檔案 API"""
        try:
            profile = build_comprehensive_student_profile(student_id)
            return jsonify(profile)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/learning-recommendations/<int:student_id>')
    def get_learning_recommendations_api(student_id):
        """取得個人化學習建議 API"""
        try:
            recommendations = generate_personalized_recommendations(student_id)
            return jsonify(recommendations)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # =========================================
    # 儲存監控功能
    # =========================================

    @app.route('/storage-management')
    def storage_management():
        """儲存空間管理頁面"""
        try:
            storage_info = monitor_storage_usage()
            cleanup_history = get_cleanup_history()
            
            return render_template('storage_management.html',
                                 storage_info=storage_info,
                                 cleanup_history=cleanup_history)
                                 
        except Exception as e:
            app.logger.error(f"儲存管理頁面錯誤: {e}")
            return render_template('storage_management.html',
                                 storage_info={},
                                 cleanup_history=[])

    @app.route('/api/storage-status')
    def storage_status_api():
        """儲存狀態 API"""
        try:
            return jsonify(monitor_storage_usage())
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cleanup/<cleanup_level>')
    def cleanup_data_api(cleanup_level):
        """資料清理 API"""
        try:
            if cleanup_level not in ['conservative', 'moderate', 'aggressive']:
                return jsonify({'error': 'Invalid cleanup level'}), 400
                
            result = perform_smart_cleanup(cleanup_level)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # =========================================
    # 基本匯出功能
    # =========================================

    @app.route('/data-export')
    def data_export():
        """資料匯出頁面"""
        try:
            export_options = {
                'comprehensive': {
                    'name': '完整教學研究資料',
                    'description': '包含所有學生資料、分析結果和洞察報告',
                    'formats': ['CSV', 'JSON', 'Excel']
                },
                'academic_paper': {
                    'name': '學術論文資料',
                    'description': '匿名化的統計資料，適合學術發表',
                    'formats': ['CSV', 'Excel', 'PDF']
                },
                'progress_report': {
                    'name': '學生進度報告',
                    'description': '個別學生的學習進度和建議',
                    'formats': ['PDF', 'Excel']
                },
                'analytics_summary': {
                    'name': '分析摘要報告',
                    'description': '班級整體分析和教學建議',
                    'formats': ['PDF', 'PowerPoint']
                }
            }
            
            recent_exports = get_recent_exports()
            
            return render_template('data_export.html',
                                 export_options=export_options,
                                 recent_exports=recent_exports)
                                 
        except Exception as e:
            app.logger.error(f"資料匯出頁面錯誤: {e}")
            return render_template('data_export.html',
                                 export_options={},
                                 recent_exports=[])

    @app.route('/api/export/<export_type>')
    def export_data_api(export_type):
        """資料匯出 API"""
        try:
            export_format = request.args.get('format', 'json')
            date_range = request.args.get('date_range', None)
            
            result = perform_data_export(export_type, export_format, date_range)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'download_url': f"/download/{result['filename']}",
                    'filename': result['filename'],
                    'size': result['size']
                })
            else:
                return jsonify({'error': result['error']}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/download/<filename>')
    def download_file(filename):
        """檔案下載"""
        try:
            # 安全檢查檔案路徑
            if not os.path.exists(filename) or '..' in filename:
                return "File not found", 404
                
            return send_file(filename, as_attachment=True)
            
        except Exception as e:
            app.logger.error(f"檔案下載錯誤: {e}")
            return "Download failed", 500

    # =========================================
    # 原有路由保持不變
    # =========================================

    @app.route('/students')
    def students():
        """學生列表頁面"""
        try:
            students = list(Student.select().order_by(Student.last_active.desc()))
            return render_template('students.html', students=students)
        except Exception as e:
            app.logger.error(f"學生列表錯誤: {e}")
            return render_template('students.html', students=[])

    @app.route('/student/<int:student_id>')
    def student_detail(student_id):
        """學生詳細頁面"""
        try:
            student = Student.get_by_id(student_id)
            
            # 取得學生訊息
            messages = list(Message.select().where(
                Message.student == student
            ).order_by(Message.timestamp.desc()).limit(20))
            
            # 學習分析
            analysis = analyze_student_patterns(student_id)
            
            # 對話摘要
            conversation_summary = get_student_conversation_summary(student_id, days=30)
            
            return render_template('student_detail.html', 
                                 student=student,
                                 messages=messages,
                                 analysis=analysis,
                                 conversation_summary=conversation_summary)
                                 
        except Student.DoesNotExist:
            return "Student not found", 404
        except Exception as e:
            app.logger.error(f"學生詳細頁面錯誤: {e}")
            return "Error loading student details", 500

    @app.route('/health')
    def health_check():
        """健康檢查"""
        try:
            status = get_system_status()
            return jsonify(status)
        except Exception as e:
            return jsonify({'error': str(e), 'status': 'unhealthy'}), 500

    return app

# =========================================
# 分析函數實作
# =========================================

def analyze_class_engagement():
    """分析班級參與度"""
    try:
        students = list(Student.select().where(~Student.name.startswith('[DEMO]')))
        
        if not students:
            return {'status': 'no_data'}
        
        engagement_levels = {
            'high': len([s for s in students if s.participation_rate >= 75]),
            'medium': len([s for s in students if 50 <= s.participation_rate < 75]),
            'low': len([s for s in students if s.participation_rate < 50])
        }
        
        avg_participation = sum(s.participation_rate for s in students) / len(students)
        avg_questions = sum(s.question_count for s in students) / len(students)
        
        # 參與度趨勢（簡化版本）
        recent_messages = Message.select().where(
            Message.timestamp > datetime.datetime.now() - datetime.timedelta(days=7)
        ).count()
        
        previous_messages = Message.select().where(
            Message.timestamp.between(
                datetime.datetime.now() - datetime.timedelta(days=14),
                datetime.datetime.now() - datetime.timedelta(days=7)
            )
        ).count()
        
        trend = 'increasing' if recent_messages > previous_messages else 'decreasing'
        
        return {
            'engagement_levels': engagement_levels,
            'avg_participation': round(avg_participation, 1),
            'avg_questions': round(avg_questions, 1),
            'trend': trend,
            'total_students': len(students)
        }
        
    except Exception as e:
        return {'error': str(e)}

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

def generate_conversation_summary(student_id):
    """生成對話摘要"""
    try:
        if not model:
            return {'error': 'AI model not available'}
            
        # 取得學生最近的對話
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()).limit(15))
        
        if len(messages) < 3:
            return {'status': 'insufficient_data'}
        
        # 建構對話內容
        conversation_text = []
        for msg in reversed(messages):  # 按時間順序
            conversation_text.append(f"Student: {msg.content}")
        
        prompt = f"""As an educational expert, create a teaching-focused summary of this student conversation:

Conversation:
{chr(10).join(conversation_text)}

Create a summary that includes:
1. **Key Topics Discussed**: Main subjects covered
2. **Student Understanding Level**: What they grasp vs. areas of confusion  
3. **Learning Progression**: How their understanding developed
4. **Teaching Recommendations**: Specific suggestions for continued learning

Format as a structured summary (max 200 words):"""

        response = model.generate_content(prompt)
        
        if response and response.text:
            return {
                'success': True,
                'summary': response.text.strip(),
                'message_count': len(messages),
                'generated_at': datetime.datetime.now().isoformat()
            }
        else:
            return {'error': 'Failed to generate summary'}
            
    except Exception as e:
        return {'error': str(e)}

def generate_personalized_recommendations(student_id):
    """生成個人化學習建議"""
    try:
        student = Student.get_by_id(student_id)
        
        # 分析學生學習模式
        question_analyses = list(Analysis.select().where(
            (Analysis.student_id == student_id) &
            (Analysis.analysis_type == 'question_classification')
        ))
        
        if len(question_analyses) < 3:
            return {'status': 'insufficient_data'}
        
        # 分析問題模式
        cognitive_levels = {}
        content_domains = {}
        difficulties = {}
        
        for analysis in question_analyses:
            try:
                data = json.loads(analysis.analysis_data)
                
                cognitive = data.get('cognitive_level', 'Unknown')
                cognitive_levels[cognitive] = cognitive_levels.get(cognitive, 0) + 1
                
                domain = data.get('content_domain', 'Unknown')
                content_domains[domain] = content_domains.get(domain, 0) + 1
                
                difficulty = data.get('difficulty', 'Unknown')
                difficulties[difficulty] = difficulties.get(difficulty, 0) + 1
                
            except json.JSONDecodeError:
                continue
        
        # 生成建議
        recommendations = {
            'immediate_focus': [],
            'skill_development': [],
            'challenge_level': '',
            'learning_resources': [],
            'teacher_notes': []
        }
        
        # 基於參與度的建議
        if student.participation_rate < 50:
            recommendations['immediate_focus'].append({
                'area': 'Engagement',
                'suggestion': 'Encourage more active participation',
                'action': 'Set daily interaction goals (2-3 questions per class)'
            })
        
        # 基於認知層次的建議
        most_common_cognitive = max(cognitive_levels, key=cognitive_levels.get) if cognitive_levels else 'Unknown'
        
        if most_common_cognitive == 'Remember':
            recommendations['challenge_level'] = 'Ready to move beyond memorization'
            recommendations['skill_development'].append({
                'area': 'Application Skills',
                'suggestion': 'Introduce practical examples and case studies',
                'action': 'Ask "How would you apply this concept?"'
            })
        elif most_common_cognitive == 'Understand':
            recommendations['challenge_level'] = 'Ready for analytical thinking'
            recommendations['skill_development'].append({
                'area': 'Analysis Skills', 
                'suggestion': 'Encourage comparison and evaluation questions',
                'action': 'Ask "What\'s the difference between X and Y?"'
            })
        
        # 基於內容領域的建議
        if content_domains:
            primary_domain = max(content_domains, key=content_domains.get)
            recommendations['teacher_notes'].append(
                f"Student shows primary interest in {primary_domain}"
            )
        
        return {
            'success': True,
            'student_name': student.name,
            'recommendations': recommendations,
            'analysis_based_on': len(question_analyses),
            'generated_at': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        return {'error': str(e)}

def monitor_storage_usage():
    """監控儲存使用量"""
    try:
        # 計算各表的記錄數
        student_count = Student.select().count()
        message_count = Message.select().count()
        analysis_count = Analysis.select().count()
        
        # 估算儲存大小 (粗略估算)
        estimated_size_mb = (
            student_count * 0.001 +  # 每個學生約1KB
            message_count * 0.005 +  # 每則訊息約5KB
            analysis_count * 0.002   # 每個分析約2KB
        )
        
        # Railway 免費額度
        free_limit_mb = 512
        usage_percentage = (estimated_size_mb / free_limit_mb) * 100
        
        # 分類建議
        if usage_percentage < 50:
            recommendation = {
                'level': 'safe',
                'message': '儲存空間充足',
                'action': 'continue_monitoring'
            }
        elif usage_percentage < 75:
            recommendation = {
                'level': 'caution', 
                'message': '建議清除演示資料',
                'action': 'conservative_cleanup'
            }
        elif usage_percentage < 90:
            recommendation = {
                'level': 'warning',
                'message': '建議進行資料清理',
                'action': 'moderate_cleanup'
            }
        else:
            recommendation = {
                'level': 'critical',
                'message': '急需清理或匯出資料',
                'action': 'export_and_cleanup'
            }
        
        return {
            'total_size_mb': round(estimated_size_mb, 2),
            'free_limit_mb': free_limit_mb,
            'usage_percentage': round(usage_percentage, 1),
            'remaining_mb': round(free_limit_mb - estimated_size_mb, 2),
            'record_counts': {
                'students': student_count,
                'messages': message_count,
                'analyses': analysis_count
            },
            'recommendation': recommendation,
            'last_check': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        return {'error': str(e)}

def perform_data_export(export_type, export_format='json', date_range=None):
    """執行資料匯出"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if export_type == 'comprehensive':
            return export_comprehensive_data(timestamp, export_format)
        elif export_type == 'academic_paper':
            return export_academic_data(timestamp, export_format)
        elif export_type == 'progress_report':
            return export_progress_data(timestamp, export_format)
        elif export_type == 'analytics_summary':
            return export_analytics_summary(timestamp, export_format)
        else:
            return {'success': False, 'error': 'Unknown export type'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def export_comprehensive_data(timestamp, format_type):
    """匯出完整資料"""
    try:
        filename = f'comprehensive_data_{timestamp}'
        
        # 準備資料
        students_data = []
        for student in Student.select():
            students_data.append({
                'id': student.id,
                'name': student.name,
                'participation_rate': student.participation_rate,
                'question_count': student.question_count,
                'message_count': student.message_count,
                'created_at': student.created_at.isoformat() if student.created_at else '',
                'last_active': student.last_active.isoformat() if student.last_active else ''
            })
        
        if format_type == 'json':
            filename += '.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_info': {
                        'type': 'comprehensive',
                        'timestamp': timestamp,
                        'record_count': len(students_data)
                    },
                    'students': students_data
                }, f, ensure_ascii=False, indent=2)
        
        elif format_type == 'csv':
            filename += '.csv'
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if students_data:
                    writer = csv.DictWriter(f, fieldnames=students_data[0].keys())
                    writer.writeheader()
                    writer.writerows(students_data)
        
        # 取得檔案大小
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return {
            'success': True,
            'filename': filename,
            'size': file_size,
            'record_count': len(students_data)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# 繼續實作其他匯出函數...
def export_academic_data(timestamp, format_type):
    """匯出學術研究資料（匿名化）"""
    # 實作匿名化的學術資料匯出
    pass

def export_progress_data(timestamp, format_type):
    """匯出學生進度資料"""
    # 實作學生進度報告匯出
    pass

def export_analytics_summary(timestamp, format_type):
    """匯出分析摘要"""
    # 實作分析摘要匯出
    pass
