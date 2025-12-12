import argparse
import os
import unicodedata
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from fpdf import FPDF
from pyscipopt import Model
import traceback


def read_spot_price_data(path='spot_summary_2024.csv', path_2023='spot_summary_2023.csv'):
    """
    JEPXスポット価格データを読み込み、30分間隔の価格データに変換
    2024年の完全なデータを得るため、2023年度と2024年度のデータを組み合わせる
    - 2024年1~3月: spot_summary_2023.csv（2024年1~3月分）
    - 2024年4~12月: spot_summary_2024.csv（2024年4~12月分）
    """
    def process_spot_data(df):
        """スポット価格データを30分間隔に展開"""
        expanded_data = []
        for _, row in df.iterrows():
            date_str = row['受渡日']
            time_code = row['時刻コード']  # 1=00:00-01:00, 2=01:00-02:00, ..., 48=23:00-24:00
            price = row['エリアプライス北海道(円/kWh)']

            # 時刻コードから開始時刻を計算
            if time_code <= 47:
                start_hour = time_code - 1
                base_date = pd.to_datetime(date_str)
            else:
                start_hour = 23
                base_date = pd.to_datetime(date_str)

            # 30分間隔で2つのデータポイントを作成（00分と30分）
            for minute in [0, 30]:
                timestamp = base_date + pd.Timedelta(hours=start_hour, minutes=minute)
                expanded_data.append({
                    'datetime': timestamp,
                    'price_yen_per_kWh': price
                })
        return expanded_data

    # 2024年度データを読み込み
    df_2024 = pd.read_csv(path, encoding='shift_jis')
    expanded_2024 = process_spot_data(df_2024)

    # 2023年度データを読み込み（2024年1~3月をカバー）
    try:
        df_2023 = pd.read_csv(path_2023, encoding='shift_jis')
        expanded_2023 = process_spot_data(df_2023)
        # 両方を結合
        all_data = expanded_2023 + expanded_2024
    except Exception as e:
        print(f'Warning: Could not load 2023 data ({e}), using 2024 data only')
        all_data = expanded_2024

    price_df = pd.DataFrame(all_data)
    # 重複を除去（同じ時刻の重複データがある場合）
    price_df = price_df.drop_duplicates(subset=['datetime'])
    price_df.set_index('datetime', inplace=True)
    price_df.sort_index(inplace=True)
    # インデックスの重複も除去（最初のものを保持）
    price_df = price_df[~price_df.index.duplicated(keep='first')]

    return price_df


def read_sample_excel(path, sheet_name='30分値'):
    path = unicodedata.normalize('NFC', path)
    xls = pd.ExcelFile(path)
    df = pd.read_excel(xls, sheet_name=sheet_name, header=0)
    # Drop rows where 消費電力量 is non-numeric (unit row etc.)
    col = '消費電力量'
    if col not in df.columns:
        raise KeyError(f"Expected column '{col}' in sheet '{sheet_name}'")
    # Remove header/unit rows: keep rows where 消費電力量 can be converted to numeric
    df = df[df[col].apply(lambda x: is_number(x))]
    df = df.copy()
    # If 発電量 (PV) column exists, ensure numeric, otherwise fill with zeros
    pv_col = '発電量'
    if pv_col in df.columns:
        df = df[df[pv_col].apply(lambda x: is_number(x)) | df[pv_col].isnull()]
        df[pv_col] = pd.to_numeric(df[pv_col], errors='coerce').fillna(0.0)
    else:
        # create PV column with zeros to simplify downstream logic
        df[pv_col] = 0.0

    # Build datetime
    df['datetime'] = pd.to_datetime(df['日付'].astype(str) + ' ' + df['時刻'].astype(str))
    df.set_index('datetime', inplace=True)
    # Ensure numeric
    df[col] = pd.to_numeric(df[col])

    # Excelの30分エネルギー[kWh] → 平均電力[kW]へ変換（Δt=0.5h なので×2）
    df['consumption_kW'] = df[col] * 2.0
    df['pv_kW'] = df[pv_col] * 2.0

    return df


def is_number(x):
    try:
        float(x)
        return True
    except Exception:
        return False


def calculate_hokkaido_electricity_cost(energy_kWh_monthly, peak_demand_kW, month, year=2024, plan_type='hokkaido_basic'):
    """
    北海道電力の電気料金を計算

    Args:
        energy_kWh_monthly: 月間電力使用量 (kWh)
        peak_demand_kW: 月間最大需要電力 (kW) - 契約電力として使用
        month: 月 (1-12)
        year: 年
        plan_type: 'hokkaido_basic' or 'market_linked'

    Returns:
        dict with 'basic_charge', 'energy_charge', 'fuel_adjustment', 'renewable_levy', 'total'
    """
    # 料金単価 (2024年4月1日実施 → 2025年10月1日実施)
    if year == 2024:
        basic_rate_yen_per_kW = 2829.60  # 2024年4月1日実施
        energy_rate_yen_per_kWh = 21.51  # 2024年4月1日実施
    else:  # 2025年以降
        basic_rate_yen_per_kW = 2880.20  # 2025年10月1日実施
        energy_rate_yen_per_kWh = 21.62  # 2025年10月1日実施

    # 基本料金: 契約電力(kW) × 料金単価(円/kW) × 0.85 × 12か月 / 12 (月割)
    basic_charge = peak_demand_kW * basic_rate_yen_per_kW * 0.85

    # 燃料費調整額 (2024年の月別データ)
    fuel_adjustment_rates = {
        1: -8.76, 2: -8.59, 3: -8.56, 4: -8.85, 5: -9.02, 6: -7.47,
        7: -5.69, 8: -5.69, 9: -9.60, 10: -9.47, 11: -8.06, 12: -5.83
    }
    fuel_adjustment_rate = fuel_adjustment_rates.get(month, 0.0)

    # 再エネ賦課金
    renewable_levy_rate = 3.98  # 円/kWh

    if plan_type == 'hokkaido_basic':
        # 北海道電力基本プラン
        energy_charge = energy_kWh_monthly * energy_rate_yen_per_kWh
        fuel_adjustment = energy_kWh_monthly * fuel_adjustment_rate
        renewable_levy = energy_kWh_monthly * renewable_levy_rate
    else:  # market_linked
        # 市場価格連動プランの場合、energy_chargeは別途JEPX価格で計算
        energy_charge = 0.0  # 呼び出し元でJEPX価格を加算
        fuel_adjustment = 0.0  # 市場価格連動では燃料費調整額なし
        renewable_levy = energy_kWh_monthly * renewable_levy_rate

    total = basic_charge + energy_charge + fuel_adjustment + renewable_levy

    return {
        'basic_charge': basic_charge,
        'energy_charge': energy_charge,
        'fuel_adjustment': fuel_adjustment,
        'renewable_levy': renewable_levy,
        'total': total
    }


