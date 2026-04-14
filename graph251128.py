import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd

# 1. 데이터 준비
raw_data = """11:50 10.5ppm
12:05 7.8ppm
12:27 6.7ppm
12:48 5.8ppm
13:07 5.8ppm
13:28 5.1ppm"""

cycles_raw = """1st : 11:50~12:27
2nd : 12:28~13:07
3rd : 13:08~13:29"""

# 2. PPM 데이터 파싱
data_list = []
for line in raw_data.split('\n'):
    t_str, v_str = line.split()
    value = float(v_str.replace('ppm', ''))
    data_list.append({'time': t_str, 'ppm': value})

df = pd.DataFrame(data_list)
df['datetime'] = pd.to_datetime(df['time'], format='%H:%M')
start_time = df['datetime'].iloc[0] # 기준 시간 (10:21)
df['elapsed_minutes'] = (df['datetime'] - start_time).dt.total_seconds() / 60

# 3. 사이클 데이터 파싱 및 구간 계산
cycle_list = []
for line in cycles_raw.strip().split('\n'):
    parts = line.split(':', 1) # 첫 번째 콜론만 분리
    label = parts[0].strip()
    times = parts[1].strip().split('~')
    
    # 시작/종료 시간의 경과 분(minute) 계산
    s_obj = pd.to_datetime(times[0].strip(), format='%H:%M')
    e_obj = pd.to_datetime(times[1].strip(), format='%H:%M')
    
    s_elapsed = (s_obj - start_time).total_seconds() / 60
    e_elapsed = (e_obj - start_time).total_seconds() / 60
    
    cycle_list.append({'label': label, 'start': s_elapsed, 'end': e_elapsed})

# 4. 그래프 그리기
plt.figure(figsize=(12, 6))

# (1) 배경색 칠하기 (Cycles)
colors = ['#e6f2ff', '#fff0e6'] # 파랑/주황 파스텔톤 교차
for i, cycle in enumerate(cycle_list):
    plt.axvspan(cycle['start'], cycle['end'], color=colors[i % 2], alpha=0.6)
    # 상단 라벨 표시
    mid = (cycle['start'] + cycle['end']) / 2
    plt.text(mid, df['ppm'].max() + 0.5, f"{cycle['label']} cycle", ha='center', fontweight='bold')

# (2) 선 그래프 그리기
plt.plot(df['elapsed_minutes'], df['ppm'], marker='o', color='#1f77b4', linewidth=2)

# (3) 데이터 값 표시
for i, row in df.iterrows():
    plt.text(row['elapsed_minutes'], row['ppm'] - 0.3, f"{row['ppm']}", ha='center', fontsize=9)

#plt.title('PPM Trend by Cycle')
plt.xlabel('Time (min)')
plt.ylabel(r'F$^{-}$ Concentration (ppm)')
plt.grid(True, linestyle='--', alpha=0.5)
plt.ylim(df['ppm'].min() - 1, df['ppm'].max() + 1.5) # 라벨 공간 확보

plt.show()