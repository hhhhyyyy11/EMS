#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年間のPV発電・買電・需要の推移グラフを生成するスクリプト
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAPGothic']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

def generate_annual_pv_buy_demand_graph():
    """年間のPV発電・買電・需要の推移グラフを生成"""

    # データ読み込み
    base_dir = Path(__file__).parent.parent
    results_file = Path(base_dir) / results_dir / 'rolling_results.csv'
    output_dir = Path(base_dir) / png_dir
    output_dir.mkdir(exist_ok=True)

    print(f"データ読み込み中: {results_file}")
    df = pd.read_csv(results_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # グラフ作成
    fig, ax = plt.subplots(figsize=(14, 6))

    # データプロット
    ax.plot(df['timestamp'], df['demand_kW'], label='需要', linewidth=0.5, alpha=0.7, color='red')
    ax.plot(df['timestamp'], df['pv_kW'], label='PV発電', linewidth=0.5, alpha=0.7, color='orange')
    ax.plot(df['timestamp'], df['sBY'], label='買電', linewidth=0.5, alpha=0.7, color='blue')

    # グラフ設定
    ax.set_xlabel('日付', fontsize=12)
    ax.set_ylabel('電力 [kW]', fontsize=12)
    ax.set_title('年間のPV発電・買電・需要の推移（2024年）', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)

    # X軸の日付フォーマット
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=45)

    # Y軸の範囲設定（0から開始）
    ax.set_ylim(bottom=0)

    plt.tight_layout()

    # 保存
    output_file = output_dir / 'annual_pv_buy_demand.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"グラフ保存完了: {output_file}")

    # 統計情報表示
    print("\n=== データ統計 ===")
    print(f"データ期間: {df['timestamp'].min()} ～ {df['timestamp'].max()}")
    print(f"データポイント数: {len(df)}")
    print(f"\n需要 [kW]: 平均={df['demand_kW'].mean():.2f}, 最大={df['demand_kW'].max():.2f}, 最小={df['demand_kW'].min():.2f}")
    print(f"PV発電 [kW]: 平均={df['pv_kW'].mean():.2f}, 最大={df['pv_kW'].max():.2f}, 最小={df['pv_kW'].min():.2f}")
    print(f"買電 [kW]: 平均={df['sBY'].mean():.2f}, 最大={df['sBY'].max():.2f}, 最小={df['sBY'].min():.2f}")

    # PV発電がゼロでないデータ点の確認
    pv_nonzero = df[df['pv_kW'] > 0]
    print(f"\nPV発電がゼロでないデータ点: {len(pv_nonzero)} / {len(df)} ({100*len(pv_nonzero)/len(df):.1f}%)")

    plt.close()

def generate_annual_soc_graph():
    """年間のSOC推移グラフを生成"""

    # データ読み込み
    base_dir = Path(__file__).parent.parent
    results_file = Path(base_dir) / results_dir / 'rolling_results.csv'
    output_dir = Path(base_dir) / png_dir
    output_dir.mkdir(exist_ok=True)

    print(f"\nデータ読み込み中: {results_file}")
    df = pd.read_csv(results_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # グラフ作成
    fig, ax = plt.subplots(figsize=(14, 6))

    # SOCデータプロット
    ax.plot(df['timestamp'], df['bF'], linewidth=0.5, alpha=0.8, color='green')

    # グラフ設定
    ax.set_xlabel('日付', fontsize=12)
    ax.set_ylabel('SOC [kWh]', fontsize=12)
    ax.set_title('年間の蓄電池SOC推移（2024年）', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # X軸の日付フォーマット
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=45)

    # Y軸の範囲設定（0-860kWh）
    ax.set_ylim(0, 860)

    # 容量の50%ライン（430kWh）を追加
    ax.axhline(y=430, color='red', linestyle='--', linewidth=1, alpha=0.5, label='50% (430kWh)')
    ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()

    # 保存
    output_file = output_dir / 'annual_soc.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"グラフ保存完了: {output_file}")

    # 統計情報表示
    print("\n=== SOC統計 ===")
    print(f"平均SOC: {df['bF'].mean():.2f} kWh ({100*df['bF'].mean()/860:.1f}%)")
    print(f"最大SOC: {df['bF'].max():.2f} kWh ({100*df['bF'].max()/860:.1f}%)")
    print(f"最小SOC: {df['bF'].min():.2f} kWh ({100*df['bF'].min()/860:.1f}%)")
    print(f"標準偏差: {df['bF'].std():.2f} kWh")

    plt.close()

if __name__ == '__main__':
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

    generate_annual_pv_buy_demand_graph(results_dir=results_dir, png_dir=png_dir)
    generate_annual_soc_graph(results_dir=results_dir, png_dir=png_dir)