def build_and_solve_horizon(demand_kW, bF0, params, pv_kW=None, time_limit=60, debug=False, skip_groups=None, buy_prices=None):
    # demand_kW: array-like length H
    # buy_prices: array-like length H with prices for each time step (optional)
    H = len(demand_kW)
    model = Model('rolling_horizon')
    # set time limit
    try:
        model.setRealParam('limits/time', float(time_limit))
    except Exception:
        try:
            model.setParam('limits/time', time_limit)
        except Exception:
            pass

    M = 1e6

    # variables (mirror original structure)
    sBY = {k: model.addVar(vtype='C', name=f'sBY_{k}', lb=0) for k in range(H)}
    sSL = {k: model.addVar(vtype='C', name=f'sSL_{k}', lb=0) for k in range(H)}

    # 契約電力変数（最大買電電力）
    sBYMAX = model.addVar(vtype='C', name='sBYMAX', lb=0)

    # solar
    # gP1: available (exogenous) PV generation for each time step (kW)
    if pv_kW is None:
        gP1 = {k: 0.0 for k in range(H)}
    else:
        # allow pv_kW to be list/array-like
        gP1 = {k: float(pv_kW[k]) if k < len(pv_kW) else 0.0 for k in range(H)}
    gP2 = {k: model.addVar(vtype='C', name=f'gP2_{k}', lb=0) for k in range(H)}

    dA1 = {k: model.addVar(vtype='C', name=f'dA1_{k}', lb=0) for k in range(H)}

    bF = {k: model.addVar(vtype='C', name=f'bF_{k}', lb=0) for k in range(H)}
    xFC1 = {k: model.addVar(vtype='C', name=f'xFC1_{k}', lb=0) for k in range(H)}
    xFC2 = {k: model.addVar(vtype='C', name=f'xFC2_{k}', lb=0) for k in range(H)}
    xFD1 = {k: model.addVar(vtype='C', name=f'xFD1_{k}', lb=0) for k in range(H)}
    xFD2 = {k: model.addVar(vtype='C', name=f'xFD2_{k}', lb=0) for k in range(H)}

    # 非同時充放電制約用の二値変数
    # z[k] = 1: 充電可能, z[k] = 0: 放電可能
    z = {k: model.addVar(vtype='B', name=f'z_charge_{k}') for k in range(H)}

    # knowns
    dA2 = demand_kW

    # 時間別価格の設定（buy_pricesが指定されない場合は基本料金計算を含む）
    if buy_prices is not None and len(buy_prices) == H:
        # 市場価格連動プランまたは詳細な時間別価格が指定された場合
        price_per_time = buy_prices
    else:
        # 北海道電力基本プランの場合、電力量料金のみを使用
        # （基本料金は別途月間で計算）
        year = params.get('year', 2024)
        if year == 2024:
            energy_rate = 21.51  # 2024年料金
        else:
            energy_rate = 21.62  # 2025年料金

        # 月を取得（time indexが利用可能な場合）
        month = params.get('month', 1)

        # 燃料費調整額（2024年月別）
        fuel_adjustment_rates = {
            1: -8.76, 2: -8.59, 3: -8.56, 4: -8.85, 5: -9.02, 6: -7.47,
            7: -5.69, 8: -5.69, 9: -9.60, 10: -9.47, 11: -8.06, 12: -5.83
        }
        fuel_adjustment = fuel_adjustment_rates.get(month, 0.0)

        # 再エネ賦課金
        renewable_levy = 3.98

        # 北海道電力基本プランの電力量料金
        total_energy_rate = energy_rate + fuel_adjustment + renewable_levy
        price_per_time = [total_energy_rate] * H

    # objective - 基本料金と電力量料金の両方を考慮
    # 基本料金: 契約電力 × 2829.60円/kW × 0.85 × 12ヶ月
    # 電力量料金: 時間別価格 × 買電量 × 0.5時間

    # 基本料金の重み付け係数
    # 1ヶ月の予測期間(H時刻)から年間への換算
    basic_charge_rate = 2829.60 * 0.85  # 円/kW/月
    # MPCの予測期間(30分×Hステップ)を月数に換算
    horizon_hours = H * 0.5  # 時間単位
    horizon_months = horizon_hours / (24 * 30)  # 概算の月数
    # 年間基本料金への換算係数
    basic_charge_weight = basic_charge_rate * 12 * horizon_months

    # 売電価格: 逆潮流不可の場合は0円/kWh
    sell_price = params.get('sell_price', 0.0)
    pSL = [sell_price] * H if isinstance(sell_price, (int, float)) else params.get('pSL', [0.0] * H)

    # 目的関数: 基本料金 + 電力量料金
    # 30分間隔なので0.5をかけて時間単位に変換
    model.setObjective(
        basic_charge_weight * sBYMAX +
        sum(price_per_time[k] * sBY[k] * 0.5 - pSL[k] * sSL[k] * 0.5 for k in range(H)),
        'minimize'
    )

    # constraints (follow original ordering and equations)
    if skip_groups is None:
        skip_groups = []

    for k in range(H):
        # electric balance: available PV (gP2) + sBY - sSL - xFC1 + xFD2 - dA1 == 0
        if 'balance' not in skip_groups:
            model.addCons(gP2[k] + sBY[k] - sSL[k] - xFC1[k] + xFD2[k] - dA1[k] == 0)

        # 契約電力制約: 各時刻の買電が契約電力以下
        model.addCons(sBY[k] <= sBYMAX)

        # solar conversion inequality: gP2 <= gP1
        # PV発電量をそのまま利用可能（過剰な場合は必要な分だけ使う）
        if 'solar_conv' not in skip_groups:
            model.addCons(gP2[k] <= gP1[k])

        # demand conversion (use equality like original)
        if 'demand_conv' not in skip_groups:
            model.addCons(dA2[k] == params.get('alpha_DA', 0.98) * dA1[k])

        # battery SOC update (with 0.5h time step)
        if 'soc_update' not in skip_groups:
            if k > 0:
                # bF[k] = bF[k-1] + xFC2[k] * 0.5 - xFD1[k] * 0.5
                # SOC更新: 前ステップのSOC + 充電エネルギー - 放電エネルギー
                # xFC2, xFD1 は[kW]なので、0.5h をかけて[kWh]へ変換
                model.addCons(bF[k] == bF[k - 1] + 0.5 * xFC2[k] - 0.5 * xFD1[k])
            else:
                    # initial SOC
                    # ensure bF0 is numeric; fall back to half of capacity when missing
                    if not isinstance(bF0, (int, float)):
                        param_bF0 = params.get('bF0', None)
                        if isinstance(param_bF0, (int, float)):
                            try:
                                bF0_val = float(param_bF0)
                            except Exception:
                                bF0_val = float(params['bF_max'] * 0.5)
                        else:
                            bF0_val = float(params['bF_max'] * 0.5)
                    else:
                        bF0_val = float(bF0)
                    # 初期SOC制約 - k=0の場合のみ
                    if k == 0:
                        model.addCons(bF[0] == bF0_val + 0.5 * xFC2[0] - 0.5 * xFD1[0])

        # battery bounds and charge/discharge limits
        if 'battery_bounds' not in skip_groups:
            model.addCons(bF[k] <= params.get('bF_max', 860))
            model.addCons(bF[k] >= 0.0)  # バッテリー残量は非負
        if 'charge_eq' not in skip_groups:
            model.addCons(xFC2[k] == params.get('alpha_FC', 0.98) * xFC1[k])
            model.addCons(xFD2[k] == params.get('alpha_FD', 0.98) * xFD1[k])
        if 'charge_limits' not in skip_groups:
            model.addCons(xFC2[k] <= params.get('aFC', 400))
            model.addCons(xFD1[k] <= params.get('aFD', 400))

        # 非同時充放電制約: 充電と放電を同時に行わない
        if 'mutual_exclusion' not in skip_groups:
            # z[k] = 1 のとき充電可能、z[k] = 0 のとき放電可能
            model.addCons(xFC1[k] <= M * z[k])
            model.addCons(xFD1[k] <= M * (1 - z[k]))

        # buy/sell constraints
        if 'buy_sell' not in skip_groups:
            # 売電制約: 逆潮流不可の場合は上限を0に設定
            sell_max = params.get('sSLMAX', M)
            model.addCons(sSL[k] <= sell_max)

        # redundant bounds from original - skip duplicate bF_max constraint
        if 'redundant_bounds' not in skip_groups:
            pass  # bF bounds already handled above

    # If debugging, return the constructed model and variable dictionaries before optimizing
    if debug:
        return model, {
            'sBY': sBY, 'sSL': sSL, 'gP2': gP2,
            'dA1': dA1,
            'bF': bF, 'xFC1': xFC1, 'xFC2': xFC2, 'xFD1': xFD1, 'xFD2': xFD2,
            'params': params, 'demand_kW': demand_kW
        }

    # optimize
    try:
        model.optimize()
    except Exception as e:
        print('Error during model.optimize():', e)
        traceback.print_exc()

    # collect results
    res = {k: [0.0] * H for k in ['sBY', 'sSL', 'xFC1', 'xFC2', 'xFD1', 'xFD2']}
    # Initialize bF with proper initial SOC value even for infeasible cases
    if isinstance(bF0, (int, float)):
        bF0_val = float(bF0)
    else:
        bF0_val = float(params.get('bF0', params['bF_max'] * 0.5))
    res['bF'] = [bF0_val] * H  # Initialize with proper SOC value
    # include gP2 in results to report how much PV was used
    res['gP2'] = [0.0] * H
    try:
        status = model.getStatus()
    except Exception as exc:
        print(f'Failed to get status: {exc}')
        status = 'unknown'

    # if infeasible, try a simple relaxation: allow buying up to demand (avoid infeasibility due to tight sBYMAX)
    if status == 'infeasible':
        try:
            new_ub = max(demand_kW) if len(demand_kW) > 0 else params.get('sBYMAX', 1e6)
            for k in range(H):
                try:
                    model.chgVarUb(sBY[k], new_ub)
                except Exception:
                    # try alternate API
                    try:
                        sBY[k].setUb(new_ub)
                    except Exception:
                        pass
            # reoptimize
            model.optimize()
            try:
                status = model.getStatus()
            except Exception:
                status = 'unknown'
        except Exception:
            pass

    if status == 'optimal':
        try:
            res['sBY'] = [model.getVal(sBY[k]) for k in range(H)]
            res['sSL'] = [model.getVal(sSL[k]) for k in range(H)]
            res['xFC1'] = [model.getVal(xFC1[k]) for k in range(H)]
            res['xFC2'] = [model.getVal(xFC2[k]) for k in range(H)]
            res['xFD1'] = [model.getVal(xFD1[k]) for k in range(H)]
            res['xFD2'] = [model.getVal(xFD2[k]) for k in range(H)]
            res['bF'] = [model.getVal(bF[k]) for k in range(H)]
            res['gP2'] = [model.getVal(gP2[k]) for k in range(H)]
            res['sBYMAX'] = model.getVal(sBYMAX)  # 契約電力の値も記録
        except Exception as exc:
            print(f'Failed to extract optimal solution: {exc}')
            pass
    else:
        # 最適解が見つからなかった場合はデバッグ情報を出力
        if status != 'optimal':
            print(f'Warning: Optimization status is {status}, not extracting solution values')

    return res, status


