# PV・蓄電池システム ローリング最適化プロジェクト

北海道十勝地方のPV・蓄電池システムにおける年間電気料金最小化のための最適化研究

## プロジェクト概要

- **対象システム**: PV容量250kW、蓄電池容量860kWh、充放電最大出力400kW
- **最適化手法**: モデル予測制御(MPC)に基づくローリング最適化
- **期間**: 2024年1月1日〜12月31日（17,520ステップ、30分間隔）
- **ソルバー**: PySCIPOpt

## 主要な成果

### 目的関数修正による契約電力削減

- **契約電力**: 538.8 kW → 78.9 kW（**85.4%削減**）
- **基本料金**: ¥15,550,096 → ¥2,276,940（**¥13,273,597削減**）
- **総電気料金**: ¥18,790,622 → ¥5,410,064（**71.2%削減**）

### 年間電気料金比較（2024年実績）

- **市場価格連動プラン**: ¥5,360,338
- **北海道電力基本プラン**: ¥5,410,064
- **差額**: ¥49,726（市場価格連動プランが有利）

### システム運用統計

- **PV自給率**: 32.1%
- **PV利用率**: 90.7%
- **最大買電電力**: 78.9 kW
- **平均買電電力**: 19.7 kW
- **最適解取得率**: 100%（全17,520ステップ）

## ディレクトリ構造

```
EMS/
├── README.md                   # このファイル
├── requirement.txt             # 必要なPythonパッケージ
│
├── data/                       # 入力データ
│   ├── 20250901サンプルデータ.xlsx       # 需要データ
│   ├── 202505-09電力量データ.xlsx        # 電力量データ
│   ├── spot_summary_2024.csv             # JEPX市場価格（2024年）
│   ├── spot_summary_2023.csv             # JEPX市場価格（2023年）
│   └── monthly_statistics.csv            # 月別統計データ
│
├── scripts/                    # Pythonスクリプト
│   ├── rolling_opt.py                    # メイン最適化スクリプト
│   ├── calculate_annual_costs.py         # 年間コスト計算
│   ├── generate_daily_pattern.py         # 日次パターン生成
│   ├── generate_monthly_figures.py       # 月別図表生成
│   ├── check_consistency.py              # データ整合性チェック
│   └── test_pv_curtailment.py            # PV抑制テスト
│
├── results/                    # 最適化結果
│   ├── rolling_results.csv               # 年間最適化結果（全時系列）
│   ├── rolling_results.pdf               # 結果サマリーPDF
│   ├── annual_cost_comparison.json       # 年間コスト比較
│   └── png/                              # 図表ファイル
│       ├── monthly_statistics.png        # 月別統計
│       ├── monthly_contract_power.png    # 月別契約電力
│       ├── daily_battery_pattern.png     # 日次運用パターン
│       ├── annual_pv_buy_demand.png      # 年間PV・買電・需要
│       ├── rolling_results_*.png         # 最適化結果図（5枚）
│       └── *.xbb                         # BoundingBoxファイル
│
├── logs/                       # ログファイル
│   ├── rolling_full_year_new.log         # 最新の年間最適化ログ
│   ├── check_progress.sh                 # 進捗確認スクリプト
│   ├── monitor_optimization.sh           # 監視スクリプト
│   └── wait_and_analyze.sh               # 待機・分析スクリプト
│
├── docs/                       # ドキュメント
│   ├── research_report.pdf               # 最終レポート（LaTeX）
│   ├── research_report.tex               # LaTeXソースファイル
│   ├── research_report.dvi               # DVIファイル
│   ├── research_report.synctex.gz        # SyncTeXファイル
│   └── pv_curtailment_results.md         # PV抑制結果まとめ
│
├── archive/                    # アーカイブ（古いファイル）
│   ├── rolling_full_year.log             # 旧最適化ログ
│   ├── full_test.log                     # テストログ
│   └── test_run.log                      # テスト実行ログ
│
├── __pycache__/                # Pythonキャッシュ
└── .venv/                      # Python仮想環境

```

## 使用方法

### 1. 環境構築

```bash
# 仮想環境の作成と有効化
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 必要なパッケージのインストール
pip install -r requirement.txt
```

### 2. 年間最適化の実行

```bash
cd scripts
python3 rolling_opt.py --time_limit 10
```

オプション:
- `--time_limit`: 各ステップの最適化時間制限（秒）

### 3. 図表の生成

```bash
# 月別統計図の生成
python3 generate_monthly_figures.py

# 日次パターン図の生成
python3 generate_daily_pattern.py
```

### 4. 年間コストの計算

```bash
python3 calculate_annual_costs.py
```

## 主要な技術的成果

### 目的関数の改善

**旧目的関数** (エネルギー料金のみ):
```
minimize Σ(price[k] × sBY[k] × 0.5)
```
→ 契約電力538.8kW、基本料金¥15.5M（総コストの86.8%）

**新目的関数** (基本料金 + エネルギー料金):
```
minimize (w_basic × sBYMAX) + Σ(price[k] × sBY[k] × 0.5)
```
→ 契約電力78.9kW、基本料金¥2.3M（85.4%削減）

### 制約条件

1. 電力収支制約
2. PV変換効率制約
3. SOC更新式・範囲制約（0〜860kWh）
4. 充放電電力制約（0〜400kW）
5. 逆潮流禁止制約
6. **契約電力制約**: sBY[k] ≤ sBYMAX

## 依存パッケージ

- Python 3.x
- pandas
- numpy
- matplotlib
- pyscipopt
- openpyxl

## 参考文献

- Camacho, E.F., Bordons, C. (2007). Model Predictive Control. Springer-Verlag.
- Parisio, A., et al. (2014). A model predictive control approach to microgrid operation optimization. IEEE Trans. Control Syst. Technol.

## ライセンス

研究用途のみ

## 更新履歴

- **2025/10/09**: 目的関数修正完了、年間最適化実行、レポート更新
- **2025/09/XX**: 初期実装、PV出力抑制機能追加

## 連絡先

北海道十勝地方 PV・蓄電池システム最適化プロジェクト
