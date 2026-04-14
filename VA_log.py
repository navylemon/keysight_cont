import pyvisa
import time
import csv
import os
import matplotlib.pyplot as plt
from collections import deque

# --- 1. 설정값 (반드시 수정해주세요) ---
# 기존: SERIAL_PORT = 'COM3' (제거됨)
# 기존: BAUD_RATE = 9600 (제거됨)

VISA_ADDRESS = 'USB0::0x2A8D::0x1102::MY57210010::0::INSTR' # (현재 설정 유지)

# 사용 중인 파워서플라이 채널을 리스트로 지정합니다.
AFN_PSU_CHANNELS = ['P6V'] 

# 파워서플라이에 설정할 전압과 전류
TARGET_VOLTAGE = 1.5  # 설정할 전압값 (단위: V)
TARGET_CURRENT = 1.0  # 설정할 전류값 (단위: A)

DATA_INTERVAL = 1

# CSV 파일 저장 폴더 및 파일명 규칙(절대경로-원드라이브)
DATA_FOLDER_NAME = 'expdata'
DATA_FOLDER = os.path.join('C:/Users/navyl/OneDrive/문서/25-1 CNT CDI/keysight_cont', DATA_FOLDER_NAME)

FILE_SAVE_INTERVAL_MINUTES = 5

MAX_POINTS = 100

# --- 2. 하드웨어 연결 및 설정 함수 ---
def setup_devices():
    psu = None

    rm = pyvisa.ResourceManager()
    try:
        psu = rm.open_resource(VISA_ADDRESS)
        psu.timeout = 5000
        idn = psu.query('*IDN?')
        print(f"✅ 파워서플라이 연결 성공: {idn.strip()}")
    except pyvisa.errors.VisaIOError as e:
        print(f"❌ 파워서플라이 연결 실패: {e}")

    # ser가 제거되었으므로 psu만 반환
    return psu

# --- 2.2 파워서플라이 설정 함수 (E36312A 모델용) ---
def configure_psu(psu, channel, voltage, current):
    """
    키사이트 E36312A 파워서플라이의 전압과 전류를 설정합니다.
    """
    if psu is None:
        return
    try:
        # 1. 먼저 채널을 선택합니다.
        psu.write(f'INSTrument:SELect {channel}')
        
        # 2. 선택된 채널에 전압과 전류를 설정합니다.
        psu.write(f'SOURce:VOLTage {voltage}')
        psu.write(f'SOURce:CURRent {current}')
        
        print(f"✅ 파워서플라이 채널 '{channel}'의 전압이 {voltage}V, 전류가 {current}A로 설정되었습니다.")
    except Exception as e:
        print(f"❌ 파워서플라이 설정 실패: {e}")

# --- 3. 데이터 읽기 함수 ---
# read_dht_data 함수 제거됨

def read_psu_data(psu, channel):
    if psu is None:
        return None, None
    try:
        voltage_str = psu.query(f'MEASure:VOLTage:DC? {channel}')
        current_str = psu.query(f'MEASure:CURRent:DC? {channel}')
        
        try:
            voltage = float(voltage_str)
            current = float(current_str)
            
            return voltage, current
        except (ValueError, IndexError):
            print(f"⚠️ {channel} 채널에서 손상된 데이터가 수신되었습니다.")
            return None, None
            
    except Exception as e:
        print(f"⚠️ {channel} 채널 통신 오류: {e}")
        return None, None