def run_rolling(df, horizon=96, control_horizon=1, time_limit=60, max_steps=None, params=None, price_data=None):
    if params is None:
        params = {}
    # provide defaults if missing
    defaults = {
        'bF_max': 860,           # Battery容量: 860kWh
        'aFC': 400,              # 充放電最大出力: 400kW
        'aFD': 400,              # 充放電最大出力: 400kW
        'bF0': 430,              # SOC初期値: 430kWh (50%)
        'alpha_DA': 0.98,        # 需要側効率
        'alpha_FC': 0.98,        # 充電効率
        'alpha_FD': 0.98,        # 放電効率
        'buy_price': 18.47,      # 北海道電力基本プラン（2024年1月）: 21.51-8.76+3.98
        'sell_price': 0.0,       # 売電価格: 逆潮流不可
        'sBYMAX': 1e6,           # 買電上限: 実質無制限
        'sSLMAX': 0.0,           # 売電上限: 逆潮流不可
        'year': 2024,            # 料金計算用年
        'month': 1,              # 料金計算用月（動的に更新される）
    }
    for k, v in defaults.items():
        params.setdefault(k, v)
    N = len(df)
    if max_steps is None:
        max_steps = N

    # Excelの30分エネルギー[kWh]は read_sample_excel() で平均電力[kW]へ変換済み
    # consumption_kW と pv_kW 列を使用
    consumption_kW_all = df['consumption_kW'].values.tolist()
    pv_kW_all = df['pv_kW'].values.tolist()

    # 実際の建物消費電力をそのまま使用（PVは最適化内で別途考慮される）
    demand_kW_all = consumption_kW_all

    # 価格データの準備
    if price_data is not None:
        # 市場価格連動プラン: JEPX価格 + 再エネ賦課金
        renewable_levy = 3.98  # 円/kWh
        # データフレームのインデックスに合わせて価格を取得
        price_kW_all = []

        # 燃料費調整額（2024年月別）- フォールバック用
        fuel_adjustment_rates = {
            1: -8.76, 2: -8.59, 3: -8.56, 4: -8.85, 5: -9.02, 6: -7.47,
            7: -5.69, 8: -5.69, 9: -9.60, 10: -9.47, 11: -8.06, 12: -5.83
        }

        for idx in df.index:
            # マイクロ秒を削除して正規化（Excelデータに含まれる可能性があるため）
            normalized_idx = idx.replace(microsecond=0)

            # JEPX価格データから取得を試みる
            if normalized_idx in price_data.index:
                jepx_price = price_data.loc[normalized_idx, 'price_yen_per_kWh']
                # Seriesが返された場合は最初の値を取得
                if isinstance(jepx_price, pd.Series):
                    jepx_price = jepx_price.iloc[0]
                price_kW_all.append(float(jepx_price) + renewable_levy)
            else:
                # JEPX価格が存在しない場合は北海道電力基本プランの料金を使用（念のため）
                month = idx.month
                energy_rate = 21.51  # 2024年料金
                fuel_adjustment = fuel_adjustment_rates.get(month, 0.0)
                total_rate = energy_rate + fuel_adjustment + renewable_levy
                price_kW_all.append(total_rate)
                print(f'Warning: No JEPX price for {normalized_idx}, using fallback rate {total_rate:.2f} yen/kWh')
    else:
        # 北海道電力基本プラン: 既に燃料費調整額と再エネ賦課金を含む
        price_kW_all = [params['buy_price']] * len(df)

    results_rows = []
    bF0 = df.get('bF0_init', None)
    if bF0 is None or not isinstance(bF0, (int, float, np.floating, np.integer)):
        bF0 = params.get('bF0', params['bF_max'] * 0.5)
    # ensure numeric
    try:
        bF0 = float(bF0)
    except Exception:
        bF0 = float(params['bF_max'] * 0.5)

    for t in range(0, min(N, max_steps)):
        H = min(horizon, N - t)
        demand_segment = demand_kW_all[t:t + H]
        pv_segment = pv_kW_all[t:t + H]
        price_segment = price_kW_all[t:t + H] if price_data is not None else None

        # 現在の時刻に基づいて月を更新（北海道電力基本プランの場合）
        current_timestamp = df.index[t]
        current_month = current_timestamp.month
        params['month'] = current_month

        # 進行状況表示（100ステップごと）
        if t % 100 == 0:
            print(f'Progress: Step {t}/{min(N, max_steps)} ({t*100//min(N, max_steps)}%) - {current_timestamp}')

        try:
            res, status = build_and_solve_horizon(demand_segment, bF0, params, pv_kW=pv_segment, time_limit=time_limit, buy_prices=price_segment)
        except Exception as e:
            print(f'Exception at rolling step t={t}:', e)
            traceback.print_exc()
            # abort rolling on exception
            break
        # apply first step decisions
        sBY0 = res['sBY'][0]
        sSL0 = res['sSL'][0]
        xFC10 = res['xFC1'][0]
        xFD10 = res['xFD1'][0]
        bF_after = res['bF'][0]
        pv_used0 = res.get('gP2', [0.0])[0]
        pv_surplus0 = max(0.0, pv_kW_all[t] - pv_used0)

        timestamp = df.index[t]
        current_price = price_kW_all[t] if price_data is not None else params['buy_price']

        # 予測期間内での契約電力(sBYMAX)を記録
        sBYMAX_horizon = res.get('sBYMAX', max(res['sBY']) if 'sBY' in res else 0.0)

        results_rows.append({
            'timestamp': timestamp,
            'consumption_kW': consumption_kW_all[t],
            'pv_kW': pv_kW_all[t],
            'demand_kW': demand_kW_all[t],
            'sBY': sBY0,
            'sSL': sSL0,
            'pv_used_kW': pv_used0,
            'pv_surplus_kW': pv_surplus0,
            'xFC1': xFC10,
            'xFD1': xFD10,
            'bF': bF_after,
            'price_yen_per_kWh': current_price,
            'sBYMAX_horizon': sBYMAX_horizon,  # 予測期間内の契約電力
            'status': str(status)
        })

        # update initial SOC for next iteration
        bF0 = bF_after
        # move forward by control_horizon steps
        # here loop increments by 1, so we just continue

    print(f'\nCompleted: {len(results_rows)} steps processed out of {min(N, max_steps)} requested')

    if len(results_rows) == 0:
        return pd.DataFrame()
    df_res = pd.DataFrame(results_rows)
    df_res.set_index('timestamp', inplace=True)
    return df_res


