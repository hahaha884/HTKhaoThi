import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from question_bank.models import CauHoi, DapAn, MachKienThuc, NoiDungKienThuc
from core.models import GiaoVien

# Lấy giáo viên đầu tiên làm người tạo
nguoi_tao = GiaoVien.objects.first()

# ============================================================
# XÓA TOÀN BỘ CÂU HỎI CŨ
# ============================================================
print("Xóa toàn bộ câu hỏi cũ...")
DapAn.objects.all().delete()
CauHoi.objects.all().delete()
print("Đã xóa xong.")

# ============================================================
# HÀM TIỆN ÍCH
# ============================================================
def make_mcq(khoi_id, mon_id, mach_id, nd_id, muc_do, noi_dung, choices, correct_idx):
    """choices = [(label, content), ...], correct_idx = index of correct answer"""
    q = CauHoi.objects.create(
        Khoi_id=khoi_id, MonHoc_id=mon_id,
        MachKienThuc_id=mach_id, NoiDungKienThuc_id=nd_id,
        HinhThuc='Trắc nghiệm', DangCauHoi='MCQ', MucDo=muc_do,
        NoiDungCauHoi=noi_dung, NguoiTao=nguoi_tao
    )
    for i, (label, content) in enumerate(choices):
        DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDungTrai=label,
                             NoiDung=content, LaDapAnDung=(i == correct_idx))
    return q

def make_msq(khoi_id, mon_id, mach_id, nd_id, muc_do, noi_dung, choices, correct_idxs):
    """correct_idxs = list of correct indices"""
    q = CauHoi.objects.create(
        Khoi_id=khoi_id, MonHoc_id=mon_id,
        MachKienThuc_id=mach_id, NoiDungKienThuc_id=nd_id,
        HinhThuc='Trắc nghiệm', DangCauHoi='MSQ', MucDo=muc_do,
        NoiDungCauHoi=noi_dung, NguoiTao=nguoi_tao
    )
    for i, (label, content) in enumerate(choices):
        DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDungTrai=label,
                             NoiDung=content, LaDapAnDung=(i in correct_idxs))
    return q

def make_tf(khoi_id, mon_id, mach_id, nd_id, muc_do, noi_dung, statements, tf_labels='Đúng, Sai'):
    """statements = [(content, correct_label), ...]"""
    q = CauHoi.objects.create(
        Khoi_id=khoi_id, MonHoc_id=mon_id,
        MachKienThuc_id=mach_id, NoiDungKienThuc_id=nd_id,
        HinhThuc='Trắc nghiệm', DangCauHoi='TF', MucDo=muc_do,
        NoiDungCauHoi=noi_dung, DapAnMau=tf_labels, NguoiTao=nguoi_tao
    )
    for i, (content, correct_label) in enumerate(statements):
        DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDung=content,
                             NoiDungTrai=correct_label, LaDapAnDung=True)
    return q

def make_matching(khoi_id, mon_id, mach_id, nd_id, muc_do, noi_dung, pairs):
    """pairs = [(left, right), ...]"""
    q = CauHoi.objects.create(
        Khoi_id=khoi_id, MonHoc_id=mon_id,
        MachKienThuc_id=mach_id, NoiDungKienThuc_id=nd_id,
        HinhThuc='Trắc nghiệm', DangCauHoi='Matching', MucDo=muc_do,
        NoiDungCauHoi=noi_dung, NguoiTao=nguoi_tao
    )
    for i, (left, right) in enumerate(pairs):
        DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDungTrai=left,
                             NoiDung=right, LaDapAnDung=True)
    return q

def make_fib(khoi_id, mon_id, mach_id, nd_id, muc_do, noi_dung, answers):
    """answers = [str, ...]"""
    q = CauHoi.objects.create(
        Khoi_id=khoi_id, MonHoc_id=mon_id,
        MachKienThuc_id=mach_id, NoiDungKienThuc_id=nd_id,
        HinhThuc='Trắc nghiệm', DangCauHoi='FIB', MucDo=muc_do,
        NoiDungCauHoi=noi_dung, NguoiTao=nguoi_tao
    )
    for i, ans in enumerate(answers):
        DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDung=ans, LaDapAnDung=True)
    return q

def make_essay(khoi_id, mon_id, mach_id, nd_id, muc_do, noi_dung, dap_an_mau, dang='EssayShort'):
    q = CauHoi.objects.create(
        Khoi_id=khoi_id, MonHoc_id=mon_id,
        MachKienThuc_id=mach_id, NoiDungKienThuc_id=nd_id,
        HinhThuc='Tự luận', DangCauHoi=dang, MucDo=muc_do,
        NoiDungCauHoi=noi_dung, DapAnMau=dap_an_mau, NguoiTao=nguoi_tao
    )
    return q

print("Bắt đầu seed câu hỏi...")
count = 0

# ============================================================
# KHỐI 1 - TOÁN - Số và Phép tính (mach=156)
# nd=158: Số đếm đến 10, phép cộng trừ trong phạm vi 10
# nd=159: Đọc viết so sánh số đến 100, cộng trừ không nhớ
# ============================================================

# --- MCQ Khối 1 Toán ---
make_mcq(1, 1, 156, 158, 'Mức 1',
    '5 + 3 = ?',
    [('A','6'), ('B','7'), ('C','8'), ('D','9')], 2)
count += 1

make_mcq(1, 1, 156, 158, 'Mức 1',
    '9 - 4 = ?',
    [('A','3'), ('B','4'), ('C','5'), ('D','6')], 2)
count += 1

make_mcq(1, 1, 156, 158, 'Mức 1',
    'Số nào lớn hơn trong hai số 7 và 4?',
    [('A','4'), ('B','5'), ('C','6'), ('D','7')], 3)
count += 1

make_mcq(1, 1, 156, 159, 'Mức 1',
    '35 + 24 = ?',
    [('A','58'), ('B','59'), ('C','60'), ('D','61')], 1)
count += 1

make_mcq(1, 1, 156, 159, 'Mức 2',
    'Trong các số: 47, 52, 38, 61. Số nào nhỏ nhất?',
    [('A','47'), ('B','52'), ('C','38'), ('D','61')], 2)
count += 1

make_mcq(1, 1, 156, 159, 'Mức 2',
    'Một hộp có 60 chiếc bút. Lấy ra 25 chiếc. Hỏi còn lại bao nhiêu chiếc?',
    [('A','30'), ('B','35'), ('C','40'), ('D','45')], 1)
count += 1

# --- FIB Khối 1 Toán ---
make_fib(1, 1, 156, 158, 'Mức 1',
    'Điền số còn thiếu: 6 + ___ = 10',
    ['4'])
count += 1

make_fib(1, 1, 156, 158, 'Mức 1',
    'Điền số còn thiếu: 8 - ___ = 3',
    ['5'])
count += 1

make_fib(1, 1, 156, 159, 'Mức 2',
    'Điền số còn thiếu: 45 + ___ = 70',
    ['25'])
count += 1

# --- TF Khối 1 Toán ---
make_tf(1, 1, 156, 158, 'Mức 1',
    'Đúng hay Sai về các phép tính sau đây?',
    [
        ('3 + 4 = 7', 'Đúng'),
        ('2 + 5 = 8', 'Sai'),
        ('9 - 6 = 3', 'Đúng'),
        ('7 - 3 = 5', 'Sai'),
    ])
count += 1

# --- Essay Khối 1 Toán ---
make_essay(1, 1, 156, 159, 'Mức 3',
    'Lớp 1A có 28 học sinh, lớp 1B có 32 học sinh. Hỏi cả hai lớp có bao nhiêu học sinh?',
    'Số học sinh cả hai lớp là: 28 + 32 = 60 (học sinh). Đáp số: 60 học sinh.')
count += 1

make_essay(1, 1, 156, 159, 'Mức 3',
    'Trên sân có 45 con chim. Bay đi 18 con. Hỏi còn lại bao nhiêu con chim?',
    'Số con chim còn lại là: 45 - 18 = 27 (con chim). Đáp số: 27 con chim.')
count += 1

print(f"  Khối 1 Toán: {count} câu")

# ============================================================
# KHỐI 1 - TOÁN - Hình học và Đo lường (mach=157)
# nd=160: Nhận diện hình vuông, hình tròn, hình tam giác
# nd=161: Đo độ dài (cm), xem giờ đúng
# ============================================================
c2 = 0

make_mcq(1, 1, 157, 160, 'Mức 1',
    'Hình nào sau đây có 3 cạnh và 3 góc?',
    [('A','Hình vuông'), ('B','Hình tròn'), ('C','Hình tam giác'), ('D','Hình chữ nhật')], 2)
c2 += 1

make_mcq(1, 1, 157, 160, 'Mức 1',
    'Hình nào không có góc?',
    [('A','Hình vuông'), ('B','Hình tam giác'), ('C','Hình tròn'), ('D','Hình chữ nhật')], 2)
c2 += 1

make_mcq(1, 1, 157, 161, 'Mức 2',
    'Cây bút chì dài 15 cm, cây thước dài 30 cm. Cây thước dài hơn cây bút chì bao nhiêu cm?',
    [('A','10 cm'), ('B','15 cm'), ('C','20 cm'), ('D','25 cm')], 1)
c2 += 1

make_mcq(1, 1, 157, 161, 'Mức 1',
    'Đồng hồ chỉ 3 giờ đúng. Kim ngắn chỉ vào số mấy?',
    [('A','Số 12'), ('B','Số 3'), ('C','Số 6'), ('D','Số 9')], 1)
c2 += 1

make_tf(1, 1, 157, 160, 'Mức 1',
    'Đúng hay Sai về đặc điểm các hình?',
    [
        ('Hình vuông có 4 cạnh bằng nhau', 'Đúng'),
        ('Hình tròn có 4 góc', 'Sai'),
        ('Hình tam giác có 3 đỉnh', 'Đúng'),
        ('Hình chữ nhật có 3 cạnh', 'Sai'),
    ])
