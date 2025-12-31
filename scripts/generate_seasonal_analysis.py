#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
季節別・月別の電力運用分析スクリプト
蓄電池の効果が季節によってどう異なるかを分析
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import json

# 日本語フォントの設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'TakaoPGothic', 'IPAexGothic']
plt.rcParams['axes.unicode_minus'] = False

def load_data(results_dir='results'):
    """データを読み込む"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    results_file = os.path.join(project_root, results_dir, 'rolling_results.csv')

    df = pd.read_csv(results_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['month'] = df['timestamp'].dt.month
    df['date'] = df['timestamp'].dt.date

    # 季節の定義（日本の一般的な区分）
    def get_season(month):
        if month in [3, 4, 5]:
            return '春 (3-5月)'
        elif month in [6, 7, 8]:
            return '夏 (6-8月)'
        elif month in [9, 10, 11]:
            return '秋 (9-11月)'
        else:
            return '冬 (12-2月)'

    df['season'] = df['month'].apply(get_season)

    return df, project_root

def analyze_monthly(df):
    """月別の統計を計算"""
    monthly_stats = []

    for month in range(1, 13):
        month_data = df[df['month'] == month]

        # 各種統計
        stats = {
            'month': month,
            'demand_total_kWh': month_data['demand_kW'].sum() * 0.5,
            'pv_total_kWh': month_data['pv_used_kW'].sum() * 0.5,
            'buy_total_kWh': month_data['sBY'].sum() * 0.5,
            'demand_peak_kW': month_data['demand_kW'].max(),
            'buy_peak_kW': month_data['sBY'].max(),
            'pv_peak_kW': month_data['pv_used_kW'].max(),
            'avg_soc_kWh': month_data['bF'].mean(),
            'min_soc_kWh': month_data['bF'].min(),
            'max_soc_kWh': month_data['bF'].max(),
            # 充放電量
            'charge_total_kWh': month_data['xFC1'].sum() * 0.5,
            'discharge_total_kWh': month_data['xFD1'].sum() * 0.5,
        }

        # PV自家消費率（需要に対するPV直接利用の割合）
        stats['pv_self_consumption_rate'] = (stats['pv_total_kWh'] / stats['demand_total_kWh'] * 100) if stats['demand_total_kWh'] > 0 else 0

        # 蓄電池による需要カバー率
        stats['battery_contribution_rate'] = (stats['discharge_total_kWh'] / stats['demand_total_kWh'] * 100) if stats['demand_total_kWh'] > 0 else 0

        # ピークカット率（需要ピークに対する買電ピークの削減率）
        stats['peak_cut_rate'] = ((stats['demand_peak_kW'] - stats['buy_peak_kW']) / stats['demand_peak_kW'] * 100) if stats['demand_peak_kW'] > 0 else 0

        monthly_stats.append(stats)

    return pd.DataFrame(monthly_stats)

def analyze_seasonal(df):
    """季節別の統計を計算"""
    seasonal_stats = []
    seasons = ['春 (3-5月)', '夏 (6-8月)', '秋 (9-11月)', '冬 (12-2月)']

    for season in seasons:
        season_data = df[df['season'] == season]

        stats = {
            'season': season,
            'demand_total_kWh': season_data['demand_kW'].sum() * 0.5,
            'pv_total_kWh': season_data['pv_used_kW'].sum() * 0.5,
            'buy_total_kWh': season_data['sBY'].sum() * 0.5,
            'demand_peak_kW': season_data['demand_kW'].max(),
            'buy_peak_kW': season_data['sBY'].max(),
            'charge_total_kWh': season_data['xFC1'].sum() * 0.5,
            'discharge_total_kWh': season_data['xFD1'].sum() * 0.5,
            'avg_price': season_data['price_yen_per_kWh'].mean(),
        }

        stats['pv_self_consumption_rate'] = (stats['pv_total_kWh'] / stats['demand_total_kWh'] * 100) if stats['demand_total_kWh'] > 0 else 0
        stats['battery_contribution_rate'] = (stats['discharge_total_kWh'] / stats['demand_total_kWh'] * 100) if stats['demand_total_kWh'] > 0 else 0
        stats['peak_cut_rate'] = ((stats['demand_peak_kW'] - stats['buy_peak_kW']) / stats['demand_peak_kW'] * 100) if stats['demand_peak_kW'] > 0 else 0

        seasonal_stats.append(stats)

    return pd.DataFrame(seasonal_stats)

def plot_monthly_analysis(monthly_df, png_dir, project_root):
    """月別分析のグラフを作成"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    months = monthly_df['month']
    month_labels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

    # 1. 月別エネルギー量（需要、PV、買電）
    ax1 = axes[0, 0]
    width = 0.25
    x = np.arange(12)
    ax1.bar(x - width, monthly_df['demand_total_kWh'] / 1000, width, label='需要', color='red', alpha=0.7)
    ax1.bar(x, monthly_df['pv_total_kWh'] / 1000, width, label='PV発電', color='orange', alpha=0.7)
    ax1.bar(x + width, monthly_df['buy_total_kWh'] / 1000, width, label='買電', color='blue', alpha=0.7)
    ax1.set_xlabel('月')
    ax1.set_ylabel('電力量 [MWh]')
    ax1.set_title('月別エネルギー量')
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 月別ピーク電力
    ax2 = axes[0, 1]
    ax2.bar(x - width/2, monthly_df['demand_peak_kW'], width, label='需要ピーク', color='red', alpha=0.7)
    ax2.bar(x + width/2, monthly_df['buy_peak_kW'], width, label='買電ピーク', color='blue', alpha=0.7)
    ax2.set_xlabel('月')
    ax2.set_ylabel('ピーク電力 [kW]')
    ax2.set_title('月別ピーク電力（需要 vs 買電）')
    ax2.set_xticks(x)
    ax2.set_xticklabels(month_labels)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 月別蓄電池効果（PV自家消費率、蓄電池貢献率）
    ax3 = axes[1, 0]
    ax3.bar(x - width/2, monthly_df['pv_self_consumption_rate'], width, label='PV自家消費率', color='orange', alpha=0.7)
    ax3.bar(x + width/2, monthly_df['battery_contribution_rate'], width, label='蓄電池放電貢献率', color='green', alpha=0.7)
    ax3.set_xlabel('月')
    ax3.set_ylabel('割合 [%]')
    ax3.set_title('月別PV・蓄電池貢献率（対需要）')
    ax3.set_xticks(x)
    ax3.set_xticklabels(month_labels)
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. 月別ピークカット率
    ax4 = axes[1, 1]
    colors = ['#ff6b6b' if rate < 50 else '#4ecdc4' if rate < 70 else '#45b7d1' for rate in monthly_df['peak_cut_rate']]
    bars = ax4.bar(x, monthly_df['peak_cut_rate'], color=colors, alpha=0.8)
    ax4.axhline(y=monthly_df['peak_cut_rate'].mean(), color='red', linestyle='--', label=f'年間平均: {monthly_df["peak_cut_rate"].mean():.1f}%')
    ax4.set_xlabel('月')
    ax4.set_ylabel('ピークカット率 [%]')
    ax4.set_title('月別ピークカット率（(需要ピーク-買電ピーク)/需要ピーク）')
    ax4.set_xticks(x)
    ax4.set_xticklabels(month_labels)
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = os.path.join(project_root, png_dir, 'monthly_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f'✓ 月別分析グラフを保存: {output_file}')
    plt.close()

def plot_seasonal_analysis(seasonal_df, png_dir, project_root):
    """季節別分析のグラフを作成"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    seasons = seasonal_df['season']
    x = np.arange(4)

    # 1. 季節別エネルギー構成
    ax1 = axes[0]
    width = 0.25
    ax1.bar(x - width, seasonal_df['demand_total_kWh'] / 1000, width, label='需要', color='red', alpha=0.7)
    ax1.bar(x, seasonal_df['pv_total_kWh'] / 1000, width, label='PV発電', color='orange', alpha=0.7)
    ax1.bar(x + width, seasonal_df['buy_total_kWh'] / 1000, width, label='買電', color='blue', alpha=0.7)
    ax1.set_xlabel('季節')
    ax1.set_ylabel('電力量 [MWh]')
    ax1.set_title('季節別エネルギー量')
    ax1.set_xticks(x)
    ax1.set_xticklabels(seasons, rotation=15)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 季節別効果指標
    ax2 = axes[1]
    width = 0.35
    ax2.bar(x - width/2, seasonal_df['pv_self_consumption_rate'], width, label='PV自家消費率', color='orange', alpha=0.7)
    ax2.bar(x + width/2, seasonal_df['peak_cut_rate'], width, label='ピークカット率', color='green', alpha=0.7)
    ax2.set_xlabel('季節')
    ax2.set_ylabel('割合 [%]')
    ax2.set_title('季節別 PV自家消費率・ピークカット率')
    ax2.set_xticks(x)
    ax2.set_xticklabels(seasons, rotation=15)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = os.path.join(project_root, png_dir, 'seasonal_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f'✓ 季節別分析グラフを保存: {output_file}')
    plt.close()

def plot_monthly_battery_cycle(df, png_dir, project_root):
    """月別蓄電池サイクル数の分析"""
    # 日ごとの充放電サイクルを計算
    daily_stats = df.groupby('date').agg({
        'xFC1': lambda x: x.sum() * 0.5,  # 充電量 kWh
        'xFD1': lambda x: x.sum() * 0.5,  # 放電量 kWh
        'bF': ['min', 'max', 'mean'],
    }).reset_index()

    daily_stats.columns = ['date', 'charge_kWh', 'discharge_kWh', 'soc_min', 'soc_max', 'soc_mean']
    daily_stats['date'] = pd.to_datetime(daily_stats['date'])
    daily_stats['month'] = daily_stats['date'].dt.month

    # 月別集計
    monthly_cycle = daily_stats.groupby('month').agg({
        'charge_kWh': 'sum',
        'discharge_kWh': 'sum',
        'soc_min': 'min',
        'soc_max': 'max',
    }).reset_index()

    # サイクル数の推定（放電量 / 有効容量）
    # 860kWhの場合、有効容量は約731kWh (85%DOD想定)
    effective_capacity = 731  # kWh
    monthly_cycle['cycles'] = monthly_cycle['discharge_kWh'] / effective_capacity

    fig, ax = plt.subplots(figsize=(10, 5))

    month_labels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    x = np.arange(12)

    bars = ax.bar(x, monthly_cycle['cycles'], color='teal', alpha=0.7)
    ax.axhline(y=monthly_cycle['cycles'].mean(), color='red', linestyle='--',
               label=f'月平均: {monthly_cycle["cycles"].mean():.1f} サイクル')
    ax.axhline(y=monthly_cycle['cycles'].sum() / 12, color='orange', linestyle=':',
               label=f'年間合計: {monthly_cycle["cycles"].sum():.0f} サイクル')

    ax.set_xlabel('月')
    ax.set_ylabel('推定サイクル数')
    ax.set_title('月別蓄電池サイクル数（放電量ベース推定）')
    ax.set_xticks(x)
    ax.set_xticklabels(month_labels)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = os.path.join(project_root, png_dir, 'monthly_battery_cycles.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f'✓ 月別サイクル分析グラフを保存: {output_file}')
    plt.close()

    return monthly_cycle

def main(results_dir='results', png_dir='png'):
    """メイン処理"""
    print('\n=== 季節別・月別分析 ===')

    df, project_root = load_data(results_dir)
    os.makedirs(os.path.join(project_root, png_dir), exist_ok=True)

    # 月別分析
    print('\n--- 月別統計 ---')
    monthly_df = analyze_monthly(df)

    month_names = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

    print(f'{"月":<6} {"需要[MWh]":>10} {"PV[MWh]":>10} {"買電[MWh]":>10} {"ピークカット率":>12}')
    print('-' * 55)
    for i, row in monthly_df.iterrows():
        print(f'{month_names[i]:<6} {row["demand_total_kWh"]/1000:>10.1f} {row["pv_total_kWh"]/1000:>10.1f} {row["buy_total_kWh"]/1000:>10.1f} {row["peak_cut_rate"]:>11.1f}%')

    # 季節別分析
    print('\n--- 季節別統計 ---')
    seasonal_df = analyze_seasonal(df)

    print(f'{"季節":<12} {"需要[MWh]":>10} {"PV[MWh]":>10} {"買電[MWh]":>10} {"ピークカット率":>12}')
    print('-' * 60)
    for i, row in seasonal_df.iterrows():
        print(f'{row["season"]:<12} {row["demand_total_kWh"]/1000:>10.1f} {row["pv_total_kWh"]/1000:>10.1f} {row["buy_total_kWh"]/1000:>10.1f} {row["peak_cut_rate"]:>11.1f}%')

    # グラフ生成
    plot_monthly_analysis(monthly_df, png_dir, project_root)
    plot_seasonal_analysis(seasonal_df, png_dir, project_root)
    monthly_cycle = plot_monthly_battery_cycle(df, png_dir, project_root)

    # 結果をJSONで保存
    results = {
        'monthly': monthly_df.to_dict(orient='records'),
        'seasonal': seasonal_df.to_dict(orient='records'),
        'summary': {
            'best_peak_cut_month': month_names[monthly_df['peak_cut_rate'].idxmax()],
            'worst_peak_cut_month': month_names[monthly_df['peak_cut_rate'].idxmin()],
            'best_pv_month': month_names[monthly_df['pv_total_kWh'].idxmax()],
            'highest_demand_month': month_names[monthly_df['demand_total_kWh'].idxmax()],
            'annual_cycles': float(monthly_cycle['cycles'].sum()),
        }
    }

    json_file = os.path.join(project_root, results_dir, 'seasonal_analysis.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\n✓ 分析結果をJSONで保存: {json_file}')

    # サマリー表示
    print('\n=== サマリー ===')
    print(f'ピークカット率が最も高い月: {results["summary"]["best_peak_cut_month"]} ({monthly_df["peak_cut_rate"].max():.1f}%)')
    print(f'ピークカット率が最も低い月: {results["summary"]["worst_peak_cut_month"]} ({monthly_df["peak_cut_rate"].min():.1f}%)')
    print(f'PV発電量が最も多い月: {results["summary"]["best_pv_month"]} ({monthly_df["pv_total_kWh"].max()/1000:.1f} MWh)')
    print(f'需要が最も多い月: {results["summary"]["highest_demand_month"]} ({monthly_df["demand_total_kWh"].max()/1000:.1f} MWh)')
    print(f'年間推定サイクル数: {results["summary"]["annual_cycles"]:.0f} サイクル')

    return monthly_df, seasonal_df

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--soc', type=str, default=None, help='SOCサブフォルダ名（例: soc860）')
    parser.add_argument('--horizon', type=int, default=96, help='予測期間（ステップ数）')
    args = parser.parse_args()

    if args.horizon == 96:
        horizon_prefix = ''
    else:
        horizon_prefix = f'h{args.horizon}/'

    if args.soc:
        results_dir = f'results/{horizon_prefix}{args.soc}'
        png_dir = f'png/{horizon_prefix}{args.soc}'
    else:
        results_dir = f'results/{horizon_prefix}'.rstrip('/')
        png_dir = f'png/{horizon_prefix}'.rstrip('/')

    main(results_dir=results_dir, png_dir=png_dir)
    print('\n完了しました!')
