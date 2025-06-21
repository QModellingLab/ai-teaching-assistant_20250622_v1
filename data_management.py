# data_management.py - 資料管理與匯出功能
# 包含：資料匯出、儲存監控、智能清理

import os
import json
import datetime
import csv
import zipfile
import logging
from io import StringIO
from collections import defaultdict, Counter
from models import Student, Message, Analysis, db

logger = logging.getLogger(__name__)

# =========================================
# 1. 資料匯出功能
# =========================================

def perform_data_export(export_type, export_format='json', date_range=None):
    """執行資料匯出"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if export_type == 'comprehensive':
            return export_comprehensive_data(timestamp, export_format, date_range)
        elif export_type == 'academic_paper':
            return export_academic_data(timestamp, export_format, date_range)
        elif export_type == 'progress_report':
            return export_progress_data(timestamp, export_format, date_range)
        elif export_type == 'analytics_summary':
            return export_analytics_summary(timestamp, export_format, date_range)
        else:
            return {'success': False, 'error': 'Unknown export type'}
            
    except Exception as e:
        logger.error(f"資料匯出錯誤: {e}")
        return {'success': False, 'error': str(e)}

def export_comprehensive_data(timestamp, format_type, date_range=None):
    """匯出完整教學研究資料"""
    try:
        filename = f'comprehensive_teaching_data_{timestamp}'
        
        # 收集所有資料
        students_data = []
        messages_data = []
        analyses_data = []
        
        # 學生資料
        students_query = Student.select()
        if date_range:
            start_date, end_date = date_range
            students_query = students_query.where(
                Student.created_at.between(start_date, end_date)
            )
        
        for student in students_query:
            students_data.append({
                'id': student.id,
                'name': student.name,
                'line_user_id': student.line_user_id,
                'participation_rate': student.participation_rate,
                'question_count': student.question_count,
                'message_count': student.message_count,
                'question_rate': student.question_rate,
                'active_days': student.active_days,
                'learning_style': student.learning_style or '',
                'language_preference': student.language_preference or '',
                'created_at': student.created_at.isoformat() if student.created_at else '',
                'last_active': student.last_active.isoformat() if student.last_active else '',
                'notes': student.notes or ''
            })
        
        # 訊息資料（匿名化處理）
        messages_query = Message.select()
        if date_range:
            start_date, end_date = date_range
            messages_query = messages_query.where(
                Message.timestamp.between(start_date, end_date)
            )
        
        for message in messages_query:
            messages_data.append({
                'id': message.id,
                'student_id': message.student_id,
                'content_length': len(message.content),
                'message_type': message.message_type,
                'timestamp': message.timestamp.isoformat(),
                'source_type': message.source_type or '',
                'sentiment': message.sentiment or '',
                'topic_category': message.topic_category or '',
                'language_detected': message.language_detected or '',
                'complexity_score': message.complexity_score or 0
            })
        
        # 分析資料
        analyses_query = Analysis.select()
        if date_range:
            start_date, end_date = date_range
            analyses_query = analyses_query.where(
                Analysis.timestamp.between(start_date, end_date)
            )
        
        for analysis in analyses_query:
            try:
                analysis_data = json.loads(analysis.analysis_data) if analysis.analysis_data else {}
            except json.JSONDecodeError:
                analysis_data = {}
                
            analyses_data.append({
                'id': analysis.id,
                'student_id': analysis.student_id,
                'analysis_type': analysis.analysis_type,
                'timestamp': analysis.timestamp.isoformat(),
                'confidence_score': analysis.confidence_score,
                'content_domain': analysis_data.get('content_domain', ''),
                'cognitive_level': analysis_data.get('cognitive_level', ''),
                'question_type': analysis_data.get('question_type', ''),
                'language_complexity': analysis_data.get('language_complexity', ''),
                'difficulty': analysis_data.get('difficulty', ''),
                'key_concepts': ', '.join(analysis_data.get('key_concepts', [])),
                'reasoning': analysis_data.get('reasoning', '')
            })
        
        # 綜合資料包
        export_data = {
            'export_info': {
                'type': 'comprehensive_teaching_data',
                'timestamp': timestamp,
                'format': format_type,
                'date_range': date_range,
                'total_students': len(students_data),
                'total_messages': len(messages_data),
                'total_analyses': len(analyses_data)
            },
            'students': students_data,
            'messages': messages_data,
            'analyses': analyses_data,
            'class_summary': generate_export_summary(students_data, messages_data, analyses_data)
        }
        
        # 根據格式匯出
        if format_type == 'json':
            filename += '.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
        elif format_type == 'csv':
            # 為 CSV 格式創建多個檔案的壓縮包
            zip_filename = filename + '.zip'
            
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 學生資料 CSV
                students_csv = StringIO()
                if students_data:
                    students_writer = csv.DictWriter(students_csv, fieldnames=students_data[0].keys())
                    students_writer.writeheader()
                    students_writer.writerows(students_data)
                zipf.writestr('students.csv', students_csv.getvalue())
                
                # 訊息資料 CSV
                messages_csv = StringIO()
                if messages_data:
                    messages_writer = csv.DictWriter(messages_csv, fieldnames=messages_data[0].keys())
                    messages_writer.writeheader()
                    messages_writer.writerows(messages_data)
                zipf.writestr('messages.csv', messages_csv.getvalue())
                
                # 分析資料 CSV
                analyses_csv = StringIO()
                if analyses_data:
                    analyses_writer = csv.DictWriter(analyses_csv, fieldnames=analyses_data[0].keys())
                    analyses_writer.writeheader()
                    analyses_writer.writerows(analyses_data)
                zipf.writestr('analyses.csv', analyses_csv.getvalue())
                
                # 摘要報告
                summary_csv = StringIO()
                summary_writer = csv.writer(summary_csv)
                summary_writer.writerow(['Metric', 'Value'])
                for key, value in export_data['class_summary'].items():
                    summary_writer.writerow([key, value])
                zipf.writestr('class_summary.csv', summary_csv.getvalue())
            
            filename = zip_filename
        
        # 取得檔案大小
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return {
            'success': True,
            'filename': filename,
            'size': file_size,
            'record_counts': {
                'students': len(students_data),
                'messages': len(messages_data),
                'analyses': len(analyses_data)
            },
            'export_type': 'comprehensive'
        }
        
    except Exception as e:
        logger.error(f"完整資料匯出錯誤: {e}")
        return {'success': False, 'error': str(e)}

def generate_export_summary(students_data, messages_data, analyses_data):
    """生成匯出資料摘要"""
    try:
        summary = {
            'total_students': len(students_data),
            'total_messages': len(messages_data),
            'total_analyses': len(analyses_data),
            'avg_participation_rate': 0,
            'total_questions': 0,
            'most_common_cognitive_level': '',
            'most_common_content_domain': '',
            'active_period_days': 0
        }
        
        if students_data:
            # 平均參與度
            participation_rates = [s['participation_rate'] for s in students_data if s['participation_rate']]
            if participation_rates:
                summary['avg_participation_rate'] = round(sum(participation_rates) / len(participation_rates), 2)
            
            # 總問題數
            summary['total_questions'] = sum(s['question_count'] for s in students_data)
        
        if analyses_data:
            # 最常見的認知層次
            cognitive_levels = [a['cognitive_level'] for a in analyses_data if a['cognitive_level']]
            if cognitive_levels:
                summary['most_common_cognitive_level'] = Counter(cognitive_levels).most_common(1)[0][0]
            
            # 最常見的內容領域
            content_domains = [a['content_domain'] for a in analyses_data if a['content_domain']]
            if content_domains:
                summary['most_common_content_domain'] = Counter(content_domains).most_common(1)[0][0]
        
        if messages_data:
            # 活動期間
            timestamps = [datetime.datetime.fromisoformat(m['timestamp']) for m in messages_data if m['timestamp']]
            if timestamps:
                min_date = min(timestamps)
                max_date = max(timestamps)
                summary['active_period_days'] = (max_date - min_date).days
        
        return summary
        
    except Exception as e:
        logger.error(f"匯出摘要生成錯誤: {e}")
        return {}

def export_academic_data(timestamp, format_type, date_range=None):
    """匯出學術研究資料（匿名化）"""
    try:
        filename = f'academic_research_data_{timestamp}'
        
        # 匿名化的學術資料
        academic_data = {
            'export_info': {
                'type': 'academic_research_data',
                'timestamp': timestamp,
                'anonymized': True,
                'suitable_for_publication': True
            },
            'class_statistics': generate_class_statistics(),
            'cognitive_development_analysis': analyze_cognitive_development_trends(),
            'engagement_patterns': analyze_engagement_patterns(),
            'question_classification_results': get_question_category_stats(),
            'learning_progression_data': generate_learning_progression_data()
        }
        
        if format_type == 'json':
            filename += '.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(academic_data, f, ensure_ascii=False, indent=2)
                
        elif format_type == 'csv':
            # 為學術研究創建結構化的 CSV 資料
            filename += '.csv'
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 寫入各種統計資料
                writer.writerow(['Metric Category', 'Metric Name', 'Value'])
                
                for category, data in academic_data.items():
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, (str, int, float)):
                                writer.writerow([category, key, value])
                            else:
                                writer.writerow([category, key, json.dumps(value)])
        
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return {
            'success': True,
            'filename': filename,
            'size': file_size,
            'export_type': 'academic_paper'
        }
        
    except Exception as e:
        logger.error(f"學術資料匯出錯誤: {e}")
        return {'success': False, 'error': str(e)}

def export_progress_data(timestamp, format_type, date_range=None):
    """匯出學生進度資料"""
    try:
        filename = f'student_progress_report_{timestamp}'
        
        students = list(Student.select().where(~Student.name.startswith('[DEMO]')))
        progress_data = []
        
        for student in students:
            # 收集學生進度資料
            analyses = list(Analysis.select().where(
                (Analysis.student_id == student.id) &
                (Analysis.analysis_type == 'question_classification')
            ).order_by(Analysis.timestamp.asc()))
            
            messages = list(Message.select().where(
                Message.student_id == student.id
            ).order_by(Message.timestamp.asc()))
            
            progress_info = {
                'student_name': student.name,
                'participation_rate': student.participation_rate,
                'total_questions': student.question_count,
                'total_messages': student.message_count,
                'learning_period_days': (datetime.datetime.now() - student.created_at).days if student.created_at else 0,
                'cognitive_progression': analyze_student_cognitive_progression(analyses),
                'engagement_trend': analyze_student_engagement_trend(messages),
                'recent_activity': len([m for m in messages if m.timestamp > datetime.datetime.now() - datetime.timedelta(days=7)])
            }
            
            progress_data.append(progress_info)
        
        export_data = {
            'export_info': {
                'type': 'student_progress_report',
                'timestamp': timestamp,
                'total_students': len(progress_data)
            },
            'progress_reports': progress_data,
            'class_summary': generate_class_progress_summary(progress_data)
        }
        
        if format_type == 'json':
            filename += '.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
        elif format_type == 'csv':
            filename += '.csv'
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if progress_data:
                    # 扁平化資料以適合 CSV
                    flattened_data = []
                    for item in progress_data:
                        flat_item = {
                            'student_name': item['student_name'],
                            'participation_rate': item['participation_rate'],
                            'total_questions': item['total_questions'],
                            'total_messages': item['total_messages'],
                            'learning_period_days': item['learning_period_days'],
                            'recent_activity': item['recent_activity']
                        }
                        flattened_data.append(flat_item)
                    
                    writer = csv.DictWriter(f, fieldnames=flattened_data[0].keys())
                    writer.writeheader()
                    writer.writerows(flattened_data)
        
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return {
            'success': True,
            'filename': filename,
            'size': file_size,
            'export_type': 'progress_report'
        }
        
    except Exception as e:
        logger.error(f"進度資料匯出錯誤: {e}")
        return {'success': False, 'error': str(e)}

def export_analytics_summary(timestamp, format_type, date_range=None):
    """匯出分析摘要報告"""
    try:
        filename = f'analytics_summary_{timestamp}'
        
        # 從 teaching_analytics 模組匯入分析函數
        from teaching_analytics import (
            analyze_class_engagement, 
            analyze_cognitive_development_trends,
            analyze_learning_difficulties,
            generate_class_teaching_recommendations
        )
        
        summary_data = {
            'export_info': {
                'type': 'analytics_summary',
                'timestamp': timestamp,
                'report_period': date_range or 'all_time'
            },
            'class_engagement': analyze_class_engagement(),
            'cognitive_trends': analyze_cognitive_development_trends(),
            'learning_difficulties': analyze_learning_difficulties(),
            'teaching_recommendations': generate_class_teaching_recommendations(),
            'system_metrics': get_system_metrics()
        }
        
        if format_type == 'json':
            filename += '.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
                
        elif format_type == 'csv':
            filename += '.csv'
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Analysis Category', 'Metric', 'Value'])
                
                # 展平所有分析資料
                for category, data in summary_data.items():
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, (str, int, float)):
                                writer.writerow([category, key, value])
                            elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
                                for i, item in enumerate(value):
                                    writer.writerow([category, f"{key}_{i}", json.dumps(item)])
                            else:
                                writer.writerow([category, key, str(value)])
        
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return {
            'success': True,
            'filename': filename,
            'size': file_size,
            'export_type': 'analytics_summary'
        }
        
    except Exception as e:
        logger.error(f"分析摘要匯出錯誤: {e}")
        return {'success': False, 'error': str(e)}

# =========================================
# 2. 儲存監控功能
# =========================================

def monitor_storage_usage():
    """監控儲存使用量"""
    try:
        # 計算各表的記錄數和估算大小
        student_count = Student.select().count()
        message_count = Message.select().count()
        analysis_count = Analysis.select().count()
        
        # 詳細大小估算
        estimated_sizes = {
            'students_mb': student_count * 0.001,  # 每個學生約1KB
            'messages_mb': message_count * 0.005,  # 每則訊息約5KB
            'analyses_mb': analysis_count * 0.002  # 每個分析約2KB
        }
        
        total_size_mb = sum(estimated_sizes.values())
        
        # Railway PostgreSQL 免費額度
        free_limit_mb = 512
        usage_percentage = (total_size_mb / free_limit_mb) * 100
        
        # 生成建議
        recommendation = generate_storage_recommendation(usage_percentage)
        
        return {
            'total_size_mb': round(total_size_mb, 2),
            'size_breakdown': estimated_sizes,
            'free_limit_mb': free_limit_mb,
            'usage_percentage': round(usage_percentage, 1),
            'remaining_mb': round(free_limit_mb - total_size_mb, 2),
            'record_counts': {
                'students': student_count,
                'messages': message_count,
                'analyses': analysis_count,
                'real_students': Student.select().where(~Student.name.startswith('[DEMO]')).count(),
                'demo_students': Student.select().where(Student.name.startswith('[DEMO]')).count()
            },
            'recommendation': recommendation,
            'last_check': datetime.datetime.now().isoformat(),
            'projected_monthly_growth': estimate_monthly_growth()
        }
        
    except Exception as e:
        logger.error(f"儲存監控錯誤: {e}")
        return {'error': str(e)}

def generate_storage_recommendation(usage_percentage):
    """生成儲存建議"""
    if usage_percentage < 30:
        return {
            'level': 'safe',
            'message': '儲存空間充足，系統運行良好',
            'action': 'continue_monitoring',
            'urgency': 'low'
        }
    elif usage_percentage < 50:
        return {
            'level': 'good',
            'message': '儲存使用正常，可考慮定期清理演示資料',
            'action': 'routine_maintenance',
            'urgency': 'low'
        }
    elif usage_percentage < 70:
        return {
            'level': 'caution',
            'message': '建議進行保守清理，移除演示資料',
            'action': 'conservative_cleanup',
            'urgency': 'medium'
        }
    elif usage_percentage < 85:
        return {
            'level': 'warning',
            'message': '建議進行適度資料清理並匯出備份',
            'action': 'moderate_cleanup_with_export',
            'urgency': 'medium'
        }
    else:
        return {
            'level': 'critical',
            'message': '急需清理或匯出資料以避免服務中斷',
            'action': 'immediate_action_required',
            'urgency': 'high'
        }

def estimate_monthly_growth():
    """估算月增長量"""
    try:
        # 基於最近30天的資料增長估算
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        
        recent_messages = Message.select().where(Message.timestamp > thirty_days_ago).count()
        recent_analyses = Analysis.select().where(Analysis.timestamp > thirty_days_ago).count()
        
        # 估算月增長（MB）
        monthly_growth_mb = (recent_messages * 0.005) + (recent_analyses * 0.002)
        
        return {
            'messages_per_month': recent_messages,
            'analyses_per_month': recent_analyses,
            'estimated_mb_per_month': round(monthly_growth_mb, 2),
            'months_to_limit': round(512 / max(monthly_growth_mb, 1), 1) if monthly_growth_mb > 0 else float('inf')
        }
        
    except Exception as e:
        logger.error(f"增長估算錯誤: {e}")
        return {'estimated_mb_per_month': 0}

# =========================================
# 3. 智能清理功能
# =========================================

def perform_smart_cleanup(cleanup_level):
    """執行智能清理"""
    try:
        cleanup_actions = []
        total_space_freed = 0
        records_affected = {'students': 0, 'messages': 0, 'analyses': 0}
        
        if cleanup_level == 'conservative':
            # 保守清理：只刪除演示資料
            result = cleanup_demo_data()
            cleanup_actions.append(result)
            records_affected['students'] += result.get('students_deleted', 0)
            total_space_freed += result.get('space_freed_mb', 0)
            
        elif cleanup_level == 'moderate':
            # 適度清理：演示資料 + 壓縮舊資料
            demo_result = cleanup_demo_data()
            cleanup_actions.append(demo_result)
            records_affected['students'] += demo_result.get('students_deleted', 0)
            
            compress_result = compress_old_messages(90)  # 90天前的資料
            cleanup_actions.append(compress_result)
            records_affected['messages'] += compress_result.get('messages_compressed', 0)
            
            total_space_freed += demo_result.get('space_freed_mb', 0) + compress_result.get('space_freed_mb', 0)
            
        elif cleanup_level == 'aggressive':
            # 積極清理：大幅減少資料量
            demo_result = cleanup_demo_data()
            cleanup_actions.append(demo_result)
            
            aggressive_result = aggressive_data_cleanup()
            cleanup_actions.append(aggressive_result)
            
            total_space_freed += demo_result.get('space_freed_mb', 0) + aggressive_result.get('space_freed_mb', 0)
            records_affected.update(aggressive_result.get('records_affected', {}))
        
        return {
            'success': True,
            'cleanup_level': cleanup_level,
            'actions_taken': cleanup_actions,
            'total_space_freed_mb': round(total_space_freed, 2),
            'records_affected': records_affected,
            'completed_at': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"智能清理錯誤: {e}")
        return {'success': False, 'error': str(e)}

def cleanup_demo_data():
    """清理演示資料"""
    try:
        # 找出演示學生
        demo_students = list(Student.select().where(
            (Student.name.startswith('[DEMO]')) |
            (Student.line_user_id.startswith('demo_'))
        ))
        
        deleted_count = 0
        space_freed = 0
        
        for student in demo_students:
            # 計算釋放的空間
            student_messages = Message.select().where(Message.student == student).count()
            student_analyses = Analysis.select().where(Analysis.student == student).count()
            
            space_freed += (student_messages * 0.005) + (student_analyses * 0.002) + 0.001
            
            # 刪除相關資料
            Message.delete().where(Message.student == student).execute()
            Analysis.delete().where(Analysis.student == student).execute()
            student.delete_instance()
            
            deleted_count += 1
        
        return {
            'action': 'cleanup_demo_data',
            'students_deleted': deleted_count,
            'space_freed_mb': round(space_freed, 2),
            'description': f'成功清理 {deleted_count} 個演示學生的所有資料'
        }
        
    except Exception as e:
        logger.error(f"演示資料清理錯誤: {e}")
        return {'action': 'cleanup_demo_data', 'error': str(e)}

def compress_old_messages(retention_days):
    """壓縮舊訊息內容"""
    try:
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        
        # 找出舊訊息
        old_messages = list(Message.select().where(
            (Message.timestamp < cutoff_date) &
            (Message.content.length() > 50)  # 只處理長訊息
        ))
        
        compressed_count = 0
        space_freed = 0
        
        for message in old_messages:
            original_length = len(message.content)
            # 保留前50字符 + 摘要標記
            message.content = message.content[:50] + "...[已壓縮]"
            message.save()
            
            # 估算節省的空間
            space_saved = (original_length - len(message.content)) * 0.001 / 1024  # 轉換為MB
            space_freed += space_saved
            compressed_count += 1
        
        return {
            'action': 'compress_old_messages',
            'messages_compressed': compressed_count,
            'space_freed_mb': round(space_freed, 2),
            'description': f'壓縮了 {compressed_count} 則 {retention_days} 天前的訊息內容'
        }
        
    except Exception as e:
        logger.error(f"訊息壓縮錯誤: {e}")
        return {'action': 'compress_old_messages', 'error': str(e)}

def aggressive_data_cleanup():
    """積極資料清理"""
    try:
        actions_taken = []
        total_space_freed = 0
        
        # 1. 刪除所有超過60天的原始訊息內容，只保留統計
        old_messages = Message.select().where(
            Message.timestamp < datetime.datetime.now() - datetime.timedelta(days=60)
        )
        
        message_count = 0
        for message in old_messages:
            original_size = len(message.content) * 0.001 / 1024  # MB
            message.content = f"[已清理-{message.message_type}-{message.timestamp.strftime('%Y-%m-%d')}]"
            message.save()
            total_space_freed += original_size
            message_count += 1
        
        actions_taken.append({
            'action': 'aggressive_message_cleanup',
            'messages_affected': message_count,
            'description': f'清理了 {message_count} 則舊訊息的詳細內容'
        })
        
        # 2. 合併重複的分析記錄
        duplicate_analyses = find_duplicate_analyses()
        if duplicate_analyses:
            removed_duplicates = remove_duplicate_analyses(duplicate_analyses)
            actions_taken.append(removed_duplicates)
            total_space_freed += removed_duplicates.get('space_freed_mb', 0)
        
        return {
            'action': 'aggressive_data_cleanup',
            'space_freed_mb': round(total_space_freed, 2),
            'records_affected': {'messages': message_count},
            'sub_actions': actions_taken,
            'description': '執行積極清理，大幅減少資料量'
        }
        
    except Exception as e:
        logger.error(f"積極清理錯誤: {e}")
        return {'action': 'aggressive_data_cleanup', 'error': str(e)}

def find_duplicate_analyses():
    """找出重複的分析記錄"""
    try:
        # 簡化版本：基於學生ID和時間戳找出可能的重複
        analyses = list(Analysis.select().order_by(Analysis.student_id, Analysis.timestamp))
        
        duplicates = []
        prev_analysis = None
        
        for analysis in analyses:
            if (prev_analysis and 
                analysis.student_id == prev_analysis.student_id and
                analysis.analysis_type == prev_analysis.analysis_type and
                abs((analysis.timestamp - prev_analysis.timestamp).total_seconds()) < 300):  # 5分鐘內
                duplicates.append(analysis.id)
            prev_analysis = analysis
        
        return duplicates
        
    except Exception as e:
        logger.error(f"重複分析查找錯誤: {e}")
        return []

def remove_duplicate_analyses(duplicate_ids):
    """移除重複的分析記錄"""
    try:
        removed_count = Analysis.delete().where(Analysis.id.in_(duplicate_ids)).execute()
        space_freed = removed_count * 0.002  # 每個分析約2KB
        
        return {
            'action': 'remove_duplicate_analyses',
            'analyses_removed': removed_count,
            'space_freed_mb': round(space_freed, 2),
            'description': f'移除了 {removed_count} 個重複的分析記錄'
        }
        
    except Exception as e:
        logger.error(f"重複分析移除錯誤: {e}")
        return {'action': 'remove_duplicate_analyses', 'error': str(e)}

def get_cleanup_history():
    """取得清理歷史記錄"""
    try:
        # 這裡可以從日誌或專門的歷史表中讀取
        # 暫時返回示例資料
        return [
            {
                'action': '保守清理',
                'result': '清理了 3 個演示學生，釋放 2.1 MB',
                'date': '2025-06-20 15:30'
            },
            {
                'action': '資料匯出',
                'result': '匯出完整教學資料，檔案大小 5.8 MB',
                'date': '2025-06-19 10:15'
            }
        ]
        
    except Exception as e:
        logger.error(f"清理歷史取得錯誤: {e}")
        return []

def get_recent_exports():
    """取得最近匯出記錄"""
    try:
        # 這裡可以從檔案系統或資料庫中讀取
        # 暫時返回示例資料
        return [
            {
                'name': '完整教學研究資料',
                'filename': 'comprehensive_teaching_data_20250620_143000.json',
                'size': '5.8 MB',
                'format': 'JSON',
                'date': '2025-06-20 14:30'
            },
            {
                'name': '學術論文資料',
                'filename': 'academic_research_data_20250619_101500.csv',
                'size': '2.3 MB',
                'format': 'CSV',
                'date': '2025-06-19 10:15'
            }
        ]
        
    except Exception as e:
        logger.error(f"匯出記錄取得錯誤: {e}")
        return []

# =========================================
# 輔助函數
# =========================================

def generate_class_statistics():
    """生成班級統計資料"""
    try:
        students = list(Student.select().where(~Student.name.startswith('[DEMO]')))
        
        if not students:
            return {'status': 'no_data'}
        
        stats = {
            'total_students': len(students),
            'participation_rate_mean': round(sum(s.participation_rate for s in students) / len(students), 2),
            'participation_rate_std': calculate_std([s.participation_rate for s in students]),
            'question_count_mean': round(sum(s.question_count for s in students) / len(students), 2),
            'question_count_std': calculate_std([s.question_count for s in students]),
            'message_count_mean': round(sum(s.message_count for s in students) / len(students), 2),
            'message_count_std': calculate_std([s.message_count for s in students]),
            'high_engagement_percentage': round(len([s for s in students if s.participation_rate >= 75]) / len(students) * 100, 2),
            'medium_engagement_percentage': round(len([s for s in students if 50 <= s.participation_rate < 75]) / len(students) * 100, 2),
            'low_engagement_percentage': round(len([s for s in students if s.participation_rate < 50]) / len(students) * 100, 2)
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"班級統計生成錯誤: {e}")
        return {'error': str(e)}

def calculate_std(values):
    """計算標準差"""
    try:
        if len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return round(variance ** 0.5, 2)
        
    except Exception:
        return 0

def analyze_cognitive_development_trends():
    """分析認知發展趨勢（簡化版本）"""
    try:
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ))
        
        if not analyses:
            return {'status': 'no_data'}
        
        cognitive_distribution = Counter()
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                cognitive_level = data.get('cognitive_level', 'Unknown')
                cognitive_distribution[cognitive_level] += 1
            except json.JSONDecodeError:
                continue
        
        return {
            'total_analyses': len(analyses),
            'cognitive_distribution': dict(cognitive_distribution)
        }
        
    except Exception as e:
        logger.error(f"認知發展趨勢分析錯誤: {e}")
        return {'error': str(e)}

def analyze_engagement_patterns():
    """分析參與度模式"""
    try:
        # 取得所有真實學生的訊息
        messages = list(Message.select().join(Student).where(
            ~Student.name.startswith('[DEMO]')
        ))
        
        if not messages:
            return {'status': 'no_data'}
        
        patterns = {
            'total_messages': len(messages),
            'questions_vs_statements': {
                'questions': len([m for m in messages if m.message_type == 'question']),
                'statements': len([m for m in messages if m.message_type == 'statement'])
            },
            'hourly_distribution': analyze_hourly_patterns(messages),
            'weekly_distribution': analyze_weekly_patterns(messages),
            'message_length_distribution': analyze_message_lengths(messages)
        }
        
        return patterns
        
    except Exception as e:
        logger.error(f"參與度模式分析錯誤: {e}")
        return {'error': str(e)}

def analyze_hourly_patterns(messages):
    """分析每小時的活動模式"""
    hourly_counts = defaultdict(int)
    for message in messages:
        hour = message.timestamp.hour
        hourly_counts[hour] += 1
    
    return dict(hourly_counts)

def analyze_weekly_patterns(messages):
    """分析每週的活動模式"""
    weekly_counts = defaultdict(int)
    for message in messages:
        weekday = message.timestamp.strftime('%A')
        weekly_counts[weekday] += 1
    
    return dict(weekly_counts)

def analyze_message_lengths(messages):
    """分析訊息長度分布"""
    lengths = [len(message.content) for message in messages]
    
    if not lengths:
        return {}
    
    return {
        'mean_length': round(sum(lengths) / len(lengths), 2),
        'min_length': min(lengths),
        'max_length': max(lengths),
        'std_length': calculate_std(lengths)
    }

def get_question_category_stats():
    """取得問題分類統計（簡化版本）"""
    try:
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ))
        
        stats = {
            'total_questions': len(analyses),
            'category_distribution': Counter(),
            'cognitive_levels': Counter(),
            'question_types': Counter(),
            'difficulty_levels': Counter()
        }
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                stats['category_distribution'][data.get('content_domain', 'Unknown')] += 1
                stats['cognitive_levels'][data.get('cognitive_level', 'Unknown')] += 1
                stats['question_types'][data.get('question_type', 'Unknown')] += 1
                stats['difficulty_levels'][data.get('difficulty', 'Unknown')] += 1
            except json.JSONDecodeError:
                continue
        
        # 轉換為字典
        for key in ['category_distribution', 'cognitive_levels', 'question_types', 'difficulty_levels']:
            stats[key] = dict(stats[key])
        
        return stats
        
    except Exception as e:
        logger.error(f"問題分類統計錯誤: {e}")
        return {'error': str(e)}

def generate_learning_progression_data():
    """生成學習進展資料"""
    try:
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ).order_by(Analysis.timestamp.asc()))
        
        if len(analyses) < 5:
            return {'status': 'insufficient_data'}
        
        # 按時間分組分析進展
        monthly_progression = defaultdict(lambda: {
            'total_questions': 0,
            'cognitive_levels': Counter(),
            'difficulty_levels': Counter()
        })
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                month_key = analysis.timestamp.strftime('%Y-%m')
                
                monthly_progression[month_key]['total_questions'] += 1
                monthly_progression[month_key]['cognitive_levels'][data.get('cognitive_level', 'Unknown')] += 1
                monthly_progression[month_key]['difficulty_levels'][data.get('difficulty', 'Unknown')] += 1
                
            except json.JSONDecodeError:
                continue
        
        # 轉換為可序列化的格式
        progression_data = {}
        for month, data in monthly_progression.items():
            progression_data[month] = {
                'total_questions': data['total_questions'],
                'cognitive_levels': dict(data['cognitive_levels']),
                'difficulty_levels': dict(data['difficulty_levels'])
            }
        
        return progression_data
        
    except Exception as e:
        logger.error(f"學習進展資料生成錯誤: {e}")
        return {'error': str(e)}

def analyze_student_cognitive_progression(analyses):
    """分析單一學生的認知進展"""
    try:
        if not analyses:
            return {'status': 'no_data'}
        
        progression = []
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                progression.append({
                    'date': analysis.timestamp.strftime('%Y-%m-%d'),
                    'cognitive_level': data.get('cognitive_level', 'Unknown'),
                    'difficulty': data.get('difficulty', 'Unknown')
                })
            except json.JSONDecodeError:
                continue
        
        return {
            'progression': progression,
            'total_analyses': len(progression)
        }
        
    except Exception as e:
        logger.error(f"學生認知進展分析錯誤: {e}")
        return {'error': str(e)}

def analyze_student_engagement_trend(messages):
    """分析學生參與度趨勢"""
    try:
        if not messages:
            return {'status': 'no_data'}
        
        # 按週統計訊息數量
        weekly_counts = defaultdict(int)
        for message in messages:
            week_key = message.timestamp.strftime('%Y-W%U')
            weekly_counts[week_key] += 1
        
        # 計算趨勢
        weeks = sorted(weekly_counts.keys())
        if len(weeks) >= 2:
            recent_avg = sum(weekly_counts[week] for week in weeks[-2:]) / 2
            early_avg = sum(weekly_counts[week] for week in weeks[:2]) / 2
            
            if recent_avg > early_avg * 1.2:
                trend = 'increasing'
            elif recent_avg < early_avg * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'weekly_counts': dict(weekly_counts),
            'trend': trend,
            'total_weeks': len(weeks)
        }
        
    except Exception as e:
        logger.error(f"學生參與度趨勢分析錯誤: {e}")
        return {'error': str(e)}

def generate_class_progress_summary(progress_data):
    """生成班級進度摘要"""
    try:
        if not progress_data:
            return {'status': 'no_data'}
        
        summary = {
            'total_students': len(progress_data),
            'avg_participation_rate': round(sum(p['participation_rate'] for p in progress_data) / len(progress_data), 2),
            'total_questions': sum(p['total_questions'] for p in progress_data),
            'total_messages': sum(p['total_messages'] for p in progress_data),
            'avg_learning_period': round(sum(p['learning_period_days'] for p in progress_data) / len(progress_data), 1),
            'active_students': len([p for p in progress_data if p['recent_activity'] > 0])
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"班級進度摘要生成錯誤: {e}")
        return {'error': str(e)}

def get_system_metrics():
    """取得系統指標"""
    try:
        return {
            'uptime_days': 30,  # 示例數據
            'total_api_calls': 1250,
            'avg_response_time_ms': 150,
            'error_rate_percentage': 0.2,
            'database_connections': 5
        }
        
    except Exception as e:
        logger.error(f"系統指標取得錯誤: {e}")
        return {'error': str(e)}