def save_plots_and_pdf(df_res, out_prefix='rolling_results'):
    os.makedirs('png', exist_ok=True)
    # 1) Time series: consumption, pv, pv_used, net demand
    plt.figure(figsize=(12, 4))
    ax = plt.gca()
    if 'consumption_kW' in df_res.columns:
        ax.plot(df_res.index, df_res['consumption_kW'], label='consumption_kW', color='tab:gray', linewidth=1)
    if 'pv_kW' in df_res.columns:
        ax.plot(df_res.index, df_res['pv_kW'], label='pv_kW', color='tab:orange', linewidth=1)
    if 'pv_used_kW' in df_res.columns:
        ax.plot(df_res.index, df_res['pv_used_kW'], label='pv_used_kW', color='tab:olive', linewidth=1)
    if 'demand_kW' in df_res.columns:
        ax.plot(df_res.index, df_res['demand_kW'], label='net_demand_kW', color='tab:red', linewidth=1)
    ax.set_ylabel('kW')
    ax.legend(ncol=3)
    ax.grid(alpha=0.3)
    p_timeseries = f'png/{out_prefix}_timeseries.png'
    plt.tight_layout()
    plt.savefig(p_timeseries, dpi=200)
    plt.close()

    # 2) Buy / Sell dedicated plot (sBY positive, sSL positive) stacked as separate lines
    plt.figure(figsize=(12, 3))
    ax = plt.gca()
    if 'sBY' in df_res.columns:
        ax.plot(df_res.index, df_res['sBY'], label='buy sBY (kW)', color='tab:blue')
    if 'sSL' in df_res.columns:
        ax.plot(df_res.index, df_res['sSL'], label='sell sSL (kW)', color='tab:green')
    ax.set_ylabel('kW')
    ax.set_title('Grid buy/sell (per interval)')
    ax.legend()
    ax.grid(alpha=0.3)
    p_buysell = f'png/{out_prefix}_buysell.png'
    plt.tight_layout()
    plt.savefig(p_buysell, dpi=200)
    plt.close()

    # 3) Battery: SOC and charge/discharge (xFC1: charge, xFD1: discharge)
    plt.figure(figsize=(12, 3))
    ax = plt.gca()
    if 'bF' in df_res.columns:
        ax.plot(df_res.index, df_res['bF'], label='SOC bF (kWh)', color='tab:purple')
    if 'xFC1' in df_res.columns:
        ax.bar(df_res.index, df_res['xFC1'], width=0.02, label='charge xFC1 (kW)', color='tab:cyan', alpha=0.6)
    if 'xFD1' in df_res.columns:
        ax.bar(df_res.index, -df_res['xFD1'], width=0.02, label='discharge xFD1 (kW)', color='tab:orange', alpha=0.6)
    ax.set_ylabel('kW / kWh')
    ax.set_title('Battery SOC and charge/discharge (first-step)')
    ax.legend(ncol=2)
    ax.grid(alpha=0.3)
    p_battery = f'png/{out_prefix}_battery.png'
    plt.tight_layout()
    plt.savefig(p_battery, dpi=200)
    plt.close()

    # 4) PV stacked usage: pv_used vs pv_surplus (area) to visualise how PV is allocated
    plt.figure(figsize=(12, 3))
    ax = plt.gca()
    if 'pv_used_kW' in df_res.columns:
        used = df_res['pv_used_kW'].fillna(0.0)
    else:
        used = pd.Series(0.0, index=df_res.index)
    if 'pv_surplus_kW' in df_res.columns:
        surplus = df_res['pv_surplus_kW'].fillna(0.0)
    else:
        surplus = (df_res['pv_kW'].fillna(0.0) - used).clip(lower=0.0)
    ax.stackplot(df_res.index, used, surplus, labels=['pv_used_kW', 'pv_surplus_kW'], colors=['tab:olive', 'tab:gray'], alpha=0.8)
    ax.set_ylabel('kW')
    ax.set_title('PV allocation: used vs surplus')
    ax.legend()
    ax.grid(alpha=0.2)
    p_pvstack = f'png/{out_prefix}_pvstack.png'
    plt.tight_layout()
    plt.savefig(p_pvstack, dpi=200)
    plt.close()

    # 5) Summary metrics as a small table figure
    total_intervals = len(df_res)
    interval_h = 0.5
    def safe_sum(col):
        return float(df_res[col].fillna(0.0).sum()) if col in df_res.columns else 0.0

    total_pv_kwh = safe_sum('pv_kW') * interval_h
    total_pv_used_kwh = safe_sum('pv_used_kW') * interval_h
    total_sold_kwh = safe_sum('sSL') * interval_h
    total_bought_kwh = safe_sum('sBY') * interval_h
    total_batt_charged_kwh = safe_sum('xFC1') * interval_h
    total_batt_discharged_kwh = safe_sum('xFD1') * interval_h

    summary_text = [
        f'intervals: {total_intervals} (each {interval_h} h)',
        f'total PV generation: {total_pv_kwh:.2f} kWh',
        f'PV used: {total_pv_used_kwh:.2f} kWh',
        f'sold (sSL): {total_sold_kwh:.2f} kWh',
        f'bought (sBY): {total_bought_kwh:.2f} kWh',
        f'batt charged (xFC1): {total_batt_charged_kwh:.2f} kWh',
        f'batt discharged (xFD1): {total_batt_discharged_kwh:.2f} kWh',
    ]

    plt.figure(figsize=(8, 3))
    plt.axis('off')
    plt.text(0.01, 0.99, 'Summary', fontsize=14, weight='bold', va='top')
    for i, line in enumerate(summary_text):
        plt.text(0.01, 0.9 - i * 0.13, line, fontsize=10, va='top')
    p_summary = f'png/{out_prefix}_summary.png'
    plt.tight_layout()
    plt.savefig(p_summary, dpi=200)
    plt.close()

    # make a PDF that includes all generated images in a 2-column grid per page
    images = [p_timeseries, p_buysell, p_battery, p_pvstack, p_summary]
    pdf = FPDF(orientation='L', unit='mm', format='A4')  # landscape for better width
    pdf.set_auto_page_break(True, margin=10)

    # grid parameters (A4 landscape ~ 297 x 210 mm)
    margin = 10
    gap = 5
    col_w = (297 - 2 * margin - gap) / 2
    row_h = (210 - 2 * margin - gap) / 2

    grid_imgs = images[:-1]  # leave last (summary) for its own page
    for i in range(0, len(grid_imgs), 4):
        page_imgs = grid_imgs[i:i+4]
        pdf.add_page()
        pdf.set_font('Arial', size=12)
        pdf.cell(0, 8, 'Rolling Optimization Figures', ln=True, align='C')
        # place up to 4 images in 2x2 grid
        for j, img in enumerate(page_imgs):
            row = j // 2
            col = j % 2
            x = margin + col * (col_w + gap)
            # y offset: leave space for title (8+2 mm)
            y = margin + 10 + row * (row_h + gap)
            # fit image into cell preserving aspect (use width col_w)
            try:
                pdf.image(img, x=x, y=y, w=col_w)
            except Exception:
                # fallback: try smaller width
                try:
                    pdf.image(img, x=x, y=y, w=col_w * 0.9)
                except Exception:
                    pass

    # add summary on its own page (portrait style effect)
    pdf.add_page()
    pdf.set_font('Arial', size=12)
    pdf.cell(0, 8, 'Summary', ln=True, align='C')
    try:
        pdf.image(p_summary, x=20, y=25, w=257)  # fit landscape width
    except Exception:
        try:
            pdf.image(p_summary, x=30, y=30, w=237)
        except Exception:
            pass

    out_pdf = f'{out_prefix}.pdf'
    pdf.output(out_pdf)
    return images, out_pdf


