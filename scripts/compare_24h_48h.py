#!/usr/bin/env python3
"""
24時間予測と48時間予測の結果を比較するスクリプト
"""
import pandas as pd
import numpy as np

print("=" * 80)
print("24時間予測 vs 48時間予測の比較分析")
print("=" * 80)

# 結果を読み込み（現在のresults/はarchive/に24時間版を保存済みと仮定）
# 48時間予測の結果
df_48h = pd.read_csv('results/rolling_results.csv')

# 3月7日のデータを抽出
march_7_48h = df_48h[df_48h['timestamp'].str.startswith('2024-03-07')].copy()

print("\n" + "=" * 80)
print("【48時間予測】3月7日の運用パターン")
print("=" * 80)

pv_total_48h = march_7_48h['pv_kW'].sum() * 0.5
pv_used_48h = march_7_48h['pv_used_kW'].sum() * 0.5
pv_surplus_48h = march_7_48h['pv_surplus_kW'].sum() * 0.5
surplus_rate_48h = (pv_surplus_48h / pv_total_48h * 100) if pv_total_48h > 0 else 0

print(f"\nPV発電可能量: {pv_total_48h:.2f} kWh")
print(f"PV使用量:     {pv_used_48h:.2f} kWh")
print(f"PV余剰量:     {pv_surplus_48h:.2f} kWh (余剰率 {surplus_rate_48h:.1f}%)")
print(f"総需要:       {march_7_48h['demand_kW'].sum() * 0.5:.2f} kWh")
print(f"総買電:       {march_7_48h['sBY'].sum() * 0.5:.2f} kWh")
print(f"最大買電:     {march_7_48h['sBY'].max():.2f} kW")

print(f"\nSOC統計:")
print(f"  最小SOC:    {march_7_48h['bF'].min():.2f} kWh")
print(f"  最大SOC:    {march_7_48h['bF'].max():.2f} kWh")
print(f"  平均SOC:    {march_7_48h['bF'].mean():.2f} kWh")
print(f"  満充電回数: {(march_7_48h['bF'] >= 859.9).sum()} 回")

# 12:00〜16:00の詳細
print("\n" + "=" * 80)
print("12:00〜16:00の詳細（24時間予測ではPV余剰が多かった時間帯）")
print("=" * 80)

noon_period_48h = march_7_48h[(march_7_48h['timestamp'] >= '2024-03-07 12:00:00') &
                               (march_7_48h['timestamp'] <= '2024-03-07 16:00:00')]

print(f"\n{'時刻':<8} {'PV発電':>8} {'需要':>8} {'買電':>8} {'充電':>8} {'放電':>8} {'SOC':>8} {'PV余剰':>8}")
print(f"{'':8} {'(kW)':>8} {'(kW)':>8} {'(kW)':>8} {'(kW)':>8} {'(kW)':>8} {'(kWh)':>8} {'(kW)':>8}")
print("-" * 80)

for _, row in noon_period_48h.iterrows():
    time_str = row['timestamp'][11:16]
    print(f"{time_str:<8} {row['pv_kW']:>8.2f} {row['demand_kW']:>8.2f} {row['sBY']:>8.2f} "
          f"{row['xFC1']:>8.2f} {row['xFD1']:>8.2f} {row['bF']:>8.2f} {row['pv_surplus_kW']:>8.2f}")

# 年間統計
print("\n" + "=" * 80)
print("【48時間予測】年間統計")
print("=" * 80)

annual_pv_total = df_48h['pv_kW'].sum() * 0.5
annual_pv_used = df_48h['pv_used_kW'].sum() * 0.5
annual_pv_surplus = df_48h['pv_surplus_kW'].sum() * 0.5
annual_demand = df_48h['demand_kW'].sum() * 0.5
annual_buy = df_48h['sBY'].sum() * 0.5
max_buy = df_48h['sBY'].max()

print(f"\n総PV発電量:     {annual_pv_total:.2f} kWh")
print(f"PV自家消費量:   {annual_pv_used:.2f} kWh")
print(f"PV余剰量:       {annual_pv_surplus:.2f} kWh")
print(f"PV利用率:       {(annual_pv_used / annual_pv_total * 100):.1f}%")
print(f"総需要:         {annual_demand:.2f} kWh")
print(f"総買電量:       {annual_buy:.2f} kWh")
print(f"契約電力:       {max_buy:.2f} kW")
print(f"PV自給率:       {(annual_pv_used / annual_demand * 100):.1f}%")

# 24時間予測との比較用データ（archive/に保存されている想定）
print("\n" + "=" * 80)
print("【参考】24時間予測の主要指標（前回の結果）")
print("=" * 80)
print("PV余剰量:       557 kWh (3月7日)")
print("PV余剰率:       45.5% (3月7日)")
print("最大SOC:        589.66 kWh (3月7日)")
print("年間PV余剰:     20,958 kWh")
print("契約電力:       157.78 kW")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
