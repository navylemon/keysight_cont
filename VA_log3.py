import pyvisa
import time
import csv
import os
import matplotlib.pyplot as plt
from collections import deque
import sys
import re
import traceback  # 에러 추적을 위해 추가

# --- 0. 채널 매핑 및 상수 정의 ---
CHANNEL_MAPPING = {
    '1': 'P6V',
    '2': 'P25V',
    '3': 'N25V'
}
VALID_CHANNEL_NUMS = list(CHANNEL_MAPPING.keys())

# 채널별 플롯 색상 정의
CHANNEL_COLORS = {
    'P6V': 'r',
    'P25V': 'g',
    'N25V': 'b',
}

# --- 1. 디폴트 설정값 ---
DEFAULT_CONFIG = {
    'visa_address': 'USB0::0x2A8D::0x1102::MY57210010::0::INSTR',
    'base_path': 'C:/Users/IDIM_SNU/OneDrive/PythonBuild/keysight_cont',
    'channels': ['1'], 
    'target_voltage': {'1': 1.5, '2': 1.5, '3': 1.5},
    'target_current': {'1': 1.0, '2': 1.0, '3': 1.0},
    'data_interval': 1,           # 초 (s)
    'file_save_interval': 5,      # 분 (min)
    'max_plot_points': 100        # 1-100
}
DATA_FOLDER_NAME = 'expdata'

# --- 1.1 사용자 입력 헬퍼 함수 ---
def get_input_with_default(prompt, default_value, input_type=str):
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
    default_channels_str = ','.join(default_config['channels'])
    
    while True:
        channels_input = get_input_with_default(
            f"사용할 채널 번호 (쉼표로 구분, 예: 1,2,3). 1=P6V, 2=P25V, 3=N25V",
            default_channels_str,
            str
        )
        
        selected_channels_num = [ch.strip() for ch in channels_input.split(',') if ch.strip()]
        invalid_channels = [ch for ch in selected_channels_num if ch not in VALID_CHANNEL_NUMS]
        
        if not selected_channels_num:
            print(f"❗ 채널 번호를 최소한 하나 이상 선택해야 합니다.")
            continue
        if invalid_channels:
            print(f"❗ 잘못된 채널 번호: {', '.join(invalid_channels)}")
            continue
        break
        
    config_v = {}
    config_i = {}
    print("\n================= 채널별 전압/전류 설정 =================")
    for ch_num in selected_channels_num:
        default_v = default_config['target_voltage'].get(ch_num, 0.0)
        default_i = default_config['target_current'].get(ch_num, 0.0)
        ch_name = CHANNEL_MAPPING.get(ch_num, ch_num)

        v_input = get_input_with_default(f"[{ch_num} ({ch_name})] 설정 전압 (V)", default_v, float)
        config_v[ch_num] = v_input
        
        i_input = get_input_with_default(f"[{ch_num} ({ch_name})] 설정 전류 (A)", default_i, float)
        config_i[ch_num] = i_input
        print("-" * 40)

    return selected_channels_num, config_v, config_i

def get_user_inputs():
    config = DEFAULT_CONFIG.copy()
    
    print("\n==================================================")
    print("        [1/3] 실험 설정값 입력 (디폴트: D 입력)")
    print("==================================================")
    
    visa_address = get_input_with_default("파워서플라이 VISA 주소", config['visa_address'])
    config['visa_address'] = visa_address
    
    base_path = get_input_with_default("데이터 저장 기본 경로", config['base_path'])
    config['base_path'] = base_path
    config['data_folder'] = os.path.join(base_path, DATA_FOLDER_NAME)
    
    channels_num, target_v, target_i = get_channel_config(config)
    config['channels'] = channels_num
    config['target_voltage'] = target_v
    config['target_current'] = target_i
    
    data_interval = get_input_with_default("데이터 측정 주기 (초)", config['data_interval'], int)
    config['data_interval'] = data_interval
    
    file_save_interval = get_input_with_default("CSV 파일 저장 주기 (분)", config['file_save_interval'], int)
    config['file_save_interval'] = file_save_interval
    
    max_plot_points = get_input_with_default("플롯에 표시할 최대 데이터 수 (1~100)", config['max_plot_points'], int)
    config['max_plot_points'] = min(max(max_plot_points, 1), 100)
    
    return config

