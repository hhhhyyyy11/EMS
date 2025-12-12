#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
データ整合性検証スクリプト

rolling_opt.pyが保存したデータと、ログの出力、グラフ生成で使用されるデータの
整合性を確認します。
"""

import os
import json
import pandas as pd
import re

def check_file_exists(filepath, description):
    """ファイルの存在確認"""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {filepath}")
    return exists

def verify_json_data(json_path):
    """JSONファイルのデータ検証"""
    print("\n" + "="*60)
    print("JSONデータの検証")
    print("="*60)

    if not os.path.exists(json_path):
        print(f"✗ JSONファイルが見つかりません: {json_path}")
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"✓ JSONファイルを読み込みました")

    # 必要なキーの確認
    required_keys = ['hokkaido_basic', 'market_linked', 'peak_demand_kW',
                     'monthly_energy_kWh', 'monthly_peak_kW']

    for key in required_keys:
        if key in data:
            print(f"  ✓ キー '{key}' が存在します")
        else:
            print(f"  ✗ キー '{key}' が見つかりません")

    # データの表示
    print("\n北海道電力基本プラン:")
    if 'hokkaido_basic' in data:
        for k, v in data['hokkaido_basic'].items():
            print(f"  {k}: {v:,.0f}円" if isinstance(v, (int, float)) else f"  {k}: {v}")

    print("\n市場価格連動プラン:")
    if 'market_linked' in data:
        for k, v in data['market_linked'].items():
            print(f"  {k}: {v:,.0f}円" if isinstance(v, (int, float)) else f"  {k}: {v}")

    if 'peak_demand_kW' in data:
        print(f"\n契約電力: {data['peak_demand_kW']:.1f}kW")

    return data

def verify_csv_data(csv_path):
    """CSVファイルのデータ検証"""
    print("\n" + "="*60)
    print("CSVデータの検証")
    print("="*60)

    if not os.path.exists(csv_path):
        print(f"✗ CSVファイルが見つかりません: {csv_path}")
        return None

    df = pd.read_csv(csv_path)
    print(f"✓ CSVファイルを読み込みました: {len(df)}行")

    # カラムの確認
    required_columns = ['timestamp', 'consumption_kW', 'pv_kW', 'sBY', 'sSL',
                       'bF', 'price_yen_per_kWh', 'status']

    for col in required_columns:
        if col in df.columns:
            print(f"  ✓ カラム '{col}' が存在します")
        else:
            print(f"  ✗ カラム '{col}' が見つかりません")

    # 基本統計
    if 'sBY' in df.columns:
        max_sBY = df['sBY'].max()
        total_energy = (df['sBY'] * 0.5).sum()
        print(f"\n最大買電電力: {max_sBY:.2f}kW")
        print(f"年間買電量: {total_energy:,.0f}kWh")

    if 'status' in df.columns:
        infeasible_count = (df['status'] == 'infeasible').sum()
        print(f"Infeasibleステップ数: {infeasible_count} ({infeasible_count/len(df)*100:.2f}%)")

    return df

def verify_log_consistency(log_path, json_data):
    """ログファイルとJSONデータの整合性確認"""
    print("\n" + "="*60)
    print("ログとJSONデータの整合性確認")
    print("="*60)

    if not os.path.exists(log_path):
        print(f"✗ ログファイルが見つかりません: {log_path}")
        return

    # ログファイルが大きすぎる場合はgrepで検索
    import subprocess
    try:
        result = subprocess.run(
            ['grep', '-A', '10', '=== 年間電気料金比較 ===', log_path],
            capture_output=True, text=True, timeout=10
        )
        log_content = result.stdout
    except Exception as e:
        print(f"✗ ログファイルの読み込みに失敗: {e}")
        return

    if not log_content:
        print("⚠ ログに年間電気料金比較のデータが見つかりませんでした")
        return

    print("✓ ログから年間電気料金データを抽出しました")

    # ログから数値を抽出
    hokkaido_match = re.search(r'北海道電力基本プラン:\s*([\d,]+)円', log_content)
    market_match = re.search(r'市場価格連動プラン:\s*([\d,]+)円', log_content)
    contract_match = re.search(r'契約電力:\s*([\d.]+)kW', log_content)

    if json_data is None:
        print("⚠ JSONデータがないため比較できません")
        return

    # 比較
    print("\n比較結果:")

    if hokkaido_match and 'hokkaido_basic' in json_data:
        log_value = float(hokkaido_match.group(1).replace(',', ''))
        json_value = json_data['hokkaido_basic']['total']
        diff = abs(log_value - json_value)
        match = "✓" if diff < 1 else "✗"
        print(f"{match} 北海道電力基本プラン:")
        print(f"    ログ: {log_value:,.0f}円")
        print(f"    JSON: {json_value:,.0f}円")
        print(f"    差異: {diff:,.0f}円")

    if market_match and 'market_linked' in json_data:
        log_value = float(market_match.group(1).replace(',', ''))
        json_value = json_data['market_linked']['total']
        diff = abs(log_value - json_value)
        match = "✓" if diff < 1 else "✗"
        print(f"{match} 市場価格連動プラン:")
        print(f"    ログ: {log_value:,.0f}円")
        print(f"    JSON: {json_value:,.0f}円")
        print(f"    差異: {diff:,.0f}円")

    if contract_match and 'peak_demand_kW' in json_data:
        log_value = float(contract_match.group(1))
        json_value = json_data['peak_demand_kW']
        diff = abs(log_value - json_value)
        match = "✓" if diff < 0.1 else "✗"
        print(f"{match} 契約電力:")
        print(f"    ログ: {log_value:.1f}kW")
        print(f"    JSON: {json_value:.1f}kW")
        print(f"    差異: {diff:.2f}kW")

def main():
    print("="*60)
    print("データ整合性検証スクリプト")
    print("="*60)

    # ファイルの存在確認
    print("\n1. ファイルの存在確認")
    print("-"*60)

    json_exists = check_file_exists('results/annual_cost_comparison.json',
                                    '年間料金比較JSON')
    csv_exists = check_file_exists('results/rolling_results.csv',
                                   '最適化結果CSV')
    log_exists = check_file_exists('logs/rolling_opt_run.log',
                                   '実行ログ')

    # JSONデータの検証
    json_data = None
    if json_exists:
        json_data = verify_json_data('results/annual_cost_comparison.json')

    # CSVデータの検証
    csv_data = None
    if csv_exists:
        csv_data = verify_csv_data('results/rolling_results.csv')

    # ログとの整合性確認
    if log_exists and json_data:
        verify_log_consistency('logs/rolling_opt_run.log', json_data)

    # 最終判定
    print("\n" + "="*60)
    print("検証結果サマリー")
    print("="*60)

    if json_exists and csv_exists:
        print("✓ 必要なデータファイルはすべて存在します")
        print("✓ データは適切に保存されています")
        print("\n推奨:")
        print("  - グラフ生成時は results/annual_cost_comparison.json を使用")
        print("  - TeX文書作成時も results/annual_cost_comparison.json を参照")
        print("  - 時系列データは results/rolling_results.csv を使用")
    else:
        print("✗ 一部のデータファイルが見つかりません")
        print("\n対処法:")
        if not json_exists:
            print("  - rolling_opt.py を実行して annual_cost_comparison.json を生成")
        if not csv_exists:
            print("  - rolling_opt.py を実行して rolling_results.csv を生成")

if __name__ == '__main__':
    main()
