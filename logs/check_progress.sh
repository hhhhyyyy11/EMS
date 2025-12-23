#!/bin/bash
while true; do
    clear
    echo "========================================"
    echo "  最適化実行状況（1年分 17,520ステップ）"
    echo "========================================"
    echo ""
    
    # 最新の進捗を表示
    if [ -f rolling_full_year.log ]; then
        echo "【最新の進捗】"
        grep "Progress:" rolling_full_year.log | tail -5
        echo ""
        
        # 完了チェック
        if grep -q "Completed:" rolling_full_year.log; then
            echo "✓ 最適化完了！"
            echo ""
            grep "Completed:" rolling_full_year.log
            echo ""
            tail -20 rolling_full_year.log
            break
        fi
        
        # infeasible発生チェック
        infeasible_count=$(grep -c "status=infeasible" rolling_full_year.log 2>/dev/null || echo "0")
        echo "Infeasible発生数: $infeasible_count"
        echo ""
        echo "次の更新まで 10秒..."
    else
        echo "ログファイルが見つかりません"
    fi
    
    sleep 10
done
