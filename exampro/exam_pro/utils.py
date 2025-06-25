import frappe

def redirect_to_exams_list():
    frappe.local.flags.redirect_location = "/my-exams"
    raise frappe.Redirect

def get_website_context(context):
    user_roles = frappe.get_roles(frappe.session.user)
    top_bar_items = []
    
    if "Exam Proctor" in user_roles:
        top_bar_items.append({"label": "Proctor Exam", "url": "/proctor"})
    
    if "Exam Evaluator" in user_roles:
        top_bar_items.append({"label": "Evaluate Exam", "url": "/evaluate"})
    
    if "Exam Manager" in user_roles:
        top_bar_items.append({
            "label": "🛠️ Exam Builder", "right": True, "url": "/manage/exam-builder"
        })
        top_bar_items.append({
            "label": "Manage",
            "url": "#",  # Add a URL or use "#" for dropdown parent
            "right": True,
            "child_items": [  # Use child_items instead of dropdown_items
                {"label": "Users", "url": "/manage/users"},
                {"label": "Batches", "url": "/manage/batches"},
                {"label": "Exams", "url": "/manage/exams"},
                {"label": "Schedules", "url": "/manage/schedules"},
                {"label": "Questions", "url": "/manage/questions"}
            ]
        })
    
    context.top_bar_items = top_bar_items
    return context