# --- 4. Real-time plot function ---
def setup_plot():
    # 2x2 그리드로 변경
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle('IPCNT Team Keysight PS Data Live Plot', fontsize=16)

    # 4개 서브플롯을 각각의 변수에 할당합니다.
    ax_voltage = axes[0, 0]
    ax_current = axes[0, 1]
    ax_resistance = axes[1, 0]
    ax_power = axes[1, 1] # 새로운 Power 플롯

    # 각 플롯에 제목과 라벨 설정
    ax_voltage.set_title(f'Voltage (V) from {AFN_PSU_CHANNELS[0]}')
    ax_current.set_title(f'Current (A) from {AFN_PSU_CHANNELS[0]}')
    ax_resistance.set_title(f'Resistance (Ω) from {AFN_PSU_CHANNELS[0]}')
    ax_power.set_title(f'Power (W) from {AFN_PSU_CHANNELS[0]}')

    # 모든 플롯에 공통적으로 X축 라벨 설정
    for ax_row in axes:
        for ax in ax_row:
            ax.set_xlabel('Time (s)')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show(block=False)
    
    # 반환값 변경
    return fig, ax_voltage, ax_current, ax_resistance, ax_power

def update_plot(fig, ax_voltage, ax_current, ax_resistance, ax_power, data):
    # data 구조 변경: temps, humidities 제거, powers 추가
    timestamps, voltages, currents, resistances, powers = data
    
    # DHT 플롯 제거됨

    ax_voltage.clear()
    ax_voltage.plot(timestamps, voltages, 'g-', label='Voltage (V)')
    ax_voltage.set_ylabel('V')
    ax_voltage.grid(True)
    ax_voltage.set_title(f'Voltage (V) from {AFN_PSU_CHANNELS[0]}') # clear() 후 제목 다시 설정
    
    ax_current.clear()
    ax_current.plot(timestamps, currents, 'm-', label='Current (A)')
    ax_current.set_ylabel('A')
    ax_current.grid(True)
    ax_current.set_title(f'Current (A) from {AFN_PSU_CHANNELS[0]}') # clear() 후 제목 다시 설정

    ax_resistance.clear()
    ax_resistance.plot(timestamps, resistances, 'c-', label='Resistance (Ω)')
    ax_resistance.set_ylabel('Ω')
    ax_resistance.grid(True)
    ax_resistance.set_title(f'Resistance (Ω) from {AFN_PSU_CHANNELS[0]}') # clear() 후 제목 다시 설정
    
    # Power 플롯 추가
    ax_power.clear()
    ax_power.plot(timestamps, powers, 'k-', label='Power (W)')
    ax_power.set_ylabel('W')
    ax_power.grid(True)
    ax_power.set_title(f'Power (W) from {AFN_PSU_CHANNELS[0]}') # clear() 후 제목 다시 설정
    
    # 모든 플롯에 X축 라벨 설정
    for ax in [ax_voltage, ax_current, ax_resistance, ax_power]:
        ax.set_xlabel('Time (s)')

    fig.canvas.draw()
    fig.canvas.flush_events()

