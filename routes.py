import csv
import datetime
from io import StringIO
from flask import render_template_string, redirect, url_for, jsonify, Response, request
from models import Student, Message, Analysis, AIResponse, LearningSession, get_db_stats
from templates import (
    HOME_TEMPLATE, 
    STUDENTS_TEMPLATE, 
    STUDENT_DETAIL_TEMPLATE, 
    ANALYSIS_TEMPLATE, 
    INSIGHTS_TEMPLATE
)
import logging

logger = logging.getLogger(__name__)

def init_routes(app):
    """初始化所有路由"""
    
    @app.route('/')
    def home():
        """首頁 - 系統概覽"""
        try:
            # 取得統計資料
            stats = get_db_stats()
            
            # 計算今日活躍學生
            today = datetime.date.today()
            active_today = Student.select().where(
                Student.last_active >= today
            ).count()
            
            # 取得近期活動
            recent_activities = get_recent_activities()
            
            template_data = {
                'total_students': stats.get('students', 0),
                'total_messages': stats.get('messages', 0),
                'total_questions': stats.get('questions', 0),
                'active_today': active_today,
                'recent_activities': recent_activities
            }
            
            return render_template_string(HOME_TEMPLATE, **template_data)
            
        except Exception as e:
            logger.error(f"首頁載入錯誤: {e}")
            return render_template_string(
                '<h1>系統錯誤</h1><p>請稍後再試</p>'
            ), 500

    @app.route('/students')
    def students_list():
        """學生列表頁面"""
        try:
            students = Student.select().order_by(Student.last_active.desc())
            
            # 為每個學生準備顯示資料
            students_data = []
            for student in students:
                student_info = {
                    'id': student.id,
                    'name': student.name,
                    'message_count': student.message_count,
                    'question_count': student.question_count,
                    'participation_rate': round(student.participation_rate, 1),
                    'question_rate': round(student.question_rate, 1),
                    'last_active': student.last_active,
                    'is_active': student.is_active
                }
                students_data.append(student_info)
            
            return render_template_string(
                STUDENTS_TEMPLATE, 
                students=students_data
            )
            
        except Exception as e:
            logger.error(f"學生列表載入錯誤: {e}")
            return redirect(url_for('home'))

    @app.route('/student/<int:student_id>')
    def student_detail(student_id):
        """學生詳細分析頁面"""
        try:
            student = Student.get_by_id(student_id)
            
            # 取得近期提問
            recent_questions = Message.select().where(
                (Message.student == student) & 
                (Message.message_type == 'question')
            ).order_by(Message.timestamp.desc()).limit(10)
            
            # 取得最新的 AI 分析
            ai_analysis = Analysis.select().where(
                Analysis.student == student
            ).order_by(Analysis.created_at.desc()).first()
            
            # 取得學習會話資料
            recent_sessions = LearningSession.select().where(
                LearningSession.student == student
            ).order_by(LearningSession.start_time.desc()).limit(5)
            
            # 計算額外統計
            total_ai_interactions = AIResponse.select().where(
                AIResponse.student == student
            ).count()
            
            # 計算本週活動
            week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            weekly_messages = Message.select().where(
                (Message.student == student) & 
                (Message.timestamp >= week_ago)
            ).count()
            
            template_data = {
                'student': student,
                'recent_questions': recent_questions,
                'ai_analysis': ai_analysis,
                'recent_sessions': recent_sessions,
                'total_ai_interactions': total_ai_interactions,
                'weekly_messages': weekly_messages
            }
            
            return render_template_string(
                STUDENT_DETAIL_TEMPLATE, 
                **template_data
            )
            
        except Student.DoesNotExist:
            return redirect(url_for('students_list'))
        except Exception as e:
            logger.error(f"學生詳細頁面載入錯誤: {e}")
            return redirect(url_for('students_list'))

    @app.route('/analysis')
    def analysis_report():
        """分析報告頁面"""
        try:
            # 計算班級統計
            stats = calculate_class_statistics()
            
            # 取得趨勢資料
            trend_data = get_participation_trends()
            
            template_data = {
                'stats': stats,
                'trend_data': trend_data
            }
            
            return render_template_string(
                ANALYSIS_TEMPLATE, 
                **template_data
            )
            
        except Exception as e:
            logger.error(f"分析報告載入錯誤: {e}")
            return redirect(url_for('home'))

    @app.route('/insights')
    def ai_insights():
        """AI 洞察頁面"""
        try:
            # 取得所有 AI 分析洞察
            insights = Analysis.select().where(
                Analysis.is_active == True
            ).order_by(Analysis.created_at.desc()).limit(20)
            
            # 格式化洞察資料
            insights_data = []
            for insight in insights:
                insight_info = {
                    'id': insight.id,
                    'title': insight.title or f"{insight.student.name} 的學習分析",
                    'content': insight.content,
                    'analysis_type': get_analysis_type_display(insight.analysis_type),
                    'created_at': insight.created_at,
                    'student_name': insight.student.name,
                    'confidence_score': insight.confidence_score
                }
                insights_data.append(insight_info)
            
            return render_template_string(
                INSIGHTS_TEMPLATE, 
                insights=insights_data
            )
            
        except Exception as e:
            logger.error(f"AI 洞察頁面載入錯誤: {e}")
            return redirect(url_for('home'))

    @app.route('/export')
    def export_data():
        """資料匯出頁面"""
        try:
            export_format = request.args.get('format', 'csv')
            data_type = request.args.get('type', 'students')
            
            if export_format == 'csv':
                return export_csv(data_type)
            elif export_format == 'json':
                return export_json(data_type)
            else:
                return jsonify({'error': 'Unsupported format'}), 400
                
        except Exception as e:
            logger.error(f"資料匯出錯誤: {e}")
            return jsonify({'error': 'Export failed'}), 500

    @app.route('/api/student/<int:student_id>/stats')
    def api_student_stats(student_id):
        """API: 取得學生統計資料"""
        try:
            student = Student.get_by_id(student_id)
            
            # 計算詳細統計
            daily_stats = get_daily_message_stats(student)
            weekly_stats = get_weekly_participation(student)
            monthly_stats = get_monthly_trends(student)
            
            response_data = {
                'student_id': student.id,
                'name': student.name,
                'basic_stats': {
                    'total_messages': student.message_count,
                    'total_questions': student.question_count,
                    'participation_rate': student.participation_rate,
                    'question_rate': student.question_rate,
                    'active_days': student.active_days
                },
                'daily_stats': daily_stats,
                'weekly_stats': weekly_stats,
                'monthly_stats': monthly_stats,
                'last_updated': datetime.datetime.now().isoformat()
            }
            
            return jsonify(response_data)
            
        except Student.DoesNotExist:
            return jsonify({'error': 'Student not found'}), 404
        except Exception as e:
            logger.error(f"API 學生統計錯誤: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/class/overview')
    def api_class_overview():
        """API: 取得班級概覽資料"""
        try:
            overview_data = {
                'total_students': Student.select().count(),
                'active_students': Student.select().where(Student.is_active == True).count(),
                'total_messages': Message.select().count(),
                'total_questions': Message.select().where(Message.message_type == 'question').count(),
                'total_ai_responses': AIResponse.select().count(),
                'avg_participation': get_average_participation(),
                'top_participants': get_top_participants(),
                'recent_activity': get_recent_activity_summary(),
                'language_distribution': get_language_distribution(),
                'generated_at': datetime.datetime.now().isoformat()
            }
            
            return jsonify(overview_data)
            
        except Exception as e:
            logger.error(f"API 班級概覽錯誤: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/trends/participation')
    def api_participation_trends():
        """API: 取得參與度趨勢資料"""
        try:
            days = int(request.args.get('days', 30))
            trends = get_participation_trends(days)
            
            return jsonify({
                'period_days': days,
                'trends': trends,
                'generated_at': datetime.datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"API 參與度趨勢錯誤: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/dashboard')
    def dashboard():
        """儀表板頁面"""
        try:
            # 這裡可以整合更複雜的儀表板
            dashboard_data = {
                'class_stats': get_db_stats(),
                'recent_insights': get_recent_ai_insights(),
                'top_questions': get_most_common_questions(),
                'engagement_alerts': get_engagement_alerts()
            }
            
            # 使用簡化的儀表板模板
            dashboard_template = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>教學分析儀表板</title>
                <meta charset="utf-8">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .card { background: white; padding: 20px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
                    .stat-item { text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; }
                    .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
                    .nav-links { margin: 20px 0; }
                    .nav-links a { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎓 教學分析儀表板</h1>
                    
                    <div class="nav-links">
                        <a href="/">首頁</a>
                        <a href="/students">學生列表</a>
                        <a href="/analysis">分析報告</a>
                        <a href="/insights">AI 洞察</a>
                        <a href="/export?format=csv&type=students">匯出資料</a>
                    </div>
                    
                    <div class="card">
                        <h2>班級統計</h2>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-number">{{ class_stats.students }}</div>
                                <div>註冊學生</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{{ class_stats.messages }}</div>
                                <div>總訊息數</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{{ class_stats.questions }}</div>
                                <div>學生提問</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{{ class_stats.ai_responses }}</div>
                                <div>AI 回應</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>近期 AI 洞察</h2>
                        {% for insight in recent_insights %}
                        <div style="padding: 10px; border-left: 3px solid #007bff; margin: 10px 0; background: #f8f9fa;">
                            <strong>{{ insight.title }}</strong><br>
                            <small>{{ insight.created_at.strftime('%Y-%m-%d %H:%M') }}</small><br>
                            {{ insight.content[:200] }}...
                        </div>
                        {% endfor %}
                    </div>
                    
                    <div class="card">
                        <h2>參與度警報</h2>
                        {% for alert in engagement_alerts %}
                        <div style="padding: 10px; border-left: 3px solid #dc3545; margin: 10px 0; background: #fff5f5;">
                            <strong>{{ alert.type }}</strong>: {{ alert.message }}
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </body>
            </html>
            '''
            
            return render_template_string(dashboard_template, **dashboard_data)
            
        except Exception as e:
            logger.error(f"儀表板載入錯誤: {e}")
            return redirect(url_for('home'))

def get_recent_activities():
    """取得近期活動"""
    try:
        activities = []
        
        # 近期註冊學生
        recent_students = Student.select().order_by(Student.created_at.desc()).limit(3)
        for student in recent_students:
            activities.append({
                'text': f"新學生 {student.name} 加入系統",
                'time': student.created_at.strftime('%m-%d %H:%M')
            })
        
        # 近期分析
        recent_analyses = Analysis.select().order_by(Analysis.created_at.desc()).limit(3)
        for analysis in recent_analyses:
            activities.append({
                'text': f"完成 {analysis.student.name} 的{get_analysis_type_display(analysis.analysis_type)}",
                'time': analysis.created_at.strftime('%m-%d %H:%M')
            })
        
        # 按時間排序
        activities.sort(key=lambda x: x['time'], reverse=True)
        return activities[:5]
        
    except Exception as e:
        logger.error(f"取得近期活動錯誤: {e}")
        return []

def calculate_class_statistics():
    """計算班級統計資料"""
    try:
        students = Student.select()
        total_students = students.count()
        
        if total_students == 0:
            return {
                'avg_participation': 0,
                'total_questions': 0,
                'active_students': 0,
                'avg_questions_per_student': 0
            }
        
        # 計算平均參與度
        total_participation = sum(s.participation_rate for s in students)
        avg_participation = round(total_participation / total_students, 1)
        
        # 計算總提問數
        total_questions = Message.select().where(Message.message_type == 'question').count()
        
        # 計算活躍學生數
        active_students = Student.select().where(Student.is_active == True).count()
        
        # 計算人均提問數
        avg_questions_per_student = round(total_questions / total_students, 1)
        
        return {
            'avg_participation': avg_participation,
            'total_questions': total_questions,
            'active_students': active_students,
            'avg_questions_per_student': avg_questions_per_student
        }
        
    except Exception as e:
        logger.error(f"計算班級統計錯誤: {e}")
        return {}

def get_participation_trends(days=30):
    """取得參與度趨勢"""
    try:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        
        trends = []
        current_date = start_date
        
        while current_date <= end_date:
            # 計算當日活躍學生數
            active_count = Student.select().where(
                Student.last_active >= current_date
            ).count()
            
            # 計算當日訊息數
            message_count = Message.select().where(
                Message.timestamp >= datetime.datetime.combine(current_date, datetime.time.min),
                Message.timestamp < datetime.datetime.combine(current_date + datetime.timedelta(days=1), datetime.time.min)
            ).count()
            
            trends.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'active_students': active_count,
                'message_count': message_count
            })
            
            current_date += datetime.timedelta(days=1)
        
        return trends
        
    except Exception as e:
        logger.error(f"取得參與度趨勢錯誤: {e}")
        return []

def export_csv(data_type):
    """匯出 CSV 資料"""
    try:
        output = StringIO()
        
        if data_type == 'students':
            writer = csv.writer(output)
            writer.writerow([
                '學生ID', '姓名', 'LINE用戶ID', '註冊時間', '最後活動',
                '總訊息數', '提問次數', '參與度', '提問率', '是否活躍'
            ])
            
            students = Student.select()
            for student in students:
                writer.writerow([
                    student.id,
                    student.name,
                    student.line_user_id,
                    student.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    student.last_active.strftime('%Y-%m-%d %H:%M:%S') if student.last_active else '',
                    student.message_count,
                    student.question_count,
                    student.participation_rate,
                    student.question_rate,
                    '是' if student.is_active else '否'
                ])
        
        elif data_type == 'messages':
            writer = csv.writer(output)
            writer.writerow([
                '訊息ID', '學生姓名', '內容', '類型', '時間戳記', '來源類型'
            ])
            
            messages = Message.select().join(Student).order_by(Message.timestamp.desc())
            for message in messages:
                writer.writerow([
                    message.id,
                    message.student.name,
                    message.content,
                    message.message_type,
                    message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    message.source_type
                ])
        
        elif data_type == 'analyses':
            writer = csv.writer(output)
            writer.writerow([
                '分析ID', '學生姓名', '分析類型', '標題', '內容', '建立時間'
            ])
            
            analyses = Analysis.select().join(Student).order_by(Analysis.created_at.desc())
            for analysis in analyses:
                writer.writerow([
                    analysis.id,
                    analysis.student.name,
                    analysis.analysis_type,
                    analysis.title,
                    analysis.content,
                    analysis.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={data_type}_{datetime.date.today()}.csv'
            }
        )
        
    except Exception as e:
        logger.error(f"CSV 匯出錯誤: {e}")
        return jsonify({'error': 'Export failed'}), 500

def export_json(data_type):
    """匯出 JSON 資料"""
    try:
        if data_type == 'students':
            students = Student.select()
            data = []
            for student in students:
                data.append({
                    'id': student.id,
                    'name': student.name,
                    'line_user_id': student.line_user_id,
                    'created_at': student.created_at.isoformat(),
                    'last_active': student.last_active.isoformat() if student.last_active else None,
                    'message_count': student.message_count,
                    'question_count': student.question_count,
                    'participation_rate': student.participation_rate,
                    'question_rate': student.question_rate,
                    'is_active': student.is_active
                })
        
        return jsonify({
            'data_type': data_type,
            'exported_at': datetime.datetime.now().isoformat(),
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        logger.error(f"JSON 匯出錯誤: {e}")
        return jsonify({'error': 'Export failed'}), 500

def get_analysis_type_display(analysis_type):
    """取得分析類型的顯示名稱"""
    type_mapping = {
        'pattern_analysis': '模式分析',
        'learning_style': '學習風格分析',
        'progress_tracking': '進度追蹤',
        'recommendation': '學習建議',
        'engagement_analysis': '參與度分析'
    }
    return type_mapping.get(analysis_type, analysis_type)

# 輔助函數
def get_daily_message_stats(student):
    """取得學生每日訊息統計"""
    # 實作細節...
    return {}

def get_weekly_participation(student):
    """取得學生每週參與度"""
    # 實作細節...
    return {}

def get_monthly_trends(student):
    """取得學生每月趨勢"""
    # 實作細節...
    return {}

def get_average_participation():
    """取得平均參與度"""
    try:
        students = Student.select()
        if students.count() == 0:
            return 0
        total = sum(s.participation_rate for s in students)
        return round(total / students.count(), 1)
    except:
        return 0

def get_top_participants():
    """取得參與度最高的學生"""
    try:
        return list(Student.select().order_by(Student.participation_rate.desc()).limit(5))
    except:
        return []

def get_recent_activity_summary():
    """取得近期活動摘要"""
    try:
        today = datetime.date.today()
        return {
            'messages_today': Message.select().where(
                Message.timestamp >= datetime.datetime.combine(today, datetime.time.min)
            ).count(),
            'active_users_today': Student.select().where(
                Student.last_active >= today
            ).count()
        }
    except:
        return {}

def get_language_distribution():
    """取得語言使用分布"""
    try:
        # 簡化版本，實際可根據訊息內容分析
        return {
            'chinese': 60,
            'english': 30,
            'mixed': 10
        }
    except:
        return {}

def get_recent_ai_insights():
    """取得近期 AI 洞察"""
    try:
        return list(Analysis.select().order_by(Analysis.created_at.desc()).limit(5))
    except:
        return []

def get_most_common_questions():
    """取得最常見問題"""
    try:
        # 簡化版本，實際可用 AI 分析相似問題
        return []
    except:
        return []

def get_engagement_alerts():
    """取得參與度警報"""
    try:
        alerts = []
        
        # 檢查低參與度學生
        low_participation = Student.select().where(
            (Student.participation_rate < 20) & 
            (Student.is_active == True)
        )
        
        for student in low_participation:
            alerts.append({
                'type': '低參與度警報',
                'message': f'{student.name} 的參與度僅 {student.participation_rate}%'
            })
        
        return alerts[:5]  # 最多顯示5個警報
        
    except:
        return []
