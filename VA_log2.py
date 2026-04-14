import pyvisa
import time
import csv
import os
import matplotlib.pyplot as plt
from collections import deque
import sys
import re

# --- 0. 채널 매핑 및 상수 정의 ---
# 사용자 입력 (1, 2, 3)을 SCPI 채널 이름 (P6V, P25V, N25V)으로 변환하기 위한 딕셔너리
CHANNEL_MAPPING = {
    '1': 'P6V',
    '2': 'P25V',
    '3': 'N25V'
}
REVERSE_MAPPING = {v: k for k, v in CHANNEL_MAPPING.items()}
VALID_CHANNEL_NUMS = list(CHANNEL_MAPPING.keys()) # ['1', '2', '3']

# 채널별 플롯 색상 정의 (이전 코드와 동일)
CHANNEL_COLORS = {
    'P6V': 'r',
    'P25V': 'g',
    'N25V': 'b',
}

# --- 1. 디폴트 설정값 (하드코딩 유지 및 디폴트로 사용) ---
DEFAULT_CONFIG = {
    'visa_address': 'USB0::0x2A8D::0x1102::MY57210010::0::INSTR',
    'base_path': 'C:/Users/IDIM_SNU/OneDrive/PythonBuild/keysight_cont',
    'channels': ['1,2'], 
    'target_voltage': {'1': 1.5, '2': 1.5, '3': 1.5}, # <<<<<<< 수정: 채널 3번 디폴트 전압 추가
    'target_current': {'1': 1.0, '2': 1.0, '3': 1.0},  # <<<<<<< 수정: 채널 3번 디폴트 전류 추가
    'data_interval': 1,           # 초 (s)
    'file_save_interval': 5,      # 분 (min)
    'max_plot_points': 100        # 1-100
}
DATA_FOLDER_NAME = 'expdata'

# --- 1.1 사용자 입력 헬퍼 함수 (변경 없음) ---
def get_input_with_default(prompt, default_value, input_type=str):
    """디폴트 값을 사용하거나 새로운 값을 입력받는 함수"""
    default_str = default_value
    if isinstance(default_value, dict):
        default_str = ', '.join(f'{k}:{v}' for k, v in default_value.items())
    elif isinstance(default_value, list):
        default_str = ', '.join(default_value)
    
    while True:
        try:
            choice = input(f"▶ {prompt} (D: {default_str}) 또는 새 값 입력: ").strip()
            
            if choice.upper() == 'D' or choice == '':
                return default_value
            
            # 입력 타입에 따라 변환 시도
            if input_type == int:
                return int(choice)
            elif input_type == float:
                return float(choice)
            else:
                return choice
        except ValueError:
            print("❗ 잘못된 입력 형식입니다. 다시 입력해주세요.")
        except Exception as e:
            print(f"❗ 오류 발생: {e}")

def get_channel_config(default_config):
    """채널(번호), 전압, 전류 설정을 입력받는 복합 함수"""
    
    # 1. 사용할 채널 선택 (복수 선택 가능)
    default_channels_str = ','.join(default_config['channels'])
    
    while True:
        channels_input = get_input_with_default(
            f"사용할 채널 번호 (쉼표로 구분, 예: 1,2,3). 1=P6V, 2=P25V, 3=N25V",
            default_channels_str,
            str
        )
        
        # 입력된 채널 번호 리스트 정리
        selected_channels_num = [ch.strip() for ch in channels_input.split(',') if ch.strip()]
        
        # 유효성 검사
        invalid_channels = [ch for ch in selected_channels_num if ch not in VALID_CHANNEL_NUMS]
        if not selected_channels_num:
            print(f"❗ 채널 번호를 최소한 하나 이상 선택해야 합니다. 유효 채널: {', '.join(VALID_CHANNEL_NUMS)}")
            continue
        if invalid_channels:
            print(f"❗ 잘못된 채널 번호가 포함되어 있습니다: {', '.join(invalid_channels)}. 유효 채널: {', '.join(VALID_CHANNEL_NUMS)}")
            continue
        
        break
        
    config_v = {}
    config_i = {}
    print("\n================= 채널별 전압/전류 설정 =================")
    for ch_num in selected_channels_num:
        # 채널 번호별 디폴트 값 가져오기 (없으면 0.0)
        default_v = default_config['target_voltage'].get(ch_num, 0.0)
        default_i = default_config['target_current'].get(ch_num, 0.0)
        
        ch_name = CHANNEL_MAPPING.get(ch_num, ch_num) # SCPI 채널명 가져오기

        # 전압 입력
        v_input = get_input_with_default(f"[{ch_num} ({ch_name})] 설정 전압 (V)", default_v, float)
        config_v[ch_num] = v_input
        
        # 전류 입력
        i_input = get_input_with_default(f"[{ch_num} ({ch_name})] 설정 전류 (A)", default_i, float)
        config_i[ch_num] = i_input
        
        print("-" * 40)

    return selected_channels_num, config_v, config_i