# --- 5. Main execution function ---
def run_experiment():
    # ser 제거됨
    psu = setup_devices()
    
    # ser 체크 로직 제거됨
    if psu is None:
        print("❌ 연결된 파워서플라이 장치가 없어 프로그램을 종료합니다.")
        return

    print(f"데이터 폴더 경로: {DATA_FOLDER}")
    try:
        os.makedirs(DATA_FOLDER, exist_ok=True)
        print(f"✅ '{DATA_FOLDER_NAME}' 폴더가 생성되었거나 이미 존재합니다.")
    except OSError as e:
        print(f"❌ 폴더 생성 실패: {e}")
        print("프로그램을 종료합니다. 관리자 권한으로 실행하거나 다른 경로를 시도해 보세요.")
        return

    # 파워서플라이 전압/전류 설정
    if psu and AFN_PSU_CHANNELS:
        configure_psu(psu, AFN_PSU_CHANNELS[0], TARGET_VOLTAGE, TARGET_CURRENT)

    # 반환값 변경
    fig, ax_voltage, ax_current, ax_resistance, ax_power = setup_plot()

    timestamps_list = deque(maxlen=MAX_POINTS)
    # temps_list, humidities_list 제거됨
    voltages_list = deque(maxlen=MAX_POINTS)
    currents_list = deque(maxlen=MAX_POINTS)
    resistances_list = deque(maxlen=MAX_POINTS)
    powers_list = deque(maxlen=MAX_POINTS) # Power 데이터용 리스트 추가

    print("\n데이터 수집 시작... (Ctrl+C를 눌러 중단)")
    # 아두이노 데이터 수집 안내 제거됨
    if psu:
        print(f"파워서플라이({AFN_PSU_CHANNELS[0]}) 데이터가 수집됩니다.")
    
    timestamp_str = time.strftime('%Y-%m-%d_%H-%M-%S')
    file_path = os.path.join(DATA_FOLDER, f'psu_data_{timestamp_str}.csv')
    print(f"✅ 새로운 파일이 생성되었습니다: {file_path}")
    
    csvfile = open(file_path, 'w', newline='')
    csv_writer = csv.writer(csvfile)
    # CSV 헤더 변경 (온도, 습도 제거, Power 추가)
    csv_writer.writerow(['Timestamp', 'Voltage_from_PSU', 'Current_from_PSU', 'Resistance_from_PSU', 'Power_from_PSU'])
    
    last_file_creation_time = time.time()

    try:
        if psu:
            psu.write('OUTPut:STATe ON') # 파워서플라이 출력 켜기
        
        start_time = time.time()
        
        while True:
            current_time = time.time()
            if (current_time - last_file_creation_time) / 60 >= FILE_SAVE_INTERVAL_MINUTES:
                csvfile.close()
                timestamp_str = time.strftime('%Y-%m-%d_%H-%M-%S')
                file_path = os.path.join(DATA_FOLDER, f'psu_data_{timestamp_str}.csv')
                print(f"✅ 새로운 파일이 생성되었습니다: {file_path}")
                csvfile = open(file_path, 'w', newline='')
                csv_writer = csv.writer(csvfile)
                # CSV 헤더 변경
                csv_writer.writerow(['Timestamp', 'Voltage_from_PSU', 'Current_from_PSU', 'Resistance_from_PSU', 'Power_from_PSU'])
                last_file_creation_time = current_time

            # temp, humidity 읽기 로직 제거됨
            voltage, current = read_psu_data(psu, AFN_PSU_CHANNELS[0])
            
            resistance = None
            if voltage is not None and current is not None:
                # 저항 계산
                if current != 0:
                    resistance = voltage / current
                else:
                    resistance = float('inf')
            
            power = None
            if voltage is not None and current is not None:
                # Power 계산
                power = voltage * current
            
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            # CSV 데이터 쓰기 변경 (온도, 습도 제거, Power 추가)
            csv_writer.writerow([timestamp, voltage, current, resistance, power])
            
            timestamps_list.append(time.time() - start_time)
            # temps_list.append(temp if temp is not None else float('nan')) (제거됨)
            # humidities_list.append(humidity if humidity is not None else float('nan')) (제거됨)
            voltages_list.append(voltage if voltage is not None else float('nan'))
            currents_list.append(current if current is not None else float('nan'))
            resistances_list.append(resistance if resistance is not None else float('nan'))
            powers_list.append(power if power is not None else float('nan')) # Power 리스트에 추가
            
            # update_plot 호출 인자 변경
            update_plot(fig, ax_voltage, ax_current, ax_resistance, ax_power, 
                        (timestamps_list, voltages_list, currents_list, resistances_list, powers_list))
            
            # 로그 출력 변경
            print(f"Logged: {timestamp}, Volt(PSU): {voltage}, Curr(PSU): {current}, Res(calc): {resistance}, Power(calc): {power}")
            
            time.sleep(DATA_INTERVAL)

    except KeyboardInterrupt:
        print("\n데이터 수집 중단.")
    finally:
        if psu:
            psu.write('OUTPut:STATe OFF') # 파워서플라이 출력 끄기
            psu.close()
        # ser.close() 제거됨
        if 'csvfile' in locals() and not csvfile.closed:
            csvfile.close()
        print("모든 장비 연결이 종료되었습니다.")

if __name__ == "__main__":
    run_experiment()