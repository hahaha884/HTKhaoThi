import io
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

CAUSO_REGEX = re.compile(r'^[1-9]\d*(,[1-9]\d*)*$')

def validate_matrix_data(header_data, details_data, action='submit', existing_matran_id=None):
    """
    Thực hiện kiểm tra tính hợp lệ của Ma trận và Chi tiết ma trận theo các Use Case 9.1 và 9.2.
    Trả về dict:
    {
        'is_valid': bool,
        'errors': list of str,
        'row_errors': dict of {row_index: list of str},
        'level_errors': list of str,
        'calc_summary': dict
    }
    """
    errors = []
    row_errors = {}
    level_errors = []
    
    # 1. Kiểm tra thông tin Header (9a, 8a, 9b)
    ten_matran = (header_data.get('TenMaTran') or '').strip()
    nam_hoc_id = header_data.get('NamHoc')
    hoc_ky = header_data.get('HocKy')
    ky_thi = header_data.get('KyThi')
    khoi_id = header_data.get('Khoi')
    mon_hoc_id = header_data.get('MonHoc')
    
    # 9a / 8a: Thiếu thông tin bắt buộc
    required_headers = [
        ('Tên ma trận', ten_matran),
        ('Năm học', nam_hoc_id),
        ('Học kỳ', hoc_ky),
        ('Kỳ thi', ky_thi),
        ('Khối', khoi_id),
        ('Môn học', mon_hoc_id),
    ]
    missing_headers = [name for name, val in required_headers if not val]
    if missing_headers:
        errors.append("Vui lòng nhập đầy đủ các thông tin bắt buộc.")
            
    # 9b. Ma trận đã tồn tại
    if nam_hoc_id and hoc_ky and ky_thi and khoi_id and mon_hoc_id:
        from .models import MaTran
        query = MaTran.objects.filter(
            NamHoc_id=nam_hoc_id,
            HocKy=hoc_ky,
            KyThi=ky_thi,
            Khoi_id=khoi_id,
            MonHoc_id=mon_hoc_id
        )
        if existing_matran_id:
            query = query.exclude(pk=existing_matran_id)
        if query.exists():
            existing = query.first()
            errors.append(f"Ma trận đã tồn tại (Được tạo bởi {existing.NguoiTao.HoTen} - Trạng thái: {existing.TrangThai}).")

    num_rows = len(details_data)
    
    # Bắt buộc phải có ít nhất 1 dòng chi tiết (9a)
    if num_rows == 0:
        errors.append("Vui lòng thêm ít nhất một dòng chi tiết ma trận.")
        return {
            'is_valid': False,
            'errors': errors,
            'row_errors': row_errors,
            'level_errors': level_errors,
            'calc_summary': {
                'tong_so_cau': 0,
                'tong_diem': 0.0,
                'tong_tyle': 0.0,
                'muc_do': {'Mức 1': {'cau': 0, 'diem': 0.0, 'tyle': 0.0, 'tyle_thucte': 0.0, 'diff': 0.0},
                           'Mức 2': {'cau': 0, 'diem': 0.0, 'tyle': 0.0, 'tyle_thucte': 0.0, 'diff': 0.0},
                           'Mức 3': {'cau': 0, 'diem': 0.0, 'tyle': 0.0, 'tyle_thucte': 0.0, 'diff': 0.0}}
            }
        }
        errors.append("Vui lòng thêm ít nhất một dòng chi tiết ma trận.")
        return {
            'is_valid': False,
            'errors': errors,
            'row_errors': row_errors,
            'level_errors': level_errors,
            'calc_summary': {}
        }

    # Tính toán chi tiết
    seen_combinations = {}  # comb -> list of row indices
    all_causos = {}         # causo_num -> row_index
    
    tong_so_cau = 0
    tong_diem = 0.0
    tong_tyle = 0.0
    
    muc_do_stats = {
        'Mức 1': {'cau': 0, 'diem': 0.0, 'tyle': 0.0, 'tyle_thucte': 0.0, 'diff': 0.0},
        'Mức 2': {'cau': 0, 'diem': 0.0, 'tyle': 0.0, 'tyle_thucte': 0.0, 'diff': 0.0},
        'Mức 3': {'cau': 0, 'diem': 0.0, 'tyle': 0.0, 'tyle_thucte': 0.0, 'diff': 0.0},
    }

    has_detail_errors = False

    for idx, row in enumerate(details_data):
        row_num = idx + 1
        current_row_errs = []
        
        mach_id = row.get('MachKienThuc')
        noidung_id = row.get('NoiDung')
        mucdo = (row.get('MucDo') or '').strip()
        loai = (row.get('LoaiCauHoi') or '').strip()
        soluong_raw = row.get('SoLuongCau')
        causo_raw = (str(row.get('CauSo') or '')).strip()
        diem_raw = row.get('Diem')
        tyle_raw = row.get('TyLe')
        

        # 9c: Thiếu thông tin bắt buộc trên dòng
        if not all([mach_id, noidung_id, mucdo, loai, soluong_raw is not None and str(soluong_raw) != '', causo_raw, diem_raw is not None and str(diem_raw) != '', tyle_raw is not None and str(tyle_raw) != '']):
            current_row_errs.append("Thiếu thông tin bắt buộc.")
            has_detail_errors = True
            row_errors[idx] = current_row_errs
            continue
            
        # 9c: Định dạng số lượng câu
        try:
            sl = int(soluong_raw)
            if sl <= 0:
                current_row_errs.append("Số lượng câu phải là số nguyên dương (> 0).")
                has_detail_errors = True
        except (ValueError, TypeError):
            current_row_errs.append("Số lượng câu sai định dạng số.")
            has_detail_errors = True
            sl = 0

        # 9c: Điểm
        try:
            diem = float(diem_raw)
            if diem <= 0:
                current_row_errs.append("Điểm phải lớn hơn 0.")
                has_detail_errors = True
        except (ValueError, TypeError):
            current_row_errs.append("Điểm sai định dạng số.")
            has_detail_errors = True
            diem = 0.0

        # 9j: Tỷ lệ (%)
        try:
            tyle = float(tyle_raw)
            if tyle <= 0 or tyle > 100:
                current_row_errs.append("Tỷ lệ (%) không hợp lệ (phải từ 0.1% đến 100%).")
                has_detail_errors = True
        except (ValueError, TypeError):
            current_row_errs.append("Tỷ lệ (%) sai định dạng số.")
            has_detail_errors = True
            tyle = 0.0

        # 9h: Kiểm tra Câu số không hợp lệ
        # Trường Câu số: một hoặc nhiều số nguyên dương, phân tách bằng dấu phẩy
        if not CAUSO_REGEX.match(causo_raw):
            current_row_errs.append("Câu số không hợp lệ (Chứa ký tự không phải số, số âm, số thập phân, hoặc sai dấu phân tách).")
            has_detail_errors = True
            cau_items = []
        else:
            cau_items = [c.strip() for c in causo_raw.split(',') if c.strip()]
            
            # Kiểm tra trùng câu số ngay trong dòng
            if len(cau_items) != len(set(cau_items)):
                current_row_errs.append("Câu số trong cùng một dòng không được trùng lặp.")
                has_detail_errors = True
                
            # 9i: Số lượng câu không khớp Câu số
            if sl > 0 and len(cau_items) != sl:
                current_row_errs.append(f"Số lượng câu ({sl}) phải bằng số lượng Câu số đã khai báo ({len(cau_items)}).")
                has_detail_errors = True
                
            # 9f: Câu số bị trùng giữa các dòng
            for c_num in cau_items:
                if c_num in all_causos:
                    prev_row = all_causos[c_num] + 1
                    current_row_errs.append(f"Câu số {c_num} đã tồn tại trong ma trận (trùng với dòng {prev_row}).")
                    has_detail_errors = True
                else:
                    all_causos[c_num] = idx

        # 9e: Trùng dòng chi tiết ma trận (Mạch + Nội dung + Mức độ + Loại câu hỏi)
        comb_key = (str(mach_id), str(noidung_id), mucdo, loai)
        if comb_key in seen_combinations:
            prev_row = seen_combinations[comb_key] + 1
            current_row_errs.append(f"Chi tiết ma trận bị trùng tổ hợp với dòng {prev_row}.")
            has_detail_errors = True
        else:
            seen_combinations[comb_key] = idx

        if current_row_errs:
            row_errors[idx] = current_row_errs

        # Tích lũy cho ma trận
        tong_so_cau += sl
        tong_diem += diem
        tong_tyle += tyle
        
        if mucdo in muc_do_stats:
            muc_do_stats[mucdo]['cau'] += sl
            muc_do_stats[mucdo]['diem'] += diem
            muc_do_stats[mucdo]['tyle'] += tyle

    if has_detail_errors:
        errors.append("Thông tin chi tiết ma trận không hợp lệ. Vui lòng kiểm tra các dòng bị đánh dấu đỏ.")

    # Kiểm tra toàn diện 9d, 9g, 9k:
    # 9g: Tổng tỷ lệ không hợp lệ (phải bằng 100%)
    if abs(tong_tyle - 100.0) > 0.01:
        errors.append(f"Tổng tỷ lệ của ma trận phải bằng 100% (Hiện tại: {round(tong_tyle, 1)}%).")

    # 9d: Tổng điểm của ma trận bắt buộc phải bằng 10.0 điểm
    if abs(tong_diem - 10.0) > 0.01:
        errors.append(f"Tổng điểm của ma trận phải bằng 10 điểm (Hiện tại: {round(tong_diem, 2)}đ).")
    if tong_so_cau <= 0:
        errors.append("Tổng số câu hoặc tổng điểm của ma trận chưa đúng quy định (Tổng số câu phải lớn hơn 0).")

    # Tỷ lệ theo mức độ: Tính theo tổng điểm và làm tròn hàng chục (không áp ngưỡng ±5%)
    if tong_diem > 0:
        for muc, data in muc_do_stats.items():
            pct = (data['diem'] / tong_diem) * 100
            data['tyle_thucte'] = round(pct, 1)
            data['tyle_lamtron'] = int(round(pct / 10) * 10)

    # Cập nhật tỷ lệ thực tế và làm tròn hàng chục cho calc_summary (dù draft hay submit)
    if tong_diem > 0:
        for muc, data in muc_do_stats.items():
            pct = (data['diem'] / tong_diem) * 100
            data['tyle_thucte'] = round(pct, 1)
            data['tyle_lamtron'] = int(round(pct / 10) * 10)
            data['diff'] = round(abs(data['tyle_thucte'] - data['tyle']), 1)


    calc_summary = {
        'tong_so_cau': tong_so_cau,
        'tong_diem': round(tong_diem, 2),
        'tong_tyle': round(tong_tyle, 1),
        'muc_do': muc_do_stats
    }

    return {
        'is_valid': len(errors) == 0 and len(row_errors) == 0,
        'errors': errors,
        'row_errors': row_errors,
        'level_errors': level_errors,
        'calc_summary': calc_summary
    }