# --- 1.2 모든 설정값 입력받기 (변경 없음) ---
def get_user_inputs():
    """사용자로부터 모든 설정값을 입력받습니다."""
    config = DEFAULT_CONFIG.copy()
    
    print("\n==================================================")
    print("        [1/3] 실험 설정값 입력 (디폴트: D 입력)")
    print("==================================================")
    
    # 1. VISA 주소
    # 이전에 저장된 주소(USB0::0x1AB1::0x0643::DG8A252002076::INSTR)를 참고할 수 있습니다.
    visa_address = get_input_with_default("파워서플라이 VISA 주소", config['visa_address'])
    config['visa_address'] = visa_address
    
    # 2. 데이터 저장 기본 경로
    base_path = get_input_with_default("데이터 저장 기본 경로", config['base_path'])
    config['base_path'] = base_path
    config['data_folder'] = os.path.join(base_path, DATA_FOLDER_NAME)
    
    # 3, 4, 5. 채널(번호), 전압, 전류
    channels_num, target_v, target_i = get_channel_config(config)
    config['channels'] = channels_num # 채널은 번호로 저장
    config['target_voltage'] = target_v
    config['target_current'] = target_i
    
    # 6. 데이터 측정 주기 (초)
    data_interval = get_input_with_default("데이터 측정 주기 (초)", config['data_interval'], int)
    config['data_interval'] = data_interval
    
    # 7. 파일 저장 주기 (분)
    file_save_interval = get_input_with_default("CSV 파일 저장 주기 (분)", config['file_save_interval'], int)
    config['file_save_interval'] = file_save_interval
    
    # 8. 플롯 최대 데이터 수
    max_plot_points = get_input_with_default("플롯에 표시할 최대 데이터 수 (1~100)", config['max_plot_points'], int)
    config['max_plot_points'] = min(max(max_plot_points, 1), 100) # 1~100 범위 강제
    
    # 최종 설정 요약
    print("\n====================== 최종 설정 요약 ======================")
    print(f"VISA 주소: {config['visa_address']}")
    print(f"데이터 폴더: {config['data_folder']}")
    print(f"사용 채널 (번호/이름): {', '.join(f'{num}/{CHANNEL_MAPPING[num]}' for num in config['channels'])}")
    for ch_num in config['channels']:
        ch_name = CHANNEL_MAPPING[ch_num]
        print(f" - [{ch_name}] 설정 전압: {config['target_voltage'][ch_num]}V / 설정 전류: {config['target_current'][ch_num]}A")
    print(f"측정 주기: {config['data_interval']}초")
    print(f"저장 주기: {config['file_save_interval']}분")
    print(f"플롯 최대점: {config['max_plot_points']}개")
    print("============================================================")
    
    return config

# --- 2. 하드웨어 연결 및 설정 함수 (변경 없음) ---
def setup_devices(visa_address):
    """VISA 주소로 파워서플라이 연결을 시도합니다."""
    print("\n==================== [2/3] 장치 연결 시도 ====================")
    psu = None
    rm = pyvisa.ResourceManager()
    try:
        psu = rm.open_resource(visa_address)
        psu.timeout = 5000
        idn = psu.query('*IDN?')
        print(f"✅ 파워서플라이 연결 성공: {idn.strip()}")
        return psu
    except pyvisa.errors.VisaIOError as e:
        print(f"❌ 파워서플라이 연결 실패: {e}")
        return None

