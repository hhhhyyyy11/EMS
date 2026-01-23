#!/usr/bin/env python3
"""
卒業論文用の追加図表を生成するスクリプト

1. ヒートマップ（Carpet Plot）: SOCと買電量の年間パターン
2. パレートフロンティア曲線: 契約電力 vs 電力量料金のトレードオフ
3. 決定要因の特定プロット: JEPX価格と充放電量の散布図
4. ピーク発生分布図: 月別の最大電力発生パターン
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
try:
    import japanize_matplotlib
except ImportError:
    # フォント設定を手動で行う
    plt.rcParams['font.family'] = ['Hiragino Sans', 'Yu Gothic', 'Meirio', 'sans-serif']
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 出力ディレクトリ
OUTPUT_DIR = Path("/Users/yzhy/Documents/大学関係/2025前期/EMS/png/thesis_figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# データディレクトリ
RESULTS_DIR = Path("/Users/yzhy/Documents/大学関係/2025前期/EMS/results")

def load_results(capacity: int, plan: str = "market_linked") -> pd.DataFrame:
    """シミュレーション結果を読み込む"""
    if capacity == 860:
        path = RESULTS_DIR / f"soc{capacity}" / f"rolling_results_{plan}.csv"
    else:
        path = RESULTS_DIR / f"soc{capacity}" / f"rolling_results_{plan}.csv"

    df = pd.read_csv(path, parse_dates=['timestamp'])
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour + df['timestamp'].dt.minute / 60
    df['month'] = df['timestamp'].dt.month
    df['day_of_year'] = df['timestamp'].dt.dayofyear
    return df


def create_heatmap_carpet_plot():
    """
    図1: ヒートマップ（Carpet Plot）
    横軸：時刻（0-24時）、縦軸：日付、色：SOCまたは買電量
    両プランの比較
    """
    print("Generating Carpet Plot (Heatmap)...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    plans = [
        ("hokkaido_basic", "北海道電力基本プラン"),
        ("market_linked", "市場価格連動プラン")
    ]

    for col, (plan, plan_name) in enumerate(plans):
        df = load_results(860, plan)

        # 日付と時刻でピボットテーブルを作成
        # 2月29日を除外（うるう年対応）
        df = df[~((df['timestamp'].dt.month == 2) & (df['timestamp'].dt.day == 29))]

        # SOCのヒートマップ
        pivot_soc = df.pivot_table(
            values='bF',
            index=df['timestamp'].dt.strftime('%m-%d'),
            columns=df['timestamp'].dt.hour + df['timestamp'].dt.minute/60,
            aggfunc='mean'
        )

        # 買電量のヒートマップ
        pivot_buy = df.pivot_table(
            values='sBY',
            index=df['timestamp'].dt.strftime('%m-%d'),
            columns=df['timestamp'].dt.hour + df['timestamp'].dt.minute/60,
            aggfunc='mean'
        )

        # SOCプロット
        ax1 = axes[0, col]
        im1 = ax1.imshow(pivot_soc.values, aspect='auto', cmap='RdYlBu_r',
                        extent=[0, 24, len(pivot_soc), 0])
        ax1.set_title(f'SOC推移 - {plan_name}', fontsize=12)
        ax1.set_xlabel('時刻 [時]')
        if col == 0:
            ax1.set_ylabel('日付 (1月→12月)')
        cbar1 = plt.colorbar(im1, ax=ax1, label='SOC [kWh]')

        # Y軸のラベルを月で表示
        month_positions = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
        month_labels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
        ax1.set_yticks(month_positions)
        ax1.set_yticklabels(month_labels, fontsize=8)

        # 買電量プロット
        ax2 = axes[1, col]
        im2 = ax2.imshow(pivot_buy.values, aspect='auto', cmap='YlOrRd',
                        extent=[0, 24, len(pivot_buy), 0], vmin=0, vmax=250)
        ax2.set_title(f'買電電力 - {plan_name}', fontsize=12)
        ax2.set_xlabel('時刻 [時]')
        if col == 0:
            ax2.set_ylabel('日付 (1月→12月)')
        cbar2 = plt.colorbar(im2, ax=ax2, label='買電電力 [kW]')

        ax2.set_yticks(month_positions)
        ax2.set_yticklabels(month_labels, fontsize=8)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "carpet_plot_soc_buy.png", dpi=300, bbox_inches='tight')
    # plt.savefig(OUTPUT_DIR / "carpet_plot_soc_buy.pdf", bbox_inches='tight')  # PDF出力は日本語フォント問題のため無効化
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / 'carpet_plot_soc_buy.png'}")


def create_pareto_frontier():
    """
    図2: パレートフロンティア曲線
    横軸：契約電力（最大買電電力）、縦軸：電力量料金（従量分）
    """
    print("Generating Pareto Frontier...")

    capacities = [0, 215, 430, 540, 645, 860, 1290, 1720]

    fig, ax = plt.subplots(figsize=(10, 8))

    # 各プランのデータを収集
    results = {'hokkaido_basic': [], 'market_linked': []}

    for cap in capacities:
        for plan in ['hokkaido_basic', 'market_linked']:
            try:
                df = load_results(cap, plan)
                max_buy = df['sBY'].max()

                # 電力量料金を計算
                if plan == 'hokkaido_basic':
                    # 固定価格 30.56円/kWh
                    energy_cost = df['sBY'].sum() * 0.5 * 30.56  # 30分間隔なので0.5を掛ける
                else:
                    # 市場価格連動
                    energy_cost = (df['sBY'] * df['price_yen_per_kWh'] * 0.5).sum()

                results[plan].append({
                    'capacity': cap,
                    'max_buy': max_buy,
                    'energy_cost': energy_cost / 10000  # 万円に変換
                })
            except Exception as e:
                print(f"  Warning: Could not load {plan} for capacity {cap}: {e}")

    # プロット
    colors = {'hokkaido_basic': '#1f77b4', 'market_linked': '#ff7f0e'}
    labels = {'hokkaido_basic': '北海道電力基本プラン', 'market_linked': '市場価格連動プラン'}
    markers = {'hokkaido_basic': 'o', 'market_linked': 's'}

    for plan in ['hokkaido_basic', 'market_linked']:
        data = results[plan]
        if data:
            x = [d['max_buy'] for d in data]
            y = [d['energy_cost'] for d in data]
            caps = [d['capacity'] for d in data]

            ax.scatter(x, y, c=colors[plan], marker=markers[plan], s=100,
                      label=labels[plan], zorder=3)
            ax.plot(x, y, c=colors[plan], alpha=0.5, linestyle='--', zorder=2)

            # 容量ラベルを追加
            for xi, yi, cap in zip(x, y, caps):
                ax.annotate(f'{cap}kWh', (xi, yi), textcoords="offset points",
                           xytext=(5, 5), fontsize=8, alpha=0.8)

    ax.set_xlabel('契約電力（最大買電電力） [kW]', fontsize=12)
    ax.set_ylabel('電力量料金 [万円/年]', fontsize=12)
    ax.set_title('パレートフロンティア：契約電力 vs 電力量料金のトレードオフ', fontsize=14)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # 矢印で最適化の方向を示す
    ax.annotate('', xy=(150, 850), xytext=(250, 950),
               arrowprops=dict(arrowstyle='->', color='gray', lw=2))
    ax.text(170, 920, '最適化の方向\n(両軸とも小さいほど良い)', fontsize=10, color='gray')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "pareto_frontier.png", dpi=300, bbox_inches='tight')
    # plt.savefig(OUTPUT_DIR / "pareto_frontier.pdf", bbox_inches='tight')  # PDF出力は日本語フォント問題のため無効化
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / 'pareto_frontier.png'}")


def create_price_charge_scatter():
    """
    図3: 決定要因の特定プロット
    横軸：JEPX価格、縦軸：充放電量（散布図）
    """
    print("Generating Price-Charge Scatter Plot...")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 市場連動プランのデータを読み込み
    df = load_results(860, "market_linked")

    # 充電量のプロット
    ax1 = axes[0]
    charge_mask = df['xFC1'] > 0.1
    scatter1 = ax1.scatter(df.loc[charge_mask, 'price_yen_per_kWh'],
                           df.loc[charge_mask, 'xFC1'],
                           c=df.loc[charge_mask, 'month'], cmap='viridis',
                           alpha=0.3, s=10)
    ax1.set_xlabel('JEPX価格 [円/kWh]', fontsize=12)
    ax1.set_ylabel('充電電力 [kW]', fontsize=12)
    ax1.set_title('JEPX価格と充電電力の関係', fontsize=14)
    ax1.axvline(x=15, color='red', linestyle='--', alpha=0.5, label='価格閾値の目安')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    cbar1 = plt.colorbar(scatter1, ax=ax1, label='月')

    # 放電量のプロット
    ax2 = axes[1]
    discharge_mask = df['xFD1'] > 0.1
    scatter2 = ax2.scatter(df.loc[discharge_mask, 'price_yen_per_kWh'],
                           df.loc[discharge_mask, 'xFD1'],
                           c=df.loc[discharge_mask, 'month'], cmap='viridis',
                           alpha=0.3, s=10)
    ax2.set_xlabel('JEPX価格 [円/kWh]', fontsize=12)
    ax2.set_ylabel('放電電力 [kW]', fontsize=12)
    ax2.set_title('JEPX価格と放電電力の関係', fontsize=14)
    ax2.axvline(x=20, color='red', linestyle='--', alpha=0.5, label='価格閾値の目安')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    cbar2 = plt.colorbar(scatter2, ax=ax2, label='月')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "price_charge_scatter.png", dpi=300, bbox_inches='tight')
    # plt.savefig(OUTPUT_DIR / "price_charge_scatter.pdf", bbox_inches='tight')  # PDF出力は日本語フォント問題のため無効化
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / 'price_charge_scatter.png'}")

    # 価格帯別の充放電パターン分析
    fig2, axes2 = plt.subplots(1, 2, figsize=(12, 5))

    # 価格帯を定義
    price_bins = [0, 10, 15, 20, 25, 35]
    price_labels = ['0-10', '10-15', '15-20', '20-25', '25+']
    df['price_bin'] = pd.cut(df['price_yen_per_kWh'], bins=price_bins, labels=price_labels)

    # 価格帯別の充電量
    charge_by_price = df.groupby('price_bin')['xFC1'].agg(['mean', 'std', 'count'])
    ax3 = axes2[0]
    bars1 = ax3.bar(range(len(price_labels)), charge_by_price['mean'],
                    yerr=charge_by_price['std'], capsize=5, color='steelblue', alpha=0.7)
    ax3.set_xticks(range(len(price_labels)))
    ax3.set_xticklabels([f'{l}\n円/kWh' for l in price_labels])
    ax3.set_xlabel('JEPX価格帯', fontsize=12)
    ax3.set_ylabel('平均充電電力 [kW]', fontsize=12)
    ax3.set_title('価格帯別の平均充電電力', fontsize=14)
    ax3.grid(True, alpha=0.3, axis='y')

    # 価格帯別の放電量
    discharge_by_price = df.groupby('price_bin')['xFD1'].agg(['mean', 'std', 'count'])
    ax4 = axes2[1]
    bars2 = ax4.bar(range(len(price_labels)), discharge_by_price['mean'],
                    yerr=discharge_by_price['std'], capsize=5, color='coral', alpha=0.7)
    ax4.set_xticks(range(len(price_labels)))
    ax4.set_xticklabels([f'{l}\n円/kWh' for l in price_labels])
    ax4.set_xlabel('JEPX価格帯', fontsize=12)
    ax4.set_ylabel('平均放電電力 [kW]', fontsize=12)
    ax4.set_title('価格帯別の平均放電電力', fontsize=14)
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "price_charge_bar.png", dpi=300, bbox_inches='tight')
    # plt.savefig(OUTPUT_DIR / "price_charge_bar.pdf", bbox_inches='tight')  # PDF出力は日本語フォント問題のため無効化
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / 'price_charge_bar.png'}")


def create_peak_distribution():
    """
    図4: ピーク発生分布図
    月別の最大電力発生回数と発生時刻のヒストグラム
    """
    print("Generating Peak Distribution...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    plans = [
        ("hokkaido_basic", "北海道電力基本プラン"),
        ("market_linked", "市場価格連動プラン")
    ]

    for col, (plan, plan_name) in enumerate(plans):
        df = load_results(860, plan)

        # 日ごとの最大買電電力とその時刻を特定
        daily_peaks = df.groupby('date').apply(
            lambda x: pd.Series({
                'max_buy': x['sBY'].max(),
                'peak_hour': x.loc[x['sBY'].idxmax(), 'hour'],
                'month': x['month'].iloc[0]
            })
        ).reset_index()

        # 年間最大の95%以上をピークとみなす
        threshold = daily_peaks['max_buy'].quantile(0.95)
        peak_days = daily_peaks[daily_peaks['max_buy'] >= threshold]

        # 月別のピーク発生回数
        ax1 = axes[0, col]
        monthly_peaks = peak_days.groupby('month').size()
        months = range(1, 13)
        peak_counts = [monthly_peaks.get(m, 0) for m in months]

        bars = ax1.bar(months, peak_counts, color='steelblue' if col == 0 else 'coral', alpha=0.7)
        ax1.set_xlabel('月', fontsize=12)
        ax1.set_ylabel('ピーク発生回数', fontsize=12)
        ax1.set_title(f'月別ピーク発生回数 - {plan_name}\n(上位5%の高需要日)', fontsize=12)
        ax1.set_xticks(months)
        ax1.set_xticklabels(['1月', '2月', '3月', '4月', '5月', '6月',
                            '7月', '8月', '9月', '10月', '11月', '12月'], fontsize=9)
        ax1.grid(True, alpha=0.3, axis='y')

        # バーに値を表示
        for bar, count in zip(bars, peak_counts):
            if count > 0:
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                        str(count), ha='center', va='bottom', fontsize=9)

        # ピーク発生時刻の分布
        ax2 = axes[1, col]
        ax2.hist(peak_days['peak_hour'], bins=48, range=(0, 24),
                color='steelblue' if col == 0 else 'coral', alpha=0.7, edgecolor='white')
        ax2.set_xlabel('時刻 [時]', fontsize=12)
        ax2.set_ylabel('頻度', fontsize=12)
        ax2.set_title(f'ピーク発生時刻の分布 - {plan_name}', fontsize=12)
        ax2.set_xlim(0, 24)
        ax2.grid(True, alpha=0.3, axis='y')

        # 主要時間帯をハイライト
        if col == 1:  # 市場連動プラン
            ax2.axvspan(0, 6, alpha=0.1, color='green', label='深夜帯（低価格）')
            ax2.axvspan(17, 21, alpha=0.1, color='red', label='夕方ピーク帯')
            ax2.legend(loc='upper right', fontsize=9)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "peak_distribution.png", dpi=300, bbox_inches='tight')
    # plt.savefig(OUTPUT_DIR / "peak_distribution.pdf", bbox_inches='tight')  # PDF出力は日本語フォント問題のため無効化
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / 'peak_distribution.png'}")

    # 追加：両プランの契約電力決定日の比較
    fig2, ax = plt.subplots(figsize=(12, 6))

    for plan, plan_name, color in [("hokkaido_basic", "北電基本", "steelblue"),
                                    ("market_linked", "市場連動", "coral")]:
        df = load_results(860, plan)
        daily_max = df.groupby('date')['sBY'].max()
        ax.plot(daily_max.index, daily_max.values, alpha=0.7, label=plan_name, color=color)

    ax.axhline(y=166.83, color='steelblue', linestyle='--', alpha=0.5, label='北電基本 契約電力')
    ax.axhline(y=218.05, color='coral', linestyle='--', alpha=0.5, label='市場連動 契約電力')

    ax.set_xlabel('日付', fontsize=12)
    ax.set_ylabel('日最大買電電力 [kW]', fontsize=12)
    ax.set_title('日最大買電電力の年間推移（蓄電池860kWh）', fontsize=14)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "daily_peak_comparison.png", dpi=300, bbox_inches='tight')
    # plt.savefig(OUTPUT_DIR / "daily_peak_comparison.pdf", bbox_inches='tight')  # PDF出力は日本語フォント問題のため無効化
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / 'daily_peak_comparison.png'}")


def main():
    """メイン関数"""
    print("=" * 60)
    print("卒業論文用追加図表の生成")
    print("=" * 60)

    # 1. ヒートマップ（Carpet Plot）
    create_heatmap_carpet_plot()

    # 2. パレートフロンティア曲線
    create_pareto_frontier()

    # 3. 決定要因の特定プロット
    create_price_charge_scatter()

    # 4. ピーク発生分布図
    create_peak_distribution()

    print("=" * 60)
    print(f"全ての図が {OUTPUT_DIR} に保存されました")
    print("=" * 60)


if __name__ == "__main__":
    main()
