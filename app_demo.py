import streamlit as st
import numpy as np
import time
import pandas as pd

# Import Logic หลักจากไฟล์ bingo_core.py
from bingo_core import BingoCardGenerator, BingoGameEngine, BingoMode, BingoValidator

# ==========================================
# 1. Config & Setup
# ==========================================
st.set_page_config(
    page_title="Bingo Demonstration (Web)",
    page_icon="🎰",
    layout="wide"
)

# ฝัง CSS เพื่อแต่งหน้าตาตารางบิงโก
st.markdown("""
<style>
    .bingo-card {
        border: 2px solid #333;
        border-radius: 10px;
        padding: 10px;
        background-color: #f0f2f6;
        margin-bottom: 20px;
        text-align: center;
    }
    .bingo-table {
        width: 100%;
        border-collapse: collapse;
        margin: 0 auto;
    }
    .bingo-cell {
        width: 40px;
        height: 40px;
        border: 1px solid #aaa;
        text-align: center;
        vertical-align: middle;
        font-weight: bold;
        font-size: 14px;
        color: #333;
    }
    /* สีสถานะต่างๆ */
    .status-normal { background-color: white; }
    .status-free { background-color: #555; color: white; }
    .status-marked { background-color: #2ecc71; color: white; } /* สีเขียว */
    .status-win { background-color: #f1c40f; color: black; border: 2px solid orange; } /* สีทอง */
    
    .player-name {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 5px;
        color: #0e1117;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Session State Management
# ==========================================
def init_session_state():
    defaults = {
        'cards': None,          # เก็บการ์ดของผู้เล่น
        'marks': None,          # เก็บสถานะการกากบาท
        'draw_seq': [],         # ลำดับเลขที่จะสุ่ม
        'current_idx': 0,       # รอบปัจจุบัน
        'last_num': "-",        # เลขล่าสุด
        'game_over': False,     # จบเกมหรือยัง
        'winner_msg': "",       # ข้อความผู้ชนะ
        'win_highlights': None, # ไฮไลท์แถวที่ชนะ
        'auto_running': False   # <--- ตัวแปรสำคัญสำหรับระบบ Auto
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# ==========================================
# 3. Helper Functions (Logic)
# ==========================================
def start_new_game(n, y, players, mode):
    try:
        # Validate Inputs
        final_mode, warnings = BingoValidator.validate(n, y, players, mode)
        if warnings:
            st.toast(warnings[0], icon="⚠️")

        # Generate Logic
        st.session_state.cards = BingoCardGenerator.generate_cards(n, y, players, final_mode)
        st.session_state.marks = (st.session_state.cards == 0) # Free space is marked
        st.session_state.draw_seq = np.random.permutation(np.arange(1, y + 1))
        
        # Reset State
        st.session_state.current_idx = 0
        st.session_state.last_num = "-"
        st.session_state.game_over = False
        st.session_state.winner_msg = ""
        st.session_state.win_highlights = np.zeros_like(st.session_state.marks, dtype=bool)
        st.session_state.auto_running = False # รีเซ็ต Auto เมื่อเริ่มเกมใหม่
        
    except ValueError as e:
        st.error(f"Error: {e}")

def check_winners(n, players):
    """เช็คผู้ชนะและระบายสีทอง"""
    has_winner = False
    st.session_state.win_highlights[:] = False 
    marks = st.session_state.marks
    
    for p in range(players):
        p_marks = marks[p]
        is_p_winner = False
        
        # 1. Rows
        for r in range(n):
            if np.all(p_marks[r, :]):
                is_p_winner = True
                st.session_state.win_highlights[p, r, :] = True
                
        # 2. Cols
        for c in range(n):
            if np.all(p_marks[:, c]):
                is_p_winner = True
                st.session_state.win_highlights[p, :, c] = True
                
        # 3. Diagonals
        if np.all(np.diag(p_marks)):
            is_p_winner = True
            rows, cols = np.diag_indices(n)
            st.session_state.win_highlights[p, rows, cols] = True
            
        if np.all(np.diag(np.fliplr(p_marks))):
            is_p_winner = True
            rows, cols = np.diag_indices(n)
            st.session_state.win_highlights[p, rows, n - 1 - cols] = True

        if is_p_winner:
            has_winner = True

    return has_winner

def next_turn(n, y, players):
    """ฟังก์ชันเดินเกม 1 ตา"""
    if st.session_state.current_idx >= len(st.session_state.draw_seq):
        st.session_state.game_over = True
        st.session_state.winner_msg = "จบเกม! (เลขหมดกอง)"
        st.session_state.auto_running = False # หยุด Auto
        return

    # 1. หยิบเลข
    number = st.session_state.draw_seq[st.session_state.current_idx]
    st.session_state.current_idx += 1
    st.session_state.last_num = number
    
    # 2. Update Marks
    matches = (st.session_state.cards == number)
    st.session_state.marks |= matches
    
    # 3. Check Win
    if check_winners(n, players):
        st.session_state.game_over = True
        st.session_state.winner_msg = f"🎉 BINGO! จบเกมในรอบที่ {st.session_state.current_idx}"
        st.session_state.auto_running = False # หยุด Auto
        st.balloons()

# ==========================================
# 4. UI Rendering
# ==========================================
def render_bingo_card(player_idx, n):
    """สร้าง HTML Table สำหรับการ์ด 1 ใบ"""
    card = st.session_state.cards[player_idx]
    marks = st.session_state.marks[player_idx]
    highlights = st.session_state.win_highlights[player_idx]
    
    html = f"<div class='bingo-card'><div class='player-name'>ผู้เล่น {player_idx + 1}</div>"
    html += "<table class='bingo-table'>"
    
    for r in range(n):
        html += "<tr>"
        for c in range(n):
            val = card[r, c]
            
            if highlights[r, c]: css_class = "status-win"
            elif val == 0: css_class = "status-free"
            elif marks[r, c]: css_class = "status-marked"
            else: css_class = "status-normal"
                
            txt = "FREE" if val == 0 else str(val)
            html += f"<td class='bingo-cell {css_class}'>{txt}</td>"
        html += "</tr>"
    html += "</table></div>"
    return html

# ==========================================
# 5. Main App Layout
# ==========================================
def main():
    # --- Sidebar: Controls ---
    with st.sidebar:
        st.header("⚙️ ตั้งค่าเกมสาธิต")
        
        n = st.number_input("ขนาดตาราง (n)", min_value=3, max_value=7, value=5)
        y = st.number_input("จำนวนเลข (y)", min_value=10, max_value=100, value=75)
        players = st.number_input("จำนวนผู้เล่น", min_value=1, max_value=50, value=6)
        
        mode_label = st.radio("โหมด:", ["Pure Math", "Free Space"])
        mode = BingoMode.PURE_MATH if mode_label == "Pure Math" else BingoMode.FREE_SPACE
        
        st.divider()
        col_layout = st.slider("จัดเรียงกระดาน (คอลัมน์)", 1, 6, 3)
        
        st.divider()
        speed = st.slider("ความเร็ว Auto (วินาที/รอบ)", 0.1, 2.0, 0.5, step=0.1)
        
        st.divider()
        if st.button("🔄 เริ่มเกมใหม่ (Restart)", type="primary", use_container_width=True):
            start_new_game(n, y, players, mode)
            st.rerun()

    # --- Main Area ---
    st.title("🎲 Bingo Live Demo")
    
    # Status Bar
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.metric("รอบที่ (Turn)", f"{st.session_state.current_idx} / {y}")
    with col2:
        st.markdown(f"<h1 style='text-align: center; color: #ff4b4b; font-size: 50px; margin:0;'>{st.session_state.last_num}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>เลขที่ออกล่าสุด</p>", unsafe_allow_html=True)
    with col3:
        if st.session_state.game_over:
            st.success(st.session_state.winner_msg)
        else:
            status_text = "🟢 กำลังเล่นอัตโนมัติ..." if st.session_state.auto_running else "🟡 รอคำสั่ง..."
            st.info(f"สถานะ: {status_text}")

    # Buttons (Next / Auto)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶️ สุ่มเลขถัดไป (Next)", use_container_width=True, 
                     disabled=st.session_state.cards is None or st.session_state.game_over or st.session_state.auto_running):
            next_turn(n, y, players)
            st.rerun()
            
    with c2:
        # ปุ่ม Auto ทำหน้าที่เป็น Toggle (สวิตช์เปิด-ปิด)
        auto_label = "⏹️ หยุด (Stop)" if st.session_state.auto_running else "⏩ เล่นอัตโนมัติ (Auto Run)"
        if st.button(auto_label, use_container_width=True, 
                     disabled=st.session_state.cards is None or st.session_state.game_over):
            # สลับค่า True <-> False
            st.session_state.auto_running = not st.session_state.auto_running
            st.rerun()

    # --- Logic สำหรับ Auto Run (ทำงานภายนอกปุ่ม) ---
    if st.session_state.auto_running and not st.session_state.game_over:
        time.sleep(speed)  # หน่วงเวลาตามที่ตั้งค่า
        next_turn(n, y, players)
        st.rerun()         # สั่งรีโหลดหน้าใหม่ (Loop กลับไปเริ่ม Main)

    st.divider()

    # --- Game Board Area ---
    if st.session_state.cards is not None:
        rows = (players // col_layout) + (1 if players % col_layout > 0 else 0)
        p_idx = 0
        for _ in range(rows):
            cols = st.columns(col_layout)
            for c in range(col_layout):
                if p_idx < players:
                    with cols[c]:
                        html_card = render_bingo_card(p_idx, n)
                        st.markdown(html_card, unsafe_allow_html=True)
                    p_idx += 1
    else:
        st.warning("👈 กรุณากดปุ่ม 'เริ่มเกมใหม่' เพื่อเริ่มต้น")

if __name__ == "__main__":
    main()
