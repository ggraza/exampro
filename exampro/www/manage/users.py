import frappe
from frappe import _
from frappe.utils import validate_email_address

@frappe.whitelist()
def update_user_role(user, role, action):
    """
    Update a user's role (add or remove)
    
    Args:
        user (str): User email or name
        role (str): Role to add or remove (Candidate, Proctor, Evaluator)
        action (str): 'add' or 'remove'
    """
    if not frappe.has_permission("User", "write"):
        return {"success": False, "error": _("Not permitted")}
    
    try:
        # Validate role
        if role not in ["Candidate", "Proctor", "Evaluator"]:
            return {"success": False, "error": _("Invalid role")}
        
        # Format role name according to application standards
        role_name = f"Exam {role}"
        
        user_doc = frappe.get_doc("User", user)
        
        # Check if role already exists for user
        has_role = False
        for r in user_doc.roles:
            if r.role == role_name:
                has_role = True
                break
        
        if action == "add" and not has_role:
            # Add role
            user_doc.append("roles", {"role": role_name})
            user_doc.save(ignore_permissions=True)
            frappe.db.commit()
            return {"success": True}
            
        elif action == "remove" and has_role:
            # Remove role
            roles = [r for r in user_doc.roles if r.role != role_name]
            user_doc.roles = roles
            user_doc.save(ignore_permissions=True)
            frappe.db.commit()
            return {"success": True}
            
        else:
            # No change needed
            return {"success": True}
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Error updating role for {user}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def add_users(emails, role, batch=None):
    """
    Add new users and assign the specified role and optionally add to a batch
    
    Args:
        emails (str): Comma-separated list of email addresses
        role (str): Role to assign (Exam Candidate, Exam Proctor, Exam Evaluator)
        batch (str, optional): Exam batch to assign users to (only applies to Exam Candidate)
    """
    if not frappe.has_permission("User", "write"):
        return {"success": False, "error": _("Not permitted")}
    
    try:
        # Validate role
        if role not in ["Exam Candidate", "Exam Proctor", "Exam Evaluator"]:
            return {"success": False, "error": _("Invalid role")}
        
        # Use the role name directly
        role_name = role
        
        # Parse emails
        email_list = [email.strip() for email in emails.split(',')]
        added_count = 0
        error_count = 0
        errors = []
        
        for email in email_list:
            if not email:
                continue
                
            # Validate email
            try:
                validate_email_address(email)
            except Exception:
                error_count += 1
                errors.append(f"Invalid email: {email}")
                continue
                
            # Check if user already exists
            user_exists = frappe.db.exists("User", {"email": email})
            
            if user_exists:
                user_doc = frappe.get_doc("User", {"email": email})
            else:
                # Create new user
                user_doc = frappe.get_doc({
                    "doctype": "User",
                    "email": email,
                    "first_name": email.split("@")[0],
                    "send_welcome_email": 1,
                    "enabled": 1,
                })
                user_doc.insert(ignore_permissions=True)
            
            # Assign role if not already assigned
            has_role = False
            for r in user_doc.roles:
                if r.role == role_name:
                    has_role = True
                    break
            
            if not has_role:
                user_doc.append("roles", {"role": role_name})
                user_doc.save(ignore_permissions=True)
            
            # Add user to batch if specified and role is Exam Candidate
            if batch and role == "Exam Candidate":
                # Check if user is already in the batch
                batch_user_exists = frappe.db.exists(
                    "Exam Batch User", 
                    {"candidate": user_doc.name, "exam_batch": batch}
                )
                
                if not batch_user_exists:
                    batch_user = frappe.get_doc({
                        "doctype": "Exam Batch User",
                        "candidate": user_doc.name,
                        "exam_batch": batch
                    })
                    batch_user.insert(ignore_permissions=True)
            
            added_count += 1
        
        frappe.db.commit()
        
        message = f"Added {added_count} users successfully"
        if error_count > 0:
            message += f", {error_count} failed"
            
        return {
            "success": True, 
            "message": message,
            "errors": errors if errors else None
        }
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error adding users")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_filtered_users(search='', role='', batch=''):
    """
    Get users with filtering applied server-side
    
    Args:
        search (str): Search term for filtering by email/name
        role (str): Filter by specific role (candidate, proctor, evaluator)
        batch (str): Filter by specific batch name
        
    Returns:
        dict: Dictionary with filtered users
    """
    if not frappe.has_permission("User", "read"):
        return {"success": False, "error": _("Not permitted")}
    
    try:
        # Get all non-system users
        users = frappe.get_all(
            "User", 
            filters={"user_type": ["!=", "System User"]},
            fields=["name", "email", "full_name", "first_name", "last_name", "enabled"]
        )
        
        # Add role information
        for user in users:
            user_roles = frappe.get_roles(user["name"])
            user["is_candidate"] = "Exam Candidate" in user_roles
            user["is_proctor"] = "Exam Proctor" in user_roles
            user["is_evaluator"] = "Exam Evaluator" in user_roles
            
            # Add batch information
            user_batches = frappe.get_all(
                "Exam Batch User", 
                filters={"candidate": user["name"]}, 
                fields=["exam_batch"]
            )
            user["batches"] = [ub.exam_batch for ub in user_batches]
        
        # Apply filters
        filtered_users = []
        for user in users:
            # Search filter
            if search and search.lower() not in user["email"].lower():
                continue
                
            # Role filter
            if role:
                if role == 'candidate' and not user["is_candidate"]:
                    continue
                elif role == 'proctor' and not user["is_proctor"]:
                    continue
                elif role == 'evaluator' and not user["is_evaluator"]:
                    continue
            
            # Batch filter
            if batch and batch not in user["batches"]:
                continue
                
            # User passed all filters
            filtered_users.append(user)
            
        return {"success": True, "users": filtered_users}
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error getting filtered users")
        return {"success": False, "error": str(e)}

def get_users():
    """
    Get all users with their roles
    """
    # Get all website users
    users = frappe.get_all(
        "User", 
        filters={"user_type": ["!=", "System User"]},
        fields=["name", "email", "full_name", "first_name", "last_name", "enabled"]
    )
    
    # Add role information
    for user in users:
        user_roles = frappe.get_roles(user["name"])
        user["is_candidate"] = "Exam Candidate" in user_roles
        user["is_proctor"] = "Exam Proctor" in user_roles
        user["is_evaluator"] = "Exam Evaluator" in user_roles
    
    return users

@frappe.whitelist()
def get_user_batches(user):
    """
    Get all batches a user belongs to
    
    Args:
        user (str): User email/name
        
    Returns:
        list: List of batch names
    """
    if not frappe.has_permission("Exam Batch User", "read"):
        return []
    
    batch_users = frappe.get_all(
        "Exam Batch User", 
        filters={"candidate": user}, 
        fields=["exam_batch"]
    )
    
    batches = [bu.exam_batch for bu in batch_users]
    return batches

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
    
    # Check if user has Exam Manager role
    if "Exam Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw(_("You are not authorized to access this page"))

    # Get all batches for filter dropdown
    batches = frappe.get_all("Exam Batch", fields=["name"])
    context.batches = batches
    
    # Set page data
    context.no_cache = 1
    
    # Users will be loaded via AJAX
    # We're no longer preloading user data in the context
    
    context.metatags = {
        "title": _("Manage Users"),
        "description": "Manage exam system users and their permissions"
    }