def configure_psu(psu, channels_num, target_v_map, target_i_map):
    """
    키사이트 E36312A 파워서플라이의 여러 채널에 대해 전압과 전류를 설정합니다.
    (채널 번호를 SCPI 이름으로 변환하여 사용)
    """
    if psu is None:
        return
    
    print("\n================== 파워서플라이 설정 적용 ==================")
    for ch_num in channels_num:
        channel = CHANNEL_MAPPING[ch_num] # 채널 번호를 SCPI 이름으로 변환
        voltage = target_v_map.get(ch_num)
        current = target_i_map.get(ch_num)
        
        try:
            # 1. 먼저 채널을 선택합니다.
            psu.write(f'INSTrument:SELect {channel}')
            
            # 2. 선택된 채널에 전압과 전류를 설정합니다.
            psu.write(f'SOURce:VOLTage {voltage}')
            psu.write(f'SOURce:CURRent {current}')
            
            print(f"✅ 채널 '{channel}' ({ch_num}): {voltage}V, {current}A로 설정 완료.")
        except Exception as e:
            print(f"❌ 채널 '{channel}' ({ch_num}) 설정 실패: {e}")

# --- 3. 데이터 읽기 함수 (변경 없음) ---
def read_psu_data(psu, channels_num):
    """모든 선택된 채널의 전압과 전류 데이터를 읽습니다. (SCPI 이름 사용)"""
    data = {}
    if psu is None:
        return data
        
    for ch_num in channels_num:
        channel = CHANNEL_MAPPING[ch_num] # 채널 번호를 SCPI 이름으로 변환
        try:
            # 측정 명령어에 채널을 지정
            voltage_str = psu.query(f'MEASure:VOLTage:DC? {channel}')
            current_str = psu.query(f'MEASure:CURRent:DC? {channel}')
            
            voltage = float(voltage_str)
            current = float(current_str)
            
            # 저항 및 전력 계산
            resistance = voltage / current if current != 0 else float('nan')
            power = voltage * current
            
            # 데이터는 채널 번호를 키로 저장
            data[ch_num] = {
                'V': voltage, 
                'I': current, 
                'R': resistance, 
                'P': power
            }
        except (pyvisa.errors.VisaIOError, ValueError, IndexError) as e:
            # 통신 오류 발생 시 해당 채널 데이터는 None 처리
            data[ch_num] = {'V': None, 'I': None, 'R': None, 'P': None}
            print(f"⚠️ {channel} ({ch_num}) 채널 통신/데이터 오류: {e}")
            
    return data

# --- 4. Real-time plot function (변경 없음) ---
PLOT_TYPES = {
    'V': {'label': 'Voltage (V)', 'ylabel': 'V'},
    'I': {'label': 'Current (A)', 'ylabel': 'A'},
    'R': {'label': 'Resistance (Ω)', 'ylabel': 'Ω'},
    'P': {'label': 'Power (W)', 'ylabel': 'W'}
}

def setup_plot(channels_num):
    """플롯을 설정합니다. 모든 채널의 데이터를 한 그래프에 표시합니다."""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    
    # 채널 번호와 이름을 함께 표시
    channel_list_str = ', '.join(f'{num}({CHANNEL_MAPPING[num]})' for num in channels_num)
    fig.suptitle(f'Keysight PS Data Live Plot (Channels: {channel_list_str})', fontsize=16)

    ax_voltage = axes[0, 0]
    ax_current = axes[0, 1]
    ax_resistance = axes[1, 0]
    ax_power = axes[1, 1]

    ax_voltage.set_title(PLOT_TYPES['V']['label'])
    ax_current.set_title(PLOT_TYPES['I']['label'])
    ax_resistance.set_title(PLOT_TYPES['R']['label'])
    ax_power.set_title(PLOT_TYPES['P']['label'])

    for ax_row in axes:
        for ax in ax_row:
            ax.set_xlabel('Time (s)')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show(block=False)
    
    return fig, ax_voltage, ax_current, ax_resistance, ax_power

