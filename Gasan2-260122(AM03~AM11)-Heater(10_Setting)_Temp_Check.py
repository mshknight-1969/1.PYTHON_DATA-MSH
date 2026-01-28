import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import platform
from datetime import datetime
import matplotlib.font_manager as fm

# ---------------------------------------------------------
# [설정] 시스템 폰트 자동 설정
# ---------------------------------------------------------
def configure_font():
    system_os = platform.system()
    if system_os == 'Windows':
        font_name = 'Malgun Gothic'
    elif system_os == 'Darwin': # Mac
        font_name = 'AppleGothic'
    else: # Linux
        font_name = 'NanumGothic'
    
    plt.rcParams['font.family'] = font_name
    plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지
    return font_name

# ---------------------------------------------------------
# [데이터 처리] CSV 로드 및 전처리 클래스
# ---------------------------------------------------------
class DataLoader:
    def __init__(self, filepath):
        self.filepath = filepath
        self.df = None
        self.date_col = None
        self.data_cols = []
    
    def load(self):
        encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']
        for enc in encodings:
            try:
                print(f"Trying encoding: {enc}...")
                self.df = pd.read_csv(self.filepath, encoding=enc)
                print("File loaded successfully.")
                break
            except Exception:
                continue
        
        if self.df is None:
            raise ValueError("파일을 읽을 수 없습니다. 지원되지 않는 인코딩입니다.")

        # 컬럼 공백 제거 (헤더 정리)
        self.df.columns = [c.strip().replace('\n', ' ') for c in self.df.columns]
        
        self._detect_columns()
        self._parse_dates()
        return self.df, self.date_col, self.data_cols

    def _detect_columns(self):
        # 날짜 컬럼 감지
        candidates = ['날짜', '시간', 'date', 'time', '일시']
        found = False
        for col in self.df.columns:
            if any(cand in col.lower() for cand in candidates):
                self.date_col = col
                found = True
                break
        
        # 날짜 컬럼을 못 찾으면 두 번째 컬럼을 날짜로 간주 (첫번째는 보통 Index)
        if not found and len(self.df.columns) > 1:
            self.date_col = self.df.columns[1]

        # 데이터 컬럼 감지 (인덱스 성격 제외)
        exclude_keywords = ['no', 'id', 'index', '순번', self.date_col]
        self.data_cols = [
            c for c in self.df.columns 
            if not any(k in c.lower() for k in exclude_keywords)
        ]

    def _parse_dates(self):
        # 날짜 파싱 (MM-DD HH:MM 포맷 대응 및 현재 연도 부여)
        def custom_date_parser(date_str):
            try:
                # 이미 연도가 포함된 경우 (YYYY-MM-DD...)
                return pd.to_datetime(date_str)
            except:
                pass
            
            try:
                # MM-DD HH:MM 형식 처리
                current_year = datetime.now().year
                # 구분자 처리 (- 또는 /)
                date_str = date_str.replace('/', '-')
                full_str = f"{current_year}-{date_str}"
                return datetime.strptime(full_str, "%Y-%m-%d %H:%M")
            except Exception as e:
                # 파싱 실패 시 원본 유지 (나중에 에러 날 수 있음)
                return pd.NaT

        # 벡터화된 변환 대신 안전하게 apply 사용
        self.df[self.date_col] = self.df[self.date_col].astype(str).apply(custom_date_parser)
        
        # NaT(변환 실패) 제거
        self.df = self.df.dropna(subset=[self.date_col])
        
        # 날짜순 정렬 (searchsorted를 위해 필수)
        self.df = self.df.sort_values(by=self.date_col).reset_index(drop=True)

