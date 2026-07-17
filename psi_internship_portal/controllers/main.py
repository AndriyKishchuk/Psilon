from odoo import fields, http
from odoo.http import request


class InternshipPortalController(http.Controller):

    def _get_student_for_current_user(self):
        return request.env["psi.intern.student"].sudo().search(
            [("user_id", "=", request.env.user.id)],
            limit=1,
        )

    def _get_dashboard_values(self, student, message=None):
        attendances = request.env["psi.intern.attendance"]
        attendance_count = 0
        next_attendance = request.env["psi.intern.attendance"]
        current_attendance = request.env["psi.intern.attendance"]
        progress_percent = 0
        document_count = 0

        if student:
            attendances = student.attendance_ids.sorted("start_datetime")
            attendance_count = len(attendances)
            document_count = len(student.document_ids)
            now = fields.Datetime.now()
            current_attendance = attendances.filtered(lambda a: a.start_datetime and not a.end_datetime)[:1]
            next_attendance = attendances.filtered(lambda a: a.start_datetime and a.start_datetime >= now and a.id != current_attendance.id)[:1]
            if getattr(student, "required_hours", 0):
                progress_percent = min(100, round((student.total_attendance_hours / student.required_hours) * 100))

        return {
            "student": student,
            "page_name": "my_internship",
            "attendance_count": attendance_count,
            "next_attendance": next_attendance,
            "current_attendance": current_attendance,
            "progress_percent": progress_percent,
            "document_count": document_count,
            "message": message,
        }

    @http.route("/my/internship", type="http", auth="user", website=True)
    def my_internship(self, message=None, **kwargs):
        student = self._get_student_for_current_user()
        values = self._get_dashboard_values(student, message=message)
        return request.render("psi_internship_portal.portal_my_internship", values)

    @http.route("/my/internship/attendance", type="http", auth="user", website=True)
    def my_internship_attendance(self, **kwargs):
        student = self._get_student_for_current_user()
        attendances = student.attendance_ids.sorted("start_datetime") if student else request.env["psi.intern.attendance"]

        values = {
            "student": student,
            "attendances": attendances,
            "page_name": "my_internship_attendance",
        }
        return request.render("psi_internship_portal.portal_my_internship_attendance", values)

    @http.route("/my/internship/check_in", type="http", auth="user", website=True, methods=["POST"])
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

        request.env["psi.intern.attendance"].sudo().create({
            "intern_id": student.id,
            "user_id": request.env.user.id,
            "start_datetime": fields.Datetime.now(),
            "note": "Portal check in",
        })
        return request.redirect("/my/internship?message=checked_in")

    @http.route("/my/internship/check_out", type="http", auth="user", website=True, methods=["POST"])
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

        current_attendance.sudo().write({
            "end_datetime": fields.Datetime.now(),
        })
        return request.redirect("/my/internship?message=checked_out")
