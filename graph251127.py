import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 1. 데이터 준비
raw_data = """10:27 10.2ppm
10:53 8.6ppm
11:10 8.2ppm
11:27 7.9ppm
11:59 7.5ppm
12:32 7.5ppm
12:58 6.8ppm
13:11 6.9ppm
13:37 6.6ppm"""

cycles_raw = """1st : 10:27~10:53
2nd : 10:54 ~ 11:27
3rd : 11:28~11:59
4th : 12:01~12:32
5th : 12:33~13:05
6th : 13:07~13:37"""

# 2. 데이터 파싱
data_list = []
base_date_str = "2024-01-01"

for line in raw_data.split('\n'):
    t_str, v_str = line.split()
    value = float(v_str.replace('ppm', ''))
    dt = pd.to_datetime(f"{base_date_str} {t_str}")
    data_list.append({'datetime': dt, 'ppm': value})

# 다음날 데이터
new_dt = pd.to_datetime("2024-01-02 09:57")
data_list.append({'datetime': new_dt, 'ppm': 2.2})

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
    'label': 'circulation\noperation', 
    'start_dt': last_cycle_end_time, 
    'end_dt': new_dt
})

for cycle in cycle_list:
    cycle['start'] = (cycle['start_dt'] - start_time).total_seconds() / 60
    cycle['end'] = (cycle['end_dt'] - start_time).total_seconds() / 60

# ---------------------------------------------------------
# 좌표 변환 로직 (75% vs 25%)
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
plt.figure(figsize=(14, 6))

# (1) 배경색
colors = ['#e6f2ff', '#fff0e6']
for i, cycle in enumerate(cycle_list):
    plt.axvspan(cycle['visual_start'], cycle['visual_end'], color=colors[i % 2], alpha=0.6)
    mid = (cycle['visual_start'] + cycle['visual_end']) / 2
    plt.text(mid, df['ppm'].max() + 0.5, cycle['label'], ha='center', va='bottom', fontweight='bold')

# (2) 선 그래프
plt.plot(df['visual_x'], df['ppm'], marker='o', color='#1f77b4', linewidth=2)

# (3) 데이터 값 표시
for i, row in df.iterrows():
    plt.text(row['visual_x'], row['ppm'] - 0.5, f"{row['ppm']}", ha='center', fontsize=9)

# (4) X축 눈금 (실제 누적 시간)
ticks_part1 = np.arange(0, int(split_point_actual) + 1, 30)
ticks_part2 = [int(total_actual_end)] 
all_ticks_actual = np.concatenate([ticks_part1, ticks_part2])
all_ticks_visual = [transform_x(t) for t in all_ticks_actual]
tick_labels = [f"{int(t)}m" for t in all_ticks_actual]

plt.xticks(all_ticks_visual, tick_labels)

#plt.title('PPM Trend (X-axis: Accumulated Minutes, Non-linear Scale)')
plt.xlabel('Accumulated Time (minutes)')
plt.ylabel('Concentration (ppm)')
plt.grid(True, linestyle='--', alpha=0.5, axis='y')
plt.ylim(0, df['ppm'].max() + 3.0)

# [수정된 부분] 좌우 여백 추가
# 시각적 좌표가 0~100 이므로, -5 ~ 105 정도로 설정하여 여백 확보
padding = 2
plt.xlim(0 - padding, total_visual_width + padding)

plt.tight_layout()
plt.show()