c2 += 1

make_matching(1, 1, 157, 160, 'Mức 2',
    'Ghép tên hình với số cạnh tương ứng:',
    [
        ('Hình tam giác', '3 cạnh'),
        ('Hình vuông', '4 cạnh bằng nhau'),
        ('Hình tròn', 'Không có cạnh'),
        ('Hình chữ nhật', '4 cạnh, 2 cặp bằng nhau'),
    ])
c2 += 1

make_fib(1, 1, 157, 161, 'Mức 2',
    'Một đoạn dây dài 25 cm. Cắt đi 8 cm. Đoạn dây còn lại dài ___ cm.',
    ['17'])
c2 += 1

count += c2
print(f"  Khối 1 Toán Hình học: {c2} câu")

# ============================================================
# KHỐI 2 - TOÁN - Số và Phép tính (mach=158)
# nd=162: Cộng trừ có nhớ trong phạm vi 100, bảng 2 và 5
# nd=163: Số đến 1000, phép cộng trừ trong phạm vi 1000
# ============================================================
c3 = 0

make_mcq(2, 1, 158, 162, 'Mức 1',
    '2 × 6 = ?',
    [('A','10'), ('B','11'), ('C','12'), ('D','14')], 2)
c3 += 1

make_mcq(2, 1, 158, 162, 'Mức 1',
    '5 × 7 = ?',
    [('A','30'), ('B','35'), ('C','40'), ('D','45')], 1)
c3 += 1

make_mcq(2, 1, 158, 162, 'Mức 2',
    '56 + 37 = ?',
    [('A','83'), ('B','91'), ('C','93'), ('D','95')], 2)
c3 += 1

make_mcq(2, 1, 158, 162, 'Mức 2',
    'Bảng nhân 5: 5 × ___ = 40. Điền số còn thiếu.',
    [('A','6'), ('B','7'), ('C','8'), ('D','9')], 2)
c3 += 1

make_mcq(2, 1, 158, 163, 'Mức 2',
    '348 + 215 = ?',
    [('A','553'), ('B','563'), ('C','573'), ('D','583')], 1)
c3 += 1

make_mcq(2, 1, 158, 163, 'Mức 2',
    '700 - 265 = ?',
    [('A','425'), ('B','435'), ('C','445'), ('D','455')], 1)
c3 += 1

make_mcq(2, 1, 158, 163, 'Mức 3',
    'Một cửa hàng có 450 kg gạo. Buổi sáng bán 125 kg, buổi chiều bán 180 kg. Hỏi còn lại bao nhiêu kg gạo?',
    [('A','135 kg'), ('B','145 kg'), ('C','155 kg'), ('D','165 kg')], 1)
c3 += 1

make_msq(2, 1, 158, 162, 'Mức 2',
    'Những phép tính nào sau đây có kết quả bằng 10? (Chọn tất cả đáp án đúng)',
    [('A','2 × 5'), ('B','5 × 2'), ('C','4 × 3'), ('D','2 × 4 + 2')], [0, 1, 3])
c3 += 1

make_tf(2, 1, 158, 162, 'Mức 2',
    'Đúng hay Sai về bảng nhân 2 và bảng nhân 5?',
    [
        ('2 × 9 = 18', 'Đúng'),
        ('5 × 6 = 25', 'Sai'),
        ('2 × 7 = 14', 'Đúng'),
        ('5 × 8 = 45', 'Sai'),
    ])
c3 += 1

make_fib(2, 1, 158, 163, 'Mức 2',
    'Điền số thích hợp vào chỗ trống:\n500 + ___ = 800',
    ['300'])
c3 += 1

make_essay(2, 1, 158, 163, 'Mức 3',
    'Một trường học có 3 khối lớp. Khối 1 có 125 học sinh, khối 2 có 140 học sinh, khối 3 có 118 học sinh. Hỏi trường đó có tất cả bao nhiêu học sinh?',
    'Số học sinh cả trường là:\n125 + 140 + 118 = 383 (học sinh)\nĐáp số: 383 học sinh.')
c3 += 1

count += c3
print(f"  Khối 2 Toán: {c3} câu")

# ============================================================
# KHỐI 2 - TOÁN - Hình học và Đo lường (mach=159)
# nd=164: Khối trụ, khối cầu, đo lường kg và lít
# KHỐI 2 - TOÁN - Thống kê (mach=160)
# nd=165: Làm quen biểu đồ tranh
# ============================================================
c4 = 0

make_mcq(2, 1, 159, 164, 'Mức 1',
    'Vật nào sau đây có dạng khối cầu?',
    [('A','Hộp sữa'), ('B','Quả bóng'), ('C','Cái lon'), ('D','Cái hộp')], 1)
c4 += 1

make_mcq(2, 1, 159, 164, 'Mức 1',
    'Vật nào sau đây có dạng khối trụ?',
    [('A','Quả bóng đá'), ('B','Viên đá'), ('C','Cái lon nước ngọt'), ('D','Hộp bánh vuông')], 2)
c4 += 1

make_mcq(2, 1, 159, 164, 'Mức 2',
    'Một túi gạo nặng 5 kg. Hai túi gạo như thế nặng bao nhiêu kg?',
    [('A','8 kg'), ('B','10 kg'), ('C','12 kg'), ('D','15 kg')], 1)
c4 += 1

make_matching(2, 1, 159, 164, 'Mức 1',
    'Ghép tên khối với mô tả đặc điểm:',
    [
        ('Khối cầu', 'Tròn đều, không có mặt phẳng, lăn được mọi hướng'),
        ('Khối trụ', 'Có 2 mặt tròn bằng nhau và 1 mặt cong'),
        ('Khối hộp chữ nhật', 'Có 6 mặt phẳng hình chữ nhật'),
        ('Khối lập phương', 'Có 6 mặt phẳng hình vuông bằng nhau'),
    ])
c4 += 1

make_mcq(2, 1, 160, 165, 'Mức 2',
    'Biểu đồ tranh cho thấy: Lớp 2A bán được 4 gói kẹo, lớp 2B bán được 6 gói kẹo. Cả hai lớp bán được bao nhiêu gói kẹo?',
    [('A','8 gói'), ('B','9 gói'), ('C','10 gói'), ('D','12 gói')], 2)
c4 += 1

make_essay(2, 1, 160, 165, 'Mức 3',
    'Biểu đồ tranh về số sách đọc trong tháng của 4 bạn: An: 3 quyển, Bình: 5 quyển, Chi: 4 quyển, Dũng: 6 quyển. Hỏi: a) Ai đọc nhiều sách nhất? b) Trung bình mỗi bạn đọc bao nhiêu quyển?',
    'a) Dũng đọc nhiều sách nhất (6 quyển).\nb) Tổng số sách: 3 + 5 + 4 + 6 = 18 quyển.\n   Trung bình: 18 : 4 = 4,5 quyển/bạn.')
c4 += 1

count += c4
print(f"  Khối 2 Toán Hình học+Thống kê: {c4} câu")

# ============================================================
# KHỐI 3 - TOÁN - Số và Phép tính (mach=161)
# nd=166: Số đến 10000, bảng nhân chia 3-9
# nd=167: Số đến 100000, cộng trừ nhân chia trong phạm vi 100000
# ============================================================
c5 = 0

make_mcq(3, 1, 161, 166, 'Mức 1',
    '3 × 7 = ?',
    [('A','18'), ('B','21'), ('C','24'), ('D','27')], 1)
c5 += 1

make_mcq(3, 1, 161, 166, 'Mức 1',
    '56 ÷ 7 = ?',
    [('A','6'), ('B','7'), ('C','8'), ('D','9')], 2)
c5 += 1

make_mcq(3, 1, 161, 166, 'Mức 2',
    '4 × 8 + 12 = ?',
    [('A','40'), ('B','44'), ('C','48'), ('D','52')], 1)
c5 += 1

make_mcq(3, 1, 161, 166, 'Mức 2',
    'Một hộp có 6 ngăn, mỗi ngăn chứa 9 quyển sách. Hỏi hộp đó chứa tất cả bao nhiêu quyển sách?',
    [('A','45 quyển'), ('B','50 quyển'), ('C','54 quyển'), ('D','60 quyển')], 2)
c5 += 1

make_mcq(3, 1, 161, 166, 'Mức 3',
    '45 học sinh xếp thành các hàng, mỗi hàng 9 người. Hỏi có bao nhiêu hàng?',
    [('A','4 hàng'), ('B','5 hàng'), ('C','6 hàng'), ('D','7 hàng')], 1)
c5 += 1

make_msq(3, 1, 161, 166, 'Mức 2',
    'Phép tính nào có kết quả chia hết cho 3? (Chọn tất cả đáp án đúng)',
    [('A','27 ÷ 3'), ('B','28 ÷ 3'), ('C','36 ÷ 3'), ('D','40 ÷ 3')], [0, 2])
c5 += 1

make_tf(3, 1, 161, 166, 'Mức 2',
    'Đúng hay Sai?',
    [
        ('6 × 9 = 54', 'Đúng'),
        ('7 × 8 = 54', 'Sai'),
        ('81 ÷ 9 = 9', 'Đúng'),
        ('42 ÷ 6 = 8', 'Sai'),
    ])
c5 += 1

make_fib(3, 1, 161, 166, 'Mức 2',
    'Điền số thích hợp:\n___ × 9 = 63',
    ['7'])
c5 += 1

make_essay(3, 1, 161, 166, 'Mức 3',
    'Một vườn táo có 8 hàng cây, mỗi hàng có 9 cây táo. Hỏi vườn đó có tất cả bao nhiêu cây táo?',
    'Số cây táo trong vườn là:\n8 × 9 = 72 (cây táo)\nĐáp số: 72 cây táo.')
c5 += 1

count += c5
print(f"  Khối 3 Toán Số+Phép tính: {c5} câu")

# ============================================================
# KHỐI 3 - TOÁN - Hình học (mach=162)
# nd=168: Góc vuông, góc không vuông
# nd=169: Chu vi, diện tích hình chữ nhật, hình vuông
# ============================================================
c6 = 0

