import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# [설정] 폰트 사이즈 일괄 설정
# ---------------------------------------------------------
plt.rcParams.update({'font.size': 12})

# 1. 데이터 준비 (기존 데이터)
raw_data = """11:50 10.5ppm
12:05 7.8ppm
12:27 6.7ppm
12:48 5.8ppm
13:07 5.8ppm
13:28 5.1ppm"""

cycles_raw = """1st : 11:50~12:27
2nd : 12:28~13:07
3rd : 13:08~13:29"""

# [추가] 4. 구간별 추가 정보 (Power, Energy) 리스트 정의
# 순서는 cycle_list 생성 순서(1st, 2nd, 3rd, Continuous)와 같아야 합니다.
cycle_stats = [
    {'pow': '0.0106 W', 'eng': '0.0065 Wh'}, # 1st
    {'pow': '0.0055 W', 'eng': '0.0040 Wh'}, # 2nd
    {'pow': '0.0039 W', 'eng': '0.0016 Wh'}, # 3rd
    {'pow': '0.0009 W', 'eng': '0.0214 Wh'}  # Continuous
]

# 2. 데이터 파싱
data_list = []
base_date_str = "2024-01-01"

for line in raw_data.split('\n'):
    t_str, v_str = line.split()
    value = float(v_str.replace('ppm', ''))
    dt = pd.to_datetime(f"{base_date_str} {t_str}")
    data_list.append({'datetime': dt, 'ppm': value})

new_dt = pd.to_datetime("2024-01-02 13:50")
data_list.append({'datetime': new_dt, 'ppm': 3.5})

df = pd.DataFrame(data_list)
start_time = df['datetime'].iloc[0]
df['actual_elapsed'] = (df['datetime'] - start_time).dt.total_seconds() / 60

# 3. 사이클 파싱
cycle_list = []
for line in cycles_raw.strip().split('\n'):
    parts = line.split(':', 1)
    label = parts[0].strip()
    times = parts[1].strip().split('~')
    s_obj = pd.to_datetime(f"{base_date_str} {times[0].strip()}")
    e_obj = pd.to_datetime(f"{base_date_str} {times[1].strip()}")
    cycle_list.append({'label': label, 'start_dt': s_obj, 'end_dt': e_obj})

# Circulation Operate 추가
last_cycle_end_time = pd.to_datetime(f"{base_date_str} 13:37")
cycle_list.append({
    'label': 'Continuous', # 이름 조금 짧게 수정
    'start_dt': last_cycle_end_time, 
    'end_dt': new_dt
})

for cycle in cycle_list:
    cycle['start'] = (cycle['start_dt'] - start_time).total_seconds() / 60
    cycle['end'] = (cycle['end_dt'] - start_time).total_seconds() / 60

# ---------------------------------------------------------
# 좌표 변환 로직
# ---------------------------------------------------------
split_point_actual = cycle_list[-2]['end']
total_actual_end = cycle_list[-1]['end']

visual_split_ratio = 0.75
total_visual_width = 100.0
visual_split_point = total_visual_width * visual_split_ratio

def transform_x(actual_x):
    if actual_x <= split_point_actual:
        return actual_x * (visual_split_point / split_point_actual)
    else:
        actual_remaining = actual_x - split_point_actual
        actual_duration_op = total_actual_end - split_point_actual
        visual_remaining = total_visual_width - visual_split_point
        return visual_split_point + actual_remaining * (visual_remaining / actual_duration_op)

df['visual_x'] = df['actual_elapsed'].apply(transform_x)
for cycle in cycle_list:
    cycle['visual_start'] = transform_x(cycle['start'])
    cycle['visual_end'] = transform_x(cycle['end'])

# ---------------------------------------------------------
# 그래프 그리기
# ---------------------------------------------------------
plt.figure(figsize=(14, 7)) # 세로 길이 약간 늘림 (정보 표시 공간 확보)

# (1) 배경색 및 텍스트 정보 표시
colors = ['#e6f2ff', '#fff0e6']
max_ppm = df['ppm'].max()

for i, cycle in enumerate(cycle_list):
    # 배경색
    plt.axvspan(cycle['visual_start'], cycle['visual_end'], color=colors[i % 2], alpha=0.6)
    
    mid = (cycle['visual_start'] + cycle['visual_end']) / 2
    
    # [수정] 사이클 이름 (가장 위)
    plt.text(mid, max_ppm + 1.8, f"{cycle['label']} Cycle", 
             ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    # [추가] Power / Energy 정보 박스 (사이클 이름 아래)
    # bbox를 사용하여 흰색 박스를 만들어 가독성을 높임
    stats = cycle_stats[i]
    info_text = f"Avg P: {stats['pow']}\nEnergy: {stats['eng']}"
    
    plt.text(mid, max_ppm + 1.6, info_text, 
             ha='center', va='top', fontsize=10, color='#333333',
             bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))

# (2) 선 그래프
plt.plot(df['visual_x'], df['ppm'], marker='o', color='#1f77b4', linewidth=2, label='F- Concentration')

# (3) 데이터 값 표시
for i, row in df.iterrows():
    plt.text(row['visual_x'], row['ppm'] - 0.6, f"{row['ppm']}", ha='center', fontsize=12)

# (4) X축 눈금
ticks_part1 = np.arange(0, int(split_point_actual) + 1, 30)
ticks_part2 = [int(total_actual_end)] 
all_ticks_actual = np.concatenate([ticks_part1, ticks_part2])
all_ticks_visual = [transform_x(t) for t in all_ticks_actual]
tick_labels = [f"{int(t)}m" for t in all_ticks_actual]

plt.xticks(all_ticks_visual, tick_labels, fontsize=12)
plt.yticks(fontsize=12)

plt.xlabel('Time (minutes)', fontsize=12)
plt.ylabel(r'F$^{-}$ Concentration (ppm)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5, axis='y')

# Y축 범위 조정 (위쪽 여백을 더 줘서 텍스트 박스 공간 확보)
plt.ylim(0, max_ppm + 4.0)

# X축 여백
padding = 2
plt.xlim(0 - padding, total_visual_width + padding)

plt.tight_layout()
plt.show()