def update_plot(fig, ax_voltage, ax_current, ax_resistance, ax_power, data_tuple):
    """
    모든 채널의 데이터를 V, I, R, P 그래프에 색을 달리하여 플롯합니다.
    data_tuple: (timestamps_list, plot_data_buffers, channels_num)
    """
    timestamps, plot_data_buffers, channels_num = data_tuple
    
    x_min = min(timestamps) if timestamps else 0
    x_max = max(timestamps) if timestamps else 1

    plot_axes = {
        'V': ax_voltage,
        'I': ax_current,
        'R': ax_resistance,
        'P': ax_power
    }
    
    # 각 플롯 타입(V, I, R, P)별로 반복
    for plot_key, ax in plot_axes.items():
        plot_info = PLOT_TYPES[plot_key]
        
        ax.clear()
        
        # 각 채널 번호별로 데이터를 플롯
        for ch_num in channels_num:
            ch_name = CHANNEL_MAPPING[ch_num] # SCPI 채널명
            
            # 해당 채널의 플롯 데이터 가져오기
            channel_data = plot_data_buffers.get(ch_num, {}).get(plot_key, deque())
            
            # 플롯
            color = CHANNEL_COLORS.get(ch_name, 'k') # SCPI 채널명 기준으로 색상 가져오기
            ax.plot(timestamps, channel_data, color, label=f'{ch_num} ({ch_name})')
            
        # 축 및 제목 설정
        ax.set_title(plot_info['label'])
        ax.set_ylabel(plot_info['ylabel'])
        ax.set_xlabel('Time (s)')
        ax.set_xlim(left=x_min, right=x_max + 1)
        ax.grid(True)
        if len(channels_num) > 0:
            ax.legend(loc='best') 

    fig.canvas.draw()
    fig.canvas.flush_events()

