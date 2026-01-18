#!/usr/bin/env python3
"""契約電力と蓄電池容量の関係を示すグラフを生成"""

import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# 日本語フォント設定
matplotlib.rcParams['font.family'] = 'Hiragino Sans'
matplotlib.rcParams['axes.unicode_minus'] = False

# データ（表から抽出）
capacity = [0, 215, 430, 540, 645, 860, 1290, 1720]

# 北海道電力基本プラン
hokkaido_contract = [267.35, 202.38, 189.84, 184.10, 178.70, 170.93, 161.16, 161.16]
hokkaido_cost = [18516214, 15984316, 15354276, 15148351, 14980427, 14757247, 14478318, 14476495]

# 市場価格連動プラン
market_contract = [267.35, 202.54, 205.73, 214.75, 216.37, 221.56, 226.95, 232.94]
market_cost = [17829792, 15177856, 15007684, 15226725, 15256184, 15396972, 15549018, 15715245]

# グラフ作成（2段構成）
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# 上段: 契約電力 vs 蓄電池容量
ax1.plot(capacity, hokkaido_contract, 'o-', color='#1f77b4', linewidth=2, markersize=8, label='北海道電力基本プラン')
ax1.plot(capacity, market_contract, 's-', color='#ff7f0e', linewidth=2, markersize=8, label='市場価格連動プラン')
ax1.set_xlabel('蓄電池容量 [kWh]', fontsize=12)
ax1.set_ylabel('契約電力 [kW]', fontsize=12)
ax1.set_title('蓄電池容量と契約電力の関係', fontsize=14)
ax1.legend(loc='upper right', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(-50, 1800)
ax1.set_ylim(150, 280)



# 下段: 年間コスト vs 蓄電池容量
hokkaido_cost_man = [c / 10000 for c in hokkaido_cost]  # 万円単位
market_cost_man = [c / 10000 for c in market_cost]

ax2.plot(capacity, hokkaido_cost_man, 'o-', color='#1f77b4', linewidth=2, markersize=8, label='北海道電力基本プラン')
ax2.plot(capacity, market_cost_man, 's-', color='#ff7f0e', linewidth=2, markersize=8, label='市場価格連動プラン')
ax2.set_xlabel('蓄電池容量 [kWh]', fontsize=12)
ax2.set_ylabel('年間コスト [万円]', fontsize=12)
ax2.set_title('蓄電池容量と年間コストの関係', fontsize=14)
ax2.legend(loc='upper right', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.set_xlim(-50, 1800)

# 交差点をマーク
# 430kWh付近で逆転
ax2.axvline(x=430, color='gray', linestyle='--', alpha=0.5)
ax2.annotate('優位性の\n逆転点', xy=(430, 1550), xytext=(550, 1650),
             fontsize=9, ha='left',
             arrowprops=dict(arrowstyle='->', color='gray'))

plt.tight_layout()
plt.savefig('/Users/yzhy/Documents/大学関係/2025前期/EMS/png/soc860/capacity_contract_power.png', dpi=150, bbox_inches='tight')
plt.close()

print("✓ グラフを保存しました: png/soc860/capacity_contract_power.png")
