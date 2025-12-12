# ローリング最適化 実行ガイド

## 🚀 1コマンドで完全実行

```bash
cd /Users/yzhy/Documents/大学関係/2025前期/EMS
python scripts/rolling_opt.py
```

**引数は不要です!** すべてのファイルパスはデフォルト設定されています。

このコマンド1つで、以下が**すべて自動実行**されます:

✅ ローリング最適化（17,520ステップ、1年間）  
✅ 年間料金比較の計算  
✅ すべてのグラフ生成（PNG形式、7枚）  
✅ PDFレポート生成  
✅ データ保存（CSV、JSON）  

実行時間: 約10-15分

---

## 📁 保存されるデータ

### 主要データ

| ファイル | 内容 | サイズ |
|---------|------|--------|
| `results/rolling_results.csv` | 30分間隔の最適化結果 | 2.4MB |
| `results/annual_cost_comparison.json` | 年間料金比較データ | 1.2KB |
| `data/monthly_statistics.csv` | 月別統計データ | 数KB |

### グラフ（すべて`png/`ディレクトリ）

1. `rolling_results_timeseries.png` - 時系列グラフ
2. `rolling_results_buysell.png` - 買電・売電グラフ
3. `rolling_results_battery.png` - 蓄電池運用グラフ
4. `rolling_results_pvstack.png` - PV発電グラフ
5. `rolling_results_summary.png` - サマリーグラフ
6. `monthly_statistics.png` - 月別統計グラフ
7. `monthly_contract_power.png` - 月別契約電力グラフ

### レポート

- `scripts/rolling_results.pdf` - 基本グラフPDF
- `docs/rolling_optimization_results.pdf` - 完全技術レポート（LaTeX生成）

---

## 💰 実行結果の例

```
=== 年間電気料金比較 ===
北海道電力基本プラン: 10,818,388円
市場価格連動プラン: 10,699,682円
差額: 118,705円 (市場価格連動プランが安い)
契約電力: 157.8kW

✓ すべての処理が完了しました!
```

---

## 📊 データの確認方法

### Pythonで確認

```python
import pandas as pd
import json

# 最適化結果
df = pd.read_csv('results/rolling_results.csv')
print(df.head())

# 年間料金比較
with open('results/annual_cost_comparison.json', 'r') as f:
    cost = json.load(f)
print(f"削減額: {cost['difference']:,}円")
```

### Excelで確認

- `results/rolling_results.csv`を直接Excelで開く
- `data/monthly_statistics.csv`を直接Excelで開く

---

## ⚙️ オプション

### 北海道電力基本プランのみで計算

```bash
python scripts/rolling_opt.py --use_fixed_price
```

### 計算時間を短縮（各ステップ5秒制限）

```bash
python scripts/rolling_opt.py --time_limit 5.0
```

### 一部期間のみ実行（デバッグ用）

```bash
python scripts/rolling_opt.py --max_steps 100
```

### 使用するデータファイルを変更（通常は不要）

```bash
python scripts/rolling_opt.py --excel data/別のファイル.xlsx --price_data data/別の価格データ.csv
```

---

## 🔧 トラブルシューティング

### エラーが発生した場合

1. ログを確認: `logs/rolling_opt_run_latest.log`
2. 必要なパッケージをインストール:

   ```bash
   pip install -r requirement.txt
   ```

3. データファイルの存在確認:
   - `data/20250901サンプルデータ.xlsx`
   - `data/spot_summary_2024.csv`
   - `data/spot_summary_2023.csv`

### グラフが生成されない

```bash
pip install matplotlib
```

### 日本語が文字化けする

```bash
# matplotlibの日本語フォント設定を確認
python -c "import matplotlib.pyplot as plt; print(plt.rcParams['font.family'])"
```

---

## 📝 詳細ドキュメント

- データ保存場所の詳細: `README_DATA_LOCATIONS.md`
- システム概要: `README.md`
- 検証レポート: `docs/verification_report.md`

---

## 🎯 次のステップ

1. **グラフを確認**: `png/`ディレクトリ内のPNGファイルを開く
2. **データを分析**: `results/rolling_results.csv`をPython/Excelで分析
3. **レポートを確認**: `docs/rolling_optimization_results.pdf`を開く
