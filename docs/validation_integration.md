# データ検証機能の統合完了

## 概要

`rolling_opt.py`に、削除した8つの検証スクリプトの機能を統合しました。
これにより、一時的なスクリプトを作成することなく、メインの最適化スクリプトから直接データ検証が実行できるようになりました。

## 統合した機能

### 1. `validate_results(csv_path, battery_capacity, output_report)`
**旧スクリプト:** `verify_annual_stats.py`, `find_pv_surplus_days.py`, `find_full_charge_days.py`

包括的なデータ検証を実行します:
- PV余剰発生日のTop 10ランキング
- バッテリーフル充電達成日のTop 10
- 年間統計 (総買電量、平均買電、平均SOC、PV利用率など)
- サンプル日付の詳細データ

**実行例:**
```bash
python3 scripts/rolling_opt.py --validate
```

**出力例:**
```
================================================================================
データ検証レポート
================================================================================

【年間統計】
  総買電量:      547,825.0 kWh
  平均買電:           62.54 kW
  平均SOC:           349.60 kWh (40.7%)
  総PV発電:      431,345.0 kWh
  総需要:      1,025,892.0 kWh
  総PV余剰:          141.0 kWh
  PV利用率:           99.97 %

【PV余剰発生日 Top 10】
   1. 2024-06-19  余剰:   62.0 kWh
   2. 2024-05-29  余剰:   28.5 kWh
   ...
```

---

### 2. `verify_specific_dates(csv_path, dates_to_check)`
**旧スクリプト:** `verify_dates.py`, `check_march8.py`, `check_june19.py`, `check_may15.py`, `check_june2_buy.py`

特定の日付のデータを詳細に検証します:
- 日次の需要、PV、買電、余剰の合計値
- 平均SOC、最大SOC、最小SOC
- 特定時刻 (14:00, 16:00) のSOC

**実行例:**
```bash
python3 scripts/rolling_opt.py --verify-dates 2024-06-02 2024-05-15 2024-03-08
```

**出力例:**
```
【2024-06-02 のデータ】
  需要合計:   2,349.0 kWh
  PV合計:     1,223.0 kWh
  買電合計:   1,275.0 kWh
  余剰合計:      0.0 kWh
  平均SOC:     694.0 kWh
  最大SOC:     857.0 kWh
  14:00 SOC:   857.5 kWh
  16:00 SOC:   860.0 kWh
```

---

### 3. `find_representative_day(csv_path, battery_capacity, min_surplus, max_surplus)`
**統合機能:** PV余剰発生 + バッテリーフル充電の代表日を検索

PV余剰が一定範囲内で、かつバッテリーがフル充電される「代表日」を検索します。
論文やレポートで使用する典型例を見つけるのに便利です。

**実行例:**
```bash
python3 scripts/rolling_opt.py --find-representative
```

**出力例:**
```
【代表日候補】
条件: PV余剰 1.0~10.0 kWh, フル充電達成
------------------------------------------------------------
  2024-05-15  余剰:    2.0 kWh, フル充電:  6 ステップ
  2024-06-12  余剰:    5.3 kWh, フル充電:  4 ステップ
  ...
```

---

## 複数の検証を同時実行

複数のオプションを組み合わせて使用できます:

```bash
# 包括検証 + 特定日付検証 + 代表日検索を一度に実行
python3 scripts/rolling_opt.py --validate --verify-dates 2024-06-02 2024-05-15 --find-representative
```

---

## カスタムCSVファイルの指定

デフォルトでは`results/rolling_results.csv`を検証しますが、別のファイルを指定できます:

```bash
python3 scripts/rolling_opt.py --validate --csv results/custom_results.csv
```

---

## 実装の詳細

### 追加した関数 (1320行目付近)

1. **`validate_results()`** (約80行)
   - PandasでCSVを読み込み
   - 日次集計でPV余剰とフル充電を分析
   - 年間統計を計算
   - 整形されたレポートを出力

2. **`verify_specific_dates()`** (約60行)
   - 指定日付のデータをフィルタリング
   - 日次および特定時刻の統計を計算
   - 各日付の詳細レポートを出力

3. **`find_representative_day()`** (約40行)
   - 余剰量とフル充電条件で日付を絞り込み
   - 条件を満たす日付のリストを表示

### コマンドライン引数の追加 (890行目付近)

既存のargparseに4つのオプションを追加:
- `--validate`: 包括検証
- `--verify-dates`: 特定日付検証
- `--find-representative`: 代表日検索
- `--csv`: CSVファイルパス指定

検証モードが指定された場合、最適化を実行せずに検証のみを行って終了します。

---

## 削除したファイル (8個)

以下の一時検証スクリプトは不要になったため削除されました:

1. `check_march8.py` → `verify_specific_dates()`に統合
2. `find_pv_surplus_days.py` → `validate_results()`に統合
3. `check_june19.py` → `verify_specific_dates()`に統合
4. `find_full_charge_days.py` → `validate_results()`に統合
5. `check_may15.py` → `verify_specific_dates()`に統合
6. `verify_dates.py` → `verify_specific_dates()`に統合
7. `check_june2_buy.py` → `verify_specific_dates()`に統合
8. `verify_annual_stats.py` → `validate_results()`に統合

---

## 利点

✅ **ワークフロー統合**: メインスクリプトから直接検証実行
✅ **コード再利用**: 検証ロジックを関数として定義し、他のスクリプトからも利用可能
✅ **リポジトリ整理**: 一時ファイルが不要
✅ **メンテナンス性向上**: 1つのファイルで管理
✅ **柔軟性**: コマンドラインオプションで必要な検証のみ実行可能

---

## 今後の使用方法

### 最適化実行後の検証
```bash
# 1. 最適化を実行
python3 scripts/rolling_opt.py

# 2. 結果を検証
python3 scripts/rolling_opt.py --validate
```

### 論文執筆時のデータ確認
```bash
# 代表日を検索
python3 scripts/rolling_opt.py --find-representative

# 特定の日付を詳細確認
python3 scripts/rolling_opt.py --verify-dates 2024-05-15
```

### 年間統計の確認
```bash
# 包括的な年間統計レポート
python3 scripts/rolling_opt.py --validate
```

---

## 検証機能の呼び出し (Python内部から)

他のPythonスクリプトから関数として呼び出すことも可能:

```python
from scripts.rolling_opt import validate_results, verify_specific_dates, find_representative_day

# 包括検証
results = validate_results('results/rolling_results.csv', output_report=True)

# 特定日付検証
verify_specific_dates('results/rolling_results.csv', 
                     dates_to_check=['2024-06-02', '2024-05-15'])

# 代表日検索
candidates = find_representative_day('results/rolling_results.csv', 
                                    min_surplus=1.0, max_surplus=10.0)
```

---

## まとめ

8つの一時検証スクリプトの機能を`rolling_opt.py`に完全統合しました。
これにより、プロフェッショナルなワークフローで、動的にデータ検証が実行できるようになりました。

**統合ファイル:** `/Users/yzhy/Documents/大学関係/2025前期/EMS/scripts/rolling_opt.py`
**追加行数:** 約180行 (3つの検証関数 + コマンドライン統合)
**削除ファイル:** 8個の一時検証スクリプト