make_mcq(3, 1, 162, 168, 'Mức 1',
    'Góc vuông là góc có số đo bằng bao nhiêu độ?',
    [('A','45°'), ('B','60°'), ('C','90°'), ('D','180°')], 2)
c6 += 1

make_mcq(3, 1, 162, 168, 'Mức 2',
    'Hình chữ nhật có bao nhiêu góc vuông?',
    [('A','1'), ('B','2'), ('C','3'), ('D','4')], 3)
c6 += 1

make_mcq(3, 1, 162, 169, 'Mức 2',
    'Hình vuông có cạnh 5 cm. Chu vi hình vuông đó là bao nhiêu cm?',
    [('A','15 cm'), ('B','20 cm'), ('C','25 cm'), ('D','30 cm')], 1)
c6 += 1

make_mcq(3, 1, 162, 169, 'Mức 2',
    'Hình chữ nhật có chiều dài 8 cm, chiều rộng 5 cm. Diện tích hình chữ nhật là bao nhiêu cm²?',
    [('A','26 cm²'), ('B','30 cm²'), ('C','40 cm²'), ('D','45 cm²')], 2)
c6 += 1

make_mcq(3, 1, 162, 169, 'Mức 3',
    'Chu vi hình vuông là 36 cm. Diện tích hình vuông đó là bao nhiêu cm²?',
    [('A','64 cm²'), ('B','72 cm²'), ('C','81 cm²'), ('D','90 cm²')], 2)
c6 += 1

make_matching(3, 1, 162, 169, 'Mức 2',
    'Ghép công thức tính chu vi và diện tích:',
    [
        ('Chu vi hình vuông', 'C = 4 × a'),
        ('Diện tích hình vuông', 'S = a × a'),
        ('Chu vi hình chữ nhật', 'C = (dài + rộng) × 2'),
        ('Diện tích hình chữ nhật', 'S = dài × rộng'),
    ])
c6 += 1

make_essay(3, 1, 162, 169, 'Mức 3',
    'Một mảnh vườn hình chữ nhật có chiều dài 12 m, chiều rộng bằng một nửa chiều dài. Tính chu vi và diện tích mảnh vườn.',
    'Chiều rộng mảnh vườn là: 12 : 2 = 6 (m)\nChu vi mảnh vườn là: (12 + 6) × 2 = 36 (m)\nDiện tích mảnh vườn là: 12 × 6 = 72 (m²)\nĐáp số: Chu vi = 36 m; Diện tích = 72 m².')
c6 += 1

count += c6
print(f"  Khối 3 Toán Hình học: {c6} câu")

# ============================================================
# KHỐI 4 - TOÁN - Số và Phép tính (mach=164)
# nd=171: Số nhiều chữ số, trung bình cộng, tính chất phép cộng/nhân
# nd=172: Phân số và các phép tính với phân số
# ============================================================
c7 = 0

make_mcq(4, 1, 164, 171, 'Mức 1',
    'Trung bình cộng của 4 số: 12, 16, 20, 24 là bao nhiêu?',
    [('A','16'), ('B','17'), ('C','18'), ('D','19')], 2)
c7 += 1

make_mcq(4, 1, 164, 171, 'Mức 2',
    'Theo tính chất giao hoán của phép nhân: 5 × 7 = ___',
    [('A','5 + 7'), ('B','7 × 5'), ('C','5 + 5 + 5'), ('D','7 + 5')], 1)
c7 += 1

make_mcq(4, 1, 164, 172, 'Mức 1',
    'Phân số 3/4 đọc là gì?',
    [('A','Ba phần ba'), ('B','Ba phần tư'), ('C','Bốn phần ba'), ('D','Ba trên bốn')], 1)
c7 += 1

make_mcq(4, 1, 164, 172, 'Mức 2',
    '1/2 + 1/4 = ?',
    [('A','2/6'), ('B','2/4'), ('C','3/4'), ('D','1/6')], 2)
c7 += 1

make_mcq(4, 1, 164, 172, 'Mức 2',
    'Phân số nào sau đây bằng 1/2?',
    [('A','2/3'), ('B','3/6'), ('C','4/10'), ('D','3/8')], 1)
c7 += 1

make_mcq(4, 1, 164, 172, 'Mức 3',
    'Một cái bánh được chia thành 8 phần bằng nhau. Lan ăn 3 phần, Minh ăn 2 phần. Hỏi hai bạn ăn tất cả bao nhiêu phần cái bánh (viết dưới dạng phân số)?',
    [('A','4/8'), ('B','5/8'), ('C','6/8'), ('D','7/8')], 1)
c7 += 1

make_msq(4, 1, 164, 172, 'Mức 2',
    'Phân số nào sau đây lớn hơn 1/2? (Chọn tất cả đáp án đúng)',
    [('A','3/4'), ('B','1/3'), ('C','5/8'), ('D','2/6')], [0, 2])
c7 += 1

make_tf(4, 1, 164, 172, 'Mức 2',
    'Đúng hay Sai về phân số?',
    [
        ('2/4 = 1/2', 'Đúng'),
        ('3/5 > 4/5', 'Sai'),
        ('1/3 + 1/3 = 2/3', 'Đúng'),
        ('5/6 = 6/5', 'Sai'),
    ])
c7 += 1

make_fib(4, 1, 164, 171, 'Mức 2',
    'Trung bình cộng của 3 số 18, 24 và ___ bằng 20.',
    ['18'])
c7 += 1

make_essay(4, 1, 164, 172, 'Mức 3',
    'Một lớp học có 32 học sinh. Số học sinh giỏi chiếm 1/4 số học sinh cả lớp. Hỏi lớp đó có bao nhiêu học sinh giỏi?',
    'Số học sinh giỏi là:\n32 × 1/4 = 8 (học sinh)\nĐáp số: 8 học sinh giỏi.')
c7 += 1

count += c7
print(f"  Khối 4 Toán: {c7} câu")

# ============================================================
# KHỐI 4 - TOÁN - Hình học (mach=165)
# nd=173: Góc bẹt, nhọn, tù; đường thẳng song song/vuông góc
# nd=174: Hình bình hành, hình thoi
# ============================================================
c8 = 0

make_mcq(4, 1, 165, 173, 'Mức 1',
    'Góc bẹt có số đo bằng bao nhiêu độ?',
    [('A','90°'), ('B','120°'), ('C','150°'), ('D','180°')], 3)
c8 += 1

make_mcq(4, 1, 165, 173, 'Mức 1',
    'Góc nhọn là góc có số đo như thế nào?',
    [('A','Bằng 90°'), ('B','Lớn hơn 90°'), ('C','Nhỏ hơn 90°'), ('D','Bằng 180°')], 2)
c8 += 1

make_mcq(4, 1, 165, 173, 'Mức 2',
    'Hai đường thẳng vuông góc với nhau tạo thành góc có số đo bằng bao nhiêu?',
    [('A','45°'), ('B','60°'), ('C','90°'), ('D','180°')], 2)
c8 += 1

make_mcq(4, 1, 165, 174, 'Mức 2',
    'Hình bình hành có đặc điểm gì?',
    [('A','4 cạnh bằng nhau'), ('B','2 cặp cạnh song song và bằng nhau'), ('C','4 góc vuông'), ('D','4 cạnh bằng nhau và 4 góc vuông')], 1)
c8 += 1

make_mcq(4, 1, 165, 174, 'Mức 3',
    'Hình bình hành có đáy 10 cm và chiều cao 6 cm. Diện tích hình bình hành là bao nhiêu cm²?',
    [('A','32 cm²'), ('B','48 cm²'), ('C','60 cm²'), ('D','80 cm²')], 2)
c8 += 1

make_tf(4, 1, 165, 173, 'Mức 2',
    'Đúng hay Sai?',
    [
        ('Góc vuông lớn hơn góc nhọn', 'Đúng'),
        ('Góc tù nhỏ hơn 90°', 'Sai'),
        ('Hai đường thẳng song song không cắt nhau', 'Đúng'),
        ('Hình vuông có 4 góc tù', 'Sai'),
    ])
c8 += 1

make_matching(4, 1, 165, 173, 'Mức 2',
    'Ghép loại góc với số đo tương ứng:',
    [
        ('Góc nhọn', 'Nhỏ hơn 90°'),
        ('Góc vuông', 'Bằng 90°'),
        ('Góc tù', 'Lớn hơn 90° và nhỏ hơn 180°'),
        ('Góc bẹt', 'Bằng 180°'),
    ])
c8 += 1

count += c8
print(f"  Khối 4 Toán Hình học: {c8} câu")

# ============================================================
# KHỐI 5 - TOÁN - Số và Phép tính (mach=167)
# nd=176: Phân số thập phân, hỗn số, số thập phân, tỉ số %
# nd=177: Toán chuyển động đều
# ============================================================
c9 = 0

make_mcq(5, 1, 167, 176, 'Mức 1',
    '0,75 = ?',
    [('A','3/5'), ('B','7/10'), ('C','3/4'), ('D','7/5')], 2)
c9 += 1

make_mcq(5, 1, 167, 176, 'Mức 2',
    '30% của 200 là bao nhiêu?',
    [('A','50'), ('B','60'), ('C','70'), ('D','80')], 1)
c9 += 1

make_mcq(5, 1, 167, 176, 'Mức 2',
    '1,5 + 2,75 = ?',
    [('A','3,25'), ('B','4,15'), ('C','4,25'), ('D','4,35')], 2)
c9 += 1

make_mcq(5, 1, 167, 176, 'Mức 3',
    'Một lớp có 40 học sinh, có 25% đạt học sinh giỏi. Hỏi lớp đó có bao nhiêu học sinh giỏi?',
    [('A','8 học sinh'), ('B','10 học sinh'), ('C','12 học sinh'), ('D','15 học sinh')], 1)
c9 += 1

