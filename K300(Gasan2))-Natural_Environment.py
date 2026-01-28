import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import platform
from matplotlib import font_manager, rc

# 1. 운영체제 감지 및 한글 폰트 설정
system_name = platform.system()

if system_name == 'Windows':
    # Windows의 경우 맑은 고딕 설정
    rc('font', family='Malgun Gothic')
elif system_name == 'Darwin':
    # Mac의 경우 애플 고딕 설정
    rc('font', family='AppleGothic')
else:
    # Linux 계열(Colab 등)은 나눔 폰트가 설치되어 있다고 가정
    # 폰트가 없다면 설치 후 경로 지정 필요
    rc('font', family='NanumGothic')

# 마이너스 기호 깨짐 방지 설정 
plt.rcParams['axes.unicode_minus'] = False

# 2. 데이터 로드 및 전처리 
# 실제 파일 경로에 맞게 수정 필요
file_path = '가산역(260123)-15도세팅.csv'

try:
    # CSV 파일 읽기
    df = pd.read_csv(file_path)
    
    # '날짜' 컬럼을 datetime 객체로 변환하여 시계열 처리 준비
    df['날짜'] = pd.to_datetime(df['날짜'])
    
    # 데이터를 시간순으로 정렬 (혹시 모를 순서 섞임 방지)
    df.sort_values('날짜', inplace=True)
    
    # 날짜를 인덱스로 설정
    df.set_index('날짜', inplace=True)

except Exception as e:
    print(f"데이터 로드 중 오류 발생: {e}")
    # 오류 발생 시 더미 데이터 생성 또는 중단 로직 필요

# 3. 그래프 그리기 (시각화)
plt.figure(figsize=(15, 8)) # 가독성을 위해 큰 사이즈 설정

# 각 센서 데이터 플로팅
# 02번 프린터위 데이터: 가장 높은 온도를 보이므로 붉은 계열 사용
plt.plot(df.index, df['02 프린터위'], label='02 프린터 위 (최고온도 구역)', 
         color='#FF4500', linewidth=2.5)

# 01번 프린터앞 데이터: 사용자와 맞닿는 부분, 낮은 온도 주의 필요
plt.plot(df.index, df['01 프린터앞'], label='01 프린터 앞 (사용자 인터페이스)', 
         color='#2E8B57', linewidth=1.5, linestyle='--')

# 03번 부스내부 데이터: 내부 공기 온도
plt.plot(df.index, df['03 부스내부'], label='03 부스 내부 (주변 공기)', 
         color='#1E90FF', linewidth=1.5, linestyle='-.')

# 04번 부스외부 데이터: 외기 온도 (베이스라인)
plt.plot(df.index, df['04 부스외부'], label='04 부스 외부 (외기)', 
         color='#708090', linewidth=1.5, alpha=0.7)

# 4. 기준선 추가 (분석의 핵심)
# "15도 세팅"이라는 파일명에 근거하여 목표 온도 표시
plt.axhline(y=15, color='red', linestyle=':', alpha=0.8, label='목표 설정 온도 (15°C)')
# 결빙 위험 구간 표시 (0도)
plt.axhline(y=0, color='blue', linestyle=':', alpha=0.6, label='결빙점 (0°C)')

# 5. 그래프 세부 디자인 및 포맷팅
plt.title('가산역 무인 프린터 부스 열환경 모니터링 분석\n(2026년 1월 23일 03:00~05:00, 설정온도: 15°C)', 
          fontsize=18, pad=20)
plt.ylabel('온도 (°C)', fontsize=14)
plt.xlabel('시간 (HH:MM)', fontsize=14)

# X축 날짜 포맷팅 [7]
date_fmt = mdates.DateFormatter('%H:%M')
plt.gca().xaxis.set_major_formatter(date_fmt)
plt.gca().xaxis.set_major_locator(mdates.MinuteLocator(interval=10)) # 10분 간격 눈금

plt.grid(True, which='major', linestyle='-', alpha=0.6)
plt.grid(True, which='minor', linestyle=':', alpha=0.3)
plt.legend(loc='center right', fontsize=12, frameon=True, shadow=True)
plt.xticks(rotation=45) # X축 라벨 회전

# 6. 출력
plt.tight_layout()
plt.show()