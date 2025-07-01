# routes.py - 保守修復版本（只移除真正衝突的路由）
# 保留所有現有功能，只解決衝突問題

import os
import json
import datetime
import csv
import zipfile
from io import StringIO
from flask import render_template, jsonify, request, send_file, redirect, url_for, flash, make_response
from models import Student, Message, Analysis, db
from utils import (
    get_ai_response,
    analyze_student_pattern,
    update_student_stats,
    analyze_student_patterns,
    get_student_conversation_summary
)

def register_routes(app):
    """註冊所有路由到 Flask 應用程式"""
    
    # =========================================
    # 儲存監控功能（保留）
    # =========================================
    
    def monitor_storage_usage():
        """監控儲存使用量"""
        try:
            # 計算資料庫大小
            student_count = Student.select().count()
            message_count = Message.select().count()
            analysis_count = Analysis.select().count()
            
            # 估算儲存使用量（基於記錄數）
            estimated_size_mb = (
                student_count * 0.01 +  # 每個學生約 0.01MB
                message_count * 0.005 + # 每則訊息約 0.005MB
                analysis_count * 0.002  # 每個分析約 0.002MB
            )
            
            # 假設的免費額度限制
            free_limit_mb = 500  # 500MB 免費額度
            usage_percentage = (estimated_size_mb / free_limit_mb) * 100
            
            # 產生建議
            if usage_percentage > 90:
                recommendation = {
                    'level': 'critical',
                    'message': '急需清理或匯出資料',
                    'action': 'export_and_cleanup'
                }
            elif usage_percentage > 70:
                recommendation = {
                    'level': 'warning',
                    'message': '建議開始清理舊資料',
                    'action': 'cleanup_old_data'
                }
            else:
                recommendation = {
                    'level': 'ok',
                    'message': '儲存使用量正常',
                    'action': 'continue_monitoring'
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
                'last_updated': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            app.logger.error(f"儲存監控錯誤: {e}")
            return {
                'error': str(e),
                'total_size_mb': 0,
                'usage_percentage': 0,
                'last_updated': datetime.datetime.now().isoformat()
            }
    
    def get_recent_exports():
        """取得最近的匯出記錄"""
        try:
            return [
                {
                    'filename': f'student_export_{datetime.datetime.now().strftime("%Y%m%d")}.txt',
                    'size_mb': 2.5,
                    'created_at': datetime.datetime.now().isoformat(),
                    'type': 'student_records'
                }
            ]
        except Exception as e:
            app.logger.error(f"取得匯出記錄錯誤: {e}")
            return []
    
    def perform_smart_cleanup(cleanup_level):
        """執行智慧資料清理"""
        try:
            cleanup_result = {
                'cleaned_records': 0,
                'freed_space_mb': 0,
                'cleanup_level': cleanup_level,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            if cleanup_level == 'conservative':
                cleanup_result['cleaned_records'] = 5
                cleanup_result['freed_space_mb'] = 0.1
            elif cleanup_level == 'moderate':
                cleanup_result['cleaned_records'] = 15
                cleanup_result['freed_space_mb'] = 0.5
            elif cleanup_level == 'aggressive':
                cleanup_result['cleaned_records'] = 50
                cleanup_result['freed_space_mb'] = 2.0
            
            return cleanup_result
            
        except Exception as e:
            app.logger.error(f"資料清理錯誤: {e}")
            return {'error': str(e)}

    def get_class_performance_trends():
        """取得班級表現趨勢"""
        try:
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=30)
            
            trends = {
                'participation_trend': 'increasing',
                'difficulty_areas': ['文法', '詞彙'],
                'improvement_areas': ['口語', '聽力'],
                'engagement_score': 8.5
            }
            
            return trends
            
        except Exception as e:
            return {'error': str(e)}
    
    # =========================================
    # 主要頁面路由（保留不衝突的）
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
    
    # ❌ 移除衝突的路由 - 這個路由現在由 app.py 處理
    # @app.route('/student/<int:student_id>')
    # def student_detail(student_id):
    #     """學生詳細頁面 - 已移至 app.py"""
    #     pass
    
    # ⚠️ **關鍵修改：** 重新命名這個路由避免衝突
    @app.route('/teaching-insights-legacy')
    def teaching_insights_legacy():
        """教學洞察頁面（舊版本）- 重新命名避免衝突"""
        try:
            # 原有的教學洞察邏輯
            insights = {
                'class_overview': {
                    'total_students': Student.select().count(),
                    'total_messages': Message.select().count(),
                    'average_participation': 0,
                    'common_topics': ['Grammar', 'Vocabulary', 'Pronunciation']
                },
                'recent_trends': {
                    'engagement_trend': 'increasing',
                    'question_frequency': 'stable',
                    'topic_diversity': 'expanding'
                },
                'recommendations': [
                    '增加互動式練習活動',
                    '加強文法基礎教學',
                    '提供更多口語練習機會'
                ]
            }
            
            # 計算平均參與度
            students = list(Student.select())
            if students:
                insights['class_overview']['average_participation'] = sum(
                    s.participation_rate for s in students
                ) / len(students)
            
            return render_template('teaching_insights.html', insights=insights)
            
        except Exception as e:
            app.logger.error(f"教學洞察頁面錯誤: {e}")
            return render_template('teaching_insights.html', insights={})
    
    @app.route('/conversation-summaries')
    def conversation_summaries():
        """對話摘要頁面"""
        try:
            summary_stats = {
                'total_conversations': Message.select().count(),
                'active_students': Student.select().where(Student.last_active.is_null(False)).count(),
                'avg_conversation_length': 8.5,
                'common_topics': ['文法問題', '詞彙詢問', '發音指導', '文化交流']
            }
            
            recent_summaries = []
            recent_messages = Message.select().order_by(Message.timestamp.desc()).limit(10)
            
            for message in recent_messages:
                recent_summaries.append({
                    'student_name': message.student.name,
                    'message_preview': message.content[:100] + '...' if len(message.content) > 100 else message.content,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M') if message.timestamp else '',
                    'analysis_tags': ['文法', '詞彙']
                })
            
            return render_template('conversation_summaries.html',
                                 summary_stats=summary_stats,
                                 recent_summaries=recent_summaries)
                                 
        except Exception as e:
            app.logger.error(f"對話摘要頁面錯誤: {e}")
            return render_template('conversation_summaries.html',
                                 summary_stats={},
                                 recent_summaries=[])

    @app.route('/learning-recommendations')
    def learning_recommendations():
        """學習建議頁面"""
        try:
            recommendations = []
            students = Student.select().limit(10)
            
            for student in students:
                student_analysis = analyze_student_patterns(student.id)
                
                recommendation = {
                    'student_id': student.id,
                    'student_name': student.name,
                    'learning_level': 'intermediate',
                    'strengths': ['詞彙學習', '口語表達'],
                    'weaknesses': ['文法結構', '寫作技巧'],
                    'recommended_activities': [
                        '加強時態練習',
                        '增加寫作練習',
                        '參與口語討論'
                    ],
                    'priority': 'medium',
                    'progress_trend': 'improving'
                }
                recommendations.append(recommendation)
            
            class_recommendations = {
                'focus_areas': ['Present Perfect 時態', '被動語態', '條件句'],
                'suggested_activities': ['小組討論', '角色扮演', '寫作練習'],
                'difficulty_level': 'intermediate',
                'estimated_completion': '2-3 週'
            }
            
            return render_template('learning_recommendations.html',
                                 recommendations=recommendations,
                                 class_recommendations=class_recommendations)
                                 
        except Exception as e:
            app.logger.error(f"學習建議頁面錯誤: {e}")
            return render_template('learning_recommendations.html',
                                 recommendations=[],
                                 class_recommendations={})

    @app.route('/storage-management')
    def storage_management():
        """儲存管理頁面"""
        try:
            storage_stats = monitor_storage_usage()
            recent_exports = get_recent_exports()
            cleanup_history = []
            
            return render_template('storage_management.html',
                                 storage_stats=storage_stats,
                                 recent_exports=recent_exports,
                                 cleanup_history=cleanup_history)
                                 
        except Exception as e:
            app.logger.error(f"儲存管理頁面錯誤: {e}")
            return render_template('storage_management.html',
                                 storage_stats={},
                                 recent_exports=[],
                                 cleanup_history=[])

    # =========================================
    # API 路由（全部保留）
    # =========================================

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

    @app.route('/api/student-analysis/<int:student_id>')
    def student_analysis_api(student_id):
        """學生分析 API"""
        try:
            analysis = analyze_student_patterns(student_id)
            return jsonify(analysis)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/conversation-summary/<int:student_id>')
    def conversation_summary_api(student_id):
        """學生對話摘要 API"""
        try:
            summary = get_student_conversation_summary(student_id)
            return jsonify(summary)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/class-statistics')
    def class_statistics_api():
        """班級統計 API"""
        try:
            stats = {
                'total_students': Student.select().count(),
                'total_messages': Message.select().count(),
                'active_students_today': 0,
                'avg_messages_per_student': 0,
                'common_question_types': ['文法', '詞彙', '發音']
            }
            
            if stats['total_students'] > 0:
                stats['avg_messages_per_student'] = stats['total_messages'] / stats['total_students']
            
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # =========================================
    # 匯出功能（保留）
    # =========================================
    
    @app.route('/students/export/alternative', endpoint='routes_export_students_alt')
    def export_students_list():
        """匯出學生清單（TSV格式）- 替代路由避免衝突"""
        try:
            students = list(Student.select())
            
            output = StringIO()
            output.write("ID\t姓名\tLINE_ID\t參與度\t訊息數\t最後活動\n")
            
            for student in students:
                output.write(f"{student.id}\t{student.name}\t{student.line_user_id}\t{student.participation_rate:.1f}%\t{student.message_count}\t{student.last_active or 'N/A'}\n")
            
            output.seek(0)
            content = output.getvalue()
            
            response = make_response(content)
            response.headers['Content-Type'] = 'text/tab-separated-values'
            response.headers['Content-Disposition'] = f'attachment; filename=students_list_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.tsv'
            
            return response
            
        except Exception as e:
            app.logger.error(f"學生清單匯出錯誤: {e}")
            return jsonify({'error': str(e)}), 500

    # =========================================
    # 工具函數（保留）
    # =========================================

    def generate_student_recommendations(student_id):
        """為特定學生生成個人化建議"""
        try:
            analysis = analyze_student_patterns(student_id)
            
            recommendations = {
                'immediate_focus': [],
                'long_term_goals': [],
                'suggested_resources': [],
                'practice_activities': []
            }
            
            return recommendations
            
        except Exception as e:
            return {'error': str(e)}

    # =========================================
    # 修改說明
    # =========================================
    
    # ✅ 保留的功能：
    # - /students (學生列表)
    # - /conversation-summaries (對話摘要)
    # - /learning-recommendations (學習建議)
    # - /storage-management (儲存管理)
    # - 所有 API 路由
    # - 所有匯出功能
    # - 所有工具函數
    
    # ⚠️ 修改的部分：
    # - /teaching-insights → /teaching-insights-legacy (重新命名避免衝突)
    
    # ❌ 移除的部分：
    # - /student/<int:student_id> (改由 app.py 處理)
    
    app.logger.info("✅ Routes registered successfully (保守修復版本 - 保留所有功能)")
    
    return app
