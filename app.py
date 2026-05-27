import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import platform
from bingo_core import BingoValidator, BingoCardGenerator, BingoGameEngine, BingoMode

# ==========================================
# ตั้งค่าเบื้องต้นของหน้าเว็บ (Page Config)
# ==========================================
st.set_page_config(
    page_title="BWN Bingo Research Simulation",
    page_icon="🎲",
    layout="wide"
)

# ==========================================
# คลาสหลักสำหรับ Web Application
# ==========================================
class BingoWebApp:
    def __init__(self):
        self.setup_session_state()
        self.setup_fonts()

    def setup_session_state(self):
        """กำหนดค่าตัวแปรที่จะจำค่าไว้ระหว่างการกดปุ่ม (State Management)"""
        if 'results_data' not in st.session_state:
            st.session_state.results_data = [] # เก็บข้อมูลผลลัพธ์ทั้งหมด

    def setup_fonts(self):
        """ตั้งค่าฟอนต์สำหรับกราฟให้รองรับภาษาไทยหรือฟอนต์มาตรฐาน"""
        system = platform.system()
        if system == "Windows":
            plt.rcParams['font.family'] = 'Tahoma'
        elif system == "Darwin": # Mac
            plt.rcParams['font.family'] = 'Ayuthaya'
        else:
            # สำหรับ Linux/Cloud Server (Streamlit Cloud)
            # มักไม่มีฟอนต์ไทย ให้ใช้ sans-serif มาตรฐานเพื่อไม่ให้ error
            plt.rcParams['font.family'] = 'sans-serif'

    def render_sidebar(self):
        """สร้างส่วนควบคุมด้านซ้าย (Sidebar)"""
        st.sidebar.header("⚙️ ตั้งค่าตัวแปรวิจัย")

        # --- Input: n (Grid Size) ---
        st.sidebar.subheader("1. ขนาดตาราง (n)")
        n_mode = st.sidebar.radio("รูปแบบ n:", ["ค่าเดียว", "ช่วง (Range)"], horizontal=True, key="n_mode")
        if n_mode == "ค่าเดียว":
            n_vals = [st.sidebar.number_input("ค่า n:", min_value=3, value=5, step=1)]
        else:
            c1, c2, c3 = st.sidebar.columns(3)
            start = c1.number_input("เริ่ม n:", min_value=3, value=3)
            end = c2.number_input("ถึง n:", min_value=3, value=7)
            step = c3.number_input("เพิ่มทีละ:", min_value=1, value=1)
            n_vals = list(range(start, end + 1, step))

        # --- Input: y (Max Number) ---
        st.sidebar.subheader("2. จำนวนตัวเลข (y)")
        y_mode = st.sidebar.radio("รูปแบบ y:", ["ค่าเดียว", "ช่วง (Range)"], horizontal=True, key="y_mode")
        if y_mode == "ค่าเดียว":
            y_vals = [st.sidebar.number_input("ค่า y:", min_value=10, value=75, step=5)]
        else:
            c1, c2, c3 = st.sidebar.columns(3)
            start = c1.number_input("เริ่ม y:", min_value=10, value=50)
            end = c2.number_input("ถึง y:", min_value=10, value=100)
            step = c3.number_input("เพิ่มทีละ:", min_value=1, value=25)
            y_vals = list(range(start, end + 1, step))

        # --- Input: Players (x) ---
        st.sidebar.subheader("3. จำนวนผู้เล่น (x)")
        x_mode = st.sidebar.radio("รูปแบบผู้เล่น:", ["ค่าเดียว", "ช่วง (Range)"], horizontal=True, key="x_mode")
        if x_mode == "ค่าเดียว":
            x_vals = [st.sidebar.number_input("จำนวนคน:", min_value=1, value=10, step=10)]
        else:
            c1, c2, c3 = st.sidebar.columns(3)
            start = c1.number_input("เริ่มคน:", min_value=1, value=10)
            end = c2.number_input("ถึงคน:", min_value=1, value=100)
            step = c3.number_input("เพิ่มทีละ:", min_value=1, value=10)
            x_vals = list(range(start, end + 1, step))

        # --- Other Settings ---
        st.sidebar.markdown("---")
        trials = st.sidebar.number_input("จำนวนรอบทดลอง (Trials):", min_value=10, value=1000, step=100)
        
        mode_label = st.sidebar.radio("โหมดกติกา:", ["Pure Math (เต็มตาราง)", "Free Space (มีช่องฟรี)"])
        mode_key = BingoMode.PURE_MATH if "Pure" in mode_label else BingoMode.FREE_SPACE
        
        append_data = st.sidebar.checkbox("สะสมข้อมูลต่อเนื่อง (ไม่ล้างค่าเดิม)", value=False)

        # --- Return configurations as a dictionary ---
        return {
            "n_vals": n_vals,
            "y_vals": y_vals,
            "x_vals": x_vals,
            "trials": trials,
            "mode": mode_key,
            "append_data": append_data
        }

    def run_simulation(self, config):
        """ฟังก์ชันหลักสำหรับรัน Simulation"""
        
        # เตรียม Progress Bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # คำนวณจำนวนรอบรวมทั้งหมดเพื่อทำ Progress Bar
        total_iterations = len(config['n_vals']) * len(config['y_vals']) * len(config['x_vals'])
        current_iter = 0

        # ถ้าไม่สะสมข้อมูล ให้เคลียร์ของเดิม
        if not config['append_data']:
            st.session_state.results_data = []

        # ลูปใหญ่ควบคุมโครงสร้างการรันจำลอง
        try:
            for n in config['n_vals']:
                for y in config['y_vals']:
                    try:
                        # --- ตรวจสอบความถูกต้อง (Validation) รายคู่ตัวแปร ---
                        final_mode, warnings = BingoValidator.validate(n, y, max(config['x_vals']), config['mode'])
                        
                        if warnings:
                            st.warning(f"⚠️ คำเตือนที่ n={n}, y={y}: {warnings[0]}")
                        
                        # ตัวแปรสำหรับเก็บผลลัพธ์ย่อยเพื่อนำไปพลอตกราฟ
                        batch_means = []
                        batch_x = []
                        last_hist_data = []

                        for x in config['x_vals']:
                            # อัปเดตสถานะหน้าจอ
                            status_text.text(f"กำลังจำลอง... n={n}, y={y}, ผู้เล่น={x} ({current_iter + 1}/{total_iterations})")
                            
                            # --- Core Simulation Loop ---
                            turns_in_this_group = []
                            for _ in range(config['trials']):
                                cards = BingoCardGenerator.generate_cards(n, y, x, final_mode)
                                turns = BingoGameEngine.play_one_game(cards, y)
                                turns_in_this_group.append(turns)
                            # ----------------------------

                            # คำนวณสถิติ
                            mean_val = np.mean(turns_in_this_group)
                            sd_val = np.std(turns_in_this_group)
                            
                            # บันทึกลง Session State
                            st.session_state.results_data.append({
                                "n": n, "y": y, "Players": x, "Trials": config['trials'],
                                "Mean": round(mean_val, 4), "S.D.": round(sd_val, 4),
                                "Min": int(np.min(turns_in_this_group)), 
                                "Max": int(np.max(turns_in_this_group))
                            })

                            # เก็บข้อมูลสำหรับกราฟ
                            batch_means.append(mean_val)
                            batch_x.append(x)
                            last_hist_data = turns_in_this_group
                            
                            current_iter += 1
                            progress_bar.progress(min(current_iter / total_iterations, 1.0))

                        # จบลูปย่อย x: แสดงกราฟทันที (Real-time update logic)
                        self.display_charts(batch_x, batch_means, last_hist_data, n, y, config['trials'])

                    except ValueError as e:
                        # [จุดแก้ไขสำคัญ] ดักจับค่าพารามิเตอร์ที่ไม่ผ่านเกณฑ์คณิตศาสตร์
                        st.warning(f"⚠️ ข้ามชุดตัวแปร n={n}, y={y}: {str(e)}")
                        
                        # ชดเชยค่า Iteration ของผู้เล่น (x) ทั้งหมดในรอบนี้ เพื่อให้เข็ม Progress Bar เดินหน้าต่ออย่างถูกต้อง ไม่ค้างคา
                        current_iter += len(config['x_vals'])
                        progress_bar.progress(min(current_iter / total_iterations, 1.0))
                        continue

            status_text.success("✅ การจำลองเสร็จสิ้นเรียบร้อย!")
            
        except Exception as e:
            st.error(f"⛔ เกิดข้อผิดพลาดร้ายแรงในระบบ: {str(e)}")

    def display_charts(self, x_vals, y_means, hist_data, n, y, trials):
        """แสดงกราฟโดยใช้ Matplotlib ผ่าน Streamlit"""
        
        # สร้าง Layout 2 คอลัมน์สำหรับกราฟ
        c1, c2 = st.columns(2)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        
        # กราฟ 1: แนวโน้ม
        if len(x_vals) > 1:
            ax1.plot(x_vals, y_means, marker='o', color='#2c3e50', linestyle='-')
        else:
            ax1.scatter(x_vals, y_means, color='#2c3e50', s=100)
        ax1.set_title(f"Mean Turns vs Players\n(n={n}, y={y})")
        ax1.set_xlabel("Players")
        ax1.set_ylabel("Avg Turns")
        ax1.grid(True, linestyle='--', alpha=0.6)
        
        # กราฟ 2: Histogram (เฉพาะชุดล่าสุด)
        ax2.hist(hist_data, bins=range(min(hist_data), max(hist_data)+2), 
                 color='#e74c3c', edgecolor='black', alpha=0.7)
        ax2.set_title(f"Distribution (Last Run)\n(Players={x_vals[-1]})")
        ax2.set_xlabel("Turns to Win")
        ax2.set_ylabel("Frequency")
        
        plt.tight_layout()
        
        # แสดงผลลงหน้าเว็บ (container ด้านบน)
        with st.container():
            st.pyplot(fig)
            st.caption(f"👆 ผลลัพธ์ล่าสุด: n={n}, y={y}")

    def main(self):
        """ส่วนแสดงผลหลัก (UI Layout)"""
        st.title("🎲 BWN Bingo Research Simulation")
        st.markdown("โปรแกรมจำลองความน่าจะเป็นในเกมบิงโก เพื่อการศึกษาทางสถิติ โดย โรงเรียนบุญวัฒนา")
        
        # 1. รับค่าจาก Sidebar
        config = self.render_sidebar()
        
        # 2. ปุ่ม Run
        if st.sidebar.button("🚀 เริ่มการจำลอง (Start Simulation)", type="primary"):
            self.run_simulation(config)
            
        # 3. แสดงผลลัพธ์ (Tab View)
        st.markdown("---")
        tab1, tab2 = st.tabs(["📊 ตารางข้อมูล (Data Table)", "📈 คำแนะนำการใช้งาน"])
        
        with tab1:
            if st.session_state.results_data:
                df = pd.DataFrame(st.session_state.results_data)
                
                # แสดง Dataframe
                st.dataframe(df, use_container_width=True)
                
                # ปุ่ม Download CSV
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="💾 ดาวน์โหลด CSV",
                    data=csv,
                    file_name='bingo_simulation_results.csv',
                    mime='text/csv',
                )
            else:
                st.info("ยังไม่มีข้อมูล กรุณากดปุ่ม 'เริ่มการจำลอง' ทางด้านซ้าย")
        
        with tab2:
            st.markdown("""
            **วิธีใช้งาน:**
            1. กำหนดค่าตัวแปร **n** (ขนาดตาราง), **y** (จำนวนเลขสูงสุด), **x** (ผู้เล่น) ทางเมนูซ้ายมือ
            2. สามารถเลือกใส่แบบ **ค่าเดียว** หรือ **ช่วง (Range)** เพื่อดูแนวโน้ม
            3. กดปุ่ม **Start Simulation**
            4. ระบบจะคำนวณและแสดงกราฟวิเคราะห์ผลให้ทีละชุดข้อมูล
            5. เมื่อเสร็จสิ้น สามารถดาวน์โหลดผลเป็นไฟล์ CSV ได้ที่แท็บ 'ตารางข้อมูล'
            """)

# ==========================================
# Entry Point
# ==========================================
if __name__ == "__main__":
    app = BingoWebApp()
    app.main()
