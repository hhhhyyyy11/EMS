#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市場価格（JEPX）の季節別分析スクリプト
- 季節別の価格統計
- 価格スパイク（高騰）の分析
- 北海道電力基本プラン(21.51円/kWh)との比較
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import json

# 日本語フォントの設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'TakaoPGothic', 'IPAexGothic']
plt.rcParams['axes.unicode_minus'] = False

HOKKAIDO_PRICE = 21.51  # 北海道電力基本プランの電力量料金 [円/kWh]

def load_data(results_dir='results'):
    """データを読み込む"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    results_file = os.path.join(project_root, results_dir, 'rolling_results.csv')

    df = pd.read_csv(results_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['month'] = df['timestamp'].dt.month
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour

    # 季節の定義
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

def analyze_price_statistics(df):
    """価格の統計分析"""
    print('\n=== 市場価格（JEPX）統計分析 ===')

    # 全体統計
    print(f'\n--- 年間統計 ---')
    print(f'平均価格: {df["price_yen_per_kWh"].mean():.2f} 円/kWh')
    print(f'中央値: {df["price_yen_per_kWh"].median():.2f} 円/kWh')
    print(f'最小値: {df["price_yen_per_kWh"].min():.2f} 円/kWh')
    print(f'最大値: {df["price_yen_per_kWh"].max():.2f} 円/kWh')
    print(f'標準偏差: {df["price_yen_per_kWh"].std():.2f} 円/kWh')
    print(f'北海道電力基本プラン: {HOKKAIDO_PRICE:.2f} 円/kWh（固定）')

    # 北海道電力より高い時間帯の割合
    above_hokkaido = (df['price_yen_per_kWh'] > HOKKAIDO_PRICE).sum()
    total_steps = len(df)
    print(f'\n市場価格 > 北海道電力 の時間帯: {above_hokkaido} / {total_steps} ({above_hokkaido/total_steps*100:.1f}%)')

    return df

def analyze_seasonal_price(df):
    """季節別価格分析"""
    seasons = ['春 (3-5月)', '夏 (6-8月)', '秋 (9-11月)', '冬 (12-2月)']
    seasonal_stats = []

    print(f'\n--- 季節別価格統計 ---')
    print(f'{"季節":<12} {"平均":>8} {"中央値":>8} {"最小":>8} {"最大":>8} {"標準偏差":>8} {">北電率":>8}')
    print('-' * 70)

    for season in seasons:
        season_data = df[df['season'] == season]
        prices = season_data['price_yen_per_kWh']

        above_hokkaido_rate = (prices > HOKKAIDO_PRICE).sum() / len(prices) * 100

        stats = {
            'season': season,
            'mean': prices.mean(),
            'median': prices.median(),
            'min': prices.min(),
            'max': prices.max(),
            'std': prices.std(),
            'above_hokkaido_rate': above_hokkaido_rate,
            'count': len(prices),
        }
        seasonal_stats.append(stats)

        print(f'{season:<12} {stats["mean"]:>7.2f}円 {stats["median"]:>7.2f}円 {stats["min"]:>7.2f}円 {stats["max"]:>7.2f}円 {stats["std"]:>7.2f}円 {above_hokkaido_rate:>7.1f}%')

    return pd.DataFrame(seasonal_stats)

def analyze_monthly_price(df):
    """月別価格分析"""
    monthly_stats = []
    month_names = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

    print(f'\n--- 月別価格統計 ---')
    print(f'{"月":<6} {"平均":>8} {"中央値":>8} {"最小":>8} {"最大":>8} {">北電率":>8}')
    print('-' * 55)

    for month in range(1, 13):
        month_data = df[df['month'] == month]
        prices = month_data['price_yen_per_kWh']

        above_hokkaido_rate = (prices > HOKKAIDO_PRICE).sum() / len(prices) * 100

        stats = {
            'month': month,
            'month_name': month_names[month-1],
            'mean': prices.mean(),
            'median': prices.median(),
            'min': prices.min(),
            'max': prices.max(),
            'std': prices.std(),
            'above_hokkaido_rate': above_hokkaido_rate,
        }
        monthly_stats.append(stats)

        print(f'{month_names[month-1]:<6} {stats["mean"]:>7.2f}円 {stats["median"]:>7.2f}円 {stats["min"]:>7.2f}円 {stats["max"]:>7.2f}円 {above_hokkaido_rate:>7.1f}%')

    return pd.DataFrame(monthly_stats)

def analyze_price_spikes(df, threshold=25.0):
    """価格スパイク（高騰）の分析"""
    print(f'\n--- 価格スパイク分析（閾値: {threshold}円/kWh以上） ---')

    spikes = df[df['price_yen_per_kWh'] >= threshold].copy()
    print(f'スパイク発生回数: {len(spikes)} / {len(df)} ({len(spikes)/len(df)*100:.2f}%)')

    if len(spikes) > 0:
        # 月別スパイク発生回数
        spike_by_month = spikes.groupby('month').size()
        print(f'\n月別スパイク発生回数:')
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
        for month in range(1, 13):
            count = spike_by_month.get(month, 0)
            print(f'  {month_names[month-1]}: {count}回')

        # 時間帯別スパイク発生回数
        spike_by_hour = spikes.groupby('hour').size()
        print(f'\n時間帯別スパイク発生回数（上位5時間帯）:')
        for hour, count in spike_by_hour.sort_values(ascending=False).head(5).items():
            print(f'  {hour}:00-{hour+1}:00: {count}回')

        # 最高価格の日
        max_price_idx = df['price_yen_per_kWh'].idxmax()
        max_price_row = df.loc[max_price_idx]
        print(f'\n最高価格: {max_price_row["price_yen_per_kWh"]:.2f}円/kWh')
        print(f'  発生日時: {max_price_row["timestamp"]}')

    return spikes

def analyze_hourly_price_pattern(df):
    """時間帯別価格パターン"""
    hourly_stats = df.groupby('hour')['price_yen_per_kWh'].agg(['mean', 'std', 'min', 'max'])
    hourly_stats.columns = ['mean', 'std', 'min', 'max']

    print(f'\n--- 時間帯別価格パターン ---')
    print(f'{"時間帯":<10} {"平均":>8} {"標準偏差":>8}')
    print('-' * 30)
    for hour in range(24):
        row = hourly_stats.loc[hour]
        print(f'{hour:02d}:00-{hour+1:02d}:00 {row["mean"]:>7.2f}円 {row["std"]:>7.2f}円')

    return hourly_stats

def plot_price_analysis(df, monthly_df, seasonal_df, hourly_stats, png_dir, project_root):
    """価格分析グラフの作成"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. 月別平均価格と北海道電力との比較
    ax1 = axes[0, 0]
    months = range(1, 13)
    month_labels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

    bars = ax1.bar(months, monthly_df['mean'], color='steelblue', alpha=0.7, label='市場価格（平均）')
    ax1.axhline(y=HOKKAIDO_PRICE, color='red', linestyle='--', linewidth=2, label=f'北海道電力基本プラン ({HOKKAIDO_PRICE}円/kWh)')
    ax1.errorbar(months, monthly_df['mean'], yerr=monthly_df['std'], fmt='none', color='black', capsize=3, label='標準偏差')

    ax1.set_xlabel('月')
    ax1.set_ylabel('電力価格 [円/kWh]')
    ax1.set_title('月別市場価格と北海道電力基本プランの比較')
    ax1.set_xticks(months)
    ax1.set_xticklabels(month_labels, rotation=45)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, monthly_df['mean'].max() * 1.3)

    # 2. 時間帯別価格パターン
    ax2 = axes[0, 1]
    hours = range(24)
    ax2.fill_between(hours, hourly_stats['mean'] - hourly_stats['std'],
                     hourly_stats['mean'] + hourly_stats['std'], alpha=0.3, color='steelblue')
    ax2.plot(hours, hourly_stats['mean'], color='steelblue', linewidth=2, label='市場価格（平均±標準偏差）')
    ax2.axhline(y=HOKKAIDO_PRICE, color='red', linestyle='--', linewidth=2, label=f'北海道電力 ({HOKKAIDO_PRICE}円/kWh)')

    ax2.set_xlabel('時刻')
    ax2.set_ylabel('電力価格 [円/kWh]')
    ax2.set_title('時間帯別市場価格パターン')
    ax2.set_xticks(range(0, 24, 2))
    ax2.set_xticklabels([f'{h}:00' for h in range(0, 24, 2)], rotation=45)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

    # 3. 季節別価格分布（箱ひげ図）
    ax3 = axes[1, 0]
    seasons = ['春 (3-5月)', '夏 (6-8月)', '秋 (9-11月)', '冬 (12-2月)']
    season_data = [df[df['season'] == s]['price_yen_per_kWh'].values for s in seasons]

    bp = ax3.boxplot(season_data, labels=['春', '夏', '秋', '冬'], patch_artist=True)
    colors = ['lightgreen', 'lightyellow', 'lightcoral', 'lightblue']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
    ax3.axhline(y=HOKKAIDO_PRICE, color='red', linestyle='--', linewidth=2, label=f'北海道電力 ({HOKKAIDO_PRICE}円/kWh)')

    ax3.set_xlabel('季節')
    ax3.set_ylabel('電力価格 [円/kWh]')
    ax3.set_title('季節別市場価格分布')
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)

    # 4. 月別「市場価格 > 北海道電力」の割合
    ax4 = axes[1, 1]
    colors = ['green' if rate < 50 else 'orange' if rate < 70 else 'red' for rate in monthly_df['above_hokkaido_rate']]
    bars = ax4.bar(months, monthly_df['above_hokkaido_rate'], color=colors, alpha=0.7)
    ax4.axhline(y=50, color='gray', linestyle=':', linewidth=1, alpha=0.7)

    ax4.set_xlabel('月')
    ax4.set_ylabel('割合 [%]')
    ax4.set_title('月別「市場価格 > 北海道電力基本プラン」の時間帯割合')
    ax4.set_xticks(months)
    ax4.set_xticklabels(month_labels, rotation=45)
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, 100)

    # 年間平均を追加
    annual_above_rate = (df['price_yen_per_kWh'] > HOKKAIDO_PRICE).sum() / len(df) * 100
    ax4.axhline(y=annual_above_rate, color='red', linestyle='--', linewidth=2,
                label=f'年間平均: {annual_above_rate:.1f}%')
    ax4.legend(loc='upper right')

    plt.tight_layout()
    output_file = os.path.join(project_root, png_dir, 'price_seasonal_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f'\n✓ 価格分析グラフを保存: {output_file}')
    plt.close()

def plot_price_histogram(df, png_dir, project_root):
    """価格分布ヒストグラム"""
    fig, ax = plt.subplots(figsize=(10, 6))

    prices = df['price_yen_per_kWh']

    # ヒストグラム
    n, bins, patches = ax.hist(prices, bins=50, color='steelblue', alpha=0.7, edgecolor='black')

    # 北海道電力の価格ライン
    ax.axvline(x=HOKKAIDO_PRICE, color='red', linestyle='--', linewidth=2,
               label=f'北海道電力基本プラン ({HOKKAIDO_PRICE}円/kWh)')

    # 平均価格ライン
    ax.axvline(x=prices.mean(), color='orange', linestyle='-', linewidth=2,
               label=f'市場価格平均 ({prices.mean():.2f}円/kWh)')

    ax.set_xlabel('電力価格 [円/kWh]')
    ax.set_ylabel('頻度（30分コマ数）')
    ax.set_title('市場価格（JEPX）の分布')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = os.path.join(project_root, png_dir, 'price_histogram.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f'✓ 価格分布ヒストグラムを保存: {output_file}')
    plt.close()

def main(results_dir='results', png_dir='png'):
    """メイン処理"""
    print('\n' + '='*60)
    print('市場価格（JEPX）季節別分析')
    print('='*60)

    df, project_root = load_data(results_dir)
    os.makedirs(os.path.join(project_root, png_dir), exist_ok=True)

    # 分析実行
    analyze_price_statistics(df)
    seasonal_df = analyze_seasonal_price(df)
    monthly_df = analyze_monthly_price(df)
    analyze_price_spikes(df, threshold=25.0)
    hourly_stats = analyze_hourly_price_pattern(df)

    # グラフ生成
    plot_price_analysis(df, monthly_df, seasonal_df, hourly_stats, png_dir, project_root)
    plot_price_histogram(df, png_dir, project_root)

    # 結果をJSONで保存
    results = {
        'annual_statistics': {
            'mean': float(df['price_yen_per_kWh'].mean()),
            'median': float(df['price_yen_per_kWh'].median()),
            'min': float(df['price_yen_per_kWh'].min()),
            'max': float(df['price_yen_per_kWh'].max()),
            'std': float(df['price_yen_per_kWh'].std()),
            'above_hokkaido_rate': float((df['price_yen_per_kWh'] > HOKKAIDO_PRICE).sum() / len(df) * 100),
            'hokkaido_price': HOKKAIDO_PRICE,
        },
        'monthly': monthly_df.to_dict(orient='records'),
        'seasonal': seasonal_df.to_dict(orient='records'),
        'insights': {
            'highest_price_month': monthly_df.loc[monthly_df['mean'].idxmax(), 'month_name'],
            'lowest_price_month': monthly_df.loc[monthly_df['mean'].idxmin(), 'month_name'],
            'most_volatile_month': monthly_df.loc[monthly_df['std'].idxmax(), 'month_name'],
        }
    }

    json_file = os.path.join(project_root, results_dir, 'price_seasonal_analysis.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\n✓ 分析結果をJSONで保存: {json_file}')

    # サマリー
    print('\n' + '='*60)
    print('サマリー: なぜ北海道電力基本プランが有利か')
    print('='*60)
    above_rate = results['annual_statistics']['above_hokkaido_rate']
    print(f'1. 市場価格が北海道電力（{HOKKAIDO_PRICE}円/kWh）を上回る時間帯: {above_rate:.1f}%')
    print(f'2. 市場価格の年間平均: {results["annual_statistics"]["mean"]:.2f}円/kWh')
    print(f'3. 価格変動（標準偏差）: {results["annual_statistics"]["std"]:.2f}円/kWh')
    print(f'4. 最高価格月: {results["insights"]["highest_price_month"]}')
    print(f'5. 最低価格月: {results["insights"]["lowest_price_month"]}')

    return results

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
