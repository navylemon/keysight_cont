import pandas as pd
import glob
import os
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta

# --------------------------------------------------------------------------------
# 1. 설정 및 파일 불러오기
# --------------------------------------------------------------------------------

folder_path = r'C:\Users\chohyunbin\OneDrive\PythonBuild\keysight_cont\expdata(1128)'
file_pattern = os.path.join(folder_path, "psu_data_*.csv")

all_files = sorted(glob.glob(file_pattern))

if not all_files:
    print(f"❌ 파일을 찾을 수 없습니다. 경로를 확인해주세요: {file_pattern}")
    exit()

print(f"✅ 총 {len(all_files)}개의 파일을 발견했습니다. 데이터를 병합합니다...")

df_list = []
for filename in all_files:
    try:
        df_temp = pd.read_csv(filename)
        df_list.append(df_temp)
    except Exception as e:
        print(f"파일 읽기 오류 ({os.path.basename(filename)}): {e}")

df_all = pd.concat(df_list, ignore_index=True)

# --------------------------------------------------------------------------------
# 2. 데이터 전처리
# --------------------------------------------------------------------------------

df_all['Timestamp'] = pd.to_datetime(df_all['Timestamp'])
df_all = df_all.sort_values(by='Timestamp').reset_index(drop=True)

start_time = df_all['Timestamp'].iloc[0]
df_all['Elapsed_Min'] = (df_all['Timestamp'] - start_time).dt.total_seconds() / 60.0
df_all['dt'] = df_all['Timestamp'].diff().dt.total_seconds().fillna(0)
df_all.loc[df_all['dt'] > 300, 'dt'] = 0  
df_all['Energy_J'] = df_all['P_P6V'] * df_all['dt']

# --------------------------------------------------------------------------------
# 3. 4개 그룹(Cycle) 정의 및 통계 계산
# --------------------------------------------------------------------------------

base_date = "2025-11-28"

cycles_info = [
    {"name": "1st Cycle",  "start_t": "11:50:00", "end_t": "12:27:00", "days_offset": 0},
    {"name": "2nd Cycle",  "start_t": "12:28:00", "end_t": "13:07:00", "days_offset": 0},
    {"name": "3rd Cycle",  "start_t": "13:08:00", "end_t": "13:29:00", "days_offset": 0},
    {"name": "Continuous", "start_t": "13:40:00", "end_t": "15:00:00", "days_offset": 1}
]

print("-" * 80)
print(f"{'Group':<12} | {'Avg Power (W)':<15} | {'Energy (Wh)':<15} | {'Duration (min)':<15}")
print("-" * 80)

cycle_data_list = []

for info in cycles_info:
    s_dt = pd.to_datetime(f"{base_date} {info['start_t']}")
    e_dt = pd.to_datetime(f"{base_date} {info['end_t']}") + timedelta(days=info['days_offset'])

    mask = (df_all['Timestamp'] >= s_dt) & (df_all['Timestamp'] <= e_dt)
    cycle_df = df_all.loc[mask].copy()

    if cycle_df.empty:
        print(f"{info['name']:<12} | 데이터 없음")
        cycle_data_list.append(None)
        continue

    avg_power = cycle_df['P_P6V'].mean()
    total_energy_Wh = cycle_df['Energy_J'].sum() / 3600
    duration_min = cycle_df['dt'].sum() / 60
    
    print(f"{info['name']:<12} | {avg_power:.6f} W     | {total_energy_Wh:.6f} Wh     | {duration_min:.2f} min")

    cycle_data_list.append({
        "name": info['name'],
        "power": avg_power,
        "energy": total_energy_Wh
    })

print("-" * 80)

# --------------------------------------------------------------------------------
# 4. 그래프 그리기 (범례 위치 수정됨)
# --------------------------------------------------------------------------------

labels = []
power_vals = []
energy_vals = []

for data in cycle_data_list:
    if data is not None:
        labels.append(data['name'])
        power_vals.append(data['power'])
        energy_vals.append(data['energy'])

x = np.arange(len(labels))
width = 0.45 

fig, ax1 = plt.subplots(figsize=(10, 6))
plt.style.use('default') 

# --- 첫 번째 축 (왼쪽): Power (W) ---
rects1 = ax1.bar(x - width/2, power_vals, width, label='Avg Power (W)', color='skyblue', edgecolor='black', alpha=0.9)
ax1.set_ylabel('Average Power (W)', fontsize=12, color='tab:blue')
#ax1.set_title('Power Consumption & Total Energy by Cycle', fontsize=14, pad=15)
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=11)
ax1.tick_params(axis='y', labelcolor='tab:blue')
# 범례와 텍스트가 들어갈 공간 확보를 위해 상단 여백을 1.25배 -> 1.3배로 조금 더 늘림
ax1.set_ylim(0, max(power_vals) * 1.3)

# --- 두 번째 축 (오른쪽): Energy (Wh) ---
ax2 = ax1.twinx()
rects2 = ax2.bar(x + width/2, energy_vals, width, label='Energy (Wh)', color='lightcoral', edgecolor='black', alpha=0.9)
ax2.set_ylabel('Total Energy (Wh)', fontsize=12, color='tab:red')
ax2.tick_params(axis='y', labelcolor='tab:red')
ax2.set_ylim(0, max(energy_vals) * 1.3)

# --- 막대 위에 값 표시 함수 ---
def autolabel(rects, ax, unit):
    for rect in rects:
        height = rect.get_height()
        label_text = f'{height:.5f} {unit}'
        
        ax.annotate(label_text,
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3), 
                    textcoords="offset points",
                    ha='center', va='bottom', 
                    fontsize=12, fontweight='bold')

autolabel(rects1, ax1, "W")
autolabel(rects2, ax2, "Wh")

# --- 범례 표시 (수정됨: 그래프 안쪽 상단) ---
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()

# bbox_to_anchor 제거하고 loc='upper center' 사용
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center', ncol=2)

ax1.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()