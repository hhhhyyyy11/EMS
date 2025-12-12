# データ保存場所ガイド

このドキュメントは、`python scripts/rolling_opt.py`を実行した際に、どこに何のデータが保存されるかを説明します。

## 🚀 実行方法

```bash
cd /Users/yzhy/Documents/大学関係/2025前期/EMS
python scripts/rolling_opt.py
```

**引数は不要です!** すべてのデータファイルパスはデフォルト設定されています:
- Excelファイル: `data/20250901サンプルデータ.xlsx`
- JEPX価格データ(2024年4-12月): `data/spot_summary_2024.csv`
- JEPX価格データ(2024年1-3月): `data/spot_summary_2023.csv`

このコマンド1つで、以下のすべてが自動実行されます:
1. ローリング最適化の実行（17,520ステップ、1年間）
2. 年間料金比較の計算
3. すべてのデータとグラフの保存

---

## 📁 データ保存場所一覧

### 1. 最適化結果データ

#### `results/rolling_results.csv`
- **内容**: 30分間隔の最適化結果（17,521行）
- **サイズ**: 約2.4MB
- **列**: 
  - `timestamp`: タイムスタンプ
  - `consumption_kW`: 消費電力
  - `pv_kW`: PV発電電力
  - `pv_used_kW`: PV使用電力
  - `sBY`: 買電電力
  - `sSL`: 売電電力（常に0、逆潮流不可）
  - `bF`: 蓄電池SOC（状態）
  - `xFC1`: 蓄電池充電電力
  - `xFD1`: 蓄電池放電電力
  - その他の最適化変数

#### `results/annual_cost_comparison.json`
- **内容**: 年間電気料金比較データ
- **サイズ**: 約1.2KB
- **含まれるデータ**:
  ```json
  {
    "hokkaido_basic": {
      "basic_charge": 4553874,      // 基本料金
      "energy_charge": 7436705,     // 電力量料金
      "fuel_adjustment": -2548207,  // 燃料費調整額
      "renewable_levy": 1376015,    // 再エネ賦課金
      "total": 10818388            // 合計
    },
    "market_linked": {
      "basic_charge": 4553874,      // 基本料金
      "energy_charge": 4769793,     // 市場価格料金
      "renewable_levy": 1376015,    // 再エネ賦課金
      "total": 10699682            // 合計
    },
    "difference": 118705,           // 差額（円）
    "percent_diff": 1.10,           // 削減率（%）
    "peak_demand_kW": 157.8,       // 契約電力（kW）
    "annual_buy_kWh": 345732.0,    // 年間買電量（kWh）
    "system_stats": {
      "total_consumption_kWh": ...,
      "total_pv_generation_kWh": ...,
      "self_sufficiency_rate": ...
    }
  }
  ```

---

### 2. グラフファイル（PNG形式）

すべてのグラフは`png/`ディレクトリに保存されます。

#### 基本グラフ（rolling_opt.pyで自動生成）

1. **`png/rolling_results_timeseries.png`**
   - 時系列グラフ
   - 内容: 需要・PV発電・蓄電池SOCの推移
   - サイズ: 約247KB

2. **`png/rolling_results_buysell.png`**
   - 買電・売電グラフ
   - 内容: 買電電力(sBY)と売電電力(sSL)の推移
   - サイズ: 約139KB

3. **`png/rolling_results_battery.png`**
   - 蓄電池運用グラフ
   - 内容: 充電・放電・SOCの推移
   - サイズ: 約229KB

4. **`png/rolling_results_pvstack.png`**
   - PV発電スタックグラフ
   - 内容: PV発電・使用・抑制の内訳
   - サイズ: 約281KB

5. **`png/rolling_results_summary.png`**
   - サマリーグラフ
   - 内容: 年間統計の数値サマリー
   - サイズ: 約70KB

#### 月別統計グラフ（自動生成）

6. **`png/monthly_statistics.png`**
   - 月別エネルギー統計（4つのサブグラフ）
   - 内容:
     - 月別消費電力量と買電量
     - 月別PV発電・抑制状況
     - 月別PV自給率・利用率
     - 年間蓄電池SOC推移
   - サイズ: 約591KB

7. **`png/monthly_contract_power.png`**
   - 月別契約電力（最大買電電力）
   - 内容: 各月の最大買電電力と年間最大値
   - サイズ: 約148KB

#### その他のグラフ（過去に生成されたもの）

8. `png/annual_pv_buy_demand.png` - 年間PV・買電・需要グラフ
9. `png/daily_battery_pattern.png` - 日別蓄電池パターン

---

### 3. PDFレポート

#### `scripts/rolling_results.pdf`
- **内容**: 基本グラフをまとめたPDFレポート
- **サイズ**: 約2.5MB
- **含まれるグラフ**: 時系列、買電・売電、蓄電池、PVスタック、サマリー

#### `docs/rolling_optimization_results.pdf`
- **内容**: 完全な技術レポート（LaTeX生成）
- **サイズ**: 約96KB
- **構成**: 
  - システム概要
  - 料金プラン比較
  - 月別統計
  - ローリング最適化結果
  - 結果の分析と考察
  - 結論
- **すべてのグラフと数値を含む**

---

### 4. 月別統計CSV

#### `data/monthly_statistics.csv`
- **内容**: 月別の集計データ
- **列**:
  - `消費電力量` (kWh)
  - `PV発電量` (kWh)
  - `PV使用量` (kWh)
  - `PV抑制量` (kWh)
  - `買電量` (kWh)
  - `平均SOC` (kWh)
  - `最大買電電力` (kW)