# --- 2. 하드웨어 연결 및 설정 함수 ---
def setup_devices(visa_address):
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
    except Exception as e:
        print(f"❌ 알 수 없는 오류 발생: {e}")
        return None

def configure_psu(psu, channels_num, target_v_map, target_i_map):
    if psu is None:
        return
    
    print("\n================== 파워서플라이 설정 적용 ==================")
    for ch_num in channels_num:
        channel = CHANNEL_MAPPING[ch_num]
        voltage = target_v_map.get(ch_num)
        current = target_i_map.get(ch_num)
        
        try:
            psu.write(f'INSTrument:SELect {channel}')
            psu.write(f'SOURce:VOLTage {voltage}')
            psu.write(f'SOURce:CURRent {current}')
            print(f"✅ 채널 '{channel}' ({ch_num}): {voltage}V, {current}A로 설정 완료.")
        except Exception as e:
            print(f"❌ 채널 '{channel}' ({ch_num}) 설정 실패: {e}")

# --- 3. 데이터 읽기 함수 ---
def read_psu_data(psu, channels_num):
    data = {}
    if psu is None:
        return data
        
    for ch_num in channels_num:
        channel = CHANNEL_MAPPING[ch_num]
        try:
            voltage_str = psu.query(f'MEASure:VOLTage:DC? {channel}')
            current_str = psu.query(f'MEASure:CURRent:DC? {channel}')
            
            voltage = float(voltage_str)
            current = float(current_str)
            resistance = voltage / current if current != 0 else float('nan')
            power = voltage * current
            
            data[ch_num] = {'V': voltage, 'I': current, 'R': resistance, 'P': power}
        except Exception as e:
            data[ch_num] = {'V': None, 'I': None, 'R': None, 'P': None}
            # print(f"⚠️ 통신 오류 ({channel}): {e}") # 로그가 너무 많으면 주석 처리
            
    return data

# --- 4. Real-time plot function (채널별 분리형) ---
def setup_plot(channels_num):
    """
    채널 수에 맞춰 N행 2열의 그래프를 동적으로 생성합니다.
    """
    plt.style.use('seaborn-v0_8-whitegrid')
    
    num_channels = len(channels_num)
    # squeeze=False: 채널 1개여도 2차원 배열 유지
    fig, axes = plt.subplots(num_channels, 2, figsize=(10, 4 * num_channels), squeeze=False)
    
    channel_list_str = ', '.join(f'{num}({CHANNEL_MAPPING[num]})' for num in channels_num)
    fig.suptitle(f'Keysight PS Live Plot (Channels: {channel_list_str})', fontsize=16)

    axes_dict = {}

    for i, ch_num in enumerate(channels_num):
        ch_name = CHANNEL_MAPPING[ch_num]
        
        # 왼쪽 그래프 (Voltage)
        ax_v = axes[i, 0]
        ax_v.set_title(f'[{ch_num}:{ch_name}] Voltage')
        ax_v.set_ylabel('Voltage (V)')
        
        # 오른쪽 그래프 (Current)
        ax_i = axes[i, 1]
        ax_i.set_title(f'[{ch_num}:{ch_name}] Current')
        ax_i.set_ylabel('Current (A)')
        
        axes_dict[ch_num] = {'V': ax_v, 'I': ax_i}
        
        # 마지막 행에만 X축 라벨
        if i == num_channels - 1:
            ax_v.set_xlabel('Time (s)')
            ax_i.set_xlabel('Time (s)')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show(block=False)
    
    return fig, axes_dict

