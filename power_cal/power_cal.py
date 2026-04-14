import pandas as pd
import glob
import os

# 1. 파일 불러오기 및 합치기
# 현재 폴더 내의 'psu_data_'로 시작하는 모든 csv 파일을 읽어옵니다.
all_files = sorted(glob.glob("psu_data_*.csv"))

if not all_files:
    print("파일을 찾을 수 없습니다. 경로를 확인해주세요.")
else:
    print(f"총 {len(all_files)}개의 파일을 발견했습니다. 데이터를 병합합니다...")
    
    df_list = []
    for filename in all_files:
        df_temp = pd.read_csv(filename)
        df_list.append(df_temp)

    # 하나의 데이터프레임으로 합치기
    df_all = pd.concat(df_list, ignore_index=True)

    # 2. 데이터 전처리
    # Timestamp 컬럼을 날짜시간 형식으로 변환
    df_all['Timestamp'] = pd.to_datetime(df_all['Timestamp'])
    
    # 시간 순서대로 정렬
    df_all = df_all.sort_values(by='Timestamp').reset_index(drop=True)

    # 각 측정 사이의 시간 간격(초) 계산 (정확한 에너지 계산을 위해 필수)
    # 첫 번째 데이터의 간격은 0 또는 평균적인 1초로 가정
    df_all['dt'] = df_all['Timestamp'].diff().dt.total_seconds().fillna(0)

    # 3. 사이클(시간 구간) 정의
    # 파일명에 있는 날짜(2025-11-28)를 기준으로 설정합니다.
    target_date = "2025-11-28"
    
    cycles = {
        "1st Cycle": ("11:50:00", "12:27:00"),
        "2nd Cycle": ("12:28:00", "13:07:00"),
        "3rd Cycle": ("13:08:00", "13:29:00")
    }

    print("-" * 50)
    print(f"{'Cycle Name':<15} | {'Avg Power (W)':<15} | {'Energy (Wh)':<15}")
    print("-" * 50)

    for cycle_name, (start_time, end_time) in cycles.items():
        # 시작 및 종료 시간 생성
        start_dt = pd.to_datetime(f"{target_date} {start_time}")
        end_dt = pd.to_datetime(f"{target_date} {end_time}")

        # 해당 구간 데이터 필터링
        mask = (df_all['Timestamp'] >= start_dt) & (df_all['Timestamp'] <= end_dt)
        cycle_df = df_all.loc[mask]

        if cycle_df.empty:
            print(f"{cycle_name:<15} | 데이터를 찾을 수 없음")
            continue

        # --- 핵심 계산 로직 ---
        # 1. 평균 사용 전력 (W)
        avg_power = cycle_df['P_P6V'].mean()

        # 2. 전력량 (Wh) = 전력(W) * 시간(h)
        # 각 구간의 전력 * 시간간격(초)를 모두 더한 뒤 3600으로 나누어 Wh로 변환
        total_energy_joules = (cycle_df['P_P6V'] * cycle_df['dt']).sum()
        total_energy_wh = total_energy_joules / 3600

        print(f"{cycle_name:<15} | {avg_power:.6f} W     | {total_energy_wh:.6f} Wh")

    print("-" * 50)