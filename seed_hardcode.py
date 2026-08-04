import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import MonHoc, Khoi
from question_bank.models import MachKienThuc, NoiDungKienThuc

curriculum = {
    "Toán": {
        "1": {
            "Số và Phép tính": [
                "Số đếm đến 10. Phép cộng, trừ trong phạm vi 10.",
                "Đọc, viết, so sánh số đến 100. Cộng, trừ không nhớ trong phạm vi 100."
            ],
            "Hình học và Đo lường": [
                "Nhận diện hình vuông, hình tròn, hình tam giác.",
                "Đo độ dài (cm), xem giờ đúng."
            ]
        },
        "2": {
            "Số và Phép tính": [
                "Cộng, trừ có nhớ trong phạm vi 100. Làm quen với phép nhân, phép chia (bảng 2, 5).",
                "Số đến 1.000. Phép cộng, trừ trong phạm vi 1.000."
            ],
            "Hình học và Đo lường": [
                "Khối trụ, khối cầu. Đo lường (kg, lít)."
            ],
            "Thống kê và Xác suất": [
                "Làm quen với biểu đồ tranh."
            ]
        },
        "3": {
            "Số và Phép tính": [
                "Số đến 10.000. Bảng nhân, bảng chia từ 3 đến 9. Tính giá trị biểu thức.",
                "Số đến 100.000. Phép cộng, trừ, nhân, chia (có dư và không dư) trong phạm vi 100.000."
            ],
            "Hình học và Đo lường": [
                "Góc vuông, góc không vuông.",
                "Tính chu vi, diện tích hình chữ nhật, hình vuông."
            ],
            "Thống kê và Xác suất": [
                "Làm quen số liệu thống kê cơ bản."
            ]
        },
        "4": {
            "Số và Phép tính": [
                "Số có nhiều chữ số. Trung bình cộng. Các tính chất của phép cộng/nhân.",
                "Phân số và các phép tính với phân số."
            ],
            "Hình học và Đo lường": [
                "Góc bẹt, góc nhọn, góc tù. Đường thẳng song song/vuông góc.",
                "Hình bình hành, hình thoi."
            ],
            "Thống kê và Xác suất": [
                "Biểu đồ cột."
            ]
        },
        "5": {
            "Số và Phép tính": [
                "Phân số thập phân, Hỗn số. Đọc, viết, tính toán với Số thập phân. Tỉ số phần trăm.",
                "Toán chuyển động đều (Vận tốc, Quãng đường, Thời gian)."
            ],
            "Hình học và Đo lường": [
                "Hình tam giác, hình thang.",
                "Thể tích hình hộp chữ nhật, hình lập phương."
            ],
            "Thống kê và Xác suất": [
                "Biểu đồ hình quạt tròn."
            ]
        }
    },
    "Tiếng Việt": {
        "1": {
            "Đọc": [
                "Âm, Vần, Thanh điệu. Ghép vần, đọc trơn tiếng/từ khóa.",
                "Đọc trơn đoạn văn, bài thơ ngắn. Trả lời câu hỏi đọc hiểu đơn giản."
            ],
            "Viết": [
                "Viết đúng chữ cái và tiếng vừa học.",
                "Viết chính tả (nhìn - chép) các đoạn ngắn."
            ]
        },
        "2": {
            "Đọc": [
                "Đọc hiểu các văn bản kể chuyện, miêu tả ngắn."
            ],
            "Kiến thức tiếng Việt & Văn học": [
                "Luyện từ và câu (từ chỉ sự vật, hoạt động, đặc điểm; câu kiểu Ai là gì, Ai làm gì).",
                "Mở rộng vốn từ theo chủ đề (Thiên nhiên, Đất nước...)."
            ],
            "Viết": [
                "Viết đoạn văn ngắn (4 - 7 câu) miêu tả đồ vật, kể việc làm.",
                "Viết thư, viết đoạn văn nêu tình cảm, cảm xúc hoặc nêu ý kiến đơn giản."
            ]
        },
        "3": {
            "Đọc": [
                "Đọc hiểu các văn bản kể chuyện, miêu tả ngắn."
            ],
            "Kiến thức tiếng Việt & Văn học": [
                "Nhận biết biện pháp nhân hóa, so sánh.",
                "Mở rộng vốn từ theo chủ đề (Thiên nhiên, Đất nước...)."
            ],
            "Viết": [
                "Viết đoạn văn ngắn (4 - 7 câu) miêu tả đồ vật, kể việc làm.",
                "Viết thư, viết đoạn văn nêu tình cảm, cảm xúc hoặc nêu ý kiến đơn giản."
            ]
        },
        "4": {
            "Đọc": [
                "Đọc hiểu văn bản dài."
            ],
            "Kiến thức tiếng Việt & Văn học": [
                "Danh từ, Động từ, Tính từ.",
                "Trạng ngữ."
            ],
            "Viết": [
                "Luyện tập viết bài văn kể chuyện (có cốt truyện, nhân vật), văn miêu tả (cây cối, con vật).",
                "Viết thư, viết báo cáo, tóm tắt tin tức."
            ],
            "Nói và Nghe": [
                "Luyện nói và nghe qua tranh luận, thuyết trình nhóm."
            ]
        },
        "5": {
            "Kiến thức tiếng Việt & Văn học": [
                "Đại từ, Quan hệ từ, Từ đồng nghĩa, trái nghĩa, đồng âm.",
                "Ôn tập tổng hợp về câu (câu đơn, câu ghép)."
            ],
            "Viết": [
                "Viết bài văn miêu tả cảnh, tả người.",
                "Viết bài văn thuyết minh, viết chương trình hoạt động."
            ],
            "Đọc": [
                "Đọc hiểu các tác phẩm văn học có chiều sâu về ý nghĩa nhân văn, lịch sử."
            ]
        }
    },
    "Tự nhiên và Xã hội": {
        "1": {
            "Chung": ["Gia đình, Trường học, Cộng đồng địa phương. Các thói quen vệ sinh, an toàn.", "Thực vật, Động vật, Trái đất và Bầu trời. Chăm sóc sức khỏe bản thân."]
        },
        "2": {
            "Chung": ["Gia đình, Trường học, Cộng đồng địa phương. Các thói quen vệ sinh, an toàn.", "Thực vật, Động vật, Trái đất và Bầu trời. Chăm sóc sức khỏe bản thân."]
        },
        "3": {
            "Chung": ["Gia đình, Trường học, Cộng đồng địa phương. Các thói quen vệ sinh, an toàn.", "Thực vật, Động vật, Trái đất và Bầu trời. Chăm sóc sức khỏe bản thân."]
        }
    },
    "Khoa học": {
        "4": {
            "Chung": ["Trao đổi chất (Người, Thực vật, Động vật). Nước, Không khí, Âm thanh, Ánh sáng.", "Vật chất và Năng lượng (Nhiệt, Điện). Sự sinh sản. Môi trường và tài nguyên."]
        },
        "5": {
            "Chung": ["Trao đổi chất (Người, Thực vật, Động vật). Nước, Không khí, Âm thanh, Ánh sáng.", "Vật chất và Năng lượng (Nhiệt, Điện). Sự sinh sản. Môi trường và tài nguyên."]
        }
    },
    "Lịch sử và Địa lý": {
        "4": {
            "Chung": ["Lịch sử địa phương, các triều đại cổ - trung đại. Địa lý tự nhiên, dân cư Việt Nam.", "Lịch sử cận - hiện đại (chống Pháp, Mỹ)."]
        },
        "5": {
            "Chung": ["Lịch sử địa phương, các triều đại cổ - trung đại. Địa lý tự nhiên, dân cư Việt Nam.", "Lịch sử cận - hiện đại (chống Pháp, Mỹ). Địa lý các châu lục và thế giới."]
        }
    }
}

MachKienThuc.objects.all().delete()
NoiDungKienThuc.objects.all().delete()

for mon_ten, khoi_dict in curriculum.items():
    mon, _ = MonHoc.objects.get_or_create(TenMon=mon_ten)
    for khoi_ten, mach_dict in khoi_dict.items():
        khoi, _ = Khoi.objects.get_or_create(TenKhoi=f"Khối {khoi_ten}")
        mon.KhoiApDung.add(khoi)
        
        for mach_ten, noidungs in mach_dict.items():
            mach = MachKienThuc.objects.create(MonHoc=mon, Khoi=khoi, TenMach=mach_ten)
            for nd_ten in noidungs:
                NoiDungKienThuc.objects.create(MachKienThuc=mach, TenNoidung=nd_ten)
