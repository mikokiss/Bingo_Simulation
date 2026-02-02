import numpy as np
import math

# ==========================================
# ส่วนที่ 1: การกำหนดค่าคงที่ (Constants)
# ==========================================
class BingoMode:
    PURE_MATH = "pure_math"     # สุ่มเต็มตาราง (ใช้สำหรับ n เลขคู่ หรือต้องการสถิติเพียวๆ)
    FREE_SPACE = "free_space"   # มีช่องฟรีตรงกลาง (สำหรับ n เลขคี่เท่านั้น)

# ==========================================
# ส่วนที่ 2: ด่านตรวจสอบความถูกต้อง (Validator)
# ==========================================
class BingoValidator:
    """
    คลาสสำหรับตรวจสอบค่า Input ก่อนเริ่มการทำงาน
    เพื่อให้มั่นใจว่าโปรแกรมจะไม่พังกลางคัน
    """
    @staticmethod
    def validate(n, y, max_players, mode):
        """
        ตรวจสอบค่า n, y, และจำนวนคน
        Return: (final_mode, warnings_list)
        """
        warnings = []
        final_mode = mode

        # --- Check 1: ตรวจสอบความสมมาตรของตาราง (Even Number) ---
        if n % 2 == 0 and mode == BingoMode.FREE_SPACE:
            final_mode = BingoMode.PURE_MATH
            warnings.append(f"คำเตือน: ตารางขนาด {n}x{n} เป็นเลขคู่ ไม่มีจุดกึ่งกลางกลาง ระบบเปลี่ยนโหมดเป็น 'Pure Math' อัตโนมัติ")

        # --- Check 2: ตรวจสอบจำนวนตัวเลข (y) ว่าพอหรือไม่ ---
        # ถ้า Pure Math ต้องใช้ n*n ตัว
        # ถ้า Free Space ต้องใช้ (n*n) - 1 ตัว
        required_numbers = (n * n) - 1 if final_mode == BingoMode.FREE_SPACE else (n * n)
        
        if y < required_numbers:
            raise ValueError(f"ข้อผิดพลาด: ค่า y ({y}) น้อยเกินไป! สำหรับตาราง {n}x{n} ต้องมีตัวเลขอย่างน้อย {required_numbers} ตัว")

        # --- Check 3: ตรวจสอบขีดจำกัดจำนวนรูปแบบการ์ด (Permutation Limit) ---
        # สูตร P(n, k) = n! / (n-k)!
        # เราใช้ math.perm (มีใน Python 3.8+)
        try:
            max_unique_cards = math.perm(y, required_numbers)
            if max_players > max_unique_cards:
                raise ValueError(f"ข้อผิดพลาด: จำนวนผู้เล่น ({max_players:,}) มากกว่ารูปแบบการ์ดที่เป็นไปได้ทั้งหมด ({max_unique_cards:,} รูปแบบ)")
        except OverflowError:
            # กรณีเลขเยอะจนคำนวณไม่ได้ แปลว่ารองรับได้มหาศาล -> ผ่าน
            pass

        return final_mode, warnings

