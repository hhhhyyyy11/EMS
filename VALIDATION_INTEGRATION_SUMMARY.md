# データ検証機能統合 - 概要

## 実施内容

削除した8つの一時検証スクリプトの機能を`rolling_opt.py`に完全統合しました。

## 統合した関数

### 1. `validate_results()` 
**統合元:** `verify_annual_stats.py`, `find_pv_surplus_days.py`, `find_full_charge_days.py`

年間統計、PV余剰Top 10、フル充電日Top 10を包括的に検証

### 2. `verify_specific_dates()`
**統合元:** `verify_dates.py`, `check_march8.py`, `check_june19.py`, `check_may15.py`, `check_june2_buy.py`

特定日付の需要、PV、買電、SOC等を詳細検証

### 3. `find_representative_day()`
**新規機能:** PV余剰+フル充電の代表日を検索

## 使用方法

```bash
# 包括検証
python3 scripts/rolling_opt.py --validate

# 特定日付検証
python3 scripts/rolling_opt.py --verify-dates 2024-06-02 2024-05-15

# 代表日検索
python3 scripts/rolling_opt.py --find-representative

# すべて同時実行
python3 scripts/rolling_opt.py --validate --verify-dates 2024-06-02 --find-representative
```

## 動作確認

```bash
# テストスクリプトで確認
./test_integrated_validation.sh
```

## 削除したファイル

- check_march8.py
- find_pv_surplus_days.py
- check_june19.py
- find_full_charge_days.py
- check_may15.py
- verify_dates.py
- check_june2_buy.py
- verify_annual_stats.py

## 効果

✅ ワークフロー統合 (メインスクリプトから直接実行)
✅ コード再利用 (関数として定義)
✅ リポジトリ整理 (一時ファイル不要)
✅ メンテナンス性向上 (1ファイル管理)

## 詳細ドキュメント

`docs/validation_integration.md` を参照