make_mcq(5, 1, 167, 177, 'Mức 2',
    'Một ô tô đi với vận tốc 60 km/h. Sau 3 giờ, ô tô đi được bao nhiêu km?',
    [('A','120 km'), ('B','150 km'), ('C','180 km'), ('D','210 km')], 2)
c9 += 1

make_mcq(5, 1, 167, 177, 'Mức 2',
    'Quãng đường từ A đến B dài 240 km. Một xe máy đi từ A đến B mất 4 giờ. Tính vận tốc của xe máy.',
    [('A','50 km/h'), ('B','55 km/h'), ('C','60 km/h'), ('D','65 km/h')], 2)
c9 += 1

make_mcq(5, 1, 167, 177, 'Mức 3',
    'Hai xe ô tô xuất phát cùng một lúc từ hai đầu một quãng đường dài 300 km, đi ngược chiều nhau. Xe thứ nhất có vận tốc 60 km/h, xe thứ hai có vận tốc 65 km/h. Sau bao nhiêu giờ hai xe gặp nhau?',
    [('A','2 giờ'), ('B','2,4 giờ'), ('C','3 giờ'), ('D','3,5 giờ')], 1)
c9 += 1

make_tf(5, 1, 167, 176, 'Mức 2',
    'Đúng hay Sai về số thập phân và tỉ số phần trăm?',
    [
        ('0,5 = 50%', 'Đúng'),
        ('1/4 = 0,4', 'Sai'),
        ('0,25 = 25%', 'Đúng'),
        ('3/5 = 0,35', 'Sai'),
    ])
c9 += 1

make_fib(5, 1, 167, 177, 'Mức 2',
    'Một người đi xe đạp với vận tốc 15 km/h trong 2 giờ. Người đó đi được ___ km.',
    ['30'])
c9 += 1

make_essay(5, 1, 167, 177, 'Mức 3',
    'Một tàu hỏa xuất phát từ ga A lúc 7 giờ sáng và đến ga B lúc 12 giờ trưa. Biết quãng đường AB dài 350 km. Tính vận tốc của tàu hỏa.',
    'Thời gian tàu đi từ A đến B là: 12 - 7 = 5 (giờ)\nVận tốc tàu hỏa là: 350 : 5 = 70 (km/h)\nĐáp số: 70 km/h.')
c9 += 1

count += c9
print(f"  Khối 5 Toán: {c9} câu")

# ============================================================
# KHỐI 5 - TOÁN - Hình học (mach=168)
# nd=178: Hình tam giác, hình thang
# nd=179: Thể tích hình hộp chữ nhật, hình lập phương
# ============================================================
c10 = 0

make_mcq(5, 1, 168, 178, 'Mức 2',
    'Hình thang có chiều cao 8 cm, đáy lớn 12 cm, đáy nhỏ 6 cm. Diện tích hình thang là bao nhiêu cm²?',
    [('A','64 cm²'), ('B','72 cm²'), ('C','80 cm²'), ('D','96 cm²')], 1)
c10 += 1

make_mcq(5, 1, 168, 178, 'Mức 2',
    'Tam giác vuông có 2 cạnh góc vuông là 6 cm và 8 cm. Diện tích tam giác vuông đó là bao nhiêu cm²?',
    [('A','24 cm²'), ('B','48 cm²'), ('C','14 cm²'), ('D','28 cm²')], 0)
c10 += 1

make_mcq(5, 1, 168, 179, 'Mức 2',
    'Hình lập phương có cạnh 5 cm. Thể tích hình lập phương đó là bao nhiêu cm³?',
    [('A','25 cm³'), ('B','75 cm³'), ('C','100 cm³'), ('D','125 cm³')], 3)
c10 += 1

make_mcq(5, 1, 168, 179, 'Mức 2',
    'Hình hộp chữ nhật có chiều dài 10 cm, chiều rộng 6 cm, chiều cao 4 cm. Thể tích là bao nhiêu cm³?',
    [('A','200 cm³'), ('B','220 cm³'), ('C','240 cm³'), ('D','260 cm³')], 2)
c10 += 1

make_matching(5, 1, 168, 179, 'Mức 2',
    'Ghép công thức tính với tên hình:',
    [
        ('Diện tích hình tam giác', 'S = (đáy × chiều cao) ÷ 2'),
        ('Diện tích hình thang', 'S = (đáy lớn + đáy nhỏ) × chiều cao ÷ 2'),
        ('Thể tích hình lập phương', 'V = cạnh × cạnh × cạnh'),
        ('Thể tích hình hộp chữ nhật', 'V = dài × rộng × cao'),
    ])
c10 += 1

make_essay(5, 1, 168, 179, 'Mức 3',
    'Một bể cá hình hộp chữ nhật có chiều dài 80 cm, chiều rộng 40 cm, chiều cao 50 cm. Hiện bể đang chứa nước đến 3/4 chiều cao. Tính thể tích lượng nước trong bể.',
    'Thể tích toàn bộ bể: 80 × 40 × 50 = 160 000 (cm³)\nChiều cao mực nước: 50 × 3/4 = 37,5 (cm)\nThể tích nước: 80 × 40 × 37,5 = 120 000 (cm³)\nĐáp số: 120 000 cm³ = 120 lít.')
c10 += 1

count += c10
print(f"  Khối 5 Toán Hình học: {c10} câu")

# ============================================================
# TIẾNG VIỆT - KHỐI 2 (mach=172, 173, 174)
# nd=185: Đọc hiểu văn bản
# nd=186: Luyện từ và câu
# nd=188: Viết đoạn văn ngắn
# ============================================================
c11 = 0

make_mcq(2, 2, 172, 185, 'Mức 1',
    'Đọc đoạn văn sau và trả lời câu hỏi:\n"Chú chim sẻ nhỏ nhắn bay từ cành này sang cành khác, hót líu lo. Tiếng hót trong trẻo vang cả khu vườn xanh mát."\nTrong đoạn văn, chú chim sẻ đang làm gì?',
    [('A','Đang ăn'), ('B','Đang bay và hót'), ('C','Đang ngủ'), ('D','Đang xây tổ')], 1)
c11 += 1

make_mcq(2, 2, 172, 185, 'Mức 2',
    'Trong câu "Bầu trời xanh trong như gương.", từ "trong" mang nghĩa gì?',
    [('A','Chỉ không gian bên trong'), ('B','Chỉ màu xanh'), ('C','Chỉ sự trong sáng, không bị vẩn đục'), ('D','Chỉ sự im lặng')], 2)
c11 += 1

make_mcq(2, 2, 173, 186, 'Mức 1',
    'Trong câu "Con mèo đang ngủ.", từ nào là từ chỉ hoạt động?',
    [('A','Con mèo'), ('B','đang'), ('C','ngủ'), ('D','Con')], 2)
c11 += 1

make_mcq(2, 2, 173, 186, 'Mức 2',
    'Câu "Bông hoa hồng rất đẹp." thuộc kiểu câu nào?',
    [('A','Câu kiểu Ai làm gì?'), ('B','Câu kiểu Ai là gì?'), ('C','Câu kiểu Ai thế nào?'), ('D','Câu hỏi')], 2)
c11 += 1

make_tf(2, 2, 173, 186, 'Mức 2',
    'Đúng hay Sai về các từ loại?',
    [
        ('"học sinh" là từ chỉ sự vật', 'Đúng'),
        ('"chạy" là từ chỉ đặc điểm', 'Sai'),
        ('"cao" là từ chỉ đặc điểm', 'Đúng'),
        ('"trường học" là từ chỉ hoạt động', 'Sai'),
    ])
c11 += 1

make_matching(2, 2, 173, 186, 'Mức 2',
    'Ghép từ với nhóm từ loại phù hợp:',
    [
        ('Bàn, ghế, sách', 'Từ chỉ sự vật'),
        ('Chạy, nhảy, hát', 'Từ chỉ hoạt động'),
        ('Đẹp, xanh, to', 'Từ chỉ đặc điểm'),
        ('Tôi, em, bạn', 'Đại từ chỉ người'),
    ])
c11 += 1

make_essay(2, 2, 174, 188, 'Mức 3',
    'Viết một đoạn văn ngắn (4-5 câu) miêu tả con vật mà em yêu thích.',
    'Đoạn văn tham khảo:\nEm rất thích con mèo nhà em. Bộ lông của mèo màu vàng óng, mềm mại. Đôi mắt mèo tròn xoe, sáng lấp lánh. Mèo thường nằm phơi nắng ở hiên nhà và chạy đuổi theo những con bướm bay qua. Em rất yêu quý con mèo của mình.\n(Học sinh có thể chọn con vật khác, yêu cầu: có 4-5 câu, miêu tả đặc điểm và thói quen của con vật)')
c11 += 1

count += c11
print(f"  Khối 2 Tiếng Việt: {c11} câu")

# ============================================================
# TIẾNG VIỆT - KHỐI 3 (mach=175, 176, 177)
# nd=190: Đọc hiểu
# nd=191: Nhân hóa, so sánh
# nd=193: Viết đoạn văn
# ============================================================
c12 = 0

make_mcq(3, 2, 175, 190, 'Mức 2',
    'Đọc đoạn văn:\n"Dòng sông quê em xanh biếc. Hai bên bờ, những hàng tre xanh tốt nghiêng mình soi bóng xuống mặt nước. Sáng sáng, lũ trẻ thường ra sông tắm và vui đùa."\nĐâu là câu văn miêu tả hoạt động trong đoạn trên?',
    [
        ('A','Dòng sông quê em xanh biếc.'),
        ('B','Hai bên bờ, những hàng tre xanh tốt nghiêng mình soi bóng xuống mặt nước.'),
        ('C','Sáng sáng, lũ trẻ thường ra sông tắm và vui đùa.'),
        ('D','Dòng sông và hàng tre đều rất đẹp.')
    ], 2)
c12 += 1