---

### 5. ログファイル

#### `logs/rolling_opt_run_latest.log`
- **内容**: 最新の実行ログ
- **サイズ**: 約74MB
- **含まれる情報**:
  - 各ステップの最適化結果
  - ソルバー（SCIP）の出力
  - エラーメッセージ（あれば）

---

## 📊 データの使い方

### CSVファイルの読み込み（Python）

```python
import pandas as pd

# 最適化結果を読み込む
df = pd.read_csv('results/rolling_results.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 月別統計を読み込む
monthly = pd.read_csv('data/monthly_statistics.csv', index_col=0)
```

### JSONファイルの読み込み（Python）

```python
import json

# 年間料金比較データを読み込む
with open('results/annual_cost_comparison.json', 'r', encoding='utf-8') as f:
    cost_data = json.load(f)

print(f"市場価格連動プラン: {cost_data['market_linked']['total']:,}円")
print(f"削減額: {cost_data['difference']:,}円")
```

### Excelで開く

- `results/rolling_results.csv` → Excelで直接開ける
- `data/monthly_statistics.csv` → Excelで直接開ける
- UTF-8 BOM付きで保存されているため、文字化けしません

---

## 🔄 再実行時の動作

`python scripts/rolling_opt.py`を再実行すると、以下のファイルが**上書き**されます:

- `results/rolling_results.csv`
- `results/annual_cost_comparison.json`
- `png/rolling_results_*.png` (5ファイル)
- `png/monthly_statistics.png`
- `png/monthly_contract_power.png`
- `data/monthly_statistics.csv`
- `scripts/rolling_results.pdf`

**重要**: 既存のデータを保存したい場合は、事前にバックアップしてください!

---

## 📝 実行時の出力メッセージ

実行が成功すると、以下のようなメッセージが表示されます:

```
=== 年間電気料金比較 ===
北海道電力基本プラン: 10,818,388円
  - 基本料金: 4,553,874円
  - 電力量料金: 7,436,705円
  - 燃料費調整額: -2,548,207円
  - 再エネ賦課金: 1,376,015円
市場価格連動プラン: 10,699,682円
  - 基本料金: 4,553,874円
  - 市場価格料金: 4,769,793円
  - 再エネ賦課金: 1,376,015円
差額: 118,705円 (市場価格連動プランが安い)
契約電力: 157.8kW

Saved annual cost comparison to results/annual_cost_comparison.json

=== 月別統計グラフの生成 ===
✓ 月別統計グラフの生成が完了しました

=== データ保存場所 ===
✓ 最適化結果CSV: results/rolling_results.csv
✓ 年間料金比較JSON: results/annual_cost_comparison.json
✓ 基本グラフPDF: scripts/rolling_results.pdf
✓ すべてのグラフPNG: png/*.png
  - 時系列グラフ: png/rolling_results_timeseries.png
  - 買電・売電グラフ: png/rolling_results_buysell.png
  - 蓄電池運用グラフ: png/rolling_results_battery.png
  - PV発電グラフ: png/rolling_results_pvstack.png
  - サマリーグラフ: png/rolling_results_summary.png
  - 月別統計グラフ: png/monthly_statistics.png
  - 月別契約電力グラフ: png/monthly_contract_power.png

✓ すべての処理が完了しました!
```

---

## ⚙️ 設定ファイル

設定は`scripts/rolling_opt.py`の`main()`関数内の`params`辞書で定義されています:

```python
params = {
    'pv_capacity': 250,      # PV容量: 250kW
    'bF_max': 860,           # Battery容量: 860kWh
    'aFC': 400,              # 充電最大出力: 400kW
    'aFD': 400,              # 放電最大出力: 400kW
    'bF0': 430,              # SOC初期値: 430kWh (50%)
    'alpha_DA': 0.98,        # 需要側効率
    'alpha_FC': 0.98,        # 充電効率
    'alpha_FD': 0.98,        # 放電効率
    'alpha_P': 0.98,         # PV利用効率
    'buy_price': 24.44,      # 固定買電価格 (円/kWh)
    'sell_price': 0.0,       # 売電価格: 0円/kWh (逆潮流不可)
    'sBYMAX': 1e6,           # 買電上限: 実質無制限
    'sSLMAX': 0.0,           # 売電上限: 0kW (逆潮流不可)
}
```

---

## 🎯 よくある質問

### Q: グラフが生成されない
A: `matplotlib`がインストールされているか確認してください。
```bash
pip install matplotlib
```

### Q: JSONファイルが文字化けする
A: UTF-8で保存されています。テキストエディタやPythonで正しく読み込めます。

### Q: 実行時間はどれくらい?
A: 約10-15分（17,520ステップ、各ステップ10秒制限）

### Q: 途中で停止した場合は?
A: 再実行すると最初からやり直しになります。部分的な結果は保存されません。

### Q: データを変更したい
A: `data/20250901サンプルデータ.xlsx`のExcelファイルを編集してください。

---

## 📞 サポート

問題が発生した場合は、以下を確認してください:
1. `logs/rolling_opt_run_latest.log` - エラーメッセージを確認
2. 必要なパッケージがインストールされているか: `pip install -r requirement.txt`
3. データファイルが正しいパスにあるか: `data/20250901サンプルデータ.xlsx`, `data/spot_summary_2024.csv`
