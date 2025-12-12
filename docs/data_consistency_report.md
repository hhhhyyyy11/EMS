# データ整合性に関する問題レポート

## 🚨 発見された問題

### 1. ファイル間のデータ不整合

現在、以下の3つのファイルが**異なる実行結果**を保持しています:

| ファイル | 更新日時 | 最大需要電力 | 年間料金(北海道電力) | 年間料金(市場価格) |
|---------|----------|-------------|---------------------|-------------------|
| `logs/rolling_opt_run.log` | 10/22 13:17 | 230.8kW | 14,221,160円 | 16,758,578円 |
| `results/rolling_results.csv` | 10/22 13:42 | 230.83kW | - | - |
| `results/annual_cost_comparison.json` | 10/29 20:49 | 157.8kW | 10,818,173円 | 10,742,566円 |

**差異**: 
- 最大需要電力: 約73kWの差
- 年間料金: 約340万円〜600万円の差

### 2. 根本原因

**`rolling_opt.py`が年間料金データをJSONファイルに保存していませんでした**

- プログラムはログには年間料金を出力していましたが、JSONファイルには保存していませんでした
- `calculate_annual_costs.py`を別途実行してJSONを作成していましたが、CSVファイルが異なる実行結果でした
- グラフ生成やTeX文書が参照するJSONデータと、実際の最適化結果が一致していない可能性がありました

## ✅ 実施した修正

### 1. `rolling_opt.py`の修正

```python
# 年間料金比較データをJSONファイルに保存
import json
os.makedirs('results', exist_ok=True)
json_path = 'results/annual_cost_comparison.json'
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(annual_cost_analysis, f, ensure_ascii=False, indent=2)
print(f'\nSaved annual cost comparison to {json_path}')
```

- プログラム実行時に自動的に`results/annual_cost_comparison.json`を保存
- `results/rolling_results.csv`も同じディレクトリに保存

### 2. `calculate_annual_costs.py`の修正

- データ読み込みパスを`results/rolling_results.csv`に変更
- JSON保存先を`results/annual_cost_comparison.json`に変更

### 3. `generate_monthly_figures.py`の修正

- データ読み込みパスを`results/`ディレクトリに統一

### 4. 検証スクリプトの作成

`scripts/verify_data_consistency.py`を作成:
- ファイルの存在確認
- JSONデータの構造検証
- CSVデータの統計情報表示
- ログとJSONの整合性チェック

## 📋 推奨される対処法

### 今すぐ実施すべきこと

1. **`rolling_opt.py`を再実行**して、整合性のあるデータを生成:
   ```bash
   python scripts/rolling_opt.py --excel 20250901サンプルデータ.xlsx
   ```

2. **検証スクリプトで確認**:
   ```bash
   python scripts/verify_data_consistency.py
   ```

3. **グラフを再生成**:
   ```bash
   python scripts/generate_monthly_figures.py
   ```

### データの使用方法

#### ✓ 正しい方法

- **年間料金データ**: `results/annual_cost_comparison.json` を参照
- **時系列データ**: `results/rolling_results.csv` を参照
- **グラフ生成**: 上記2つのファイルを使用
- **TeX文書**: JSONファイルからデータを読み込む

#### ✗ 避けるべき方法

- ログファイルから手動でデータをコピー
- 異なる実行結果のファイルを混在させる
- CSVとJSONが同じ実行結果であることを確認せずに使用

## 🔍 今後の確認ポイント

### プログラム実行後の確認

```bash
# ファイルの更新日時を確認
ls -lht results/

# データ整合性を検証
python scripts/verify_data_consistency.py
```

### 期待される出力

- すべてのファイルが同じ日時に更新されている
- JSONとCSVの最大需要電力が一致している
- ログとJSONの年間料金が一致している（差異 < 1円）

## 📊 現在のデータの状態

### results/annual_cost_comparison.json (10/29 20:49)

```
北海道電力基本プラン: 10,818,173円
  - 基本料金: 4,553,874円
  - 電力量料金: 7,436,437円
  - 燃料費調整額: -2,548,104円
  - 再エネ賦課金: 1,375,966円

市場価格連動プラン: 10,742,566円
  - 基本料金: 4,553,874円
  - 市場価格料金: 4,812,727円
  - 再エネ賦課金: 1,375,966円

契約電力: 157.8kW
差額: 75,607円 (北海道電力が高い)
```

### logs/rolling_opt_run.log (10/22 13:17)

```
北海道電力基本プラン: 14,221,160円
市場価格連動プラン: 16,758,578円
契約電力: 230.8kW
差額: -2,537,418円 (市場価格連動プランが高い)
```

**⚠️ これらは異なる実行結果です！**

## まとめ

1. **修正完了**: `rolling_opt.py`は今後、年間料金データをJSONに自動保存します
2. **検証ツール**: `verify_data_consistency.py`でデータの整合性を確認できます
3. **再実行推奨**: 最新の整合性のあるデータを得るため、`rolling_opt.py`の再実行を推奨します