make_mcq(3, 2, 176, 191, 'Mức 2',
    'Câu "Những chiếc lá vàng nhảy múa trong gió." sử dụng biện pháp tu từ gì?',
    [('A','So sánh'), ('B','Nhân hóa'), ('C','Điệp ngữ'), ('D','Liệt kê')], 1)
c12 += 1

make_mcq(3, 2, 176, 191, 'Mức 2',
    'Câu nào sau đây sử dụng biện pháp so sánh?',
    [
        ('A','Con chim hót véo von trên cành.'),
        ('B','Mái tóc bà bạc trắng như mây.'),
        ('C','Chiếc lá rơi xuống đất.'),
        ('D','Bầu trời trong xanh.')
    ], 1)
c12 += 1

make_mcq(3, 2, 176, 191, 'Mức 3',
    'Tìm phép nhân hóa trong câu: "Ông mặt trời thức dậy sớm, ban phát ánh vàng cho muôn loài."',
    [
        ('A','Ông mặt trời'),
        ('B','ánh vàng'),
        ('C','muôn loài'),
        ('D','Cả A và B đều đúng')
    ], 0)
c12 += 1

make_tf(3, 2, 176, 191, 'Mức 2',
    'Đúng hay Sai về biện pháp tu từ?',
    [
        ('"Tiếng suối trong như tiếng hát" là câu so sánh', 'Đúng'),
        ('"Con gà gáy o o" là câu nhân hóa', 'Sai'),
        ('"Mặt trăng như chiếc đĩa bạc" là câu so sánh', 'Đúng'),
        ('"Gió thổi lá cây" là câu nhân hóa', 'Sai'),
    ])
c12 += 1

make_essay(3, 2, 177, 193, 'Mức 3',
    'Viết đoạn văn ngắn (4-6 câu) tả lại cảnh buổi sáng ở quê hương em (hoặc nơi em ở). Trong đoạn văn có sử dụng ít nhất một phép so sánh hoặc nhân hóa.',
    'Yêu cầu:\n- Đủ 4-6 câu văn\n- Có hình ảnh thiên nhiên hoặc con người buổi sáng\n- Có ít nhất 1 phép so sánh hoặc nhân hóa\n- Câu văn mạch lạc, diễn đạt rõ ràng\n\nVí dụ: Sáng sớm, ông mặt trời thức dậy, phủ ánh vàng lên cánh đồng quê em. Những giọt sương còn đọng trên lá như những viên ngọc long lanh. Tiếng chim hót líu lo vang khắp vườn cây. Bầu trời xanh trong vắt như một tấm gương khổng lồ.')
c12 += 1

count += c12
print(f"  Khối 3 Tiếng Việt: {c12} câu")

# ============================================================
# TIẾNG VIỆT - KHỐI 4 (mach=178, 179, 180)
# nd=195: Đọc hiểu văn bản dài
# nd=196: Danh từ, Động từ, Tính từ
# nd=197: Trạng ngữ
# nd=198: Kể chuyện, miêu tả
# ============================================================
c13 = 0

make_mcq(4, 2, 178, 195, 'Mức 2',
    'Đọc đoạn văn:\n"Chú bé Dế Mèn trong truyện của nhà văn Tô Hoài là một chú dế khỏe mạnh, ưa phiêu lưu nhưng cũng rất kiêu ngạo. Chú đã trải qua nhiều bài học đau đớn để trở thành người dế tốt hơn."\nĐâu là nhân vật chính trong đoạn văn trên?',
    [('A','Nhà văn Tô Hoài'), ('B','Dế Mèn'), ('C','Một chú dế khỏe mạnh'), ('D','Người kể chuyện')], 1)
c13 += 1

make_mcq(4, 2, 178, 195, 'Mức 3',
    'Đọc đoạn văn:\n"Những ngôi sao thức ngoài kia\nChẳng bằng mẹ đã thức vì chúng con\nĐêm nay con ngủ giấc tròn\nMẹ là ngọn gió của con suốt đời."\n(Trần Quốc Minh)\nHình ảnh "Mẹ là ngọn gió của con" thể hiện điều gì?',
    [
        ('A','Mẹ thổi gió mát cho con ngủ'),
        ('B','Tình yêu thương vô bờ và sự hi sinh của mẹ'),
        ('C','Mẹ là người làm việc như gió'),
        ('D','Gió và mẹ đều quan trọng')
    ], 1)
c13 += 1

make_mcq(4, 2, 179, 196, 'Mức 1',
    'Trong câu "Cô giáo đang giảng bài rất hăng say.", từ nào là tính từ?',
    [('A','Cô giáo'), ('B','giảng bài'), ('C','hăng say'), ('D','đang')], 2)
c13 += 1

make_mcq(4, 2, 179, 196, 'Mức 2',
    'Xác định danh từ trong câu: "Những đứa trẻ hồn nhiên đang vui chơi trong sân trường."',
    [('A','hồn nhiên'), ('B','vui chơi'), ('C','đứa trẻ, sân trường'), ('D','đang')], 2)
c13 += 1

make_mcq(4, 2, 179, 197, 'Mức 2',
    'Trong câu "Vào mùa xuân, hoa đào nở rộ khắp nơi.", bộ phận nào là trạng ngữ?',
    [('A','hoa đào nở rộ'), ('B','khắp nơi'), ('C','Vào mùa xuân'), ('D','hoa đào')], 2)
c13 += 1

make_msq(4, 2, 179, 196, 'Mức 2',
    'Những từ nào sau đây là tính từ? (Chọn tất cả đáp án đúng)',
    [('A','xinh đẹp'), ('B','học tập'), ('C','thông minh'), ('D','chăm chỉ')], [0, 2, 3])
c13 += 1

make_tf(4, 2, 179, 197, 'Mức 2',
    'Đúng hay Sai về trạng ngữ?',
    [
        ('Trạng ngữ có thể đứng đầu câu', 'Đúng'),
        ('Trạng ngữ là thành phần bắt buộc trong câu', 'Sai'),
        ('Trạng ngữ có thể bổ sung thời gian, nơi chốn, nguyên nhân', 'Đúng'),
        ('Trạng ngữ không thể bị tách khỏi câu', 'Sai'),
    ])
c13 += 1

make_essay(4, 2, 180, 198, 'Mức 3',
    'Viết một đoạn văn ngắn (5-7 câu) kể lại một việc tốt mà em đã làm (hoặc chứng kiến). Chú ý sử dụng danh từ, động từ, tính từ đa dạng.',
    'Yêu cầu:\n- 5-7 câu, mạch lạc, đúng chủ đề\n- Kể được: ai làm việc tốt, làm gì, kết quả\n- Sử dụng đa dạng từ loại (danh từ, động từ, tính từ)\n- Câu văn có cảm xúc, chân thực')
c13 += 1

count += c13
print(f"  Khối 4 Tiếng Việt: {c13} câu")

# ============================================================
# TIẾNG VIỆT - KHỐI 5 (mach=182, 183, 184)
# nd=201: Đại từ, Quan hệ từ, Từ đồng nghĩa, trái nghĩa
# nd=205: Đọc hiểu tác phẩm văn học
# nd=203: Viết bài văn miêu tả
# ============================================================
c14 = 0

make_mcq(5, 2, 182, 201, 'Mức 1',
    'Từ nào sau đây là quan hệ từ?',
    [('A','tôi'), ('B','và'), ('C','đẹp'), ('D','chạy')], 1)
c14 += 1

make_mcq(5, 2, 182, 201, 'Mức 2',
    'Cặp từ nào sau đây là từ trái nghĩa?',
    [('A','vui - mừng'), ('B','buồn - buồn bã'), ('C','cao - thấp'), ('D','đẹp - xinh')], 2)
c14 += 1

make_mcq(5, 2, 182, 201, 'Mức 2',
    'Cặp từ nào sau đây là từ đồng nghĩa?',
    [('A','nhanh - chậm'), ('B','vui - buồn'), ('C','xinh - đẹp'), ('D','to - nhỏ')], 2)
c14 += 1

make_mcq(5, 2, 184, 205, 'Mức 3',
    'Đọc đoạn trích truyện "Chiếc lá cuối cùng" (O. Henry):\n"Cụ Bơ-men đã hi sinh tính mạng của mình để vẽ chiếc lá cuối cùng trên tường, cứu sống cô gái trẻ Giôn-xi đang mất dần ý chí sống."\nHành động của cụ Bơ-men thể hiện điều gì?',
    [
        ('A','Cụ rất giỏi hội họa'),
        ('B','Lòng nhân ái và sự hi sinh cao cả'),
        ('C','Cụ muốn nổi tiếng'),
        ('D','Cụ thích vẽ trong đêm mưa')
    ], 1)
c14 += 1

make_msq(5, 2, 182, 201, 'Mức 2',
    'Những từ nào sau đây là từ đồng nghĩa với từ "vui mừng"? (Chọn tất cả đáp án đúng)',
    [('A','hân hoan'), ('B','buồn bã'), ('C','phấn khởi'), ('D','hớn hở')], [0, 2, 3])
c14 += 1

make_matching(5, 2, 182, 201, 'Mức 2',
    'Ghép từ với từ trái nghĩa tương ứng:',
    [
        ('dũng cảm', 'hèn nhát'),
        ('chăm chỉ', 'lười biếng'),
        ('trung thực', 'gian dối'),
        ('khiêm tốn', 'kiêu ngạo'),
    ])
c14 += 1

make_tf(5, 2, 182, 201, 'Mức 2',
    'Đúng hay Sai?',
    [
        ('"nhanh" và "mau" là hai từ đồng nghĩa', 'Đúng'),
        ('"đen" và "trắng" là hai từ đồng âm', 'Sai'),
        ('"tôi, chúng tôi, em" là các đại từ chỉ người nói', 'Đúng'),
        ('"và, nhưng, vì" là các danh từ', 'Sai'),
    ])
c14 += 1

