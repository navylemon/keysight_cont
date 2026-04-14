import matplotlib.pyplot as plt

# 데이터 준비
time = [0, 20, 40, 60, 120]
c_1st_operation = [10.0, 7.2, 7.1, 7.1, 7.0]
c_after_regen = [10.0, 8.0, 7.0, 6.9, 6.9]

# 그래프 그리기
plt.figure(figsize=(8, 5))

# 음영 영역으로 구간 구분
# Adsorption (0 ~ 40분)
plt.axvspan(0, 40, color='#e6f2ff', alpha=0.6)
plt.text(20, 6.0, 'Adsorption\n(< 40 min)', ha='center', va='center', fontsize=20, color='#1f77b4')

# Saturation (40 ~ 120분)
plt.axvspan(40, 125, color='#ffe6e6', alpha=0.6)
plt.text(80, 6.0, 'Saturation\n(> 40 min)', ha='center', va='center', fontsize=20, color='red')

# 선 그래프 그리기
plt.plot(time, c_1st_operation, marker='s', linestyle='-', linewidth=2, label='1st operation', color='#1f77b4')
plt.plot(time, c_after_regen, marker='s', linestyle='-', linewidth=2, label='After regenation', color='#ff7f0e')

# 축 설정
plt.xlabel('Time (min)', fontsize=14)

# [수정됨] LaTeX 문법을 사용하여 위첨자(-) 적용
plt.ylabel(r'F$^{-}$ Concentration (ppm)', fontsize=14)

plt.xlim(-5, 125)
plt.ylim(5.5, 10.5) # y축 시작점을 5 근처로 설정하여 그래프 상단 배치
plt.xticks([0, 20, 40, 60, 80, 100, 120], fontsize=12)
plt.yticks(fontsize=12)

# 범례 표시
plt.legend(fontsize=12, loc='upper right')

plt.tight_layout()
plt.show()