# ---------------------------------------------------------
# [시각화] 인터랙티브 그래프 클래스
# ---------------------------------------------------------
class InteractivePlotter:
    def __init__(self, df, date_col, data_cols):
        self.df = df
        self.date_col = date_col
        self.data_cols = data_cols
        
        # Matplotlib 날짜(float)로 미리 변환 (성능 최적화)
        self.dates_num = mdates.date2num(self.df[self.date_col])
        
        # Figure 설정
        self.fig, self.ax = plt.subplots(figsize=(12, 7))
        self.lines = {}
        self.dots = [] # 데이터 포인트 마커
        self.annotations = [] # 텍스트 라벨
        self.v_line = None # 수직선

        # 설정값
        self.label_box_height_px = 40 # 라벨끼리의 최소 간격 (픽셀 단위)
        
        self.setup_plot()
        self.create_interactive_elements()
        
        # 이벤트 연결
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

    def setup_plot(self):
        # 그래프 그리기
        colors = plt.cm.tab10(np.linspace(0, 1, len(self.data_cols)))
        
        for idx, col in enumerate(self.data_cols):
            # Line Plot
            line, = self.ax.plot(self.df[self.date_col], self.df[col], 
                               label=col, linewidth=1.5, color=colors[idx])
            self.lines[col] = line
            
            # Fill Between (가독성 향상)
            self.ax.fill_between(self.df[self.date_col], self.df[col], 
                               alpha=0.1, color=colors[idx])

        # 축 설정
        self.ax.set_title(f"Temperature Monitoring ({self.df[self.date_col].iloc[0].strftime('%Y-%m-%d')})", fontsize=14, pad=15)
        self.ax.set_ylabel("Temperature (°C)")
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=True)

        # X축 날짜 포맷
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(self.ax.get_xticklabels(), rotation=0, ha='center')
        
        plt.tight_layout()

    def create_interactive_elements(self):
        # 1. 수직선 (초기엔 숨김)
        self.v_line = self.ax.axvline(x=self.dates_num[0], color='gray', linestyle='--', alpha=0.8)
        self.v_line.set_visible(False)

        # 2. 마커와 어노테이션 생성 (초기엔 숨김)
        # 매번 객체를 생성/삭제하면 느리므로, 미리 생성해두고 위치만 업데이트
        for col in self.data_cols:
            # 점 (Dot)
            line = self.lines[col]
            color = line.get_color()
            dot, = self.ax.plot([], [], 'o', color=color, markersize=6, zorder=5)
            dot.set_visible(False)
            self.dots.append(dot)
            
            # 라벨 (Annotation)
            # bbox 스타일: 둥근 모서리, 반투명 흰색 배경
            bbox_props = dict(boxstyle="round,pad=0.4", fc="white", ec=color, alpha=0.9, lw=1.5)
            ann = self.ax.annotate(
                "", 
                xy=(0, 0), 
                xytext=(10, 0), 
                textcoords="offset points",
                bbox=bbox_props,
                fontsize=9,
                fontweight='bold',
                color='black'
            )
            ann.set_visible(False)
            self.annotations.append(ann)

    def on_mouse_move(self, event):
        if not event.inaxes:
            # 마우스가 그래프 밖으로 나가면 요소 숨기기
            self.v_line.set_visible(False)
            for dot, ann in zip(self.dots, self.annotations):
                dot.set_visible(False)
                ann.set_visible(False)
            self.fig.canvas.draw_idle()
            return

        # 1. 가장 가까운 시간 인덱스 찾기 (SearchSorted 이용 - 매우 빠름)
        x_mouse = event.xdata
        idx = np.searchsorted(self.dates_num, x_mouse)
        
        # 인덱스 범위 보정
        if idx >= len(self.dates_num):
            idx = len(self.dates_num) - 1
        
        # 앞/뒤 인덱스 중 더 가까운 쪽 선택
        if idx > 0:
            prev_dist = abs(x_mouse - self.dates_num[idx-1])
            curr_dist = abs(x_mouse - self.dates_num[idx])
            if prev_dist < curr_dist:
                idx = idx - 1

        curr_date_num = self.dates_num[idx]
        
        # 2. 수직선 업데이트 (마우스 위치가 아닌, 스냅된 데이터 시간 위치로)
        self.v_line.set_xdata([curr_date_num])
        self.v_line.set_visible(True)

        # 3. 데이터 수집 및 픽셀 좌표 변환
        # 화면상의 픽셀 좌표를 구해야 겹침 방지를 할 수 있음
        points_info = []
        trans = self.ax.transData
        
        for i, col in enumerate(self.data_cols):
            val = self.df[col].iloc[idx]
            
            # 데이터 좌표 -> 픽셀 좌표 변환
            # (x, y) data coordinates to (x, y) display coordinates
            try:
                pixel_x, pixel_y = trans.transform((curr_date_num, val))
            except ValueError:
                # NaN 값 등 예외 처리
                pixel_x, pixel_y = 0, 0
                val = 0

            points_info.append({
                'index': i,
                'col_name': col,
                'value': val,
                'data_x': curr_date_num,
                'data_y': val,
                'pixel_y': pixel_y
            })

        # 4. [핵심] 픽셀 기반 겹침 방지 알고리즘 (Relaxation)
        # Y축 픽셀 기준으로 정렬
        points_info.sort(key=lambda x: x['pixel_y'])

        # 반복적으로 위치 조정 (Relaxation loop)
        # 라벨들이 너무 붙어있으면 위아래로 조금씩 밀어냄
        iterations = 5
        min_dist = self.label_box_height_px

        # 조정된 Y 픽셀 위치를 저장할 변수 초기화
        for p in points_info:
            p['adjusted_pixel_y'] = p['pixel_y']

        for _ in range(iterations):
            for i in range(len(points_info) - 1):
                p1 = points_info[i]
                p2 = points_info[i+1]
                
                dist = p2['adjusted_pixel_y'] - p1['adjusted_pixel_y']
                
                if dist < min_dist:
                    # 겹침 발생! 중심에서 서로 밀어냄
                    overlap = min_dist - dist
                    move = overlap / 2
                    p1['adjusted_pixel_y'] -= move
                    p2['adjusted_pixel_y'] += move

        # 5. UI 업데이트 (위치 결정 및 그리기)
        # 마우스가 화면 오른쪽 40% 영역에 있는지 확인
        axis_width = self.ax.bbox.width
        mouse_pixel_x = event.x
        is_right_side = mouse_pixel_x > (self.ax.bbox.x0 + axis_width * 0.6)
        
        x_offset = -20 if is_right_side else 20
        ha_align = 'right' if is_right_side else 'left'

        for p in points_info:
            original_idx = p['index']
            dot = self.dots[original_idx]
            ann = self.annotations[original_idx]

            # 점 위치 업데이트 (스냅된 데이터 위치)
            dot.set_data([p['data_x']], [p['data_y']])
            dot.set_visible(True)

            # 라벨 텍스트 업데이트 (센서명 + 값)
            label_text = f"[{p['col_name']}]\n{p['value']:.1f}°C"
            ann.set_text(label_text)
            
            # 라벨 위치 업데이트
            # xy는 데이터 포인트, xytext는 겹침 방지된 픽셀 오프셋 적용
            # 픽셀 좌표계에서의 차이를 offset point로 변환하여 적용
            
            pixel_diff_y = p['adjusted_pixel_y'] - p['pixel_y']
            
            ann.xy = (p['data_x'], p['data_y'])
            ann.set_position((x_offset, pixel_diff_y)) # (x offset, y offset from data point)
            ann.set_ha(ha_align)
            ann.set_visible(True)

        self.fig.canvas.draw_idle()

# ---------------------------------------------------------
# [메인] 실행 진입점
# ---------------------------------------------------------
def main():
    # Tkinter Root 숨기기
    root = tk.Tk()
    root.withdraw()
    configure_font()

    print("CSV 파일을 선택해주세요...")
    file_path = filedialog.askopenfilename(
        title="온도 데이터 CSV 파일 선택",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not file_path:
        print("파일이 선택되지 않았습니다. 종료합니다.")
        return

    try:
        # 1. 데이터 로드
        loader = DataLoader(file_path)
        df, date_col, data_cols = loader.load()
        
        print(f"로드 완료: {len(df)} 행")
        print(f"기준 날짜 컬럼: {date_col}")
        print(f"데이터 컬럼: {data_cols}")

        # 2. 플로터 실행
        plotter = InteractivePlotter(df, date_col, data_cols)
        plt.show()

    except Exception as e:
        messagebox.showerror("Error", f"오류가 발생했습니다:\n{str(e)}")
        print(f"Error detail: {e}")

if __name__ == "__main__":
    main()