# --- 5. Main execution function (변경 없음) ---
def run_experiment(config):
    
    # 1. 경로 설정 및 폴더 생성
    data_folder = config['data_folder']
    channels_num = config['channels'] # 채널 번호 리스트
    
    if not channels_num:
        print("❌ 실행할 채널이 선택되지 않았습니다. 프로그램을 종료합니다.")
        return
        
    try:
        os.makedirs(data_folder, exist_ok=True)
        print(f"✅ 데이터 폴더가 생성되었거나 이미 존재합니다: {data_folder}")
    except OSError as e:
        print(f"❌ 폴더 생성 실패: {e}")
        print("프로그램을 종료합니다. 관리자 권한으로 실행하거나 다른 경로를 시도해 보세요.")
        return

    # 2. 장치 연결 및 설정
    psu = setup_devices(config['visa_address'])
    if psu is None:
        print("❌ 장치 연결이 실패했습니다. 프로그램을 종료합니다.")
        return

    configure_psu(psu, channels_num, config['target_voltage'], config['target_current'])
    
    # 3. 구동 시작 입력
    start_input = input("\n==================== [3/3] 장치 구동 시작 ====================\n데이터 수집을 시작하시겠습니까? (y/n): ").strip().lower()
    if start_input != 'y':
        print("데이터 수집을 취소하고 프로그램을 종료합니다.")
        if psu:
            psu.close()
        return
        
    print("\n✅ 데이터 수집 시작... (Ctrl+C를 눌러 중단)")
    
    # 4. CSV 헤더 준비 (모든 채널 포함)
    csv_header = ['Timestamp']
    for ch_num in channels_num:
        ch_name = CHANNEL_MAPPING[ch_num]
        csv_header.extend([f'V_{ch_name}', f'I_{ch_name}', f'R_{ch_name}', f'P_{ch_name}'])

    timestamp_str = time.strftime('%Y-%m-%d_%H-%M-%S')
    file_path = os.path.join(data_folder, f'psu_data_{timestamp_str}.csv')
    print(f"✅ 새로운 파일이 생성되었습니다: {file_path}")
    
    csvfile = open(file_path, 'w', newline='')
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(csv_header)
    
    last_file_creation_time = time.time()

    # 5. 플롯 설정
    fig, ax_voltage, ax_current, ax_resistance, ax_power = setup_plot(channels_num)

    # 6. 데이터 버퍼 초기화
    max_points = config['max_plot_points']
    timestamps_list = deque(maxlen=max_points)
    
    # 채널 번호별 데이터를 저장할 딕셔너리
    plot_data_buffers = {}
    for ch_num in channels_num:
        plot_data_buffers[ch_num] = {
            'V': deque(maxlen=max_points),
            'I': deque(maxlen=max_points),
            'R': deque(maxlen=max_points),
            'P': deque(maxlen=max_points)
        }

    try:
        if psu:
            psu.write('OUTPut:STATe ON') # 파워서플라이 출력 켜기
            print("✅ 파워서플라이 출력 ON.")
        
        start_time = time.time()
        
        while True:
            current_time = time.time()
            
            # --- 파일 저장 주기 확인 ---
            if (current_time - last_file_creation_time) / 60 >= config['file_save_interval']:
                csvfile.close()
                timestamp_str = time.strftime('%Y-%m-%d_%H-%M-%S')
                file_path = os.path.join(data_folder, f'psu_data_{timestamp_str}.csv')
                print(f"✅ 새로운 파일이 생성되었습니다: {file_path}")
                csvfile = open(file_path, 'w', newline='')
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(csv_header)
                last_file_creation_time = current_time

            # --- 데이터 읽기 ---
            data_all_channels = read_psu_data(psu, channels_num) # 키는 번호
            
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # --- CSV 데이터 및 플롯 버퍼 준비 ---
            csv_row = [timestamp]
            log_output = f"Logged: {timestamp}"
            
            timestamps_list.append(time.time() - start_time)

            for ch_num in channels_num:
                ch_name = CHANNEL_MAPPING[ch_num]
                ch_data = data_all_channels.get(ch_num, {'V': None, 'I': None, 'R': None, 'P': None})
                V, I, R, P = ch_data['V'], ch_data['I'], ch_data['R'], ch_data['P']
                
                # CSV 데이터
                csv_row.extend([V, I, R, P])
                log_output += f" | {ch_name} ({ch_num}): V={V}, I={I}, R={R}, P={P}"
                
                # 플롯 버퍼 업데이트
                buffers = plot_data_buffers[ch_num]
                buffers['V'].append(V if V is not None else float('nan'))
                buffers['I'].append(I if I is not None else float('nan'))
                buffers['R'].append(R if R is not None else float('nan'))
                buffers['P'].append(P if P is not None else float('nan'))
            
            csv_writer.writerow(csv_row)
            
            # --- 플롯 업데이트 및 로그 출력 ---
            update_plot(fig, ax_voltage, ax_current, ax_resistance, ax_power, 
                        (timestamps_list, plot_data_buffers, channels_num))
            
            print(log_output)
            
            time.sleep(config['data_interval'])

    except KeyboardInterrupt:
        print("\n데이터 수집 중단. 최종 정리 작업을 수행합니다...")
    finally:
        is_psu_closed = False
        is_csv_closed = False
        
        if psu:
            try:
                psu.write('OUTPut:STATe OFF') # 파워서플라이 출력 끄기
                psu.close()
                print("✅ 파워서플라이 출력 OFF 및 연결 종료.")
                is_psu_closed = True
            except Exception as e:
                print(f"❌ 파워서플라이 종료 중 오류 발생: {e}")

        if 'csvfile' in locals() and not csvfile.closed:
            csvfile.close()
            print("✅ CSV 파일 닫기 완료.")
            is_csv_closed = True
        
        # Matplotlib 윈도우 닫기
        try:
            plt.close(fig)
        except Exception:
            pass
            
        print("\n==================================================")
        print("          최종 정리 완료. 프로그램 종료 대기")
        print(f"장치 연결 종료: {'완료' if is_psu_closed else '실패/연결 없음'}")
        print(f"데이터 파일 저장: {'완료' if is_csv_closed else '실패/미처리'}")
        print("==================================================")
        
        # 터미널 창 종료 여부 확인
        input("터미널 창을 닫으려면 아무 키나 누르세요...")

if __name__ == "__main__":
    # 1. 설정값 입력
    final_config = get_user_inputs()
    
    # 2. 실험 시작
    run_experiment(final_config)