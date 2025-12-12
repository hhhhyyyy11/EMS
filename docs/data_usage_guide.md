# データの保存と使用に関するガイド

## 概要

`rolling_opt.py`実行時のデータの流れと、各ファイルの役割について説明します。

## 📁 データフロー

```
rolling_opt.py 実行
    ↓
    ├─→ results/rolling_results.csv (時系列データ)
    ├─→ results/annual_cost_comparison.json (年間料金データ)
    ├─→ png/*.png (グラフ画像)
    ├─→ rolling_results.pdf (レポート)
    └─→ logs/rolling_opt_run.log (実行ログ)
```

## 📄 各ファイルの役割

### 1. results/rolling_results.csv

**内容**: 30分ごとの最適化結果

**カラム**:
- `timestamp`: 日時
- `consumption_kW`: 消費電力 [kW]
- `pv_kW`: PV発電量 [kW]
- `sBY`: 買電電力 [kW]
- `sSL`: 売電電力 [kW]
- `bF`: バッテリー残量 [kWh]
- `xFC1`: 充電電力 [kW]
- `xFD1`: 放電電力 [kW]
- `price_yen_per_kWh`: 電力単価 [円/kWh]
- `status`: 最適化ステータス

**使用例**:
```python
import pandas as pd
df = pd.read_csv('results/rolling_results.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 月別集計
df['month'] = df['timestamp'].dt.month
monthly_buy = df.groupby('month')['sBY'].sum() * 0.5  # kWh
```

### 2. results/annual_cost_comparison.json

**内容**: 年間電気料金の比較データ

**構造**:
```json
{
  "hokkaido_basic": {
    "basic_charge": 基本料金,
    "energy_charge": 電力量料金,
    "fuel_adjustment": 燃料費調整額,
    "renewable_levy": 再エネ賦課金,
    "total": 合計
  },
  "market_linked": {
    "basic_charge": 基本料金,
    "energy_charge": 市場価格料金,
    "renewable_levy": 再エネ賦課金,
    "total": 合計
  },
  "peak_demand_kW": 契約電力,
  "monthly_energy_kWh": {月別電力使用量},
  "monthly_peak_kW": {月別最大需要}
}
```

**使用例**:
```python
import json
with open('results/annual_cost_comparison.json', 'r') as f:
    data = json.load(f)

hokkaido_total = data['hokkaido_basic']['total']
market_total = data['market_linked']['total']
savings = hokkaido_total - market_total
```

### 3. logs/rolling_opt_run.log

**内容**: プログラム実行ログ

**含まれる情報**:
- 実行パラメータ
- 進捗状況
- 年間料金比較結果
- エラーメッセージ

**注意**: ログは参考情報です。**データ分析には必ずJSONまたはCSVファイルを使用**してください。

## 🎯 データの使用方法

### グラフ生成時

```python
# 時系列グラフ
df = pd.read_csv('results/rolling_results.csv')
plt.plot(df['timestamp'], df['sBY'])

# 年間料金比較グラフ
with open('results/annual_cost_comparison.json', 'r') as f:
    cost_data = json.load(f)
# cost_dataを使ってグラフ作成
```

### TeX文書作成時

```python
import json

with open('results/annual_cost_comparison.json', 'r') as f:
    data = json.load(f)

# LaTeX変数として出力
print(f"\\newcommand{{\\HokkaidoTotal}}{{{data['hokkaido_basic']['total']:,.0f}}}")
print(f"\\newcommand{{\\MarketTotal}}{{{data['market_linked']['total']:,.0f}}}")
```

### データ分析時

```python
import pandas as pd
import json

# CSVから時系列データを読み込み
df = pd.read_csv('results/rolling_results.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# JSONから年間料金データを読み込み
with open('results/annual_cost_comparison.json', 'r') as f:
    annual_data = json.load(f)

# 分析実施
peak_demand = annual_data['peak_demand_kW']
annual_energy = df['sBY'].sum() * 0.5  # kWh
```

## ✅ データ整合性の確認

### プログラム実行後の確認手順

1. **ファイルが正しく生成されているか確認**
   ```bash
   ls -lht results/
   ```
   - `rolling_results.csv`
   - `annual_cost_comparison.json`
   が同じ日時に更新されていることを確認

2. **データ整合性を検証**
   ```bash
   python scripts/verify_data_consistency.py
   ```

3. **期待される出力**
   - すべてのファイルが存在
   - JSONとCSVの契約電力が一致
   - ログとJSONの年間料金が一致（差異 < 1円）

### トラブルシューティング

#### Q: JSONとCSVの契約電力が一致しない

**原因**: 異なる実行結果のファイルが混在している

**対処法**:
```bash
# rolling_opt.pyを再実行
python scripts/rolling_opt.py --excel 20250901サンプルデータ.xlsx

# 検証
python scripts/verify_data_consistency.py
```

#### Q: グラフ生成でJSONファイルが見つからない

**原因**: ファイルパスが間違っている

**対処法**:
- `results/annual_cost_comparison.json`を使用
- カレントディレクトリを確認

#### Q: ログとJSONの数値が大きく異なる

**原因**: ログが古い実行結果

**対処法**:
- **JSONファイルを信頼する**
- 必要であればrolling_opt.pyを再実行

## 🔒 ベストプラクティス

### DO ✓

1. **rolling_opt.py実行後は必ずverify_data_consistency.pyで確認**
2. **データ分析にはJSONとCSVファイルを使用**
3. **ファイルの更新日時を確認**
4. **resultsディレクトリにデータを一元管理**

### DON'T ✗

1. **ログファイルから手動でデータをコピー**
2. **異なる実行結果のファイルを混在させる**
3. **ルートディレクトリに結果ファイルを散在させる**
4. **検証せずにデータを使用**

## 📊 データの信頼性

### 優先順位

1. **最優先**: `results/annual_cost_comparison.json` と `results/rolling_results.csv`（同じ実行結果）
2. **参考**: `logs/rolling_opt_run.log`（ログは参考情報として使用）

### 確認方法

```bash
# 同じ実行結果かチェック
python scripts/verify_data_consistency.py
```

すべての差異が1円未満または0.1kW未満であればOKです。

## まとめ

- **データは`results/`ディレクトリに保存される**
- **JSONとCSVが同じ実行結果であることを確認する**
- **データ分析にはログではなくJSONとCSVを使用する**
- **検証スクリプトで整合性を定期的に確認する**
