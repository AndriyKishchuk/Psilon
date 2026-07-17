from odoo import http
from odoo.http import request


class InternshipPortalController(http.Controller):

    @http.route("/my/internship", type="http", auth="user", website=True)
    def my_internship(self, **kwargs):
        student = request.env["psi.intern.student"].sudo().search(
            [("user_id", "=", request.env.user.id)],
            limit=1,
        )

        values = {
            "student": student,
            "page_name": "my_internship",
        }
        return request.render("psi_internship_portal.portal_my_internship", values)

    @http.route("/my/internship/attendance", type="http", auth="user", website=True)
    def my_internship_attendance(self, **kwargs):
        student = request.env["psi.intern.student"].sudo().search(
            [("user_id", "=", request.env.user.id)],
            limit=1,
        )

        attendances = student.attendance_ids.sorted("start_datetime") if student else request.env["psi.intern.attendance"]

        values = {
            "student": student,
            "attendances": attendances,
            "page_name": "my_internship_attendance",
        }
        return request.render("psi_internship_portal.portal_my_internship_attendance", values)