def update_plot(fig, axes_dict, data_tuple):
    timestamps, plot_data_buffers, channels_num = data_tuple
    
    x_min = min(timestamps) if timestamps else 0
    x_max = max(timestamps) if timestamps else 1

    for ch_num in channels_num:
        ch_name = CHANNEL_MAPPING[ch_num]
        color = CHANNEL_COLORS.get(ch_name, 'k')
        
        ax_v = axes_dict[ch_num]['V']
        ax_i = axes_dict[ch_num]['I']
        
        data_v = plot_data_buffers.get(ch_num, {}).get('V', deque())
        data_i = plot_data_buffers.get(ch_num, {}).get('I', deque())
        
        if len(data_v) == len(timestamps):
            # 전압 그래프
            ax_v.clear()
            ax_v.plot(timestamps, data_v, color=color, label=f'{ch_num} V')
            ax_v.set_title(f'[{ch_num}:{ch_name}] Voltage')
            ax_v.set_ylabel('Voltage (V)')
            ax_v.set_xlim(left=x_min, right=x_max + 1)
            ax_v.grid(True)
            
            # 전류 그래프
            ax_i.clear()
            ax_i.plot(timestamps, data_i, color=color, linestyle='--', label=f'{ch_num} I')
            ax_i.set_title(f'[{ch_num}:{ch_name}] Current')
            ax_i.set_ylabel('Current (A)')
            ax_i.set_xlim(left=x_min, right=x_max + 1)
            ax_i.grid(True)

    fig.canvas.draw()
    fig.canvas.flush_events()

