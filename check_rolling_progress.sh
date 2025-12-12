#!/bin/bash
LOG_FILE="logs/rolling_48h_20251106_145405.log"
while true; do
    clear
    echo "=== 48時間予測ローリング最適化 進捗状況 ==="
    echo "ログファイル: $LOG_FILE"
    echo "----------------------------------------"
    tail -5 "$LOG_FILE" | grep -E "(Progress|Step|Completed)" || tail -3 "$LOG_FILE"
    echo "----------------------------------------"
    echo "最終更新: $(date)"
    echo "Ctrl+C で終了"
    sleep 10
done
