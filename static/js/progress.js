// ===== 進度提示系統 =====
class ProgressManager {
    constructor() {
        this.modal = null;
        this.progressBar = null;
        this.titleElement = null;
        this.messageElement = null;
        this.createModal();
    }
    
    createModal() {
        // 建立進度模態視窗
        this.modal = document.createElement('div');
        this.modal.className = 'progress-modal';
        this.modal.style.display = 'none';
        
        const content = document.createElement('div');
        content.className = 'progress-content';
        
        this.titleElement = document.createElement('h3');
        this.titleElement.style.marginBottom = '1rem';
        
        this.messageElement = document.createElement('p');
        this.messageElement.style.marginBottom = '1rem';
        this.messageElement.style.color = 'var(--gray-600)';
        
        const progressContainer = document.createElement('div');
        progressContainer.className = 'progress-bar';
        
        this.progressBar = document.createElement('div');
        this.progressBar.className = 'progress-fill';
        this.progressBar.style.width = '0%';
        
        progressContainer.appendChild(this.progressBar);
        content.appendChild(this.titleElement);
        content.appendChild(this.messageElement);
        content.appendChild(progressContainer);
        this.modal.appendChild(content);
        
        document.body.appendChild(this.modal);
    }
    
    show(title, message, progress = 0) {
        this.titleElement.textContent = title;
        this.messageElement.textContent = message;
        this.progressBar.style.width = progress + '%';
        this.modal.style.display = 'flex';
        
        // 添加淡入動畫
        this.modal.style.opacity = '0';
        setTimeout(() => {
            this.modal.style.opacity = '1';
            this.modal.style.transition = 'opacity 0.3s ease-in-out';
        }, 10);
    }
    
    update(message, progress) {
        this.messageElement.textContent = message;
        this.progressBar.style.width = progress + '%';
    }
    
    hide() {
        this.modal.style.opacity = '0';
        setTimeout(() => {
            this.modal.style.display = 'none';
        }, 300);
    }
}

// 全域進度管理器
let progressManager;

// 初始化進度管理器
document.addEventListener('DOMContentLoaded', function() {
    progressManager = new ProgressManager();
});

// ===== 進度提示函數 =====
function showProgress(title, message, progress = 0) {
    if (!progressManager) {
        progressManager = new ProgressManager();
    }
    progressManager.show(title, message, progress);
}

function updateProgress(message, progress) {
    if (progressManager) {
        progressManager.update(message, progress);
    }
}

function hideProgress() {
    if (progressManager) {
        progressManager.hide();
    }
}

// ===== 下載功能 =====
function downloadWithProgress(url, filename, progressTitle = '下載中') {
    showProgress(progressTitle, '準備下載...', 0);
    
    // 模擬下載進度
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) {
            progress = 90;
        }
        updateProgress('正在下載...', progress);
    }, 200);
    
    // 實際下載邏輯
    fetch(url, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('下載失敗');
        }
        return response.blob();
    })
    .then(blob => {
        clearInterval(interval);
        updateProgress('下載完成！', 100);
        
        // 建立下載連結
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        setTimeout(() => {
            hideProgress();
            showSuccess('檔案下載完成');
        }, 1000);
    })
    .catch(error => {
        clearInterval(interval);
        console.error('下載錯誤:', error);
        hideProgress();
        showError('下載失敗，請重試');
    });
}

function downloadStudentQuestions(studentId) {
    const url = `/students/${studentId}/download-questions`;
    const filename = `student_${studentId}_questions.tsv`;
    downloadWithProgress(url, filename, '下載學生提問');
}

// ===== 通知系統 =====
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // 設定樣式
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '1rem 1.5rem',
        borderRadius: '0.5rem',
        color: 'white',
        fontWeight: '500',
        zIndex: '3000',
        transform: 'translateX(100%)',
        transition: 'transform 0.3s ease-in-out',
        maxWidth: '300px',
        wordWrap: 'break-word'
    });
    
    // 設定顏色
    switch (type) {
        case 'success':
            notification.style.backgroundColor = 'var(--success-color)';
            break;
        case 'error':
            notification.style.backgroundColor = 'var(--error-color)';
            break;
        case 'warning':
            notification.style.backgroundColor = 'var(--warning-color)';
            break;
        default:
            notification.style.backgroundColor = 'var(--info-color)';
    }
    
    document.body.appendChild(notification);
    
    // 滑入動畫
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    // 自動消失
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, duration);
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showWarning(message) {
    showNotification(message, 'warning');
}

function showInfo(message) {
    showNotification(message, 'info');
}

// ===== 簡易圖表功能 =====
function createSimpleChart(canvasId, data, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const { labels, values } = data;
    const { type = 'bar', color = '#667eea' } = options;
    
    // 清除畫布
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const padding = 40;
    const chartWidth = canvas.width - 2 * padding;
    const chartHeight = canvas.height - 2 * padding;
    
    if (type === 'bar') {
        const maxValue = Math.max(...values);
        const barWidth = chartWidth / labels.length * 0.6;
        const barSpacing = chartWidth / labels.length;
        
        // 繪製柱狀圖
        values.forEach((value, index) => {
            const barHeight = (value / maxValue) * chartHeight;
            const x = padding + index * barSpacing + (barSpacing - barWidth) / 2;
            const y = padding + chartHeight - barHeight;
            
            // 繪製柱子
            ctx.fillStyle = color;
            ctx.fillRect(x, y, barWidth, barHeight);
            
            // 繪製標籤
            ctx.fillStyle = '#4a5568';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(labels[index], x + barWidth / 2, canvas.height - 15);
            
            // 繪製數值
            ctx.fillText(value.toString(), x + barWidth / 2, y - 5);
        });
    }
}
