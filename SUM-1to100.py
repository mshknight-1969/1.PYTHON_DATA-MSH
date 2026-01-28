import matplotlib.pyplot as plt
import numpy as np

def plot_cumulative_sum():
    # 1. 데이터 생성
    # 1부터 100까지의 배열 생성
    n = np.arange(1, 101)
    # 누적 합 계산 (Cumulative Sum)
    # loop를 돌며 더하는 것보다 numpy의 벡터 연산이 압도적으로 빠르고 효율적입니다.
    cumulative_sum = np.cumsum(n)

    # 2. 그래프 그리기
    plt.figure(figsize=(10, 6))
    plt.plot(n, cumulative_sum, label='Cumulative Sum ($S_n$)', color='blue', linewidth=2)

    # 3. 주요 지점 강조 (중간값 50과 최종값 100)
    # 시각화의 목적은 데이터의 특징을 빠르게 파악하는 것입니다.
    # 주요 변곡점이나 끝값을 명시하는 것이 좋습니다.
    points = [50, 100]
    for p in points:
        value = cumulative_sum[p-1]
        plt.scatter(p, value, color='red', zorder=5) # 점 찍기
        plt.annotate(f'n={p}\nSum={value}', 
                     (p, value), 
                     xytext=(p-15, value+500),
                     arrowprops=dict(facecolor='black', arrowstyle='->'))

    # 4. 레이블 및 설정
    plt.title('Cumulative Sum Progression (1 to 100)')
    plt.xlabel('Integer (n)')
    plt.ylabel('Total Sum ($S_n$)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    
    # 그래프 표시 (로컬 환경에서는 plt.show() 사용)
    plt.show()
    print("Graph generated successfully.")

if __name__ == "__main__":
    plot_cumulative_sum()