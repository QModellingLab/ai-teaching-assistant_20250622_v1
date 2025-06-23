# routes.py - 更新版本（移除 data-export 路由，整合匯出功能到 teaching-insights）

import os
import json
import datetime
import csv
import zipfile
from io import StringIO
from flask import render_template, jsonify, request, send_file, redirect, url_for, flash
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
    # 儲存監控功能
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
                'last_check': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def perform_smart_cleanup(cleanup_level='conservative'):
        """執行智能資料清理"""
        try:
            if cleanup_level == 'conservative':
                # 保守清理：只刪除超過 1 年的資料
                cutoff_date = datetime.datetime.now() - datetime.timedelta(days=365)
            elif cleanup_level == 'moderate':
                # 中等清理：刪除超過 6 個月的資料
                cutoff_date = datetime.datetime.now() - datetime.timedelta(days=180)
            elif cleanup_level == 'aggressive':
                # 積極清理：刪除超過 3 個月的資料
                cutoff_date = datetime.datetime.now() - datetime.timedelta(days=90)
            else:
                return {'success': False, 'error': 'Invalid cleanup level'}
            
            # 執行清理
            deleted_messages = Message.delete().where(Message.timestamp < cutoff_date).execute()
            deleted_analyses = Analysis.delete().where(Analysis.created_at < cutoff_date).execute()
            
            return {
                'success': True,
                'deleted_messages': deleted_messages,
                'deleted_analyses': deleted_analyses,
                'cleanup_level': cleanup_level,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_recent_exports():
        """取得最近的匯出記錄"""
        # 這裡應該從資料庫或檔案系統中取得實際的匯出記錄
        return [
            {
                'filename': 'comprehensive_data_20241223.json',
                'type': 'comprehensive',
                'size_mb': 15.2,
                'created_at': '2024-12-23 14:30:00',
                'download_count': 3
            },
            {
                'filename': 'student_progress_20241222.pdf',
                'type': 'progress_report',
                'size_mb': 2.8,
                'created_at': '2024-12-22 16:45:00',
                'download_count': 1
            }
        ]
    
    # =========================================
    # 儲存管理路由
    # =========================================
    
    @app.route('/storage-management')
    def storage_management():
        """儲存管理頁面"""
        try:
            storage_stats = monitor_storage_usage()
            recent_exports = get_recent_exports()
            cleanup_history = []  # 可以從資料庫取得清理歷史
            
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
    # 移除的路由：資料匯出中心
    # =========================================
    # @app.route('/data-export') - 已移除
    # 功能已整合到 /teaching-insights 路由中
    # 使用者現在可以在教師分析後台直接進行資料匯出

    # =========================================
    # 匯出 API 路由（保留，由 app.py 中的路由處理）
    # =========================================
    # 這些 API 路由現在由 app.py 中的程式碼處理：
    # - /api/export/<export_type>
    # - /download/<filename>

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
            conversation_summary = get_student_conversation_summary(student_id)
            
            return render_template('student_detail.html',
                                 student=student,
                                 messages=messages,
                                 analysis=analysis,
                                 conversation_summary=conversation_summary)
                                 
        except Exception as e:
            app.logger.error(f"學生詳細頁面錯誤: {e}")
            return f"學生資料載入失敗: {str(e)}", 500

    @app.route('/conversation-summaries')
    def conversation_summaries():
        """對話摘要頁面"""
        try:
            # 取得對話摘要統計
            summary_stats = {
                'total_conversations': Message.select().count(),
                'active_students': Student.select().where(Student.last_active.is_null(False)).count(),
                'avg_conversation_length': 8.5,  # 可以從實際資料計算
                'common_topics': ['文法問題', '詞彙詢問', '發音指導', '文化交流']
            }
            
            # 取得最近的對話摘要
            recent_summaries = []
            recent_messages = Message.select().order_by(Message.timestamp.desc()).limit(10)
            
            for message in recent_messages:
                recent_summaries.append({
                    'student_name': message.student.name,
                    'message_preview': message.content[:100] + '...' if len(message.content) > 100 else message.content,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M') if message.timestamp else '',
                    'analysis_tags': ['文法', '詞彙']  # 可以從分析資料取得
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
            # 取得個人化學習建議
            recommendations = []
            students = Student.select().limit(10)  # 限制數量以提升效能
            
            for student in students:
                # 分析學生學習模式
                student_analysis = analyze_student_patterns(student.id)
                
                recommendation = {
                    'student_id': student.id,
                    'student_name': student.name,
                    'learning_level': 'intermediate',  # 可以從分析結果取得
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
            
            # 班級整體建議
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

    # =========================================
    # API 路由
    # =========================================

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
                'active_students_today': 0,  # 可以根據實際需求計算
                'avg_messages_per_student': 0,
                'common_question_types': ['文法', '詞彙', '發音']
            }
            
            if stats['total_students'] > 0:
                stats['avg_messages_per_student'] = stats['total_messages'] / stats['total_students']
            
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # =========================================
    # 工具函數
    # =========================================

    def generate_student_recommendations(student_id):
        """為特定學生生成個人化建議"""
        try:
            # 分析學生的學習模式
            analysis = analyze_student_patterns(student_id)
            
            # 基於分析結果生成建議
            recommendations = {
                'immediate_focus': [],
                'long_term_goals': [],
                'suggested_resources': [],
                'practice_activities': []
            }
            
            # 這裡可以加入更複雜的推薦邏輯
            
            return recommendations
            
        except Exception as e:
            return {'error': str(e)}

    def get_class_performance_trends():
        """取得班級表現趨勢"""
        try:
            # 計算最近 30 天的表現趨勢
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=30)
            
            # 這裡可以加入實際的趨勢分析邏輯
            trends = {
                'participation_trend': 'increasing',
                'difficulty_areas': ['文法', '詞彙'],
                'improvement_areas': ['口語', '聽力'],
                'engagement_score': 8.5
            }
            
            return trends
            
        except Exception as e:
            return {'error': str(e)}

    return app  # 回傳配置完成的 app
