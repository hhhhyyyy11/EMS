#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代表的な1日の運用パターンを生成するスクリプト
PV発電量が多い日と少ない日を比較
蓄電池の充放電は表示せず、左右の軸の0を合わせる
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

# 日本語フォントの設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'TakaoPGothic', 'IPAexGothic']
plt.rcParams['axes.unicode_minus'] = False

def generate_daily_pattern_graph(date1='2024-06-02', date2='2024-06-24', results_dir='results', png_dir='png'):
    """
    2つの日の運用パターンを比較したグラフを生成
    results_dir, png_dir: サブフォルダ対応（例: results/soc860, png/soc860）

    Parameters:
    -----------
    date1 : str
        1つ目の対象日付 (YYYY-MM-DD形式) - PV発電量が多い日
    date2 : str
        2つ目の対象日付 (YYYY-MM-DD形式) - PV発電量が少ない日
    results_dir : str
        入力CSVのディレクトリ
    png_dir : str
        出力PNGのディレクトリ
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    results_file = os.path.join(project_root, results_dir, 'rolling_results.csv')
    os.makedirs(os.path.join(project_root, png_dir), exist_ok=True)

    print(f'\n=== 日次パターングラフ生成 ===')
    print(f'データ読み込み: {results_file}')

    df = pd.read_csv(results_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 2つの日のデータを抽出
    target_day1 = pd.to_datetime(date1)
    target_day2 = pd.to_datetime(date2)
    df_day1 = df[df['timestamp'].dt.date == target_day1.date()].copy()
    df_day2 = df[df['timestamp'].dt.date == target_day2.date()].copy()

    if len(df_day1) == 0 or len(df_day2) == 0:
        print(f'エラー: データが見つかりません')
        return

    # 時刻のみを抽出（日付部分を統一して比較しやすくする）
    df_day1['time'] = df_day1['timestamp'].dt.time
    df_day2['time'] = df_day2['timestamp'].dt.time

    # 統計情報の計算
    pv_total1 = df_day1['pv_used_kW'].sum() * 0.5  # kWh
    pv_total2 = df_day2['pv_used_kW'].sum() * 0.5  # kWh

    print(f'\n{date1}: PV発電量 {pv_total1:.2f} kWh')
    print(f'{date2}: PV発電量 {pv_total2:.2f} kWh')

    # 2つのサブプロットを作成
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # 共通のy軸範囲を設定（比較しやすくするため）
    y1_max = max(
        df_day1['demand_kW'].max(), df_day1['pv_used_kW'].max(), df_day1['sBY'].max(),
        df_day2['demand_kW'].max(), df_day2['pv_used_kW'].max(), df_day2['sBY'].max()
    )

    # === 上のグラフ: PV発電量が多い日 ===
    ax1_left = ax1
    ax1_left.plot(df_day1['timestamp'], df_day1['demand_kW'],
                  color='red', linewidth=2, label='需要')
    ax1_left.plot(df_day1['timestamp'], df_day1['pv_used_kW'],
                  color='orange', linewidth=2, label='PV発電')
    ax1_left.plot(df_day1['timestamp'], df_day1['sBY'],
                  color='blue', linewidth=2, label='買電')

    ax1_left.set_ylabel('電力 [kW]', fontsize=12)
    ax1_left.grid(True, alpha=0.3)
    ax1_left.legend(loc='upper left', fontsize=10)
    ax1_left.set_ylim(0, y1_max * 1.1)

    # 右軸：SOC
    ax1_right = ax1_left.twinx()
    ax1_right.plot(df_day1['timestamp'], df_day1['bF'],
                   color='green', linewidth=2, linestyle='--', label='蓄電池SOC')
    ax1_right.axhline(y=430, color='red', linestyle=':', linewidth=1, alpha=0.5, label='50%容量')
    ax1_right.set_ylabel('蓄電池SOC [kWh]', fontsize=12)
    ax1_right.legend(loc='upper right', fontsize=10)
    ax1_right.set_ylim(0, 800)

    # 時刻軸のフォーマット
    ax1_left.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax1_left.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    plt.setp(ax1_left.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # タイトル
    ax1_left.set_title(f'PV発電量が多い日 ({date1}, PV発電量: {pv_total1:.0f} kWh)',
                       fontsize=12, pad=10)

    # === 下のグラフ: PV発電量が少ない日 ===
    ax2_left = ax2
    ax2_left.plot(df_day2['timestamp'], df_day2['demand_kW'],
                  color='red', linewidth=2, label='需要')
    ax2_left.plot(df_day2['timestamp'], df_day2['pv_used_kW'],
                  color='orange', linewidth=2, label='PV発電')
    ax2_left.plot(df_day2['timestamp'], df_day2['sBY'],
                  color='blue', linewidth=2, label='買電')

    ax2_left.set_xlabel('時刻', fontsize=12)
    ax2_left.set_ylabel('電力 [kW]', fontsize=12)
    ax2_left.grid(True, alpha=0.3)
    ax2_left.legend(loc='upper left', fontsize=10)
    ax2_left.set_ylim(0, y1_max * 1.1)

    # 右軸：SOC
    ax2_right = ax2_left.twinx()
    ax2_right.plot(df_day2['timestamp'], df_day2['bF'],
                   color='green', linewidth=2, linestyle='--', label='蓄電池SOC')
    ax2_right.axhline(y=430, color='red', linestyle=':', linewidth=1, alpha=0.5, label='50%容量')
    ax2_right.set_ylabel('蓄電池SOC [kWh]', fontsize=12)
    ax2_right.legend(loc='upper right', fontsize=10)
    ax2_right.set_ylim(0, 800)

    # 時刻軸のフォーマット
    ax2_left.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax2_left.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    plt.setp(ax2_left.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # タイトル
    ax2_left.set_title(f'PV発電量が少ない日 ({date2}, PV発電量: {pv_total2:.0f} kWh)',
                       fontsize=12, pad=10)

    plt.tight_layout()

    # 保存
    output_file = os.path.join(project_root, png_dir, 'daily_battery_pattern.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f'✓ グラフを保存: {output_file}')

    # 統計情報の表示
    print(f'\n=== {date1} の統計（PV発電量が多い日） ===')
    print(f'需要: 平均 {df_day1["demand_kW"].mean():.2f} kW, 最大 {df_day1["demand_kW"].max():.2f} kW')
    print(f'PV発電: 平均 {df_day1["pv_used_kW"].mean():.2f} kW, 最大 {df_day1["pv_used_kW"].max():.2f} kW')
    print(f'買電: 平均 {df_day1["sBY"].mean():.2f} kW, 最大 {df_day1["sBY"].max():.2f} kW')
    print(f'SOC: 平均 {df_day1["bF"].mean():.2f} kWh, 最大 {df_day1["bF"].max():.2f} kWh, 最小 {df_day1["bF"].min():.2f} kWh')

    print(f'\n=== {date2} の統計（PV発電量が少ない日） ===')
    print(f'需要: 平均 {df_day2["demand_kW"].mean():.2f} kW, 最大 {df_day2["demand_kW"].max():.2f} kW')
    print(f'PV発電: 平均 {df_day2["pv_used_kW"].mean():.2f} kW, 最大 {df_day2["pv_used_kW"].max():.2f} kW')
    print(f'買電: 平均 {df_day2["sBY"].mean():.2f} kW, 最大 {df_day2["sBY"].max():.2f} kW')
    print(f'SOC: 平均 {df_day2["bF"].mean():.2f} kWh, 最大 {df_day2["bF"].max():.2f} kWh, 最小 {df_day2["bF"].min():.2f} kWh')

    plt.close()

if __name__ == '__main__':
    # 需要がほぼ同等(約2,450 kWh)でPV発電量が大きく異なる2日を比較
    # 2024-06-02: 需要2,436 kWh, PV発電1,433 kWh
    # 2024-06-24: 需要2,461 kWh, PV発電237 kWh
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--soc', type=str, default=None, help='SOCサブフォルダ名（例: soc860）')
    args = parser.parse_args()

    if args.soc:
        results_dir = f'results/{args.soc}'
        png_dir = f'png/{args.soc}'
    else:
        results_dir = 'results'
        png_dir = 'png'

    generate_daily_pattern_graph('2024-06-02', '2024-06-24', results_dir=results_dir, png_dir=png_dir)
    print('\n完了しました!')
