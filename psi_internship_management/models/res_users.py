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
