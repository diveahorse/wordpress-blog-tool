// メインのJavaScriptファイル

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
    console.log('WordPressブログ管理ツールが読み込まれました');
    
    // ツールチップの初期化
    initializeTooltips();
    
    // フォームのバリデーション
    initializeFormValidation();
    
    // アニメーション効果
    initializeAnimations();
    
    // ダークモード切り替え（オプション）
    initializeDarkMode();
});

// ツールチップの初期化
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// フォームのバリデーション
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

// アニメーション効果の初期化
function initializeAnimations() {
    // スクロール時のフェードイン効果
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // アニメーション対象の要素を監視
    document.querySelectorAll('.card, .btn, .alert').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

// ダークモード切り替え（オプション）
function initializeDarkMode() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            const isDarkMode = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDarkMode);
            
            // アイコンの切り替え
            const icon = this.querySelector('i');
            if (isDarkMode) {
                icon.className = 'fas fa-sun';
            } else {
                icon.className = 'fas fa-moon';
            }
        });
        
        // 保存された設定を復元
        const savedDarkMode = localStorage.getItem('darkMode');
        if (savedDarkMode === 'true') {
            document.body.classList.add('dark-mode');
            const icon = darkModeToggle.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-sun';
            }
        }
    }
}

// ユーティリティ関数

// 日付のフォーマット
function formatDate(date) {
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(date).toLocaleDateString('ja-JP', options);
}

// ファイルサイズのフォーマット
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 成功メッセージの表示
function showSuccess(message, duration = 5000) {
    showNotification(message, 'success', duration);
}

// エラーメッセージの表示
function showError(message, duration = 5000) {
    showNotification(message, 'danger', duration);
}

// 警告メッセージの表示
function showWarning(message, duration = 5000) {
    showNotification(message, 'warning', duration);
}

// 通知メッセージの表示
function showNotification(message, type = 'info', duration = 5000) {
    // 既存の通知を削除
    const existingNotifications = document.querySelectorAll('.custom-notification');
    existingNotifications.forEach(notification => notification.remove());
    
    // 新しい通知を作成
    const notification = document.createElement('div');
    notification.className = `custom-notification alert alert-${type} alert-dismissible fade show`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border-radius: 8px;
        border: none;
    `;
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // 自動削除
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
}

// 確認ダイアログの表示
function showConfirmDialog(message, onConfirm, onCancel = null) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.setAttribute('tabindex', '-1');
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">確認</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
                    <button type="button" class="btn btn-primary confirm-btn">確認</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
    
    // 確認ボタンのイベント
    modal.querySelector('.confirm-btn').addEventListener('click', function() {
        modalInstance.hide();
        if (onConfirm) onConfirm();
    });
    
    // モーダルが閉じられたときの処理
    modal.addEventListener('hidden.bs.modal', function() {
        if (onCancel) onCancel();
        modal.remove();
    });
}

// ローディング状態の管理
function showLoading(element, text = '読み込み中...') {
    const originalContent = element.innerHTML;
    element.disabled = true;
    element.innerHTML = `<span class="loading-spinner me-2"></span>${text}`;
    element.dataset.originalContent = originalContent;
}

function hideLoading(element) {
    if (element.dataset.originalContent) {
        element.innerHTML = element.dataset.originalContent;
        element.disabled = false;
        delete element.dataset.originalContent;
    }
}

// テーブルのソート機能
function initializeTableSorting() {
    const tables = document.querySelectorAll('.sortable-table');
    
    tables.forEach(table => {
        const headers = table.querySelectorAll('th[data-sort]');
        
        headers.forEach(header => {
            header.addEventListener('click', function() {
                const column = this.dataset.sort;
                const direction = this.dataset.direction === 'asc' ? 'desc' : 'asc';
                
                // 他のヘッダーのソート状態をリセット
                headers.forEach(h => {
                    h.dataset.direction = '';
                    h.classList.remove('sort-asc', 'sort-desc');
                });
                
                // 現在のヘッダーのソート状態を設定
                this.dataset.direction = direction;
                this.classList.add(direction === 'asc' ? 'sort-asc' : 'sort-desc');
                
                // テーブルをソート
                sortTable(table, column, direction);
            });
        });
    });
}

// テーブルのソート実行
function sortTable(table, column, direction) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aValue = a.querySelector(`td[data-${column}]`).dataset[column];
        const bValue = b.querySelector(`td[data-${column}]`).dataset[column];
        
        if (direction === 'asc') {
            return aValue.localeCompare(bValue, 'ja');
        } else {
            return bValue.localeCompare(aValue, 'ja');
        }
    });
    
    // ソートされた行を再配置
    rows.forEach(row => tbody.appendChild(row));
}

// 検索機能
function initializeSearch() {
    const searchInputs = document.querySelectorAll('.search-input');
    
    searchInputs.forEach(input => {
        input.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const table = this.closest('.card').querySelector('table');
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });
}

// エクスポート機能
function exportTableToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    const rows = table.querySelectorAll('tr');
    let csv = [];
    
    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const rowData = [];
        cols.forEach(col => {
            rowData.push('"' + col.textContent.replace(/"/g, '""') + '"');
        });
        csv.push(rowData.join(','));
    });
    
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// ページ読み込み完了時の処理
window.addEventListener('load', function() {
    // テーブルのソート機能を初期化
    initializeTableSorting();
    
    // 検索機能を初期化
    initializeSearch();
    
    console.log('すべてのリソースが読み込まれました');
});
