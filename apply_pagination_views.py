import os
import re

VIEWS_TO_UPDATE = {
    r"core\\views_teacher.py": ("teachers", "def teacher_list(request):"),
    r"core\\views_account.py": ("accounts", "def account_list(request):"),
    r"core\\views_schoolyear.py": ("schoolyears", "def schoolyear_list(request):"),
    r"core\\views_subject.py": ("subjects", "def subject_list(request):"),
    r"core\\views_class.py": ("classes", "def class_list(request):"),
    r"question_bank\\views.py": ("questions", "def question_list(request):"),
    r"matrix\\views.py": ("matrices", "def matrix_list(request):"),
    r"exam\\views.py": ("exams", "def exam_list(request):"),
    r"schedule\\views_schedule.py": ("schedules", "def schedule_list(request):"),
}

base_dir = r"d:\HT Khao Thi"

for rel_path, (var_name, func_def) in VIEWS_TO_UPDATE.items():
    file_path = os.path.join(base_dir, rel_path)
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "from django.core.paginator import Paginator" not in content:
        content = "from django.core.paginator import Paginator\n" + content
        
    # Replace the return render block
    # We look for the last line of the function before return render.
    # Usually it's something like:
    # return render(request, '...', {'teachers': teachers, ...})
    
    # We can just insert the paginator code right before return render
    pattern = r"(return render\(request, '[^']+', \{[^\}]*" + var_name + r"[^\}]*\}\))"
    
    def repl(m):
        render_stmt = m.group(1)
        paginator_code = f"""
    paginator = Paginator({var_name}, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    {var_name} = page_obj
    # inject page_obj into context
"""
        # Inject 'page_obj': page_obj into the context dict if not there
        if "'page_obj'" not in render_stmt:
            render_stmt = render_stmt.replace("})", ", 'page_obj': page_obj})")
            
        return paginator_code + "    " + render_stmt
        
    new_content = re.sub(pattern, repl, content)
    
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {file_path}")
    else:
        print(f"Failed or already updated {file_path}")

