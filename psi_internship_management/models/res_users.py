from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    intern_student_ids = fields.One2many(
        "psi.intern.student",
        "supervisor_id",
        string="Praktykanci",
    )
    intern_application_ids = fields.One2many(
        "psi.intern.application",
        "supervisor_id",
        string="Zgloszenia praktykantow",
    )

    def unlink(self):
        portal_users = self.filtered("share")
        if portal_users:
            students = self.env["psi.intern.student"].sudo().search(
                [("user_id", "in", portal_users.ids)]
            )
            applications = self.env["psi.intern.application"].sudo().search(
                [("user_id", "in", portal_users.ids)]
            )

            if students:
                students.write({"user_id": False})
                students.unlink()

            if applications:
                applications.write({"user_id": False})
                applications.unlink()

        return super().unlink()