make_essay(5, 2, 183, 203, 'Mức 3',
    'Viết một bài văn ngắn (8-10 câu) tả cảnh một buổi học mà em ấn tượng nhất. Bài văn cần có phần mở bài, thân bài và kết bài.',
    'Yêu cầu:\n- Bài văn có 3 phần: mở bài, thân bài, kết bài\n- Miêu tả được: thời gian, không gian, hoạt động của thầy/cô và học sinh\n- Câu văn đa dạng về cấu trúc (câu đơn, câu ghép)\n- Có sử dụng biện pháp so sánh hoặc nhân hóa\n- Bày tỏ được cảm xúc của bản thân')
c14 += 1

count += c14
print(f"  Khối 5 Tiếng Việt: {c14} câu")

# ============================================================
# KHOA HỌC - KHỐI 4 (mach=188)
# nd=212: Trao đổi chất, Nước, Không khí, Âm thanh, Ánh sáng
# nd=213: Vật chất và Năng lượng, Sự sinh sản, Môi trường
# ============================================================
c15 = 0

make_mcq(4, 4, 188, 212, 'Mức 1',
    'Quá trình cây xanh tự tổng hợp chất hữu cơ từ nước, CO₂ và ánh sáng mặt trời gọi là gì?',
    [('A','Hô hấp'), ('B','Trao đổi chất'), ('C','Quang hợp'), ('D','Tiêu hóa')], 2)
c15 += 1

make_mcq(4, 4, 188, 212, 'Mức 1',
    'Không khí trong lành cần thiết cho sự sống. Thành phần chiếm tỉ lệ lớn nhất trong không khí là khí gì?',
    [('A','Ô-xi (O₂)'), ('B','Ni-tơ (N₂)'), ('C','CO₂'), ('D','Hơi nước')], 1)
c15 += 1

make_mcq(4, 4, 188, 212, 'Mức 2',
    'Âm thanh truyền được qua môi trường nào?',
    [('A','Chỉ qua không khí'), ('B','Chỉ qua chất lỏng'), ('C','Chỉ qua chất rắn'), ('D','Qua cả không khí, chất lỏng và chất rắn')], 3)
c15 += 1

make_mcq(4, 4, 188, 212, 'Mức 2',
    'Vật nào sau đây cho ánh sáng truyền qua hoàn toàn?',
    [('A','Tờ giấy trắng'), ('B','Tấm gỗ'), ('C','Tấm kính trong suốt'), ('D','Tấm nhựa mờ')], 2)
c15 += 1

make_mcq(4, 4, 188, 213, 'Mức 2',
    'Nguồn năng lượng nào sau đây là năng lượng tái tạo?',
    [('A','Than đá'), ('B','Dầu mỏ'), ('C','Năng lượng mặt trời'), ('D','Khí ga tự nhiên')], 2)
c15 += 1

make_msq(4, 4, 188, 212, 'Mức 2',
    'Những điều nào sau đây đúng về nước? (Chọn tất cả đáp án đúng)',
    [
        ('A','Nước không có màu, không mùi, không vị'),
        ('B','Nước sôi ở 100°C'),
        ('C','Nước đá nặng hơn nước lỏng'),
        ('D','Nước tồn tại ở 3 thể: rắn, lỏng, khí')
    ], [0, 1, 3])
c15 += 1

make_tf(4, 4, 188, 212, 'Mức 2',
    'Đúng hay Sai về các hiện tượng tự nhiên?',
    [
        ('Ánh sáng mặt trời truyền theo đường thẳng', 'Đúng'),
        ('Âm thanh truyền nhanh hơn ánh sáng', 'Sai'),
        ('Nước bay hơi khi bị đun nóng', 'Đúng'),
        ('Không khí không có trọng lượng', 'Sai'),
    ])
c15 += 1

make_essay(4, 4, 188, 213, 'Mức 3',
    'Em hãy nêu ít nhất 3 việc làm cụ thể để bảo vệ môi trường xung quanh nơi em sinh sống. Giải thích tại sao những việc làm đó có ích.',
    'Gợi ý đáp án (học sinh có thể kể khác):\n1. Không vứt rác bừa bãi → giảm ô nhiễm đất, nước, không khí\n2. Trồng cây xanh → cung cấp oxy, làm sạch không khí, chống xói mòn đất\n3. Tiết kiệm điện, nước → giảm ô nhiễm từ nhà máy điện, bảo tồn nguồn nước ngầm\n4. Không đốt rác → tránh thải khói độc vào không khí\nYêu cầu: nêu đúng việc làm, giải thích có logic và liên quan đến kiến thức khoa học')
c15 += 1

count += c15
print(f"  Khối 4 Khoa học: {c15} câu")

# ============================================================
# KHOA HỌC - KHỐI 5 (mach=189)
# nd=214: Trao đổi chất, Nước, Ánh sáng (Khối 5)
# nd=215: Năng lượng, Sinh sản, Môi trường (Khối 5)
# ============================================================
c16 = 0

make_mcq(5, 4, 189, 214, 'Mức 1',
    'Cơ quan nào trong cơ thể người thực hiện chức năng trao đổi khí?',
    [('A','Tim'), ('B','Phổi'), ('C','Gan'), ('D','Thận')], 1)
c16 += 1

make_mcq(5, 4, 189, 214, 'Mức 2',
    'Hệ tuần hoàn của người gồm những bộ phận chính nào?',
    [
        ('A','Tim và phổi'),
        ('B','Tim và các mạch máu'),
        ('C','Phổi và mạch máu'),
        ('D','Tim, phổi và thận')
    ], 1)
c16 += 1

make_mcq(5, 4, 189, 215, 'Mức 2',
    'Chuỗi thức ăn nào sau đây đúng?',
    [
        ('A','Cỏ → Sâu → Ếch → Rắn'),
        ('B','Sâu → Cỏ → Ếch → Rắn'),
        ('C','Rắn → Ếch → Sâu → Cỏ'),
        ('D','Ếch → Cỏ → Sâu → Rắn')
    ], 0)
c16 += 1

make_mcq(5, 4, 189, 215, 'Mức 3',
    'Hiệu ứng nhà kính xảy ra chủ yếu do nguyên nhân nào?',
    [
        ('A','Trái đất quay quanh mặt trời'),
        ('B','Khí CO₂ và các khí nhà kính tăng cao trong khí quyển do hoạt động con người'),
        ('C','Mưa axit phá hủy rừng'),
        ('D','Biển ngày càng rộng hơn')
    ], 1)
c16 += 1

make_tf(5, 4, 189, 215, 'Mức 2',
    'Đúng hay Sai?',
    [
        ('Thực vật là sinh vật sản xuất trong chuỗi thức ăn', 'Đúng'),
        ('Rắn ăn ếch nên ếch là sinh vật phân giải', 'Sai'),
        ('Nấm và vi khuẩn là sinh vật phân giải', 'Đúng'),
        ('Khi một loài biến mất, chuỗi thức ăn không bị ảnh hưởng', 'Sai'),
    ])
c16 += 1

make_matching(5, 4, 189, 215, 'Mức 2',
    'Ghép sinh vật với vai trò trong chuỗi thức ăn:',
    [
        ('Cây cỏ, lúa', 'Sinh vật sản xuất'),
        ('Châu chấu, sâu', 'Sinh vật tiêu thụ bậc 1'),
        ('Ếch, chim', 'Sinh vật tiêu thụ bậc 2'),
        ('Nấm, vi khuẩn', 'Sinh vật phân giải'),
    ])
c16 += 1

make_essay(5, 4, 189, 215, 'Mức 3',
    'Em hãy nêu sự khác nhau giữa sinh sản hữu tính và sinh sản vô tính. Cho ví dụ mỗi loại.',
    'Sinh sản vô tính:\n- Không cần sự kết hợp của tế bào sinh dục đực và cái\n- Cơ thể mới giống hoàn toàn cơ thể mẹ\n- Ví dụ: Cây khoai lang mọc từ rễ, cây chuối mọc từ chồi, trùng roi phân chia\n\nSinh sản hữu tính:\n- Có sự kết hợp của tế bào sinh dục đực (tinh trùng) và cái (trứng)\n- Tạo ra cơ thể mới có đặc điểm của cả bố và mẹ\n- Ví dụ: Người, động vật có vú, chim, hoa thụ phấn tạo hạt')
c16 += 1

count += c16
print(f"  Khối 5 Khoa học: {c16} câu")

# ============================================================
# LỊCH SỬ & ĐỊA LÝ - KHỐI 4 (mach=190)
# nd=216: Lịch sử địa phương, các triều đại cổ-trung đại
# nd=217: Lịch sử cận-hiện đại
# ============================================================
c17 = 0

make_mcq(4, 15, 190, 216, 'Mức 1',
    'Nhà nước Văn Lang do ai sáng lập?',
    [('A','An Dương Vương'), ('B','Hùng Vương'), ('C','Ngô Quyền'), ('D','Đinh Bộ Lĩnh')], 1)
c17 += 1

make_mcq(4, 15, 190, 216, 'Mức 2',
    'Chiến thắng Bạch Đằng năm 938 do ai lãnh đạo, đánh bại quân xâm lược nào?',
    [
        ('A','Lý Thường Kiệt - quân Tống'),
        ('B','Ngô Quyền - quân Nam Hán'),
        ('C','Trần Hưng Đạo - quân Nguyên Mông'),
        ('D','Lê Lợi - quân Minh')
    ], 1)
c17 += 1

make_mcq(4, 15, 190, 216, 'Mức 2',
    'Thủ đô của nước ta hiện nay có tên là gì và được Vua Lý Thái Tổ đặt tên là gì?',
    [
        ('A','Hà Nội - Thăng Long'),
        ('B','Hà Nội - Đại La'),
        ('C','Huế - Phú Xuân'),
        ('D','Hà Nội - Đông Đô')
    ], 0)
c17 += 1

make_mcq(4, 15, 190, 217, 'Mức 2',
    'Thực dân Pháp bắt đầu xâm lược nước ta vào năm nào?',
    [('A','1802'), ('B','1858'), ('C','1884'), ('D','1945')], 1)
c17 += 1

