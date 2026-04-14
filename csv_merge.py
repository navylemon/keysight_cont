import pandas as pd
import glob
import os

# 1. 대상 폴더 경로 설정 (문자열 앞에 r을 붙여 이스케이프 문자 처리)
folder_path = r'C:\Users\chohyunbin\OneDrive\PythonBuild\keysight_cont\expdata(1128)'

# 2. 해당 경로에 있는 모든 csv 파일 리스트 가져오기
csv_files = glob.glob(os.path.join(folder_path, "*.csv"))

# 파일이 있는지 확인
if not csv_files:
    print("해당 경로에서 CSV 파일을 찾을 수 없습니다.")
else:
    print(f"총 {len(csv_files)}개의 파일을 발견했습니다. 병합을 시작합니다...")

    # 3. 모든 CSV 파일을 읽어서 리스트에 저장
    # (컬럼이 통일되어 있다고 하셨으므로 그대로 concat 합니다)
    df_list = [pd.read_csv(file) for file in csv_files]

    # 4. 데이터프레임 하나로 합치기
    merged_df = pd.concat(df_list, ignore_index=True)

    # 5. 결과 저장 (같은 폴더에 'merged_data.csv'로 저장)
    output_path = os.path.join(folder_path, "merged_data.csv")
    
    # 한글 깨짐 방지를 위해 'utf-8-sig' 인코딩 사용
    merged_df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"병합 완료! 파일이 저장되었습니다:\n{output_path}")