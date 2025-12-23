#!/bin/bash
# 最適化の進捗を監視するスクリプト

LOG_FILE="rolling_full_year_new.log"

echo "=== 年間最適化 進捗監視 ==="
echo "ログファイル: $LOG_FILE"
echo ""

while true; do
    clear
    echo "=== 最適化進捗 ($(date '+%H:%M:%S')) ==="
    echo ""

    # 処理ステップ数を確認
    if [ -f "$LOG_FILE" ]; then
        PROGRESS=$(grep -o "Progress: Step [0-9]*/[0-9]*" "$LOG_FILE" | tail -1)
        if [ -n "$PROGRESS" ]; then
            echo "現在の進捗: $PROGRESS"
        fi

        # 最新の最適化結果
        echo ""
        echo "--- 最近の目的関数値 ---"
        grep "Primal Bound" "$LOG_FILE" | tail -5 | awk '{print $4}'

        # ファイルサイズ
        echo ""
        echo "ログサイズ: $(du -h $LOG_FILE | cut -f1)"

        # 最終行
        echo ""
        echo "--- 最新のログ ---"
        tail -3 "$LOG_FILE"
    else
        echo "ログファイルが見つかりません"
    fi

    echo ""
    echo "Press Ctrl+C to exit"
    sleep 5
done