make_tf(4, 15, 190, 216, 'Mức 2',
    'Đúng hay Sai về lịch sử Việt Nam?',
    [
        ('Hùng Vương là người sáng lập nước Văn Lang', 'Đúng'),
        ('Lý Thường Kiệt đánh thắng quân Nguyên Mông', 'Sai'),
        ('Ngô Quyền chiến thắng quân Nam Hán trên sông Bạch Đằng năm 938', 'Đúng'),
        ('Đinh Bộ Lĩnh dẹp loạn 15 sứ quân, lập ra nhà Tiền Lê', 'Sai'),
    ])
c17 += 1

make_matching(4, 15, 190, 216, 'Mức 2',
    'Ghép nhân vật lịch sử với sự kiện tương ứng:',
    [
        ('Ngô Quyền', 'Đánh tan quân Nam Hán trên sông Bạch Đằng (938)'),
        ('Đinh Bộ Lĩnh', 'Dẹp loạn 12 sứ quân, lập nước Đại Cồ Việt'),
        ('Lý Thái Tổ', 'Dời đô từ Hoa Lư về Thăng Long'),
        ('Trần Hưng Đạo', 'Ba lần đánh thắng quân Nguyên Mông'),
    ])
c17 += 1

make_essay(4, 15, 190, 217, 'Mức 3',
    'Em hãy kể lại ý nghĩa của chiến thắng Điện Biên Phủ năm 1954 đối với lịch sử Việt Nam.',
    'Chiến thắng Điện Biên Phủ (7/5/1954):\n- Là chiến thắng lớn nhất trong cuộc kháng chiến chống Pháp\n- Tiêu diệt và bắt sống toàn bộ tập đoàn cứ điểm mạnh nhất của Pháp\n- Buộc Pháp phải ký Hiệp định Giơ-ne-vơ (7/1954), rút quân khỏi miền Bắc Việt Nam\n- Chấm dứt ách thống trị 80 năm của thực dân Pháp\n- Cổ vũ phong trào giải phóng dân tộc trên toàn thế giới')
c17 += 1

count += c17
print(f"  Khối 4 Lịch sử & Địa lý: {c17} câu")

# ============================================================
# LỊCH SỬ & ĐỊA LÝ - KHỐI 5 (mach=191)
# nd=218: Lịch sử địa phương, các triều đại (Khối 5)
# nd=219: Lịch sử cận-hiện đại, Địa lý các châu lục
# ============================================================
c18 = 0

make_mcq(5, 15, 191, 219, 'Mức 1',
    'Cách mạng tháng Tám năm 1945 thành công, nước Việt Nam Dân chủ Cộng hòa được thành lập vào ngày tháng năm nào?',
    [('A','19/8/1945'), ('B','2/9/1945'), ('C','30/4/1975'), ('D','7/5/1954')], 1)
c18 += 1

make_mcq(5, 15, 191, 219, 'Mức 2',
    'Đại thắng mùa Xuân 1975, đất nước thống nhất vào ngày nào?',
    [('A','19/8/1945'), ('B','7/5/1954'), ('C','30/4/1975'), ('D','2/9/1975')], 2)
c18 += 1

make_mcq(5, 15, 191, 219, 'Mức 2',
    'Việt Nam nằm ở khu vực nào của châu Á?',
    [('A','Đông Á'), ('B','Nam Á'), ('C','Đông Nam Á'), ('D','Tây Á')], 2)
c18 += 1

make_mcq(5, 15, 191, 219, 'Mức 2',
    'Sông nào dài nhất châu Phi?',
    [('A','Sông Congo'), ('B','Sông Niger'), ('C','Sông Nile'), ('D','Sông Zambezi')], 2)
c18 += 1

make_msq(5, 15, 191, 219, 'Mức 2',
    'Những lục địa nào sau đây thuộc bán cầu Nam? (Chọn tất cả đáp án đúng)',
    [('A','Châu Phi (phần lớn)'), ('B','Châu Âu'), ('C','Nam Mỹ'), ('D','Châu Á')], [0, 2])
c18 += 1

make_tf(5, 15, 191, 218, 'Mức 2',
    'Đúng hay Sai?',
    [
        ('Hồ Chí Minh là người sáng lập Đảng Cộng sản Việt Nam năm 1930', 'Đúng'),
        ('Miền Nam Việt Nam hoàn toàn giải phóng ngày 30/4/1975', 'Đúng'),
        ('Hiệp định Paris ký năm 1975 chấm dứt chiến tranh Việt Nam', 'Sai'),
        ('Nước Việt Nam Dân chủ Cộng hòa thành lập ngày 2/9/1945', 'Đúng'),
    ])
c18 += 1

make_matching(5, 15, 191, 219, 'Mức 2',
    'Ghép châu lục với đặc điểm địa lý tiêu biểu:',
    [
        ('Châu Phi', 'Có sa mạc Sahara lớn nhất thế giới'),
        ('Châu Mỹ', 'Có dãy núi Andes dài nhất thế giới'),
        ('Châu Á', 'Có đỉnh Everest cao nhất thế giới'),
        ('Châu Đại Dương', 'Có lục địa Úc và nhiều đảo nhỏ trên Thái Bình Dương'),
    ])
c18 += 1

make_essay(5, 15, 191, 219, 'Mức 3',
    'Em hãy nêu ý nghĩa lịch sử của chiến thắng 30/4/1975 đối với dân tộc Việt Nam.',
    'Ý nghĩa chiến thắng 30/4/1975:\n- Kết thúc 21 năm kháng chiến chống Mỹ cứu nước\n- Giải phóng hoàn toàn miền Nam, thống nhất đất nước\n- Chấm dứt sự chia cắt đất nước sau Hiệp định Giơ-ne-vơ 1954\n- Mở ra kỷ nguyên độc lập, tự do và xây dựng đất nước\n- Nâng cao vị thế Việt Nam trên trường quốc tế\n- Cổ vũ phong trào đấu tranh giải phóng dân tộc trên thế giới')
c18 += 1

count += c18
print(f"  Khối 5 Lịch sử & Địa lý: {c18} câu")

# ============================================================
# TỰ NHIÊN VÀ XÃ HỘI - KHỐI 1, 2, 3 (mach=185, 186, 187)
# nd=206,208,210: Gia đình, Trường học, Cộng đồng
# nd=207,209,211: Thực vật, Động vật, Trái đất và Bầu trời
# ============================================================
c19 = 0

# Khối 1 - Tự nhiên & Xã hội
make_mcq(1, 14, 185, 206, 'Mức 1',
    'Trong gia đình, ai thường là người chăm sóc và nuôi dưỡng các con?',
    [('A','Ông bà'), ('B','Bố và mẹ'), ('C','Anh chị'), ('D','Hàng xóm')], 1)
c19 += 1

make_mcq(1, 14, 185, 207, 'Mức 1',
    'Cây cần gì để sống và phát triển? (Chọn yếu tố quan trọng nhất)',
    [('A','Chỉ cần đất'), ('B','Ánh sáng, nước và chất dinh dưỡng'), ('C','Chỉ cần ánh sáng'), ('D','Chỉ cần nước')], 1)
c19 += 1

make_tf(1, 14, 185, 207, 'Mức 1',
    'Đúng hay Sai?',
    [
        ('Mặt trời mọc ở hướng Đông', 'Đúng'),
        ('Tất cả động vật đều ăn thịt', 'Sai'),
        ('Cây xanh cần ánh sáng để quang hợp', 'Đúng'),
        ('Mưa là nước từ biển bay lên rồi tạo thành mây', 'Đúng'),
    ])
c19 += 1

# Khối 2 - Tự nhiên & Xã hội
make_mcq(2, 14, 186, 208, 'Mức 1',
    'Để giữ gìn sức khỏe, em cần làm gì mỗi ngày?',
    [
        ('A','Chỉ cần ăn nhiều'),
        ('B','Rửa tay trước khi ăn, đánh răng, tập thể dục'),
        ('C','Chỉ cần ngủ đủ giấc'),
        ('D','Không cần làm gì')
    ], 1)
c19 += 1

make_mcq(2, 14, 186, 209, 'Mức 2',
    'Bộ phận nào của cây hoa hấp thụ nước và muối khoáng từ đất?',
    [('A','Lá'), ('B','Thân'), ('C','Rễ'), ('D','Hoa')], 2)
c19 += 1

make_matching(2, 14, 186, 209, 'Mức 2',
    'Ghép bộ phận cây với chức năng tương ứng:',
    [
        ('Rễ', 'Hút nước và muối khoáng từ đất'),
        ('Thân', 'Dẫn nước và chất dinh dưỡng lên lá'),
        ('Lá', 'Quang hợp tạo chất hữu cơ nuôi cây'),
        ('Hoa', 'Thụ phấn, tạo quả và hạt'),
    ])
c19 += 1

# Khối 3 - Tự nhiên & Xã hội
make_mcq(3, 14, 187, 211, 'Mức 2',
    'Mặt trăng quay quanh Trái đất một vòng mất bao lâu?',
    [('A','7 ngày'), ('B','Khoảng 29-30 ngày'), ('C','365 ngày'), ('D','24 giờ')], 1)
c19 += 1

make_mcq(3, 14, 187, 211, 'Mức 2',
    'Nguyên nhân chính gây ra hiện tượng ngày và đêm là gì?',
    [
        ('A','Mặt trăng che khuất Mặt trời'),
        ('B','Trái đất tự quay quanh trục của nó'),
        ('C','Mặt trời quay quanh Trái đất'),
        ('D','Trái đất quay quanh Mặt trăng')
    ], 1)
c19 += 1

make_tf(3, 14, 187, 211, 'Mức 2',
    'Đúng hay Sai về Trái đất và bầu trời?',
    [
        ('Trái đất có hình cầu', 'Đúng'),
        ('Mặt trời là ngôi sao gần Trái đất nhất', 'Đúng'),
        ('Mặt trăng tự phát sáng như Mặt trời', 'Sai'),
        ('Trái đất quay quanh Mặt trời một vòng mất 365 ngày', 'Đúng'),
    ])
