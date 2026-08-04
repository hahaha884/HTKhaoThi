import random
from collections import defaultdict
from django.db.models import Q
from core.models import GiaoVien, LopHoc, Khoi
from .models import PhanCongGiamThi, LichThi

def auto_assign_invigilators(lich_thi_list):
    """
    Thuật toán phân công tự động (Constraint Satisfaction Problem - Backtracking)
    Hỗ trợ tìm phương án phân công tối ưu (best-effort) nếu không thể phân công đầy đủ
    cho tất cả các lớp do thiếu giáo viên thỏa mãn các ràng buộc.
    """
    results = []
    errors = []
    
    all_teachers = list(GiaoVien.objects.filter(
        TrangThai='Đang hoạt động'
    ).exclude(
        ChucVu__in=['Hiệu trưởng', 'Phó hiệu trưởng', 'Nhân viên văn thư', 'Admin/Giáo vụ']
    ).prefetch_related('KhoiPhuTrach'))
    
    # 8a: Kiểm tra không có dữ liệu giáo viên hoặc lớp học
    if not all_teachers:
        errors.append("Không có giáo viên hoặc lớp học để phân công")
        return results, errors
            
    lich_thi_list = sorted(lich_thi_list, key=lambda x: str(x.Khoi.TenKhoi), reverse=True)
    
    slots = []
    domains = []
    
    # Pre-processing: Generate Variables (slots) and Domains
    for lich in lich_thi_list:
        lop_hocs = LopHoc.objects.filter(MaKhoi=lich.Khoi, MaNamHoc=lich.NamHoc)
        if not lop_hocs.exists():
            errors.append(f"Không có lớp học nào cho khối {lich.Khoi.TenKhoi}")
            continue
            
        is_k5_toan_tv = ('5' in lich.Khoi.TenKhoi and lich.MonHoc.TenMon in ['Toán', 'Tiếng Việt'])
        
        for lop in lop_hocs:
            valid_teachers = []
            for t in all_teachers:
                # Rule 2: Giáo viên chủ nhiệm không được coi lớp mình dạy
                if lop.GVCN_id == t.id:
                    continue
                    
                khoi_gd_names = [k.TenKhoi for k in t.KhoiPhuTrach.all()]
                if not khoi_gd_names:
                    continue
                    
                if '1' in lich.Khoi.TenKhoi:
                    if not any('1' in k or '2' in k for k in khoi_gd_names):
                        continue
                elif any(c in lich.Khoi.TenKhoi for c in ['2', '3']):
                    if any(lich.Khoi.TenKhoi in k for k in khoi_gd_names):
                        continue
                elif any(c in lich.Khoi.TenKhoi for c in ['4', '5']):
                    if any(lich.Khoi.TenKhoi in k for k in khoi_gd_names):
                        continue
                        
                valid_teachers.append(t)
                
            if is_k5_toan_tv:
                slots.append({'lich': lich, 'lop': lop, 'type': 'gt1', 'is_k5': True})
                domains.append(valid_teachers)
            else:
                slots.append({'lich': lich, 'lop': lop, 'type': 'gt1', 'is_k5': False})
                domains.append(valid_teachers)
                slots.append({'lich': lich, 'lop': lop, 'type': 'gt2', 'is_k5': False})
                domains.append(valid_teachers)

    if not slots:
        errors.append("Không tìm thấy lịch thi hoặc lịch thi chưa hoàn tất")
        return results, errors

    assignment = [None] * len(slots)
    teacher_schedule = defaultdict(list)
    
    best_assignment = [None] * len(slots)
    min_unassigned = len(slots)
    
    import random
    iteration_count = 0
    
    def solve(slot_index, unassigned_count):
        nonlocal min_unassigned, best_assignment, iteration_count
        
        iteration_count += 1
        if iteration_count > 15000:
            return
            
        # Pruning
        if unassigned_count >= min_unassigned:
            return
            
        if slot_index == len(slots):
            if unassigned_count < min_unassigned:
                min_unassigned = unassigned_count
                best_assignment = list(assignment)
            return

        slot = slots[slot_index]
        lich = slot['lich']
        
        # Shuffle domain to get different solutions, then sort by teacher workload ascending
        dom = list(domains[slot_index])
        random.shuffle(dom)
        domain = sorted(dom, key=lambda t: len(teacher_schedule[t.id]))
        
        # Try assigning a teacher
        for t in domain:
            overlap = False
            for (d, start, end) in teacher_schedule[t.id]:
                if d == lich.NgayThi:
                    if max(lich.GioBatDau, start) < min(lich.GioKetThuc, end):
                        overlap = True
                        break
            if overlap:
                continue
                
            if slot['type'] == 'gt2':
                # Check if same as gt1 of the same room/exam
                if assignment[slot_index - 1] == t:
                    continue
                    
            # Assign
            assignment[slot_index] = t
            teacher_schedule[t.id].append((lich.NgayThi, lich.GioBatDau, lich.GioKetThuc))
            
            solve(slot_index + 1, unassigned_count)
            if min_unassigned == 0:
                return
                
            # Backtrack
            assignment[slot_index] = None
            teacher_schedule[t.id].pop()
            
        # Try leaving this slot unassigned
        assignment[slot_index] = None
        solve(slot_index + 1, unassigned_count + 1)

    solve(0, 0)
    
    # Build kết quả từ best_assignment
    idx = 0
    while idx < len(slots):
        slot = slots[idx]
        lich = slot['lich']
        lop = slot['lop']
        
        res = {
            'lich_thi_id': lich.id,
            'lich_thi_str': str(lich),
            'lop_hoc_id': lop.id,
            'lop_hoc_str': lop.TenLop,
            'is_khối_5_toan_tv': slot['is_k5'],
            'giam_thi_1_id': None, 'giam_thi_1_str': '',
            'giam_thi_2_id': None, 'giam_thi_2_str': '',
            'giam_thi_thcs': ''
        }
        
        gt1 = best_assignment[idx]
        if gt1:
            res['giam_thi_1_id'] = gt1.id
            res['giam_thi_1_str'] = gt1.HoTen
            
        if not slot['is_k5']:
            gt2 = best_assignment[idx + 1]
            if gt2:
                res['giam_thi_2_id'] = gt2.id
                res['giam_thi_2_str'] = gt2.HoTen
            idx += 2
        else:
            idx += 1
            
        results.append(res)
        
    if min_unassigned > 0:
        errors.append(f"Không thể phân công giám thị đầy đủ cho tất cả các lớp do không đủ giáo viên thỏa mãn các ràng buộc nghiệp vụ (Thiếu {min_unassigned} lượt phân công). Các phòng thi chưa phân công đủ được đánh dấu rõ bằng nhãn 'Thiếu giám thị'.")
        
    return results, errors