def generate_monthly_figures():
    """
    月別統計グラフを生成する関数
    results/rolling_results.csvから読み込んで、png/ディレクトリにグラフを保存
    """
    import json

    # データ読み込み
    df = pd.read_csv('results/rolling_results.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['month'] = df['timestamp'].dt.month
    df['pv_curtailed'] = df['pv_kW'] - df['pv_used_kW']

    # 月別集計
    monthly_stats = df.groupby('month').agg({
        'consumption_kW': lambda x: (x * 0.5).sum(),  # kWh
        'pv_kW': lambda x: (x * 0.5).sum(),  # kWh
        'pv_used_kW': lambda x: (x * 0.5).sum(),  # kWh
        'pv_curtailed': lambda x: (x * 0.5).sum(),  # kWh
        'sBY': lambda x: (x * 0.5).sum(),  # kWh
        'bF': 'mean'  # 平均SOC
    }).round(2)

    monthly_stats.columns = ['消費電力量', 'PV発電量', 'PV使用量', 'PV抑制量', '買電量', '平均SOC']

    # 最大買電電力（契約電力）も月別に集計
    monthly_max_buy = df.groupby('month')['sBY'].max()

    # 図の作成
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('月別エネルギー統計（2024年）', fontsize=16, fontweight='bold')

    months = monthly_stats.index
    month_labels = [f'{m}月' for m in months]

    # 1. 月別電力量
    ax1 = axes[0, 0]
    width = 0.35
    x = np.arange(len(months))

    bars1 = ax1.bar(x - width/2, monthly_stats['消費電力量'], width, label='消費電力量', color='#2E86AB')
    bars2 = ax1.bar(x + width/2, monthly_stats['買電量'], width, label='買電量', color='#A23B72')

    ax1.set_xlabel('月', fontsize=12)
    ax1.set_ylabel('電力量 (kWh)', fontsize=12)
    ax1.set_title('月別消費電力量と買電量', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 月別PV利用状況
    ax2 = axes[0, 1]
    bars1 = ax2.bar(x - width/2, monthly_stats['PV使用量'], width, label='PV使用量', color='#F18F01')
    bars2 = ax2.bar(x + width/2, monthly_stats['PV抑制量'], width, label='PV抑制量', color='#C73E1D')

    ax2.set_xlabel('月', fontsize=12)
    ax2.set_ylabel('電力量 (kWh)', fontsize=12)
    ax2.set_title('月別PV発電・抑制状況', fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(month_labels)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 月別PV自給率とPV利用率
    ax3 = axes[1, 0]
    pv_self_sufficiency = (monthly_stats['PV使用量'] / monthly_stats['消費電力量'] * 100).fillna(0)
    pv_utilization = (monthly_stats['PV使用量'] / monthly_stats['PV発電量'] * 100).fillna(0)

    line1 = ax3.plot(months, pv_self_sufficiency, marker='o', linewidth=2, markersize=8,
                     label='PV自給率', color='#06A77D')
    line2 = ax3.plot(months, pv_utilization, marker='s', linewidth=2, markersize=8,
                     label='PV利用率', color='#F18F01')

    ax3.set_xlabel('月', fontsize=12)
    ax3.set_ylabel('割合 (%)', fontsize=12)
    ax3.set_title('月別PV自給率・利用率', fontsize=13, fontweight='bold')
    ax3.set_xticks(months)
    ax3.set_xticklabels(month_labels)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, 105)

    # 4. 年間蓄電池SOC推移
    ax4 = axes[1, 1]

    # 全データをプロット(サンプリングして表示を軽くする)
    sample_rate = 48  # 1日1点(30分×48ステップ=24時間)
    df_sample = df.iloc[::sample_rate].copy()

    line1 = ax4.plot(df_sample['timestamp'], df_sample['bF'], linewidth=1.5, color='#4ECDC4', alpha=0.8)

    ax4.set_xlabel('月', fontsize=12)
    ax4.set_ylabel('蓄電池SOC (kWh)', fontsize=12)
    ax4.set_title('年間蓄電池SOC推移', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, 900)  # 蓄電池容量860kWhに余裕を持たせる

    # X軸を月表示に
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m月'))
    ax4.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=0)

    # 容量上限を示す線
    ax4.axhline(y=860, color='red', linestyle='--', linewidth=1, alpha=0.5, label='容量上限 (860kWh)')
    ax4.legend(loc='upper right')

    plt.tight_layout()
    os.makedirs('png', exist_ok=True)
    plt.savefig('png/monthly_statistics.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 月別契約電力（最大買電電力）
    fig2, ax = plt.subplots(1, 1, figsize=(10, 6))
    bars = ax.bar(months, monthly_max_buy, color='#A23B72', alpha=0.8)
    ax.axhline(y=monthly_max_buy.max(), color='red', linestyle='--', linewidth=2,
               label=f'年間最大: {monthly_max_buy.max():.1f} kW')

    ax.set_xlabel('月', fontsize=12)
    ax.set_ylabel('最大買電電力 (kW)', fontsize=12)
    ax.set_title('月別契約電力（最大買電電力）', fontsize=14, fontweight='bold')
    ax.set_xticks(months)
    ax.set_xticklabels(month_labels)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    # 値をバーの上に表示
    for i, (month, value) in enumerate(zip(months, monthly_max_buy)):
        ax.text(month, value + 5, f'{value:.1f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig('png/monthly_contract_power.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 月別統計をCSVに保存
    monthly_stats['最大買電電力'] = monthly_max_buy
    os.makedirs('data', exist_ok=True)
    monthly_stats.to_csv('data/monthly_statistics.csv', encoding='utf-8-sig')


def main():
    """
    年間合計の電気料金最小化を目的とした ローリング最適化

    対象プラン:
    1. 北海道電力の基本プラン (高圧電力、一般料金) - 固定価格モード
    2. 市場価格連動プラン - スポット価格モード (基本料金は北海道電力と同じと仮定)

    導入条件:
    - 地域: 北海道/十勝地方
    - PV: 250kW (南向き40度設置)
    - Battery: 860kWh (430kWh×2), 充放電400kW
    - 売電: 逆潮流不可
    - 価格データ: JEPX 2024年データ使用
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--excel', default='data/20250901サンプルデータ.xlsx')
    parser.add_argument('--sheet', default='30分値')
    parser.add_argument('--horizon', type=int, default=96)  # 48時間先まで予測（96ステップ）
    parser.add_argument('--time_limit', type=float, default=10.0)
    parser.add_argument('--max_steps', type=int, default=None)
    parser.add_argument('--price_data', default='data/spot_summary_2024.csv', help='JEPX spot price data file (2024年度)')
    parser.add_argument('--price_data_2023', default='data/spot_summary_2023.csv', help='JEPX spot price data file (2023年度、2024年1-3月用)')
    parser.add_argument('--use_fixed_price', action='store_true', help='Use fixed price (北海道電力基本プラン) instead of market price (市場価格連動プラン)')

    # データ検証用オプション
    parser.add_argument('--validate', action='store_true', help='最適化結果の包括的な検証を実行')
    parser.add_argument('--verify-dates', nargs='+', metavar='DATE', help='特定日付のデータを検証 (例: 2024-06-02 2024-03-08)')
    parser.add_argument('--find-representative', action='store_true', help='PV余剰+フル充電の代表日を検索')
    parser.add_argument('--csv', default='results/rolling_results.csv', help='検証対象のCSVファイルパス (デフォルト: results/rolling_results.csv)')

    args = parser.parse_args()

    # 検証モードの実行 (最適化を実行せずに終了)
    if args.validate or args.verify_dates or args.find_representative:
        if args.validate:
            print("データ検証を実行中...")
            validate_results(csv_path=args.csv, output_report=True)

        if args.verify_dates:
            print(f"\n特定日付を検証中: {', '.join(args.verify_dates)}")
            verify_specific_dates(csv_path=args.csv, dates_to_check=args.verify_dates)

        if args.find_representative:
            print("\n代表日を検索中...")
            find_representative_day(csv_path=args.csv)

        import sys
        sys.exit(0)

    params = {
        # 導入内容: 北海道/十勝地方の設定
        'pv_capacity': 250,      # PV容量: 250kW (南向き40度設置)
        'bF_max': 860,           # Battery容量: 860kWh (430kWh×2)
        'aFC': 400,              # 充放電最大出力: 400kW
        'aFD': 400,              # 充放電最大出力: 400kW
        'bF0': 430,              # SOC初期値: 430kWh (50%)
        'alpha_DA': 0.98,        # 需要側効率
        'alpha_FC': 0.98,        # 充電効率
        'alpha_FD': 0.98,        # 放電効率
        'buy_price': 24.44,      # 固定買電価格 (円/kWh)
        'sell_price': 0.0,       # 売電価格: 0円/kWh (逆潮流不可)
        'sBYMAX': 1e6,           # 買電上限: 実質無制限
        'sSLMAX': 0.0,           # 売電上限: 0kW (逆潮流不可)
        'year': 2024,            # データ年: 2024年
    }

    print('Reading', args.excel, 'sheet', args.sheet)
    df = read_sample_excel(args.excel, sheet_name=args.sheet)

    # 2025年データを2024年として扱う（2/29を除外）
    def remap_year(ts):
        try:
            return ts.replace(year=2024)
        except ValueError:  # 2/29の場合
            return pd.NaT

    df.index = df.index.map(remap_year)
    df = df[df.index.notna()]  # NaTを削除

    print('Rows:', len(df))

    # 価格データの読み込み
    price_data = None
    if not args.use_fixed_price:
        try:
            print(f'\nJEPX価格データ読み込み中...')
            print(f'  - 2024年4-12月データ: {args.price_data}')
            print(f'  - 2024年1-3月データ: {args.price_data_2023}')
            price_data = read_spot_price_data(args.price_data, args.price_data_2023)
            print(f'✓ Price data loaded: {len(price_data)} records')
            print(f'  Price range: {price_data["price_yen_per_kWh"].min():.2f} - {price_data["price_yen_per_kWh"].max():.2f} yen/kWh')
            print(f'  Average price: {price_data["price_yen_per_kWh"].mean():.2f} yen/kWh')
        except Exception as e:
            print(f'Failed to load spot price data: {e}')
            print('Falling back to fixed price mode')
            args.use_fixed_price = True

    os.makedirs('results', exist_ok=True)

    # ========================================
    # 1️⃣ 北海道電力基本プランで最適化
    # ========================================
    print('\n' + '='*70)
    print('1️⃣  北海道電力基本プランで最適化実行中...')
    print('='*70)
    print('プラン: 北海道電力基本プラン (電力量料金+燃料費調整額+再エネ賦課金)')

    df_res_hokkaido = run_rolling(df, horizon=args.horizon, control_horizon=1, time_limit=args.time_limit,
                                   max_steps=args.max_steps, params=params, price_data=None)

    out_csv_hokkaido = 'results/rolling_results_hokkaido_basic.csv'
    df_res_hokkaido.to_csv(out_csv_hokkaido)
    print(f'✓ Saved {out_csv_hokkaido}')

    # 北海道電力プランの料金計算
    hokkaido_costs = calculate_single_plan_costs(df_res_hokkaido, None, 'hokkaido_basic')

    # ========================================
    # 2️⃣ 市場価格連動プランで最適化
    # ========================================
    if not args.use_fixed_price and price_data is not None:
        print('\n' + '='*70)
        print('2️⃣  市場価格連動プランで最適化実行中...')
        print('='*70)
        print('プラン: 市場価格連動プラン (JEPX spot price data)')

        df_res_market = run_rolling(df, horizon=args.horizon, control_horizon=1, time_limit=args.time_limit,
                                     max_steps=args.max_steps, params=params, price_data=price_data)

        out_csv_market = 'results/rolling_results_market_linked.csv'
        df_res_market.to_csv(out_csv_market)
        print(f'✓ Saved {out_csv_market}')

        # 市場価格連動プランの料金計算
        market_costs = calculate_single_plan_costs(df_res_market, price_data, 'market_linked')

        # 両プランの結果を統合（デフォルトは市場価格連動プランの結果を使用）
        df_res = df_res_market
        out_csv = out_csv_market
    else:
        # 固定価格モードの場合は北海道電力プランのみ
        market_costs = None
        df_res = df_res_hokkaido
        out_csv = out_csv_hokkaido

    # メインの結果CSVを保存（後方互換性のため）
    df_res.to_csv('results/rolling_results.csv')
    print(f'\n✓ Saved results/rolling_results.csv (メイン結果)')

    # ========================================
    # 3️⃣ 年間料金比較
    # ========================================
    print('\n' + '='*70)
    print('3️⃣  年間電気料金比較')
    print('='*70)

    print(f"\n北海道電力基本プラン: {hokkaido_costs['total']:,.0f}円")
    print(f"  - 基本料金: {hokkaido_costs['basic_charge']:,.0f}円")
    print(f"  - 電力量料金: {hokkaido_costs['energy_charge']:,.0f}円")
    print(f"  - 燃料費調整額: {hokkaido_costs['fuel_adjustment']:,.0f}円")
    print(f"  - 再エネ賦課金: {hokkaido_costs['renewable_levy']:,.0f}円")
    print(f"  - 契約電力: {hokkaido_costs['peak_demand_kW']:.2f}kW")

    if market_costs is not None:
        print(f"\n市場価格連動プラン: {market_costs['total']:,.0f}円")
        print(f"  - 基本料金: {market_costs['basic_charge']:,.0f}円")
        print(f"  - 市場価格料金: {market_costs['energy_charge']:,.0f}円")
        print(f"  - 再エネ賦課金: {market_costs['renewable_levy']:,.0f}円")
        print(f"  - 契約電力: {market_costs['peak_demand_kW']:.2f}kW")

        savings = hokkaido_costs['total'] - market_costs['total']
        savings_pct = (savings / hokkaido_costs['total']) * 100
        print(f"\n差額: {savings:,.0f}円 ({savings_pct:.2f}%)")
        print(f"→ 市場価格連動プランが{'安い' if savings > 0 else '高い'}!")

        # 比較結果をJSON保存
        comparison_data = {
            'hokkaido_basic': hokkaido_costs,
            'market_linked': market_costs,
            'difference': savings,
            'percent_diff': savings_pct,
            'cheaper_plan': 'market_linked' if savings > 0 else 'hokkaido_basic'
        }
    else:
        comparison_data = {
            'hokkaido_basic': hokkaido_costs,
            'message': 'Fixed price mode - only Hokkaido Basic plan calculated'
        }

    # 年間料金比較データをJSONファイルに保存
    import json
    json_path = 'results/annual_cost_comparison.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, ensure_ascii=False, indent=2)
    print(f'\n✓ Saved annual cost comparison to {json_path}')

    # グラフ生成（市場価格連動プランの結果を使用）
    print('\n' + '='*70)
    print('4️⃣  グラフ生成中...')
    print('='*70)

    images, out_pdf = save_plots_and_pdf(df_res)
    print('✓ Saved images:', images)
    print('✓ Saved PDF:', out_pdf)

    # 月別統計グラフの自動生成
    try:
        generate_monthly_figures()
        print('✓ 月別統計グラフの生成が完了しました')
    except Exception as e:
        print(f'⚠ 月別統計グラフの生成に失敗しました: {e}')
        traceback.print_exc()

    # 年間グラフの自動生成
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        annual_graph_script = os.path.join(script_dir, 'generate_annual_graph.py')
        subprocess.run(['python3', annual_graph_script], check=True)
        print('✓ 年間グラフ（PV発電・買電・需要、SOC推移）の生成が完了しました')
    except Exception as e:
        print(f'⚠ 年間グラフの生成に失敗しました: {e}')
        traceback.print_exc()

    # 日次パターングラフの自動生成
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        daily_pattern_script = os.path.join(script_dir, 'generate_daily_pattern.py')
        subprocess.run(['python3', daily_pattern_script], check=True)
        print('✓ 日次パターングラフ（2024年5月15日）の生成が完了しました')
    except Exception as e:
        print(f'⚠ 日次パターングラフの生成に失敗しました: {e}')
        traceback.print_exc()

    # PV余剰パターングラフの自動生成（最大余剰日を自動選択）
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pv_curtailment_script = os.path.join(script_dir, 'generate_pv_curtailment_pattern.py')
        subprocess.run(['python3', pv_curtailment_script], check=True)
        print('✓ PV余剰パターングラフ（最大余剰日）の生成が完了しました')
    except Exception as e:
        print(f'⚠ PV余剰パターングラフの生成に失敗しました: {e}')
        traceback.print_exc()

    # データ保存場所のサマリーを表示
    print('\n' + '='*70)
    print('✅ すべての処理が完了しました!')
    print('='*70)
    print('\n📁 データ保存場所:')
    print('  ✓ 北海道電力プラン結果: results/rolling_results_hokkaido_basic.csv')
    if market_costs is not None:
        print('  ✓ 市場価格連動プラン結果: results/rolling_results_market_linked.csv')
    print('  ✓ メイン結果CSV: results/rolling_results.csv')
    print('  ✓ 年間料金比較JSON: results/annual_cost_comparison.json')
    print('  ✓ 基本グラフPDF: scripts/rolling_results.pdf')
    print('\n📊 すべてのグラフ (png/):')
    print('  • rolling_results_timeseries.png')
    print('  • rolling_results_buysell.png')
    print('  • rolling_results_battery.png')
    print('  • rolling_results_pvstack.png')
    print('  • rolling_results_summary.png')
    print('  • monthly_statistics.png')
    print('  • monthly_contract_power.png')
    print('  • annual_pv_buy_demand.png  (年間PV発電・買電・需要)')
    print('  • annual_soc.png  (年間SOC推移)')
    print('  • daily_battery_pattern.png  (代表的な1日の運用パターン)')
    print('  • pv_curtailment_pattern.png  (PV余剰が最大の日のパターン)')
    print('\n' + '='*70)


def calculate_single_plan_costs(df_res, price_data=None, plan_type='hokkaido_basic'):
    """
    単一プランの年間電気料金を計算

    Args:
        df_res: 最適化結果DataFrame
        price_data: JEPX価格データ (市場価格連動プラン用、Noneの場合は北海道電力プラン)
        plan_type: 'hokkaido_basic' or 'market_linked'

    Returns:
        dict: 年間料金詳細
    """
    # 月別データを集計
    df_monthly = df_res.copy()
    df_monthly['month'] = df_monthly.index.month

    # 月別電力使用量と最大需要電力を計算
    monthly_energy = df_monthly.groupby('month')['sBY'].sum() * 0.5  # 30分→kWh変換
    monthly_peak = df_monthly.groupby('month')['sBY'].max()  # 月間最大需要
    annual_peak = df_monthly['sBY'].max()  # 年間最大需要（契約電力）
    annual_buy_kWh = df_monthly['sBY'].sum() * 0.5  # 年間買電量

    if plan_type == 'hokkaido_basic' or price_data is None:
        # 北海道電力基本プラン
        total_costs = {'basic_charge': 0, 'energy_charge': 0, 'fuel_adjustment': 0, 'renewable_levy': 0}

        for month in range(1, 13):
            if month in monthly_energy.index:
                month_energy = monthly_energy[month]
                costs = calculate_hokkaido_electricity_cost(
                    month_energy, annual_peak, month, 2024, 'hokkaido_basic'
                )
                for key in total_costs:
                    total_costs[key] += costs[key]

        total_costs['total'] = sum(total_costs.values())
        total_costs['peak_demand_kW'] = annual_peak
        total_costs['annual_buy_kWh'] = annual_buy_kWh

    else:
        # 市場価格連動プラン
        df_with_prices = df_res.copy()
        price_series = price_data.reindex(df_res.index, method='nearest')
        df_with_prices['jepx_price'] = price_series['price_yen_per_kWh']

        # 市場価格での電力量料金（再エネ賦課金は含まない）
        market_energy_cost = (df_with_prices['sBY'] * df_with_prices['jepx_price'] * 0.5).sum()
        renewable_levy_cost = (df_with_prices['sBY'] * 3.98 * 0.5).sum()

        # 基本料金は北海道電力と同じ
        basic_charge_annual = annual_peak * 2829.60 * 0.85 * 12

        total_costs = {
            'basic_charge': basic_charge_annual,
            'energy_charge': market_energy_cost,
            'renewable_levy': renewable_levy_cost,
            'total': basic_charge_annual + market_energy_cost + renewable_levy_cost,
            'peak_demand_kW': annual_peak,
            'annual_buy_kWh': annual_buy_kWh
        }

    return total_costs


def calculate_annual_costs(df_res, price_data=None):
    """
    年間電気料金を計算し、両プランを比較

    Args:
        df_res: 最適化結果DataFrame
        price_data: JEPX価格データ (市場価格連動プラン用)

    Returns:
        dict: 年間料金比較結果
    """
    # 月別データを集計
    df_monthly = df_res.copy()
    df_monthly['month'] = df_monthly.index.month
    df_monthly['year'] = df_res.index[0].year

    # 月別電力使用量と最大需要電力を計算
    monthly_energy = df_monthly.groupby('month')['sBY'].sum() * 0.5  # 30分→kWh変換
    monthly_peak = df_monthly.groupby('month')['sBY'].max()  # 月間最大需要
    annual_peak = df_monthly['sBY'].max()  # 年間最大需要（契約電力）

    # 北海道電力基本プラン
    hokkaido_total = {'basic_charge': 0, 'energy_charge': 0, 'fuel_adjustment': 0, 'renewable_levy': 0}

    for month in range(1, 13):
        if month in monthly_energy.index:
            month_energy = monthly_energy[month]
            month_peak = monthly_peak[month]
            costs = calculate_hokkaido_electricity_cost(
                month_energy, annual_peak, month, 2024, 'hokkaido_basic'
            )
            for key in hokkaido_total:
                hokkaido_total[key] += costs[key]

    # 市場価格連動プラン
    market_total = {'basic_charge': 0, 'energy_charge': 0, 'renewable_levy': 0}

    if price_data is not None:
        # 実際のJEPX価格データを使用
        df_with_prices = df_res.copy()
        price_series = price_data.reindex(df_res.index, method='nearest')
        df_with_prices['jepx_price'] = price_series['price_yen_per_kWh']

        # 市場価格での電力量料金（再エネ賦課金は含まない）
        market_energy_cost = (df_with_prices['sBY'] * df_with_prices['jepx_price'] * 0.5).sum()
        renewable_levy_cost = (df_with_prices['sBY'] * 3.98 * 0.5).sum()
    else:
        # 固定価格での概算
        total_energy = monthly_energy.sum()
        market_energy_cost = total_energy * 20.0  # 概算JEPX価格
        renewable_levy_cost = total_energy * 3.98

    # 基本料金は北海道電力と同じ
    basic_charge_annual = annual_peak * 2829.60 * 0.85 * 12

    market_total = {
        'basic_charge': basic_charge_annual,
        'energy_charge': market_energy_cost,
        'renewable_levy': renewable_levy_cost,
        'total': basic_charge_annual + market_energy_cost + renewable_levy_cost
    }

    hokkaido_total['total'] = sum(hokkaido_total.values())

    return {
        'hokkaido_basic': hokkaido_total,
        'market_linked': market_total,
        'peak_demand_kW': annual_peak,
        'monthly_energy_kWh': monthly_energy.to_dict(),
        'monthly_peak_kW': monthly_peak.to_dict()
    }


if __name__ == '__main__':
    main()


def run_period_from_df(df, start=None, end=None, out_prefix='rolling_results', horizon=96, time_limit=10.0,
                       max_steps=None, params=None, price_data=None, control_horizon=1, sheet_name=None,
                       force_year=None):
    """
    Run rolling optimization on a DataFrame `df` (as returned by `read_sample_excel`) for an optional
    start/end timestamp window. Save CSV and figures/PDF using `out_prefix` and return results.

    Returns: (df_res, images, out_pdf, out_csv)
    """
    # Optionally remap the datetime index to a different year while keeping month/day/time
    df_proc = df.copy()
    if force_year is not None:
        def remap_year(ts):
            try:
                return ts.replace(year=int(force_year))
            except Exception:
                return pd.Timestamp(year=int(force_year), month=ts.month, day=ts.day, hour=ts.hour, minute=ts.minute, second=ts.second)

        df_proc.index = df_proc.index.map(remap_year)

    # slice by start/end if provided (after optional remap)
    if start is not None:
        df_proc = df_proc[df_proc.index >= pd.to_datetime(start)]
    if end is not None:
        df_proc = df_proc[df_proc.index <= pd.to_datetime(end)]

    if df_proc.empty:
        raise ValueError(f'No data in requested period: start={start}, end={end}')

    df_res = run_rolling(df_proc, horizon=horizon, control_horizon=control_horizon,
                         time_limit=time_limit, max_steps=max_steps, params=params, price_data=price_data)

    out_csv = f'{out_prefix}.csv'
    df_res.to_csv(out_csv)

    images, out_pdf = save_plots_and_pdf(df_res, out_prefix=out_prefix)
    return df_res, images, out_pdf, out_csv


def run_period_from_dates(excel_path, start, end, out_prefix='rolling_results', sheet='30分値',
                          price_file=None, use_fixed_price=False, horizon=96, time_limit=10.0,
                          max_steps=None, params=None, control_horizon=1, force_year=None):
    """
    Convenience wrapper: read Excel with `read_sample_excel`, optionally read spot price data from
    `price_file` (unless `use_fixed_price` True), then run optimization for the [start, end] window.

    Returns: (df_res, images, out_pdf, out_csv)
    """
    df = read_sample_excel(excel_path, sheet_name=sheet)
    # prepare price_data
    price_data = None
    if (not use_fixed_price) and price_file is not None:
        try:
            price_data = read_spot_price_data(price_file)
        except Exception:
            price_data = None

    return run_period_from_df(df, start=start, end=end, out_prefix=out_prefix, horizon=horizon,
                              time_limit=time_limit, max_steps=max_steps, params=params,
                              price_data=price_data, control_horizon=control_horizon, force_year=force_year)


###############################################################################
# Data Validation Module
###############################################################################

def validate_results(csv_path='results/rolling_results.csv', battery_capacity=860.0, output_report=True):
    """
    統合データ検証機能: 最適化結果の妥当性を包括的に検証

    検証項目:
    1. PV余剰が発生した日の特定とランキング (Top 10)
    2. バッテリーがフル充電された日の特定
    3. 年間統計の計算 (総買電量、平均買電、平均SOC)
    4. 特定日付のデータ検証

    Args:
        csv_path: 検証対象のCSVファイルパス
        battery_capacity: バッテリー容量 [kWh]
        output_report: Trueの場合、検証レポートを出力

    Returns:
        dict: 検証結果を含む辞書
    """
    import pandas as pd
    import numpy as np
    from pathlib import Path

    if not Path(csv_path).exists():
        print(f"警告: {csv_path} が見つかりません")
        return None

    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    df['date'] = df['datetime'].dt.date

    validation_results = {}

    # 1. PV余剰日の特定
    daily_surplus = df.groupby('date')['pv_curtail'].sum().reset_index()
    daily_surplus.columns = ['date', 'total_surplus']
    daily_surplus = daily_surplus[daily_surplus['total_surplus'] > 0].sort_values('total_surplus', ascending=False)
    validation_results['pv_surplus_days'] = daily_surplus.head(10).to_dict('records')

    # 2. フル充電日の特定
    full_charge_days = df[df['soc'] >= battery_capacity - 0.1].groupby('date').size().reset_index()
    full_charge_days.columns = ['date', 'full_charge_steps']
    full_charge_days = full_charge_days.sort_values('full_charge_steps', ascending=False)
    validation_results['full_charge_days'] = full_charge_days.head(10).to_dict('records')

    # 3. 年間統計
    total_buy = df['buy'].sum()
    avg_buy = df['buy'].mean()
    avg_soc = df['soc'].mean()
    total_pv = df['pv'].sum()
    total_pv_to_battery = df['pv_to_battery'].sum()
    total_pv_to_demand = df['pv_to_demand'].sum()
    total_demand = df['demand'].sum()
    total_surplus = df['pv_curtail'].sum()

    validation_results['annual_stats'] = {
        'total_buy_kwh': round(total_buy, 1),
        'avg_buy_kw': round(avg_buy, 2),
        'avg_soc_kwh': round(avg_soc, 2),
        'avg_soc_percent': round(avg_soc / battery_capacity * 100, 1),
        'total_pv_kwh': round(total_pv, 1),
        'total_demand_kwh': round(total_demand, 1),
        'total_pv_surplus_kwh': round(total_surplus, 1),
        'pv_utilization_percent': round((total_pv - total_surplus) / total_pv * 100, 2) if total_pv > 0 else 0
    }

    # 4. 特定日付のデータ取得 (レポート用の代表例)
    validation_results['sample_dates'] = {}

    # 最も余剰が多い日
    if len(daily_surplus) > 0:
        max_surplus_date = daily_surplus.iloc[0]['date']
        validation_results['sample_dates']['max_surplus'] = {
            'date': str(max_surplus_date),
            'data': df[df['date'] == max_surplus_date][['datetime', 'demand', 'pv', 'buy', 'soc', 'pv_curtail']].to_dict('records')
        }

    # フル充電が最も長い日
    if len(full_charge_days) > 0:
        max_full_charge_date = full_charge_days.iloc[0]['date']
        validation_results['sample_dates']['max_full_charge'] = {
            'date': str(max_full_charge_date),
            'data': df[df['date'] == max_full_charge_date][['datetime', 'demand', 'pv', 'buy', 'soc', 'pv_curtail']].to_dict('records')
        }

    # レポート出力
    if output_report:
        print("\n" + "="*80)
        print("データ検証レポート")
        print("="*80)

        print("\n【年間統計】")
        stats = validation_results['annual_stats']
        print(f"  総買電量:     {stats['total_buy_kwh']:>10,.1f} kWh")
        print(f"  平均買電:     {stats['avg_buy_kw']:>10,.2f} kW")
        print(f"  平均SOC:      {stats['avg_soc_kwh']:>10,.2f} kWh ({stats['avg_soc_percent']:.1f}%)")
        print(f"  総PV発電:     {stats['total_pv_kwh']:>10,.1f} kWh")
        print(f"  総需要:       {stats['total_demand_kwh']:>10,.1f} kWh")
        print(f"  総PV余剰:     {stats['total_pv_surplus_kwh']:>10,.1f} kWh")
        print(f"  PV利用率:     {stats['pv_utilization_percent']:>10,.2f} %")

        print("\n【PV余剰発生日 Top 10】")
        for i, day in enumerate(validation_results['pv_surplus_days'], 1):
            print(f"  {i:2d}. {day['date']}  余剰: {day['total_surplus']:>6.1f} kWh")

        print("\n【フル充電達成日 Top 10】")
        for i, day in enumerate(validation_results['full_charge_days'], 1):
            print(f"  {i:2d}. {day['date']}  フル充電ステップ数: {day['full_charge_steps']:>3d}")

        print("\n" + "="*80 + "\n")

    return validation_results


def verify_specific_dates(csv_path='results/rolling_results.csv', dates_to_check=None):
    """
    特定日付のデータを詳細に検証

    Args:
        csv_path: 検証対象のCSVファイルパス
        dates_to_check: 検証する日付のリスト (例: ['2024-06-02', '2024-03-08'])

    Returns:
        dict: 日付ごとの検証結果
    """
    import pandas as pd
    from pathlib import Path

    if not Path(csv_path).exists():
        print(f"警告: {csv_path} が見つかりません")
        return None

    if dates_to_check is None:
        dates_to_check = []

    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    df['date'] = df['datetime'].dt.date

    results = {}

    for date_str in dates_to_check:
        target_date = pd.to_datetime(date_str).date()
        day_data = df[df['date'] == target_date]

        if len(day_data) == 0:
            results[date_str] = {'error': 'データが見つかりません'}
            continue

        results[date_str] = {
            'total_demand': round(day_data['demand'].sum(), 1),
            'total_pv': round(day_data['pv'].sum(), 1),
            'total_buy': round(day_data['buy'].sum(), 1),
            'total_surplus': round(day_data['pv_curtail'].sum(), 1),
            'avg_soc': round(day_data['soc'].mean(), 1),
            'max_soc': round(day_data['soc'].max(), 1),
            'min_soc': round(day_data['soc'].min(), 1),
            'soc_at_14:00': round(day_data[day_data['datetime'].dt.hour == 14].iloc[0]['soc'], 1) if len(day_data[day_data['datetime'].dt.hour == 14]) > 0 else None,
            'soc_at_16:00': round(day_data[day_data['datetime'].dt.hour == 16].iloc[0]['soc'], 1) if len(day_data[day_data['datetime'].dt.hour == 16]) > 0 else None
        }

        print(f"\n【{date_str} のデータ】")
        print(f"  需要合計:   {results[date_str]['total_demand']:>8.1f} kWh")
        print(f"  PV合計:     {results[date_str]['total_pv']:>8.1f} kWh")
        print(f"  買電合計:   {results[date_str]['total_buy']:>8.1f} kWh")
        print(f"  余剰合計:   {results[date_str]['total_surplus']:>8.1f} kWh")
        print(f"  平均SOC:    {results[date_str]['avg_soc']:>8.1f} kWh")
        print(f"  最大SOC:    {results[date_str]['max_soc']:>8.1f} kWh")
        if results[date_str]['soc_at_14:00'] is not None:
            print(f"  14:00 SOC:  {results[date_str]['soc_at_14:00']:>8.1f} kWh")
        if results[date_str]['soc_at_16:00'] is not None:
            print(f"  16:00 SOC:  {results[date_str]['soc_at_16:00']:>8.1f} kWh")

    return results


def find_representative_day(csv_path='results/rolling_results.csv', battery_capacity=860.0,
                            min_surplus=1.0, max_surplus=10.0):
    """
    PV余剰が発生し、かつバッテリーがフル充電される「代表日」を検索

    Args:
        csv_path: 検証対象のCSVファイルパス
        battery_capacity: バッテリー容量 [kWh]
        min_surplus: 最小余剰量 [kWh]
        max_surplus: 最大余剰量 [kWh]

    Returns:
        list: 条件を満たす日付のリスト
    """
    import pandas as pd
    from pathlib import Path

    if not Path(csv_path).exists():
        print(f"警告: {csv_path} が見つかりません")
        return None

    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    df['date'] = df['datetime'].dt.date

    # 各日の余剰量とフル充電達成を集計
    daily_stats = df.groupby('date').agg({
        'pv_curtail': 'sum',
        'soc': lambda x: (x >= battery_capacity - 0.1).sum()
    }).reset_index()
    daily_stats.columns = ['date', 'total_surplus', 'full_charge_steps']

    # 条件: min_surplus <= 余剰 <= max_surplus かつ フル充電あり
    candidates = daily_stats[
        (daily_stats['total_surplus'] >= min_surplus) &
        (daily_stats['total_surplus'] <= max_surplus) &
        (daily_stats['full_charge_steps'] > 0)
    ].sort_values('total_surplus')

    print("\n【代表日候補】")
    print(f"条件: PV余剰 {min_surplus}~{max_surplus} kWh, フル充電達成")
    print("-" * 60)

    for _, row in candidates.iterrows():
        print(f"  {row['date']}  余剰: {row['total_surplus']:>6.1f} kWh, フル充電: {row['full_charge_steps']:>2d} ステップ")

    return candidates.to_dict('records')


###############################################################################
# Main execution with validation support
###############################################################################
