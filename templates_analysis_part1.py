# templates_analysis_part1.py - 教師分析後台模板

# 教師分析後台模板
TEACHING_INSIGHTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 教師分析後台 - EMI 智能教學助理</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            text-align: center;
        }
        
        .header h1 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 2.5em;
        }
        
        .quick-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .primary { color: #3498db; }
        .success { color: #27ae60; }
        .warning { color: #f39c12; }
        .danger { color: #e74c3c; }
        
        .stat-trend {
            font-size: 0.8em;
            margin-top: 8px;
        }
        
        .trend-up { color: #27ae60; }
        .trend-down { color: #e74c3c; }
        .trend-stable { color: #f39c12; }
        
        .tabs-container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
            overflow: hidden;
        }
        
        .tabs-nav {
            display: flex;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            flex-wrap: wrap;
        }
        
        .tab-btn {
            flex: 1;
            padding: 20px;
            border: none;
            background: transparent;
            color: #6c757d;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            min-width: 150px;
        }
        
        .tab-btn:hover {
            background: #e9ecef;
            color: #495057;
        }
        
        .tab-btn.active {
            background: white;
            color: #3498db;
            border-bottom: 3px solid #3498db;
        }
        
        .tab-content {
            padding: 30px;
            min-height: 500px;
        }
        
        .tab-pane {
            display: none;
        }
        
        .tab-pane.active {
            display: block;
        }
        
        .chart-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .chart-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .chart-title {
            font-size: 1.2em;
            color: #2c3e50;
            margin-bottom: 20px;
            text-align: center;
            font-weight: 600;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
        }
        
        .insights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .insight-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #3498db;
        }
        
        .insight-title {
            font-size: 1.1em;
            color: #2c3e50;
            margin-bottom: 15px;
            font-weight: 600;
        }
        
        .insight-content {
            color: #7f8c8d;
            line-height: 1.6;
        }
        
        .insight-metric {
            font-size: 1.8em;
            font-weight: bold;
            color: #3498db;
            margin: 10px 0;
        }
        
        .student-performance-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .student-performance-table th {
            background: #3498db;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        
        .student-performance-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        
        .student-performance-table tr:hover {
            background: #f8f9fa;
        }
        
        .performance-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            text-align: center;
        }
        
        .badge-excellent { background: #d4edda; color: #155724; }
        .badge-good { background: #d1ecf1; color: #0c5460; }
        .badge-average { background: #fff3cd; color: #856404; }
        .badge-needs-attention { background: #f8d7da; color: #721c24; }
        
        .action-buttons {
            display: flex;
            gap: 15px;
            margin-top: 30px;
            flex-wrap: wrap;
        }
        
        .action-btn {
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary { background: linear-gradient(135deg, #3498db, #2980b9); color: white; }
        .btn-success { background: linear-gradient(135deg, #27ae60, #2ecc71); color: white; }
        .btn-warning { background: linear-gradient(135deg, #f39c12, #e67e22); color: white; }
        .btn-info { background: linear-gradient(135deg, #17a2b8, #138496); color: white; }
        
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        }
        
        .recommendations-list {
            list-style: none;
            padding: 0;
        }
        
        .recommendation-item {
            background: #f8f9fa;
            padding: 20px;
            margin: 15px 0;
            border-radius: 10px;
            border-left: 4px solid #3498db;
            transition: all 0.3s ease;
        }
        
        .recommendation-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        
        .recommendation-title {
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 8px;
        }
        
        .recommendation-desc {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .back-btn {
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            padding: 12px 20px;
            border-radius: 25px;
            text-decoration: none;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .back-btn:hover {
            background: white;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid;
        }
        
        .alert-info {
            background: #d1ecf1;
            border-left-color: #17a2b8;
            color: #0c5460;
        }
        
        @media (max-width: 768px) {
            .tabs-nav {
                flex-direction: column;
            }
            
            .tab-btn {
                min-width: auto;
            }
            
            .chart-section {
                grid-template-columns: 1fr;
            }
            
            .action-buttons {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <a href="/" class="back-btn">← 返回首頁</a>
    
    <div class="container">
        <!-- 頁面標題 -->
        <div class="header">
            <h1>📊 教師分析後台</h1>
            <p>深度了解學生學習狀況，優化教學策略</p>
        </div>
        
        <!-- 快速統計 -->
        <div class="quick-stats">
            <div class="stat-card">
                <div class="stat-value primary">{{ category_stats.grammar_questions or 45 }}</div>
                <div class="stat-label">文法問題</div>
                <div class="stat-trend trend-up">↗ +12% 本週</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value success">{{ category_stats.vocabulary_questions or 32 }}</div>
                <div class="stat-label">詞彙問題</div>
                <div class="stat-trend trend-stable">→ 持平</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value warning">{{ category_stats.pronunciation_questions or 18 }}</div>
                <div class="stat-label">發音問題</div>
                <div class="stat-trend trend-down">↘ -5% 本週</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value danger">{{ engagement_analysis.daily_average or 78 }}%</div>
                <div class="stat-label">平均參與度</div>
                <div class="stat-trend trend-up">↗ +{{ engagement_analysis.weekly_trend or 5 }}% 本週</div>
            </div>
        </div>
        
        <!-- 標籤式分析介面 -->
        <div class="tabs-container">
            <div class="tabs-nav">
                <button class="tab-btn active" data-tab="overview">📈 總覽分析</button>
                <button class="tab-btn" data-tab="students">👥 學生表現</button>
                <button class="tab-btn" data-tab="content">📚 內容分析</button>
                <button class="tab-btn" data-tab="engagement">🎯 參與度</button>
                <button class="tab-btn" data-tab="recommendations">💡 建議</button>
            </div>
            
            <div class="tab-content">
                <!-- 總覽分析標籤 -->
                <div class="tab-pane active" id="overview">
                    <div class="chart-section">
                        <div class="chart-card">
                            <div class="chart-title">問題類型分布</div>
                            <div class="chart-container">
                                <canvas id="questionTypesChart"></canvas>
                            </div>
                        </div>
                        
                        <div class="chart-card">
                            <div class="chart-title">每日活動趨勢</div>
                            <div class="chart-container">
                                <canvas id="dailyActivityChart"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="insights-grid">
                        <div class="insight-card">
                            <div class="insight-title">🔥 熱門時段</div>
                            <div class="insight-content">
                                學生最活躍的時間段：
                                <ul style="margin: 10px 0; padding-left: 20px;">
                                    {% for hour in engagement_analysis.peak_hours or ['10:00-11:00', '14:00-15:00', '19:00-20:00'] %}
                                    <li>{{ hour }}</li>
                                    {% endfor %}
                                </ul>
                                建議在這些時段安排重要教學內容。
                            </div>
                        </div>
                        
                        <div class="insight-card">
                            <div class="insight-title">📊 學習模式</div>
                            <div class="insight-content">
                                學生傾向於：
                                <br>• 在文法問題上花費更多時間
                                <br>• 對實際應用場景更感興趣
                                <br>• 需要更多發音練習機會
                            </div>
                        </div>
                        
                        <div class="insight-card">
                            <div class="insight-title">⚡ 即時狀態</div>
                            <div class="insight-content">
                                目前有 <span class="insight-metric">{{ stats.active_students or 12 }}</span> 位學生在線
                                <br>平均回應時間：<strong>{{ stats.avg_response_time or '2.3' }} 秒</strong>
                                <br>系統負載：<strong>{{ stats.system_load or '正常' }}</strong>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 學生表現標籤 -->
                <div class="tab-pane" id="students">
                    <div class="alert alert-info">
                        <strong>提示：</strong> 點擊學生姓名可查看詳細分析報告
                    </div>
                    
                    <table class="student-performance-table">
                        <thead>
                            <tr>
                                <th>學生姓名</th>
                                <th>參與度</th>
                                <th>問題數量</th>
                                <th>學習進度</th>
                                <th>表現評級</th>
                                <th>最後活動</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for student in students or [] %}
                            <tr>
                                <td><a href="/student/{{ student.id }}" style="color: #3498db; text-decoration: none;">{{ student.name }}</a></td>
                                <td>{{ student.engagement }}%</td>
                                <td>{{ student.questions_count }}</td>
                                <td>{{ student.progress }}%</td>
                                <td>
                                    <span class="performance-badge badge-{{ student.performance_level }}">
                                        {{ student.performance_text }}
                                    </span>
                                </td>
                                <td>{{ student.last_active }}</td>
                            </tr>
                            {% else %}
                            <!-- 示範資料 -->
                            <tr>
                                <td><a href="/student/1" style="color: #3498db; text-decoration: none;">王小明</a></td>
                                <td>85%</td>
                                <td>32</td>
                                <td>78%</td>
                                <td><span class="performance-badge badge-excellent">優秀</span></td>
                                <td>2 小時前</td>
                            </tr>
                            <tr>
                                <td><a href="/student/2" style="color: #3498db; text-decoration: none;">李小華</a></td>
                                <td>72%</td>
                                <td>28</td>
                                <td>65%</td>
                                <td><span class="performance-badge badge-good">良好</span></td>
                                <td>5 小時前</td>
                            </tr>
                            <tr>
                                <td><a href="/student/3" style="color: #3498db; text-decoration: none;">張美玲</a></td>
                                <td>68%</td>
                                <td>24</td>
                                <td>72%</td>
                                <td><span class="performance-badge badge-good">良好</span></td>
                                <td>1 天前</td>
                            </tr>
                            <tr>
                                <td><a href="/student/4" style="color: #3498db; text-decoration: none;">陳大偉</a></td>
                                <td>45%</td>
                                <td>15</td>
                                <td>52%</td>
                                <td><span class="performance-badge badge-needs-attention">需關注</span></td>
                                <td>3 天前</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                
                <!-- 內容分析標籤 -->
                <div class="tab-pane" id="content">
                    <div class="chart-section">
                        <div class="chart-card">
                            <div class="chart-title">學習主題熱度</div>
                            <div class="chart-container">
                                <canvas id="topicsChart"></canvas>
                            </div>
                        </div>
                        
                        <div class="chart-card">
                            <div class="chart-title">難度分布</div>
                            <div class="chart-container">
                                <canvas id="difficultyChart"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="insights-grid">
                        <div class="insight-card">
                            <div class="insight-title">📖 熱門主題</div>
                            <div class="insight-content">
                                1. 現在完成式 (32 次詢問)
                                <br>2. 被動語態 (28 次詢問)
                                <br>3. 條件句 (24 次詢問)
                                <br>4. 商業英文 (19 次詢問)
                                <br>5. 學術寫作 (15 次詢問)
                            </div>
                        </div>
                        
                        <div class="insight-card">
                            <div class="insight-title">🎯 學習重點</div>
                            <div class="insight-content">
                                學生在以下領域需要加強：
                                <br>• <strong>語法應用</strong> - 理論理解良好，實際運用待加強
                                <br>• <strong>口語表達</strong> - 需要更多練習機會
                                <br>• <strong>文化理解</strong> - 跨文化溝通技巧
                            </div>
                        </div>
                        
                        <div class="insight-card">
                            <div class="insight-title">📈 進步趨勢</div>
                            <div class="insight-content">
                                整體學習成效：
                                <div class="insight-metric">+15%</div>
                                相較上月進步顯著，建議持續目前教學策略
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 參與度標籤 -->
                <div class="tab-pane" id="engagement">
                    <div class="chart-section">
                        <div class="chart-card">
                            <div class="chart-title">每週參與度變化</div>
                            <div class="chart-container">
                                <canvas id="weeklyEngagementChart"></canvas>
                            </div>
                        </div>
                        
                        <div class="chart-card">
                            <div class="chart-title">互動類型分析</div>
                            <div class="chart-container">
                                <canvas id="interactionTypesChart"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="insights-grid">
                        <div class="insight-card">
                            <div class="insight-title">💬 對話品質</div>
                            <div class="insight-content">
                                平均對話輪次：<span class="insight-metric">4.2</span>
                                <br>深度問題比例：<strong>68%</strong>
                                <br>學生滿意度：<strong>4.6/5.0</strong>
                            </div>
                        </div>
                        
                        <div class="insight-card">
                            <div class="insight-title">⏱️ 使用模式</div>
                            <div class="insight-content">
                                • 平均會話時長：<strong>12 分鐘</strong>
                                <br>• 週末使用率：<strong>45%</strong>
                                <br>• 重複訪問率：<strong>82%</strong>
                                <br>• 問題解決率：<strong>91%</strong>
                            </div>
                        </div>
                        
                        <div class="insight-card">
                            <div class="insight-title">🎉 參與亮點</div>
                            <div class="insight-content">
                                • 本週新增 5 位活躍學生
                                <br>• 平均問題深度提升 23%
                                <br>• 學生自主學習時間增加
                                <br>• 跨文化交流討論增多
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 建議標籤 -->
                <div class="tab-pane" id="recommendations">
                    <div class="alert alert-info">
                        <strong>系統建議：</strong> 基於 AI 分析為您提供個人化教學建議
                    </div>
                    
                    <ul class="recommendations-list">
                        <li class="recommendation-item">
                            <div class="recommendation-title">🎯 加強文法實踐</div>
                            <div class="recommendation-desc">
                                學生對文法概念理解良好，但在實際應用中仍有困難。建議增加情境練習和案例分析。
                            </div>
                        </li>
                        
                        <li class="recommendation-item">
                            <div class="recommendation-title">🗣️ 增加口語練習</div>
                            <div class="recommendation-desc">
                                發音問題詢問較少，可能表示學生缺乏口語練習機會。建議安排更多對話練習時間。
                            </div>
                        </li>
                        
                        <li class="recommendation-item">
                            <div class="recommendation-title">📱 優化學習時段</div>
                            <div class="recommendation-desc">
                                根據參與度分析，建議在 10:00-11:00 和 14:00-15:00 安排重要課程內容。
                            </div>
                        </li>
                        
                        <li class="recommendation-item">
                            <div class="recommendation-title">🌍 強化文化教學</div>
                            <div class="recommendation-desc">
                                跨文化相關問題較少，建議在課程中加入更多文化背景介紹和討論。
                            </div>
                        </li>
                        
                        <li class="recommendation-item">
                            <div class="recommendation-title">📊 個別化關注</div>
                            <div class="recommendation-desc">
                                有 3 位學生參與度較低，建議進行個別關懷和學習輔導。
                            </div>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- 行動按鈕 -->
        <div class="action-buttons">
            <a href="/conversation-summaries" class="action-btn btn-primary">
                📝 查看對話摘要
            </a>
            <a href="/learning-recommendations" class="action-btn btn-success">
                🎯 個人化建議
            </a>
            <a href="/storage-management" class="action-btn btn-warning">
                💾 儲存管理
            </a>
            <a href="/data-export" class="action-btn btn-info">
                📊 匯出報告
            </a>
        </div>
    </div>
    
    <script>
        // 標籤切換功能
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                
                this.classList.add('active');
                const tabId = this.dataset.tab;
                document.getElementById(tabId).classList.add('active');
                
                setTimeout(() => loadChartsForTab(tabId), 100);
            });
        });
        
        // 圖表配置
        const chartColors = {
            primary: '#3498db',
            success: '#27ae60',
            warning: '#f39c12',
            danger: '#e74c3c',
            info: '#17a2b8',
            purple: '#9b59b6'
        };
        
        // 問題類型分布圖
        function createQuestionTypesChart() {
            const ctx = document.getElementById('questionTypesChart');
            if (!ctx) return;
            
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['文法問題', '詞彙問題', '發音問題', '文化問題'],
                    datasets: [{
                        data: [
                            {{ category_stats.grammar_questions or 45 }},
                            {{ category_stats.vocabulary_questions or 32 }},
                            {{ category_stats.pronunciation_questions or 18 }},
                            {{ category_stats.cultural_questions or 12 }}
                        ],
                        backgroundColor: [
                            chartColors.primary,
                            chartColors.success,
                            chartColors.warning,
                            chartColors.danger
                        ],
                        borderWidth: 3,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true
                            }
                        }
                    }
                }
            });
        }
        
        // 每日活動趨勢圖
        function createDailyActivityChart() {
            const ctx = document.getElementById('dailyActivityChart');
            if (!ctx) return;
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['週一', '週二', '週三', '週四', '週五', '週六', '週日'],
                    datasets: [{
                        label: '活動次數',
                        data: [65, 78, 90, 84, 92, 45, 38],
                        borderColor: chartColors.primary,
                        backgroundColor: chartColors.primary + '20',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#f8f9fa' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
        
        // 其他圖表函數
        function createTopicsChart() {
            const ctx = document.getElementById('topicsChart');
            if (!ctx) return;
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['現在完成式', '被動語態', '條件句', '商業英文', '學術寫作'],
                    datasets: [{
                        label: '詢問次數',
                        data: [32, 28, 24, 19, 15],
                        backgroundColor: [
                            chartColors.primary,
                            chartColors.success,
                            chartColors.warning,
                            chartColors.danger,
                            chartColors.info
                        ],
                        borderRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#f8f9fa' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
        
        function createDifficultyChart() {
            const ctx = document.getElementById('difficultyChart');
            if (!ctx) return;
            
            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['基礎', '中級', '進階', '專業'],
                    datasets: [{
                        data: [35, 40, 20, 5],
                        backgroundColor: [
                            chartColors.success,
                            chartColors.primary,
                            chartColors.warning,
                            chartColors.danger
                        ],
                        borderWidth: 3,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { padding: 20, usePointStyle: true }
                        }
                    }
                }
            });
        }
        
        function createWeeklyEngagementChart() {
            const ctx = document.getElementById('weeklyEngagementChart');
            if (!ctx) return;
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['第1週', '第2週', '第3週', '第4週', '第5週', '第6週', '第7週', '第8週'],
                    datasets: [{
                        label: '參與度 (%)',
                        data: [65, 68, 72, 78, 75, 82, 85, 88],
                        borderColor: chartColors.success,
                        backgroundColor: chartColors.success + '20',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, max: 100, grid: { color: '#f8f9fa' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
        
        function createInteractionTypesChart() {
            const ctx = document.getElementById('interactionTypesChart');
            if (!ctx) return;
            
            new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: ['提問', '回答', '討論', '練習', '測驗', '反饋'],
                    datasets: [{
                        label: '互動頻率',
                        data: [85, 72, 68, 90, 45, 78],
                        borderColor: chartColors.purple,
                        backgroundColor: chartColors.purple + '20',
                        borderWidth: 2,
                        pointBackgroundColor: chartColors.purple,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: '#f8f9fa' },
                            pointLabels: { font: { size: 12 } }
                        }
                    }
                }
            });
        }
        
        // 根據標籤載入對應圖表
        function loadChartsForTab(tabId) {
            switch(tabId) {
                case 'overview':
                    createQuestionTypesChart();
                    createDailyActivityChart();
                    break;
                case 'content':
                    createTopicsChart();
                    createDifficultyChart();
                    break;
                case 'engagement':
                    createWeeklyEngagementChart();
                    createInteractionTypesChart();
                    break;
            }
        }
        
        // 初始載入
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(() => {
                createQuestionTypesChart();
                createDailyActivityChart();
            }, 500);
        });
        
        // 即時數據更新
        setInterval(() => {
            fetch('/api/dashboard-stats')
                .then(response => response.json())
                .then(data => console.log('統計數據已更新', data))
                .catch(error => console.error('數據更新失敗:', error));
        }, 30000);
    </script>
</body>
</html>
"""

def get_template(template_name):
    """取得模板"""
    templates = {
        'teaching_insights.html': TEACHING_INSIGHTS_TEMPLATE,
    }
    return templates.get(template_name, '')

# 匯出
__all__ = ['TEACHING_INSIGHTS_TEMPLATE', 'get_template']