c19 += 1

make_essay(3, 14, 187, 210, 'Mức 3',
    'Em hãy nêu 3 quy tắc an toàn khi tham gia giao thông mà học sinh cần thực hiện.',
    '1. Đi bộ trên vỉa hè hoặc đi sát lề đường bên phải; quan sát kỹ trước khi qua đường\n2. Khi đi xe đạp: đội mũ bảo hiểm, đi đúng làn đường, không dàn hàng ngang\n3. Chấp hành đèn tín hiệu giao thông: đèn đỏ dừng lại, đèn xanh được đi\n4. Không đùa giỡn, không chạy nhảy dưới lòng đường\n5. Ngồi trên xe máy phải đội mũ bảo hiểm và ngồi đúng tư thế')
c19 += 1

count += c19
print(f"  Khối 1-3 Tự nhiên & Xã hội: {c19} câu")

# ============================================================
# THỐNG KÊ KHỐI 3 và KHỐI 5 (mach=163, 169)
# nd=170: Làm quen số liệu thống kê cơ bản (Khối 3)
# nd=180: Biểu đồ hình quạt tròn (Khối 5)
# ============================================================
c20 = 0

make_mcq(3, 1, 163, 170, 'Mức 2',
    'Bảng số liệu dưới đây ghi số học sinh vắng mặt trong tuần:\nThứ 2: 2, Thứ 3: 0, Thứ 4: 3, Thứ 5: 1, Thứ 6: 2\nNgày nào có nhiều học sinh vắng nhất?',
    [('A','Thứ 2'), ('B','Thứ 4'), ('C','Thứ 6'), ('D','Thứ 3')], 1)
c20 += 1

make_mcq(3, 1, 163, 170, 'Mức 2',
    'Cùng bảng số liệu trên, tổng số học sinh vắng trong tuần là bao nhiêu?',
    [('A','6'), ('B','7'), ('C','8'), ('D','9')], 2)
c20 += 1

make_mcq(5, 1, 169, 180, 'Mức 2',
    'Biểu đồ hình quạt tròn cho thấy: Học sinh thích Toán: 40%, thích Tiếng Việt: 30%, thích Khoa học: 20%, thích môn khác: 10%. Môn nào được học sinh yêu thích nhất?',
    [('A','Tiếng Việt'), ('B','Khoa học'), ('C','Toán'), ('D','Môn khác')], 2)
c20 += 1

make_mcq(5, 1, 169, 180, 'Mức 3',
    'Cùng biểu đồ trên, nếu lớp có 40 học sinh, có bao nhiêu em thích Tiếng Việt?',
    [('A','10 em'), ('B','12 em'), ('C','15 em'), ('D','20 em')], 1)
c20 += 1

make_essay(5, 1, 169, 180, 'Mức 3',
    'Một lớp học gồm 40 học sinh tham gia khảo sát về phương tiện đến trường:\n- Đi bộ: 8 học sinh\n- Xe đạp: 12 học sinh\n- Xe máy (ba mẹ chở): 16 học sinh\n- Xe buýt: 4 học sinh\n\nHãy tính tỉ lệ phần trăm của từng phương tiện và nhận xét về phương tiện phổ biến nhất.',
    'Tổng: 40 học sinh = 100%\n- Đi bộ: 8/40 × 100% = 20%\n- Xe đạp: 12/40 × 100% = 30%\n- Xe máy (ba mẹ chở): 16/40 × 100% = 40%\n- Xe buýt: 4/40 × 100% = 10%\n\nNhận xét: Phương tiện phổ biến nhất là xe máy (ba mẹ chở) chiếm 40%. Ít học sinh đi xe buýt nhất (10%). Đây phản ánh thực tế giao thông đô thị Việt Nam.')
c20 += 1

count += c20
print(f"  Thống kê Khối 3 & 5: {c20} câu")

# ============================================================
# TIẾNG VIỆT KHỐI 1 (mach=170, 171)
# nd=181: Âm, vần, thanh điệu
# nd=182: Đọc đoạn văn ngắn
# ============================================================
c21 = 0

make_mcq(1, 2, 170, 181, 'Mức 1',
    'Từ "bàn" có vần gì?',
    [('A','ban'), ('B','an'), ('C','àn'), ('D','bn')], 1)
c21 += 1

make_mcq(1, 2, 170, 181, 'Mức 1',
    'Tiếng "học" có âm đầu là gì?',
    [('A','h'), ('B','o'), ('C','oc'), ('D','k')], 0)
c21 += 1

make_mcq(1, 2, 170, 181, 'Mức 1',
    'Tiếng nào sau đây mang thanh hỏi?',
    [('A','bà'), ('B','bá'), ('C','bả'), ('D','bạ')], 2)
c21 += 1

make_mcq(1, 2, 170, 182, 'Mức 2',
    'Đọc câu sau và trả lời: "Mẹ đi chợ mua rau và cá." Mẹ mua những gì?',
    [('A','Rau và thịt'), ('B','Cá và tôm'), ('C','Rau và cá'), ('D','Rau và quả')], 2)
c21 += 1

make_tf(1, 2, 170, 181, 'Mức 1',
    'Đúng hay Sai về các tiếng sau đây?',
    [
        ('Tiếng "mẹ" có thanh huyền', 'Đúng'),
        ('Tiếng "bố" có thanh nặng', 'Sai'),
        ('Tiếng "có" có thanh sắc', 'Đúng'),
        ('Tiếng "cỏ" có thanh hỏi', 'Đúng'),
    ])
c21 += 1

count += c21
print(f"  Khối 1 Tiếng Việt: {c21} câu")

# ============================================================
# TIẾNG VIỆT KHỐI 5 (mach=184) - Đọc hiểu chuyên sâu
# nd=205: Đọc hiểu tác phẩm văn học có chiều sâu
# ============================================================
c22 = 0

make_mcq(5, 2, 184, 205, 'Mức 2',
    'Đọc đoạn trích:\n"Tre xanh, xanh tự bao giờ?\nChuyện ngày xưa... đã có bờ tre xanh\nThân gầy guộc, lá mong manh\nMà sao nên lũy nên thành tre ơi?\n(Nguyễn Duy - Tre Việt Nam)\nHình ảnh cây tre tượng trưng cho điều gì của người Việt Nam?',
    [
        ('A','Sự yếu đuối, mong manh'),
        ('B','Sức sống bền bỉ, tinh thần đoàn kết của dân tộc'),
        ('C','Sự nghèo nàn của đất nước'),
        ('D','Màu sắc thiên nhiên đẹp đẽ')
    ], 1)
c22 += 1

make_mcq(5, 2, 184, 205, 'Mức 3',
    'Trong truyện "Tấm Cám", sự biến hóa của Tấm (từ chim vàng anh → cây xoan đào → khung cửi → quả thị) thể hiện điều gì?',
    [
        ('A','Tấm là người có phép thuật'),
        ('B','Tấm là người may mắn'),
        ('C','Sức sống mãnh liệt và khát vọng hạnh phúc không bị dập tắt'),
        ('D','Thiên nhiên có thể biến hóa kỳ diệu')
    ], 2)
c22 += 1

make_essay(5, 2, 184, 205, 'Mức 3',
    'Đọc đoạn kết truyện "Chiếc lá cuối cùng" của O. Henry:\n"Bây giờ em có thể nói với chị điều này: Chiếc lá cuối cùng trên tường là tác phẩm của cụ Bơ-men. Cụ đã vẽ nó vào cái đêm chiếc lá thường xuân cuối cùng rụng xuống."\n\nEm cảm nhận được điều gì về nhân vật cụ Bơ-men qua chi tiết này? Liên hệ với bản thân em.',
    'Gợi ý:\n- Cụ Bơ-men là người họa sĩ già nghèo khổ nhưng có tấm lòng nhân ái cao cả\n- Cụ đã hi sinh tính mạng (ra ngoài trong đêm mưa gió lạnh để vẽ) để cứu Giôn-xi\n- Chiếc lá cuối cùng chính là "kiệt tác" mà cụ đã ấp ủ - không phải tranh đẹp mà là tình người\n- Bài học: tình yêu thương và lòng hi sinh có thể cứu sống người khác\n- Liên hệ bản thân: mỗi học sinh cũng có thể làm điều tốt, dù nhỏ, để giúp đỡ người xung quanh')
c22 += 1

count += c22
print(f"  Khối 5 TV Đọc hiểu nâng cao: {c22} câu")

# ============================================================
# THỐNG KÊ CUỐI CÙNG
# ============================================================
print(f"\n{'='*50}")
print(f"TỔNG CỘNG: {count} câu hỏi đã được tạo")
print('='*50)

# Kiểm tra lại
from question_bank.models import CauHoi, DapAn
total_q = CauHoi.objects.count()
total_a = DapAn.objects.count()
no_answer = CauHoi.objects.filter(dap_ans__isnull=True, DapAnMau__isnull=True).count()
essay_with_dapan = CauHoi.objects.filter(DangCauHoi__startswith='Essay').exclude(DapAnMau='').exclude(DapAnMau__isnull=True).count()

print(f"\nKiểm tra database:")
print(f"  Tổng câu hỏi: {total_q}")
print(f"  Tổng đáp án (bản ghi DapAn): {total_a}")
print(f"  Essay có DapAnMau: {essay_with_dapan}")
print(f"  Câu hỏi không có DapAn và DapAnMau: {no_answer}")

from django.db.models import Count
print("\nPhân bố theo dạng câu hỏi:")
for row in CauHoi.objects.values('DangCauHoi').annotate(n=Count('id')).order_by('-n'):
    print(f"  {row['DangCauHoi']}: {row['n']}")

print("\nPhân bố theo mức độ:")
for row in CauHoi.objects.values('MucDo').annotate(n=Count('id')).order_by('MucDo'):
    print(f"  {row['MucDo']}: {row['n']}")