def set_cell_background(cell, hex_color):
    """Đặt màu nền cho ô trong table python-docx"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Đặt padding cho ô trong bảng python-docx"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def generate_matrix_docx(matran):
    """
    Sinh tài liệu Word (.docx) chuyên nghiệp cho Ma trận đề thi.
    Đầy đủ thông tin:
    - Tiêu đề trường & Phòng GD&ĐT
    - Thông tin chung
    - Bảng ma trận đề thi
    - Bảng thống kê theo mức độ nhận thức
    - Chữ ký
    """
    doc = Document()

    # Thiết lập lề trang chuẩn (lề trên, dưới: 2cm, trái: 2.5cm, phải: 2cm)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.8)

    # 1. Header (Cơ quan chủ quản & Quốc hiệu)
    header_table = doc.add_table(rows=2, cols=2)
    header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_table.autofit = False
    header_table.columns[0].width = Inches(3.2)
    header_table.columns[1].width = Inches(3.6)

    # Cột trái
    p_cq = header_table.cell(0, 0).paragraphs[0]
    p_cq.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_cq = p_cq.add_run("PHÒNG GD&ĐT QUẬN/HUYỆN\nTRƯỜNG TIỂU HỌC ĐẶNG VĂN NGỮ")
    run_cq.font.name = "Times New Roman"
    run_cq.font.size = Pt(11)
    run_cq.bold = True

    p_line_left = header_table.cell(1, 0).paragraphs[0]
    p_line_left.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ll = p_line_left.add_run("--------------------")
    r_ll.font.name = "Times New Roman"
    r_ll.font.size = Pt(9)

    # Cột phải
    p_qh = header_table.cell(0, 1).paragraphs[0]
    p_qh.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_qh = p_qh.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc")
    run_qh.font.name = "Times New Roman"
    run_qh.font.size = Pt(11)
    run_qh.bold = True

    p_line_right = header_table.cell(1, 1).paragraphs[0]
    p_line_right.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_lr = p_line_right.add_run("--------------------")
    r_lr.font.name = "Times New Roman"
    r_lr.font.size = Pt(9)

    doc.add_paragraph()  # khoảng cách

    # 2. Tiêu đề ma trận
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("MA TRẬN ĐỀ THI")
    run_title.font.name = "Times New Roman"
    run_title.font.size = Pt(16)
    run_title.bold = True
    run_title.font.color.rgb = RGBColor(0, 51, 102)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run(f"TÊN: {matran.TenMaTran.upper()}")
    run_sub.font.name = "Times New Roman"
    run_sub.font.size = Pt(13)
    run_sub.bold = True

    # 3. Thông tin chung
    info_table = doc.add_table(rows=3, cols=2)
    info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    info_table.columns[0].width = Inches(3.4)
    info_table.columns[1].width = Inches(3.4)

    def set_info(row, col, label, val):
        p = info_table.cell(row, col).paragraphs[0]
        p.paragraph_format.line_spacing = 1.2
        r_lbl = p.add_run(f"- {label}: ")
        r_lbl.font.name = "Times New Roman"
        r_lbl.font.size = Pt(11)
        r_lbl.bold = True
        r_val = p.add_run(str(val or '-'))
        r_val.font.name = "Times New Roman"
        r_val.font.size = Pt(11)

    set_info(0, 0, "Năm học", matran.NamHoc.TenNamHoc if matran.NamHoc else "-")
    set_info(0, 1, "Học kỳ & Kỳ thi", f"{matran.HocKy or '-'} ({matran.KyThi or '-'})")
    set_info(1, 0, "Khối lớp", matran.Khoi.TenKhoi if matran.Khoi else "-")
    set_info(1, 1, "Môn học", matran.MonHoc.TenMon if matran.MonHoc else "-")
    set_info(2, 0, "Người tạo", matran.NguoiTao.HoTen if matran.NguoiTao else "-")
    set_info(2, 1, "Trạng thái", matran.TrangThai)

    doc.add_paragraph()

    # 4. Bảng chi tiết ma trận
    table_headers = [
        ("STT", Inches(0.4)),
        ("Mạch kiến thức", Inches(1.3)),
        ("Nội dung kiến thức", Inches(1.5)),
        ("Mức độ", Inches(0.7)),
        ("Loại", Inches(0.8)),
        ("Số câu", Inches(0.6)),
        ("Câu số", Inches(0.8)),
        ("Điểm", Inches(0.6)),
        ("Tỷ lệ", Inches(0.6)),
    ]

    chi_tiet_list = list(matran.chi_tiet.all())
    matrix_table = doc.add_table(rows=len(chi_tiet_list) + 2, cols=len(table_headers))
    matrix_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    matrix_table.style = 'Table Grid'

    # Format Header Row
    hdr_cells = matrix_table.rows[0].cells
    for i, (head_text, width) in enumerate(table_headers):
        hdr_cells[i].width = width
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(head_text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.bold = True
        set_cell_background(hdr_cells[i], "D9E1F2")
        set_cell_margins(hdr_cells[i], top=80, bottom=80, left=80, right=80)

    # Format Data Rows
    for idx, ct in enumerate(chi_tiet_list):
        row_cells = matrix_table.rows[idx + 1].cells
        
        row_data = [
            (str(idx + 1), WD_ALIGN_PARAGRAPH.CENTER),
            (ct.MachKienThuc.TenMach if ct.MachKienThuc else "-", WD_ALIGN_PARAGRAPH.LEFT),
            (ct.NoiDung.TenNoidung if ct.NoiDung else "-", WD_ALIGN_PARAGRAPH.LEFT),
            (ct.MucDo, WD_ALIGN_PARAGRAPH.CENTER),
            (ct.LoaiCauHoi, WD_ALIGN_PARAGRAPH.CENTER),
            (str(ct.SoLuongCau), WD_ALIGN_PARAGRAPH.CENTER),
            (ct.CauSo or "-", WD_ALIGN_PARAGRAPH.CENTER),
            (str(ct.Diem), WD_ALIGN_PARAGRAPH.CENTER),
            (f"{ct.TyLe}%", WD_ALIGN_PARAGRAPH.CENTER),
        ]
        
        for c_idx, (text, align) in enumerate(row_data):
            row_cells[c_idx].width = table_headers[c_idx][1]
            p = row_cells[c_idx].paragraphs[0]
            p.alignment = align
            r = p.add_run(text)
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            set_cell_margins(row_cells[c_idx], top=60, bottom=60, left=60, right=60)
            if idx % 2 == 1:
                set_cell_background(row_cells[c_idx], "F2F2F2")

    # Format Footer Row (Tổng cộng)
    foot_row = matrix_table.rows[-1].cells
    foot_data = [
        ("TỔNG CỘNG", WD_ALIGN_PARAGRAPH.CENTER, 5),  # gộp 5 cột đầu
        (str(matran.TongSoCau), WD_ALIGN_PARAGRAPH.CENTER, 1),
        ("", WD_ALIGN_PARAGRAPH.CENTER, 1),
        (f"{matran.TongSoDiem}đ", WD_ALIGN_PARAGRAPH.CENTER, 1),
        ("100%", WD_ALIGN_PARAGRAPH.CENTER, 1),
    ]

    # Gộp 5 cột đầu
    a = foot_row[0]
    b = foot_row[4]
    a.merge(b)
    p_tot = a.paragraphs[0]
    p_tot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_tot = p_tot.add_run("TỔNG CỘNG:  ")
    r_tot.font.name = "Times New Roman"
    r_tot.font.size = Pt(10)
    r_tot.bold = True
    set_cell_background(a, "EAEAEA")

    # Cột Tổng câu
    p_c = foot_row[5].paragraphs[0]
    p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_c = p_c.add_run(f"{matran.TongSoCau}")
    r_c.font.name = "Times New Roman"
    r_c.font.size = Pt(10)
    r_c.bold = True
    set_cell_background(foot_row[5], "EAEAEA")

    # Cột trống Câu số
    set_cell_background(foot_row[6], "EAEAEA")

    # Cột Tổng điểm
    p_d = foot_row[7].paragraphs[0]
    p_d.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_d = p_d.add_run(f"{matran.TongSoDiem}")
    r_d.font.name = "Times New Roman"
    r_d.font.size = Pt(10)
    r_d.bold = True
    set_cell_background(foot_row[7], "EAEAEA")

    # Cột Tổng tỷ lệ
    p_t = foot_row[8].paragraphs[0]
    p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t = p_t.add_run("100%")
    r_t.font.name = "Times New Roman"
    r_t.font.size = Pt(10)
    r_t.bold = True
    set_cell_background(foot_row[8], "EAEAEA")

    doc.add_paragraph()

    # 5. Bảng thống kê theo mức độ nhận thức
    p_tk = doc.add_paragraph()
    r_tk = p_tk.add_run("BẢNG THỐNG KÊ THEO MỨC ĐỘ NHẬN THỨC:")
    r_tk.font.name = "Times New Roman"
    r_tk.font.size = Pt(11)
    r_tk.bold = True

    stats_table = doc.add_table(rows=5, cols=5)
    stats_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    stats_table.style = 'Table Grid'
    stats_headers = ["Mức độ", "Số câu", "Tổng điểm", "Tỷ lệ khai báo", "Tỷ lệ làm tròn (Hàng chục)"]
    
    for i, h in enumerate(stats_headers):
        c = stats_table.rows[0].cells[i]
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.bold = True
        set_cell_background(c, "E2EFDA")
        set_cell_margins(c, 60, 60, 60, 60)

    # Thống kê data
    muc_cau = {'Mức 1': 0, 'Mức 2': 0, 'Mức 3': 0}
    muc_diem = {'Mức 1': 0.0, 'Mức 2': 0.0, 'Mức 3': 0.0}
    muc_tyle = {'Mức 1': 0.0, 'Mức 2': 0.0, 'Mức 3': 0.0}
    for ct in chi_tiet_list:
        if ct.MucDo in muc_cau:
            muc_cau[ct.MucDo] += ct.SoLuongCau
            muc_diem[ct.MucDo] += ct.Diem
            muc_tyle[ct.MucDo] += ct.TyLe

    levels = ['Mức 1', 'Mức 2', 'Mức 3']
    for idx, lvl in enumerate(levels):
        r_cells = stats_table.rows[idx + 1].cells
        thuc_te_pct = (muc_diem[lvl] / matran.TongSoDiem * 100) if matran.TongSoDiem > 0 else 0
        lamtron_pct = int(round(thuc_te_pct / 10) * 10)
        vals = [lvl, str(muc_cau[lvl]), f"{round(muc_diem[lvl], 2)}đ", f"{round(muc_tyle[lvl], 1)}%", f"{lamtron_pct}%"]
        for c_idx, val in enumerate(vals):
            p = r_cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            set_cell_margins(r_cells[c_idx], 50, 50, 50, 50)

    # Hàng tổng bảng thống kê
    tot_cells = stats_table.rows[4].cells
    tot_vals = ["TỔNG", str(matran.TongSoCau), f"{matran.TongSoDiem}đ", "100%", "100%"]
    for c_idx, val in enumerate(tot_vals):
        p = tot_cells[c_idx].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(val)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.bold = True
        set_cell_background(tot_cells[c_idx], "F2F2F2")

    doc.add_paragraph()
    doc.add_paragraph()

    # 6. Phần chữ ký xác nhận
    sign_table = doc.add_table(rows=3, cols=3)
    sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sign_table.columns[0].width = Inches(2.2)
    sign_table.columns[1].width = Inches(2.3)
    sign_table.columns[2].width = Inches(2.3)

    signs = [
        ("NGƯỜI LẬP MA TRẬN", "(Ký và ghi rõ họ tên)", matran.NguoiTao.HoTen if matran.NguoiTao else ""),
        ("TỔ TRƯỞNG CHUYÊN MÔN", "(Ký và ghi rõ họ tên)", ""),
        ("BAN GIÁM HIỆU", "(Ký, đóng dấu)", "")
    ]

    for c_idx, (role, note, name) in enumerate(signs):
        p0 = sign_table.cell(0, c_idx).paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(role)
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(11)
        r0.bold = True

        p1 = sign_table.cell(1, c_idx).paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p1.add_run(f"\n\n\n\n{note}")
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(9)
        r1.italic = True

        if name:
            p2 = sign_table.cell(2, c_idx).paragraphs[0]
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r2 = p2.add_run(f"\n{name}")
            r2.font.name = "Times New Roman"
            r2.font.size = Pt(11)
            r2.bold = True

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

