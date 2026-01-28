import sys
import os
import platform
import csv
import traceback
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import math

# [안정성] 그래픽 백엔드를 TkAgg로 강제
import matplotlib
try:
    matplotlib.use('TkAgg')
except:
    pass

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np 
except ImportError as e:
    print("\n[치명적 오류] 필수 라이브러리(matplotlib, numpy)가 없습니다.")
    sys.exit(1)

def select_file_gui():
    try:
        root = tk.Tk()
        root.withdraw() 
        root.attributes('-topmost', True) 
        file_path = filedialog.askopenfilename(
            title="CSV 파일 선택",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        root.destroy()
        return file_path
    except: return None

def read_csv_data_robust(filename):
    """CSV 데이터 로드"""
    times = []
    data_series = {}
    
    if not filename: filename = '온도데이타-1.csv'
    if not os.path.exists(filename):
        print(f"[오류] 파일 없음: {filename}")
        return None, None

    encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']
    file_content = None

    for enc in encodings:
        try:
            with open(filename, mode='r', encoding=enc) as f:
                file_content = list(csv.reader(f))
            break
        except: continue

    if not file_content: return None, None

    try:
        headers = file_content[0]
        labels = [h.replace('\n', ' ').strip() for h in headers[1:]]
        
        for label in labels: data_series[label] = []
        curr_year = datetime.now().year
        
        for row in file_content[1:]:
            if not row or len(row) < len(headers): continue
            date_str = row[0].strip()
            if not date_str: continue
            
            try:
                dt = datetime.strptime(date_str, "%m-%d %H:%M")
                dt = dt.replace(year=curr_year)
                times.append(dt)
            except: continue
            
            for i, label in enumerate(labels):
                try:
                    val_str = row[i+1].strip()
                    val = float(val_str) if val_str else np.nan
                except: val = np.nan
                data_series[label].append(val)
                
        return times, data_series
    except:
        traceback.print_exc()
        return None, None

def plot_temperature_data():
    filename = select_file_gui()
    if not filename: filename = '온도데이타-1.csv'
    
    time_objs, data_series = read_csv_data_robust(filename)
    if not time_objs or not data_series: return

    try:
        x_nums = mdates.date2num(time_objs)
    except Exception as e:
        print(f"[오류] 날짜 변환 실패: {e}")
        return

    system_name = platform.system()
    if system_name == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif system_name == 'Darwin':
        plt.rc('font', family='AppleGothic')
    else:
        plt.rc('font', family='NanumGothic')
    plt.rcParams['axes.unicode_minus'] = False

    try:
        fig, ax = plt.subplots(figsize=(14, 8))
        lines = []
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']

        for i, (label, temps) in enumerate(data_series.items()):
            min_len = min(len(temps), len(x_nums))
            x_vals = x_nums[:min_len]
            y_vals = temps[:min_len]
            
            color = colors[i % len(colors)]
            line, = ax.plot(x_vals, y_vals, color=color, lw=1.5, marker='o', ms=3, label=label, zorder=2)
            lines.append(line)
            try:
                y_arr = np.array(y_vals, dtype=float)
                ax.fill_between(x_vals, y_vals, color=color, alpha=0.05, where=~np.isnan(y_arr), zorder=1)
            except: pass

        ax.set_title(f'반응형 정밀 분석: {os.path.basename(filename)}', fontsize=16, pad=20)
        ax.legend(loc='upper left', framealpha=0.9, shadow=True)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.grid(True, which='major', alpha=0.3, linestyle='--')
        plt.xticks(rotation=45)

        # ---------------------------------------------------------
        # 인터랙티브 객체 초기화
        # ---------------------------------------------------------
        
        cursor_line, = ax.plot([], [], '--', color='gray', alpha=0.8, lw=1.5, zorder=5)
        
        highlight_dots = []
        for line in lines:
            dot, = ax.plot([], [], 'o', ms=8, mec=line.get_color(), mfc='white', mew=2, visible=False, zorder=6)
            highlight_dots.append(dot)

        annots = []
        for i, line in enumerate(lines):
            annot = ax.annotate(
                text="", 
                xy=(x_nums[0], 0), 
                xytext=(80, 0), # 초기값 (나중에 동적으로 바뀜)
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=line.get_color(), alpha=0.9, lw=1.5),
                arrowprops=dict(
                    arrowstyle="->", 
                    color=line.get_color(), 
                    connectionstyle="arc3,rad=0.1", 
                    lw=1.5
                ),
                fontsize=9, color='black', fontweight='bold',
                zorder=200, clip_on=False
            )
            annot.set_visible(False)
            annots.append(annot)

        if lines:
            x_data_ref = lines[0].get_xdata()
        else:
            x_data_ref = []

        def on_hover(event):
            if event.inaxes != ax:
                cursor_line.set_visible(False)
                for dot in highlight_dots: dot.set_visible(False)
                for annot in annots: annot.set_visible(False)
                fig.canvas.draw_idle()
                return

            mouse_x = event.xdata
            if mouse_x is None or len(x_data_ref) == 0: return

            try:
                # 1. 화면의 좌우 영역 판단 (가장자리 잘림 방지)
                xlim = ax.get_xlim()
                x_range = xlim[1] - xlim[0]
                
                # 마우스의 상대 위치 (0.0 ~ 1.0)
                rel_x = (mouse_x - xlim[0]) / x_range if x_range > 0 else 0.5
                
                # [핵심] 오른쪽 60% 지점을 넘어가면 라벨을 왼쪽으로 보냄
                is_right_side = rel_x > 0.6
                
                # 방향에 따른 설정값
                # 오른쪽 끝에 있으면 -> 왼쪽으로 표시 (-80)
                # 왼쪽/중간에 있으면 -> 오른쪽으로 표시 (+80)
                base_x_offset = -90 if is_right_side else 90
                # 화살표 곡률도 반대로 뒤집어야 자연스러움
                arc_rad = -0.2 if is_right_side else 0.2
                
                # 2. 회색선 업데이트
                ylim = ax.get_ylim()
                cursor_line.set_data([mouse_x, mouse_x], [ylim[0], ylim[1]])
                cursor_line.set_visible(True)

                # 3. 데이터 스냅
                idx = np.searchsorted(x_data_ref, mouse_x)
                if idx >= len(x_data_ref): idx = len(x_data_ref) - 1
                if idx > 0:
                    if abs(x_data_ref[idx-1] - mouse_x) < abs(x_data_ref[idx] - mouse_x):
                        idx = idx - 1
                
                current_time_val = x_data_ref[idx]
                
                # 4. 라벨 위치 계산 및 업데이트
                active_labels = []
                
                for line, dot, annot in zip(lines, highlight_dots, annots):
                    y_data = line.get_ydata()
                    if idx < len(y_data):
                        val = y_data[idx]
                        if val is not None and np.isfinite(val):
                            active_labels.append({
                                'val': val,
                                'line': line,
                                'dot': dot,
                                'annot': annot
                            })
                        else:
                            dot.set_visible(False)
                            annot.set_visible(False)
                    else:
                        dot.set_visible(False)
                        annot.set_visible(False)
                
                # 높은 값부터 정렬
                active_labels.sort(key=lambda x: x['val'], reverse=True)
                
                count = len(active_labels)
                if count > 0:
                    spacing = 40 
                    start_offset = (count - 1) * spacing / 2
                    
                    for i, item in enumerate(active_labels):
                        val = item['val']
                        annot = item['annot']
                        dot = item['dot']
                        line = item['line']
                        
                        dot.set_data([current_time_val], [val])
                        dot.set_visible(True)
                        
                        dt_val = mdates.num2date(current_time_val)
                        time_str = dt_val.strftime('%H:%M')
                        label = line.get_label()
                        annot.set_text(f"{label}\n{val:.1f}°C")
                        
                        annot.xy = (current_time_val, val)
                        
                        # [핵심] Y축 분산(Spreading) + X축 방향 전환(Flipping)
                        y_offset = start_offset - (i * spacing)
                        
                        # 계산된 X방향(base_x_offset)을 적용
                        annot.set_position((base_x_offset, y_offset))
                        
                        # 화살표 스타일 동적 업데이트 (방향에 따라 곡률 반전)
                        annot.arrow_patch.set_connectionstyle(f"arc3,rad={arc_rad}")
                        
                        annot.set_visible(True)

                fig.canvas.draw_idle()
                
            except Exception as e:
                print(f"[렌더링 경고] {e}")

        fig.canvas.mpl_connect("motion_notify_event", on_hover)
        
        plt.tight_layout()
        print("[실행 완료] 가장자리 잘림 방지 기능이 적용되었습니다.")
        plt.show()

    except Exception:
        print("\n[오류] 그래프 초기화 실패")
        traceback.print_exc()

if __name__ == "__main__":
    plot_temperature_data()
    if platform.system() == 'Windows':
        input("\n종료하려면 엔터 키를 누르세요...")