# --- 5. Main execution function ---
def run_experiment(config):
    
    data_folder = config['data_folder']
    channels_num = config['channels'] 
    
    if not channels_num:
        print("❌ 실행할 채널이 선택되지 않았습니다. 프로그램을 종료합니다.")
        return
        
    try:
        os.makedirs(data_folder, exist_ok=True)
        print(f"✅ 데이터 폴더: {data_folder}")
    except OSError as e:
        print(f"❌ 폴더 생성 실패: {e}")
        return

    # 장치 연결
    psu = setup_devices(config['visa_address'])
    if psu is None:
        return

    # 전압/전류 값 설정
    configure_psu(psu, channels_num, config['target_voltage'], config['target_current'])
    
    # 구동 시작 확인
    start_input = input("\n==================== [3/3] 장치 구동 시작 ====================\n데이터 수집을 시작하시겠습니까? (y/n): ").strip().lower()
    if start_input != 'y':
        print("데이터 수집을 취소합니다.")
        if psu: psu.close()
        return
        
    print("\n✅ 데이터 수집 시작... (Ctrl+C를 눌러 중단)")
    
    # CSV 헤더
    csv_header = ['Timestamp']
    for ch_num in channels_num:
        ch_name = CHANNEL_MAPPING[ch_num]
        csv_header.extend([f'V_{ch_name}', f'I_{ch_name}', f'R_{ch_name}', f'P_{ch_name}'])

    timestamp_str = time.strftime('%Y-%m-%d_%H-%M-%S')
    file_path = os.path.join(data_folder, f'psu_data_{timestamp_str}.csv')
    csvfile = open(file_path, 'w', newline='')
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(csv_header)
    last_file_creation_time = time.time()

    # 플롯 설정 (수정된 분리형 함수 호출)
    fig, axes_dict = setup_plot(channels_num)

    # 데이터 버퍼
    max_points = config['max_plot_points']
    timestamps_list = deque(maxlen=max_points)
    plot_data_buffers = {}
    for ch_num in channels_num:
        plot_data_buffers[ch_num] = {
            'V': deque(maxlen=max_points), 'I': deque(maxlen=max_points),
            'R': deque(maxlen=max_points), 'P': deque(maxlen=max_points)
        }

    try:
        if psu:
            # --- [수정됨] 모든 채널 순회하며 켜기 ---
            print("\n--- 채널 출력 활성화 ---")
            for ch_num in channels_num:
                ch_name = CHANNEL_MAPPING[ch_num]
                try:
                    psu.write(f'INSTrument:SELect {ch_name}')
                    psu.write('OUTPut:STATe ON')
                    print(f"✅ [{ch_num}:{ch_name}] Output ON")
                except Exception as e:
                    print(f"❌ [{ch_num}:{ch_name}] 켜기 실패: {e}")
            print("-----------------------")
            # -------------------------------------
        
        start_time = time.time()
        
        while True:
            current_time = time.time()
            
            # 파일 저장 주기 체크
            if (current_time - last_file_creation_time) / 60 >= config['file_save_interval']:
                csvfile.close()
                timestamp_str = time.strftime('%Y-%m-%d_%H-%M-%S')
                file_path = os.path.join(data_folder, f'psu_data_{timestamp_str}.csv')
                print(f"\n✅ 새 파일 생성: {file_path}")
                csvfile = open(file_path, 'w', newline='')
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(csv_header)
                last_file_creation_time = current_time

            # 데이터 수집
            data_all_channels = read_psu_data(psu, channels_num)
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            
            csv_row = [timestamp]
            log_output = f"Logged: {timestamp.split(' ')[1]}"
            timestamps_list.append(time.time() - start_time)

            for ch_num in channels_num:
                ch_name = CHANNEL_MAPPING[ch_num]
                ch_data = data_all_channels.get(ch_num, {'V': None, 'I': None, 'R': None, 'P': None})
                V, I, R, P = ch_data['V'], ch_data['I'], ch_data['R'], ch_data['P']
                
                csv_row.extend([V, I, R, P])
                if V is not None:
                    log_output += f" | {ch_name}: {V:.3f}V, {I:.3f}A"
                
                buffers = plot_data_buffers[ch_num]
                buffers['V'].append(V if V is not None else float('nan'))
                buffers['I'].append(I if I is not None else float('nan'))
                buffers['R'].append(R if R is not None else float('nan'))
                buffers['P'].append(P if P is not None else float('nan'))
            
            csv_writer.writerow(csv_row)
            
            # 플롯 업데이트
            update_plot(fig, axes_dict, (timestamps_list, plot_data_buffers, channels_num))
            
            print(log_output)
            time.sleep(config['data_interval'])

    except KeyboardInterrupt:
        print("\n데이터 수집 중단. 최종 정리 작업을 수행합니다...")
    except Exception as e:
        print(f"\n❗ 실행 중 예상치 못한 오류 발생:\n{traceback.format_exc()}")
    finally:
        is_psu_closed = False
        is_csv_closed = False
        
        if psu:
            try:
                # --- [수정됨] 모든 채널 순회하며 끄기 ---
                print("\n--- 채널 출력 비활성화 ---")
                for ch_num in channels_num:
                    ch_name = CHANNEL_MAPPING[ch_num]
                    try:
                        psu.write(f'INSTrument:SELect {ch_name}')
                        psu.write('OUTPut:STATe OFF')
                    except:
                        pass
                print("✅ 모든 채널 Output OFF 명령 전송 완료.")
                # --------------------------------------
                
                psu.close()
                is_psu_closed = True
            except Exception as e:
                print(f"❌ 파워서플라이 종료 중 오류 발생: {e}")

        if 'csvfile' in locals() and not csvfile.closed:
            csvfile.close()
            is_csv_closed = True
        
        try:
            plt.close(fig)
        except Exception:
            pass
            
        print("\n==================================================")
        print("          최종 정리 완료.")
        print(f"장치 연결 종료: {'완료' if is_psu_closed else '실패/연결 없음'}")
        print("==================================================")

if __name__ == "__main__":
    try:
        # 1. 설정값 입력
        final_config = get_user_inputs()
        
        # 2. 실험 시작
        run_experiment(final_config)
    except Exception as e:
        print(f"\n❗ 치명적인 오류 발생:\n{traceback.format_exc()}")
    
    # 프로그램 종료 전 대기 (창이 바로 꺼지는 것 방지)
    input("\n종료하려면 Enter 키를 누르세요...")