import pandas as pd

df = pd.read_excel('data/20250901サンプルデータ.xlsx', sheet_name='30分値')
print(f'データ行数（元データ）: {len(df)}')
print(f'\n列名: {df.columns.tolist()}')
print(f'\n最初の10行:')
print(df.head(10))
print(f'\n最後の10行:')
print(df.tail(10))

# 1行目はヘッダーの説明行なので除外
df = df[1:].reset_index(drop=True)
dates = pd.to_datetime(df['日付'])
print(f'\n日付範囲:')
print(f'開始日: {dates.min().strftime("%Y年%m月%d日")}')
print(f'終了日: {dates.max().strftime("%Y年%m月%d日")}')
print(f'日数: {(dates.max() - dates.min()).days + 1}')
print(f'ユニークな日付数: {dates.nunique()}')
print(f'\n総ステップ数: {len(df)}')
print(f'理論値（366日×48）: {366 * 48}')
print(f'差分: {366 * 48 - len(df)} ステップ不足')

# 月別の統計
print(f'\n月別のデータ数:')
monthly = dates.dt.to_period('M').value_counts().sort_index()
for month, count in monthly.items():
    print(f'{month}: {count}ステップ = {count/48:.1f}日分')