# ==========================================
# ส่วนที่ 3: โรงงานผลิตการ์ด (Generator)
# ==========================================
class BingoCardGenerator:
    """
    คลาสสำหรับสร้างการ์ดบิงโกแบบไม่ซ้ำกัน (Unique Cards)
    """
    @staticmethod
    def generate_cards(n, y, num_players, mode):
        """
        สร้างการ์ดจำนวน num_players ใบ
        Return: numpy array 3 มิติ (num_players, n, n)
        """
        # Set สำหรับเก็บ "ลายเซ็น" ของการ์ด เพื่อเช็คซ้ำ (ทำงานเร็วมาก)
        generated_signatures = set()
        cards_list = []
        
        required_slots = (n * n)
        center_idx = n // 2

        count = 0
        while count < num_players:
            # 1. สุ่มตัวเลขจาก 1 ถึง y แบบไม่ซ้ำ ตามจำนวนช่องที่ต้องใช้
            # เราสุ่มมาเต็มจำนวนช่องก่อน แล้วค่อยจัดการ Free Space ทีหลัง
            if mode == BingoMode.FREE_SPACE:
                # สุ่มมา n*n - 1 ตัว
                choices = np.random.choice(range(1, y + 1), size=required_slots - 1, replace=False)
                # แทรก 0 (Free Space) ไว้ตรงกลาง
                # สร้าง Grid ชั่วคราว
                grid_flat = np.insert(choices, (n * n) // 2, 0)
                grid = grid_flat.reshape((n, n))
            else:
                # Pure Math: สุ่มเต็ม n*n ตัว
                choices = np.random.choice(range(1, y + 1), size=required_slots, replace=False)
                grid = choices.reshape((n, n))

            # 2. สร้างลายเซ็น (Tuple) เพื่อเช็คใน Set
            # ต้องแปลงเป็น tuple เพราะ list ใส่ใน set ไม่ได้
            signature = tuple(grid.flatten())

            # 3. เช็คว่าซ้ำไหม?
            if signature not in generated_signatures:
                generated_signatures.add(signature)
                cards_list.append(grid)
                count += 1
            # ถ้าซ้ำ (else): ก็แคบวนลูปใหม่ ไม่ต้องทำอะไร

        # แปลง List เป็น Numpy Array 3D เพื่อความเร็วในการคำนวณภายหลัง
        # Shape: (จำนวนคน, แถว, หลัก)
        return np.array(cards_list, dtype=int)

# ==========================================
# ส่วนที่ 4: กรรมการคุมเกม (Game Engine)
# ==========================================
class BingoGameEngine:
    """
    คลาสสำหรับรันเกมและตรวจสอบผลแพ้ชนะ
    """
    @staticmethod
    def play_one_game(cards, y):
        """
        จำลองการเล่น 1 เกม
        cards: numpy array 3D ของผู้เล่นทุกคน
        y: จำนวนตัวเลขสูงสุด
        Return: จำนวนรอบที่ใช้จนกว่าจะมีคนชนะคนแรก (int)
        """
        num_players, n, _ = cards.shape
        
        # 1. สุ่มลำดับตัวเลขที่จะขาน (Permutation)
        draw_sequence = np.random.permutation(np.arange(1, y + 1))
        
        # 2. สร้างตารางเช็คผล (Marks) เริ่มต้นเป็น False ทั้งหมด
        # ถ้าการ์ดช่องไหนเป็น 0 (Free Space) ให้ถือว่าถูก Mark แล้ว (True)
        marks = (cards == 0)

        # 3. เริ่มวนลูปหยิบเลขทีละตัว
        for turn, number in enumerate(draw_sequence):
            current_turn = turn + 1
            
            # --- Vectorized Marking (หัวใจความเร็ว) ---
            # เทียบเลขที่ออก กับการ์ดทุกใบพร้อมกันทีเดียว
            # cards == number จะได้ตาราง True/False เฉพาะตำแหน่งที่มีเลขนั้น
            # ใช้ |= (OR Update) เพื่อสะสมแต้ม
            marks |= (cards == number)
            
            # --- Check Win Conditions (เช็คทุกใบพร้อมกัน) ---
            
            # 1. เช็คแถวแนวนอน (Row) -> check axis 2 (columns in each row)
            # all(axis=2) = True ถ้าทั้งแถวนั้นถูกกากบาทครบ
            # any(axis=1) = True ถ้ามีการ์ดใบใดใบหนึ่งมีแถวที่ครบ
            row_win = marks.all(axis=2).any(axis=1)
            
            # 2. เช็คแถวแนวตั้ง (Column) -> check axis 1 (rows in each col)
            col_win = marks.all(axis=1).any(axis=1)
            
            # 3. เช็คแนวทแยง (Diagonal)
            # diagonal ปกติ
            d1 = np.diagonal(marks, axis1=1, axis2=2) # ได้ shape (num_players, n)
            d1_win = d1.all(axis=1) # เช็คว่าครบแนวไหม
            
            # diagonal กลับด้าน (Flip)
            d2 = np.diagonal(np.flip(marks, axis=2), axis1=1, axis2=2)
            d2_win = d2.all(axis=1)
            
            # --- Combine Wins ---
            # เอาผลของทุกคนมารวมกัน (Bitwise OR)
            # ผลลัพธ์ player_wins คือ array boolean [True, False, ...] บอกว่าใครชนะบ้าง
            player_wins = row_win | col_win | d1_win | d2_win
            
            # ถ้ามีใครสักคนชนะ (True อย่างน้อย 1 คน) -> จบเกมทันที
            if player_wins.any():
                return current_turn
                
        return y # กรณีสุดวิสัย (ไม่น่าเกิดขึ้น)