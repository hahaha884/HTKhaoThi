import os
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

os.makedirs('media/templates', exist_ok=True)

document = Document()

# Tiêu đề
p = document.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("TRƯỜNG TIỂU HỌC SỐ 1 AN ĐÔNG\n")
run.bold = True
run.font.size = Pt(13)

run2 = p.add_run("KIỂM TRA ĐỊNH KÌ {{ ky_thi }} NĂM HỌC {{ nam_hoc }}\n")
run2.bold = True
run2.font.size = Pt(13)

run3 = p.add_run("MÔN: {{ mon_hoc }} - KHỐI {{ khoi }}\n")
run3.bold = True
run3.font.size = Pt(13)

run4 = p.add_run("Thời gian: {{ thoi_gian }} phút\nNgày thi: {{ ngay_thi_str }}")
run4.font.size = Pt(12)

document.add_paragraph()

# Bảng điểm
table = document.add_table(rows=4, cols=4)
table.style = 'Table Grid'
cell_00 = table.cell(0, 0)
cell_10 = table.cell(1, 0)
cell_00.merge(cell_10)
cell_00.text = "Họ và tên:...........................................................\nLớp:........................................................................."

cell_01 = table.cell(0, 1)
cell_02 = table.cell(0, 2)
cell_03 = table.cell(0, 3)
cell_01.merge(cell_02)
cell_01.text = "Giám thị"
cell_03.text = "Giám khảo"

table.cell(1, 1).merge(table.cell(1, 2))
table.cell(1, 1).text = "\n\n"
table.cell(1, 3).text = "\n\n"

table.cell(2, 0).text = "Điểm"
table.cell(2, 1).text = "Điểm đọc"
table.cell(2, 2).text = "Điểm viết"
table.cell(2, 3).text = "Nhận xét của giáo viên"

table.cell(3, 0).text = "\n\n\n"
table.cell(3, 1).text = "\n\n\n"
table.cell(3, 2).text = "\n\n\n"
table.cell(3, 3).text = "\n\n\n"

document.add_paragraph()

# Vòng lặp câu hỏi
document.add_paragraph("{% for q in questions %}")
p = document.add_paragraph("Câu {{ q.thu_tu }} ({{ q.diem }} điểm). {{ q.noi_dung }}")
p = document.add_paragraph("{{ q.dap_ans }}")
document.add_paragraph("{% endfor %}")

document.add_page_break()

# Đáp án
p = document.add_paragraph("HƯỚNG DẪN CHẤM")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

document.add_paragraph("{% for q in questions %}")
p = document.add_paragraph("Câu {{ q.thu_tu }}: {{ q.dap_an_dung }}")
document.add_paragraph("{% endfor %}")

document.save('media/templates/dethi_template.docx')
print("Created media/templates/dethi_template.docx successfully.")
