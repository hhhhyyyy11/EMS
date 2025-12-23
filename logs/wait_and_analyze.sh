#!/bin/bash
# 1年分の最適化が完了するまで待機し、完了後に分析を実行

echo "=========================================="
echo "  1年分最適化実行の監視開始"
echo "=========================================="
echo ""

# 完了を待つ
while ps aux | grep -q "[p]ython rolling_opt.py.*17520"; do
    echo "$(date '+%H:%M:%S') - 実行中..."
    sleep 30
done

echo ""
echo "✓ 最適化完了！"
echo ""

# 結果を分析
if [ -f rolling_results.csv ]; then
    echo "=========================================="
    echo "  結果分析"
    echo "=========================================="
    echo ""

    python3 << 'PYEOF'
import pandas as pd
import numpy as np

df = pd.read_csv('rolling_results.csv')
df['pv_curtailed'] = df['pv_kW'] - df['pv_used_kW']

print('【基本統計】')
print(f'総ステップ数: {len(df):,}')
print(f'期間: {df["timestamp"].min()} ~ {df["timestamp"].max()}')
print()

print('【最適化結果】')
optimal_count = (df['status'] == 'optimal').sum()
infeasible_count = (df['status'] == 'infeasible').sum()
print(f'Optimal: {optimal_count:,} ({optimal_count/len(df)*100:.2f}%)')
print(f'Infeasible: {infeasible_count:,} ({infeasible_count/len(df)*100:.2f}%)')
print()

print('【PV利用状況】')
total_pv_gen = (df['pv_kW'] * 0.5).sum()
total_pv_used = (df['pv_used_kW'] * 0.5).sum()
total_pv_curtailed = (df['pv_curtailed'] * 0.5).sum()
print(f'総PV発電量: {total_pv_gen:,.0f} kWh')
print(f'総PV使用量: {total_pv_used:,.0f} kWh ({total_pv_used/total_pv_gen*100:.1f}%)')
print(f'総PV抑制量: {total_pv_curtailed:,.0f} kWh ({total_pv_curtailed/total_pv_gen*100:.1f}%)')
print()

print('【買電・契約電力】')
max_buy = df['sBY'].max()
total_buy = (df['sBY'] * 0.5).sum()
print(f'最大買電電力: {max_buy:.2f} kW')
print(f'総買電量: {total_buy:,.0f} kWh')
print()

print('【月別infeasible発生状況】')
if infeasible_count > 0:
    df['month'] = pd.to_datetime(df['timestamp']).dt.month
    inf_df = df[df['status'] == 'infeasible']
    monthly_inf = inf_df.groupby('month').size()
    print(monthly_inf.to_string())
else:
    print('✓ Infeasibleは1件も発生していません！')
print()

print('=' * 50)
print('✓ 分析完了')
print('=' * 50)
PYEOF

else
    echo "エラー: rolling_results.csv が見つかりません"
fi
