import base64

from odoo import fields, http
from odoo.http import request


class InternshipPortalController(http.Controller):

    @staticmethod
    def _format_hours_label(hours):
        total_minutes = round((hours or 0.0) * 60)
        hour_part = total_minutes // 60
        minute_part = total_minutes % 60
        if hour_part and minute_part:
            return f"{hour_part} h {minute_part} min"
        if hour_part:
            return f"{hour_part} h"
        return f"{minute_part} min"

    def _get_student_for_current_user(self):
        return request.env["psi.intern.student"].sudo().search(
            [("user_id", "=", request.env.user.id)],
            limit=1,
        )

    def _get_portal_status(self, student):
        if not student:
            return "new", "Nowy"

        if student.status == "cancelled":
            return "cancelled", "Anulowany"

        today = fields.Date.today()
        if not student.start_date:
            return "new", "Nowy"
        if student.end_date:
            if today < student.start_date:
                return "new", "Nowy"
            if student.start_date <= today <= student.end_date:
                return "active", "Aktywna"
            if today > student.end_date:
                return "finished", "Zakonczona"
        if today < student.start_date:
            return "new", "Nowy"
        return "active", "Aktywna"

    def _get_default_supervisor(self):
        return request.env["res.users"].sudo().search(
            [("share", "=", False), ("active", "=", True)],
            limit=1,
            order="id asc",
        )

    def _get_dashboard_values(self, student, message=None, form_values=None):
        attendances = request.env["psi.intern.attendance"]
        attendance_count = 0
        next_attendance = request.env["psi.intern.attendance"]
        current_attendance = request.env["psi.intern.attendance"]
        progress_percent = 0
        document_count = 0
        total_hours_display = self._format_hours_label(0.0)
        next_attendance_duration_display = self._format_hours_label(0.0)
        portal_status, portal_status_label = self._get_portal_status(student)

        if student:
            attendances = student.attendance_ids.sorted("start_datetime")
            attendance_count = len(attendances)
            document_count = len(student.document_ids)
            total_hours_display = self._format_hours_label(
                student.total_attendance_hours
            )
            now = fields.Datetime.now()
            current_attendance = attendances.filtered(
                lambda a: a.start_datetime and not a.end_datetime
            )[:1]
            next_attendance = attendances.filtered(
                lambda a: a.start_datetime
                and a.start_datetime >= now
                and a.id != current_attendance.id
            )[:1]
            if getattr(student, "required_hours", 0):
                progress_percent = min(
                    100,
                    round(
                        (student.total_attendance_hours / student.required_hours) * 100
                    ),
                )
            if next_attendance:
                next_attendance_duration_display = self._format_hours_label(
                    next_attendance.duration_hours
                )

        documents = student.document_ids.sorted(
            key=lambda d: d.create_date or d.id,
            reverse=True,
        ) if student else request.env["ir.attachment"]

        return {
            "student": student,
            "page_name": "my_internship",
            "portal_status": portal_status,
            "portal_status_label": portal_status_label,
            "attendance_count": attendance_count,
            "next_attendance": next_attendance,
            "current_attendance": current_attendance,
            "progress_percent": progress_percent,
            "document_count": document_count,
            "documents": documents,
            "total_hours_display": total_hours_display,
            "next_attendance_duration_display": next_attendance_duration_display,
            "message": message,
            "form_values": form_values or {},
        }

    def _get_profile_values(self, student, message=None):
        portal_status, portal_status_label = self._get_portal_status(student)
        documents = (
            student.document_ids.sorted(
                key=lambda d: d.create_date or d.id,
                reverse=True,
            )
            if student
            else request.env["ir.attachment"]
        )
        return {
            "student": student,
            "page_name": "my_internship_profile",
            "portal_status": portal_status,
            "portal_status_label": portal_status_label,
            "documents": documents,
            "document_count": len(documents) if student else 0,
            "total_hours_display": self._format_hours_label(
                student.total_attendance_hours if student else 0.0
            ),
            "message": message,
        }

    def _get_documents_values(self, student, message=None):
        portal_status, portal_status_label = self._get_portal_status(student)
        documents = (
            student.document_ids.sorted(
                key=lambda d: d.create_date or d.id,
                reverse=True,
            )
            if student
            else request.env["ir.attachment"]
        )
        return {
            "student": student,
            "page_name": "my_internship_documents",
            "portal_status": portal_status,
            "portal_status_label": portal_status_label,
            "documents": documents,
            "document_count": len(documents) if student else 0,
            "message": message,
        }

    def _get_public_registration_values(self, message=None, form_values=None):
        return {
            "page_name": "internship_public_register",
            "message": message,
            "form_values": form_values or {},
        }

    @http.route("/internship/register", type="http", auth="public", website=True)
    def internship_public_register(self, message=None, **kwargs):
        if request.env.user and request.env.user.id and not request.env.user._is_public():
            student = self._get_student_for_current_user()
            if student:
                return request.redirect("/my/internship")
        values = self._get_public_registration_values(message=message)
        return request.render("psi_internship_portal.portal_internship_public_register", values)

    @http.route(
        "/internship/register/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def internship_public_register_submit(self, **post):
        name = (post.get("name") or "").strip()
        email = (post.get("email") or "").strip().lower()
        password = (post.get("password") or "").strip()
        password_confirm = (post.get("password_confirm") or "").strip()
        phone = (post.get("phone") or "").strip()
        school = (post.get("school") or "").strip()
        field_of_study = (post.get("field_of_study") or "").strip()
        required_hours_raw = (post.get("required_hours") or "").strip()
        start_date = (post.get("start_date") or "").strip()
        end_date = (post.get("end_date") or "").strip()
        notes = (post.get("notes") or "").strip()

        form_values = {
            "name": name,
            "email": email,
            "phone": phone,
            "school": school,
            "field_of_study": field_of_study,
            "required_hours": required_hours_raw,
            "start_date": start_date,
            "end_date": end_date,
            "notes": notes,
        }

        if not name or not email or not password or not password_confirm or not school or not field_of_study or not required_hours_raw:
            values = self._get_public_registration_values(
                message="registration_missing_fields",
                form_values=form_values,
            )
            return request.render("psi_internship_portal.portal_internship_public_register", values)

        try:
            required_hours = int(required_hours_raw)
        except ValueError:
            required_hours = 0

        if required_hours <= 0:
            values = self._get_public_registration_values(
                message="registration_invalid_required_hours",
                form_values=form_values,
            )
            return request.render("psi_internship_portal.portal_internship_public_register", values)

        if password != password_confirm:
            values = self._get_public_registration_values(
                message="registration_password_mismatch",
                form_values=form_values,
            )
            return request.render("psi_internship_portal.portal_internship_public_register", values)

        existing_user = request.env["res.users"].sudo().search(
            [("login", "=", email)],
            limit=1,
        )
        if existing_user:
            values = self._get_public_registration_values(
                message="registration_email_exists",
                form_values=form_values,
            )
            return request.render("psi_internship_portal.portal_internship_public_register", values)

        supervisor = self._get_default_supervisor()
        if not supervisor:
            values = self._get_public_registration_values(
                message="registration_no_supervisor",
                form_values=form_values,
            )
            return request.render("psi_internship_portal.portal_internship_public_register", values)

        portal_group = request.env.ref("base.group_portal")
        user = request.env["res.users"].sudo().with_context(no_reset_password=True).create(
            {
                "name": name,
                "login": email,
                "password": password,
                "email": email,
                "phone": phone,
                "groups_id": [(6, 0, [portal_group.id])],
            }
        )

        vals = {
            "name": name,
            "user_id": user.id,
            "phone": phone,
            "email": email,
            "school": school,
            "field_of_study": field_of_study,
            "required_hours": required_hours,
            "supervisor_id": supervisor.id,
            "notes": notes,
        }
        if start_date:
            vals["start_date"] = start_date
        if end_date:
            vals["end_date"] = end_date

        request.env["psi.intern.student"].sudo().create(vals)
        request.env.cr.commit()
        request.session.authenticate(request.db, {"login": email, "password": password, "type": "password"})
        return request.redirect("/my/internship?message=registered")

    @http.route("/my/internship", type="http", auth="user", website=True)
    def my_internship(self, message=None, **kwargs):
        student = self._get_student_for_current_user()
        values = self._get_dashboard_values(student, message=message)
        return request.render("psi_internship_portal.portal_my_internship", values)

    @http.route("/my/internship/profile", type="http", auth="user", website=True)
    def my_internship_profile(self, message=None, **kwargs):
        student = self._get_student_for_current_user()
        values = self._get_profile_values(student, message=message)
        return request.render(
            "psi_internship_portal.portal_my_internship_profile",
            values,
        )

    @http.route("/my/internship/documents", type="http", auth="user", website=True)
    def my_internship_documents(self, message=None, **kwargs):
        student = self._get_student_for_current_user()
        values = self._get_documents_values(student, message=message)
        return request.render(
            "psi_internship_portal.portal_my_internship_documents",
            values,
        )

    @http.route(
        "/my/internship/register",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def my_internship_register(self, **post):
        student = self._get_student_for_current_user()
        if student:
            return request.redirect("/my/internship")

        name = (post.get("name") or request.env.user.name or "").strip()
        phone = (post.get("phone") or "").strip()
        school = (post.get("school") or "").strip()
        field_of_study = (post.get("field_of_study") or "").strip()
        start_date = (post.get("start_date") or "").strip()
        end_date = (post.get("end_date") or "").strip()
        notes = (post.get("notes") or "").strip()
        email = (request.env.user.email or request.env.user.partner_id.email or "").strip()

        form_values = {
            "name": name,
            "phone": phone,
            "school": school,
            "field_of_study": field_of_study,
            "start_date": start_date,
            "end_date": end_date,
            "notes": notes,
        }

        if not name or not school or not field_of_study:
            values = self._get_dashboard_values(
                request.env["psi.intern.student"],
                message="registration_missing_fields",
                form_values=form_values,
            )
            return request.render("psi_internship_portal.portal_my_internship", values)

        supervisor = self._get_default_supervisor()
        if not supervisor:
            values = self._get_dashboard_values(
                request.env["psi.intern.student"],
                message="registration_no_supervisor",
                form_values=form_values,
            )
            return request.render("psi_internship_portal.portal_my_internship", values)

        vals = {
            "name": name,
            "user_id": request.env.user.id,
            "phone": phone,
            "email": email,
            "school": school,
            "field_of_study": field_of_study,
            "supervisor_id": supervisor.id,
            "notes": notes,
        }
        if start_date:
            vals["start_date"] = start_date
        if end_date:
            vals["end_date"] = end_date

        request.env["psi.intern.student"].sudo().create(vals)
        request.env.user.sudo().write({"name": name})
        request.env.user.partner_id.sudo().write(
            {
                "name": name,
                "phone": phone,
                "email": email,
            }
        )
        return request.redirect("/my/internship?message=registered")

    @http.route("/my/internship/attendance", type="http", auth="user", website=True)
    def my_internship_attendance(self, **kwargs):
        student = self._get_student_for_current_user()
        attendances = (
            student.attendance_ids.sorted("start_datetime")
            if student
            else request.env["psi.intern.attendance"]
        )

        values = {
            "student": student,
            "attendances": attendances,
            "page_name": "my_internship_attendance",
            "documents": student.document_ids.sorted(
                key=lambda d: d.create_date or d.id,
                reverse=True,
            ) if student else request.env["ir.attachment"],
        }
        return request.render(
            "psi_internship_portal.portal_my_internship_attendance", values
        )

    @http.route(
        "/my/internship/check_in",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def my_internship_check_in(self, **kwargs):
        student = self._get_student_for_current_user()
        if not student:
            return request.redirect("/my/internship?message=no_student")

        current_attendance = request.env["psi.intern.attendance"].sudo().search(
            [
                ("intern_id", "=", student.id),
                ("user_id", "=", request.env.user.id),
                ("end_datetime", "=", False),
            ],
            limit=1,
            order="start_datetime desc",
        )
        if current_attendance:
            return request.redirect("/my/internship?message=already_checked_in")

        request.env["psi.intern.attendance"].sudo().create(
            {
                "intern_id": student.id,
                "user_id": request.env.user.id,
                "start_datetime": fields.Datetime.now(),
                "note": "Portal check in",
            }
        )
        return request.redirect("/my/internship?message=checked_in")

    @http.route(
        "/my/internship/check_out",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def my_internship_check_out(self, **kwargs):
        student = self._get_student_for_current_user()
        if not student:
            return request.redirect("/my/internship?message=no_student")

        current_attendance = request.env["psi.intern.attendance"].sudo().search(
            [
                ("intern_id", "=", student.id),
                ("user_id", "=", request.env.user.id),
                ("end_datetime", "=", False),
            ],
            limit=1,
            order="start_datetime desc",
        )
        if not current_attendance:
            return request.redirect("/my/internship?message=no_open_attendance")

        current_attendance.sudo().write(
            {
                "end_datetime": fields.Datetime.now(),
            }
        )
        return request.redirect("/my/internship?message=checked_out")


    @http.route(
        "/my/internship/upload_document",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def my_internship_upload_document(self, **post):
        student = self._get_student_for_current_user()
        if not student:
            return request.redirect("/my/internship?message=no_student")

        file_storage = request.httprequest.files.get("document")
        if not file_storage or not file_storage.filename:
            return request.redirect("/my/internship?message=upload_missing")

        content = file_storage.read()
        if not content:
            return request.redirect("/my/internship?message=upload_missing")

        attachment = request.env["ir.attachment"].sudo().create({
            "name": file_storage.filename,
            "datas": base64.b64encode(content),
            "res_model": "psi.intern.student",
            "res_id": student.id,
            "mimetype": file_storage.mimetype,
            "type": "binary",
        })
        student.sudo().write({"document_ids": [(4, attachment.id)]})
        return request.redirect("/my/internship?message=upload_success")
